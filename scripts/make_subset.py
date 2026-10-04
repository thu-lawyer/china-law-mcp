#!/usr/bin/env python3
"""从完整语料中抽取常用法律子集，用于公开仓库。

用法：python scripts/make_subset.py <完整语料.jsonl> [输出.jsonl]
"""
import json
import sys
from pathlib import Path

# 公开子集：覆盖最高频的咨询场景，够跑通 demo
KEEP = [
    "中华人民共和国民法典", "中华人民共和国刑法", "中华人民共和国劳动合同法",
    "中华人民共和国道路交通安全法", "中华人民共和国消费者权益保护法",
    "中华人民共和国食品安全法", "中华人民共和国治安管理处罚法",
    "中华人民共和国行政诉讼法", "中华人民共和国行政处罚法",
    "中华人民共和国个人信息保护法", "中华人民共和国公司法",
    "中华人民共和国婚姻法", "中华人民共和国继承法", "中华人民共和国侵权责任法",
]

def main() -> None:
    src = Path(sys.argv[1])
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "data/sample_corpus.jsonl")
    keep = set(KEEP) | {k.replace("中华人民共和国", "") for k in KEEP}
    n = 0
    with open(src, encoding="utf-8") as f, open(out, "w", encoding="utf-8") as g:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("law_name") in keep:
                g.write(line + "\n")
                n += 1
    print(f"{n} 条条文 → {out} ({out.stat().st_size/1e6:.1f} MB)")

if __name__ == "__main__":
    main()
