from fastapi import APIRouter, HTTPException
from app.repositories import recipes as repo
from app.schemas.recipe import ActiveIn, RecipeCreate, RecipeVersionIn
from app.services import recipe_service
router = APIRouter()

@router.get("/recipes")
def list_all():
    return {"items": repo.list_recipes()}

@router.get("/recipes/active")
def list_active():
    return {"items": repo.list_recipes(active_only=True)}

@router.get("/recipes/{rid}")
def detail(rid: int):
    r = repo.get_recipe(rid)
    if not r:
        raise HTTPException(404, "recipe not found")
    return r

@router.get("/recipes/{rid}/versions")
def versions(rid: int):
    return {"items": repo.list_versions(rid)}

@router.get("/recipes/{rid}/versions/{rev}")
def version_detail(rid: int, rev: int):
    v = repo.get_version(rid, rev)
    if not v:
        raise HTTPException(404, "recipe revision not found")
    return v

@router.post("/recipes", status_code=201)
def create(body: RecipeCreate):
    return recipe_service.create_recipe(body)

@router.post("/recipes/{rid}/versions", status_code=201)
def add_version(rid: int, body: RecipeVersionIn):
    return recipe_service.add_version(rid, body)

@router.post("/recipes/{rid}/active")
def set_active(rid: int, body: ActiveIn):
    return recipe_service.set_active(rid, body.active)
