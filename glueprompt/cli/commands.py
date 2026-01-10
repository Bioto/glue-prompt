"""CLI commands for glue-prompt."""

from pathlib import Path

import click
import yaml
from git import Repo
from git.exc import InvalidGitRepositoryError
from rich.console import Console
from rich.table import Table

from glueprompt.exceptions import GitOperationError
from glueprompt.registry import PromptRegistry
from glueprompt.repo_manager import RepoManager

console = Console()
err_console = Console(stderr=True)


def ensure_git_repo(prompts_dir: Path) -> Repo:
    """Get git repository for prompts directory.

    Cached repos should already be git repos. This just opens them.

    Args:
        prompts_dir: Path to prompts directory (should be a cached repo)

    Returns:
        Git Repo instance

    Raises:
        GitOperationError: If not a git repository
    """
    try:
        return Repo(str(prompts_dir))
    except InvalidGitRepositoryError as e:
        raise GitOperationError(
            f"Not a git repository: {prompts_dir}. "
            f"Cached repos should be cloned via 'glueprompt repo add <url>'"
        ) from e


def bump_version(version: str, bump_type: str = "patch") -> str:
    """Bump semantic version.

    Args:
        version: Current version string (e.g., "1.2.3")
        bump_type: Type of bump - "major", "minor", or "patch"

    Returns:
        New version string
    """
    parts = version.split(".")
    if len(parts) != 3:
        parts = ["1", "0", "0"]

    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    else:  # patch
        patch += 1

    return f"{major}.{minor}.{patch}"


def git_commit(repo: Repo, file_path: Path, message: str, tag: str | None = None) -> None:
    """Add, commit, and push a file to git. Optionally create and push a tag.

    Args:
        repo: Git Repo instance
        file_path: Path to file to commit
        message: Commit message
    """
    from git import GitCommandError

    try:
        rel_path = file_path.relative_to(repo.working_dir)
        repo.index.add([str(rel_path)])
        repo.index.commit(message)
        console.print(f"[green]✓[/green] Committed: {message}")

        # Auto-push to remote
        try:
            # Get current branch
            if repo.head.is_detached:
                console.print("[yellow]Warning:[/yellow] Detached HEAD, skipping push")
                return

            branch = repo.active_branch.name
            remote = repo.remote()
            if remote:
                repo.git.push(remote.name, branch)
                console.print(f"[green]✓[/green] Pushed to {remote.name}/{branch}")

                # Create and push tag if specified
                if tag:
                    repo.create_tag(tag, message=f"Version {tag}")
                    repo.git.push(remote.name, tag)
                    console.print(f"[green]✓[/green] Created and pushed tag: {tag}")
            else:
                console.print("[yellow]Warning:[/yellow] No remote configured, skipping push")
                if tag:
                    repo.create_tag(tag, message=f"Version {tag}")
                    console.print(f"[green]✓[/green] Created tag locally: {tag}")
        except GitCommandError as e:
            console.print(f"[yellow]Warning:[/yellow] Push failed: {e}")
            console.print("[yellow]Note:[/yellow] Changes are committed locally but not pushed")
    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Git commit failed: {e}")


