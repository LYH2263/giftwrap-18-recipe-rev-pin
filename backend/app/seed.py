from app.db import connect

_RUN_COLUMNS = (
    ("recipe_id", "INTEGER"),
    ("recipe_rev", "INTEGER"),
    ("paper_id", "INTEGER"),
    ("paper_name", "TEXT"),
    ("paper_m2", "REAL"),
    ("ribbon_m", "REAL"),
    ("wrap_style", "TEXT"),
)

def _migrate(c):
    have = {r["name"] for r in c.execute("PRAGMA table_info(calc_runs)").fetchall()}
    for name, coltype in _RUN_COLUMNS:
        if name not in have:
            c.execute(f"ALTER TABLE calc_runs ADD COLUMN {name} {coltype}")
    c.commit()

def init_db():
    c = connect()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS boxes(id INTEGER PRIMARY KEY,name TEXT,length REAL,width REAL,height REAL,data_quality TEXT,note TEXT);
    CREATE TABLE IF NOT EXISTS papers(id INTEGER PRIMARY KEY,name TEXT,roll_width REAL,data_quality TEXT,note TEXT);
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
    CREATE TABLE IF NOT EXISTS calc_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,box_id INT,overlap REAL,result_json TEXT,note TEXT,created_at TEXT);
    CREATE TABLE IF NOT EXISTS recipes(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,note TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS recipe_versions(recipe_id INTEGER NOT NULL,rev INTEGER NOT NULL,overlap REAL NOT NULL,wrap_style TEXT NOT NULL,paper_id INTEGER NOT NULL,note TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,PRIMARY KEY (recipe_id,rev),CHECK (overlap > 0),CHECK (wrap_style IN ('cross','band')));
    """)
    _migrate(c)
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
    c.close()
