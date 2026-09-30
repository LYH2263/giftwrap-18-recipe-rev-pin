import sqlite3

from fastapi import APIRouter, HTTPException

from app.repositories import papers, recipes
from app.schemas.recipe import RecipeCreate, RevisionCreate

router = APIRouter()


def _require_paper(paper_id: int):
    if not papers.get_paper(paper_id):
        raise HTTPException(404, "paper not found")


@router.get("/recipes")
def list_all():
    return {"items": recipes.list_recipes()}


@router.get("/recipes/active")
def list_active():
    # Bench dropdown source — must stay in sync with the Recipes page current rev.
    return {"items": recipes.list_recipes(active_only=True)}


@router.post("/recipes")
def create_recipe(body: RecipeCreate):
    _require_paper(body.paper_id)
    return recipes.create_recipe(body.name, body.overlap, body.wrap_style, body.paper_id)


@router.get("/recipes/{rid}")
def get_recipe(rid: int):
    master = recipes.get_recipe(rid)
    if not master:
        raise HTTPException(404)
    return {**master, "revisions": recipes.list_versions(rid)}


@router.post("/recipes/{rid}/revisions")
def add_revision(rid: int, body: RevisionCreate):
    master = recipes.get_recipe(rid)
    if not master:
        raise HTTPException(404, "recipe not found")
    if master["active"] != 1:
        raise HTTPException(409, "recipe is deactivated")
    _require_paper(body.paper_id)
    try:
        return recipes.add_revision(rid, body.overlap, body.wrap_style, body.paper_id)
    except sqlite3.IntegrityError:
        raise HTTPException(409, "revision conflict")


@router.get("/recipes/{rid}/revisions/{rev}")
def get_revision(rid: int, rev: int):
    if not recipes.get_recipe(rid):
        raise HTTPException(404, "recipe not found")
    version = recipes.get_version(rid, rev)
    if not version:
        raise HTTPException(404, "recipe revision not found")
    return version


@router.post("/recipes/{rid}/deactivate")
def deactivate(rid: int):
    if not recipes.set_active(rid, False):
        raise HTTPException(404)
    master = recipes.get_recipe(rid)
    return {"id": rid, "active": master["active"], "current_rev": master["current_rev"]}


@router.post("/recipes/{rid}/activate")
def activate(rid: int):
    if not recipes.set_active(rid, True):
        raise HTTPException(404)
    master = recipes.get_recipe(rid)
    return {"id": rid, "active": master["active"], "current_rev": master["current_rev"]}
