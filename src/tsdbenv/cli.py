# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import hashlib
import sys
from datetime import datetime
from pathlib import Path

import click
from tabulate import tabulate

from tsdbenv import __version__
from tsdbenv.engine_config import Engine, get_engine_from_cli_or_env


def _expand_short_aliases():
    """Expand -n, -l, -c, -g, -m, -a, -t to full command names."""
    if len(sys.argv) <= 1:
        return

    # Move --engine/-e to the front if present but not already there
    for i in range(1, len(sys.argv)):
        if sys.argv[i] in ("--engine", "-e") and i > 1:
            # Found engine flag after position 1, move it and its value to the front
            if i + 1 < len(sys.argv):
                engine_flag = sys.argv[i]
                engine_value = sys.argv[i + 1]
                # Remove from current position
                sys.argv.pop(i + 1)
                sys.argv.pop(i)
                # Insert at position 1
                sys.argv.insert(1, engine_value)
                sys.argv.insert(1, engine_flag)
            break

    aliases = {"-n": "new", "-l": "list", "-r": "remove", "-c": "connectstring", "-g": "versionrefresh", "-m": "matrix", "-a": "removeall", "-t": "tablespaces"}

    # Find the first positional argument (command) - skip option names and their values
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]

        # Skip option values
        if arg in ("--engine", "-e"):
            i += 2  # Skip the option and its value
            continue

        # If it starts with - but isn't a known option, it's a short command alias
        if arg.startswith("-") and not arg.startswith("--"):
            if arg in aliases:
                sys.argv[i] = aliases[arg]
                break
        elif not arg.startswith("-"):
            # Found first positional arg (command name), check if it's a short alias
            if arg in aliases:
                sys.argv[i] = aliases[arg]
            break

        i += 1


_expand_short_aliases()


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
    def __init__(self, engine: Engine = Engine.DOCKER):
        self.engine = engine
        self.state_dir = ensure_state_dir()
        self.state_tracker = StateTracker(state_dir=self.state_dir)
        self.version_manager = VersionManager(cache_dir=self.state_dir)
        self.docker_client: DockerClient | None = None
        try:
            self.docker_client = DockerClient(engine=engine.value)
        except RuntimeError:
            pass


cli_state = CLIState()


def init_cli_state(engine: Engine) -> None:
    """Reinitialize CLI state with specified engine."""
    global cli_state
    cli_state = CLIState(engine=engine)
    if cli_state.docker_client is None:
        engine_name = engine.value.capitalize()
        click.echo(f"[ERROR] {engine_name} is not installed or not running.")
        if engine == Engine.DOCKER:
            click.echo("   Please install Docker: https://docs.docker.com/get-docker/")
        else:
            click.echo("   Please install Podman: https://podman.io/")
        raise click.Abort()


@click.group(context_settings={"help_option_names": ["-h", "--help"]}, invoke_without_command=True)
@click.option("-v", "--version", is_flag=True, help="Show version and exit")
@click.option(
    "-e",
    "--engine",
    type=click.Choice(["docker", "podman"]),
    default="docker",
    help="Container engine (default: docker)",
)
@click.pass_context
def main(ctx, version, engine):
    """tsdbenv - PostgreSQL + TimescaleDB environment manager.

Examples:

    # Create container:

    tsdbenv -n --postgres 16 --timescaledb 2.29.2

    # Create with init SQL and tablespaces:

    tsdbenv -n --postgres 16 --timescaledb 2.29.2 -t fast,archive -i schema.sql

    # List existing containers:

    tsdbenv -l

    # Show the current compatibility matrix:

    tsdbenv -m

    # Get connection string:

    tsdbenv -c mycontainer

    # Create tablespaces on container:

    tsdbenv -t mycontainer --tablespaces fast,archive

    # Use Podman instead of Docker:

    tsdbenv -n --postgres 16 --engine podman

    # Refresh version cache:

    tsdbenv -g
    """
    if version:
        click.echo(f"tsdbenv {__version__}")
        ctx.exit(0)
    init_cli_state(Engine(engine))
    if ctx.invoked_subcommand is None:
        show_interactive_menu()


