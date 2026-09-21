---
name: call
description: >
  统一把子任务派给其他 coding CLI(Cursor / Kimi),在 tmux 可视窗格执行并回收报告。
  用户说「调用 cursor/kimi」「让 kimi/cursor 做…」「派给…」时使用本 skill,
  不必再分别加载 $cursor / $kimi。
---

# Codex → 其他 Agent(call-in-tmux)

唯一入口:PATH 中的 `call-in-tmux`,或本 skill 仓库内 `bin/call-in-tmux` 的绝对路径。

当前本宿主(`codex`)支持的后端:**cursor / kimi**(不支持再派给 codex 自己)。

## 派发

把任务写成简报后:

```bash
CALL_IN_TMUX_HOST=codex call-in-tmux to <cursor|kimi> \
  -t <任务名> -C /absolute/project \
  -o /absolute/reports/<名>.report.md \
  --brief /absolute/reports/<名>.brief.md --timeout 900
```

不要提前结束本回合。`exec_command` 必须等到 `call-in-tmux` 退出再读报告(把 `yield_time_ms` 设得足够大,或循环 `write_stdin` 直到进程结束)。退出 0 后确认 `.done`,读报告与 `.meta.json`,再决定审核通过还是给下一步;不要停在「已派发」。

若因 `--timeout` 先返回 124:子任务仍在跑,后台会在它真正写完报告后把一句 `call-in-tmux: 子任务 … 已结束` 贴回本窗格。看到这句话就去读报告并继续,不要干等。命令 session id ≠ 后端 agent session id。

## 续聊与管理

```bash
CALL_IN_TMUX_HOST=codex call-in-tmux to <engine> --resume <id> -t followup -o /abs/new.report.md --brief /abs/followup.brief.md
call-in-tmux list
call-in-tmux kill --to <engine> done
call-in-tmux matrix
```

Codex app 找不到宿主 pane 时加 `--target %PANE`,或让其降级无头。

## 契约

分层终报、独立 `-o`、禁止并行改同一文件(并行用 worktree)。后端 `--force`/`--auto` 不是 Codex 沙箱。
