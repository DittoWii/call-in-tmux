---
name: call
description: >
  统一把子任务派给其他 coding CLI(Codex / Cursor / Kimi),在 tmux 可视窗格执行并回收报告。
  用户说「调用 cursor/kimi/codex」「让 kimi/cursor 做…」「派给…」时使用本 skill,
  不必再分别加载多个后端 skill。
argument-hint: <cursor|kimi|codex> <任务描述>
---

# Claude → 其他 Agent(call-in-tmux)

唯一入口:优先 PATH 里的 `call-in-tmux`;否则

```bash
CALL="$(cd "$(dirname "$0")/../.." && pwd)/bin/call-in-tmux"   # 从本 SKILL 目录解析
# 或: CALL=/home/dongjiang/jd/workspace/call-in-tmux/bin/call-in-tmux
```

当前本宿主(`claude`)支持的后端:**codex / cursor / kimi**。

## 怎么用

1. 从用户话里认出后端(`cursor`/`agent`/`kimi`/`codex`);未点名则默认 `cursor`。
2. 写自包含简报(目标、工作目录、允许改动、验收、禁止反问、双文件终报契约)。
3. 派发(后台,退出即唤醒):

```bash
CALL_IN_TMUX_HOST=claude call-in-tmux to <engine> \
  -t <任务名> -C /absolute/workdir \
  -o /absolute/<名>.report.md --brief /absolute/<名>.brief.md \
  --timeout 900
```

4. 唤醒后只读 `<名>.report.md`(≤50 行摘要);证据在 `<名>.evidence.md`。
5. 续聊:`call-in-tmux to <engine> --resume <session-id> -t ... -o <新报告> --brief <追问>`。

## 契约

- 路径全绝对;每任务独立 `-o`。
- 终报双文件:`.report.md` + `.evidence.md`。
- 派给 **codex** 时,若引擎支持,在 `--` 后附加 `-c 'model_reasoning_effort="max"'`(机械任务可降 medium/high)。
- 管理:`call-in-tmux list` / `call-in-tmux kill --to <engine> done`。
- 矩阵:`call-in-tmux matrix`。

## 宿主注意

用 Claude Code 的 `run_in_background` / Bash 后台语义;不要假设 Codex 的 `write_stdin`。引擎与本会话共享文件系统,不是沙箱隔离。