@main.command()
@click.option("--postgres", help="PostgreSQL version (e.g., 14)")
@click.option("--timescaledb", help="TimescaleDB version (e.g., 2.8.0)")
@click.option("--port", type=int, default=None, help="PostgreSQL port")
@click.option("--config", type=click.Path(exists=True), help="PostgreSQL config file")
@click.option("--bind-ip", help="IP to bind to (default: 127.0.0.1)")
@click.option("--init", "-i", type=click.Path(exists=True), help="SQL file to execute")
@click.option("--tablespaces", "-t", help="Comma-separated tablespace names")
@click.option("--force", is_flag=True, help="Skip version compatibility check")
def new(postgres, timescaledb, port, config, bind_ip, init, tablespaces, force):
    """Create PostgreSQL + TimescaleDB container (-n)"""
    click.echo("[REFRESH] Checking for latest TimescaleDB versions...")
    cli_state.version_manager.refresh()

    if not postgres:
        postgres = click.prompt("PostgreSQL version", type=str)
    if not timescaledb:
        timescaledb = click.prompt("TimescaleDB version", type=str)

    if not force and not cli_state.version_manager.is_compatible(postgres, timescaledb):
        compatible_versions = cli_state.version_manager.get_compatible_timescaledb_versions(postgres)
        click.echo(f"[ERROR] TSDB {timescaledb} is not compatible with PostgreSQL {postgres}")
        if compatible_versions:
            versions_str = ", ".join(compatible_versions)
            click.echo(f"   [INFO]  Compatible TSDB versions: {versions_str}")
        click.echo("   [WARNING]  Use --force to override")
        raise click.Abort()

    timestamp_hash = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
    name = f"tsdb-{timestamp_hash}"

    if config:
        try:
            ConfigHandler.parse_file(Path(config))
        except Exception as e:
            click.echo(f"[ERROR] Failed to parse config: {e}")
            return

    if not bind_ip:
        bind_ip = "127.0.0.1"

    is_valid, warning = NetworkValidator.validate_bind_ip(bind_ip)
    if not is_valid:
        click.echo(warning)
        if not click.confirm("Continue anyway?"):
            return

    if port is None:
        port = NetworkValidator.find_available_port(bind_ip)

    tsdbadmin_password = generate_password()

    try:
        dockerfile_dir = str(get_dockerfiles_dir())
        image_tag = f"tsdbenv:pg{postgres}-latest"
        cli_state.docker_client.build_image(
            dockerfile_dir=dockerfile_dir,
            tag=image_tag,
            build_args={"PG_VERSION": postgres},
        )
    except Exception as e:
        click.echo(f"[ERROR] Failed to build Docker image: {e}")
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

    if init:
        try:
            click.echo("[INFO] Waiting for PostgreSQL to be fully ready...")
            cli_state.docker_client.wait_for_postgres(container_id, timeout=60)
            click.echo("[INFO] Executing init SQL file...")
            cli_state.docker_client.execute_sql_file(container_id, init)
            click.echo("[OK] Init SQL executed successfully")
        except Exception as e:
            click.echo(f"[WARNING]  Init SQL execution failed: {e}")
            click.echo("   Container created but schema setup incomplete")

    if tablespaces:
        try:
            ts_list = [ts.strip() for ts in tablespaces.split(",")]
            click.echo(f"[ACTION] Creating {len(ts_list)} tablespace(s)...")
            results = cli_state.docker_client.create_tablespaces(container_id, ts_list)
            successful = sum(1 for v in results.values() if v)
            click.echo(f"[OK] Created {successful}/{len(ts_list)} tablespace(s)")
            if successful < len(ts_list):
                failed = [k for k, v in results.items() if not v]
                click.echo(f"   [WARNING]  Failed: {', '.join(failed)}")
        except Exception as e:
            click.echo(f"[WARNING]  Tablespace creation failed: {e}")
            click.echo("   Container created but tablespaces incomplete")

    display_connection_info(container)


