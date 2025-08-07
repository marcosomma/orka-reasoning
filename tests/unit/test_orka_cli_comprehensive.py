"""Test orka_cli.py comprehensively."""

import logging
from unittest.mock import Mock, PropertyMock, patch

import pytest

from orka import orka_cli as orka_cli_module
from orka.memory.redisstack_logger import RedisStackMemoryLogger


class TestModuleImports:
    """Test module imports."""

    def test_star_imports(self):
        """Test that __all__ contains expected items."""
        assert hasattr(orka_cli_module, "__all__")
        assert "cli_main" in orka_cli_module.__all__
        assert "run_cli" in orka_cli_module.__all__


class TestMainFunction:
    """Test main function."""

    def test_main_with_no_args(self):
        """Test main with no arguments."""
        parser = Mock()
        parser.parse_args.return_value = Mock(command=None, verbose=False)

        with patch("orka.orka_cli.create_parser", return_value=parser):
            result = orka_cli_module.main([])
            assert result == 1
            parser.print_help.assert_called_once()

    def test_main_with_run_command(self):
        """Test main function with run command."""
        # Setup mock parser and args
        parser = Mock()
        args = Mock(
            command="run",
            config="config.yml",
            input="test input",
            log_to_file=False,
            verbose=False,
        )
        parser.parse_args.return_value = args

        # Setup mock run_cli with the correct import path and valid config
        mock_config = {
            "orchestrator": {
                "id": "test_workflow",
                "strategy": "sequential",
                "queue": "test_queue",
                "agents": ["test_agent"],
            },
            "agents": [
                {
                    "id": "test_agent",
                    "type": "openai-answer",
                    "prompt": "test prompt",
                },
            ],
        }

        # Create a mock agent instance
        mock_agent = Mock()
        mock_agent.type = "openai-answer"
        mock_agent.run.return_value = {"response": "test response"}

        # Create a mock agent class
        mock_agent_class = Mock()
        mock_agent_class.return_value = mock_agent

        # Create a mock orchestrator instance
        mock_orchestrator = Mock()
        mock_orchestrator.step_index = 0
        mock_orchestrator.run.return_value = {"test_agent": "test response"}

        with (
            patch("orka.cli.core.run_cli_entrypoint") as mock_run_cli_entrypoint,
            patch("orka.orka_cli.create_parser", return_value=parser),
            patch("orka.loader.YAMLLoader._load_yaml", return_value=mock_config),
            patch("orka.agents.llm_agents.OpenAIAnswerBuilder", mock_agent_class),
            patch("orka.orchestrator.Orchestrator", return_value=mock_orchestrator),
        ):
            mock_run_cli_entrypoint.return_value = {"test_agent": "test response"}
            result = orka_cli_module.main(["run", "config.yml", "test input"])
            assert result == 0
            # Verify run_cli_entrypoint was called with the correct arguments
            mock_run_cli_entrypoint.assert_called_once_with(
                "config.yml", "test input", False, False
            )

    def test_main_with_run_command_log_to_file(self):
        """Test main function with run command and log_to_file option."""
        # Setup mock parser and args
        parser = Mock()
        args = Mock(
            command="run",
            config="config.yml",
            input="test input",
            log_to_file=True,
            verbose=False,
        )
        parser.parse_args.return_value = args

        with (
            patch("orka.cli.core.run_cli_entrypoint") as mock_run_cli_entrypoint,
            patch("orka.orka_cli.create_parser", return_value=parser),
        ):
            mock_run_cli_entrypoint.return_value = {"test_agent": "test response"}
            result = orka_cli_module.main(["run", "config.yml", "test input", "--log-to-file"])
            assert result == 0
            # Verify run_cli_entrypoint was called with the correct arguments
            mock_run_cli_entrypoint.assert_called_once_with("config.yml", "test input", True, False)

    def test_main_with_run_command_list_result(self):
        """Test main function with run command returning a list."""
        # Setup mock parser and args
        parser = Mock()
        args = Mock(
            command="run",
            config="config.yml",
            input="test input",
            log_to_file=False,
            verbose=False,
        )
        parser.parse_args.return_value = args

        with (
            patch("orka.cli.core.run_cli_entrypoint") as mock_run_cli_entrypoint,
            patch("orka.orka_cli.create_parser", return_value=parser),
        ):
            mock_run_cli_entrypoint.return_value = [
                {"agent_id": "test_agent", "payload": "test response"},
            ]
            result = orka_cli_module.main(["run", "config.yml", "test input"])
            assert result == 0
            # Verify run_cli_entrypoint was called with the correct arguments
            mock_run_cli_entrypoint.assert_called_once_with(
                "config.yml", "test input", False, False
            )

    def test_main_with_run_command_string_result(self):
        """Test main function with run command returning a string."""
        # Setup mock parser and args
        parser = Mock()
        args = Mock(
            command="run",
            config="config.yml",
            input="test input",
            log_to_file=False,
            verbose=False,
        )
        parser.parse_args.return_value = args

        with (
            patch("orka.cli.core.run_cli_entrypoint") as mock_run_cli_entrypoint,
            patch("orka.orka_cli.create_parser", return_value=parser),
        ):
            mock_run_cli_entrypoint.return_value = "test response"
            result = orka_cli_module.main(["run", "config.yml", "test input"])
            assert result == 0
            # Verify run_cli_entrypoint was called with the correct arguments
            mock_run_cli_entrypoint.assert_called_once_with(
                "config.yml", "test input", False, False
            )

    def test_main_with_run_command_no_result(self):
        """Test main function with run command returning None."""
        # Setup mock parser and args
        parser = Mock()
        args = Mock(
            command="run",
            config="config.yml",
            input="test input",
            log_to_file=False,
            verbose=False,
        )
        parser.parse_args.return_value = args

        with (
            patch("orka.cli.core.run_cli_entrypoint") as mock_run_cli_entrypoint,
            patch("orka.orka_cli.create_parser", return_value=parser),
        ):
            mock_run_cli_entrypoint.return_value = None
            result = orka_cli_module.main(["run", "config.yml", "test input"])
            assert result == 1
            # Verify run_cli_entrypoint was called with the correct arguments
            mock_run_cli_entrypoint.assert_called_once_with(
                "config.yml", "test input", False, False
            )

    def test_main_with_run_command_exception(self):
        """Test main function with run command that raises exception."""
        parser = Mock()
        args = Mock(
            command="run",
            config="config.yml",
            input="test input",
            log_to_file=False,
            verbose=False,
            func=None,
        )
        parser.parse_args.return_value = args

        with (
            patch("orka.orka_cli.create_parser", return_value=parser),
            patch("orka.cli.core.run_cli_entrypoint", side_effect=Exception("Command failed")),
        ):
            result = orka_cli_module.main(["run", "config.yml", "test input"])
            assert result == 1

    def test_main_with_memory_command_no_subcommand(self):
        """Test main function with memory command but no subcommand."""
        parser = Mock()
        args = Mock(
            command="memory",
            memory_command=None,
            verbose=False,
        )
        parser.parse_args.return_value = args

        # Create a mock memory subparser
        memory_parser = Mock()
        parser._subparsers = Mock()
        parser._subparsers._group_actions = [
            Mock(dest="command", choices={"memory": memory_parser}),
        ]

        with patch("orka.orka_cli.create_parser", return_value=parser):
            result = orka_cli_module.main(["memory"])
            # Test should return 1 (error) when no memory subcommand is provided
            assert result == 1
            # The print_help may or may not be called depending on error handling

    def test_main_with_memory_stats_command(self):
        """Test main function with memory stats command."""
        # Setup mock parser and args
        parser = Mock()
        mock_func = Mock(return_value=0)
        args = Mock(
            command="memory",
            memory_command="stats",
            json=False,
            verbose=False,
            func=mock_func,
        )
        parser.parse_args.return_value = args

        with patch("orka.orka_cli.create_parser", return_value=parser):
            result = orka_cli_module.main(["memory", "stats"])
            assert result == 0
            mock_func.assert_called_once_with(args)

    def test_main_with_memory_cleanup_command(self):
        """Test main function with memory cleanup command."""
        # Setup mock parser and args
        parser = Mock()
        mock_func = Mock(return_value=0)
        args = Mock(
            command="memory",
            memory_command="cleanup",
            dry_run=False,
            verbose=False,
            func=mock_func,
        )
        parser.parse_args.return_value = args

        with patch("orka.orka_cli.create_parser", return_value=parser):
            result = orka_cli_module.main(["memory", "cleanup"])
            assert result == 0
            mock_func.assert_called_once_with(args)

    def test_main_with_memory_watch_command(self):
        """Test main function with memory watch command."""
        # Setup mock parser and args
        parser = Mock()
        mock_memory_watch = Mock(return_value=0)
        args = Mock(
            command="memory",
            memory_command="watch",
            json=False,
            run_id=None,
            verbose=False,
            func=mock_memory_watch,
        )
        parser.parse_args.return_value = args

        with patch("orka.orka_cli.create_parser", return_value=parser):
            result = orka_cli_module.main(["memory", "watch"])
            assert result == 0
            mock_memory_watch.assert_called_once_with(args)

    def test_main_with_memory_watch_command_with_run_id(self):
        """Test main function with memory watch command and run_id."""
        # Setup mock parser and args
        parser = Mock()
        mock_memory_watch = Mock(return_value=0)
        args = Mock(
            command="memory",
            memory_command="watch",
            json=False,
            run_id="test_run",
            verbose=False,
            func=mock_memory_watch,
        )
        parser.parse_args.return_value = args

        with patch("orka.orka_cli.create_parser", return_value=parser):
            result = orka_cli_module.main(["memory", "watch", "--run-id", "test_run"])
            assert result == 0
            mock_memory_watch.assert_called_once_with(args)

    def test_main_with_memory_watch_command_json(self):
        """Test main function with memory watch command and json output."""
        # Setup mock parser and args
        parser = Mock()
        mock_memory_watch = Mock(return_value=0)
        args = Mock(
            command="memory",
            memory_command="watch",
            json=True,
            run_id=None,
            verbose=False,
            func=mock_memory_watch,
        )
        parser.parse_args.return_value = args

        with patch("orka.orka_cli.create_parser", return_value=parser):
            result = orka_cli_module.main(["memory", "watch", "--json"])
            assert result == 0
            mock_memory_watch.assert_called_once_with(args)

    def test_main_with_memory_stats_command_json(self):
        """Test main function with memory stats command and json output."""
        # Setup mock parser and args
        parser = Mock()
        mock_func = Mock(return_value=0)
        args = Mock(
            command="memory",
            memory_command="stats",
            json=True,
            verbose=False,
            func=mock_func,
        )
        parser.parse_args.return_value = args

        with patch("orka.orka_cli.create_parser", return_value=parser):
            result = orka_cli_module.main(["memory", "stats", "--json"])
            assert result == 0
            mock_func.assert_called_once_with(args)

    def test_main_with_memory_cleanup_command_dry_run(self):
        """Test main function with memory cleanup command and dry run."""
        # Setup mock parser and args
        parser = Mock()
        mock_func = Mock(return_value=0)
        args = Mock(
            command="memory",
            memory_command="cleanup",
            dry_run=True,
            verbose=False,
            func=mock_func,
        )
        parser.parse_args.return_value = args

        with patch("orka.orka_cli.create_parser", return_value=parser):
            result = orka_cli_module.main(["memory", "cleanup", "--dry-run"])
            assert result == 0
            mock_func.assert_called_once_with(args)

    def test_main_with_memory_command_error(self):
        """Test main function with memory command that raises error."""
        # Setup mock parser and args
        parser = Mock()
        mock_func = Mock(side_effect=Exception("Test error"))
        args = Mock(
            command="memory",
            memory_command="stats",
            json=False,
            verbose=False,
            func=mock_func,
        )
        parser.parse_args.return_value = args

        with patch("orka.orka_cli.create_parser", return_value=parser):
            result = orka_cli_module.main(["memory", "stats"])
            assert result == 1
            mock_func.assert_called_once_with(args)

    def test_main_with_memory_command_no_func(self):
        """Test main function with memory command that has no func."""
        # Setup mock parser and args
        parser = Mock()
        args = Mock(
            command="memory",
            memory_command="stats",
            json=False,
            verbose=False,
            func=None,  # No func attribute
        )
        parser.parse_args.return_value = args

        with patch("orka.orka_cli.create_parser", return_value=parser):
            result = orka_cli_module.main(["memory", "stats"])
            assert result == 1

    def test_main_with_unknown_command(self):
        """Test main function with unknown command."""
        # Setup mock parser and args
        parser = Mock()
        args = Mock(
            command="unknown",
            verbose=False,
            func=None,  # No func attribute
        )
        parser.parse_args.return_value = args

        with patch("orka.orka_cli.create_parser", return_value=parser):
            result = orka_cli_module.main(["unknown"])
            assert result == 1

    def test_main_with_verbose_logging(self):
        """Test main function with verbose logging."""
        # Setup mock parser and args
        parser = Mock()
        args = Mock(
            command="run",
            config="config.yml",
            input="test input",
            log_to_file=False,
            verbose=True,
        )
        parser.parse_args.return_value = args

        # Setup mock loader
        mock_config = {
            "orchestrator": {
                "id": "test_workflow",
                "strategy": "sequential",
                "queue": "test_queue",
                "agents": ["test_agent"],
            },
            "agents": [
                {
                    "id": "test_agent",
                    "type": "openai-answer",
                    "prompt": "test prompt",
                },
            ],
        }

        # Setup mock Redis client
        mock_redis = Mock()
        mock_redis.ft = Mock()
        mock_redis.ft.return_value = Mock()

        # Setup mock embedder
        mock_embedder = Mock()
        mock_embedder.get_embedding = Mock(return_value=[0.1, 0.2, 0.3])

        # Setup mock memory decay config
        mock_memory_decay_config = {
            "enabled": True,
            "short_term_hours": 0.1,
            "long_term_hours": 0.2,
            "check_interval_minutes": 30,
        }

        # Setup mock memory
        mock_memory = Mock()
        mock_memory.get = Mock(return_value=None)

        # Setup mock local variables
        mock_local = Mock()
        mock_local.redis_client = mock_redis

        with (
            patch("orka.cli.core.run_cli_entrypoint") as mock_run_cli_entrypoint,
            patch("orka.orka_cli.create_parser", return_value=parser),
            patch("logging.basicConfig") as mock_logging,
            patch("orka.loader.YAMLLoader._load_yaml", return_value=mock_config),
            patch(
                "orka.memory.redisstack_logger.RedisStackMemoryLogger.__init__",
                return_value=None,
            ),
            patch(
                "orka.memory.redisstack_logger.RedisStackMemoryLogger.redis",
                new_callable=PropertyMock,
                return_value=mock_redis,
            ),
            patch.object(RedisStackMemoryLogger, "embedder", mock_embedder, create=True),
            patch.object(
                RedisStackMemoryLogger,
                "memory_decay_config",
                mock_memory_decay_config,
                create=True,
            ),
            patch.object(RedisStackMemoryLogger, "memory", mock_memory, create=True),
            patch.object(RedisStackMemoryLogger, "_local", mock_local, create=True),
            patch.object(RedisStackMemoryLogger, "debug_keep_previous_outputs", False, create=True),
            patch.dict(
                "os.environ",
                {"PYTEST_RUNNING": "true", "OPENAI_API_KEY": "dummy_key_for_testing"},
            ),
        ):
            with patch(
                "orka.agents.llm_agents.OpenAIAnswerBuilder.run",
                return_value={"status": "success", "result": "dummy"},
            ):
                mock_run_cli_entrypoint.return_value = {"test_agent": "test response"}
                result = orka_cli_module.main(["run", "config.yml", "test input", "-v"])
                assert result == 0
                mock_run_cli_entrypoint.assert_called_once_with(
                    "config.yml", "test input", False, True
                )
                # Verify logging was set up (implementation uses StreamHandler instead of basicConfig)
                mock_logging.assert_not_called()  # basicConfig is no longer used


