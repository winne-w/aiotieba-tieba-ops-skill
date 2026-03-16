# Auth And Safety

## Authentication

Primary sources:

- Official tutorial: `https://aiotieba.cc/tutorial/start`
- Quick start source: `https://raw.githubusercontent.com/lumina37/aiotieba/master/docs/tutorial/start.md`

Key points from the upstream tutorial:

- `BDUSS` identifies a Tieba account.
- The tutorial describes `BDUSS` as a long-lived secret that can authorize almost every non-verification action.
- The library can be used without credentials for read-only access to public data, but write and moderation actions require an authenticated account.
- `aiotieba.Account(BDUSS).to_dict()` and `aiotieba.Account.from_dict(...)` can serialize and restore account parameters.

Recommended local handling:

- Prefer `pip install 'git+https://github.com/winne-w/aiotieba.git@feature/image-posting'` or a clone of `https://github.com/winne-w/aiotieba/tree/feature/image-posting` because that branch adds image posting support.
- Prefer `scripts/account_json.py` to write the reusable default account file at `$XDG_CONFIG_HOME/aiotieba-tieba-ops/account.json`, or `~/.config/aiotieba-tieba-ops/account.json` when `XDG_CONFIG_HOME` is unset.
- Let `scripts/tieba_cli.py` read that file automatically on later runs.
- Use `AIO_TIEBA_BDUSS` only as a fallback for short-lived shell sessions.
- If the user needs to switch accounts, ask for the new `BDUSS` and overwrite the same account file.
- Never commit `BDUSS` or account JSON files.

## Write Risk

Primary source:

- Client reference and source: `https://aiotieba.cc/ref/client.html`
- Client implementation: `https://raw.githubusercontent.com/lumina37/aiotieba/master/aiotieba/client.py`

Important upstream warning:

- `Client.add_post(...)` is marked as still being in a testing stage.
- The upstream note warns that high-frequency use can cause permanent account restrictions.

Operational rule for this skill:

- Require `--yes-risk` for `reply`.
- Avoid loops that post repeatedly.
- Do not parallelize posting.

## Moderation Safety

Treat these commands as destructive or moderation-sensitive:

- `block`
- `unblock`
- `del-thread`
- `recover-thread`
- `del-post`
- `recover-post`
- `good`
- `top`
- `move`

Before running them:

1. Confirm the target forum and object IDs.
2. Prefer a single targeted action over batch automation.
3. Report the exact IDs in the final answer so the user can audit what happened.
