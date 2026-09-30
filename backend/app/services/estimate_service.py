import math
from fastapi import HTTPException
from app.engines.wrap_math import paper_area, ribbon_estimate
from app.repositories import boxes, history, papers, recipes, settings_repo

def run_estimate(box_id: int, overlap: float | None, wrap_style: str, save: bool, note: str,
                 recipe_id: int | None = None):
    box = boxes.get_box(box_id)
    if not box:
        raise HTTPException(404)
    if box.get("data_quality") == "dirty":
        raise HTTPException(422, "dirty box")

    recipe_badge = None
    paper = None
    if recipe_id is not None:
        r = recipes.get_recipe(recipe_id)
        if not r:
            raise HTTPException(404, "recipe not found")
        if not r["active"]:
            raise HTTPException(409, "recipe inactive")
        # Recipe's current revision wins; request overlap/wrap_style are ignored.
        overlap = r["overlap"]
        wrap_style = r["wrap_style"]
        paper = papers.get_paper(r["paper_id"])
        recipe_badge = {"id": r["id"], "rev": r["current_rev"], "name": r["name"]}
    else:
        overlap = float(overlap) if overlap is not None else settings_repo.get_overlap()

    calc = paper_area(box["length"], box["width"], box["height"], overlap)
    ribbon = ribbon_estimate(box["length"], box["width"], box["height"], wrap_style)
    payload = {**calc, "ribbon": ribbon, "box_id": box_id}

    pin = None
    if recipe_id is not None:
        pin = {
            "recipe_id": recipe_badge["id"],
            "recipe_rev": recipe_badge["rev"],
            "paper_id": r["paper_id"],
            "paper_name": paper["name"] if paper else None,
            "paper_m2": calc["paper_m2"],
            "ribbon_m": ribbon["ribbon_m"],
            "wrap_style": wrap_style,
        }
    run_id = history.insert_run(box_id, overlap, payload, note, pin) if save else None
    return {
        "box": box, "run_id": run_id, **calc, "ribbon": ribbon,
        "recipe": recipe_badge,
        "paper": {"id": paper["id"], "name": paper["name"]} if paper else None,
    }

def recalc_run(run_id: int):
    """Re-run an old order with its PINNED recipe revision against the current box,
    and cross-check the recomputed numbers against the stored snapshot."""
    run = history.get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")

    stored = {
        "paper_m2": run["paper_m2"],
        "ribbon_m": run["ribbon_m"],
        "overlap": run["overlap"],
        "wrap_style": run["wrap_style"],
        "recipe_id": run["recipe_id"],
        "recipe_rev": run["recipe_rev"],
    }

    ov, style = run["overlap"], (run["wrap_style"] or "cross")
    if run["recipe_id"] is not None:
        v = recipes.get_version(run["recipe_id"], run["recipe_rev"])
        if not v:
            raise HTTPException(409, "pinned recipe revision missing")
        ov, style = v["overlap"], v["wrap_style"]

    box = boxes.get_box(run["box_id"])
    if not box:
        raise HTTPException(404, "box missing")

    try:
        calc = paper_area(box["length"], box["width"], box["height"], ov)
        ribbon = ribbon_estimate(box["length"], box["width"], box["height"], style)
    except ValueError:
        return {"run_id": run_id, "stored": stored, "recomputed": None,
                "matches": False, "reason": "box dimensions invalid"}

    recomputed = {
        "paper_m2": calc["paper_m2"],
        "ribbon_m": ribbon["ribbon_m"],
        "overlap": calc["overlap"],
        "wrap_style": ribbon["wrap_style"],
    }
    matches = (
        stored["paper_m2"] is not None
        and math.isclose(stored["paper_m2"], recomputed["paper_m2"], abs_tol=0.001)
        and stored["ribbon_m"] is not None
        and math.isclose(stored["ribbon_m"], recomputed["ribbon_m"], abs_tol=0.01)
    )
    return {"run_id": run_id, "stored": stored, "recomputed": recomputed,
            "matches": bool(matches), "reason": None}
