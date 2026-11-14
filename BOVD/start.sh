#!/usr/bin/env sh
# BOVD – no-Docker start for macOS/Linux
cd "$(dirname "$0")"
python3 -c "import cryptography" 2>/dev/null || python3 -m pip install -q cryptography 2>/dev/null || echo "[i] using built-in pure-Python AES-256-GCM"
exec python3 -m astra.server
