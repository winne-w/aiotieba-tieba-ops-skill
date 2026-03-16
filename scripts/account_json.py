#!/usr/bin/env python3
"""Export an aiotieba Account JSON file from BDUSS."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


INSTALL_HINT = (
    "aiotieba is not installed; install the image-posting branch with: "
    "pip install 'git+https://github.com/winne-w/aiotieba.git@feature/image-posting' "
    "or clone https://github.com/winne-w/aiotieba/tree/feature/image-posting "
    "and import that checkout"
)


def default_account_json_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        return Path(config_home).expanduser() / "aiotieba-tieba-ops" / "account.json"
    return Path.home() / ".config" / "aiotieba-tieba-ops" / "account.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bduss", help="BDUSS token. Falls back to AIO_TIEBA_BDUSS.")
    parser.add_argument(
        "--output",
        help="Output path for the serialized account JSON. Defaults to $XDG_CONFIG_HOME/aiotieba-tieba-ops/account.json or ~/.config/aiotieba-tieba-ops/account.json.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Also print the serialized JSON to stdout.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bduss = args.bduss or os.environ.get("AIO_TIEBA_BDUSS")
    if not bduss:
        print("missing BDUSS; pass --bduss or set AIO_TIEBA_BDUSS", file=sys.stderr)
        return 2

    try:
        import aiotieba as tb
    except ImportError:
        print(INSTALL_HINT, file=sys.stderr)
        return 3

    account = tb.Account(bduss)
    payload = account.to_dict()

    output_path = Path(args.output).expanduser() if args.output else default_account_json_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n")
    output_path.chmod(0o600)

    if args.stdout:
        print(json.dumps(payload, ensure_ascii=True, indent=2))

    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