@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Glue-Prompt: Git-based prompt versioning system."""
    ctx.ensure_object(dict)


@cli.command("serve")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=8000, type=int, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload (development)")
def serve(host: str, port: int, reload: bool) -> None:
    """Start the FastAPI prompt server.

    Example:
        glueprompt serve
        glueprompt serve --host 0.0.0.0 --port 8080
        glueprompt serve --reload  # Development mode
    """
    import uvicorn

    from glueprompt.server.app import app

    console.print(f"[green]Starting server[/green] on [cyan]http://{host}:{port}[/cyan]")
    console.print(f"API docs: [cyan]http://{host}:{port}/docs[/cyan]")

    uvicorn.run(app, host=host, port=port, reload=reload)


# ============================================================================
# Repo Management Commands
# ============================================================================


@cli.group()
def repo() -> None:
    """Manage prompt repositories."""
    pass


@repo.command("add")
@click.argument("url")
@click.option("--name", "-n", help="Custom name for the repo")
@click.option("--branch", "-b", help="Branch to checkout after cloning")
@click.option("--force", "-f", is_flag=True, help="Force re-clone if exists")
def repo_add(url: str, name: str | None, branch: str | None, force: bool) -> None:
    """Clone a prompt repository from URL.

    Example:
        glueprompt repo add https://github.com/myorg/prompts.git
        glueprompt repo add git@github.com:myorg/prompts.git --name my-prompts
    """
    manager = RepoManager()

    try:
        path = manager.clone(url, name=name, branch=branch, force=force)
        repo_name = name or path.name
        console.print(f"[green]✓[/green] Cloned '{repo_name}' to {path}")
        console.print(f"\nUse it with: [cyan]glueprompt --repo {repo_name} get <prompt-path>[/cyan]")
    except Exception as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise click.Abort() from e


@repo.command("remove")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def repo_remove(name: str, yes: bool) -> None:
    """Remove a cached prompt repository."""
    manager = RepoManager()

    if not yes:
        click.confirm(f"Remove repository '{name}'?", abort=True)

    try:
        manager.remove(name)
        console.print(f"[green]✓[/green] Removed '{name}'")
    except Exception as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise click.Abort() from e


@repo.command("list")
def repo_list() -> None:
    """List all cached prompt repositories."""
    manager = RepoManager()
    repos = manager.list_repos()

    if not repos:
        console.print("[yellow]No repositories configured.[/yellow]")
        console.print("Add one with: [cyan]glueprompt repo add <url>[/cyan]")
        return

    table = Table(title="Prompt Repositories")
    table.add_column("Name", style="cyan")
    table.add_column("Branch", style="yellow")
    table.add_column("Path", style="dim")
    table.add_column("Status", style="green")

    for repo_info in repos:
        status = "✓" if repo_info["exists"] else "[red]missing[/red]"
        table.add_row(
            repo_info["name"],
            repo_info.get("branch", "-"),
            repo_info["path"],
            status,
        )

    console.print(table)


@repo.command("update")
@click.argument("name")
@click.option("--branch", "-b", help="Checkout branch before pulling")
def repo_update(name: str, branch: str | None) -> None:
    """Pull latest changes for a repository."""
    manager = RepoManager()

    try:
        manager.update(name, branch=branch)
        console.print(f"[green]✓[/green] Updated '{name}'")
    except Exception as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise click.Abort() from e


@repo.command("default")
@click.argument("name", required=False)
def repo_default(name: str | None) -> None:
    """Get or set the default repository.

    If NAME is provided, sets it as default. If not provided, shows current default.

    Example:
        glueprompt repo default prompts
        glueprompt repo default  # Show current default
    """
    manager = RepoManager()

    if name:
        try:
            manager.set_default_repo(name)
            console.print(f"[green]✓[/green] Set default repository: {name}")
        except Exception as e:
            err_console.print(f"[red]Error:[/red] {e}")
            raise click.Abort() from e
    else:
        default = manager.get_default_repo()
        if default:
            console.print(f"Default repository: [cyan]{default}[/cyan]")
        else:
            console.print("[yellow]No default repository set.[/yellow]")
            console.print("Set one with: [cyan]glueprompt repo default <name>[/cyan]")


# ============================================================================
# Helper to resolve prompts directory
# ============================================================================


def get_prompts_dir(ctx: click.Context) -> Path:
    """Get prompts directory from --repo flag or default repo.

    Raises:
        click.Abort: If no repo specified and no default set
    """
    repo_name = ctx.obj.get("repo_name")

    # If repo specified, use it
    if repo_name:
        manager = RepoManager()
        return manager.get_path(repo_name)

    # Try default repo
    manager = RepoManager()
    default_repo = manager.get_default_repo()
    if default_repo:
        return manager.get_path(default_repo)

    # No repo specified and no default
    err_console.print("[red]Error:[/red] No repository specified.")
    err_console.print("Use [cyan]-r/--repo <name>[/cyan] or set a default with [cyan]glueprompt repo default <name>[/cyan]")
    err_console.print("\nAvailable repos:")
    repos = manager.list_repos()
    for repo_info in repos:
        if repo_info["exists"]:
            err_console.print(f"  - {repo_info['name']}")
    raise click.Abort()


# ============================================================================
# Prompt Commands
# ============================================================================


@cli.group(invoke_without_command=True)
@click.option(
    "--repo", "-r",
    "repo_name",
    help="Name of cached repository to use (or use default)",
)
@click.pass_context
def prompt(ctx: click.Context, repo_name: str | None) -> None:
    """Work with prompts (get, render, validate, etc.).

    All prompts are managed in cached repositories. Use 'glueprompt repo add <url>'
    to clone a repository first.
    """
    ctx.obj["repo_name"] = repo_name

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@prompt.command("get")
@click.argument("prompt_path")
@click.option("--validate/--no-validate", default=True, help="Validate prompt")
@click.pass_context
def prompt_get(ctx: click.Context, prompt_path: str, validate: bool) -> None:
    """Get a prompt and display its metadata."""
    prompts_dir = get_prompts_dir(ctx)
    registry = PromptRegistry(prompts_dir=prompts_dir)

    try:
        prompt = registry.get(prompt_path, validate=validate)

        table = Table(title=f"Prompt: {prompt_path}")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Name", prompt.metadata.name)
        table.add_row("Version", prompt.metadata.version)
        table.add_row("Description", prompt.metadata.description or "(none)")
        table.add_row("Author", prompt.metadata.author or "(none)")
        table.add_row("Tags", ", ".join(prompt.metadata.tags) or "(none)")
        table.add_row("Variables", ", ".join(prompt.variables.keys()) or "(none)")

        console.print(table)

        console.print("\n[bold]Template:[/bold]")
        console.print(prompt.template)
    except Exception as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise click.Abort() from e


@prompt.command("add")
@click.argument("prompt_path")
@click.option("--name", "-n", help="Prompt name (defaults to filename)")
@click.option("--description", "-d", help="Prompt description")
@click.option("--template", "-t", help="Initial template text")
@click.option("--edit", "-e", is_flag=True, help="Open in editor after creating")
@click.option("--message", "-m", help="Git commit message")
@click.pass_context
def prompt_add(
    ctx: click.Context,
    prompt_path: str,
    name: str | None,
    description: str | None,
    template: str | None,
    edit: bool,
    message: str | None,
) -> None:
    """Create a new prompt and add it to the repository.

    Automatically initializes git if needed and commits the new prompt.

    Example:
        glueprompt prompt add assistants/coding-helper
        glueprompt prompt add tools/summarizer --description "Summarizes text"
        glueprompt prompt add agents/researcher -e  # Opens in editor
    """
    prompts_dir = get_prompts_dir(ctx)

    # Ensure git repo exists (auto-init if needed)
    repo = ensure_git_repo(prompts_dir)

    # Determine file path
    if not prompt_path.endswith((".yaml", ".yml")):
        file_path = prompts_dir / f"{prompt_path}.yaml"
    else:
        file_path = prompts_dir / prompt_path

    # Check if already exists
    if file_path.exists():
        err_console.print(f"[red]Error:[/red] Prompt already exists: {file_path}")
        err_console.print(f"Use [cyan]glueprompt prompt edit {prompt_path}[/cyan] to modify it.")
        raise click.Abort()

    # Create parent directories
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Derive name from path if not provided
    if name is None:
        name = file_path.stem

    # Build prompt data
    prompt_data = {
        "name": name,
        "version": "1.0.0",
        "description": description or "",
        "template": template or f"You are {name}.\n\n{{{{ instructions }}}}",
        "variables": {
            "instructions": {
                "type": "string",
                "required": False,
                "default": "",
                "description": "Additional instructions",
            }
        },
    }

    # Write YAML file
    with file_path.open("w") as f:
        yaml.dump(prompt_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    console.print(f"[green]✓[/green] Created prompt: {file_path}")

    # Open in editor if requested
    if edit:
        click.edit(filename=str(file_path))

    # Commit to git and create initial version tag
    # Use prompt-specific tag: {prompt_path}/v{version}
    prompt_name = prompt_path.replace("/", "-")  # Sanitize for git tag
    tag_name = f"{prompt_name}/v1.0.0"
    commit_msg = message or f"Add prompt: {prompt_path}"
    git_commit(repo, file_path, commit_msg, tag=tag_name)


@prompt.command("edit")
@click.argument("prompt_path")
@click.option("--bump", "-b", type=click.Choice(["major", "minor", "patch"]), default="patch",
              help="Version bump type (default: patch)")
@click.option("--message", "-m", help="Git commit message")
@click.pass_context
def prompt_edit(
    ctx: click.Context,
    prompt_path: str,
    bump: str,
    message: str | None,
) -> None:
    """Edit a prompt, bump version, and commit changes.

    Opens the prompt in your default editor. After saving, automatically
    bumps the version and commits to git.

    Example:
        glueprompt prompt edit assistants/helper
        glueprompt prompt edit assistants/helper --bump minor
        glueprompt prompt edit assistants/helper -m "Improve tone"
    """
    prompts_dir = get_prompts_dir(ctx)

    # Ensure git repo
    repo = ensure_git_repo(prompts_dir)

    # Find file
    if not prompt_path.endswith((".yaml", ".yml")):
        file_path = prompts_dir / f"{prompt_path}.yaml"
        if not file_path.exists():
            file_path = prompts_dir / f"{prompt_path}.yml"
    else:
        file_path = prompts_dir / prompt_path

    if not file_path.exists():
        err_console.print(f"[red]Error:[/red] Prompt not found: {prompt_path}")
        raise click.Abort()

    # Load current prompt to get version
    with file_path.open("r") as f:
        prompt_data = yaml.safe_load(f)

    old_version = prompt_data.get("version", "1.0.0")

    # Open in editor
    click.edit(filename=str(file_path))

    # Reload and bump version
    with file_path.open("r") as f:
        prompt_data = yaml.safe_load(f)

    new_version = bump_version(old_version, bump)
    prompt_data["version"] = new_version

    # Write back with new version
    with file_path.open("w") as f:
        yaml.dump(prompt_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    console.print(f"[green]✓[/green] Version bumped: {old_version} → {new_version}")

    # Commit to git and create version tag
    # Use prompt-specific tag: {prompt_path}/v{version}
    prompt_name = prompt_path.replace("/", "-")  # Sanitize for git tag
    tag_name = f"{prompt_name}/v{new_version}"
    commit_msg = message or f"Update {prompt_path} to v{new_version}"
    git_commit(repo, file_path, commit_msg, tag=tag_name)


@prompt.command("remove")
@click.argument("prompt_path")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@click.option("--message", "-m", help="Git commit message")
@click.pass_context
def prompt_remove(
    ctx: click.Context,
    prompt_path: str,
    yes: bool,
    message: str | None,
) -> None:
    """Remove a prompt from the repository.

    Deletes the prompt file and commits the removal to git.

    Example:
        glueprompt prompt remove assistants/old-helper
        glueprompt prompt remove assistants/deprecated -y  # Skip confirmation
    """
    prompts_dir = get_prompts_dir(ctx)

    # Ensure git repo
    repo = ensure_git_repo(prompts_dir)

    # Find file
    if not prompt_path.endswith((".yaml", ".yml")):
        file_path = prompts_dir / f"{prompt_path}.yaml"
        if not file_path.exists():
            file_path = prompts_dir / f"{prompt_path}.yml"
    else:
        file_path = prompts_dir / prompt_path

    if not file_path.exists():
        err_console.print(f"[red]Error:[/red] Prompt not found: {prompt_path}")
        raise click.Abort()

    # Confirm deletion
    if not yes:
        click.confirm(f"Remove prompt '{prompt_path}'?", abort=True)

    # Remove from git and filesystem
    try:
        rel_path = file_path.relative_to(repo.working_dir)
        repo.index.remove([str(rel_path)], working_tree=True)

        commit_msg = message or f"Remove prompt: {prompt_path}"
        repo.index.commit(commit_msg)

        console.print(f"[green]✓[/green] Removed: {prompt_path}")
        console.print(f"[green]✓[/green] Committed: {commit_msg}")
    except Exception as e:
        # Fallback: just delete the file
        file_path.unlink()
        console.print(f"[green]✓[/green] Removed: {prompt_path}")
        console.print(f"[yellow]Warning:[/yellow] Git commit failed: {e}")


@prompt.command("render")
@click.argument("prompt_path")
@click.option("--var", "-v", multiple=True, help="Variable in KEY=VALUE format")
@click.option("--validate/--no-validate", default=True, help="Validate prompt")
@click.pass_context
def prompt_render(ctx: click.Context, prompt_path: str, var: tuple, validate: bool) -> None:
    """Render a prompt with variables.

    Example:
        glueprompt prompt render assistant --var name=Claude --var style=formal
    """
    prompts_dir = get_prompts_dir(ctx)
    registry = PromptRegistry(prompts_dir=prompts_dir)

    try:
        # Parse variables from --var flags
        variables = {}
        for v in var:
            if "=" not in v:
                err_console.print(f"[red]Error:[/red] Invalid variable format: {v}. Use KEY=VALUE")
                raise click.Abort()
            key, value = v.split("=", 1)
            variables[key] = value

        # If no vars provided, prompt interactively
        if not variables:
            prompt_obj = registry.get(prompt_path, validate=validate)
            for var_name, var_def in prompt_obj.variables.items():
                if var_def.required and var_def.default is None:
                    value = click.prompt(f"{var_name} ({var_def.description or 'required'})")
                    variables[var_name] = value
                elif var_def.default is not None:
                    value = click.prompt(
                        f"{var_name} ({var_def.description or 'optional'})",
                        default=str(var_def.default),
                    )
                    variables[var_name] = value

        rendered = registry.render(prompt_path, validate=validate, **variables)
        console.print("\n[bold]Rendered Prompt:[/bold]\n")
        console.print(rendered)
    except Exception as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise click.Abort() from e


@prompt.command("validate")
@click.argument("prompt_path")
@click.pass_context
def prompt_validate(ctx: click.Context, prompt_path: str) -> None:
    """Validate a prompt."""
    prompts_dir = get_prompts_dir(ctx)
    registry = PromptRegistry(prompts_dir=prompts_dir)

    try:
        errors = registry.validate(prompt_path)
        if errors:
            console.print(f"[red]Validation failed for {prompt_path}:[/red]")
            for error in errors:
                console.print(f"  - {error}")
            raise click.Abort()
        console.print(f"[green]✓[/green] Prompt '{prompt_path}' is valid")
    except Exception as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise click.Abort() from e


@prompt.command("list")
@click.pass_context
def prompt_list(ctx: click.Context) -> None:
    """List all prompts in the repository."""
    prompts_dir = get_prompts_dir(ctx)

    if not prompts_dir.exists():
        err_console.print(f"[red]Error:[/red] Prompts directory not found: {prompts_dir}")
        raise click.Abort()

    # Find all YAML files
    yaml_files = list(prompts_dir.rglob("*.yaml")) + list(prompts_dir.rglob("*.yml"))

    if not yaml_files:
        console.print("[yellow]No prompts found.[/yellow]")
        return

    table = Table(title=f"Prompts in {prompts_dir}")
    table.add_column("Path", style="cyan")
    table.add_column("Name", style="green")

    for yaml_file in sorted(yaml_files):
        rel_path = yaml_file.relative_to(prompts_dir)
        # Remove extension for display
        prompt_path = str(rel_path).rsplit(".", 1)[0]
        table.add_row(prompt_path, yaml_file.stem)

    console.print(table)


# ============================================================================
# Version Commands
# ============================================================================


@cli.group()
@click.option("--repo", "-r", "repo_name", help="Name of cached repository (or use default)")
@click.pass_context
def version(ctx: click.Context, repo_name: str | None) -> None:
    """Manage prompt versions (branches/tags)."""
    ctx.obj["repo_name"] = repo_name


@version.command("list")
@click.pass_context
def version_list(ctx: click.Context) -> None:
    """List all available versions (branches and tags)."""
    prompts_dir = get_prompts_dir(ctx)
    registry = PromptRegistry(prompts_dir=prompts_dir)

    try:
        versions = registry.list_versions()
        current = registry.current_version()

        # Branches table
        if versions["branches"]:
            table = Table(title="Branches")
            table.add_column("Name", style="cyan")
            table.add_column("Commit", style="yellow")
            table.add_column("Current", style="green")

            for branch in versions["branches"]:
                current_marker = "✓" if branch.is_current else ""
                table.add_row(branch.name, branch.commit_hash, current_marker)

            console.print(table)
            console.print()

        # Tags table
        if versions["tags"]:
            table = Table(title="Tags")
            table.add_column("Name", style="cyan")
            table.add_column("Commit", style="yellow")
            table.add_column("Date", style="dim")

            for tag in versions["tags"]:
                table.add_row(
                    tag.branch_or_tag,
                    tag.commit_hash,
                    tag.commit_date.strftime("%Y-%m-%d %H:%M"),
                )

            console.print(table)
            console.print()

        console.print(f"[bold]Current:[/bold] {current.branch_or_tag} ({current.commit_hash})")
    except Exception as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise click.Abort() from e


@version.command("checkout")
@click.argument("branch_or_tag")
@click.option("--create", "-c", is_flag=True, help="Create branch if it doesn't exist")
@click.pass_context
def version_checkout(ctx: click.Context, branch_or_tag: str, create: bool) -> None:
    """Checkout a version (branch or tag)."""
    prompts_dir = get_prompts_dir(ctx)
    registry = PromptRegistry(prompts_dir=prompts_dir)

    try:
        registry.checkout(branch_or_tag, create_branch=create)
        current = registry.current_version()
        console.print(
            f"[green]✓[/green] Checked out {current.branch_or_tag} "
            f"(commit: {current.commit_hash})"
        )
    except Exception as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise click.Abort() from e


@version.command("diff")
@click.argument("prompt_path")
@click.option("--v1", help="First version (branch/tag/commit)")
@click.option("--v2", help="Second version (branch/tag/commit)")
@click.pass_context
def version_diff(ctx: click.Context, prompt_path: str, v1: str | None, v2: str | None) -> None:
    """Show diff of a prompt between versions."""
    prompts_dir = get_prompts_dir(ctx)
    registry = PromptRegistry(prompts_dir=prompts_dir)

    try:
        diff_output = registry.diff(prompt_path, version1=v1, version2=v2)
        if diff_output:
            console.print(diff_output)
        else:
            console.print("[yellow]No differences found[/yellow]")
    except Exception as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise click.Abort() from e
