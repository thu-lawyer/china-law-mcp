#!/usr/bin/env python3
"""china-law · 命令行入口：检索中国现行法条、核验引用是否真实存在。

依赖 china-law-mcp（提供 laws.db 与检索代码）：

    pip install china-law-mcp

用法：

    python law.py search "邻居装修砸墙"
    python law.py get 民法典 288
    python law.py verify 民法典 288
    python law.py list 劳动
    python law.py check "根据《民法典》第288条……"

每个子命令都支持 --json，输出与 MCP 版本的同名工具一致。
"""
from __future__ import annotations

import argparse
import json
import re
import sys

CITE_RE = re.compile(r"《([^》]{2,30})》\s*第\s*([一二三四五六七八九十百千零〇0-9]+)\s*条")


def _load():
    try:
        from china_law_mcp import database, retrieval
    except ImportError:
        sys.exit(
            "缺少依赖 china-law-mcp。\n"
            "  安装：pip install china-law-mcp\n"
            "  或隔离运行：uv run --with china-law-mcp python law.py ..."
        )
    return database, retrieval


def _slim(rec: dict) -> dict:
    return {
        "law": rec.get("law_name"),
        "article_no": rec.get("article_no"),
        "article_no_arabic": rec.get("article_no_arabic"),
        "chapter": rec.get("chapter"),
        "department": rec.get("law_department"),
        "status": rec.get("status"),
        "text": rec.get("article_text"),
        "score": rec.get("score"),
        "via": rec.get("via"),
    }


def verify_citation(database, retrieval, law: str, article_no: str) -> dict:
    """核验一条引用；语义与 MCP 工具 verify_citation 一致。"""
    full = retrieval.resolve_law(law)
    if not full:
        return {"verified": False, "reason": "law_not_found", "law": law,
                "message": f"库内没有这部法律：{law}"}
    no = retrieval.cn2num(article_no)
    if no is None:
        return {"verified": False, "reason": "bad_article_no", "article_no": article_no}
    rec = database.find_article(full, no)
    if not rec:
        return {"verified": False, "reason": "article_not_found", "law": full,
                "article_no": no, "message": f"{full} 没有第 {no} 条"}
    return {"verified": True, "law": full, "article_no": rec["article_no"],
            "text": rec["article_text"], "status": rec["status"],
            "chapter": rec["chapter"]}


def _clip(s: str, n: int = 90) -> str:
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[:n] + "…"


def _out(obj, as_json: bool) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def cmd_search(database, retrieval, a) -> None:
    hits = retrieval.search(a.query, top_k=max(1, min(a.top_k, 20)), law=a.law)
    out = [_slim(h) for h in hits]
    if a.json:
        return _out(out, True)
    if not out:
        print("没有检索到相关条文。换个说法，或先用 list 确认法律是否收录。")
        return
    for i, h in enumerate(out, 1):
        print(f"{i}. {h['law']} {h['article_no']}"
              f"  [{h['status']}]  {h['chapter'] or ''}".rstrip())
        print(f"   {_clip(h['text'])}")


def cmd_get(database, retrieval, a) -> None:
    full = retrieval.resolve_law(a.law)
    if not full:
        sys.exit(f"库内没有匹配的法律：{a.law}（可用 list 查看目录）")
    no = retrieval.cn2num(a.article_no)
    if no is None:
        sys.exit(f"无法解析条号：{a.article_no}")
    rec = database.find_article(full, no)
    if not rec:
        sys.exit(f"未找到条文：{full} 第 {no} 条")
    if a.json:
        return _out(_slim(rec), True)
    print(f"{full} {rec['article_no']}  [{rec['status']}]  {rec['chapter'] or ''}".rstrip())
    print()
    print(rec["article_text"])


def cmd_verify(database, retrieval, a) -> None:
    r = verify_citation(database, retrieval, a.law, a.article_no)
    if a.json:
        return _out(r, True)
    if r["verified"]:
        print(f"✓ 存在：{r['law']} {r['article_no']}  [{r['status']}]  {r['chapter'] or ''}".rstrip())
        print()
        print(r["text"])
    else:
        print(f"✗ 不存在（{r['reason']}）：{r.get('message') or r.get('article_no')}")


def cmd_list(database, retrieval, a) -> None:
    rows = database.list_laws(department=a.department, q=a.keyword)[: max(1, min(a.limit, 200))]
    if a.json:
        return _out(rows, True)
    if not rows:
        print("没有匹配的法律。")
        return
    for r in rows:
        print(f"{r['law_name']}  [{r['status']}]  {r['law_department'] or '其他'}  {r['arts']} 条")


def cmd_check(database, retrieval, a) -> None:
    text = sys.stdin.read() if a.text == "-" else a.text
    results, seen = [], set()
    for law, no in CITE_RE.findall(text or ""):
        if (law, no) in seen:
            continue
        seen.add((law, no))
        r = verify_citation(database, retrieval, law, no)
        results.append({"citation": f"《{law}》第{no}条",
                        "verified": r.get("verified", False),
                        "law": r.get("law") or law,
                        "message": r.get("message")})
    invalid = [r for r in results if not r["verified"]]
    report = {
        "total": len(results),
        "valid": len(results) - len(invalid),
        "invalid": len(invalid),
        "invalid_citations": [r["citation"] for r in invalid],
        "details": results,
    }
    if a.json:
        return _out(report, True)
    if not results:
        print("文本里没有找到「《某法》第 N 条」形式的引用。")
        return
    print(f"共 {report['total']} 条引用：{report['valid']} 条存在，{report['invalid']} 条不存在")
    for r in results:
        mark = "✓" if r["verified"] else "✗"
        tail = "" if r["verified"] else f"    {r['message']}"
        print(f"  {mark} {r['citation']}{tail}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="law.py", description="检索中国现行法条并核验引用")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("search", help="按自然语言问题检索条文")
    p.add_argument("query")
    p.add_argument("top_k", nargs="?", type=int, default=6)
    p.add_argument("--law", default=None, help="限定在某部法律内检索")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("get", help="取指定条文原文")
    p.add_argument("law")
    p.add_argument("article_no")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("verify", help="核验单条引用是否存在")
    p.add_argument("law")
    p.add_argument("article_no")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("list", help="浏览库内法律目录")
    p.add_argument("keyword", nargs="?", default=None)
    p.add_argument("--department", default=None)
    p.add_argument("--limit", type=int, default=30)
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("check", help="抽取文本中的引用并逐条核验（text 传 - 从标准输入读）")
    p.add_argument("text")
    p.add_argument("--json", action="store_true")

    a = ap.parse_args(argv)
    database, retrieval = _load()
    {"search": cmd_search, "get": cmd_get, "verify": cmd_verify,
     "list": cmd_list, "check": cmd_check}[a.cmd](database, retrieval, a)


if __name__ == "__main__":
    main()
