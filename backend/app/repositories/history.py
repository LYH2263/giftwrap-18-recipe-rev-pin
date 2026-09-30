import json
from datetime import datetime, timezone
from app.db import connect

def insert_run(box_id, overlap, result, note="", pin=None):
    pin = pin or {}
    c = connect()
    try:
        cur = c.execute(
            """INSERT INTO calc_runs(
                box_id, overlap, result_json, note, created_at,
                recipe_id, recipe_rev, paper_id, paper_name, paper_m2, ribbon_m, wrap_style
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                box_id, overlap, json.dumps(result, ensure_ascii=False), note,
                datetime.now(timezone.utc).isoformat(),
                pin.get("recipe_id"), pin.get("recipe_rev"), pin.get("paper_id"),
                pin.get("paper_name"), pin.get("paper_m2"), pin.get("ribbon_m"),
                pin.get("wrap_style"),
            ),
        )
        c.commit()
        return int(cur.lastrowid)
    finally:
        c.close()

_SELECT = """
SELECT r.*, b.name box_name, rc.name recipe_name
FROM calc_runs r
LEFT JOIN boxes b ON b.id = r.box_id
LEFT JOIN recipes rc ON rc.id = r.recipe_id
"""

def _row_to_dict(row):
    """Single normalization shared by list and detail so the two can never disagree.
    New snapshot columns win; legacy rows fall back to result_json."""
    d = dict(row)
    result = json.loads(d.pop("result_json") or "{}")
    d["result"] = result
    ribbon = result.get("ribbon") or {}
    if d.get("paper_m2") is None:
        d["paper_m2"] = result.get("paper_m2")
    if d.get("ribbon_m") is None:
        d["ribbon_m"] = ribbon.get("ribbon_m")
    if not d.get("wrap_style"):
        d["wrap_style"] = ribbon.get("wrap_style")
    return d

def list_runs(limit=50):
    c = connect()
    try:
        rows = c.execute(
            _SELECT + "ORDER BY r.id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        c.close()

def get_run(run_id):
    c = connect()
    try:
        row = c.execute(_SELECT + "WHERE r.id=?", (run_id,)).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        c.close()
