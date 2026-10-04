"""检索：BM25 + 口语同义词扩展 + 覆盖率/短语重排 + 法条直查（移植自 律问 LawQ）。"""
from __future__ import annotations

import os
import pickle
import re
import threading
from pathlib import Path

import jieba

from . import database

PKG_ROOT = Path(__file__).resolve().parent.parent.parent
INDEX_PATH = Path(os.getenv("CHINA_LAW_INDEX") or (PKG_ROOT / "data" / "bm25.pkl"))

_lock = threading.Lock()
_index: dict | None = None
_law_names: set[str] = set()
_alias_map: dict[str, str] = {}
_RECALL_K = 60

CN_DIGITS = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
             "六": 6, "七": 7, "八": 8, "九": 9}
CN_UNITS = {"十": 10, "百": 100, "千": 1000, "万": 10000}

STOPWORDS = set("的了是在和与对于由从被把及或并等请问我你他它这那个之其什么怎么怎样如何"
                "咨询一下有关关于应该可以是否有没有如果因为所以但是然后因此出现进行予以上"
                "最久几多年多月内情况下时候属于".split())

# 口语 / 惯用语 → 法言法语；命中 key 时并入查询词
SYNONYMS = {
    "高空抛物": ["抛掷", "坠落", "建筑物"], "高空坠物": ["抛掷", "坠落", "建筑物"],
    "坠物": ["坠落", "建筑物"], "抛物": ["抛掷"],
    "酒驾": ["饮酒", "醉酒", "驾驶", "机动车"], "醉驾": ["醉酒", "驾驶", "机动车"],
    "酒后开车": ["饮酒", "驾驶", "机动车"], "喝酒开车": ["饮酒", "驾驶", "机动车"],
    "开车": ["机动车", "驾驶"],
    "冷静期": ["离婚", "三十日", "婚姻登记机关"],
    "试用期": ["劳动合同", "用人单位"], "辞退": ["解除", "劳动合同", "用人单位"],
    "开除": ["解除", "劳动合同"], "离职": ["解除", "劳动合同"],
    "正当防卫": ["不法侵害", "防卫", "制止"],
    "无理由退货": ["退货", "七日"], "退货": ["退货", "七日"],
    "借钱": ["借款", "返还"], "欠钱": ["借款", "返还"], "借钱不还": ["借款", "返还", "时效"],
    "砸伤": ["损害", "伤害", "赔偿"], "砸到": ["损害", "赔偿"],
    "维权": ["权利", "责任"], "赔偿": ["损害", "赔偿"],
    "泄露": ["泄露", "提供"], "隐私": ["隐私权", "个人信息"],
    "出资": ["认缴", "出资额", "股东"], "股东": ["股东", "出资"],
    "诉讼时效": ["诉讼时效", "时效"], "时效": ["诉讼时效"],
    "网上购物": ["网络", "经营者"], "网购": ["网络", "经营者"],
    "房子": ["不动产", "房屋"], "租房": ["租赁", "出租人", "承租人"],
    "彩礼": ["婚约", "返还"], "加班": ["加班", "工资"], "拖欠工资": ["劳动报酬", "工资"],
    "诈骗": ["诈骗", "骗取"], "偷": ["盗窃"], "偷窃": ["盗窃"], "抢劫": ["抢劫", "暴力"],
    "打架": ["殴打", "伤害"], "骂人": ["侮辱", "诽谤"],
}