@main.command("list")
def list_cmd():
    """List all containers (-l)"""
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
def logs(container_name):
    """Show container logs"""
    if not container_name:
        containers = cli_state.state_tracker.load_containers()
        if not containers:
            click.echo("No containers found.")
            return
        container_name = click.prompt(
            "Container name", type=click.Choice([c.name for c in containers])
        )

    container = next(
        (c for c in cli_state.state_tracker.load_containers() if c.name == container_name),
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
def remove(container_name):
    """Remove a container (-r)"""
    if not container_name:
        containers = cli_state.state_tracker.load_containers()
        if not containers:
            click.echo("No containers found.")
            return
        container_name = click.prompt(
            "Container name", type=click.Choice([c.name for c in containers])
        )

    container = next(
        (c for c in cli_state.state_tracker.load_containers() if c.name == container_name),
        None,
    )
    if not container:
        click.echo(f"Container '{container_name}' not found.")
        return

    if click.confirm(f"Remove container '{container_name}'? This cannot be undone."):
        cli_state.docker_client.remove_container(container.docker_id)
        cli_state.state_tracker.delete_container(container_name)
        click.echo(f"[OK] Container '{container_name}' removed.")


@main.command("removeall")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
def removeall(force):
    """Remove all containers (-a)"""
    containers = cli_state.state_tracker.load_containers()
    if not containers:
        click.echo("No containers found.")
        return

    click.echo(f"Found {len(containers)} container(s):")
    for c in containers:
        click.echo(f"  - {c.name} (PG {c.postgres_version}, TSDB {c.timescaledb_version})")

    if not force and not click.confirm("Remove all containers?"):
        click.echo("Aborted.")
        return

    removed = 0
    failed = 0
    for container in containers:
        try:
            cli_state.docker_client.remove_container(container.docker_id)
            cli_state.state_tracker.delete_container(container.name)
            removed += 1
        except Exception as e:
            click.echo(f"[WARNING] Failed to remove {container.name}: {e}")
            failed += 1

    click.echo(f"[OK] Removed {removed}/{len(containers)} container(s)")
    if failed > 0:
        click.echo(f"[WARNING] {failed} container(s) failed to remove")


@main.command()
@click.argument("container_name", required=False)
def connectstring(container_name):
    """Get psql command for container (-c)"""
    if not container_name:
        containers = cli_state.state_tracker.load_containers()
        if not containers:
            click.echo("No containers found.")
            return
        container_name = click.prompt(
            "Container name", type=click.Choice([c.name for c in containers])
        )

    container = next(
        (c for c in cli_state.state_tracker.load_containers() if c.name == container_name),
        None,
    )
    if not container:
        click.echo(f"Container '{container_name}' not found.")
        return

    connection_string = f"postgresql://tsdbadmin:{container.tsdbadmin_password}@{container.bind_ip}:{container.port}/tsdb"
    click.echo(f'psql "{connection_string}"')
    cli_state.state_tracker.mark_accessed(container_name)


@main.command("tablespaces")
@click.argument("container_name", required=False)
@click.option("--tablespaces", help="Comma-separated tablespace names")
def create_tablespaces(container_name, tablespaces):
    """Create database tablespaces (-t)"""
    if not container_name:
        containers = cli_state.state_tracker.load_containers()
        if not containers:
            click.echo("No containers found.")
            return
        container_name = click.prompt(
            "Container name", type=click.Choice([c.name for c in containers])
        )

    container = next(
        (c for c in cli_state.state_tracker.load_containers() if c.name == container_name),
        None,
    )
    if not container:
        click.echo(f"Container '{container_name}' not found.")
        return

    if not tablespaces:
        tablespaces = click.prompt("Tablespace names (comma-separated)")

    try:
        ts_list = [ts.strip() for ts in tablespaces.split(",")]
        click.echo(f"[ACTION] Creating {len(ts_list)} tablespace(s)...")
        results = cli_state.docker_client.create_tablespaces(container.docker_id, ts_list)
        successful = sum(1 for v in results.values() if v)
        click.echo(f"[OK] Created {successful}/{len(ts_list)} tablespace(s)")
        if successful < len(ts_list):
            failed = [k for k, v in results.items() if not v]
            click.echo(f"   [WARNING]  Failed: {', '.join(failed)}")
        cli_state.state_tracker.mark_accessed(container_name)
    except Exception as e:
        click.echo(f"[ERROR] Tablespace creation failed: {e}")
        raise click.Abort()


@main.command("versionrefresh")
def versionrefresh():
    """Refresh version matrix (-g)"""
    click.echo("[REFRESH] Fetching latest TimescaleDB versions...")
    matrix = cli_state.version_manager.refresh()
    versions_found = sum(len(v) for v in matrix.postgres_versions.values())
    pg_versions = len(matrix.postgres_versions)
    click.echo(f"[OK] Updated: {pg_versions} PostgreSQL versions, {versions_found} TimescaleDB versions")


@main.command("matrix")
def show_matrix():
    """Display compatibility matrix (-m)"""
    cached = cli_state.version_manager.load_from_cache()
    if cached and cli_state.version_manager._is_cache_stale(cached):
        click.echo("[REFRESH] Version cache is outdated, fetching latest...")
    matrix = cli_state.version_manager.get_or_fetch()
    if not matrix.postgres_versions:
        click.echo("[ERROR] No compatibility data available")
        return

    rows = []
    for pg_ver in sorted(matrix.postgres_versions.keys(), key=lambda x: int(x)):
        tsdb_versions = matrix.postgres_versions[pg_ver]
        if tsdb_versions:
            versions_str = ", ".join(tsdb_versions)
            rows.append([f"PostgreSQL {pg_ver}", versions_str])

    if rows:
        click.echo("\nPostgreSQL × TimescaleDB Compatibility Matrix:\n")
        table = tabulate(
            rows,
            headers=["PostgreSQL", "Compatible TimescaleDB Versions"],
            tablefmt="grid",
        )
        click.echo(table)
    else:
        click.echo("[ERROR] No compatibility data available")


def display_connection_info(container: Container) -> None:
    """Display connection information to the user."""
    connection_string = f"postgresql://tsdbadmin:{container.tsdbadmin_password}@{container.bind_ip}:{container.port}/tsdb"
    click.echo(
        f"""
[OK] Container '{container.name}' created successfully!

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
            port=None,
            config=None,
            bind_ip=None,
            init=None,
            tablespaces=None,
            force=False,
        )
    elif choice == "list":
        ctx = click.get_current_context()
        ctx.invoke(list_cmd)
    elif choice == "logs":
        ctx = click.get_current_context()
        ctx.invoke(logs, container_name=None)
    elif choice == "remove":
        ctx = click.get_current_context()
        ctx.invoke(remove, container_name=None)


if __name__ == "__main__":
    main()
