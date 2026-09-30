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
                "printf '%s\\n' \"$@\" > \"${CALL_IN_TMUX_FAKE_LOG:-/dev/null}\"\n"
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
        self.assertIn(f"runner={self.fake / 'kimi-tmux'}\n", a.stdout)
        self.assertIn(f"runner={self.fake / 'cx-kimi-tmux'}\n", b.stdout)

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

    def test_engine_flags_after_double_dash_reach_engine(self):
        log = self.base / "dispatch.log"
        env = dict(self.env, CALL_IN_TMUX_FAKE_LOG=str(log), CALL_IN_TMUX_HOST="claude")
        r = self.run_cit("to", "codex", "-t", "x", "-o", "/tmp/r.md", "--",
                         "-c", 'model_reasoning_effort="max"', env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(log.read_text().splitlines(),
                         ["-t", "x", "-o", "/tmp/r.md", "--", "-c", 'model_reasoning_effort="max"'])

    def test_doctor_on_codex_fails_clearly(self):
        r = self.run_cit("doctor", "--to", "codex", "--from", "claude")
        self.assertEqual(r.returncode, 2)
        self.assertIn("codex 引擎没有 doctor", r.stderr)


class RepoMatrixTests(unittest.TestCase):
    """Checks against the shipped config/matrix.json and install.sh."""

    def setUp(self):
        # isolate from a user override at ~/.config/call-in-tmux/matrix.json
        self.xdg = tempfile.TemporaryDirectory(prefix="call-in-tmux-xdg-")
        self.addCleanup(self.xdg.cleanup)

    def repo_env(self, **extra):
        env = dict(os.environ, CALL_IN_TMUX_ROOT=str(ROOT), XDG_CONFIG_HOME=self.xdg.name, **extra)
        env.pop("CALL_IN_TMUX_MATRIX", None)
        return env

    def test_cx_shortcut_resolves_to_codex_engine(self):
        r = subprocess.run(["bash", str(BIN), "resolve", "cx", "--from", "claude"],
                           env=self.repo_env(), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("engine=codex\n", r.stdout)

    def cit_json(self, *args, env=None):
        return subprocess.run(
            ["bash", "-c", '. "$1/lib/common.sh"; shift; cit_json_py "$@"', "_", str(ROOT),
             str(ROOT / "config/matrix.json"), *args],
            env=env or self.repo_env(),
            capture_output=True, text=True, check=True,
        ).stdout

    def test_every_host_uses_kimi_cx_engine(self):
        cx = str(ROOT / "engines/kimi/cx/kimi-tmux")
        for host in ("claude", "codex", "kimi"):
            self.assertEqual(self.cit_json("runners", host, "kimi").splitlines(), [cx], host)

    def test_every_edge_runner_exists_inside_repo(self):
        for line in self.cit_json("edges").splitlines():
            host, engine = line.split("\t")
            for runner in self.cit_json("runners", host, engine).splitlines():
                self.assertTrue(runner.startswith(str(ROOT / "engines")), runner)
                self.assertTrue(os.access(runner, os.X_OK), runner)

    def test_claude_skill_follows_claude_config_dir(self):
        base = self.repo_env()
        base.pop("CLAUDE_CONFIG_DIR", None)
        self.assertEqual(self.cit_json("skill_install", "claude", env=base),
                         str(Path.home() / ".claude/skills/call") + "\n")
        env = dict(base, CLAUDE_CONFIG_DIR="/tmp/cac-env-x")
        self.assertEqual(self.cit_json("skill_install", "claude", env=env), "/tmp/cac-env-x/skills/call\n")

    def test_install_links_claude_skill_and_only_needed_hooks(self):
        with tempfile.TemporaryDirectory(prefix="call-in-tmux-home-") as tmp:
            home = Path(tmp)
            env = dict(os.environ, HOME=str(home), CLAUDE_CONFIG_DIR=str(home / "cac-env"),
                       XDG_CONFIG_HOME=str(home / ".config"),
                       CURSOR_HOME=str(home / ".cursor"), KIMI_CODE_HOME=str(home / ".kimi-code"))
            for k in ("CALL_IN_TMUX_ROOT", "CALL_IN_TMUX_MATRIX"):
                env.pop(k, None)
            r = subprocess.run(["bash", str(ROOT / "install.sh"), "--host", "claude", "--no-hooks"],
                               env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            link = home / "cac-env/skills/call"
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(), ROOT / "hosts/claude")
            self.assertFalse((home / ".claude").exists())

            # kimi host reaches only cursor → cursor hooks, no kimi config touched
            r = subprocess.run(["bash", str(ROOT / "install.sh"), "--host", "kimi", "--hooks-only"],
                               env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((home / ".cursor/hooks.json").is_file())
            self.assertFalse((home / ".kimi-code/config.toml").exists())

            r = subprocess.run(["bash", str(ROOT / "install.sh"), "--host", "nope", "--hooks-only"],
                               env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)
            self.assertIn("未知宿主", r.stderr)


if __name__ == "__main__":
    unittest.main()
