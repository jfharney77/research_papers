"""Tests for the LaTeX build sandbox."""

from __future__ import annotations

from docbuilder.sandbox import hardened_tex_env, run_sandboxed


def test_hardened_env_disables_dangerous_tex_features(tmp_path):
    env = hardened_tex_env(tmp_path)
    assert env["shell_escape"] == "f"        # no \write18
    assert env["openin_any"] == "p"          # no reads outside the tree
    assert env["openout_any"] == "p"         # no writes outside the tree
    assert env["HOME"] == str(tmp_path)


def test_run_sandboxed_success(tmp_path):
    result = run_sandboxed(
        ["bash", "-c", "echo hello"],
        cwd=tmp_path,
        workspace=tmp_path,
        timeout=10,
    )
    assert result.returncode == 0
    assert "hello" in result.stdout
    assert result.timed_out is False


def test_run_sandboxed_times_out(tmp_path):
    result = run_sandboxed(
        ["bash", "-c", "sleep 30"],
        cwd=tmp_path,
        workspace=tmp_path,
        timeout=1,
    )
    assert result.timed_out is True
    assert result.returncode != 0


def test_run_sandboxed_propagates_hardened_env(tmp_path):
    # The child process must actually see the lockdown variables.
    result = run_sandboxed(
        ["bash", "-c", "echo $shell_escape$openin_any$openout_any"],
        cwd=tmp_path,
        workspace=tmp_path,
        timeout=10,
    )
    assert result.stdout.strip() == "fpp"