# 共现规则：口语常被 jieba 切成单字，无法靠整词命中，这里按「同时出现」补法律用语
COOCCUR: list[tuple[tuple[str, ...], list[str]]] = [
    (("借", "钱"), ["借款", "返还", "民间借贷"]),
    (("欠", "钱"), ["借款", "返还", "债务"]),
    (("不还",), ["返还", "履行", "债务"]),
    (("赖账",), ["返还", "债务", "违约"]),
    (("外卖", "吃"), ["食品", "食品安全", "消费者"]),
    (("吃出",), ["食品", "食品安全", "赔偿"]),
    (("变质",), ["食品", "食品安全", "赔偿"]),
    (("过期", "食品"), ["食品", "食品安全"]),
    (("网", "买"), ["网络", "电子商务", "消费者"]),
    (("快递", "丢"), ["运输", "赔偿", "承运人"]),
    (("房东",), ["租赁", "出租人", "承租人"]),
    (("押金",), ["租赁", "返还", "定金"]),
    (("加班",), ["加班", "工资", "劳动"]),
    (("辞退", "开除"), ["解除", "劳动合同", "补偿"]),
    (("辞退",), ["解除", "劳动合同", "补偿"]),
    (("社保",), ["社会保险", "社会保险费", "劳动"]),
    (("离婚", "孩子"), ["抚养", "离婚", "子女"]),
    (("孩子", "归"), ["抚养", "子女"]),
    (("遗产",), ["继承", "遗产"]),
    (("车祸",), ["交通事故", "机动车", "赔偿"]),
    (("撞", "人"), ["交通事故", "损害", "赔偿"]),
    (("狗", "咬"), ["饲养", "动物", "损害"]),
    (("噪音",), ["噪声", "污染", "相邻"]),
    (("漏水",), ["相邻", "不动产", "排水"]),
    (("公司", "辞"), ["劳动合同", "解除", "经济补偿"]),
    (("专利",), ["专利", "专利权"]),
    (("商标",), ["商标", "注册商标"]),
    (("借钱",), ["借款", "民间借贷", "返还"]),
    (("打架",), ["故意伤害", "殴打", "治安"]),
    (("过期",), ["食品", "食品安全", "消费者"]),
    (("东西", "坏"), ["消费者", "质量", "赔偿"]),
    (("押金",), ["租赁合同", "返还", "承租人"]),
    (("退", "钱"), ["退货", "返还", "消费者"]),
    (("定金",), ["定金", "返还"]),
    (("宠物", "咬"), ["饲养", "动物", "损害"]),
    (("高空", "掉"), ["建筑物", "坠落", "损害"]),
    (("物业",), ["物业服务", "业主"]),
    (("电梯",), ["物业服务", "特种设备"]),
]

ARTICLE_RE = re.compile(r"《([^》]{2,30})》\s*第\s*([一二三四五六七八九十百千零〇0-9]+)\s*条")
BARE_ARTICLE_RE = re.compile(r"([\u4e00-\u9fff]{2,20}?)\s*第\s*([一二三四五六七八九十百千零〇0-9]+)\s*条")


def cn2num(s: str) -> int | None:
    s = s.strip()
    if s.isdigit():
        return int(s)
    total = num = 0
    for ch in s:
        if ch in CN_DIGITS:
            num = CN_DIGITS[ch]
        elif ch in CN_UNITS:
            if num == 0:
                num = 1
            if CN_UNITS[ch] == 10000:
                total = (total + num) * 10000
            else:
                total += num * CN_UNITS[ch]
            num = 0
        else:
            return None
    return total + num


def build_index(db_path=None, out_path: Path | None = None) -> Path:
    """从 laws.db 构建 BM25 索引（首次运行自动调用）。"""
    from rank_bm25 import BM25Okapi

    out = Path(out_path or INDEX_PATH)
    out.parent.mkdir(parents=True, exist_ok=True)
    ids: list[int] = []
    tokens: list[list[str]] = []
    with database.get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT a.id, a.law_name, a.chapter, a.article_text FROM articles a "
            "JOIN laws l ON l.law_id = a.law_id "
            "WHERE a.status IN ('现行有效','已被修改') "
            "AND l.doc_type IN ('宪法','法律','立法解释')"
        )
        for r in rows:
            ids.append(r["id"])
            text = " ".join(x for x in (r["law_name"], r["chapter"], r["article_text"]) if x)
            tokens.append(tokenize(text))
    bm25 = BM25Okapi(tokens)
    with open(out, "wb") as f:
        pickle.dump({"ids": ids, "bm25": bm25}, f)
    return out


def tokenize(text: str) -> list[str]:
    return [t for t in jieba.lcut(text or "") if re.fullmatch(r"[\u4e00-\u9fff\w]+", t)]


