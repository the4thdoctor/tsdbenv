# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from tsdbenv import __version__
from tsdbenv.config_handler import ConfigHandler
from tsdbenv.docker_utils import DockerClient
from tsdbenv.models import Container
from tsdbenv.network_validator import NetworkValidator
from tsdbenv.state_tracker import StateTracker
from tsdbenv.utils import ensure_state_dir, generate_password
from tsdbenv.version_manager import VersionManager


def get_dockerfiles_dir() -> Path:
    """Get the path to the dockerfiles directory."""
    return Path(__file__).parent / "dockerfiles"


class CLIState:
    def __init__(self):
        self.state_dir = ensure_state_dir()
        self.state_tracker = StateTracker(state_dir=self.state_dir)
        self.version_manager = VersionManager(cache_dir=self.state_dir)
        self.docker_client = None
        self.engine_name = None
        self.connect_error = None
        self._connect_engine()

    def _connect_engine(self, engine: Optional[str] = None) -> None:
        try:
            self.docker_client = DockerClient(engine=engine)
            self.engine_name = self.docker_client.engine
            self.connect_error = None
        except (RuntimeError, ValueError) as e:
            self.docker_client = None
            self.engine_name = (engine or os.environ.get("TSDBENV_ENGINE") or "docker").strip().lower()
            self.connect_error = str(e)

    def set_engine(self, engine: str) -> None:
        """Switch container engine (e.g. after a --engine CLI flag)."""
        self._connect_engine(engine=engine)


cli_state = CLIState()


def engine_option(f):
    """Shared --engine option, usable on the group or on individual subcommands."""
    return click.option(
        "--engine",
        type=click.Choice(["docker", "podman"]),
        default=None,
        help="Container engine to use (default: docker, or $TSDBENV_ENGINE)",
    )(f)


def require_engine() -> None:
    """Abort with a clear, engine-specific error if the container engine isn't reachable."""
    if cli_state.docker_client is None:
        click.echo(f"❌ {cli_state.engine_name.capitalize()} is not available: {cli_state.connect_error}")
        click.echo("   Please install Docker: https://docs.docker.com/get-docker/")
        click.echo("   Or install Podman: https://podman.io/docs/installation")
        click.echo("   Select an engine with --engine docker/podman or $TSDBENV_ENGINE")
        raise click.Abort()


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show version and exit")
@engine_option
@click.pass_context
def main(ctx, version, engine):
    """tsdbenv - PostgreSQL + TimescaleDB environment manager."""
    if version:
        click.echo(f"tsdbenv {__version__}")
        ctx.exit(0)

    if engine:
        cli_state.set_engine(engine)

    if ctx.invoked_subcommand is None:
        require_engine()
        show_interactive_menu()


@main.command()
@click.option("--postgres", help="PostgreSQL version (e.g., 14)")
@click.option("--timescaledb", help="TimescaleDB version (e.g., 2.8.0)")
@click.option("--port", type=int, default=None, help="PostgreSQL port (default: 5432)")
@click.option(
    "--config", type=click.Path(exists=True), help="PostgreSQL config file path"
)
@click.option("--bind-ip", help="IP to bind container to (default: 127.0.0.1)")
@click.option("--force", is_flag=True, help="Override version compatibility check")
@engine_option
def new(postgres, timescaledb, port, config, bind_ip, force, engine):
    """Create a new PostgreSQL + TimescaleDB container."""
    if engine:
        cli_state.set_engine(engine)
    require_engine()

    if not postgres:
        postgres = click.prompt("PostgreSQL version", type=str)
    if not timescaledb:
        timescaledb = click.prompt("TimescaleDB version", type=str)

    if not force and not cli_state.version_manager.is_compatible(postgres, timescaledb):
        click.echo(
            f"❌ TimescaleDB {timescaledb} is not compatible with PostgreSQL {postgres}"
        )
        raise click.Abort()

    # Generate unique container name from current timestamp
    timestamp_hash = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
    name = f"tsdb-{timestamp_hash}"

    if config:
        try:
            ConfigHandler.parse_file(Path(config))
        except Exception as e:
            click.echo(f"❌ Failed to parse config: {e}")
            return

    # Default bind_ip to localhost if not specified
    if not bind_ip:
        bind_ip = "127.0.0.1"

    is_valid, warning = NetworkValidator.validate_bind_ip(bind_ip)
    if not is_valid:
        click.echo(warning)
        if not click.confirm("Continue anyway?"):
            return

    # Auto-find available port if not specified
    if port is None:
        port = NetworkValidator.find_available_port(bind_ip)
        click.echo(f"✅ Using port {port} (first available)")

    tsdbadmin_password = generate_password()

    # Build custom Docker image with TimescaleDB and init scripts
    try:
        dockerfile_dir = str(get_dockerfiles_dir())
        image_tag = f"tsdbenv:pg{postgres}-latest"
        click.echo(f"Building Docker image {image_tag}...")
        cli_state.docker_client.build_image(
            dockerfile_dir=dockerfile_dir,
            tag=image_tag,
            build_args={"PG_VERSION": postgres},
        )
    except Exception as e:
        click.echo(f"❌ Failed to build Docker image: {e}")
        raise click.Abort()

    container_id = cli_state.docker_client.create_container(
        image=image_tag,
        name=name,
        environment={"POSTGRES_PASSWORD": "postgres", "PGPASSWORD": tsdbadmin_password},
        ports={5432: port},
        tsdbadmin_password=tsdbadmin_password,
        bind_ip=bind_ip,
    )

    container = Container(
        name=name,
        postgres_version=postgres,
        timescaledb_version=timescaledb,
        created_at=datetime.now(),
        last_accessed_at=datetime.now(),
        config_path=config,
        docker_id=container_id,
        port=port,
        bind_ip=bind_ip,
        tsdbadmin_password=tsdbadmin_password,
    )
    cli_state.state_tracker.save_container(container)

    display_connection_info(container)


