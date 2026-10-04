<div align="center">

# ⚖️ china-law-mcp

**中国法律条文 MCP 服务器 · 让 AI 引用法条不再编造**

免费 · 免注册 · 免 API key · 本地运行

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-server-8A2BE2.svg)](https://modelcontextprotocol.io)
[![Laws](https://img.shields.io/badge/laws-378%20(full%20%2F%2011%20public)-green.svg)](#数据)
[![Articles](https://img.shields.io/badge/articles-23%2C995-brightgreen.svg)](#数据)

[English](README.en.md) · 中文

</div>

---

## 解决什么问题

直接问大模型中国法律问题，有两个后果：**引用的条文可能根本不存在或已废止**，**你无法核实**。法律是最不能容忍编造的领域。

china-law-mcp 给 AI 装上一个**离线法条库 + 引用核验器**：

- 模型要引用《民法典》第 1254 条？先调 `verify_citation` 查一下，不存在就换掉
- 模型写了一整段分析？`check_citations_in_text` 会把里面**所有**《某法》第 N 条抽出来逐条核验，列出编造的引用
- 不知道适用哪条？`search_statutes` 用自然语言检索（支持「同事借我钱不还」这种口语）

**数据在本地，不联网、不注册、不需要 API key。** 公开仓库自带常用法律子集，完整法条库加密存放。

## 快速开始

**方式一：一条命令（推荐）**

```bash
uvx --from git+https://github.com/thu-lawyer/china-law-mcp china-law-mcp
```

**方式二：克隆运行**

```bash
git clone https://github.com/thu-lawyer/china-law-mcp
cd china-law-mcp
pip install -r requirements.txt
python -m china_law_mcp        # 首次运行自动构建 BM25 索引，约 6 秒
```

**接入 Claude Code / Cursor / 其他 MCP 客户端**

```json
{
  "mcpServers": {
    "china-law": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/thu-lawyer/china-law-mcp", "china-law-mcp"]
    }
  }
}
```

## 工具

| 工具 | 作用 |
| --- | --- |
| `search_statutes(query, top_k, law?)` | 自然语言问题 → 相关法条（口语自动扩展为法言法语） |
| `get_article(law, article_no)` | 法律 + 条号 → 条文原文，支持「民法典」「1254」「第一千二百五十四条」 |
| `list_laws(keyword?, department?)` | 浏览库内法律目录 |
| `verify_citation(law, article_no)` | **核验单条引用是否真实存在** |
| `check_citations_in_text(text)` | **抽取文本中全部引用并逐条核验，列出编造的** |

## 效果示例

**自然语言检索**（口语直接问）：

```text
search_statutes("同事借我钱不还怎么办")
→ 中华人民共和国民法典 第六百七十五条  借款人应当按照约定的期限返还借款…
→ 中华人民共和国民法典 第六百七十四条  借款人应当按照约定的期限支付利息…

search_statutes("外卖吃出异物能退吗")
→ 中华人民共和国食品安全法 第一百四十八条  消费者因不符合食品安全标准的食品受到损害的，
                                            可以向经营者要求赔偿损失，也可以向生产者要求赔偿…
```

**引用核验**（防止 AI 编造）：

```text
verify_citation("民法典", "1254")   → verified=True   （真实存在）
verify_citation("民法典", "9999")   → verified=False  中华人民共和国民法典 没有第 9999 条

check_citations_in_text("根据《民法典》第1254条…依据《劳动合同法》第99条和《民法典》第88888条…")
→ 共 3 条，有效 1，无效 2
→ invalid: ['《劳动合同法》第99条', '《民法典》第88888条']
```

## 数据：两层设计

公开仓库**不带全量法条数据**，避免数据被任意再分发。

| 层 | 内容 | 位置 |
| --- | --- | --- |
| **公开子集**（随仓库） | 11 部常用法律 / 2,877 条现行条文：民法典、刑法、劳动合同法、道路交通安全法、消费者权益保护法、食品安全法、治安管理处罚法、行政诉讼法、行政处罚法、个人信息保护法、公司法 | `data/laws.db`（2 MB，开箱即用） |
| **完整数据**（不公开） | 378 部法律 / 23,995 条现行条文：宪法、法律、立法解释全量 | `data/laws.db.enc`（AES-256-GCM 加密，需口令） |

**使用完整数据**：

```bash
export CHINA_LAW_KEY='你的口令'      # 由数据提供方单独告知
python -m china_law_mcp              # 自动解密到临时文件，进程退出即清理
```

设计要点：

- 加密为 **AES-256-GCM**，密钥由 **scrypt**（n=2¹⁵）从口令派生；口令错误会因认证标签校验失败而直接拒绝，不会解出损坏数据
- 明文只落在系统临时目录，进程退出自动删除
- **未设置口令时**：检测到 `laws.db.enc` 会给出明确提示，而不是静默失败
- ⚠️ 密文与口令若放在同一处，加密等于没有——口令必须**单独传递**

**自建数据**（换成你自己的语料）：

```bash
python scripts/build_corpus.py 你的条文.jsonl     # → data/laws.db
python scripts/encrypt_data.py data/laws.db       # → data/laws.db.enc（需 CHINA_LAW_KEY）
python scripts/make_subset.py 完整语料.jsonl       # → 抽取公开子集
```

## 工作原理

```
用户提问
   ↓
search_statutes   ← BM25 召回 + 口语同义词/共现规则扩展 + 覆盖率与短语重排 + 条号直查
   ↓
返回条文原文（含出处）
   ↓
模型依据条文作答
   ↓
check_citations_in_text   ← 正则抽取《X法》第N条，逐条查库核验
   ↓
编造的引用被列出并剔除
```

检索是**纯本地 BM25**（`rank-bm25` + `jieba`），不调用任何外部 API，因此没有网络依赖、没有调用成本，也不会把你的查询发给第三方。

## 已知局限

- **公开仓库只含 11 部常用法律的子集**；完整 378 部需向维护者获取加密数据与口令。
- **检索是 BM25 基线**，口语→法言法语的映射靠一张手工规则表（约 40 条）。常见场景效果好，生僻表述可能召回不相关条文——**请始终以返回的条文原文为准**。
- 覆盖范围为**宪法、法律、立法解释**（378 部），不含行政法规、地方性法规、司法解释。修法频繁的领域请留意时效状态字段。
- 条文时效状态部分为库内推定（见语料 `status_basis` 字段）。
- 本工具提供条文检索与引用核验，**不构成法律意见**。

## 相关项目

- [律问 LawQ](https://github.com/thu-lawyer/lawq) —— 同一套检索引擎的 Web / 小程序版本（带流式问答）
- [中国行政诉讼案例数据集](https://github.com/thu-lawyer/xingzheng-susongfa-case-index) —— 635 个行政案件、425 篇裁判文书全文

## 许可

[MIT](LICENSE)。条文数据来自公开渠道整理，请遵守相应来源的使用条款。
