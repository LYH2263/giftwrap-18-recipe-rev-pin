import json
import pytest
from fastapi import HTTPException
from app.db import connect
from app.repositories import history, recipes
from app.schemas.recipe import RecipeCreate, RecipeVersionIn
from app.services import estimate_service, recipe_service

# Seed fixtures: box 1 = 书型盒 0.30x0.20x0.15 clean; papers 1 哑光纸1.0m / 2 牛皮纸0.7m.

def _make(overlap=1.15, wrap_style="cross", paper_id=1, name="标准配方"):
    return recipes.create_recipe(name, overlap, wrap_style, paper_id)

def _count_runs():
    c = connect()
    try:
        return c.execute("SELECT COUNT(*) n FROM calc_runs").fetchone()["n"]
    finally:
        c.close()

def test_create_recipe_starts_at_rev1(db):
    rid = _make()
    r = recipes.get_recipe(rid)
    assert r["current_rev"] == 1
    assert r["active"] == 1
    vs = recipes.list_versions(rid)
    assert len(vs) == 1
    assert vs[0]["rev"] == 1
    assert vs[0]["overlap"] == 1.15
    assert vs[0]["wrap_style"] == "cross"
    assert vs[0]["paper_id"] == 1
    assert vs[0]["paper_name"] == "哑光纸1.0m"

def test_add_version_appends_and_never_rewrites(db):
    # The storage tradeoff itself: no update API exists for version content.
    assert not hasattr(recipes, "update_version")
    rid = _make()
    v1_before = dict(recipes.get_version(rid, 1))

    new_rev = recipes.add_version(rid, 1.3, "band", 2)
    assert new_rev == 2

    v1_after = recipes.get_version(rid, 1)
    assert v1_after == v1_before  # old revision untouched
    rows = connect().execute(
        "SELECT rev, overlap, wrap_style, paper_id FROM recipe_versions WHERE recipe_id=? ORDER BY rev",
        (rid,),
    ).fetchall()
    assert [tuple(r) for r in rows] == [(1, 1.15, "cross", 1), (2, 1.3, "band", 2)]
    assert recipes.get_recipe(rid)["current_rev"] == 2

def test_preview_consumes_current_revision_and_does_not_persist(db):
    rid = _make()
    out = estimate_service.run_estimate(1, None, "cross", False, "", recipe_id=rid)
    assert out["recipe"] == {"id": rid, "rev": 1, "name": "标准配方"}
    assert out["overlap"] == 1.15
    assert out["ribbon"]["wrap_style"] == "cross"
    assert out["paper"] == {"id": 1, "name": "哑光纸1.0m"}
    assert out["run_id"] is None
    assert _count_runs() == 0

    recipes.add_version(rid, 1.3, "band", 2)
    out2 = estimate_service.run_estimate(1, None, "cross", False, "", recipe_id=rid)
    assert out2["recipe"]["rev"] == 2  # preview always eats current rev
    assert out2["overlap"] == 1.3
    assert out2["ribbon"]["wrap_style"] == "band"

def test_save_pins_rev_and_snapshots_values(db):
    rid = _make()
    out = estimate_service.run_estimate(1, None, "cross", True, "n", recipe_id=rid)
    run = history.get_run(out["run_id"])
    assert run["recipe_id"] == rid
    assert run["recipe_rev"] == 1
    assert run["paper_id"] == 1
    assert run["paper_name"] == "哑光纸1.0m"
    assert run["paper_m2"] == out["paper_m2"]
    assert run["ribbon_m"] == out["ribbon"]["ribbon_m"]
    assert run["wrap_style"] == "cross"
    assert run["overlap"] == 1.15
    assert run["recipe_name"] == "标准配方"

def test_post_bump_list_and_detail_keep_old_rev_and_values(db):
    rid = _make()
    out = estimate_service.run_estimate(1, None, "cross", True, "", recipe_id=rid)
    old_paper_m2, old_ribbon_m = out["paper_m2"], out["ribbon"]["ribbon_m"]
    recipes.add_version(rid, 1.3, "band", 2)

    detail = history.get_run(out["run_id"])
    listed = next(r for r in history.list_runs() if r["id"] == out["run_id"])
    keys = ("recipe_id", "recipe_rev", "paper_id", "paper_name", "paper_m2",
            "ribbon_m", "wrap_style", "overlap")
    for k in keys:  # list and detail read the same snapshot columns
        assert listed[k] == detail[k]
    assert detail["recipe_rev"] == 1
    assert detail["paper_m2"] == old_paper_m2
    assert detail["ribbon_m"] == old_ribbon_m
    assert detail["wrap_style"] == "cross"

