from fastapi import HTTPException
from app.repositories import papers, recipes

WRAP_STYLES = ("cross", "band")

def _validate(overlap, wrap_style, paper_id):
    if overlap is None or overlap <= 0:
        raise HTTPException(422, "overlap must be positive")
    if wrap_style not in WRAP_STYLES:
        raise HTTPException(422, "wrap_style must be cross or band")
    if not papers.get_paper(paper_id):
        raise HTTPException(422, "paper not found")

def create_recipe(payload):
    _validate(payload.overlap, payload.wrap_style, payload.paper_id)
    if not str(payload.name or "").strip():
        raise HTTPException(422, "name required")
    rid = recipes.create_recipe(
        payload.name.strip(), payload.overlap, payload.wrap_style,
        payload.paper_id, payload.note,
    )
    return recipes.get_recipe(rid)

def add_version(rid, payload):
    if recipes.get_recipe(rid) is None:
        raise HTTPException(404, "recipe not found")
    _validate(payload.overlap, payload.wrap_style, payload.paper_id)
    new_rev = recipes.add_version(
        rid, payload.overlap, payload.wrap_style, payload.paper_id, payload.note,
    )
    return recipes.get_version(rid, new_rev)

def set_active(rid, active):
    if recipes.get_recipe(rid) is None:
        raise HTTPException(404, "recipe not found")
    recipes.set_active(rid, active)
    return recipes.get_recipe(rid)
