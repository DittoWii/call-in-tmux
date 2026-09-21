# Upstream & Vendoring

`call-in-tmux` is a **self-contained** matrix router. Engine scripts under `engines/` are vendored copies; runtime must not require sibling `cx-*` / `cc-*` checkouts.

## Lineage

The tmux-pane dispatch + written-report pattern is inspired by [huanglune/cc-codex-tmux](https://github.com/huanglune/cc-codex-tmux) (screenshot vendored as `docs/screenshot-cc-codex-tmux.png`).

```text
huanglune/cc-codex-tmux     → engines/codex/codex-tmux
DittoWii/cc-kimi-tmux       → engines/kimi/cc/*
DittoWii/cx-kimi-tmux       → engines/kimi/cx/*
cx-cursor-tmux              → engines/cursor/*
```

## Local patches after copy

- `engines/cursor/configure.py`: script name `cursor-tmux`; hook marker `call-in-tmux-cursor`; use `--hooks-only` from top-level install (do not install a separate `$cursor` Codex skill).
- `engines/kimi/cx/configure.py`: script name `kimi-tmux`; hook marker `call-in-tmux-kimi-cx`.
- `engines/kimi/cc/install.sh`: hook command `$HERE/kimi-tmux`; marker `call-in-tmux-kimi-cc`.

## Refresh recipe

```bash
# example: refresh cursor engine from a checkout
cp /path/to/cx-cursor-tmux/skills/cursor/scripts/cx-cursor-tmux engines/cursor/cursor-tmux
cp /path/to/cx-cursor-tmux/skills/cursor/scripts/configure.py engines/cursor/configure.py
# re-apply patches above, then:
bash install.sh --hooks-only
```
