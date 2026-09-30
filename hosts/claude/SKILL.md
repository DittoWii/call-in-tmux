---
name: call
description: >
  统一把子任务派给其他 coding CLI(Codex / Cursor / Kimi),在 tmux 可视窗格执行并回收报告。
  用户说「调用 cursor/kimi/codex」「让 kimi/cursor 做…」「派给…」时使用本 skill,
  不必再分别加载多个后端 skill。
argument-hint: <cursor|kimi|codex> <任务描述>
---

# Claude → 其他 Agent(call-in-tmux)

唯一入口:PATH 里的 `call-in-tmux`(`install.sh` 链到 `~/.local/bin`)。PATH 里没有时,本 skill 目录是指向仓库 `hosts/claude` 的软链,用 `"$(realpath <本 skill 目录>)/../../bin/call-in-tmux"`。

当前本宿主(`claude`)支持的后端:**codex / cursor / kimi**。

## 怎么用

1. 从用户话里认出后端(`cursor`/`agent`/`kimi`/`codex`);未点名则默认 `cursor`。
2. 把简报写成文件,自包含:目标、工作目录、允许改动的范围、验收标准、禁止反问、双文件终报契约。
3. 用 Bash `run_in_background: true` 派发,**不要加 `--timeout`**:

```bash
CALL_IN_TMUX_HOST=claude call-in-tmux to <engine> \
  -t <任务名> -C /absolute/workdir \
  -o /absolute/<名>.report.md --brief /absolute/<名>.brief.md
```

   派给 **codex** 时在末尾加 `-- -c 'model_reasoning_effort="max"'`(机械任务可降 `medium`/`high`)。其他引擎的原生 flags 同样放在 `--` 之后。
4. 等后台任务结束通知,不要轮询。按退出码处理:

| 退出码 | 含义 | 下一步 |
| :-: | :--- | :--- |
| 0 | 已交付 | 读 `<名>.report.md`(≤50 行摘要),<br>需要细节再看 `<名>.evidence.md` 和 `.meta.json` |
| 2 | 失败 | 看命令输出末尾和 `<名>.report.md.pane.log` |
| 124 | 传了 `--timeout` 且到点 | 子任务仍在跑:cursor / kimi 交付后会往本窗格贴<br>`call-in-tmux: 子任务 … 已结束`;codex 不会,需自己 `list` 查 |
| 130 | 包装进程被杀 | 窗格里的后端仍在跑,用 `list` 查状态 |

5. 续聊:报告末尾有 `session-id`,用 `call-in-tmux to <engine> --resume <session-id> -t <新任务名> -C <同一工作目录> -o <新报告> --brief <追问文件>`。

## 契约

- 路径全绝对;每个任务独立 `-t` 和 `-o`,并行任务不要改同一批文件。
- 终报双文件:`.report.md` + `.evidence.md`。
- 查看:`call-in-tmux list`。关闭:`call-in-tmux kill --to <engine> <任务名>`。
  **不要用 `kill … done` / `all`**:登记表跨会话共享,会关掉别的会话的窗格。
- 矩阵:`call-in-tmux matrix`;自检:`call-in-tmux doctor --to cursor|kimi`。

## 宿主注意

Claude Code 的后台任务退出就是唤醒信号,所以不需要 `--timeout`;也不要假设 Codex 的 `write_stdin`。后端以免审批姿态运行,与本会话共享文件系统,不是沙箱隔离。
