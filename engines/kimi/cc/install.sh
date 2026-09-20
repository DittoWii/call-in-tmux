#!/usr/bin/env bash
# cc-kimi-tmux 安装器:
#   1. 向 ~/.kimi-code/config.toml 幂等注入 Stop hook(每次改动前必备份)
#   2. 校验依赖(kimi / tmux / bash>=4.4 / jq|node|python3)
#   3. 提示如何将本目录装为 Claude Code skill
set -u

HERE=$(cd -- "$(dirname -- "$0")" && pwd)
KIMI_HOME_DIR="${KIMI_CODE_HOME:-$HOME/.kimi-code}"
CFG="$KIMI_HOME_DIR/config.toml"
MARK_BEGIN="# >>> call-in-tmux-kimi-cc >>>"
MARK_END="# <<< call-in-tmux-kimi-cc <<<"

fail() { echo "install: $*" >&2; exit 1; }

command -v kimi  >/dev/null 2>&1 || fail "未找到 kimi CLI(先安装 Kimi Code 并登录)"
if [ "${KIMI_TMUX_MODE:-pane}" != exec ]; then
    command -v tmux >/dev/null 2>&1 || echo "install: 警告: 未找到 tmux,运行时将自动降级为 exec 无头模式"
fi
bash -c '[[ ${BASH_VERSINFO[0]} -ge 5 || (${BASH_VERSINFO[0]} -eq 4 && ${BASH_VERSINFO[1]} -ge 4) ]]' \
    || fail "需要 bash >= 4.4"
command -v jq >/dev/null 2>&1 || command -v node >/dev/null 2>&1 || command -v python3 >/dev/null 2>&1 \
    || fail "需要 jq / node / python3 之一处理 JSON"

# hook command 要嵌进 TOML 基本字符串(双引号)里,再由 shell 解析。含空格的路径必须加引号,
# 否则 kimi 执行 hook 时会把路径拦腰截断 —— hook 永不执行,任务静默永不交付。
case "$HERE" in
    *\'*|*\"*|*\\*) fail "仓库路径含引号或反斜杠,无法安全嵌入 hook 命令:$HERE" ;;
esac
HOOK_CMD="bash '$HERE/kimi-tmux' __stop_hook"

[ -f "$CFG" ] || { mkdir -p -- "$KIMI_HOME_DIR" || fail "无法创建 $KIMI_HOME_DIR"; : > "$CFG" || fail "无法创建 $CFG"; }

# 任何改动前先备份(重装同样备份 —— 重装也是改动)
BAK="$CFG.bak.kimi-tmux.$(date +%Y%m%d%H%M%S)"
cp -- "$CFG" "$BAK" || fail "备份失败:$CFG -> $BAK"
echo "install: 已备份 $CFG -> $BAK"

# 幂等:先删掉所有旧标记块,再追加新块。只用 awk(coreutils 基线),不额外依赖 python3。
# 连带吞掉块前的空行,使卸载后能逐字节还原原文件。
strip_marked_block() { # <in >out
    awk -v b="$MARK_BEGIN" -v e="$MARK_END" '
        index($0, b) == 1 { skip = 1; pend = 0; next }
        skip { if (index($0, e) == 1) skip = 0; next }
        $0 == "" { pend++; next }
        { while (pend-- > 0) print ""; pend = 0; print }
        END { while (pend-- > 0) print "" }
    '
}

if grep -qF "$MARK_BEGIN" "$CFG"; then
    tmp="$CFG.kimi-tmux.tmp.$$"
    strip_marked_block < "$CFG" > "$tmp" || { rm -f -- "$tmp"; fail "移除旧 hook 块失败"; }
    cat -- "$tmp" > "$CFG" || { rm -f -- "$tmp"; fail "写回 $CFG 失败"; }
    rm -f -- "$tmp"
    grep -qF "$MARK_BEGIN" "$CFG" && fail "旧 hook 块未被完全移除,请手工检查 $CFG(备份在 $BAK)"
    echo "install: 已移除旧 hook 块"
fi

cat >> "$CFG" <<EOF || fail "写入 hook 块失败(原文件备份在 $BAK)"

$MARK_BEGIN
# cc-kimi-tmux: Kimi 回合结束(Stop)/回合失败(StopFailure)/用户中断(Interrupt) 时通知派发器。
# 无害于普通会话——非派发的会话没有 KIMI_TMUX_REPORT 环境标记,hook 立即退出。
[[hooks]]
event = "Stop"
command = "$HOOK_CMD"
timeout = 10

[[hooks]]
event = "StopFailure"
command = "$HOOK_CMD"
timeout = 10

[[hooks]]
event = "Interrupt"
command = "$HOOK_CMD"
timeout = 10
$MARK_END
EOF

n=$(grep -c "^$MARK_BEGIN\$" "$CFG")
[ "$n" = 1 ] || fail "config.toml 里有 $n 个 cc-kimi-tmux 块(应为 1),请手工检查 $CFG(备份在 $BAK)"

if command -v timeout >/dev/null 2>&1; then
    timeout 60 kimi doctor >/dev/null 2>&1 || fail "hook 注入后 config.toml 校验失败(kimi doctor)——请检查 $CFG(备份在 $BAK)"
else
    kimi doctor >/dev/null 2>&1 || fail "hook 注入后 config.toml 校验失败(kimi doctor)——请检查 $CFG(备份在 $BAK)"
fi

echo "install: hook 已注入 $CFG"

# 装完立刻自检一次。重点是 provider 那一节:官方托管 provider 走 oauth;自建/第三方 OpenAI
# 兼容端点则直连实测 config.toml 里的 base_url —— 窗格里不走代理,doctor 探的就是同一条路。
# 这里只报告不拦安装:hook 已经装好了,连通性是环境问题,留给你按提示修。
echo
bash "$HERE/kimi-tmux" doctor || DOCTOR_RC=$?
if [ "${DOCTOR_RC:-0}" -ge 2 ]; then
    echo
    echo "install: ⚠ 上面有自检项失败 —— hook 已装好,但被派发的 kimi 现在跑不通。"
    echo "install:   修好后复查: bash \"$HERE/kimi-tmux\" doctor --live"
fi

echo
echo "install: 完成。引擎目录:$HERE(宿主 skill 由 call-in-tmux/install.sh 统一安装)。"
