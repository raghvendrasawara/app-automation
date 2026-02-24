"""
File Watcher - Monitors the service-console repo for changes and
automatically triggers test regeneration when new operations are added.
"""

import os
import time
from typing import Optional

from rich.console import Console
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from agent.orchestrator import TestAutomationAgent
from agent.git_repo import clone_or_update_repo, get_remote_head_sha, is_git_url, pull_repo

console = Console()


class OperationChangeHandler(FileSystemEventHandler):
    """Handles file system events in the service-console repo."""

    def __init__(self, agent: TestAutomationAgent, debounce_seconds: float = 2.0):
        super().__init__()
        self.agent = agent
        self.debounce_seconds = debounce_seconds
        self._last_event_time = 0
        self._previous_scan = None

    def on_modified(self, event):
        self._handle_change(event)

    def on_created(self, event):
        self._handle_change(event)

    def _handle_change(self, event):
        if event.is_directory:
            return

        if not event.src_path.endswith(".py"):
            return

        now = time.time()
        if now - self._last_event_time < self.debounce_seconds:
            return

        self._last_event_time = now
        rel_path = os.path.relpath(event.src_path, self.agent.service_console_repo)
        console.print(f"\n[yellow]📁 Change detected: {rel_path}[/yellow]")

        try:
            prev = {}
            if self._previous_scan:
                prev = {
                    name: {"source_code": op.source_code}
                    for name, op in self._previous_scan.items()
                }

            changed_ops = self.agent.scan_for_changes(prev)

            if changed_ops:
                console.print(f"[cyan]Regenerating tests for: {', '.join(changed_ops)}[/cyan]")
                self.agent.generate_for_operations(changed_ops)
                console.print("[green]✓ Tests updated[/green]")
            else:
                console.print("[dim]No operation changes detected[/dim]")

            self._previous_scan = dict(self.agent.scan_results)

        except Exception as e:
            console.print(f"[red]Error processing change: {e}[/red]")


def watch_repo(
    service_console_repo: str,
    output_dir: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: str = "gpt-4o",
    use_mock: bool = False,
    poll_seconds: float = 60,
):
    """Start watching the service-console repo for changes."""
    if is_git_url(service_console_repo):
        cache_root = os.path.join(os.path.expanduser("~"), ".cache", "test-automation-agent")
        local_repo = clone_or_update_repo(repo_url=service_console_repo, cache_root=cache_root)
        is_remote = True
    elif os.path.isdir(service_console_repo):
        local_repo = service_console_repo
        is_remote = False
    else:
        raise ValueError(f"service_console_repo must be a local directory or git URL. Got: {service_console_repo}")

    agent = TestAutomationAgent(
        service_console_repo=local_repo,
        output_dir=output_dir,
        api_key=api_key,
        base_url=base_url,
        model=model,
        use_mock=use_mock,
    )

    # Initial run
    console.print("[bold]Running initial scan and test generation...[/bold]")
    agent.run()

    if not is_remote:
        handler = OperationChangeHandler(agent)
        handler._previous_scan = dict(agent.scan_results)

        observer = Observer()
        observer.schedule(handler, agent.service_console_repo, recursive=True)
        observer.start()

        console.print(f"\n[bold green]👀 Watching for changes in: {agent.service_console_repo}[/bold green]")
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            console.print("\n[yellow]Watcher stopped[/yellow]")

        observer.join()
        return

    prev_scan = {
        name: {"source_code": op.source_code}
        for name, op in agent.scan_results.items()
    }

    last_remote_sha = ""
    try:
        last_remote_sha = get_remote_head_sha(service_console_repo)
    except Exception as e:
        console.print(f"[yellow]Unable to read remote HEAD: {e}[/yellow]")

    console.print(f"\n[bold green]👀 Watching remote repo for changes: {service_console_repo}[/bold green]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    try:
        while True:
            time.sleep(max(poll_seconds, 1))
            try:
                remote_sha = get_remote_head_sha(service_console_repo)
            except Exception as e:
                console.print(f"[yellow]Unable to read remote HEAD: {e}[/yellow]")
                continue

            if remote_sha and remote_sha != last_remote_sha:
                console.print(f"\n[cyan]New commit detected: {remote_sha}[/cyan]")
                try:
                    pull_repo(local_repo)
                except Exception as e:
                    console.print(f"[red]Failed to pull latest changes: {e}[/red]")
                    last_remote_sha = remote_sha
                    continue

                changed_ops = agent.scan_for_changes(prev_scan)
                if changed_ops:
                    console.print(f"[cyan]Regenerating tests for: {', '.join(changed_ops)}[/cyan]")
                    agent.generate_for_operations(changed_ops)
                    console.print("[green]✓ Tests updated[/green]")
                else:
                    console.print("[dim]No operation changes detected[/dim]")

                prev_scan = {
                    name: {"source_code": op.source_code}
                    for name, op in agent.scan_results.items()
                }
                last_remote_sha = remote_sha

    except KeyboardInterrupt:
        console.print("\n[yellow]Watcher stopped[/yellow]")
