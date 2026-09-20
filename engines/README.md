# Vendored engines

These directories are **copies** of the specialized tmux dispatchers. `call-in-tmux` must run without sibling `cx-*` / `cc-*` repositories.

| Path | Origin | Used when |
| --- | --- | --- |
| `codex/codex-tmux` | Claude Code `codex` skill / cc-codex-tmux lineage | host → codex |
| `cursor/cursor-tmux` | cx-cursor-tmux | host → cursor |
| `cursor/configure.py` | cx-cursor-tmux | installs `~/.cursor/hooks.json` markers `call-in-tmux-cursor` |
| `kimi/cc/kimi-tmux` | cc-kimi-tmux | claude → kimi (and default) |
| `kimi/cx/kimi-tmux` | cx-kimi-tmux | codex → kimi |
| `kimi/cx/configure.py` | cx-kimi-tmux | installs Kimi hooks marker `call-in-tmux-kimi-cx` |
| `kimi/cc/install.sh` | cc-kimi-tmux | installs Kimi hooks marker `call-in-tmux-kimi-cc` |

Refresh from upstream by re-copying and re-applying the small path/marker patches documented in `UPSTREAM.md`.
