#!/bin/sh
cd "$(dirname "$0")" || exit 1
if [ -x .venv/bin/python ]; then exec .venv/bin/python start_toolforge.py; fi
exec python3 start_toolforge.py
