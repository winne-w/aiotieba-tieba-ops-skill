---
name: aiotieba-tieba-ops
description: Use aiotieba to operate Baidu Tieba with local scripts. Trigger this skill whenever the user wants to operate Tieba, including browsing forums or threads, reading replies, creating threads including posts with local images, replying to a thread, signing forums, following or unfollowing forums, or performing bawu moderation actions such as delete, recover, good, top, move, block, and unblock.
---

# AIOTieba Tieba Ops

Use the bundled scripts instead of rewriting client code. This skill is optimized for repeatable Tieba reads, account setup, and bawu actions with `aiotieba`.

## Quick Start

Install the dependency first:

```bash
pip install 'git+https://github.com/winne-w/aiotieba.git@feature/image-posting'
```

If the user has not installed `aiotieba` yet, guide them to one of these setup paths before any operation that needs the library:

```bash
pip install 'git+https://github.com/winne-w/aiotieba.git@feature/image-posting'
```

Or clone the branch locally:

```bash
git clone --branch feature/image-posting https://github.com/winne-w/aiotieba.git
```

Prefer that branch because it includes image posting support for threads and replies.

If the user has a local checkout instead of an installed package, point the CLI at that source tree:

```bash
export AIO_TIEBA_SRC=/path/to/aiotieba
python scripts/tieba_cli.py me
```

Or pass it per command:

```bash
python scripts/tieba_cli.py --aiotieba-src /path/to/aiotieba me
```

For authenticated actions, prefer the default local account file:

```bash
python scripts/account_json.py --bduss '...'
python scripts/tieba_cli.py me
```

This writes the account to `$XDG_CONFIG_HOME/aiotieba-tieba-ops/account.json`, or `~/.config/aiotieba-tieba-ops/account.json` when `XDG_CONFIG_HOME` is unset. The CLI reuses it automatically on later runs.

You can still override the path explicitly:

```bash
python scripts/account_json.py --bduss '...' --output /tmp/tieba-account.json
python scripts/tieba_cli.py --account-json /tmp/tieba-account.json me
```

## Workflow

1. Read [references/auth-and-safety.md](./references/auth-and-safety.md) before any write or moderation action.
2. If `aiotieba` is missing locally, ask the user to install `git+https://github.com/winne-w/aiotieba.git@feature/image-posting` or clone `https://github.com/winne-w/aiotieba/tree/feature/image-posting` and use that checkout.
3. Read [references/api-notes.md](./references/api-notes.md) if you need exact method coverage or argument shapes.
4. For any authenticated operation, check whether the default account file exists at `$XDG_CONFIG_HOME/aiotieba-tieba-ops/account.json` or `~/.config/aiotieba-tieba-ops/account.json`.
5. If it does not exist, ask the user for `BDUSS`, then run `python scripts/account_json.py --bduss '...'` to save it before continuing.
6. If the user wants to switch accounts, ask for the new `BDUSS`, then rerun `python scripts/account_json.py --bduss '...'` to overwrite the same file.
7. Use `scripts/tieba_cli.py` for normal operations. It loads `--account-json`, then `AIO_TIEBA_ACCOUNT_JSON`, then the default account file, and only falls back to `AIO_TIEBA_BDUSS`.
8. If the task depends on branch-only features or the user cloned the repo instead of installing it, set `AIO_TIEBA_SRC` or pass `--aiotieba-src` so the CLI imports that local checkout first.
9. Only fall back to ad hoc Python if the CLI does not cover the required method.

## Commands

The main script supports these subcommands:

- `me`
- `list-threads`
- `list-posts`
- `add-thread`
- `reply`
- `sign-forum`
- `sign-forums`
- `follow-forum`
- `unfollow-forum`
- `block`
- `unblock`
- `del-thread`
- `recover-thread`
- `del-post`
- `recover-post`
- `good`
- `top`
- `move`

Prefer forum names when you have them. `aiotieba` accepts forum name or fid for many APIs, and the CLI forwards the value directly.

## Safe Operating Notes

- Treat `BDUSS` as a long-lived secret. Never print it in the final answer or store it in the skill files.
- Store reusable credentials in the user config directory, not in the skill directory.
- `add-thread` can attach local images through upstream `aiotieba.Client.add_thread(..., image_paths=...)`. Keep image paths local and verify the files exist before posting.
- Require explicit user intent before destructive moderation actions such as delete, recover, block, unban, move, or top.
- Treat `reply` as higher risk. The upstream project explicitly warns that high-frequency use can cause permanent account restrictions. Use `--yes-risk` to make that choice explicit.
- When a command fails, surface the exact API error and stop. Do not retry destructive actions blindly.

## Examples

Inspect a forum:

```bash
python scripts/tieba_cli.py list-threads --forum linux --rn 10
```

Inspect replies in a thread:

```bash
python scripts/tieba_cli.py list-posts --tid 1234567890 --with-comments
```

Create a thread with images:

```bash
python scripts/tieba_cli.py add-thread --forum linux --title 'kernel notes' --content 'see attached' --image ./one.jpg --image ./two.png
```

Create an untitled private image post:

```bash
python scripts/tieba_cli.py add-thread --forum linux --content 'internal note' --image ./note.jpg --private
```

Reply to a thread:

```bash
python scripts/tieba_cli.py reply --forum linux --tid 1234567890 --content 'ack' --yes-risk
```

Block a user for one day:

```bash
python scripts/tieba_cli.py block --forum linux --user tb.1.example.portrait --day 1 --reason spam
```

Delete and recover:

```bash
python scripts/tieba_cli.py del-thread --forum linux --tid 1234567890
python scripts/tieba_cli.py recover-thread --forum linux --tid 1234567890
```

## Resources

- `scripts/tieba_cli.py`: unified CLI for reading, posting threads with or without images, replying, signing, following, and moderation.
- `scripts/account_json.py`: save or update the reusable `aiotieba.Account` JSON file from a BDUSS token.
- `references/auth-and-safety.md`: authentication and risk notes distilled from the official tutorial.
- `references/api-notes.md`: exact upstream methods and argument signatures used by the CLI.
