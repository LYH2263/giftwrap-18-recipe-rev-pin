from datetime import datetime, timezone

from app.db import connect

def init_db():
    c = connect()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS boxes(id INTEGER PRIMARY KEY,name TEXT,length REAL,width REAL,height REAL,data_quality TEXT,note TEXT);
    CREATE TABLE IF NOT EXISTS papers(id INTEGER PRIMARY KEY,name TEXT,roll_width REAL,data_quality TEXT,note TEXT);
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
    CREATE TABLE IF NOT EXISTS calc_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,box_id INT,overlap REAL,result_json TEXT,note TEXT,created_at TEXT);
    CREATE TABLE IF NOT EXISTS recipes(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,current_rev INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS recipe_versions(recipe_id INTEGER NOT NULL,rev INTEGER NOT NULL,overlap REAL NOT NULL,wrap_style TEXT NOT NULL,paper_id INTEGER NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(recipe_id,rev));
    """)
    # Idempotent migration: snapshot columns pinned on each calc run. Historical
    # values are read from these columns only — never joined back to recipe_versions.
    cols = {r["name"] for r in c.execute("PRAGMA table_info(calc_runs)").fetchall()}
    for name, ddl in [
        ("recipe_id", "ALTER TABLE calc_runs ADD COLUMN recipe_id INT"),
        ("recipe_rev", "ALTER TABLE calc_runs ADD COLUMN recipe_rev INT"),
        ("recipe_name", "ALTER TABLE calc_runs ADD COLUMN recipe_name TEXT"),
        ("paper_id", "ALTER TABLE calc_runs ADD COLUMN paper_id INT"),
        ("paper_name", "ALTER TABLE calc_runs ADD COLUMN paper_name TEXT"),
        ("wrap_style", "ALTER TABLE calc_runs ADD COLUMN wrap_style TEXT"),
        ("paper_m2", "ALTER TABLE calc_runs ADD COLUMN paper_m2 REAL"),
        ("ribbon_m", "ALTER TABLE calc_runs ADD COLUMN ribbon_m REAL"),
    ]:
        if name not in cols:
            c.execute(ddl)
    if c.execute("SELECT COUNT(*) c FROM boxes").fetchone()["c"] == 0:
        c.executemany("INSERT INTO boxes(name,length,width,height,data_quality,note) VALUES (?,?,?,?,?,?)",[
            ("书型盒",0.30,0.20,0.15,"clean",""),
            ("方形礼盒",0.25,0.25,0.10,"clean",""),
            ("脏数据-负高",0.2,0.2,-0.1,"dirty","高度负"),
        ])
        c.executemany("INSERT INTO papers(name,roll_width,data_quality,note) VALUES (?,?,?,?)",[
            ("哑光纸1.0m",1.0,"clean",""),
            ("牛皮纸0.7m",0.7,"clean",""),
        ])
        c.execute("INSERT INTO settings(key,value) VALUES ('overlap','1.15')")
        c.commit()
    # Sample recipe, seeded independently of the boxes guard so pre-existing DBs get it too.
    if c.execute("SELECT COUNT(*) c FROM recipes").fetchone()["c"] == 0:
        now = datetime.now(timezone.utc).isoformat()
        cur = c.execute("INSERT INTO recipes(name,active,current_rev) VALUES (?,?,?)",
                        ("标准十字包装", 1, 1))
        rid = int(cur.lastrowid)
        c.execute(
            "INSERT INTO recipe_versions(recipe_id,rev,overlap,wrap_style,paper_id,created_at) VALUES (?,?,?,?,?,?)",
            (rid, 1, 1.15, "cross", 1, now),
        )
        c.commit()
    c.close()
