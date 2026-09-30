import json
from datetime import datetime, timezone
from app.db import connect

_SNAP_COLS = ("recipe_id", "recipe_rev", "recipe_name", "paper_id", "paper_name",
              "wrap_style", "paper_m2", "ribbon_m")


def insert_run(box_id, overlap, result, note="", snap=None):
    snap = snap or {}
    values = [snap.get(k) for k in _SNAP_COLS]
    c = connect()
    try:
        cur = c.execute(
            """INSERT INTO calc_runs(box_id,overlap,result_json,note,created_at,
                   recipe_id,recipe_rev,recipe_name,paper_id,paper_name,wrap_style,paper_m2,ribbon_m)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (box_id, overlap, json.dumps(result, ensure_ascii=False), note,
             datetime.now(timezone.utc).isoformat(), *values),
        )
        c.commit()
        return int(cur.lastrowid)
    finally:
        c.close()

def _serialize(row):
    # List and detail share this exact projection, so the two views can never diverge.
    # Snapshot columns are the source of truth; pre-feature rows fall back to result_json.
    d = dict(row)
    result = json.loads(d.pop("result_json"))
    d["result"] = result
    ribbon = result.get("ribbon") or {}
    if d.get("paper_m2") is None:
        d["paper_m2"] = result.get("paper_m2")
    if d.get("ribbon_m") is None:
        d["ribbon_m"] = ribbon.get("ribbon_m")
    if d.get("wrap_style") is None:
        d["wrap_style"] = ribbon.get("wrap_style")
    return d

def _fetch(sql, args=()):
    c = connect()
    try:
        return c.execute(sql, args).fetchall()
    finally:
        c.close()

def list_runs(limit=50):
    rows = _fetch(
        """SELECT r.*, b.name box_name FROM calc_runs r
           LEFT JOIN boxes b ON b.id=r.box_id ORDER BY r.id DESC LIMIT ?""",
        (limit,),
    )
    return [_serialize(r) for r in rows]

def get_run(run_id):
    rows = _fetch(
        """SELECT r.*, b.name box_name FROM calc_runs r
           LEFT JOIN boxes b ON b.id=r.box_id WHERE r.id=?""",
        (run_id,),
    )
    return _serialize(rows[0]) if rows else None
