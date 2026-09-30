from datetime import datetime, timezone

from app.db import connect

_CURRENT_JOIN = """
    SELECT r.*, v.rev, v.overlap, v.wrap_style, v.paper_id, v.created_at, p.name paper_name
    FROM recipes r
    JOIN recipe_versions v ON v.recipe_id = r.id AND v.rev = r.current_rev
    LEFT JOIN papers p ON p.id = v.paper_id
"""

_VERSION_JOIN = """
    SELECT v.*, p.name paper_name
    FROM recipe_versions v
    LEFT JOIN papers p ON p.id = v.paper_id
"""


def list_recipes(active_only: bool = False):
    sql = _CURRENT_JOIN + (" WHERE r.active = 1" if active_only else "") + " ORDER BY r.id"
    c = connect()
    try:
        return [dict(r) for r in c.execute(sql).fetchall()]
    finally:
        c.close()

def get_recipe(rid):
    c = connect()
    try:
        r = c.execute("SELECT * FROM recipes WHERE id=?", (rid,)).fetchone()
        return dict(r) if r else None
    finally:
        c.close()

def get_current(rid):
    c = connect()
    try:
        r = c.execute(_CURRENT_JOIN + " WHERE r.id=?", (rid,)).fetchone()
        return dict(r) if r else None
    finally:
        c.close()

def get_version(rid, rev):
    c = connect()
    try:
        r = c.execute(
            _VERSION_JOIN + " WHERE v.recipe_id=? AND v.rev=?", (rid, rev)
        ).fetchone()
        return dict(r) if r else None
    finally:
        c.close()

def list_versions(rid):
    c = connect()
    try:
        return [dict(r) for r in c.execute(
            _VERSION_JOIN + " WHERE v.recipe_id=? ORDER BY v.rev", (rid,)
        ).fetchall()]
    finally:
        c.close()

def create_recipe(name, overlap, wrap_style, paper_id):
    # Append-only from the very first row: master rev 1 + version 1 in one transaction.
    c = connect()
    try:
        now = datetime.now(timezone.utc).isoformat()
        cur = c.execute("INSERT INTO recipes(name,active,current_rev) VALUES (?,?,?)",
                        (name, 1, 1))
        rid = int(cur.lastrowid)
        c.execute(
            "INSERT INTO recipe_versions(recipe_id,rev,overlap,wrap_style,paper_id,created_at) VALUES (?,?,?,?,?,?)",
            (rid, 1, float(overlap), wrap_style, paper_id, now),
        )
        c.commit()
    finally:
        c.close()
    return get_current(rid)

def add_revision(rid, overlap, wrap_style, paper_id):
    # Editing a recipe appends a new version and bumps current_rev; recipe_versions
    # rows are never UPDATE'd (a racing duplicate rev fails on the PK instead).
    c = connect()
    try:
        now = datetime.now(timezone.utc).isoformat()
        row = c.execute(
            "SELECT COALESCE(MAX(rev),0) + 1 next_rev FROM recipe_versions WHERE recipe_id=?",
            (rid,),
        ).fetchone()
        rev = int(row["next_rev"])
        c.execute(
            "INSERT INTO recipe_versions(recipe_id,rev,overlap,wrap_style,paper_id,created_at) VALUES (?,?,?,?,?,?)",
            (rid, rev, float(overlap), wrap_style, paper_id, now),
        )
        c.execute("UPDATE recipes SET current_rev=? WHERE id=?", (rev, rid))
        c.commit()
    finally:
        c.close()
    return get_current(rid)

def set_active(rid, active: bool):
    c = connect()
    try:
        cur = c.execute("UPDATE recipes SET active=? WHERE id=?", (1 if active else 0, rid))
        c.commit()
        return cur.rowcount == 1
    finally:
        c.close()
