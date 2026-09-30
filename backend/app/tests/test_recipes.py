import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.db import connect
from app.repositories import recipes
from app.routers import recipes as recipes_router
from app.schemas.recipe import RecipeCreate, RevisionCreate

pytestmark = pytest.mark.usefixtures("temp_db")


def _create(name="测试配方", overlap=1.15, wrap_style="cross", paper_id=1):
    return recipes.create_recipe(name, overlap, wrap_style, paper_id)


def test_revision_starts_at_one_and_is_append_only():
    r = _create()
    rid = r["id"]
    assert recipes.get_recipe(rid)["current_rev"] == 1

    # Freeze the rev1 row before editing.
    rev1_before = dict(recipes.get_version(rid, 1))
    raw_before = connect().execute(
        "SELECT overlap,wrap_style,paper_id,created_at FROM recipe_versions WHERE recipe_id=? AND rev=1",
        (rid,),
    ).fetchone()
    raw_before = tuple(raw_before)

    bumped = recipes.add_revision(rid, 1.3, "band", 2)

    assert bumped["rev"] == 2
    assert bumped["current_rev"] == 2
    assert [v["rev"] for v in recipes.list_versions(rid)] == [1, 2]
    # Historical version content must be byte-identical — never overwritten in place.
    assert dict(recipes.get_version(rid, 1)) == rev1_before
    raw_after = connect().execute(
        "SELECT overlap,wrap_style,paper_id,created_at FROM recipe_versions WHERE recipe_id=? AND rev=1",
        (rid,),
    ).fetchone()
    assert tuple(raw_after) == raw_before
    # Edit = append: exactly two version rows exist, rev2 carries the new three elements.
    count = connect().execute(
        "SELECT COUNT(*) c FROM recipe_versions WHERE recipe_id=?", (rid,)
    ).fetchone()["c"]
    assert count == 2
    rev2 = recipes.get_version(rid, 2)
    assert (rev2["overlap"], rev2["wrap_style"], rev2["paper_id"]) == (1.3, "band", 2)


def test_schema_validation():
    with pytest.raises(ValidationError):
        RecipeCreate(name="x", overlap=0, wrap_style="cross", paper_id=1)
    with pytest.raises(ValidationError):
        RecipeCreate(name="x", overlap=1.1, wrap_style="bow", paper_id=1)
    with pytest.raises(ValidationError):
        RecipeCreate(name="", overlap=1.1, wrap_style="cross", paper_id=1)
    with pytest.raises(ValidationError):
        RevisionCreate(overlap=1.1, wrap_style="band", paper_id="not-an-int")


def test_missing_paper_recipe_and_revision_404():
    body = RecipeCreate(name="x", overlap=1.1, wrap_style="cross", paper_id=999)
    with pytest.raises(HTTPException) as ei:
        recipes_router.create_recipe(body)
    assert ei.value.status_code == 404

    with pytest.raises(HTTPException) as ei:
        recipes_router.add_revision(999, RevisionCreate(overlap=1.1, wrap_style="cross", paper_id=1))
    assert ei.value.status_code == 404

    r = _create()
    with pytest.raises(HTTPException) as ei:
        recipes_router.get_revision(r["id"], 99)
    assert ei.value.status_code == 404


def test_deactivate_reactivate_lifecycle():
    r = _create()
    rid = r["id"]
    assert any(x["id"] == rid for x in recipes.list_recipes(active_only=True))

    recipes.set_active(rid, False)
    assert not any(x["id"] == rid for x in recipes.list_recipes(active_only=True))
    # Still visible in the admin list.
    assert any(x["id"] == rid for x in recipes.list_recipes())

    # Frozen while deactivated: no new revision may be appended.
    with pytest.raises(HTTPException) as ei:
        recipes_router.add_revision(
            rid, RevisionCreate(overlap=1.2, wrap_style="cross", paper_id=1))
    assert ei.value.status_code == 409

    # Idempotent deactivate, then reactivate restores both selection and revisioning.
    recipes_router.deactivate(rid)
    recipes_router.activate(rid)
    assert any(x["id"] == rid for x in recipes.list_recipes(active_only=True))
    bumped = recipes_router.add_revision(
        rid, RevisionCreate(overlap=1.2, wrap_style="cross", paper_id=1))
    assert bumped["current_rev"] == 2


def test_current_revision_agreement_between_endpoints():
    r = _create(overlap=1.2, wrap_style="band", paper_id=2)
    rid = r["id"]
    admin = {x["id"]: x for x in recipes.list_recipes()}
    active = {x["id"]: x for x in recipes.list_recipes(active_only=True)}
    for key in ("current_rev", "overlap", "wrap_style", "paper_id"):
        assert admin[rid][key] == active[rid][key]

    recipes.add_revision(rid, 1.3, "cross", 1)
    admin = {x["id"]: x for x in recipes.list_recipes()}
    active = {x["id"]: x for x in recipes.list_recipes(active_only=True)}
    assert admin[rid]["current_rev"] == active[rid]["current_rev"] == 2
    assert admin[rid]["overlap"] == active[rid]["overlap"] == 1.3
    assert active[rid]["wrap_style"] == "cross"


def test_recipe_routes_registered():
    from app.main import app
    paths = {r.path for r in app.routes}
    assert "/api/recipes" in paths
    assert "/api/recipes/{rid}" in paths
    assert "/api/recipes/{rid}/revisions/{rev}" in paths
    assert "/api/runs/{run_id}" in paths
