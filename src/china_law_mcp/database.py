"""SQLite 读取层：法条 / 法律目录 / 条文直查。"""
from __future__ import annotations

import os
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB = Path(os.getenv("CHINA_LAW_DB") or (PKG_ROOT / "data" / "laws.db"))

ARTICLE_COLS = (
    "id, law_id, law_name, law_department, level, status, chapter, section, "
    "article_no, article_no_arabic, article_text, char_count"
)

# 「已被修改」是库内因存在修正案而保守标注，条文本身是现行文本，应当可见
CURRENT = "status IN ('现行有效', '已被修改')"


@contextmanager
def get_conn(db_path: Path | str | None = None):
    conn = sqlite3.connect(str(ensure_db(db_path)))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def db_exists(db_path: Path | str | None = None) -> bool:
    return Path(db_path or DEFAULT_DB).exists()


def get_stats(db_path=None) -> dict:
    with get_conn(db_path) as conn:
        laws = conn.execute("SELECT COUNT(*) c FROM laws").fetchone()["c"]
        arts = conn.execute(f"SELECT COUNT(*) c FROM articles WHERE {CURRENT}").fetchone()["c"]
        depts = conn.execute(
            f"SELECT law_department d, COUNT(DISTINCT law_id) laws, COUNT(*) arts FROM articles "
            f"WHERE {CURRENT} GROUP BY law_department ORDER BY arts DESC"
        ).fetchall()
        return {
            "laws": laws,
            "articles": arts,
            "departments": [
                {"name": r["d"] or "其他", "laws": r["laws"], "articles": r["arts"]}
                for r in depts
            ],
        }


def list_laws(department: str | None = None, q: str | None = None, db_path=None) -> list[dict]:
    sql = (
        "SELECT l.law_id, l.law_name, l.law_department, l.doc_type, l.issuing_body, "
        "l.version_date, l.status, "
        "(SELECT COUNT(*) FROM articles a WHERE a.law_id=l.law_id AND a.status IN ('现行有效','已被修改')) arts "
        "FROM laws l WHERE l.law_id IN (SELECT DISTINCT law_id FROM articles)"
    )
    args: list = []
    if department:
        sql += " AND l.law_department = ?"
        args.append(department)
    if q:
        sql += " AND l.law_name LIKE ?"
        args.append(f"%{q}%")
    sql += " ORDER BY arts DESC, l.law_name"
    with get_conn(db_path) as conn:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]


def get_articles_by_ids(ids: list[int], db_path=None) -> dict[int, dict]:
    if not ids:
        return {}
    out: dict[int, dict] = {}
    with get_conn(db_path) as conn:
        for chunk in range(0, len(ids), 400):
            part = ids[chunk:chunk + 400]
            ph = ",".join("?" * len(part))
            for r in conn.execute(f"SELECT {ARTICLE_COLS} FROM articles WHERE id IN ({ph})", part):
                d = dict(r)
                out[d["id"]] = d
    return out


def find_article(law_name: str, article_no_arabic: int, db_path=None) -> dict | None:
    """按法律全名 + 条号（阿拉伯数字）取现行条文。"""
    with get_conn(db_path) as conn:
        row = conn.execute(
            f"SELECT {ARTICLE_COLS} FROM articles WHERE law_name=? AND article_no_arabic=? "
            f"AND {CURRENT} ORDER BY id LIMIT 1",
            (law_name, article_no_arabic),
        ).fetchone()
        return dict(row) if row else None

ENC_SUFFIX = ".enc"
_decrypted_tmp: Path | None = None


def ensure_db(db_path: Path | str | None = None) -> Path:
    """确保明文数据库可用。

    优先级：
      1. 已存在的明文 laws.db
      2. laws.db.enc + 环境变量 CHINA_LAW_KEY → 解密到临时文件（进程退出时清理）
    """
    global _decrypted_tmp
    p = Path(db_path or DEFAULT_DB)
    if p.exists():
        return p
    enc = p.with_suffix(p.suffix + ENC_SUFFIX)
    if not enc.exists():
        raise FileNotFoundError(
            f"找不到数据库：{p}\n"
            "公开仓库只带常用法律子集；完整数据请向维护者获取 laws.db.enc，\n"
            "并设置 CHINA_LAW_KEY 后再启动。"
        )
    key = os.getenv("CHINA_LAW_KEY", "").strip()
    if not key:
        raise RuntimeError(
            f"检测到加密数据库 {enc.name}，但未设置 CHINA_LAW_KEY 环境变量。"
        )
    import atexit
    import tempfile

    sys_path = Path(__file__).resolve().parent.parent.parent / "scripts"
    sys.path.insert(0, str(sys_path))
    from encrypt_data import decrypt_file  # type: ignore

    fd, tmp = tempfile.mkstemp(prefix="claw-", suffix=".db")
    os.close(fd)
    tmp_path = Path(tmp)
    decrypt_file(enc, tmp_path, key)
    _decrypted_tmp = tmp_path
    atexit.register(lambda: tmp_path.unlink(missing_ok=True))
    return tmp_path
