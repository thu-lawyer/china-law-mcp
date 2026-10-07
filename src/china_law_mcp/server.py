"""china-law-mcp · 中国法律 MCP 服务器

对外工具：
  search_statutes        自然语言 → 相关法条
  get_article            法律 + 条号 → 条文原文
  list_laws              浏览法律目录
  verify_citation        核验单条引用是否存在（防幻觉）
  check_citations_in_text 抽取文本中的全部引用并逐条核验
"""
from __future__ import annotations

import re
import sys

from mcp.server.mcpserver import MCPServer

from . import database, retrieval

INSTRUCTIONS = """中国法律条文检索与引用核验工具（数据：378 部法律 / 23,995 条现行条文）。

用于回答中国法律问题时，请按此流程使用：
1. 先用 search_statutes 检索相关法条，只依据返回的条文原文作答；
2. 如果回答里要引用《某法》第 N 条，先调 verify_citation 确认该条真实存在；
3. 若你已有草稿，可用 check_citations_in_text 一次性核验其中所有引用。
不要凭记忆编造法条——本工具的数据就是用来消除这种幻觉的。"""

server = MCPServer(
    name="china-law-mcp",
    title="China Law MCP",
    instructions=INSTRUCTIONS,
    version="0.1.1",
)

try:
    database.ensure_db()
except Exception as _e:  # 启动即给出清晰提示，而不是等到第一次调用工具才报错
    print(f"china-law-mcp: {_e}", file=sys.stderr)


def _slim(rec: dict) -> dict:
    """统一输出字段，去掉内部列。"""
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


@server.tool()
def search_statutes(query: str, top_k: int = 6, law: str | None = None) -> list[dict]:
    """按自然语言问题检索中国现行法律条文。

    支持口语提问（如「同事借我钱不还怎么办」「外卖吃出异物能退吗」），
    也会自动扩展为法言法语；支持「《民法典》第1254条」这类精确引用（直查优先）。

    Args:
        query: 自然语言问题或关键词。
        top_k: 返回条数，默认 6。
        law: 可选，限定在某部法律内检索，支持简称如「民法典」「消保法」。

    Returns:
        条文列表，含 law / article_no / chapter / text / score / via。
    """
    hits = retrieval.search(query, top_k=max(1, min(int(top_k), 20)), law=law)
    return [_slim(h) for h in hits]


@server.tool()
def get_article(law: str, article_no: str) -> dict | None:
    """按法律名与条号取条文原文。

    Args:
        law: 法律名，支持简称，如「民法典」「中华人民共和国刑法」。
        article_no: 条号，中文或阿拉伯数字均可，如「1254」「第一千二百五十四条」。

    Returns:
        找到则返回条文（含所属编章、部门法、时效状态），否则 None。
    """
    full = retrieval.resolve_law(law)
    if not full:
        return {"error": f"库内没有匹配的法律：{law}", "hint": "可用 list_laws 查看法律目录"}
    no = retrieval.cn2num(article_no) if not str(article_no).isdigit() else int(article_no)
    if no is None:
        return {"error": f"无法解析条号：{article_no}"}
    rec = database.find_article(full, no)
    if not rec:
        return {"error": f"未找到条文：{full} 第 {no} 条", "law": full, "article_no": no}
    return _slim(rec)


@server.tool()
def list_laws(keyword: str | None = None, department: str | None = None,
              limit: int = 30) -> list[dict]:
    """浏览库内法律目录（可按名称关键词或部门法筛选）。

    Args:
        keyword: 法律名包含的关键词，如「劳动」「行政」。
        department: 部门法，如「民法商法」「行政法」。
        limit: 最多返回条数，默认 30。
    """
    return database.list_laws(department=department, q=keyword)[: max(1, min(int(limit), 200))]


@server.tool()
def verify_citation(law: str, article_no: str) -> dict:
    """核验一条法律引用是否真实存在（防幻觉）。

    在引用《某法》第 N 条之前调用本工具，可以避免编造或引用已废止条文。

    Args:
        law: 法律名，支持简称，如「民法典」。
        article_no: 条号，如「1254」或「第一千二百五十四条」。

    Returns:
        verified(bool) + 条文原文（存在时）/ 原因（不存在时）。
    """
    full = retrieval.resolve_law(law)
    if not full:
        return {"verified": False, "reason": "law_not_found",
                "law": law, "message": f"库内没有这部法律：{law}"}
    no = retrieval.cn2num(article_no) if not str(article_no).isdigit() else int(article_no)
    if no is None:
        return {"verified": False, "reason": "bad_article_no", "article_no": article_no}
    rec = database.find_article(full, no)
    if not rec:
        return {"verified": False, "reason": "article_not_found",
                "law": full, "article_no": no, "message": f"{full} 没有第 {no} 条"}
    return {"verified": True, "law": full, "article_no": rec["article_no"],
            "text": rec["article_text"], "status": rec["status"], "chapter": rec["chapter"]}


_CITE_RE = re.compile(r"《([^》]{2,30})》\s*第\s*([一二三四五六七八九十百千零〇0-9]+)\s*条")


@server.tool()
def check_citations_in_text(text: str) -> dict:
    """抽取一段文本中的所有《法律》第 N 条引用并逐条核验，返回不存在的引用清单。

    把模型生成的答案整段传进来，即可发现其中编造的引用。

    Args:
        text: 待检查的文本（例如模型输出的一段法律分析）。

    Returns:
        total / valid / invalid 计数，以及逐条核验结果。
    """
    found = _CITE_RE.findall(text or "")
    results = []
    seen = set()
    for law, no in found:
        key = (law, no)
        if key in seen:
            continue
        seen.add(key)
        r = verify_citation(law, no)
        results.append({"citation": f"《{law}》第{no}条",
                        "verified": r.get("verified", False),
                        "law": r.get("law") or law,
                        "message": r.get("message")})
    invalid = [r for r in results if not r["verified"]]
    return {
        "total": len(results),
        "valid": len(results) - len(invalid),
        "invalid": len(invalid),
        "invalid_citations": [r["citation"] for r in invalid],
        "details": results,
    }


def main() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main()
