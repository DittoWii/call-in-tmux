# Validation

**2026-09-30** — Claude host, tmux pane (TUI) mode. Codex engine live test left to the user (needs proxy).

| Check | Result |
| --- | --- |
| Unit tests | 12 passed; the 6 new ones fail on the pre-fix code |
| Claude → Cursor, no `--timeout` | exit 0; report `CIT_CLAUDE_CURSOR_NT_OK`; `session_id` recovered from agent transcript; host pane **not** pasted |
| Claude → Kimi (`kimi/cx`), no `--timeout` | exit 0; report `CIT_CLAUDE_KIMI_NT_OK`; delivered by Stop hook; host pane **not** pasted |
| Claude → Cursor, `--timeout 5` | exit 124; linger waiter delivered later and pasted one wake line into the host pane |
| Claude → Kimi, `--timeout 5` | exit 124; hook delivered later; linger waiter pasted one wake line |
| 2 × Kimi concurrently, same workdir | each wrapper identified its own session (matches hook `session_id`) |
| Claude → Codex | routing + `--` flag passthrough covered by unit tests; pane entered execution, then stopped by request |
| `doctor --to kimi` / `--to cursor` | 0 failures |
| Install | `call` skill linked at `$CLAUDE_CONFIG_DIR/skills/call` (`~/.claude-ppio`) |

Note: all 2026-09-21 smokes below ran in headless `exec` mode (`client=*_exec`); the pane path was first exercised here.

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
