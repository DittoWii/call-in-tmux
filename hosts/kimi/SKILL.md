---
name: call
description: >
  统一把子任务派给 Cursor Agent CLI,在 tmux 可视窗格执行并回收报告。
  用户说「调用 cursor」「让 cursor/agent 做…」时使用;通过 call-in-tmux 路由,不手写引擎脚本。
---

# Kimi → Cursor(call-in-tmux)

唯一入口:PATH 中的 `call-in-tmux`,或本 skill 仓库内 `bin/call-in-tmux`。

当前本宿主(`kimi`)支持的后端:**cursor**。

## 派发

```bash
CALL_IN_TMUX_HOST=kimi call-in-tmux to cursor \
  -t <任务名> -C /absolute/project \
  -o /absolute/reports/<名>.report.md \
  --brief /absolute/reports/<名>.brief.md --timeout 900
```

简报自包含;要求 Cursor 写 `.report.md` + `.evidence.md`;禁止反问。必须等 `call-in-tmux` 进程退出后再读摘要并继续(审核或下一步),不要在派发后结束本回合。若超时先返回,看到窗格里 `call-in-tmux: 子任务 … 已结束` 再读报告。

## 续聊与管理

```bash
CALL_IN_TMUX_HOST=kimi call-in-tmux to cursor --resume <session-id> -t followup -o /abs/new.report.md --brief /abs/q.brief.md
call-in-tmux kill --to cursor <任务名>
call-in-tmux matrix
```

不要用 `kill … done` / `all`:登记表跨会话共享,会关掉别的会话的窗格。

若矩阵日后增加 `kimi → kimi/codex` 等边,仍走同一入口,只改 `to <engine>`。
