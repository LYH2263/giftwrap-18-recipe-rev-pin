import json
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.db import connect
from app.engines.wrap_math import paper_area, ribbon_estimate
from app.repositories import history, recipes
from app.services import estimate_service

pytestmark = pytest.mark.usefixtures("temp_db")

# Seeded fixture: box 1 = 书型盒 0.30 x 0.20 x 0.15; papers 1/2 exist.
BOX = (1, 0.30, 0.20, 0.15)
FROZEN_KEYS = ("recipe_id", "recipe_rev", "recipe_name", "paper_id", "paper_name",
               "overlap", "wrap_style", "paper_m2", "ribbon_m")


def test_recipe_run_lifecycle_snapshot_and_recrosscheck():
    rid = recipes.create_recipe("标准十字包装", 1.15, "cross", 1)["id"]

    # 1. Save at rev1 — row pins recipe/rev and the at-that-time computed values.
    out = estimate_service.run_estimate(BOX[0], None, "cross", True, "首单", recipe_id=rid)
    run_id = out["run_id"]
    assert out["recipe"] == {"id": rid, "name": "标准十字包装", "rev": 1, "active": 1}
    assert out["paper"]["id"] == 1
    expect_m2 = paper_area(BOX[1], BOX[2], BOX[3], 1.15)["paper_m2"]
    expect_ribbon = ribbon_estimate(BOX[1], BOX[2], BOX[3], "cross")["ribbon_m"]

    detail = history.get_run(run_id)
    assert detail["recipe_id"] == rid
    assert detail["recipe_rev"] == 1
    assert detail["recipe_name"] == "标准十字包装"
    assert detail["paper_id"] == 1
    assert detail["paper_name"] == "哑光纸1.0m"
    assert detail["wrap_style"] == "cross"
    assert detail["paper_m2"] == expect_m2
    assert detail["ribbon_m"] == expect_ribbon

    # 2. Recipe is edited (rev2: band, more overlap) and then deactivated.
    recipes.add_revision(rid, 1.3, "band", 2)
    recipes.set_active(rid, False)

    # 3. Old order keeps the old rev/values in BOTH list and detail — mutually consistent,
    #    never brushed back by rev2 (current is 2/band/1.3 now).
    current = recipes.get_current(rid)
    assert (current["current_rev"], current["wrap_style"], current["overlap"]) == (2, "band", 1.3)
    listed = {r["id"]: r for r in history.list_runs()}
    for key in FROZEN_KEYS:
        assert listed[run_id][key] == detail[key], key
    d = history.get_run(run_id)
    assert d["recipe_rev"] == 1
    assert d["wrap_style"] == "cross"
    assert d["paper_id"] == 1
    assert d["paper_m2"] == expect_m2
    assert d["ribbon_m"] == expect_ribbon

    # 4. Re-dry-computing with the pinned old rev must match the stored view, and a pure
    #    engine recompute from the snapshot must agree too — even while deactivated.
    re = estimate_service.run_estimate(BOX[0], None, "cross", False, "",
                                       recipe_id=rid, recipe_rev=1)
    assert re["paper_m2"] == d["paper_m2"]
    assert re["ribbon"]["ribbon_m"] == d["ribbon_m"]
    assert paper_area(BOX[1], BOX[2], BOX[3], d["overlap"])["paper_m2"] == d["paper_m2"]
    assert ribbon_estimate(BOX[1], BOX[2], BOX[3], d["wrap_style"])["ribbon_m"] == d["ribbon_m"]


