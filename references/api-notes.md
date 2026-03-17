# API Notes

Primary sources:

- Reference site: `https://aiotieba.cc/ref/client.html`
- Upstream client source: `https://raw.githubusercontent.com/lumina37/aiotieba/master/aiotieba/client.py`

This skill's CLI is intentionally thin. It maps almost directly to these upstream methods.

## Read Operations

```python
async def get_self_info(self, require: ReqUInfo = ReqUInfo.ALL) -> UserInfo
async def get_threads(self, fname_or_fid: str | int, /, pn: int = 1, *, rn: int = 30, sort: ThreadSortType = ThreadSortType.REPLY, is_good: bool = False)
async def get_posts(self, tid: int, /, pn: int = 1, *, rn: int = 30, sort: PostSortType = PostSortType.ASC, only_thread_author: bool = False, with_comments: bool = False, comment_sort_by_agree: bool = True, comment_rn: int = 4)
```

## Write Operations

```python
async def add_thread(
    self,
    fname_or_fid: str | int,
    /,
    title: str,
    content: str = "",
    *,
    image_paths: list[str] | None = None,
    is_origin_image: bool = False,
    is_private: bool = False,
)
async def add_post(
    self,
    fname_or_fid: str | int,
    /,
    tid: int,
    content: str,
    *,
    image_paths: list[str] | None = None,
    is_origin_image: bool = False,
)
async def follow_forum(self, fname_or_fid: str | int)
async def unfollow_forum(self, fname_or_fid: str | int)
async def sign_forum(self, fname_or_fid: str | int)
async def sign_forums(self)
```

## Moderation Operations

```python
async def block(self, fname_or_fid: str | int, /, id_: str | int, *, day: int = 1, reason: str = "")
async def unblock(self, fname_or_fid: str | int, /, id_: str | int)
async def del_thread(self, fname_or_fid: str | int, /, tid: int)
async def del_post(self, fname_or_fid: str | int, /, tid: int, pid: int)
async def recover_thread(self, fname_or_fid: str | int, /, tid: int)
async def recover_post(self, fname_or_fid: str | int, /, pid: int)
async def good(self, fname_or_fid: str | int, /, tid: int, *, cname: str = "")
async def top(self, fname_or_fid: str | int, /, tid: int, *, is_vip: bool = False)
async def move(self, fname_or_fid: str | int, /, tid: int, *, to_tab_id: int, from_tab_id: int = 0)
```

## Notes For The CLI

- If `aiotieba` is missing, install `git+https://github.com/winne-w/aiotieba.git@feature/image-posting` or clone `https://github.com/winne-w/aiotieba/tree/feature/image-posting` and use `--aiotieba-src`.
- `--aiotieba-src /path/to/repo` or `AIO_TIEBA_SRC=/path/to/repo` prepends a local checkout to `sys.path`, so the CLI imports that branch instead of the installed package.
- Credential resolution order is: `--account-json`, `AIO_TIEBA_ACCOUNT_JSON`, `$XDG_CONFIG_HOME/aiotieba-tieba-ops/account.json` or `~/.config/aiotieba-tieba-ops/account.json`, then `AIO_TIEBA_BDUSS`.
- `block` accepts `user_id`, `user_name`, or `portrait`; upstream prefers `portrait`.
- `unblock` accepts `user_id`, `user_name`, or `portrait`; upstream prefers `user_id`.
- `add-thread` can pass repeated local image paths through `image_paths`.
- `add-thread --origin-image` maps to `is_origin_image=True`.
- `add-thread --private` maps to `is_private=True`.
- `reply` can pass repeated local image paths through `image_paths`.
- `reply --origin-image` maps to `is_origin_image=True`.
- `get_threads` sorts by `reply`, `create`, `hot`, or `follow`.
- `get_posts` sorts by `asc`, `desc`, or `hot`.
- Forum arguments can usually be a forum name or fid. The CLI exposes this as `--forum`.
- `recover-post` only needs `forum` and `pid`.
