#!/usr/bin/env bash
# call-in-tmux-kimi-cc 卸载器:从 ~/.kimi-code/config.toml 移除 Stop hook 块。
# 不动 registry/缓存(${XDG_CACHE_HOME:-~/.cache}/kimi-tmux),不恢复旧备份。
set -u

KIMI_HOME_DIR="${KIMI_CODE_HOME:-$HOME/.kimi-code}"
CFG="$KIMI_HOME_DIR/config.toml"
MARK_BEGIN="# >>> call-in-tmux-kimi-cc >>>"
MARK_END="# <<< call-in-tmux-kimi-cc <<<"

fail() { echo "uninstall: $*" >&2; exit 1; }

strip_marked_block() { # <in >out;只用 awk,不依赖 python3
    awk -v b="$MARK_BEGIN" -v e="$MARK_END" '
        index($0, b) == 1 { skip = 1; pend = 0; next }
        skip { if (index($0, e) == 1) skip = 0; next }
        $0 == "" { pend++; next }
        { while (pend-- > 0) print ""; pend = 0; print }
        END { while (pend-- > 0) print "" }
    '
}

if [ ! -f "$CFG" ] || ! grep -qF "$MARK_BEGIN" "$CFG"; then
    echo "uninstall: $CFG 中没有 call-in-tmux-kimi-cc hook 块,无需处理"
else
    BAK="$CFG.bak.kimi-tmux.$(date +%Y%m%d%H%M%S)"
    cp -- "$CFG" "$BAK" || fail "备份失败:$CFG -> $BAK"
    tmp="$CFG.kimi-tmux.tmp.$$"
    strip_marked_block < "$CFG" > "$tmp" || { rm -f -- "$tmp"; fail "移除 hook 块失败(原文件未改动)"; }
    cat -- "$tmp" > "$CFG" || { rm -f -- "$tmp"; fail "写回 $CFG 失败(备份在 $BAK)"; }
    rm -f -- "$tmp"
    grep -qF "$MARK_BEGIN" "$CFG" && fail "hook 块未被完全移除,请手工检查 $CFG(备份在 $BAK)"
    echo "uninstall: hook 块已移除(原文件备份在 $BAK)"
fi
echo "uninstall: 如需卸载 skill,请删除 ~/.claude/skills/kimi;残留缓存在 \${XDG_CACHE_HOME:-~/.cache}/kimi-tmux"
