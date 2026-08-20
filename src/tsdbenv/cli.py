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


# Preprocess argv to expand short aliases before Click parses
def _expand_short_aliases():
    """Expand -n, -l, -c, -g, -m, -a to full command names."""
    if len(sys.argv) > 1:
        # Check if first arg is docker/podman, and expand aliases in second position
        if sys.argv[1] in ("docker", "podman") and len(sys.argv) > 2:
            engine = sys.argv[1]
            # Special cases for command position after engine
            if sys.argv[2] == "-g":
                sys.argv[2] = "versionrefresh"
            elif sys.argv[2] == "-m":
                sys.argv[2] = "matrix"
            elif sys.argv[2] == "-a":
                sys.argv[2] = "removeall"
            elif sys.argv[2] in {"-n", "-l", "-r", "-c"}:
                aliases = {"-n": "new", "-l": "list", "-r": "remove", "-c": "connectstring"}
                sys.argv[2] = aliases[sys.argv[2]]
            # Convert -t VALUE to --tablespaces VALUE
            if "-t" in sys.argv and len(sys.argv) > sys.argv.index("-t") + 1:
                idx = sys.argv.index("-t")
                sys.argv[idx] = "--tablespaces"
            return

        # Special cases (before general aliases mapping)
        if sys.argv[1] == "-g":
            sys.argv[1] = "versionrefresh"
            return
        if sys.argv[1] == "-m":
            sys.argv[1] = "matrix"
            return
        if sys.argv[1] == "-a":
            sys.argv[1] = "removeall"
            return
        aliases = {"-n": "new", "-l": "list", "-r": "remove", "-c": "connectstring"}
        if sys.argv[1] in aliases:
            sys.argv[1] = aliases[sys.argv[1]]
        # Convert -t VALUE to --tablespaces VALUE
        if "-t" in sys.argv and len(sys.argv) > sys.argv.index("-t") + 1:
            idx = sys.argv.index("-t")
            sys.argv[idx] = "--tablespaces"


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


# Initialize with default engine
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
@click.pass_context
def main(ctx, version):
    """tsdbenv - PostgreSQL + TimescaleDB environment manager."""
    if version:
        click.echo(f"tsdbenv {__version__}")
        ctx.exit(0)
    if ctx.invoked_subcommand is None:
        ctx.invoke(show_help)


@main.command()
def show_help():
    """Show help message."""
    click.echo("tsdbenv - PostgreSQL + TimescaleDB environment manager")
    click.echo("")
    click.echo("Usage: tsdbenv [OPTIONS] COMMAND [ARGS]...")
    click.echo("")
    click.echo("Commands:")
    click.echo("  docker    Use Docker container engine")
    click.echo("  podman    Use Podman container engine")
    click.echo("")
    click.echo("Options:")
    click.echo("  -v, --version  Show version and exit")
    click.echo("  -h, --help     Show this message and exit")
    click.echo("")
    click.echo("Examples:")
    click.echo("  tsdbenv docker new --postgres 16 --timescaledb 2.29.2")
    click.echo("  tsdbenv podman list")


def create_engine_group(engine: Engine) -> click.Group:
    """Create a command group for the specified engine."""

    @click.group(invoke_without_command=True)
    @click.pass_context
    def engine_group(ctx):
        """PostgreSQL + TimescaleDB commands."""
        init_cli_state(engine)
        if ctx.invoked_subcommand is None:
            show_interactive_menu()

    @engine_group.command()
    @click.option("--postgres", help="PostgreSQL version (e.g., 14)")
    @click.option("--timescaledb", help="TimescaleDB version (e.g., 2.8.0)")
    @click.option("--port", type=int, default=None, help="PostgreSQL port")
    @click.option("--config", type=click.Path(exists=True), help="PostgreSQL config file")
    @click.option("--bind-ip", help="IP to bind to (default: 127.0.0.1)")
    @click.option("--init", type=click.Path(exists=True), help="SQL file to execute")
    @click.option("--tablespaces", help="Comma-separated tablespace names")
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

    @engine_group.command("list")
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

    @engine_group.command()
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

    @engine_group.command()
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

    @engine_group.command("removeall")
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

    @engine_group.command()
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

    @engine_group.command("versionrefresh")
    def versionrefresh():
        """Refresh version matrix (-g)"""
        click.echo("[REFRESH] Fetching latest TimescaleDB versions...")
        matrix = cli_state.version_manager.refresh()
        versions_found = sum(len(v) for v in matrix.postgres_versions.values())
        pg_versions = len(matrix.postgres_versions)
        click.echo(f"[OK] Updated: {pg_versions} PostgreSQL versions, {versions_found} TimescaleDB versions")

    @engine_group.command("matrix")
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

    return engine_group


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
            ctx.command.commands["new"],
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
        ctx.invoke(ctx.command.commands["list"])
    elif choice == "logs":
        ctx = click.get_current_context()
        ctx.invoke(ctx.command.commands["logs"], container_name=None)
    elif choice == "remove":
        ctx = click.get_current_context()
        ctx.invoke(ctx.command.commands["remove"], container_name=None)


# Create engine groups
main.add_command(create_engine_group(Engine.DOCKER), name="docker")
main.add_command(create_engine_group(Engine.PODMAN), name="podman")


if __name__ == "__main__":
    main()