def test_recalc_uses_pinned_rev_and_matches(db):
    rid = _make()
    out = estimate_service.run_estimate(1, None, "cross", True, "", recipe_id=rid)
    recipes.add_version(rid, 1.3, "band", 2)  # must not repaint the old run

    res = estimate_service.recalc_run(out["run_id"])
    assert res["matches"] is True
    assert res["stored"]["recipe_rev"] == 1
    assert res["recomputed"]["overlap"] == 1.15       # v1, not v2's 1.3
    assert res["recomputed"]["wrap_style"] == "cross"  # v1, not v2's band
    assert res["recomputed"]["paper_m2"] == out["paper_m2"]

def test_disabled_hidden_blocked_but_old_run_reviewable(db):
    rid = _make()
    out = estimate_service.run_estimate(1, None, "cross", True, "", recipe_id=rid)
    recipe_service.set_active(rid, False)

    assert all(x["id"] != rid for x in recipes.list_recipes(active_only=True))
    assert recipes.get_recipe(rid)["active"] == 0

    with pytest.raises(HTTPException) as ei:
        estimate_service.run_estimate(1, None, "cross", False, "", recipe_id=rid)
    assert ei.value.status_code == 409

    run = history.get_run(out["run_id"])  # old order still reviewable
    assert run["recipe_rev"] == 1
    assert estimate_service.recalc_run(out["run_id"])["matches"] is True

def test_manual_path_unchanged(db):
    out = estimate_service.run_estimate(1, None, "cross", True, "", recipe_id=None)
    assert out["recipe"] is None
    assert out["paper"] is None
    assert out["overlap"] == 1.15  # settings fallback
    run = history.get_run(out["run_id"])
    assert run["recipe_id"] is None
    assert run["recipe_rev"] is None
    assert estimate_service.recalc_run(out["run_id"])["matches"] is True

def test_validation_matrix(db):
    with pytest.raises(HTTPException) as ei:
        recipe_service.create_recipe(RecipeCreate(name="x", overlap=0, wrap_style="cross", paper_id=1))
    assert ei.value.status_code == 422
    with pytest.raises(HTTPException) as ei:
        recipe_service.create_recipe(RecipeCreate(name="x", overlap=1.1, wrap_style="spiral", paper_id=1))
    assert ei.value.status_code == 422
    with pytest.raises(HTTPException) as ei:
        recipe_service.create_recipe(RecipeCreate(name="x", overlap=1.1, wrap_style="cross", paper_id=999))
    assert ei.value.status_code == 422
    with pytest.raises(HTTPException) as ei:
        recipe_service.create_recipe(RecipeCreate(name=" ", overlap=1.1, wrap_style="cross", paper_id=1))
    assert ei.value.status_code == 422

    body = RecipeVersionIn(overlap=1.2, wrap_style="band", paper_id=2)
    with pytest.raises(HTTPException) as ei:
        recipe_service.add_version(999, body)
    assert ei.value.status_code == 404
    with pytest.raises(HTTPException) as ei:
        recipe_service.set_active(999, True)
    assert ei.value.status_code == 404
    with pytest.raises(HTTPException) as ei:
        estimate_service.run_estimate(1, None, "cross", False, "", recipe_id=999)
    assert ei.value.status_code == 404
    with pytest.raises(HTTPException) as ei:
        estimate_service.recalc_run(999)
    assert ei.value.status_code == 404

def test_migration_idempotent_and_legacy_run_fallback(db):
    seed = __import__("app.seed", fromlist=["init_db"])
    seed.init_db()  # ALTER guard must be a safe no-op on the second call

    c = connect()
    legacy_payload = {"paper_m2": 0.31, "ribbon": {"wrap_style": "band", "ribbon_m": 1.0}, "box_id": 1}
    cur = c.execute(
        "INSERT INTO calc_runs(box_id,overlap,result_json,note,created_at) VALUES (?,?,?,?,?)",
        (1, 1.15, json.dumps(legacy_payload), "legacy", "2026-01-01T00:00:00+00:00"),
    )
    c.commit()
    lid = cur.lastrowid
    c.close()

    detail = history.get_run(lid)  # snapshot columns NULL -> fall back to result_json
    assert detail["paper_m2"] == 0.31
    assert detail["ribbon_m"] == 1.0
    assert detail["wrap_style"] == "band"
    assert any(r["id"] == lid for r in history.list_runs())
    assert estimate_service.recalc_run(lid)["matches"] is True