@main.command()
def list():
    """List all containers."""
    containers = cli_state.state_tracker.load_containers()

    if not containers:
        click.echo("No containers found.")
        return

    stale = cli_state.state_tracker.get_stale_containers(days=5)
    for s in stale:
        if click.confirm(f"Container '{s.name}' unused for 5+ days. Remove?"):
            cli_state.state_tracker.delete_container(s.name)

    click.echo(f"\n{'Name':<15} {'PG':<5} {'TSDB':<10} {'IP':<15} {'Port':<6}")
    click.echo("-" * 57)
    for c in containers:
        click.echo(
            f"{c.name:<15} {c.postgres_version:<5} {c.timescaledb_version:<10} {c.bind_ip:<15} {c.port:<6}"
        )


@main.command()
@click.argument("container_name", required=False)
@engine_option
def logs(container_name, engine):
    """Show container logs."""
    if engine:
        cli_state.set_engine(engine)
    require_engine()

    if not container_name:
        containers = cli_state.state_tracker.load_containers()
        if not containers:
            click.echo("No containers found.")
            return
        container_name = click.prompt(
            "Container name", type=click.Choice([c.name for c in containers])
        )

    container = next(
        (
            c
            for c in cli_state.state_tracker.load_containers()
            if c.name == container_name
        ),
        None,
    )
    if not container:
        click.echo(f"Container '{container_name}' not found.")
        return

    cli_state.state_tracker.mark_accessed(container_name)
    logs_output = cli_state.docker_client.get_container_logs(container.docker_id)
    click.echo(logs_output)


@main.command()
@click.argument("container_name", required=False)
@engine_option
def remove(container_name, engine):
    """Remove a container."""
    if engine:
        cli_state.set_engine(engine)
    require_engine()

    if not container_name:
        containers = cli_state.state_tracker.load_containers()
        if not containers:
            click.echo("No containers found.")
            return
        container_name = click.prompt(
            "Container name", type=click.Choice([c.name for c in containers])
        )

    container = next(
        (
            c
            for c in cli_state.state_tracker.load_containers()
            if c.name == container_name
        ),
        None,
    )
    if not container:
        click.echo(f"Container '{container_name}' not found.")
        return

    if click.confirm(f"Remove container '{container_name}'? This cannot be undone."):
        cli_state.docker_client.remove_container(container.docker_id)
        cli_state.state_tracker.delete_container(container_name)
        click.echo(f"✅ Container '{container_name}' removed.")


def display_connection_info(container: Container) -> None:
    """Display connection information to the user."""
    connection_string = f"postgresql://tsdbadmin:{container.tsdbadmin_password}@{container.bind_ip}:{container.port}/tsdb"
    click.echo(
        f"""
✅ Container '{container.name}' created successfully!

Connect:
  psql "{connection_string}"
"""
    )


def show_interactive_menu() -> None:
    """Show interactive menu when no command specified."""
    choice = click.prompt(
        "What would you like to do?",
        type=click.Choice(["new", "list", "logs", "remove"]),
    )

    if choice == "new":
        ctx = click.get_current_context()
        ctx.invoke(
            new,
            postgres=None,
            timescaledb=None,
            name=None,
            config=None,
            bind_ip=None,
            force=False,
        )
    elif choice == "list":
        ctx = click.get_current_context()
        ctx.invoke(list)
    elif choice == "logs":
        ctx = click.get_current_context()
        ctx.invoke(logs, container_name=None)
    elif choice == "remove":
        ctx = click.get_current_context()
        ctx.invoke(remove, container_name=None)


if __name__ == "__main__":
    main()
