import sys
from types import SimpleNamespace

import pytest

import orka.orka_cli as oc


def test_create_parser_contains_subcommands():
    parser = oc.create_parser()
    assert hasattr(parser, "parse_args")
    # ensure 'run' and 'memory' subcommands are present
    subparsers_action = None
    for a in parser._actions:
        if getattr(a, "dest", None) == "command":
            subparsers_action = a
            break
    assert subparsers_action is not None
    assert "run" in subparsers_action.choices
    assert "memory" in subparsers_action.choices


def test_main_no_command(monkeypatch):
    # Prevent setup_logging side-effects
    monkeypatch.setattr("orka.orka_cli.setup_logging", lambda v: None)

    # oc.main treats an empty list as falsy and will fall back to sys.argv;
    # create a truthy-but-empty sequence so parse_args receives an empty
    # iterable while the truthiness check passes.
    class TruthyEmpty(list):
        def __bool__(self):
            return True

    rc = oc.main(TruthyEmpty())
    assert rc == 1


def test_main_memory_stats_and_cleanup(monkeypatch):
    monkeypatch.setattr("orka.orka_cli.setup_logging", lambda v: None)

    # stats command has a default func that returns 0
    assert oc.main(["memory", "stats"]) == 0
    # cleanup command default func returns 0
    assert oc.main(["memory", "cleanup"]) == 0


def test_main_memory_watch_calls_watch(monkeypatch):
    # Patch memory_watch to validate it's called
    called = {"watch": False}

    def fake_watch(args):
        called["watch"] = True
        return 0

    monkeypatch.setattr("orka.orka_cli.setup_logging", lambda v: None)
    monkeypatch.setattr("orka.orka_cli.memory_watch", fake_watch)

    assert oc.main(["memory", "watch"]) == 0
    assert called["watch"]


def test_main_run_missing_config(monkeypatch):
    monkeypatch.setattr("orka.orka_cli.setup_logging", lambda v: None)

    # Provide empty config string - main should treat as missing and return 1
    assert oc.main(["run", "", "input.txt"]) == 1


def test_main_run_success_passes_args_to_run_cli(monkeypatch):
    monkeypatch.setattr("orka.orka_cli.setup_logging", lambda v: None)

    received = {}

    def fake_run_cli(args):
        # expect at least the run, config and input
        received["args"] = args
        return 0

    monkeypatch.setattr(oc, "run_cli", fake_run_cli)

    rc = oc.main(["run", "cfg.yaml", "hello", "--log-to-file"])
    assert rc == 0
    # run_cli should have been called with a list starting with 'run'
    assert isinstance(received.get("args"), list)
    assert "cfg.yaml" in received["args"]


def test_main_run_handles_unicode_exception(monkeypatch):
    monkeypatch.setattr("orka.orka_cli.setup_logging", lambda v: None)

    def fake_run_cli(args):
        raise Exception("charmap encode error")

    monkeypatch.setattr(oc, "run_cli", fake_run_cli)

    # main should catch the unicode-related message and return 0 per code
    assert oc.main(["run", "cfg.yaml", "inp"]) == 0


def test_main_run_handles_other_exception(monkeypatch):
    monkeypatch.setattr("orka.orka_cli.setup_logging", lambda v: None)

    def fake_run_cli(args):
        raise Exception("something went wrong")

    monkeypatch.setattr(oc, "run_cli", fake_run_cli)

    assert oc.main(["run", "cfg.yaml", "inp"]) == 1


def test_cli_main_system_exit_on_exception(monkeypatch):
    # Patch main to raise a generic exception so cli_main will call sys.exit(1)
    monkeypatch.setattr(oc, "main", lambda: (_ for _ in ()).throw(Exception("boom")))
    monkeypatch.setattr(oc, "sanitize_for_console", lambda s: "sanitized")

    with pytest.raises(SystemExit) as se:
        oc.cli_main()
    assert se.value.code == 1
