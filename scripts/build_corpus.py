#!/usr/bin/env python3
"""从条文 JSONL 构建 data/laws.db。

用法：
    python scripts/build_corpus.py 宪法法律_条文.jsonl

语料 JSONL 每行至少包含：
    law_id, law_name, article_no, article_text
可选字段（有则更完整）：
    doc_type, level, issuing_body, publish_date, effective_date, version_date,
    status, chapter, section, article_no_arabic, char_count, law_department, embed_text
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "laws.db"

SCHEMA = """
CREATE TABLE laws (
    law_id TEXT PRIMARY KEY, law_name TEXT NOT NULL, doc_type TEXT,
    level TEXT, issuing_body TEXT, publish_date TEXT, effective_date TEXT,
    version_date TEXT, status TEXT, law_department TEXT
);
CREATE TABLE articles (
    id INTEGER PRIMARY KEY, law_id TEXT NOT NULL, law_name TEXT NOT NULL,
    law_department TEXT, level TEXT, status TEXT, chapter TEXT, section TEXT,
    article_no TEXT, article_no_arabic INTEGER, article_text TEXT, char_count INTEGER
);
CREATE INDEX idx_articles_law ON articles(law_id);
CREATE INDEX idx_articles_status ON articles(status);
"""


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("用法：python scripts/build_corpus.py <语料.jsonl>")
    src = Path(sys.argv[1])
    if not src.exists():
        sys.exit(f"找不到文件：{src}")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    t0 = time.time()
    n = 0
    latest: dict[str, dict] = {}
    ins = "INSERT INTO articles VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
    with open(src, encoding="utf-8") as f:
        for row_id, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            n += 1
            conn.execute(ins, (
                row_id, r["law_id"], r["law_name"], r.get("law_department"),
                r.get("level"), r.get("status"), r.get("chapter"), r.get("section"),
                r.get("article_no"), r.get("article_no_arabic"),
                r.get("article_text"), r.get("char_count"),
            ))
            prev = latest.get(r["law_id"])
            if prev is None or (r.get("version_date") or "") >= (prev.get("version_date") or ""):
                latest[r["law_id"]] = r
            if n % 5000 == 0:
                print(f"  已解析 {n} 行… ({time.time()-t0:.0f}s)")

    for r in latest.values():
        conn.execute("INSERT INTO laws VALUES (?,?,?,?,?,?,?,?,?,?)", (
            r["law_id"], r["law_name"], r.get("doc_type"), r.get("level"),
            r.get("issuing_body"), r.get("publish_date"), r.get("effective_date"),
            r.get("version_date"), r.get("status"), r.get("law_department"),
        ))
    conn.commit()
    conn.close()
    print(f"完成：{n} 条条文 → {DB_PATH} ({DB_PATH.stat().st_size/1e6:.0f} MB)，耗时 {time.time()-t0:.0f}s")
    print("下一步：索引会在 MCP 服务器首次运行时自动构建（约 6 秒）。")


if __name__ == "__main__":
    main()