def load(force: bool = False, db_path=None) -> dict:
    global _index, _law_names, _alias_map
    if _index is not None and not force:
        return _index
    with _lock:
        if _index is not None and not force:
            return _index
        if not INDEX_PATH.exists():
            build_index(db_path)
        with open(INDEX_PATH, "rb") as f:
            idx = pickle.load(f)
        with database.get_conn(db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT law_name FROM articles WHERE status IN ('现行有效','已被修改')"
            ).fetchall()
        _law_names = {r["law_name"] for r in rows}
        alias: dict[str, str] = {
            "民诉法": "中华人民共和国民事诉讼法", "刑诉法": "中华人民共和国刑事诉讼法",
            "行诉法": "中华人民共和国行政诉讼法", "消保法": "中华人民共和国消费者权益保护法",
            "个保法": "中华人民共和国个人信息保护法", "道交法": "中华人民共和国道路交通安全法",
            "破产法": "中华人民共和国企业破产法", "网安法": "中华人民共和国网络安全法",
        }
        for name in _law_names:
            if name.startswith("中华人民共和国") and len(name) > 8:
                alias.setdefault(name[7:], name)
        _alias_map = {k: v for k, v in alias.items() if v in _law_names}
        _index = idx
        return _index


def resolve_law(raw: str) -> str | None:
    """把《民法典》《消保法》这类简称解析成库内法律全名。"""
    name = (raw or "").strip("《》 ").strip()
    if not name:
        return None
    load()
    if name in _alias_map:
        return _alias_map[name]
    if name in _law_names:
        return name
    for full in _law_names:
        short = full[7:] if full.startswith("中华人民共和国") else full
        if short and short in name:
            return full
    return None


def _expand(tokens: list[str], question: str) -> list[str]:
    out = list(tokens)
    for key, extra in SYNONYMS.items():
        if key in question:
            out.extend(extra)
    for keys, extra in COOCCUR:          # 共现规则：抗口语分词
        if all(k in question for k in keys):
            out.extend(extra)
    return out


def _tokenize_q(q: str) -> list[str]:
    return [t for t in jieba.lcut(q) if t.strip() and t not in STOPWORDS]


def _phrase_bonus(core: str, text: str) -> float:
    best = 0
    n = len(core)
    for i in range(n):
        for j in range(n, i + 3, -1):
            if j - i > best and core[i:j] in text:
                best = j - i
    return min(best, 12) / 12


def _direct_hits(question: str, db_path=None) -> list[dict]:
    hits: list[dict] = []
    for m in ARTICLE_RE.finditer(question):
        law, no = resolve_law(m.group(1)), cn2num(m.group(2))
        if not law or no is None:
            continue
        rec = database.find_article(law, no, db_path)
        if rec:
            rec["score"], rec["via"] = 999.0, "direct"
            hits.append(rec)
    return hits


def search(question: str, top_k: int = 6, law: str | None = None, db_path=None) -> list[dict]:
    """自然语言问题 → 相关法条列表（带 score 与命中方式）。"""
    load(db_path=db_path)
    direct = _direct_hits(question, db_path)
    tokens = _expand(_tokenize_q(question), question)
    qset = {t for t in tokens if len(t) >= 1}
    core = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", question)

    boost_law = resolve_law(law) if law else None
    if boost_law is None:
        for alias, full in sorted(_alias_map.items(), key=lambda x: -len(x[0])):
            if alias in question:
                boost_law = full
                break

    name_laws = set()
    for t in qset:
        if len(t) >= 4:
            for full in _law_names:
                if t in full:
                    name_laws.add(full)

    candidates: dict[int, dict] = {h["id"]: h for h in direct}
    if tokens:
        scores = _index["bm25"].get_scores(tokens)
        ranked = sorted(zip(_index["ids"], scores), key=lambda x: -x[1])[:_RECALL_K]
        arts = database.get_articles_by_ids([i for i, _ in ranked], db_path)
        max_sc = max((s for _, s in ranked), default=1.0) or 1.0
        for art_id, sc in ranked:
            rec = arts.get(art_id)
            if not rec or sc <= 0:
                continue
            text = rec["article_text"] or ""
            cov = sum(1 for t in qset if t in text) / max(len(qset), 1)
            fb = _phrase_bonus(core, text) if len(core) >= 4 else 0.0
            name_hit = 0.25 if (rec["law_name"] in name_laws or rec["law_name"] == boost_law) else 0.0
            rec["score"] = round(float(sc) / max_sc + 0.45 * cov + 0.55 * fb + name_hit, 4)
            rec["via"] = "retrieval"
            candidates[art_id] = rec
    return sorted(candidates.values(), key=lambda h: -h["score"])[:top_k]
