#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")" && pwd)
export CALL_IN_TMUX_ROOT="$ROOT"
. "$ROOT/lib/common.sh"
MATRIX=$(cit_matrix_file)

HOSTS=(claude codex kimi)
HOOKS=1
while [ $# -gt 0 ]; do
    case "$1" in
        --host) HOSTS=("$2"); shift 2 ;;
        --all-hosts) HOSTS=(claude codex kimi); shift ;;
        --no-hooks) HOOKS=0; shift ;;
        *) echo "未知参数 $1" >&2; exit 2 ;;
    esac
done

if [ -L "$HOME/.local/bin/call-in-tmux" ] && [ "$(realpath -m -- "$HOME/.local/bin/call-in-tmux")" = "$ROOT/bin/call-in-tmux" ]; then
    rm -f "$HOME/.local/bin/call-in-tmux"
    echo "已移除 CLI 链接"
fi

for h in "${HOSTS[@]}"; do
    h=$(cit_json_py "$MATRIX" resolve_host "$h" 2>/dev/null) || continue
    dest=$(cit_json_py "$MATRIX" skill_install "$h")
    if [ -L "$dest" ] && [ "$(realpath -m -- "$dest")" = "$(realpath -m -- "$ROOT/hosts/$h")" ]; then
        rm -f "$dest"
        echo "已移除 skill 链接: $dest"
    fi
done

if [ "$HOOKS" = 1 ]; then
    python3 "$ROOT/engines/cursor/configure.py" uninstall --hooks-only 2>/dev/null || true
    python3 "$ROOT/engines/kimi/cx/configure.py" uninstall --hooks-only 2>/dev/null || true
    # kimi/cc 已不再安装;保留清理,移除旧版本装过的 call-in-tmux-kimi-cc hook 块
    if [ -x "$ROOT/engines/kimi/cc/uninstall.sh" ]; then
        bash "$ROOT/engines/kimi/cc/uninstall.sh" 2>/dev/null || true
    fi
fi
echo "已移除本插件入口与本插件 hooks;引擎脚本仍在仓库 engines/ 内。"
