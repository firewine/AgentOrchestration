import pytest
import asyncio

from src.agent.sandbox import AgentSandbox


class TestAgentSandbox:
    def test_managed_run_removes_temp_files_after_success(self, tmp_path):
        sandbox = AgentSandbox(str(tmp_path))

        with sandbox.managed_run("agent-1") as run_path:
            temp_file = run_path / "work.tmp"
            temp_file.write_text("scratch")
            assert temp_file.exists()

        assert not run_path.exists()
        assert sandbox.get_path("agent-1") is None
        assert sandbox.get_terminal_outcome("agent-1") == {
            "status": "completed",
            "path": str(run_path),
            "cleanup_removed": True,
        }

    def test_managed_run_removes_temp_files_after_failure(self, tmp_path):
        sandbox = AgentSandbox(str(tmp_path))

        with pytest.raises(RuntimeError):
            with sandbox.managed_run("agent-1") as run_path:
                (run_path / "work.tmp").write_text("scratch")
                raise RuntimeError("boom")

        assert not run_path.exists()
        assert sandbox.get_path("agent-1") is None
        assert sandbox.get_terminal_outcome("agent-1") == {
            "status": "failed",
            "path": str(run_path),
            "cleanup_removed": True,
        }

    def test_terminal_outcome_is_recorded_once(self, tmp_path):
        sandbox = AgentSandbox(str(tmp_path))

        with pytest.raises(RuntimeError):
            with sandbox.managed_run("agent-1"):
                raise RuntimeError("first")

        with sandbox.managed_run("agent-1"):
            pass

        assert sandbox.get_terminal_outcome("agent-1")["status"] == "failed"

    def test_terminal_outcome_returns_copy(self, tmp_path):
        sandbox = AgentSandbox(str(tmp_path))

        with sandbox.managed_run("agent-1"):
            pass

        outcome = sandbox.get_terminal_outcome("agent-1")
        outcome["status"] = "mutated"

        assert sandbox.get_terminal_outcome("agent-1")["status"] == "completed"

    def test_managed_run_records_cancelled_outcome(self, tmp_path):
        sandbox = AgentSandbox(str(tmp_path))

        with pytest.raises(asyncio.CancelledError):
            with sandbox.managed_run("agent-1") as run_path:
                (run_path / "work.tmp").write_text("scratch")
                raise asyncio.CancelledError()

        assert not run_path.exists()
        assert sandbox.get_terminal_outcome("agent-1")["status"] == "cancelled"

    def test_destroy_keeps_sandbox_tracked_when_delete_fails(self, tmp_path, monkeypatch):
        sandbox = AgentSandbox(str(tmp_path))
        run_path = sandbox.create("agent-1")

        def fail_rmtree(path):
            raise OSError("permission denied")

        monkeypatch.setattr("src.agent.sandbox.shutil.rmtree", fail_rmtree)

        with pytest.raises(OSError):
            sandbox.destroy("agent-1")

        assert sandbox.get_path("agent-1") == run_path
        assert run_path.exists()

    def test_cleanup_all_removes_owned_base_path(self):
        sandbox = AgentSandbox()
        base_path = sandbox.base_path
        sandbox.create("agent-1")

        sandbox.cleanup_all()

        assert not base_path.exists()

    def test_cleanup_all_preserves_user_provided_base_path(self, tmp_path):
        sandbox = AgentSandbox(str(tmp_path))
        sandbox.create("agent-1")

        sandbox.cleanup_all()

        assert tmp_path.exists()
        assert list(tmp_path.iterdir()) == []
