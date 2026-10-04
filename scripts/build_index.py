#!/usr/bin/env python3
"""预构建 BM25 索引（可选，服务器首次运行会自动建）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from china_law_mcp import retrieval  # noqa: E402

if __name__ == "__main__":
    p = retrieval.build_index()
    print(f"BM25 索引 → {p} ({p.stat().st_size/1e6:.0f} MB)")
