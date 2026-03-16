#!/usr/bin/env python3
"""Reply to a Tieba thread with images via the TiebaLite web flow.

Flow:
1. Use aiotieba to bootstrap login state and resolve forum/account fields.
2. Upload each image to `/mo/q/cooluploadpic` as base64.
3. Compute `_BSK` with TiebaLite's `new_bsk.js` via Node.js.
4. Submit `/mo/q/apubpost` with `upload_img_info`.

This follows the implementation pattern used by TiebaLite:
https://github.com/zzc10086/TiebaLite
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import random
import subprocess
import time
from pathlib import Path
from typing import Any

import aiohttp

BSK_JS_URL = (
    "https://raw.githubusercontent.com/zzc10086/TiebaLite/master/"
    "app/src/main/assets/new_bsk.js"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bduss", help="BDUSS token. Falls back to AIO_TIEBA_BDUSS.")
    parser.add_argument("--stoken", help="STOKEN token. Falls back to AIO_TIEBA_STOKEN.")
    parser.add_argument(
        "--account-json",
        help="Path to an aiotieba Account JSON file. Falls back to AIO_TIEBA_ACCOUNT_JSON.",
    )
    parser.add_argument("--forum", required=True, help="Forum name or fid.")
    parser.add_argument("--tid", required=True, type=int, help="Thread id to reply to.")
    parser.add_argument("--text", required=True, help="Plain reply text.")
    parser.add_argument(
        "--image",
        action="append",
        required=True,
        help="Local image path. Repeat this flag to upload multiple images.",
    )
    parser.add_argument("--pn", type=int, default=1, help="Thread page number used in Referer.")
    parser.add_argument("--pid", help="Reply to a post id instead of the main thread.")
    parser.add_argument("--floor", help="Floor number when replying to a post.")
    parser.add_argument("--lzl-id", help="Reply to a sub-post id.")
    parser.add_argument("--nick-name", help="Override nick_name field. Defaults to current account nickname.")
    parser.add_argument(
        "--bsk",
        help="Use a precomputed _BSK value. If omitted, this script computes it with new_bsk.js.",
    )
    parser.add_argument(
        "--bsk-js",
        help="Path to TiebaLite new_bsk.js. If omitted, the script downloads it from GitHub.",
    )
    return parser.parse_args()


def parse_forum(value: str) -> str | int:
    return int(value) if value.isdecimal() else value


def load_tb():
    try:
        import aiotieba as tb
    except ImportError as exc:
        raise SystemExit("aiotieba is not installed; run: pip install aiotieba") from exc
    return tb


def build_client_kwargs(tb: Any, args: argparse.Namespace) -> dict[str, Any]:
    account_json = args.account_json or os.environ.get("AIO_TIEBA_ACCOUNT_JSON")
    bduss = args.bduss or os.environ.get("AIO_TIEBA_BDUSS")
    stoken = args.stoken or os.environ.get("AIO_TIEBA_STOKEN")

    if account_json:
        payload = json.loads(Path(account_json).read_text())
        return {"account": tb.Account.from_dict(payload)}
    if bduss:
        kwargs: dict[str, Any] = {"BDUSS": bduss}
        if stoken:
            kwargs["STOKEN"] = stoken
        return kwargs
    return {}


def make_cookie_header(account: Any) -> str:
    pairs = []
    if getattr(account, "BDUSS", ""):
        pairs.append(("BDUSS", account.BDUSS))
    if getattr(account, "STOKEN", ""):
        pairs.append(("STOKEN", account.STOKEN))
    if not pairs:
        raise SystemExit("BDUSS is required")
    return "; ".join(f"{key}={value}" for key, value in pairs)


async def load_bsk_js(args: argparse.Namespace, session: aiohttp.ClientSession) -> str:
    if args.bsk_js:
        return Path(args.bsk_js).read_text()
    async with session.get(BSK_JS_URL) as resp:
        if resp.status != 200:
            raise RuntimeError(f"failed to download new_bsk.js: HTTP {resp.status}")
        return await resp.text()


def compute_bsk_with_node(tbs: str, bsk_js: str) -> str:
    node_src = f"""
