from unittest.mock import MagicMock, patch

import pytest

from src.agent.runtime import AgentRuntime, RESERVED_CHILD_ENV_KEYS, RuntimeState


class TestAgentRuntime:
    def setup_method(self):
        self.runtime = AgentRuntime()

    @pytest.mark.parametrize("reserved_key", sorted(RESERVED_CHILD_ENV_KEYS))
    def test_start_rejects_reserved_child_env_overrides(self, reserved_key):
        with patch("src.agent.runtime.subprocess.Popen") as popen:
            started = self.runtime.start(
                "agent-1",
                ["python", "-c", "print('hello')"],
                env={reserved_key: "spoofed"},
            )

        assert not started
        popen.assert_not_called()
        assert self.runtime.get_state("agent-1") == RuntimeState.STOPPED

    def test_start_rejects_reserved_child_env_overrides_case_insensitively(self):
        with patch("src.agent.runtime.subprocess.Popen") as popen:
            started = self.runtime.start(
                "agent-1",
                ["python", "-c", "print('hello')"],
                env={"ao_agent_id": "spoofed"},
            )

        assert not started
        popen.assert_not_called()
        assert self.runtime.get_state("agent-1") == RuntimeState.STOPPED

    def test_start_allows_non_reserved_child_env(self):
        process = MagicMock()
        process.pid = 123
        process.poll.return_value = None

        with patch("src.agent.runtime.subprocess.Popen", return_value=process) as popen:
            started = self.runtime.start(
                "agent-1",
                ["python", "-c", "print('hello')"],
                env={"CUSTOM_SETTING": "enabled"},
            )

        assert started
        assert self.runtime.get_state("agent-1") == RuntimeState.RUNNING
        process_env = popen.call_args.kwargs["env"]
        assert process_env["CUSTOM_SETTING"] == "enabled"
        assert process_env["AO_AGENT_ID"] == "agent-1"
        assert process_env["AO_AGENT_MODE"] == "managed"
