from app.db import connect

def list_papers():
    c = connect()
    try:
        return [dict(r) for r in c.execute("SELECT * FROM papers ORDER BY id").fetchall()]
    finally:
        c.close()

def get_paper(pid):
    c = connect()
    try:
        r = c.execute("SELECT * FROM papers WHERE id=?", (pid,)).fetchone()
        return dict(r) if r else None
    finally:
        c.close()
