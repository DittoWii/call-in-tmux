#!/usr/bin/env bash
# Install call-in-tmux: CLI, host skills, and engine completion hooks (self-contained).
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")" && pwd)
export CALL_IN_TMUX_ROOT="$ROOT"
export CALL_IN_TMUX_WORKSPACE="${CALL_IN_TMUX_WORKSPACE:-$(dirname -- "$ROOT")}"
# shellcheck source=lib/common.sh
. "$ROOT/lib/common.sh"
MATRIX=$(cit_matrix_file)

HOSTS=()
BIN_LINK=1
SKILLS=1
HOOKS=1
while [ $# -gt 0 ]; do
    case "$1" in
        --host) HOSTS+=("$2"); shift 2 ;;
        --all-hosts) HOSTS=(claude codex kimi); shift ;;
        --bin-only) SKILLS=0; HOOKS=0; shift ;;
        --skills-only) BIN_LINK=0; HOOKS=0; shift ;;
        --hooks-only) BIN_LINK=0; SKILLS=0; shift ;;
        --no-hooks) HOOKS=0; shift ;;
        -h|--help)
            cat <<'EOF'
用法: install.sh [--host claude|codex|kimi]... [--all-hosts]
                 [--bin-only|--skills-only|--hooks-only|--no-hooks]

默认安装: CLI 链接 + 全部宿主 skill + 所选宿主能派发到的引擎 hooks(cursor / kimi)。
Claude skill 装到 ${CLAUDE_CONFIG_DIR:-~/.claude}/skills/call;cac 多环境时每个环境各跑一次 --host claude。
引擎脚本全部在本仓库 engines/ 下,不依赖旁路 cx-* / cc-* 仓库。
EOF
            exit 0
            ;;
        *) echo "未知参数 $1" >&2; exit 2 ;;
    esac
done
if [ ${#HOSTS[@]} -eq 0 ]; then
    HOSTS=(claude codex kimi)
fi
RESOLVED=()
for h in "${HOSTS[@]}"; do
    r=$(cit_json_py "$MATRIX" resolve_host "$h") || { echo "未知宿主 $h" >&2; exit 2; }
    RESOLVED+=("$r")
done

if [ "$BIN_LINK" = 1 ]; then
    mkdir -p "$HOME/.local/bin"
    ln -sfn "$ROOT/bin/call-in-tmux" "$HOME/.local/bin/call-in-tmux"
    echo "CLI: $HOME/.local/bin/call-in-tmux → $ROOT/bin/call-in-tmux"
fi

if [ "$SKILLS" = 1 ]; then
    for h in "${RESOLVED[@]}"; do
        dest=$(cit_json_py "$MATRIX" skill_install "$h")
        src="$ROOT/hosts/$h"
        [ -d "$src" ] || { echo "缺少 $src" >&2; exit 2; }
        mkdir -p "$(dirname -- "$dest")"
        if [ -e "$dest" ] || [ -L "$dest" ]; then
            if [ -L "$dest" ] && [ "$(realpath -m -- "$dest")" = "$(realpath -m -- "$src")" ]; then
                echo "skill($h): 已是本安装 $dest"
                continue
            fi
            echo "skill($h): $dest 已存在且不属于本安装;跳过" >&2
            continue
        fi
        ln -s "$src" "$dest"
        echo "skill($h): $dest → $src"
    done
fi

if [ "$HOOKS" = 1 ]; then
    # 只装所选宿主经矩阵边能到达的引擎;codex 引擎走内联 notify,不需要 hook
    mapfile -t ENGINES < <(cit_json_py "$MATRIX" edges \
        | awk -F'\t' -v hs="${RESOLVED[*]}" 'BEGIN{n=split(hs,a," ");for(i=1;i<=n;i++)H[a[i]]=1} ($1 in H){print $2}' | sort -u)
    for e in "${ENGINES[@]}"; do
        case "$e" in
            cursor)
                echo "[hooks] cursor (engines/cursor)"
                python3 "$ROOT/engines/cursor/configure.py" install --hooks-only
                ;;
            kimi)
                echo "[hooks] kimi (engines/kimi/cx)"
                python3 "$ROOT/engines/kimi/cx/configure.py" install --hooks-only
                ;;
        esac
    done
fi

echo
echo "下一步:"
echo "  call-in-tmux matrix"
echo "  新开宿主会话: 调用 cursor / 让 kimi … / 派给 codex …"
echo "  Codex 侧请只用 \$call(或自然语言),不要再装 cx-*-tmux 插件 skill。"