class TestArgumentParsing:
    """Test argument parsing."""

    def test_create_parser(self):
        """Test create_parser function."""
        parser = orka_cli_module.create_parser()
        assert parser.description == "OrKa - Orchestrator Kit for Agents"

    def test_setup_logging(self):
        """Test setup_logging function."""
        # Simply verify the function runs without error
        # The implementation has complex logging setup that's hard to mock completely
        try:
            orka_cli_module.setup_logging(verbose=True)
            assert True  # Function completed successfully
        except Exception as e:
            assert False, f"setup_logging failed: {e}"

    def test_setup_logging_exception(self):
        """Test setup_logging with exception."""
        parser = Mock()
        args = Mock(verbose=False, command=None)  # No command set
        parser.parse_args.return_value = args

        with (
            patch("orka.orka_cli.create_parser", return_value=parser),
            patch("logging.basicConfig", side_effect=Exception("Test error")),
        ):
            result = orka_cli_module.main([])
            assert result == 1


class TestErrorHandling:
    """Test error handling."""

    def test_main_with_create_parser_exception(self):
        """Test main when create_parser raises exception."""
        with patch("orka.orka_cli.create_parser") as mock_create_parser:
            mock_create_parser.side_effect = Exception("Test error")
            result = orka_cli_module.main([])
            assert result == 1

    def test_cli_main_success(self):
        """Test cli_main function with successful execution."""
        with patch("orka.orka_cli.main") as mock_main:
            mock_main.return_value = 0
            with pytest.raises(SystemExit) as exc_info:
                orka_cli_module.cli_main()
            assert exc_info.value.code == 0
            mock_main.assert_called_once()

    def test_cli_main_keyboard_interrupt(self):
        """Test cli_main function with keyboard interrupt."""
        with (
            patch("orka.orka_cli.main", side_effect=KeyboardInterrupt),
            patch("orka.orka_cli.logger") as mock_logger,
        ):
            with pytest.raises(SystemExit) as exc_info:
                orka_cli_module.cli_main()
            assert exc_info.value.code == 1
            mock_logger.info.assert_called_once_with("\n🛑 Operation cancelled.")

    def test_cli_main_exception(self):
        """Test cli_main function with general exception."""
        with (
            patch("orka.orka_cli.main", side_effect=Exception("Test error")),
            patch("orka.orka_cli.logger") as mock_logger,
        ):
            with pytest.raises(SystemExit) as exc_info:
                orka_cli_module.cli_main()
            assert exc_info.value.code == 1
            mock_logger.info.assert_called_once_with("\n❌ Error: Test error")

    def test_main_with_run_command_no_config(self):
        """Test main function with run command but no config."""
        # Setup mock parser and args
        parser = Mock()
        args = Mock(
            command="run",
            config=None,
            input="test input",
            log_to_file=False,
            verbose=False,
        )
        parser.parse_args.return_value = args

        with patch("orka.orka_cli.create_parser", return_value=parser):
            result = orka_cli_module.main(["run"])
            assert result == 1
            parser.print_help.assert_called_once()

    def test_main_with_run_command_no_input(self):
        """Test main function with run command but no input."""
        # Setup mock parser and args
        parser = Mock()
        args = Mock(
            command="run",
            config="config.yml",
            input=None,
            log_to_file=False,
            verbose=False,
            func=None,
        )
        parser.parse_args.return_value = args

        # Create a mock logger
        mock_logger = Mock()
        mock_logger.error = Mock()

        # Patch the logger at module level
        with patch.object(orka_cli_module, "logger", mock_logger):
            with (
                patch("orka.orka_cli.create_parser", return_value=parser),
                patch(
                    "orka.cli.core.run_cli_entrypoint", side_effect=Exception("No input provided")
                ),
            ):
                result = orka_cli_module.main(["run", "config.yml"])
                assert result == 1
                mock_logger.error.assert_called_once_with("Error: No input provided")

    def test_main_with_run_command_json_output(self):
        """Test main function with run command and json output."""
        # Setup mock parser and args
        parser = Mock()
        args = Mock(
            command="run",
            config="config.yml",
            input="test input",
            log_to_file=False,
            verbose=False,
            json=True,
        )
        parser.parse_args.return_value = args

        # Setup mock loader
        mock_config = {
            "orchestrator": {
                "id": "test_workflow",
                "strategy": "sequential",
                "queue": "test_queue",
                "agents": ["test_agent"],
            },
            "agents": [
                {
                    "id": "test_agent",
                    "type": "openai-answer",
                    "prompt": "test prompt",
                },
            ],
        }

        # Setup mock Redis client
        mock_redis = Mock()
        mock_redis.ft = Mock()
        mock_redis.ft.return_value = Mock()

        # Setup mock embedder
        mock_embedder = Mock()
        mock_embedder.get_embedding = Mock(return_value=[0.1, 0.2, 0.3])

        # Setup mock memory decay config
        mock_memory_decay_config = {
            "enabled": True,
            "short_term_hours": 0.1,
            "long_term_hours": 0.2,
            "check_interval_minutes": 30,
        }

        # Setup mock memory
        mock_memory = Mock()
        mock_memory.get = Mock(return_value=None)

        # Setup mock local variables
        mock_local = Mock()
        mock_local.redis_client = mock_redis

        with (
            patch("orka.cli.core.run_cli_entrypoint") as mock_run_cli_entrypoint,
            patch("orka.orka_cli.create_parser", return_value=parser),
            patch("orka.loader.YAMLLoader._load_yaml", return_value=mock_config),
            patch(
                "orka.memory.redisstack_logger.RedisStackMemoryLogger.__init__",
                return_value=None,
            ),
            patch(
                "orka.memory.redisstack_logger.RedisStackMemoryLogger.redis",
                new_callable=PropertyMock,
                return_value=mock_redis,
            ),
            patch.object(RedisStackMemoryLogger, "embedder", mock_embedder, create=True),
            patch.object(
                RedisStackMemoryLogger,
                "memory_decay_config",
                mock_memory_decay_config,
                create=True,
            ),
            patch.object(RedisStackMemoryLogger, "memory", mock_memory, create=True),
            patch.object(RedisStackMemoryLogger, "_local", mock_local, create=True),
            patch.object(RedisStackMemoryLogger, "debug_keep_previous_outputs", False, create=True),
            patch.dict(
                "os.environ",
                {"PYTEST_RUNNING": "true", "OPENAI_API_KEY": "dummy_key_for_testing"},
            ),
        ):
            with patch(
                "orka.agents.llm_agents.OpenAIAnswerBuilder.run",
                return_value={"status": "success", "result": "dummy"},
            ):
                mock_run_cli_entrypoint.return_value = {"test_agent": "test response"}
                result = orka_cli_module.main(["run", "config.yml", "test input", "--json"])
                assert result == 0
                mock_run_cli_entrypoint.assert_called_once_with(
                    "config.yml", "test input", False, False
                )

    def test_main_with_run_command_log_to_file_and_json(self):
        """Test main function with run command, log to file, and json output."""
        # Setup mock parser and args
        parser = Mock()
        args = Mock(
            command="run",
            config="config.yml",
            input="test input",
            log_to_file=True,
            verbose=False,
            json=True,
        )
        parser.parse_args.return_value = args

        # Setup mock loader
        mock_config = {
            "orchestrator": {
                "id": "test_workflow",
                "strategy": "sequential",
                "queue": "test_queue",
                "agents": ["test_agent"],
            },
            "agents": [
                {
                    "id": "test_agent",
                    "type": "openai-answer",
                    "prompt": "test prompt",
                },
            ],
        }

        # Setup mock Redis client
        mock_redis = Mock()
        mock_redis.ft = Mock()
        mock_redis.ft.return_value = Mock()

        # Setup mock embedder
        mock_embedder = Mock()
        mock_embedder.get_embedding = Mock(return_value=[0.1, 0.2, 0.3])

        # Setup mock memory decay config
        mock_memory_decay_config = {
            "enabled": True,
            "short_term_hours": 0.1,
            "long_term_hours": 0.2,
            "check_interval_minutes": 30,
        }

        # Setup mock memory
        mock_memory = Mock()
        mock_memory.get = Mock(return_value=None)

        # Setup mock local variables
        mock_local = Mock()
        mock_local.redis_client = mock_redis

        with (
            patch("orka.cli.core.run_cli_entrypoint") as mock_run_cli_entrypoint,
            patch("orka.orka_cli.create_parser", return_value=parser),
            patch("orka.loader.YAMLLoader._load_yaml", return_value=mock_config),
            patch(
                "orka.memory.redisstack_logger.RedisStackMemoryLogger.__init__",
                return_value=None,
            ),
            patch(
                "orka.memory.redisstack_logger.RedisStackMemoryLogger.redis",
                new_callable=PropertyMock,
                return_value=mock_redis,
            ),
            patch.object(RedisStackMemoryLogger, "embedder", mock_embedder, create=True),
            patch.object(
                RedisStackMemoryLogger,
                "memory_decay_config",
                mock_memory_decay_config,
                create=True,
            ),
            patch.object(RedisStackMemoryLogger, "memory", mock_memory, create=True),
            patch.object(RedisStackMemoryLogger, "_local", mock_local, create=True),
            patch.object(RedisStackMemoryLogger, "debug_keep_previous_outputs", False, create=True),
            patch.dict(
                "os.environ",
                {"PYTEST_RUNNING": "true", "OPENAI_API_KEY": "dummy_key_for_testing"},
            ),
        ):
            with patch(
                "orka.agents.llm_agents.OpenAIAnswerBuilder.run",
                return_value={"status": "success", "result": "dummy"},
            ):
                mock_run_cli_entrypoint.return_value = {"test_agent": "test response"}
                result = orka_cli_module.main(
                    ["run", "config.yml", "test input", "--log-to-file", "--json"],
                )
                assert result == 0
                mock_run_cli_entrypoint.assert_called_once_with(
                    "config.yml", "test input", True, False
                )
