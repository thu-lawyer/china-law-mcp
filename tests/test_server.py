"""china-law-mcp 核心行为测试。

数据依赖：data/laws.db（随仓库提供）。首次运行会构建 BM25 索引（约 6 秒）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from china_law_mcp import database, retrieval, server  # noqa: E402


@pytest.fixture(scope="session")
def db():
    database.ensure_db()


def test_database_has_expected_scale(db):
    st = database.get_stats()
    assert st["laws"] > 300, "法条库应包含 300 部以上法律"
    assert st["articles"] > 20000, "现行条文应有 2 万条以上"


@pytest.mark.parametrize("alias,no,expect_law", [
    ("民法典", "1254", "中华人民共和国民法典"),
    ("刑法", "20", "中华人民共和国刑法"),
    ("消保法", "24", "中华人民共和国消费者权益保护法"),
])
def test_get_article_resolves_aliases(db, alias, no, expect_law):
    r = server.get_article(alias, no)
    assert r and r["law"] == expect_law
    assert r["article_no_arabic"] == int(no)


def test_get_article_accepts_chinese_numeral(db):
    a = server.get_article("民法典", "1254")
    b = server.get_article("民法典", "第一千二百五十四条")
    assert a and b and a["text"] == b["text"]


def test_verify_citation_true_and_false(db):
    assert server.verify_citation("民法典", "1254")["verified"] is True
    bad = server.verify_citation("民法典", "9999")
    assert bad["verified"] is False and bad["reason"] == "article_not_found"
    assert server.verify_citation("不存在法", "3")["verified"] is False


def test_check_citations_flags_fabricated(db):
    """核心防幻觉能力：真实引用保留，编造的引用被列出。"""
    text = "根据《民法典》第1254条，高空抛物由侵权人担责；另见《劳动合同法》第99条与《民法典》第88888条。"
    r = server.check_citations_in_text(text)
    assert r["total"] == 3
    assert r["valid"] == 1
    assert "《劳动合同法》第99条" in r["invalid_citations"]
    assert "《民法典》第88888条" in r["invalid_citations"]


@pytest.mark.parametrize("query,expect_law", [
    ("高空抛物砸到人", "中华人民共和国民法典"),
    ("公司无故辞退我", "中华人民共和国劳动合同法"),
    ("外卖吃出异物", "中华人民共和国食品安全法"),
])
def test_search_routes_colloquial_queries(db, query, expect_law):
    hits = retrieval.search(query, top_k=3)
    assert hits, f"查询「{query}」应有结果"
    assert any(h["law_name"] == expect_law for h in hits), \
        f"「{query}」应命中 {expect_law}，实际：{[h['law_name'] for h in hits]}"


def test_search_direct_citation_is_top(db):
    hits = retrieval.search("《民法典》第1254条", top_k=3)
    assert hits[0]["article_no_arabic"] == 1254 and hits[0]["via"] == "direct"


def test_list_laws_filters(db):
    assert server.list_laws(keyword="劳动")
    assert all("劳动" in x["law_name"] for x in server.list_laws(keyword="劳动"))
