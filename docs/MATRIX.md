# call-in-tmux Matrix

Self-contained **host → engine** routing. Runners live only under this repo's `engines/`.

## Enabled now

| From \\ To | codex | cursor | kimi |
| --- | --- | --- | --- |
| **claude** | ✅ `engines/codex` | ✅ `engines/cursor` | ✅ `engines/kimi/cc` |
| **codex** | — | ✅ `engines/cursor` | ✅ `engines/kimi/cx` |
| **kimi** | — | ✅ `engines/cursor` | — |

## Extending

1. Vendor or write a runner under `engines/<name>/`.
2. Point `config/matrix.json` → `engines.<name>.runners`.
3. Add `[host, engine]` to `edges`.
4. `bash install.sh --hooks-only` if the engine needs hooks.
5. `call-in-tmux matrix` must resolve without any path outside this repo (except `$HOME` data dirs).
