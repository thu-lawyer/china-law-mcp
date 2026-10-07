---
name: china-law
description: 检索中国现行法律法规、核对法条引用是否真实存在。当用户需要查找中国法条（民法典、刑法、劳动合同法等）、确认某一条法条是否存在或条号是否正确、检查一段文本里的「《某法》第 N 条」引用有没有编造时使用。
---

# china-law

检索中国现行法律条文，并核验引用是否真实存在 —— 用来抓住 AI 编造的法条号。

## 何时用

| 场景 | 命令 |
| --- | --- |
| 用户问「这事法律怎么规定的」「哪一条管这个」 | `search` |
| 已经写出「《X 法》第 N 条」，准备引用 | 先 `verify` 再引用 |
| 要检查一段成稿里的引用是否可靠 | `check` |
| 确认某部法律是否收录、共几条 | `list` |
| 需要某一条的完整原文 | `get` |

## 依赖

```bash
pip install china-law-mcp        # 提供 laws.db 与检索代码
```

不想装进当前环境时，用 uv 隔离运行（把下文的 `python` 换成这行）：

```bash
uv run --with china-law-mcp python law.py search "..."
```

## 用法

脚本 `law.py` 有五个子命令，各带 `--json` 便于脚本消费：

```bash
python law.py search "邻居装修砸墙"            # 自然语言 → 相关法条
python law.py get 民法典 288                  # 取指定条文原文
python law.py verify 民法典 288               # 核验单条引用
python law.py list 劳动                       # 查收录的法律
python law.py check "根据《民法典》第288条……"   # 批量核验文本中的引用
```

条号用阿拉伯数字或中文数字都可以（`288` / `第二百八十八条`）。
法律名支持简称（`民法典` / `消保法` / `劳动合同法`）。

## 铁律

- **凡引用先 `verify`**。返回 `verified: false` 时不要把该引用写进答案，改引 `search` 返回的真实条文。
- `check` 的 `invalid > 0` 时，逐条列出无效引用与原因（`law_not_found` / `article_not_found` / `bad_article_no`），不要含糊带过。
- 检索结果只覆盖「现行有效 / 已被修改」条文；已废止与历史版本不在返回范围内，所以不要把检索不到理解为「这部法律不存在」。
- 库内条文可用于回答法律内容问题，但不构成法律意见；涉及具体纠纷时提醒用户核对官方文本。

## 与 MCP 版本的关系

同一套能力的 MCP 服务器版本是 `china-law-mcp`（`uvx china-law-mcp`）。
五个工具与这里的五个子命令一一对应，输出字段相同。
