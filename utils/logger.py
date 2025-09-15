import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "events.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 嘗試創建新表格
    c.execute("""
    CREATE TABLE IF NOT EXISTS drug_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event TEXT,
        note TEXT,
        ts TEXT,
        extra TEXT
    )
    """)

    # 檢查舊表欄位
    c.execute("PRAGMA table_info(drug_log)")
    columns = [row[1] for row in c.fetchall()]

    if "event" not in columns:
        print("[log] 更新表結構：將舊欄位 drug 轉成 event")
        # 建新表
        c.execute("""
        CREATE TABLE IF NOT EXISTS drug_log_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event TEXT,
            note TEXT,
            ts TEXT,
            extra TEXT
        )
        """)
        # 搬資料
        if "drug" in columns:
            c.execute("INSERT INTO drug_log_new (id, event, note, ts, extra) "
                      "SELECT id, drug, note, ts, '' FROM drug_log")
        # 刪掉舊表，改名新表
        c.execute("DROP TABLE drug_log")
        c.execute("ALTER TABLE drug_log_new RENAME TO drug_log")

    conn.commit()
    conn.close()
    print("[log] 資料庫初始化完成")

def log_event(event, note="", ts=None, extra=None):
    ts = ts or datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO drug_log (event, note, ts, extra) VALUES (?,?,?,?)",
        (event, note, ts, json.dumps(extra) if extra else "")
    )
    conn.commit()
    conn.close()

def list_logs(limit=50):
    """列出最近的急救紀錄"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT id, event, note, ts, extra FROM drug_log ORDER BY id DESC LIMIT ?", 
        (limit,)
    )
    rows = c.fetchall()
    conn.close()
    return rows

def clear_logs():
    """清除所有急救紀錄"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM drug_log")
    conn.commit()
    conn.close()
    print("[log] 已清除所有紀錄")
