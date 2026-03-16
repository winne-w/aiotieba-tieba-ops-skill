#!/usr/bin/env python3
"""Reply to a Tieba thread with an image via the observed PC web flow.

This script intentionally reuses aiotieba for account/bootstrap work and
performs the image upload + PC reply requests with aiohttp.

The PC web endpoints require extra anti-abuse fields such as ``sign``,
``jt``, and ``Acs-Token``. This demo accepts them as explicit arguments
because they are not exposed by aiotieba's public API.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import mimetypes
import os
import secrets
from pathlib import Path
from typing import Any
from urllib.parse import quote

import aiohttp


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
    parser.add_argument("--image", required=True, help="Local image path to upload.")
    parser.add_argument("--image-width", type=int, help="Override width used in #(pic,...) content.")
    parser.add_argument("--image-height", type=int, help="Override height used in #(pic,...) content.")
    parser.add_argument("--url", help="Optional URL to embed as #(url,...).")
    parser.add_argument(
        "--url-title",
        default="网页链接",
        help="Display label for the optional #(url,...) fragment.",
    )
    parser.add_argument("--upload-sign", required=True, help="PC web sign for /c/s/uploadPicture_pc.")
    parser.add_argument("--post-sign", required=True, help="PC web sign for /c/c/post/add_pc.")
    parser.add_argument("--acs-token", required=True, help="Acs-Token request header for /c/c/post/add_pc.")
    parser.add_argument("--jt", required=True, help="jt form field required by /c/c/post/add_pc.")
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


def encode_url_fragment(url: str, title: str) -> str:
    # Tieba PC content stores the URL itself percent-encoded once inside the fragment.
    return f"#(url,0,{quote(url, safe='')},{quote(title, safe='')})"


def build_content(text: str, *, url: str | None, url_title: str, pic_id: str, width: int, height: int) -> str:
    fragments = [text]
    if url:
        fragments.append(encode_url_fragment(url, url_title))
    fragments.append(f"#(pic,{pic_id},{width},{height})")
    return "".join(fragments)


def build_resource_id() -> str:
    # The browser request used a 10-hex prefix + "/" + 22-hex suffix.
    return f"{secrets.token_hex(5)}/{secrets.token_hex(11)}"


def make_cookie_header(account: Any) -> str:
    pairs = []
    if getattr(account, "BDUSS", ""):
        pairs.append(("BDUSS", account.BDUSS))
    if getattr(account, "STOKEN", ""):
        pairs.append(("STOKEN", account.STOKEN))
    if not pairs:
        raise SystemExit("BDUSS is required")
    return "; ".join(f"{key}={value}" for key, value in pairs)


async def upload_picture(
    session: aiohttp.ClientSession,
    *,
    account: Any,
    tbs: str,
    image_path: Path,
    upload_sign: str,
) -> tuple[str, int, int]:
    content_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
    image_bytes = image_path.read_bytes()

    data = aiohttp.FormData()
    data.add_field("resourceId", build_resource_id())
    data.add_field("isFinish", "1")
    data.add_field("saveOrigin", "1")
    data.add_field("size", str(len(image_bytes)))
    data.add_field("width", "0")
    data.add_field("height", "0")
    data.add_field("chunkNo", "1")
    data.add_field("pic_water_type", "3")
    data.add_field("chunk", image_bytes, filename=image_path.name, content_type=content_type)
    data.add_field("tbs", tbs)
    data.add_field("subapp_type", "pc")
    data.add_field("_client_type", "20")
    data.add_field("sign", upload_sign)

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://tieba.baidu.com",
        "Referer": "https://tieba.baidu.com/",
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Cookie": make_cookie_header(account),
    }

    async with session.post("https://tieba.baidu.com/c/s/uploadPicture_pc", data=data, headers=headers) as resp:
        payload = await resp.json(content_type=None)

    if str(payload.get("error_code")) != "0":
        raise RuntimeError(f"uploadPicture_pc failed: {payload}")

    pic_id = str(payload["picId"])
    origin_pic = payload.get("picInfo", {}).get("originPic", {})
    width = int(origin_pic.get("width") or 0)
    height = int(origin_pic.get("height") or 0)
    return pic_id, width, height


async def reply_with_image(args: argparse.Namespace) -> dict[str, Any]:
    tb = load_tb()
    client_kwargs = build_client_kwargs(tb, args)
    image_path = Path(args.image)
    if not image_path.is_file():
        raise SystemExit(f"image file not found: {image_path}")

    async with tb.Client(**client_kwargs) as client:
        await client.get_self_info()
        account = client.account
        if not account.tbs:
            raise RuntimeError("failed to initialize tbs")

        forum = parse_forum(args.forum)
        fid = forum if isinstance(forum, int) else await client.get_fid(forum)
        forum_name = forum if isinstance(forum, str) else await client.get_fname(fid)
        self_info = await client.get_self_info()
        name_show = getattr(self_info, "show_name", "") or getattr(self_info, "nick_name", "")

        async with aiohttp.ClientSession() as session:
            pic_id, uploaded_width, uploaded_height = await upload_picture(
                session,
                account=account,
                tbs=account.tbs,
                image_path=image_path,
                upload_sign=args.upload_sign,
            )

            width = args.image_width or uploaded_width
            height = args.image_height or uploaded_height
            if width <= 0 or height <= 0:
                raise RuntimeError("image width/height are required; pass --image-width/--image-height")

            content = build_content(
                args.text,
                url=args.url,
                url_title=args.url_title,
                pic_id=pic_id,
                width=width,
                height=height,
            )

            headers = {
                "Accept": "application/json, text/plain, */*",
                "Acs-Token": args.acs_token,
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "Origin": "https://tieba.baidu.com",
                "Referer": f"https://tieba.baidu.com/p/{args.tid}",
                "User-Agent": "Mozilla/5.0",
                "X-Requested-With": "XMLHttpRequest",
                "Cookie": make_cookie_header(account),
            }

            data = {
                "tid": str(args.tid),
                "kw": str(forum_name),
                "fid": str(fid),
                "name_show": name_show,
                "content": content,
                "quote_id": "",
                "repostid": "",
                "jt": args.jt,
                "tbs": account.tbs,
                "subapp_type": "pc",
                "_client_type": "20",
                "sign": args.post_sign,
            }

            async with session.post(
                "https://tieba.baidu.com/c/c/post/add_pc",
                data=data,
                headers=headers,
            ) as resp:
                payload = await resp.json(content_type=None)

    if str(payload.get("error_code")) != "0":
        raise RuntimeError(f"post/add_pc failed: {payload}")

    return {
        "ok": True,
        "tid": payload.get("tid"),
        "pid": payload.get("pid"),
        "pic_id": pic_id,
        "content": content,
        "raw": payload,
    }


def main() -> None:
    args = parse_args()
    result = asyncio.run(reply_with_image(args))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