global.window = global;
global.start = Date.now();
{bsk_js}
process.stdout.write(String(get_bsk_data({json.dumps(tbs)})));
"""
    proc = subprocess.run(
        ["node", "-e", node_src],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"failed to compute _BSK: {proc.stderr.strip()}")
    return proc.stdout.strip()


def image_to_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


async def upload_image(
    session: aiohttp.ClientSession,
    *,
    account: Any,
    image_path: Path,
) -> dict[str, Any]:
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://tieba.baidu.com",
        "Referer": "https://tieba.baidu.com/",
        "User-Agent": "Mozilla/5.0",
        "Cookie": make_cookie_header(account),
    }
    data = {"pic": image_to_base64(image_path)}
    params = {"type": "ajax", "r": str(random.random())}
    async with session.post(
        "https://tieba.baidu.com/mo/q/cooluploadpic",
        params=params,
        data=data,
        headers=headers,
    ) as resp:
        payload = await resp.json(content_type=None)
    if not isinstance(payload, dict) or not payload.get("imageInfo"):
        raise RuntimeError(f"cooluploadpic failed: {payload}")
    return payload


async def reply_with_images(args: argparse.Namespace) -> dict[str, Any]:
    tb = load_tb()
    client_kwargs = build_client_kwargs(tb, args)
    image_paths = [Path(p) for p in args.image]
    for path in image_paths:
        if not path.is_file():
            raise SystemExit(f"image file not found: {path}")

    async with tb.Client(**client_kwargs) as client:
        forum = parse_forum(args.forum)
        if isinstance(forum, int):
            forum_id = forum
            forum_name = str(await client.get_fname(forum_id))
        else:
            forum_name = forum
            forum_id = int(str(await client.get_fid(forum_name)))
        self_info = await client.get_self_info()
        account = client.account
        if not account.tbs:
            raise RuntimeError("failed to initialize tbs")
        nick_name = (
            args.nick_name
            or getattr(self_info, "nick_name", "")
            or getattr(self_info, "show_name", "")
            or getattr(self_info, "user_name", "")
        )

        async with aiohttp.ClientSession() as session:
            if args.bsk:
                bsk = args.bsk
            else:
                bsk_js = await load_bsk_js(args, session)
                bsk = compute_bsk_with_node(account.tbs, bsk_js)

            upload_results = []
            for image_path in image_paths:
                upload_results.append(await upload_image(session, account=account, image_path=image_path))
            upload_img_info = "|".join(item["imageInfo"] for item in upload_results)

            data = {
                "co": args.text,
                "_t": str(int(asyncio.get_running_loop().time() * 1000)),
                "tag": "11",
                "upload_img_info": upload_img_info,
                "fid": str(forum_id),
                "src": "1",
                "word": forum_name,
                "tbs": account.tbs,
                "z": str(args.tid),
                "lp": "6026",
                "nick_name": nick_name,
                "_BSK": bsk,
            }
            if args.pid:
                data["pid"] = str(args.pid)
            if args.floor:
                data["floor"] = str(args.floor)
            if args.lzl_id:
                data["lzl_id"] = str(args.lzl_id)

            referer = f"https://tieba.baidu.com/p/{args.tid}?lp=5028&mo_device=1&is_jingpost=0&pn={args.pn}&"
            now_ms = str(int(time.time() * 1000))
            headers = {
                "Accept": "application/json, text/plain, */*",
                "Host": "tieba.baidu.com",
                "Origin": "https://tieba.baidu.com",
                "Referer": referer,
                "User-Agent": "Mozilla/5.0",
                "X-Requested-With": "XMLHttpRequest",
                "Cookie": make_cookie_header(account),
            }
            params = {"_t": now_ms}
            data["_t"] = now_ms

            async with session.post(
                "https://tieba.baidu.com/mo/q/apubpost",
                params=params,
                data=data,
                headers=headers,
            ) as resp:
                payload = await resp.json(content_type=None)

    if not isinstance(payload, dict) or int(payload.get("no", -1)) != 0:
        raise RuntimeError(f"apubpost failed: {payload}")

    return {
        "ok": True,
        "tid": payload.get("data", {}).get("tid"),
        "pid": payload.get("data", {}).get("pid"),
        "forum_id": forum_id,
        "forum_name": forum_name,
        "nick_name": nick_name,
        "upload_img_info": upload_img_info,
        "uploaded_images": upload_results,
        "bsk": bsk,
        "raw": payload,
    }


def main() -> None:
    args = parse_args()
    result = asyncio.run(reply_with_images(args))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
