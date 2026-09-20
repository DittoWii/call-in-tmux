#!/usr/bin/env python3
"""Unit tests for call-in-tmux matrix routing (no real agent calls)."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin/call-in-tmux"


class CallInTmuxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="call-in-tmux-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.ws = self.base / "workspace"
        self.repo = self.ws / "call-in-tmux"
        self.ws.mkdir()
        # Minimal copy: bin + lib + config + fake engines
        shutil.copytree(ROOT / "bin", self.repo / "bin")
        shutil.copytree(ROOT / "lib", self.repo / "lib")
        shutil.copytree(ROOT / "config", self.repo / "config")
        self.fake = self.ws / "fake-bin"
        self.fake.mkdir()
        for name in ("codex-tmux", "kimi-tmux", "cx-kimi-tmux", "cx-cursor-tmux"):
            path = self.fake / name
            path.write_text(
                "#!/usr/bin/env bash\n"
                "echo FAKE:\"$0\" \"$@\"\n"
                "printf '%s\\n' \"$*\" > \"${CALL_IN_TMUX_FAKE_LOG:-/dev/null}\"\n"
            )
            path.chmod(0o755)
        matrix = {
            "version": 1,
            "defaults": {"engine": "cursor", "host": "auto"},
            "hosts": {
                "claude": {"aliases": ["cc"], "skill_install": str(self.base / "skills/claude/call"), "wake": "bg"},
                "codex": {"aliases": ["cx"], "skill_install": str(self.base / "skills/codex/call"), "wake": "stdin"},
                "kimi": {"aliases": ["km"], "skill_install": str(self.base / "skills/kimi/call"), "wake": "hook"},
            },
            "engines": {
                "codex": {"aliases": ["gpt"], "runners": {"default": [str(self.fake / "codex-tmux")]}},
                "cursor": {"aliases": ["cu", "agent"], "runners": {"default": [str(self.fake / "cx-cursor-tmux")]}},
                "kimi": {
                    "aliases": ["km"],
                    "runners": {
                        "claude": [str(self.fake / "kimi-tmux")],
                        "codex": [str(self.fake / "cx-kimi-tmux")],
                        "default": [str(self.fake / "kimi-tmux")],
                    },
                },
            },
            "edges": [
                ["claude", "codex"],
                ["claude", "cursor"],
                ["claude", "kimi"],
                ["codex", "cursor"],
                ["codex", "kimi"],
                ["kimi", "cursor"],
            ],
        }
        self.matrix = self.repo / "config/matrix.json"
        self.matrix.write_text(json.dumps(matrix, indent=2))
        self.env = {
            **os.environ,
            "CALL_IN_TMUX_ROOT": str(self.repo),
            "CALL_IN_TMUX_WORKSPACE": str(self.ws),
            "CALL_IN_TMUX_MATRIX": str(self.matrix),
        }
        self.bin = self.repo / "bin/call-in-tmux"

    def run_cit(self, *args, env=None, check=False):
        return subprocess.run(
            ["bash", str(self.bin), *args],
            env=env or self.env,
            capture_output=True,
            text=True,
            check=check,
        )

    def test_matrix_lists_six_edges(self):
        r = self.run_cit("matrix")
        self.assertEqual(r.returncode, 0, r.stderr)
        for edge in (
            "claude → codex",
            "claude → cursor",
            "claude → kimi",
            "codex → cursor",
            "codex → kimi",
            "kimi → cursor",
        ):
            self.assertIn(edge, r.stdout)

    def test_resolve_picks_host_specific_kimi_runner(self):
        a = self.run_cit("resolve", "kimi", "--from", "claude")
        b = self.run_cit("resolve", "kimi", "--from", "codex")
        self.assertEqual(a.returncode, 0, a.stderr)
        self.assertEqual(b.returncode, 0, b.stderr)
        self.assertIn("kimi-tmux", a.stdout)
        self.assertIn("cx-kimi-tmux", b.stdout)

    def test_unsupported_edge_fails(self):
        r = self.run_cit("resolve", "codex", "--from", "kimi")
        self.assertEqual(r.returncode, 2)
        self.assertIn("不支持的边", r.stderr)

    def test_alias_engine_and_dispatch(self):
        log = self.base / "dispatch.log"
        env = dict(self.env, CALL_IN_TMUX_FAKE_LOG=str(log), CALL_IN_TMUX_HOST="codex")
        r = self.run_cit("to", "agent", "-t", "x", "-o", "/tmp/r.md", env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("cx-cursor-tmux", r.stderr)
        self.assertTrue(log.exists())
        self.assertIn("-t", log.read_text())

    def test_shortcut_command(self):
        r = self.run_cit("cursor", "--from", "kimi", "-h")
        # engine help may exit 0; ensure routed
        self.assertIn("kimi → cursor", r.stderr)


if __name__ == "__main__":
    unittest.main()
