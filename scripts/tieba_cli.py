#!/usr/bin/env python3
"""Unified aiotieba CLI for Tieba read, write, and moderation tasks."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any


INSTALL_HINT = (
    "aiotieba is not installed; install the image-posting branch with: "
    "pip install 'git+https://github.com/winne-w/aiotieba.git@feature/image-posting' "
    "or clone https://github.com/winne-w/aiotieba/tree/feature/image-posting "
    "and pass --aiotieba-src /path/to/aiotieba"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bduss", help="BDUSS token. Falls back to AIO_TIEBA_BDUSS.")
    parser.add_argument(
        "--aiotieba-src",
        help="Local aiotieba source tree to import first. Falls back to AIO_TIEBA_SRC.",
    )
    parser.add_argument(
        "--account-json",
        help="Path to a serialized aiotieba Account JSON file. Falls back to AIO_TIEBA_ACCOUNT_JSON.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("me", help="Show the current authenticated user.")

    list_threads = subparsers.add_parser("list-threads", help="List forum threads.")
    add_forum_arg(list_threads)
    list_threads.add_argument("--pn", type=int, default=1)
    list_threads.add_argument("--rn", type=int, default=30)
    list_threads.add_argument("--sort", choices=["reply", "create", "hot", "follow"], default="reply")
    list_threads.add_argument("--good", action="store_true", help="Read the forum's good threads.")

    list_posts = subparsers.add_parser("list-posts", help="List posts in a thread.")
    list_posts.add_argument("--tid", required=True, type=int)
    list_posts.add_argument("--pn", type=int, default=1)
    list_posts.add_argument("--rn", type=int, default=30)
    list_posts.add_argument("--sort", choices=["asc", "desc", "hot"], default="asc")
    list_posts.add_argument("--thread-author-only", action="store_true")
    list_posts.add_argument("--with-comments", action="store_true")
    list_posts.add_argument("--comment-rn", type=int, default=4)
    list_posts.add_argument(
        "--comment-sort",
        choices=["agree", "time"],
        default="agree",
        help="Only applies when --with-comments is set.",
    )

    reply = subparsers.add_parser("reply", help="Reply to a thread.")
    add_forum_arg(reply)
    reply.add_argument("--tid", required=True, type=int)
    reply.add_argument("--content", required=True)
    reply.add_argument(
        "--image",
        action="append",
        default=[],
        help="Local image path. Repeat this flag to attach multiple images.",
    )
    reply.add_argument(
        "--origin-image",
        action="store_true",
        help="Upload images as original images when supported by aiotieba.",
    )
    reply.add_argument(
        "--yes-risk",
        action="store_true",
        help="Required acknowledgement for add_post risk documented by aiotieba.",
    )

    add_thread = subparsers.add_parser("add-thread", help="Create a new thread, optionally with images.")
    add_forum_arg(add_thread)
    add_thread.add_argument("--title", default="", help="Thread title. Leave empty for an untitled post.")
    add_thread.add_argument("--content", default="", help="Thread body text.")
    add_thread.add_argument(
        "--image",
        action="append",
        default=[],
        help="Local image path. Repeat this flag to attach multiple images.",
    )
    add_thread.add_argument(
        "--origin-image",
        action="store_true",
        help="Upload images as original images when supported by aiotieba.",
    )
    add_thread.add_argument(
        "--private",
        action="store_true",
        help="Create the thread as private/hidden-to-self when supported by the forum.",
    )

    sign_forum = subparsers.add_parser("sign-forum", help="Sign a single forum.")
    add_forum_arg(sign_forum)

    subparsers.add_parser("sign-forums", help="Sign all eligible followed forums.")

    follow_forum = subparsers.add_parser("follow-forum", help="Follow a forum.")
    add_forum_arg(follow_forum)

    unfollow_forum = subparsers.add_parser("unfollow-forum", help="Unfollow a forum.")
    add_forum_arg(unfollow_forum)

    block = subparsers.add_parser("block", help="Block a user in a forum.")
    add_forum_arg(block)
    block.add_argument("--user", required=True, help="portrait, user_name, or user_id")
    block.add_argument("--day", type=int, default=1)
    block.add_argument("--reason", default="")

    unblock = subparsers.add_parser("unblock", help="Unblock a user in a forum.")
    add_forum_arg(unblock)
    unblock.add_argument("--user", required=True, help="user_id, user_name, or portrait")

    del_thread = subparsers.add_parser("del-thread", help="Delete a thread.")
    add_forum_arg(del_thread)
    del_thread.add_argument("--tid", required=True, type=int)

    recover_thread = subparsers.add_parser("recover-thread", help="Recover a deleted thread.")
    add_forum_arg(recover_thread)
    recover_thread.add_argument("--tid", required=True, type=int)

    del_post = subparsers.add_parser("del-post", help="Delete a post.")
    add_forum_arg(del_post)
    del_post.add_argument("--tid", required=True, type=int)
    del_post.add_argument("--pid", required=True, type=int)

    recover_post = subparsers.add_parser("recover-post", help="Recover a deleted post.")
    add_forum_arg(recover_post)
    recover_post.add_argument("--pid", required=True, type=int)

    good = subparsers.add_parser("good", help="Mark a thread as good.")
    add_forum_arg(good)
    good.add_argument("--tid", required=True, type=int)
    good.add_argument("--cname", default="", help="Good-thread category name.")

    top = subparsers.add_parser("top", help="Top a thread.")
    add_forum_arg(top)
    top.add_argument("--tid", required=True, type=int)
    top.add_argument("--vip", action="store_true", help="Use VIP top if the account has permission.")

    move = subparsers.add_parser("move", help="Move a thread to a tab.")
    add_forum_arg(move)
    move.add_argument("--tid", required=True, type=int)
    move.add_argument("--to-tab-id", required=True, type=int)
    move.add_argument("--from-tab-id", type=int, default=0)

    return parser.parse_args()


def add_forum_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--forum",
        required=True,
        help="Forum name or fid. Pass a decimal number to use fid.",
    )


def parse_forum(value: str) -> str | int:
    return int(value) if value.isdecimal() else value


def load_tb():
    src = os.environ.get("AIO_TIEBA_SRC")
    if src:
        sys.path.insert(0, src)
    try:
        import aiotieba as tb
    except ImportError as exc:
        raise SystemExit(INSTALL_HINT) from exc
    return tb


def default_account_json_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        return Path(config_home).expanduser() / "aiotieba-tieba-ops" / "account.json"
    return Path.home() / ".config" / "aiotieba-tieba-ops" / "account.json"


def resolve_account_json_path(explicit_path: str | None) -> Path | None:
    if explicit_path:
        return Path(explicit_path).expanduser()

    env_path = os.environ.get("AIO_TIEBA_ACCOUNT_JSON")
    if env_path:
        return Path(env_path).expanduser()

    default_path = default_account_json_path()
    if default_path.is_file():
        return default_path

    return None


def build_client_kwargs(tb: Any, args: argparse.Namespace) -> dict[str, Any]:
    account_json = resolve_account_json_path(args.account_json)
    bduss = args.bduss or os.environ.get("AIO_TIEBA_BDUSS")

    if account_json:
        payload = json.loads(account_json.read_text())
        return {"account": tb.Account.from_dict(payload)}
    if bduss:
        return {"BDUSS": bduss}
    return {}


def bool_result(result: Any) -> dict[str, Any]:
    return {"ok": bool(result), "repr": str(result)}


def serialize_user(user: Any) -> dict[str, Any]:
    data: dict[str, Any] = {"repr": str(user)}
    for field in ("user_id", "user_name", "nick_name", "portrait"):
        if hasattr(user, field):
            data[field] = getattr(user, field)
    return data


def serialize_threads(threads: Any) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for thread in threads:
        items.append(
            {
                "tid": getattr(thread, "tid", None),
                "text": getattr(thread, "text", None),
                "reply_num": getattr(thread, "reply_num", None),
                "author": getattr(thread, "author_name", None),
                "is_good": getattr(thread, "is_good", None),
                "share_url": getattr(thread, "share_url", None),
            }
        )
    return {"count": len(items), "threads": items}


def serialize_posts(posts: Any) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for post in posts:
        item: dict[str, Any] = {
            "pid": getattr(post, "pid", None),
            "tid": getattr(post, "tid", None),
            "text": getattr(post, "text", None),
            "author": getattr(post, "author_name", None),
            "reply_num": getattr(post, "reply_num", None),
        }
        comments = getattr(post, "comments", None)
        if comments is not None:
            item["comments"] = [
                {
                    "pid": getattr(comment, "pid", None),
                    "text": getattr(comment, "text", None),
                    "author": getattr(comment, "author_name", None),
                }
                for comment in comments
            ]
        items.append(item)
    return {"count": len(items), "posts": items}


async def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.aiotieba_src:
        sys.path.insert(0, args.aiotieba_src)
    tb = load_tb()
    client_kwargs = build_client_kwargs(tb, args)

    async with tb.Client(**client_kwargs) as client:
        if args.command == "me":
            return serialize_user(await client.get_self_info())

        if args.command == "list-threads":
            sort = {
                "reply": tb.ThreadSortType.REPLY,
                "create": tb.ThreadSortType.CREATE,
                "hot": tb.ThreadSortType.HOT,
                "follow": tb.ThreadSortType.FOLLOW,
            }[args.sort]
            threads = await client.get_threads(
                parse_forum(args.forum),
                args.pn,
                rn=args.rn,
                sort=sort,
                is_good=args.good,
            )
            return serialize_threads(threads)

        if args.command == "list-posts":
            sort = {
                "asc": tb.PostSortType.ASC,
                "desc": tb.PostSortType.DESC,
                "hot": tb.PostSortType.HOT,
            }[args.sort]
            posts = await client.get_posts(
                args.tid,
                args.pn,
                rn=args.rn,
                sort=sort,
                only_thread_author=args.thread_author_only,
                with_comments=args.with_comments,
                comment_sort_by_agree=args.comment_sort == "agree",
                comment_rn=args.comment_rn,
            )
            return serialize_posts(posts)

        if args.command == "reply":
            if not args.yes_risk:
                raise SystemExit("reply requires --yes-risk because aiotieba documents posting risk")
            result = await client.add_post(
                parse_forum(args.forum),
                args.tid,
                args.content,
                image_paths=args.image,
                is_origin_image=args.origin_image,
            )
            return bool_result(result)

        if args.command == "add-thread":
            result = await client.add_thread(
                parse_forum(args.forum),
                args.title,
                args.content,
                image_paths=args.image,
                is_origin_image=args.origin_image,
                is_private=args.private,
            )
            return bool_result(result)

        if args.command == "sign-forum":
            return bool_result(await client.sign_forum(parse_forum(args.forum)))

        if args.command == "sign-forums":
            return bool_result(await client.sign_forums())

        if args.command == "follow-forum":
            return bool_result(await client.follow_forum(parse_forum(args.forum)))

        if args.command == "unfollow-forum":
            return bool_result(await client.unfollow_forum(parse_forum(args.forum)))

        if args.command == "block":
            return bool_result(
                await client.block(parse_forum(args.forum), parse_user_arg(args.user), day=args.day, reason=args.reason)
            )

        if args.command == "unblock":
            return bool_result(await client.unblock(parse_forum(args.forum), parse_user_arg(args.user)))

        if args.command == "del-thread":
            return bool_result(await client.del_thread(parse_forum(args.forum), args.tid))

        if args.command == "recover-thread":
            return bool_result(await client.recover_thread(parse_forum(args.forum), args.tid))

        if args.command == "del-post":
            return bool_result(await client.del_post(parse_forum(args.forum), args.tid, args.pid))

        if args.command == "recover-post":
            return bool_result(await client.recover_post(parse_forum(args.forum), args.pid))

        if args.command == "good":
            return bool_result(await client.good(parse_forum(args.forum), args.tid, cname=args.cname))

        if args.command == "top":
            return bool_result(await client.top(parse_forum(args.forum), args.tid, is_vip=args.vip))

        if args.command == "move":
            return bool_result(
                await client.move(
                    parse_forum(args.forum),
                    args.tid,
                    to_tab_id=args.to_tab_id,
                    from_tab_id=args.from_tab_id,
                )
            )

    raise AssertionError(f"unhandled command: {args.command}")


def parse_user_arg(value: str) -> str | int:
    return int(value) if value.isdecimal() else value


def main() -> int:
    args = parse_args()
    try:
        payload = asyncio.run(run(args))
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    except Exception as exc:  # pragma: no cover
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
