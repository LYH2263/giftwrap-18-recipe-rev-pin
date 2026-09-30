from fastapi import HTTPException
from app.engines.wrap_math import paper_area, ribbon_estimate
from app.repositories import boxes, history, recipes, settings_repo

def run_estimate(box_id: int, overlap: float | None, wrap_style: str, save: bool, note: str,
                 recipe_id: int | None = None, recipe_rev: int | None = None):
    box = boxes.get_box(box_id)
    if not box:
        raise HTTPException(404)
    if box.get("data_quality") == "dirty":
        raise HTTPException(422, "dirty box")
    if recipe_rev is not None and recipe_id is None:
        raise HTTPException(400, "recipe_rev requires recipe_id")

    recipe = None
    version = None
    if recipe_id is not None:
        recipe = recipes.get_recipe(recipe_id)
        if not recipe:
            raise HTTPException(404, "recipe not found")
        version = recipes.get_version(recipe_id, recipe_rev) if recipe_rev is not None \
            else recipes.get_current(recipe_id)
        if not version:
            raise HTTPException(404, "recipe revision not found")
        # A recipe supplies all three elements; request-level overlap/wrap_style are ignored.
        ov = float(version["overlap"])
        style = version["wrap_style"]
        if recipe_rev is None and recipe.get("active") != 1:
            raise HTTPException(422, "recipe inactive")
        if save and not (recipe.get("active") == 1 and version["rev"] == recipe["current_rev"]):
            # Pinned old revisions may be dry-recomputed forever, but only the current
            # revision of an active recipe may be written to a new order.
            raise HTTPException(409, "can only save the current revision of an active recipe")
    else:
        ov = float(overlap) if overlap is not None else settings_repo.get_overlap()
        style = wrap_style

    calc = paper_area(box["length"], box["width"], box["height"], ov)
    ribbon = ribbon_estimate(box["length"], box["width"], box["height"], style)
    payload = {**calc, "ribbon": ribbon, "box_id": box_id}

    snap = {"wrap_style": style, "paper_m2": calc["paper_m2"], "ribbon_m": ribbon["ribbon_m"]}
    if recipe is not None:
        snap.update({
            "recipe_id": recipe["id"],
            "recipe_rev": version["rev"],
            "recipe_name": recipe["name"],
            "paper_id": version["paper_id"],
            "paper_name": version.get("paper_name"),
        })
        payload["recipe_id"] = recipe["id"]
        payload["recipe_rev"] = version["rev"]

    run_id = history.insert_run(box_id, ov, payload, note, snap) if save else None
    out = {"box": box, "run_id": run_id, **calc, "ribbon": ribbon}
    if recipe is not None:
        out["recipe"] = {"id": recipe["id"], "name": recipe["name"],
                         "rev": version["rev"], "active": recipe["active"]}
        out["paper"] = {"id": version["paper_id"], "name": version.get("paper_name")}
    return out
