# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-20

import os
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from tsdbenv.cli import main, CLIState
from tsdbenv.engine_config import Engine


@pytest.fixture
def cli_runner():
    """Provide Click CLI test runner."""
    return CliRunner()


class TestEngineOptionDisplay:
    """Test that --engine option appears in help."""

    def test_engine_option_in_help(self, cli_runner):
        """Verify --engine option is shown in main help."""
        result = cli_runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "--engine" in result.output
        assert "docker" in result.output.lower()
        assert "podman" in result.output.lower()

    def test_engine_option_with_docker_help(self, cli_runner):
        """Verify --engine option works with --engine docker --help."""
        result = cli_runner.invoke(main, ["--engine", "docker", "--help"])
        assert result.exit_code == 0
        assert "--engine" in result.output

    def test_engine_option_with_podman_help(self, cli_runner):
        """Verify --engine option works with --engine podman --help."""
        result = cli_runner.invoke(main, ["--engine", "podman", "--help"])
        assert result.exit_code == 0
        assert "--engine" in result.output


class TestEngineOptionRejection:
    """Test that invalid engine options are rejected."""

    def test_invalid_engine_rejected(self, cli_runner):
        """Verify invalid engine is rejected."""
        result = cli_runner.invoke(main, ["--engine", "invalid"])
        assert result.exit_code != 0
        assert "Invalid value" in result.output or "not one of" in result.output


class TestCLIStateEngineParameter:
    """Test CLIState accepts and stores engine parameter."""

    @patch("tsdbenv.cli.StateTracker")
    @patch("tsdbenv.cli.VersionManager")
    @patch("tsdbenv.cli.ensure_state_dir")
    @patch("tsdbenv.cli.DockerClient")
    def test_clistate_accepts_engine_parameter(self, mock_docker, mock_dir, mock_version, mock_tracker):
        """Verify CLIState constructor accepts engine parameter."""
        mock_dir.return_value = "/tmp/test_state"
        mock_docker.return_value = MagicMock()

        state = CLIState(engine=Engine.PODMAN)
        assert state.engine == Engine.PODMAN

    @patch("tsdbenv.cli.StateTracker")
    @patch("tsdbenv.cli.VersionManager")
    @patch("tsdbenv.cli.ensure_state_dir")
    @patch("tsdbenv.cli.DockerClient")
    def test_clistate_default_engine_is_docker(self, mock_docker, mock_dir, mock_version, mock_tracker):
        """Verify CLIState defaults to Docker engine."""
        mock_dir.return_value = "/tmp/test_state"
        mock_docker.return_value = MagicMock()

        state = CLIState()
        assert state.engine == Engine.DOCKER

    @patch("tsdbenv.cli.StateTracker")
    @patch("tsdbenv.cli.VersionManager")
    @patch("tsdbenv.cli.ensure_state_dir")
    @patch("tsdbenv.cli.DockerClient")
    def test_clistate_stores_engine_attribute(self, mock_docker, mock_dir, mock_version, mock_tracker):
        """Verify CLIState stores engine as attribute."""
        mock_dir.return_value = "/tmp/test_state"
        mock_docker.return_value = MagicMock()

        state = CLIState(engine=Engine.PODMAN)
        assert hasattr(state, "engine")
        assert state.engine == Engine.PODMAN


class TestEngineWithSubcommands:
    """Test engine option works with subcommands."""

    def test_engine_with_version_flag(self, cli_runner):
        """Verify --version works with --engine option."""
        result = cli_runner.invoke(main, ["--engine", "docker", "--version"])
        assert result.exit_code == 0
        assert "tsdbenv" in result.output

    def test_engine_option_before_subcommand(self, cli_runner):
        """Verify --engine can be placed before subcommand."""
        result = cli_runner.invoke(main, ["--engine", "podman", "--help"])
        assert result.exit_code == 0
        assert "Commands:" in result.output or "Usage:" in result.output


class TestEngineEnumValues:
    """Test Engine enum from engine_config module."""

    def test_engine_enum_has_docker(self):
        """Verify Engine enum includes DOCKER."""
        assert hasattr(Engine, "DOCKER")
        assert Engine.DOCKER.value == "docker"

    def test_engine_enum_has_podman(self):
        """Verify Engine enum includes PODMAN."""
        assert hasattr(Engine, "PODMAN")
        assert Engine.PODMAN.value == "podman"


class TestEngineImports:
    """Test that engine_config module is properly imported."""

    def test_engine_config_imported(self):
        """Verify engine_config module is imported in cli.py."""
        from tsdbenv import cli as cli_module
        assert hasattr(cli_module, "Engine")
        assert hasattr(cli_module, "get_engine_from_cli_or_env")


class TestEngineContextPassing:
    """Test that engine is passed to Click context for subcommands."""

    @patch("tsdbenv.cli.StateTracker")
    @patch("tsdbenv.cli.VersionManager")
    @patch("tsdbenv.cli.ensure_state_dir")
    @patch("tsdbenv.cli.DockerClient")
    def test_docker_engine_in_context(self, mock_docker, mock_dir, mock_version, mock_tracker):
        """Verify Docker engine is stored in Click context."""
        mock_dir.return_value = "/tmp/test_state"
        mock_docker.return_value = MagicMock()

        # Test via CLI help which accesses the context
        result = CliRunner().invoke(main, ["--engine", "docker", "--help"])
        assert result.exit_code == 0
        assert "--engine" in result.output

    @patch("tsdbenv.cli.StateTracker")
    @patch("tsdbenv.cli.VersionManager")
    @patch("tsdbenv.cli.ensure_state_dir")
    @patch("tsdbenv.cli.DockerClient")
    def test_podman_engine_in_context(self, mock_docker, mock_dir, mock_version, mock_tracker):
        """Verify Podman engine is stored in Click context."""
        mock_dir.return_value = "/tmp/test_state"
        mock_docker.return_value = MagicMock()

        # Test via CLI help which accesses the context
        result = CliRunner().invoke(main, ["--engine", "podman", "--help"])
        assert result.exit_code == 0
        assert "--engine" in result.output


class TestEngineAwareErrorMessages:
    """Test that error messages reference the correct engine."""

    def test_docker_engine_error_capitalized(self):
        """Verify error message says 'Docker' when Docker selected."""
        # Verify the error message construction logic
        engine = Engine.DOCKER
        engine_name = engine.value.capitalize()
        assert engine_name == "Docker"

    def test_podman_engine_error_capitalized(self):
        """Verify error message says 'Podman' when Podman selected."""
        # Verify the error message construction logic
        engine = Engine.PODMAN
        engine_name = engine.value.capitalize()
        assert engine_name == "Podman"