def test_save_gates_and_inactive_rules():
    rid = recipes.create_recipe("标准十字包装", 1.15, "cross", 1)["id"]

    # rev-without-recipe is a 400 regardless of save.
    with pytest.raises(HTTPException) as ei:
        estimate_service.run_estimate(BOX[0], None, "cross", False, "", recipe_rev=1)
    assert ei.value.status_code == 400

    # While active, a non-current revision can only be dry-run: saving it is 409.
    recipes.add_revision(rid, 1.3, "band", 2)
    with pytest.raises(HTTPException) as ei:
        estimate_service.run_estimate(BOX[0], None, "cross", True, "",
                                      recipe_id=rid, recipe_rev=1)
    assert ei.value.status_code == 409
    # ...but dry recompute of the old rev is fine.
    old = estimate_service.run_estimate(BOX[0], None, "cross", False, "",
                                        recipe_id=rid, recipe_rev=1)
    assert old["recipe"]["rev"] == 1

    recipes.set_active(rid, False)
    # New previews may not select a deactivated recipe (no pinned rev) -> 422.
    with pytest.raises(HTTPException) as ei:
        estimate_service.run_estimate(BOX[0], None, "cross", False, "", recipe_id=rid)
    assert ei.value.status_code == 422
    # Saving under a deactivated recipe is 409.
    with pytest.raises(HTTPException) as ei:
        estimate_service.run_estimate(BOX[0], None, "cross", True, "",
                                      recipe_id=rid, recipe_rev=2)
    assert ei.value.status_code == 409

    # Missing recipe/revision are 404.
    with pytest.raises(HTTPException) as ei:
        estimate_service.run_estimate(BOX[0], None, "cross", False, "", recipe_id=999)
    assert ei.value.status_code == 404
    with pytest.raises(HTTPException) as ei:
        estimate_service.run_estimate(BOX[0], None, "cross", False, "",
                                      recipe_id=rid, recipe_rev=99)
    assert ei.value.status_code == 404


def test_recipe_wrap_style_takes_effect():
    rid = recipes.create_recipe("缎带包装", 1.15, "cross", 1)["id"]
    cross = estimate_service.run_estimate(BOX[0], None, "cross", False, "", recipe_id=rid)
    assert cross["ribbon"]["wrap_style"] == "cross"

    recipes.add_revision(rid, 1.3, "band", 1)
    band = estimate_service.run_estimate(BOX[0], None, "cross", False, "", recipe_id=rid)
    assert band["ribbon"]["wrap_style"] == "band"
    assert band["ribbon"]["ribbon_m"] != cross["ribbon"]["ribbon_m"]
    assert band["paper_m2"] == paper_area(BOX[1], BOX[2], BOX[3], 1.3)["paper_m2"]


def test_legacy_path_unchanged_and_old_rows_fallback():
    # Response shape is byte-for-byte the old six keys without a recipe.
    dry = estimate_service.run_estimate(BOX[0], None, "cross", False, "")
    assert set(dry.keys()) == {"box", "run_id", "box_surface", "overlap", "paper_m2", "ribbon"}

    # Legacy-path saves populate the numeric snapshot columns but no recipe columns.
    run_id = estimate_service.run_estimate(BOX[0], None, "band", True, "无配方")["run_id"]
    row = history.get_run(run_id)
    assert row["recipe_id"] is None and row["recipe_rev"] is None
    assert row["wrap_style"] == "band"
    assert row["paper_m2"] is not None and row["ribbon_m"] is not None

    # A pre-feature row (all snapshot columns NULL) renders via result_json fallback.
    payload = {"box_surface": 0.27, "overlap": 1.15, "paper_m2": 0.31,
               "ribbon": {"wrap_style": "cross", "ribbon_m": 2.2}, "box_id": BOX[0]}
    c = connect()
    cur = c.execute(
        "INSERT INTO calc_runs(box_id,overlap,result_json,note,created_at) VALUES (?,?,?,?,?)",
        (BOX[0], 1.15, json.dumps(payload), "老单", datetime.now(timezone.utc).isoformat()),
    )
    c.commit()
    old_id = int(cur.lastrowid)
    c.close()
    old = history.get_run(old_id)
    assert old["recipe_id"] is None
    assert old["paper_m2"] == 0.31
    assert old["ribbon_m"] == 2.2
    assert old["wrap_style"] == "cross"
    # Same projection through the list view.
    assert {r["id"]: r for r in history.list_runs()}[old_id]["paper_m2"] == 0.31
