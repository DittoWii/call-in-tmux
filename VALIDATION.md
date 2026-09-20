# Validation

**2026-09-21** — self-contained vendoring.

| Check | Result |
| --- | --- |
| Unit tests | 5 passed |
| Matrix runners | All resolve under `call-in-tmux/engines/` only (no sibling cx/cc paths) |
| Install | CLI + `call` skills + cursor/kimi-cc/kimi-cx hooks |
| Codex cleanup | Removed `cx-kimi-tmux@personal` plugin and `~/.agents/skills/cursor` |
| Doctors | cursor hooks check OK; kimi cc/cx doctor green |

Runtime no longer requires checkouts of `cx-cursor-tmux`, `cx-kimi-tmux`, or `cc-kimi-tmux`.
