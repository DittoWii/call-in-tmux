#!/usr/bin/env python3
"""Install only this plugin's Kimi hooks and optional Codex skill link.

Python 3.9+, standard library only. Validate candidate TOML using Kimi itself,
then back up and atomically replace the user's configuration.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

BEGIN = "# >>> call-in-tmux-kimi-cx >>>"
END = "# <<< call-in-tmux-kimi-cx <<<"
SCRIPT = Path(__file__).resolve().with_name("kimi-tmux")
SKILL = SCRIPT.parent.parent
EVENTS = ("Stop", "StopFailure", "Interrupt")


def strip_block(text):
    """Refuse malformed markers instead of risking deletion of unrelated TOML."""
    lines = text.splitlines(keepends=True)
    result, inside = [], False
    for line in lines:
        marker = line.rstrip("\r\n")
        if marker == BEGIN:
            if inside:
                raise ValueError("嵌套 hook 标记;请先修复 config.toml")
            inside = True
        elif marker == END:
            if not inside:
                raise ValueError("孤立的 hook 结束标记;请先修复 config.toml")
            inside = False
        elif not inside:
            result.append(line)
    if inside:
        raise ValueError("hook 标记未闭合;config.toml 未改动")
    return "".join(result)


def hook_block():
    command = shlex.join(["bash", str(SCRIPT), "__stop_hook"])
    body = "".join(
        f'[[hooks]]\nevent = "{event}"\ncommand = {json.dumps(command, ensure_ascii=False)}\ntimeout = 10\n\n'
        for event in EVENTS
    )
    return f"{BEGIN}\n{body}{END}\n"


def check_hooks(text):
    strip_block(text)
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise ValueError("未安装完整的 call-in-tmux-kimi-cx hooks")
    block = text.split(BEGIN, 1)[1].split(END, 1)[0]
    events = re.findall(r'^event = "([^"]+)"$', block, re.M)
    commands = re.findall(r'^command = (.+)$', block, re.M)
    if tuple(events) != EVENTS or len(commands) != 3:
        raise ValueError("hook 事件不完整;请重跑 install.sh")
    for value in commands:
        argv = shlex.split(json.loads(value))
        if len(argv) != 3 or argv[0] != "bash" or argv[2] != "__stop_hook" or not Path(argv[1]).is_file():
            raise ValueError("hook 脚本已失效;请重跑 install.sh")


def validate_config(text):
    if not shutil.which("kimi"):
        raise ValueError("未找到 kimi CLI;请先安装 Kimi Code 并登录")
    with tempfile.TemporaryDirectory(prefix="cx-kimi-config-") as temp:
        candidate = Path(temp) / "config.toml"
        candidate.write_text(text, encoding="utf-8")
        candidate.chmod(0o600)
        env = dict(os.environ, KIMI_CODE_HOME=temp, KIMI_CODE_NO_AUTO_UPDATE="1")
        result = subprocess.run(["kimi", "doctor"], env=env, capture_output=True, timeout=60)
        if result.returncode:
            # Config validators may echo credentials. Keep diagnostics local and
            # leave the original untouched; the user can run kimi doctor directly.
            raise ValueError("Kimi 拒绝候选配置;原配置未改动。请先运行 kimi doctor 检查原配置")


def replace_config(path, before, after):
    if before == after:
        return
    validate_config(after)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Refuse a concurrent editor's update instead of silently overwriting it.
    if (path.read_text(encoding="utf-8") if path.exists() else "") != before:
        raise ValueError("配置在校验期间被其他进程修改;请重试")
    if path.exists():
        backup = path.with_name(path.name + f".bak.call-in-tmux-kimi-cx.{time.time_ns()}")
        shutil.copy2(path, backup)
        backup.chmod(0o600)
        print(f"已备份: {backup}")
    fd, temp = tempfile.mkstemp(prefix=".call-in-tmux-kimi-cx-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(after)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "uninstall", "check"))
    parser.add_argument("--hooks-only", action="store_true", help="仅管理 Kimi hooks;原生插件安装时使用")
    parser.add_argument("--skill-dir", type=Path, default=Path.home() / ".agents/skills", help="Codex skill 父目录")
    args = parser.parse_args()
    config = (Path(os.environ.get("KIMI_CODE_HOME", str(Path.home() / ".kimi-code"))) / "config.toml").expanduser().resolve()
    link = args.skill_dir.expanduser().absolute() / "kimi"
    owned = link.is_symlink() and link.resolve() == SKILL
    if not args.hooks_only and (link.exists() or link.is_symlink()) and not owned:
        raise ValueError(f"{link} 已存在且不属于本安装;保留原文件。可用 --hooks-only 或 --skill-dir 指定其他目录")
    before = config.read_text(encoding="utf-8") if config.exists() else ""
    if args.action == "check":
        check_hooks(before)
        if not args.hooks_only and not owned:
            raise ValueError(f"未发现本插件的 skill 链接: {link}")
        print("call-in-tmux-kimi-cx 配置检查通过")
        return
    clean = strip_block(before)
    if args.action == "install":
        after = clean + ("\n" if clean and not clean.endswith("\n") else "") + hook_block()
        replace_config(config, before, after)
        if not args.hooks_only and not owned:
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(SKILL, target_is_directory=True)
        print(f"Kimi hooks 已就绪: {config}")
        if not args.hooks_only:
            print(f"Codex skill: {link}\n在新的 Codex 对话中使用 $kimi <任务>。")
    else:
        replace_config(config, before, clean)
        if not args.hooks_only and owned:
            link.unlink()
        print("已移除本插件的 hooks / 所选 skill 链接;任务记录、报告和其他插件配置保留。")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"call-in-tmux-kimi-cx: {exc}", file=sys.stderr)
        sys.exit(2)
