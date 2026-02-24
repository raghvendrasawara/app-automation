"""
Agent Orchestrator - Main agent that coordinates scanning, LLM calls,
and test generation. Also supports watching for changes.
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from agent.scanner import RepoScanner
from agent.llm_client import LLMClient, MockLLMClient
from agent.template_generator import TemplateGenerator

console = Console()


class TestAutomationAgent:
    """Main agent that scans repos and generates Robot Framework tests."""

    def __init__(
        self,
        service_console_repo: str,
        output_dir: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o",
        use_mock: bool = False,
    ):
        self.service_console_repo = os.path.abspath(service_console_repo)
        self.output_dir = os.path.abspath(output_dir)
        self.use_mock = use_mock

        if use_mock or not (api_key or os.environ.get("OPENAI_API_KEY")):
            console.print("[yellow]No API key provided. Using template-based generator.[/yellow]")
            self.llm_client = MockLLMClient()
            self.use_mock = True
        else:
            self.llm_client = LLMClient(api_key=api_key, base_url=base_url, model=model)

        self.scanner = RepoScanner(self.service_console_repo)
        self.scan_results = {}
        self.generated_tests = {}

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

    def run(self) -> dict:
        """Execute the full agent pipeline: scan -> analyze -> generate tests."""
        console.print(Panel.fit(
            "[bold cyan]Test Automation Agent[/bold cyan]\n"
            f"Repo: {self.service_console_repo}\n"
            f"Output: {self.output_dir}\n"
            f"LLM: {self.llm_client.model}",
            title="🤖 Agent Starting",
        ))

        # Phase 1: Scan
        console.print("\n[bold]Phase 1: Scanning service-console repository...[/bold]")
        self.scan_results = self.scanner.scan()
        self._display_scan_results()

        # Phase 2: Generate tests
        console.print("\n[bold]Phase 2: Generating Robot Framework tests...[/bold]")
        self._generate_all_tests()

        # Phase 3: Generate shared resources
        console.print("\n[bold]Phase 3: Generating shared test resources...[/bold]")
        self._generate_shared_resources()

        # Phase 4: Summary
        self._display_summary()

        return self.generated_tests

    def scan_for_changes(self, previous_operations: Optional[dict] = None) -> list:
        """Scan for new or modified operations since last run."""
        current = self.scanner.scan()
        new_operations = []

        if previous_operations is None:
            return list(current.keys())

        prev_names = set(previous_operations.keys())
        curr_names = set(current.keys())

        # New operations
        added = curr_names - prev_names
        for name in added:
            new_operations.append(name)
            console.print(f"[green]+ New operation detected: {name}[/green]")

        # Modified operations (compare source code)
        for name in curr_names & prev_names:
            if current[name].source_code != previous_operations.get(name, {}).get("source_code", ""):
                new_operations.append(name)
                console.print(f"[yellow]~ Modified operation detected: {name}[/yellow]")

        # Removed operations
        removed = prev_names - curr_names
        for name in removed:
            console.print(f"[red]- Removed operation: {name}[/red]")

        self.scan_results = current
        return new_operations

    def generate_for_operations(self, operation_names: list) -> dict:
        """Generate tests only for specified operations."""
        results = {}
        for name in operation_names:
            if name in self.scan_results:
                console.print(f"  Generating tests for: [cyan]{name}[/cyan]")
                op_info = self.scan_results[name]
                test_content = self._generate_test(name, op_info)
                results[name] = test_content
        return results

    def _generate_all_tests(self):
        """Generate tests for all discovered operations."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            for op_name, op_info in self.scan_results.items():
                task = progress.add_task(f"Generating tests for {op_name}...", total=None)
                test_content = self._generate_test(op_name, op_info)
                self.generated_tests[op_name] = test_content
                progress.update(task, completed=True)

    def _generate_test(self, op_name: str, op_info) -> str:
        """Generate test for a single operation and write to file."""
        op_dict = op_info.to_dict() if hasattr(op_info, "to_dict") else op_info

        try:
            test_content = self.llm_client.generate_tests(op_dict)
        except Exception as e:
            console.print(f"[red]LLM generation failed for {op_name}: {e}[/red]")
            console.print("[yellow]Falling back to template generator...[/yellow]")
            generator = TemplateGenerator()
            test_content = generator.generate(op_dict)

        # Write test file
        filename = f"test_{op_name.lower()}.robot"
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w") as f:
            f.write(test_content)

        console.print(f"  [green]✓[/green] {filename} ({len(test_content)} bytes)")
        return test_content

    def _generate_shared_resources(self):
        """Generate shared Robot Framework resource files."""
        # Generate common keywords resource
        resource_content = self._build_common_resource()
        resource_path = os.path.join(self.output_dir, "common.resource")
        with open(resource_path, "w") as f:
            f.write(resource_content)
        console.print(f"  [green]✓[/green] common.resource")

        # Generate suite init file
        init_content = self._build_suite_init()
        init_path = os.path.join(self.output_dir, "__init__.robot")
        with open(init_path, "w") as f:
            f.write(init_content)
        console.print(f"  [green]✓[/green] __init__.robot")

        # Save scan metadata
        metadata = {
            "generated_at": datetime.now().isoformat(),
            "repo_path": self.service_console_repo,
            "operations": list(self.scan_results.keys()),
            "test_files": [f"test_{name.lower()}.robot" for name in self.scan_results],
            "llm_model": self.llm_client.model,
        }
        meta_path = os.path.join(self.output_dir, "scan_metadata.json")
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)
        console.print(f"  [green]✓[/green] scan_metadata.json")

    def _build_common_resource(self) -> str:
        """Build the common.resource file with shared keywords."""
        operations_list = "    ".join(self.scan_results.keys())
        return f"""*** Settings ***
Documentation     Common keywords and variables for service-console tests
Library           Process
Library           OperatingSystem
Library           String
Library           Collections

*** Variables ***
${{SERVICE_CONSOLE}}      service-console
${{DEFAULT_TIMEOUT}}      120
${{DOCKER_IMAGE}}         service-console:latest
@{{ALL_OPERATIONS}}       {operations_list}

*** Keywords ***
Run Service Console Operation
    [Documentation]    Run a service-console operation and return the result
    [Arguments]    ${{operation}}    @{{args}}
    ${{result}}=    Run Process    ${{SERVICE_CONSOLE}}    run    ${{operation}}    @{{args}}
    RETURN    ${{result}}

Run Service Console Operation With Dry Run
    [Documentation]    Run a service-console operation in dry-run mode
    [Arguments]    ${{operation}}    @{{args}}
    ${{result}}=    Run Process    ${{SERVICE_CONSOLE}}    run    ${{operation}}    @{{args}}    --dry-run
    RETURN    ${{result}}

Operation Should Succeed
    [Documentation]    Verify the operation completed successfully
    [Arguments]    ${{result}}
    Should Be Equal As Integers    ${{result.rc}}    0
    Should Not Contain    ${{result.stderr}}    Error

Operation Should Fail
    [Documentation]    Verify the operation failed as expected
    [Arguments]    ${{result}}
    Should Not Be Equal As Integers    ${{result.rc}}    0

Operation Should Fail With Message
    [Documentation]    Verify the operation failed with a specific error message
    [Arguments]    ${{result}}    ${{message}}
    Should Not Be Equal As Integers    ${{result.rc}}    0
    Should Contain    ${{result.stderr}}    ${{message}}

Verify Docker Is Available
    [Documentation]    Check that Docker is installed and running
    ${{result}}=    Run Process    docker    info
    Should Be Equal As Integers    ${{result.rc}}    0

Verify Service Console Is Installed
    [Documentation]    Check that service-console CLI is available
    ${{result}}=    Run Process    ${{SERVICE_CONSOLE}}    --version
    Should Be Equal As Integers    ${{result.rc}}    0
    RETURN    ${{result.stdout}}
"""

    def _build_suite_init(self) -> str:
        """Build the __init__.robot suite initialization file."""
        return f"""*** Settings ***
Documentation     Service Console End-to-End Test Suite
...               Auto-generated by Test Automation Agent on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
...               Operations tested: {', '.join(self.scan_results.keys())}
Resource          common.resource
Suite Setup       Suite Level Setup
Suite Teardown    Suite Level Teardown

*** Keywords ***
Suite Level Setup
    [Documentation]    Setup for the entire test suite
    Verify Service Console Is Installed
    Log    Test suite initialized

Suite Level Teardown
    [Documentation]    Teardown for the entire test suite
    Log    Test suite completed
"""

    def _display_scan_results(self):
        """Display scan results in a rich table."""
        table = Table(title="Discovered Operations")
        table.add_column("Operation", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Args", style="green")
        table.add_column("Functions", style="yellow", justify="right")
        table.add_column("Error Paths", style="red", justify="right")

        for name, op in self.scan_results.items():
            args_str = ", ".join(a.name for a in op.args) if op.args else "-"
            table.add_row(
                name,
                op.description[:50] + "..." if len(op.description) > 50 else op.description,
                args_str,
                str(len(op.functions)),
                str(len(op.error_conditions)),
            )

        console.print(table)

    def _display_summary(self):
        """Display final summary."""
        console.print(Panel.fit(
            f"[bold green]Test Generation Complete![/bold green]\n\n"
            f"Operations scanned: {len(self.scan_results)}\n"
            f"Test files generated: {len(self.generated_tests)}\n"
            f"Output directory: {self.output_dir}\n"
            f"LLM model used: {self.llm_client.model}\n\n"
            f"[dim]Run tests with: robot {self.output_dir}[/dim]",
            title="📊 Summary",
        ))
