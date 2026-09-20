# call-in-tmux

> One self-contained doorway for agent-to-agent calls over tmux. Say「调用 cursor / 让 kimi / 派给 codex」— no separate `cx-*` / `cc-*` skills required.

Engine scripts are **vendored** under `engines/`. This repo runs on its own after `install.sh`.

## Supported edges

```text
claude ──► codex | cursor | kimi
codex  ──► cursor | kimi
kimi   ──► cursor
```

Source of truth: `config/matrix.json`. Details: [docs/MATRIX.md](docs/MATRIX.md).

## Install

```bash
cd /path/to/call-in-tmux
bash install.sh --all-hosts
call-in-tmux matrix
```

This installs:

1. `~/.local/bin/call-in-tmux`
2. Host skill `call` for Claude / Codex / Kimi
3. Engine hooks from **this repo** (`engines/cursor`, `engines/kimi/cc`, `engines/kimi/cx`)

Do **not** install Codex plugins `cx-kimi-tmux` / `cx-cursor-tmux` as separate skills — use `$call` only.

## Usage

```bash
CALL_IN_TMUX_HOST=codex call-in-tmux to cursor \
  -t review -C /abs/project -o /abs/out.report.md --brief /abs/out.brief.md --timeout 900

call-in-tmux matrix
call-in-tmux resolve kimi --from codex
```

In a new host session:

```text
调用 cursor 审查……
让 kimi 补测试
派给 codex 做并发审查
```

## Layout

```text
bin/call-in-tmux          router CLI
config/matrix.json        edges + runners (all under engines/)
engines/codex/            vendored codex-tmux
engines/cursor/           vendored cursor-tmux + hooks installer
engines/kimi/cc/          vendored cc-kimi dispatcher + hooks
engines/kimi/cx/          vendored cx-kimi dispatcher + hooks
hosts/{claude,codex,kimi} thin skills (wake semantics only)
```

## Tests

```bash
python3 -m unittest discover -s tests -v
bash -n bin/call-in-tmux lib/common.sh
```

## License

MIT — see [LICENSE](LICENSE). Vendored engine copyrights remain with their original authors; see [UPSTREAM.md](UPSTREAM.md).
