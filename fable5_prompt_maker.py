#!/usr/bin/env python3
"""Backward-compatible wrapper for the public prompt-ops-maker CLI."""
from prompt_ops_maker import main


if __name__ == "__main__":
    raise SystemExit(main())
