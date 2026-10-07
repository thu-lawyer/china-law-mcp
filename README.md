<div align="center">

# ⚖️ china-law-mcp

**中国法律条文 MCP 服务器 · 让 AI 引用法条不再编造**

免费 · 免注册 · 免 API key · 本地运行

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/thu-lawyer/china-law-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/thu-lawyer/china-law-mcp/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab.svg)](https://python.org)
[![PyPI](https://img.shields.io/pypi/v/china-law-mcp.svg)](https://pypi.org/project/china-law-mcp/)
[![Downloads](https://img.shields.io/pypi/dm/china-law-mcp.svg)](https://pypi.org/project/china-law-mcp/)
[![MCP](https://img.shields.io/badge/MCP-server-8A2BE2.svg)](https://modelcontextprotocol.io)
[![MCP Registry](https://img.shields.io/badge/MCP%20Registry-active-2ea44f.svg)](https://registry.modelcontextprotocol.io/v0/servers?search=china-law-mcp)
[![Glama](https://glama.ai/mcp/servers/thu-lawyer/china-law-mcp/badges/score.svg)](https://glama.ai/mcp/servers/thu-lawyer/china-law-mcp)
[![ghcr.io](https://img.shields.io/badge/ghcr.io-china--law--mcp-2496ED.svg?logo=docker&logoColor=white)](https://github.com/thu-lawyer/china-law-mcp/pkgs/container/china-law-mcp)
[![Laws](https://img.shields.io/badge/laws-378-green.svg)](#数据)
[![Articles](https://img.shields.io/badge/articles-23%2C995-brightgreen.svg)](#数据)

[English](README.en.md) · 中文

</div>

<!-- mcp-name: io.github.thu-lawyer/china-law-mcp -->

---

## 解决什么问题

直接问大模型中国法律问题，有两个后果：**引用的条文可能根本不存在或已废止**，**你无法核实**。法律是最不能容忍编造的领域。

china-law-mcp 给 AI 装上一个**离线法条库 + 引用核验器**：

- 模型要引用《民法典》第 1254 条？先调 `verify_citation` 查一下，不存在就换掉
- 模型写了一整段分析？`check_citations_in_text` 会把里面**所有**《某法》第 N 条抽出来逐条核验，列出编造的引用
- 不知道适用哪条？`search_statutes` 用自然语言检索（支持「同事借我钱不还」这种口语）

**数据在本地，不联网、不注册、不需要 API key。**

## 快速开始

**方式一：一行命令（推荐）**

```bash
uvx china-law-mcp
```

**方式二：pip 安装**

```bash
pip install china-law-mcp
china-law-mcp
```

**方式三：克隆运行**

```bash
git clone https://github.com/thu-lawyer/china-law-mcp
cd china-law-mcp
pip install -r requirements.txt
python -m china_law_mcp        # 首次运行自动构建 BM25 索引，约 6 秒
```

**方式四：Docker**（镜像已发布到 ghcr.io）

```bash
docker run -i --rm ghcr.io/thu-lawyer/china-law-mcp:latest
```

```json
{
  "mcpServers": {
    "china-law": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "ghcr.io/thu-lawyer/china-law-mcp:latest"]
    }
  }
}
```

**接入 Claude Code / Cursor / 其他 MCP 客户端**

```json
{
  "mcpServers": {
    "china-law": {
      "command": "uvx",
      "args": ["china-law-mcp"]
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

## 数据

- **378 部法律、23,995 条现行条文**（宪法、法律、立法解释全量）
- 每条含：法律名、编章、条号（中文 + 阿拉伯数字）、条文全文、部门法、时效状态
- SQLite 数据库（15 MB）**随仓库提供，开箱即用**；BM25 索引首次运行自动构建（约 6 秒，之后缓存）

**换成你自己的语料**：

```bash
python scripts/build_corpus.py 你的条文.jsonl     # → data/laws.db
```

字段说明见 `scripts/build_corpus.py` 头部注释。`scripts/` 下另有两个可选工具：`make_subset.py`（抽取常用法律子集）、`encrypt_data.py`（把数据库加密为 `laws.db.enc`，服务器可用 `CHINA_LAW_KEY` 环境变量自动解密）。

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

- **检索是 BM25 基线**，口语→法言法语的映射靠一张手工规则表（约 40 条）。常见场景效果好，生僻表述可能召回不相关条文——**请始终以返回的条文原文为准**。
- 覆盖范围为**宪法、法律、立法解释**（378 部），不含行政法规、地方性法规、司法解释。修法频繁的领域请留意时效状态字段。
- 条文时效状态部分为库内推定（见语料 `status_basis` 字段）。
- 本工具提供条文检索与引用核验，**不构成法律意见**。

## 收录情况

- **PyPI**：https://pypi.org/project/china-law-mcp/
- **MCP 官方注册表**（active）：https://registry.modelcontextprotocol.io/v0/servers?search=china-law-mcp
- **Glama**：https://glama.ai/mcp/servers/thu-lawyer/china-law-mcp —— 工具定义评分 **A**
- **awesome-mcp-servers**：已提交 PR
- 容器镜像：`ghcr.io/thu-lawyer/china-law-mcp`

## 开发

```bash
pip install -r requirements-dev.txt
PYTHONPATH=src pytest tests/ -v     # 12 个测试，覆盖检索、直查、引用核验
```

## 相关项目

- [律问 LawQ](https://github.com/thu-lawyer/lawq) —— 同一套检索引擎的 Web / 小程序版本（带流式问答）
- [中国行政诉讼案例数据集](https://github.com/thu-lawyer/xingzheng-susongfa-case-index) —— 635 个行政案件、425 篇裁判文书全文

## 许可

[MIT](LICENSE)。条文数据来自公开渠道整理，请遵守相应来源的使用条款。
