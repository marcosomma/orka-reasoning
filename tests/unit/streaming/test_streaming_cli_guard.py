"""Real CLI-path test for the streaming structure-only no-op guard.

The streaming runtime only calls a model when ORKA_STREAMING_HTTP_ENABLE=1. With it
unset, `orka streaming run` accepts input and emits structure events but produces no
response text. main() must warn loudly on stdout so this isn't mistaken for success.

This drives the actual main() streaming branch and mocks only StreamingOrchestrator
(the real external boundary that would otherwise spin up the live loop).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orka import orka_cli

CONFIG = "examples/stream/live_assist.yaml"


def _run_streaming(monkeypatch, http_enabled):
    monkeypatch.setenv("ORKA_ENABLE_STREAMING", "1")
    if http_enabled:
        monkeypatch.setenv("ORKA_STREAMING_HTTP_ENABLE", "1")
    else:
        monkeypatch.delenv("ORKA_STREAMING_HTTP_ENABLE", raising=False)

    mock_orch = MagicMock()
    mock_orch.run = AsyncMock(return_value=None)
    mock_orch.shutdown = AsyncMock(return_value=None)

    with patch.object(orka_cli, "StreamingOrchestrator", return_value=mock_orch):
        rc = orka_cli.main(["streaming", "run", CONFIG, "--session", "t"])
    return rc, mock_orch


@pytest.mark.unit
def test_streaming_warns_when_http_disabled(monkeypatch, capsys):
    rc, mock_orch = _run_streaming(monkeypatch, http_enabled=False)

    out = capsys.readouterr().out
    assert "structure-only mode" in out
    assert "ORKA_STREAMING_HTTP_ENABLE=1" in out
    assert rc == 0
    mock_orch.run.assert_awaited_once()  # it still ran, just in no-op mode


@pytest.mark.unit
def test_streaming_no_warning_when_http_enabled(monkeypatch, capsys):
    rc, _ = _run_streaming(monkeypatch, http_enabled=True)

    out = capsys.readouterr().out
    assert "structure-only mode" not in out
    assert rc == 0
