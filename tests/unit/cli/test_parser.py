import argparse
import pytest
from orka.cli.parser import create_parser, setup_subcommands
from orka.cli.orchestrator import run_orchestrator
from orka.cli.memory import memory_stats, memory_cleanup, memory_configure, memory_watch

def test_create_parser():
    """Test the creation of the main parser."""
    parser = create_parser()
    assert isinstance(parser, argparse.ArgumentParser)
    # Check for global arguments
    args = parser.parse_args(['-v', '--json'])
    assert args.verbose is True
    assert args.json is True

def test_setup_subcommands_run():
    """Test the 'run' subcommand."""
    parser = create_parser()
    setup_subcommands(parser)
    args = parser.parse_args(['run', 'config.yml', 'input text'])
    assert args.command == 'run'
    assert args.config == 'config.yml'
    assert args.input == 'input text'
    assert args.func == run_orchestrator

def test_setup_subcommands_memory_stats():
    """Test the 'memory stats' subcommand."""
    parser = create_parser()
    setup_subcommands(parser)
    args = parser.parse_args(['memory', 'stats', '--backend', 'redis'])
    assert args.command == 'memory'
    assert args.memory_command == 'stats'
    assert args.backend == 'redis'
    assert args.func == memory_stats

def test_setup_subcommands_memory_cleanup():
    """Test the 'memory cleanup' subcommand."""
    parser = create_parser()
    setup_subcommands(parser)
    args = parser.parse_args(['memory', 'cleanup', '--dry-run'])
    assert args.command == 'memory'
    assert args.memory_command == 'cleanup'
    assert args.dry_run is True
    assert args.func == memory_cleanup

def test_setup_subcommands_memory_configure():
    """Test the 'memory configure' subcommand."""
    parser = create_parser()
    setup_subcommands(parser)
    args = parser.parse_args(['memory', 'configure'])
    assert args.command == 'memory'
    assert args.memory_command == 'configure'
    assert args.func == memory_configure

def test_setup_subcommands_memory_watch():
    """Test the 'memory watch' subcommand."""
    parser = create_parser()
    setup_subcommands(parser)
    args = parser.parse_args(['memory', 'watch', '--interval', '10'])
    assert args.command == 'memory'
    assert args.memory_command == 'watch'
    assert args.interval == 10.0
    assert args.func == memory_watch
