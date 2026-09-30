from datetime import datetime, timezone
from app.db import connect

_CURRENT_SQL = """
SELECT r.id, r.name, r.active, r.note,
       v.rev AS current_rev, v.overlap, v.wrap_style, v.paper_id,
       p.name AS paper_name
FROM recipes r
JOIN recipe_versions v
  ON v.recipe_id = r.id
 AND v.rev = (SELECT MAX(rev) FROM recipe_versions WHERE recipe_id = r.id)
LEFT JOIN papers p ON p.id = v.paper_id
"""

_VERSION_SQL = """
SELECT v.recipe_id, v.rev, v.overlap, v.wrap_style, v.paper_id, v.note, v.created_at,
       p.name AS paper_name
FROM recipe_versions v
LEFT JOIN papers p ON p.id = v.paper_id
"""

def _now():
    return datetime.now(timezone.utc).isoformat()

def create_recipe(name, overlap, wrap_style, paper_id, note=""):
    c = connect()
    try:
        cur = c.execute(
            "INSERT INTO recipes(name,active,note,created_at) VALUES (?,1,?,?)",
            (name, note, _now()),
        )
        rid = int(cur.lastrowid)
        c.execute(
            "INSERT INTO recipe_versions(recipe_id,rev,overlap,wrap_style,paper_id,note,created_at) VALUES (?,1,?,?,?,?,?)",
            (rid, float(overlap), wrap_style, int(paper_id), note, _now()),
        )
        c.commit()
        return rid
    finally:
        c.close()

def add_version(recipe_id, overlap, wrap_style, paper_id, note=""):
    """Append max(rev)+1. Returns new rev, or None if the recipe master does not exist.
    Historical version rows are never touched."""
    c = connect()
    try:
        row = c.execute("SELECT MAX(rev) m FROM recipe_versions WHERE recipe_id=?", (recipe_id,)).fetchone()
        exists = c.execute("SELECT 1 FROM recipes WHERE id=?", (recipe_id,)).fetchone()
        if not exists:
            return None
        new_rev = (row["m"] or 0) + 1
        c.execute(
            "INSERT INTO recipe_versions(recipe_id,rev,overlap,wrap_style,paper_id,note,created_at) VALUES (?,?,?,?,?,?,?)",
            (recipe_id, new_rev, float(overlap), wrap_style, int(paper_id), note, _now()),
        )
        c.commit()
        return int(new_rev)
    finally:
        c.close()

def set_active(recipe_id, active):
    c = connect()
    try:
        c.execute("UPDATE recipes SET active=? WHERE id=?", (1 if active else 0, recipe_id))
        c.commit()
    finally:
        c.close()

def list_recipes(active_only=False):
    c = connect()
    try:
        sql = _CURRENT_SQL + ("WHERE r.active = 1 " if active_only else "") + "ORDER BY r.id"
        return [dict(r) for r in c.execute(sql).fetchall()]
    finally:
        c.close()

def get_recipe(recipe_id):
    c = connect()
    try:
        row = c.execute(_CURRENT_SQL + "WHERE r.id=?", (recipe_id,)).fetchone()
        return dict(row) if row else None
    finally:
        c.close()

def get_version(recipe_id, rev):
    c = connect()
    try:
        row = c.execute(
            _VERSION_SQL + "WHERE v.recipe_id=? AND v.rev=?",
            (recipe_id, rev),
        ).fetchone()
        return dict(row) if row else None
    finally:
        c.close()

def list_versions(recipe_id):
    c = connect()
    try:
        rows = c.execute(
            _VERSION_SQL + "WHERE v.recipe_id=? ORDER BY v.rev",
            (recipe_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        c.close()
