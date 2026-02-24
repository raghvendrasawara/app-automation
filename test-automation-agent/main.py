"""
Test Automation Agent - CLI Entry Point

Usage:
    # One-shot: scan and generate tests
    python main.py generate --repo ../service-console --output ./generated_tests

    # Watch mode: auto-regenerate on changes
    python main.py watch --repo ../service-console --output ./generated_tests

    # Use with OpenAI API
    python main.py generate --repo ../service-console --output ./generated_tests --api-key sk-...

    # Use with local LLM (Ollama, LM Studio, etc.)
    python main.py generate --repo ../service-console --output ./generated_tests --base-url http://localhost:11434/v1 --model llama3

    # Use template-based generation (no LLM needed)
    python main.py generate --repo ../service-console --output ./generated_tests --mock
"""

import os
import sys
import click

from agent.orchestrator import TestAutomationAgent
from agent.watcher import watch_repo
from agent.git_repo import clone_or_update_repo, is_git_url


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Test Automation Agent - Auto-generate Robot Framework tests for service-console operations."""
    pass


@cli.command()
@click.option("--repo", "-r", required=True, help="Path or git URL to the service-console repository")
@click.option("--output", "-o", default="./generated_tests", help="Output directory for generated tests")
@click.option("--api-key", "-k", default=None, help="OpenAI API key (or set OPENAI_API_KEY env var)")
@click.option("--base-url", "-u", default=None, help="Custom LLM API base URL (for Ollama, LM Studio, etc.)")
@click.option("--model", "-m", default="gpt-4o", help="LLM model to use")
@click.option("--mock", is_flag=True, help="Use template-based generation (no LLM API needed)")
def generate(repo, output, api_key, base_url, model, mock):
    """Scan the service-console repo and generate Robot Framework tests."""
    if is_git_url(repo):
        cache_root = os.path.join(os.path.expanduser("~"), ".cache", "test-automation-agent")
        local_repo = clone_or_update_repo(repo_url=repo, cache_root=cache_root)
    elif os.path.isdir(repo):
        local_repo = repo
    else:
        click.echo(f"Error: --repo must be a local directory or git URL. Got: {repo}", err=True)
        sys.exit(1)

    agent = TestAutomationAgent(
        service_console_repo=local_repo,
        output_dir=output,
        api_key=api_key,
        base_url=base_url,
        model=model,
        use_mock=mock,
    )

    results = agent.run()

    if not results:
        click.echo("Warning: No tests were generated.", err=True)
        sys.exit(1)

    click.echo(f"\nGenerated {len(results)} test files in: {os.path.abspath(output)}")


@cli.command()
@click.option("--repo", "-r", required=True, help="Path or git URL to the service-console repository")
@click.option("--output", "-o", default="./generated_tests", help="Output directory for generated tests")
@click.option("--api-key", "-k", default=None, help="OpenAI API key (or set OPENAI_API_KEY env var)")
@click.option("--base-url", "-u", default=None, help="Custom LLM API base URL")
@click.option("--model", "-m", default="gpt-4o", help="LLM model to use")
@click.option("--mock", is_flag=True, help="Use template-based generation (no LLM API needed)")
@click.option("--poll-seconds", default=60, show_default=True, type=float, help="How often to check remote repo for new commits")
def watch(repo, output, api_key, base_url, model, mock, poll_seconds):
    """Watch the service-console repo and auto-regenerate tests on changes."""
    watch_repo(
        service_console_repo=repo,
        output_dir=output,
        api_key=api_key,
        base_url=base_url,
        model=model,
        use_mock=mock,
        poll_seconds=poll_seconds,
    )


@cli.command()
@click.option("--repo", "-r", required=True, help="Path or git URL to the service-console repository")
def scan(repo):
    """Scan the service-console repo and display discovered operations (no test generation)."""
    from agent.scanner import RepoScanner
    if is_git_url(repo):
        cache_root = os.path.join(os.path.expanduser("~"), ".cache", "test-automation-agent")
        local_repo = clone_or_update_repo(repo_url=repo, cache_root=cache_root)
    elif os.path.isdir(repo):
        local_repo = repo
    else:
        click.echo(f"Error: --repo must be a local directory or git URL. Got: {repo}", err=True)
        sys.exit(1)

    scanner = RepoScanner(local_repo)
    scanner.scan()
    click.echo(scanner.get_scan_summary())


if __name__ == "__main__":
    cli()
