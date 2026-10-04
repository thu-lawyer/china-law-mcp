#!/usr/bin/env python3
"""把 laws.db 加密为 laws.db.enc（AES-256-GCM + scrypt 派生密钥）。

用法：
    export CHINA_LAW_KEY='你的口令'
    python scripts/encrypt_data.py data/laws.db          # → data/laws.db.enc

MCP 服务器启动时，若只有 laws.db.enc，会用同样的 CHINA_LAW_KEY 解密到临时文件。
注意：密文与口令放在同一处等于没加密；口令必须单独传递。
"""
from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

MAGIC = b"CLAW1"


def derive(passphrase: str, salt: bytes) -> bytes:
    import hashlib
    return hashlib.scrypt(passphrase.encode(), salt=salt, n=2 ** 15, r=8, p=1, dklen=32,
                          maxmem=128 * 1024 * 1024)


def encrypt_file(src: Path, dst: Path, passphrase: str) -> None:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = derive(passphrase, salt)
    blob = AESGCM(key).encrypt(nonce, src.read_bytes(), None)
    dst.write_bytes(MAGIC + salt + nonce + blob)
    print(f"加密完成 → {dst} ({dst.stat().st_size/1e6:.1f} MB)")


def decrypt_file(src: Path, dst: Path, passphrase: str) -> None:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    raw = src.read_bytes()
    if not raw.startswith(MAGIC):
        raise ValueError("不是有效的加密文件")
    salt, nonce, blob = raw[5:21], raw[21:33], raw[33:]
    key = derive(passphrase, salt)
    dst.write_bytes(AESGCM(key).decrypt(nonce, blob, None))


if __name__ == "__main__":
    key = os.getenv("CHINA_LAW_KEY", "").strip()
    if not key:
        sys.exit("请先设置环境变量 CHINA_LAW_KEY")
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "data/laws.db")
    if not src.exists():
        sys.exit(f"找不到 {src}")
    encrypt_file(src, src.with_suffix(src.suffix + ".enc"), key)
