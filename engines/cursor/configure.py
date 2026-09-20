#!/usr/bin/env python3
"""Install this plugin's Cursor hooks and optional Codex skill link.

Python 3.9+, standard library only. Merge ~/.cursor/hooks.json without
disturbing unrelated hooks; back up and replace atomically.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import sys
import tempfile
import time

EVENTS = ("sessionStart", "stop", "sessionEnd")
SCRIPT = Path(__file__).resolve().with_name("cursor-tmux")
SKILL = SCRIPT.parent.parent
MARKER = "call-in-tmux-cursor"


def hook_command():
    return shlex.join(["bash", str(SCRIPT), "__stop_hook"])


def is_ours(entry):
    if not isinstance(entry, dict):
        return False
    command = entry.get("command")
    if not isinstance(command, str):
        return False
    if "__stop_hook" not in command:
        return False
    # Match either explicit marker token or this repo's vendored script path.
    return MARKER in command or str(SCRIPT) in command or "engines/cursor/cursor-tmux" in command


def ours_entry():
    return {"command": hook_command(), "timeout": 10, "loop_limit": 0}


def load_hooks(path):
    if not path.exists():
        return {"version": 1, "hooks": {}}
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return {"version": 1, "hooks": {}}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"hooks.json 不是合法 JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("hooks.json 根节点必须是对象")
    data.setdefault("version", 1)
    hooks = data.get("hooks")
    if hooks is None:
        data["hooks"] = {}
    elif not isinstance(hooks, dict):
        raise ValueError("hooks.json 的 hooks 必须是对象")
    return data


def strip_ours(data):
    hooks = data.setdefault("hooks", {})
    for event, entries in list(hooks.items()):
        if not isinstance(entries, list):
            continue
        hooks[event] = [item for item in entries if not is_ours(item)]
        if not hooks[event]:
            del hooks[event]
    return data


def inject_ours(data):
    hooks = data.setdefault("hooks", {})
    for event in EVENTS:
        existing = [item for item in hooks.get(event, []) if isinstance(item, dict)]
        others = [item for item in existing if not is_ours(item)]
        hooks[event] = others + [ours_entry()]
    return data


def check_hooks(data):
    hooks = data.get("hooks") or {}
    for event in EVENTS:
        entries = hooks.get(event) or []
        ours = [item for item in entries if is_ours(item)]
        if len(ours) != 1:
            raise ValueError(f"未安装完整的 call-in-tmux-cursor {event} hook")
        argv = shlex.split(ours[0]["command"])
        if len(argv) != 3 or argv[0] != "bash" or argv[2] != "__stop_hook" or not Path(argv[1]).is_file():
            raise ValueError("hook 脚本已失效;请重跑 install.sh")


def dump_hooks(data):
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def replace_config(path, before, after):
    after_text = dump_hooks(after)
    if before == after_text:
        return
    if before.strip():
        try:
            if json.loads(before) == after:
                return
        except json.JSONDecodeError:
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if current != before:
        raise ValueError("配置在校验期间被其他进程修改;请重试")
    if path.exists():
        backup = path.with_name(path.name + f".bak.call-in-tmux-cursor.{time.time_ns()}")
        shutil.copy2(path, backup)
        backup.chmod(0o600)
        print(f"已备份: {backup}")
    fd, temp = tempfile.mkstemp(prefix=".call-in-tmux-cursor-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(after_text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        path.chmod(0o600)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "uninstall", "check"))
    parser.add_argument("--hooks-only", action="store_true", help="仅管理 Cursor hooks;原生插件安装时使用")
    parser.add_argument("--skill-dir", type=Path, default=Path.home() / ".agents/skills", help="Codex skill 父目录")
    args = parser.parse_args()
    cursor_home = Path(os.environ.get("CURSOR_HOME", str(Path.home() / ".cursor"))).expanduser().resolve()
    config = cursor_home / "hooks.json"
    link = args.skill_dir.expanduser().absolute() / "cursor"
    owned = link.is_symlink() and link.resolve() == SKILL
    if not args.hooks_only and (link.exists() or link.is_symlink()) and not owned:
        raise ValueError(f"{link} 已存在且不属于本安装;保留原文件。可用 --hooks-only 或 --skill-dir 指定其他目录")
    before_text = config.read_text(encoding="utf-8") if config.exists() else ""
    before = load_hooks(config) if before_text.strip() else {"version": 1, "hooks": {}}
    if before_text.strip():
        before = json.loads(before_text)
        if not isinstance(before, dict):
            raise ValueError("hooks.json 根节点必须是对象")
        before.setdefault("version", 1)
        before.setdefault("hooks", {})
    if args.action == "check":
        check_hooks(before)
        if not args.hooks_only and not owned:
            raise ValueError(f"未发现本插件的 skill 链接: {link}")
        print("call-in-tmux-cursor 配置检查通过")
        return
    if args.action == "install":
        after = inject_ours(json.loads(json.dumps(before)))
        replace_config(config, before_text, after)
        if not args.hooks_only and not owned:
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(SKILL, target_is_directory=True)
        print(f"Cursor hooks 已就绪: {config}")
        if not args.hooks_only:
            print(f"Codex skill: {link}\n在新的 Codex 对话中使用 $cursor <任务>。")
    else:
        after = strip_ours(json.loads(json.dumps(before)))
        replace_config(config, before_text, after)
        if not args.hooks_only and owned:
            link.unlink()
        print("已移除本插件的 hooks / 所选 skill 链接;任务记录、报告和其他插件配置保留。")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as exc:
        print(f"call-in-tmux-cursor: {exc}", file=sys.stderr)
        sys.exit(2)
