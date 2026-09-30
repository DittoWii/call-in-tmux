# Vendored engines

These directories are **copies** of the specialized tmux dispatchers. `call-in-tmux` must run without sibling `cx-*` / `cc-*` repositories.

| Path | Origin | Used when |
| --- | --- | --- |
| `codex/codex-tmux` | Claude Code `codex` skill / cc-codex-tmux lineage | host → codex |
| `cursor/cursor-tmux` | cx-cursor-tmux | host → cursor |
| `cursor/configure.py` | cx-cursor-tmux | installs `~/.cursor/hooks.json` markers `call-in-tmux-cursor` |
| `kimi/cx/kimi-tmux` | cx-kimi-tmux | every host → kimi |
| `kimi/cx/configure.py` | cx-kimi-tmux | installs Kimi hooks marker `call-in-tmux-kimi-cx` |
| `kimi/cc/*` | cc-kimi-tmux | **legacy, unused**: older fork of the same dispatcher; `uninstall.sh` still strips its old `call-in-tmux-kimi-cc` hook block |

Refresh from upstream by re-copying and re-applying the small path/marker patches documented in `UPSTREAM.md`.
