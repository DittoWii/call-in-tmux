# Validation

**2026-09-21** — self-contained install + Codex/Kimi smokes (Claude skipped by request).

| Check | Result |
| --- | --- |
| Unit tests | 5 passed |
| Matrix runners | All under `call-in-tmux/engines/` |
| Install (codex+kimi) | CLI + `$call` skills; cursor + kimi-cx hooks |
| Codex→Cursor smoke | exit 0; `CALL_IN_TMUX_CODEX_CURSOR_OK`; `.done` |
| Codex→Kimi smoke | exit 0; `CALL_IN_TMUX_CODEX_KIMI_OK`; `.done` |
| Kimi→Cursor smoke | exit 0; `CALL_IN_TMUX_KIMI_CURSOR_OK`; `.done` |
| Claude | Not installed / not tested |
| Cleanup | Removed Claude `call` + old `~/.claude/skills/kimi`; removed kimi-cc hooks; no Codex `cx-*` plugin/skill |

Artifacts under `.runs/` (gitignored).
