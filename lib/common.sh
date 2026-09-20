#!/usr/bin/env bash
# Shared helpers for call-in-tmux.
set -u

cit_die() { echo "call-in-tmux: $*" >&2; exit 2; }

cit_root() {
    local self
    self=$(realpath -m -- "${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}" 2>/dev/null || printf '%s' "${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}")
    # lib/common.sh → repo root
    dirname -- "$(dirname -- "$self")"
}

cit_expand() {
    # Expand ${HOME}, ${CALL_IN_TMUX_WORKSPACE}, ${CALL_IN_TMUX_ROOT}, ~ 
    local s="$1" root workspace
    root="${CALL_IN_TMUX_ROOT:-}"
    [ -n "$root" ] || root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
    workspace="${CALL_IN_TMUX_WORKSPACE:-$(dirname -- "$root")}"
    s=${s//\$\{HOME\}/$HOME}
    s=${s//\$HOME/$HOME}
    s=${s//\$\{CALL_IN_TMUX_ROOT\}/$root}
    s=${s//\$\{CALL_IN_TMUX_WORKSPACE\}/$workspace}
    case "$s" in
        ~/*) s="$HOME/${s#~/}" ;;
        ~) s="$HOME" ;;
    esac
    printf '%s' "$s"
}

cit_matrix_file() {
    if [ -n "${CALL_IN_TMUX_MATRIX:-}" ] && [ -f "$CALL_IN_TMUX_MATRIX" ]; then
        printf '%s' "$CALL_IN_TMUX_MATRIX"
        return 0
    fi
    local root user
    root="${CALL_IN_TMUX_ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
    user="${XDG_CONFIG_HOME:-$HOME/.config}/call-in-tmux/matrix.json"
    if [ -f "$user" ]; then printf '%s' "$user"; else printf '%s' "$root/config/matrix.json"; fi
}

cit_json_py() {
    python3 - "$@" <<'PY'
import json, os, sys
path = sys.argv[1]
op = sys.argv[2]
with open(path, encoding="utf-8") as f:
    data = json.load(f)

def expand(s: str) -> str:
    root = os.environ.get("CALL_IN_TMUX_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(path)))
    # If path is user override, still prefer env root when set; else derive from env or sibling of config in repo.
    if not os.environ.get("CALL_IN_TMUX_ROOT"):
        # Prefer repo root from CALL_IN_TMUX_ROOT already unset — caller should set it.
        pass
    workspace = os.environ.get("CALL_IN_TMUX_WORKSPACE") or os.path.dirname(root)
    home = os.path.expanduser("~")
    s = s.replace("${HOME}", home).replace("$HOME", home)
    s = s.replace("${CALL_IN_TMUX_ROOT}", root).replace("${CALL_IN_TMUX_WORKSPACE}", workspace)
    if s.startswith("~/"):
        s = os.path.join(home, s[2:])
    elif s == "~":
        s = home
    return s

if op == "edges":
    for h, e in data.get("edges", []):
        print(f"{h}\t{e}")
elif op == "hosts":
    for name, meta in data.get("hosts", {}).items():
        aliases = ",".join(meta.get("aliases") or [])
        print(f"{name}\t{aliases}")
elif op == "engines":
    for name, meta in data.get("engines", {}).items():
        aliases = ",".join(meta.get("aliases") or [])
        print(f"{name}\t{aliases}")
elif op == "resolve_host":
    want = sys.argv[3].lower()
    for name, meta in data.get("hosts", {}).items():
        if want == name or want in [a.lower() for a in (meta.get("aliases") or [])]:
            print(name); sys.exit(0)
    sys.exit(1)
elif op == "resolve_engine":
    want = sys.argv[3].lower()
    for name, meta in data.get("engines", {}).items():
        if want == name or want in [a.lower() for a in (meta.get("aliases") or [])]:
            print(name); sys.exit(0)
    sys.exit(1)
elif op == "edge_ok":
    host, engine = sys.argv[3], sys.argv[4]
    ok = [host, engine] in [list(x) for x in data.get("edges", [])]
    sys.exit(0 if ok else 1)
elif op == "runners":
    host, engine = sys.argv[3], sys.argv[4]
    eng = data["engines"][engine]
    runners = eng.get("runners") or {}
    seq = runners.get(host) or runners.get("default") or []
    for item in seq:
        print(expand(item))
elif op == "default_engine":
    print((data.get("defaults") or {}).get("engine") or "cursor")
elif op == "skill_install":
    host = sys.argv[3]
    print(expand(data["hosts"][host]["skill_install"]))
elif op == "wake":
    host = sys.argv[3]
    print(data["hosts"][host].get("wake", ""))
elif op == "dump_matrix":
    print(json.dumps(data, ensure_ascii=False, indent=2))
else:
    raise SystemExit(f"unknown op {op}")
PY
}

cit_detect_host() {
    if [ -n "${CALL_IN_TMUX_HOST:-}" ]; then
        printf '%s' "$CALL_IN_TMUX_HOST"
        return 0
    fi
    # Heuristics: parent process / env markers from known hosts.
    if [ -n "${CLAUDECODE:-}" ] || [ -n "${CLAUDE_CODE_ENTRYPOINT:-}" ] || [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
        printf 'claude'; return 0
    fi
    if [ -n "${CODEX_THREAD_ID:-}" ] || [ -n "${CODEX_HOME:-}" ] && ps -o args= -p "$PPID" 2>/dev/null | grep -qi codex; then
        printf 'codex'; return 0
    fi
    if ps -o args= -p "$PPID" 2>/dev/null | grep -qiE '(^|/)(claude)( |$)'; then
        printf 'claude'; return 0
    fi
    if ps -o args= -p "$PPID" 2>/dev/null | grep -qiE '(^|/)(codex)( |$)'; then
        printf 'codex'; return 0
    fi
    if ps -o args= -p "$PPID" 2>/dev/null | grep -qiE '(^|/)(kimi)( |$)'; then
        printf 'kimi'; return 0
    fi
    if [ -n "${KIMI_CODE_HOME:-}" ] && ps -o args= -p "$PPID" 2>/dev/null | grep -qi kimi; then
        printf 'kimi'; return 0
    fi
    printf 'auto'
}

cit_first_existing() {
    local p
    for p in "$@"; do
        [ -n "$p" ] || continue
        if [ -x "$p" ] || [ -f "$p" ]; then
            printf '%s' "$p"
            return 0
        fi
    done
    return 1
}
