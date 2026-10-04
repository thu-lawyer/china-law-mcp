<div align="center">

# ⚖️ china-law-mcp

**Chinese statute retrieval + citation verification, as an MCP server.**

Free · No signup · No API key · Runs locally

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-server-8A2BE2.svg)](https://modelcontextprotocol.io)

[中文](README.md) · English

</div>

---

## Why

Ask an LLM a Chinese legal question and it may cite **an article that does not exist**. You have no way to check. Law is the last domain where that is acceptable.

china-law-mcp gives your AI an **offline statute database plus a citation checker**:

- Before citing《民法典》Art. 1254, the model calls `verify_citation` — if it does not exist, it gets corrected.
- After drafting an answer, `check_citations_in_text` extracts **every** 《law》Art. N citation and reports the fabricated ones.
- To find the right article, `search_statutes` does natural-language retrieval over 23,995 articles.

Everything is local: no network, no signup, no API key.

## Quick start

```bash
uvx --from git+https://github.com/thu-lawyer/china-law-mcp china-law-mcp
```

MCP client config:

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

## Tools

| Tool | What it does |
| --- | --- |
| `search_statutes(query, top_k, law?)` | Natural-language query → relevant articles |
| `get_article(law, article_no)` | Law + article number → article text |
| `list_laws(keyword?, department?)` | Browse the statute catalogue |
| `verify_citation(law, article_no)` | **Check whether a citation actually exists** |
| `check_citations_in_text(text)` | **Extract all citations from a text and flag fabricated ones** |

## Data

378 statutes / 23,995 in-force articles (constitution, statutes, legislative interpretations). The SQLite DB (15 MB) ships with the repo and works out of the box; the BM25 index is built on first run (~6 s) and cached.

## Limitations

- Retrieval is a **BM25 baseline** with a hand-built colloquial-to-legal rule table (~40 rules). Treat the returned article text as ground truth.
- Scope is constitution / statutes / legislative interpretations only — no administrative regulations or judicial interpretations.
- Not legal advice.

## License

[MIT](LICENSE).
