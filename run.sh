#!/usr/bin/env bash
# Lanza Void of Voices desde el código fuente (prepara el entorno la primera vez).
cd "$(dirname "$(readlink -f "$0")")" || exit 1
if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt && .venv/bin/pip install -q --no-deps pyrnnoise
fi
exec .venv/bin/python main.py "$@"
