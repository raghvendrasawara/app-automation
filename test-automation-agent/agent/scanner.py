"""
Repository Scanner - Scans the service-console repo to discover operations,
their arguments, validation rules, and error conditions.
"""

import os
import ast
import json
import re
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class OperationArg:
    name: str
    required: bool
    arg_type: str = "string"
    default: Optional[str] = None
    description: str = ""


@dataclass
class OperationInfo:
    name: str
    description: str
    script_path: str
    args: list = field(default_factory=list)
    functions: list = field(default_factory=list)
    env_vars: list = field(default_factory=list)
    error_conditions: list = field(default_factory=list)
    source_code: str = ""

    def to_dict(self):
        return asdict(self)


class RepoScanner:
    """Scans the service-console repository to extract operation metadata."""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.operations = {}

    def scan(self) -> dict:
        """Full scan of the repository. Returns dict of operation name -> OperationInfo."""
        print(f"[Scanner] Scanning repository: {self.repo_path}")

        # Step 1: Parse the CLI to find registered operations
        cli_operations = self._parse_cli()

        # Step 2: Parse each operation script for detailed info
        for op_name, op_info in cli_operations.items():
            self._parse_operation_script(op_info)
            self.operations[op_name] = op_info

        print(f"[Scanner] Found {len(self.operations)} operations")
        return self.operations

    def _parse_cli(self) -> dict:
        """Parse cli.py to extract AVAILABLE_OPERATIONS registry."""
        cli_path = os.path.join(self.repo_path, "service_console", "cli.py")
        if not os.path.exists(cli_path):
            # Try alternate paths
            for candidate in ["cli.py", "service_console/cli.py", "src/cli.py"]:
                full = os.path.join(self.repo_path, candidate)
                if os.path.exists(full):
                    cli_path = full
                    break

        if not os.path.exists(cli_path):
            matches = []
            for root, dirs, files in os.walk(self.repo_path):
                if "service_console" in dirs:
                    candidate = os.path.join(root, "service_console", "cli.py")
                    if os.path.exists(candidate):
                        matches.append(candidate)

            if matches:
                cli_path = sorted(matches, key=lambda p: len(p.split(os.sep)))[0]
                self.repo_path = os.path.dirname(os.path.dirname(cli_path))

        if not os.path.exists(cli_path):
            print(f"[Scanner] Warning: cli.py not found at {cli_path}")
            return {}

        with open(cli_path, "r") as f:
            source = f.read()

        operations = {}

        # Parse the AST to find AVAILABLE_OPERATIONS dict
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "AVAILABLE_OPERATIONS":
                        operations = self._extract_operations_dict(node.value, source)

        # Also parse click options from the run command
        cli_args = self._parse_click_options(tree)

        # Merge CLI args into operations
        for op_name, op_info in operations.items():
            for arg in op_info.args:
                # Find matching click option
                for cli_arg in cli_args:
                    if cli_arg.name == arg.name:
                        arg.arg_type = cli_arg.arg_type
                        arg.default = cli_arg.default
                        arg.description = cli_arg.description

        return operations

    def _extract_operations_dict(self, node, source) -> dict:
        """Extract operation definitions from the AST Dict node."""
        operations = {}

        if not isinstance(node, ast.Dict):
            return operations

        for key, value in zip(node.keys, node.values):
            if not isinstance(key, ast.Constant):
                continue

            op_name = key.value
            op_data = {"description": "", "args": [], "script": ""}

            if isinstance(value, ast.Dict):
                for k, v in zip(value.keys, value.values):
                    if isinstance(k, ast.Constant):
                        if k.value == "description" and isinstance(v, ast.Constant):
                            op_data["description"] = v.value
                        elif k.value == "script" and isinstance(v, ast.Constant):
                            op_data["script"] = v.value
                        elif k.value == "args" and isinstance(v, ast.List):
                            for elt in v.elts:
                                if isinstance(elt, ast.Constant):
                                    arg_name = elt.value.lstrip("-").replace("-", "_")
                                    op_data["args"].append(
                                        OperationArg(name=arg_name, required=True)
                                    )

            operations[op_name] = OperationInfo(
                name=op_name,
                description=op_data["description"],
                script_path=op_data["script"],
                args=op_data["args"],
            )

        return operations

    def _parse_click_options(self, tree) -> list:
        """Parse click.option decorators to extract CLI argument metadata."""
        args = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "run":
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        func = decorator.func
                        if isinstance(func, ast.Attribute) and func.attr == "option":
                            if decorator.args:
                                opt_name = None
                                for a in decorator.args:
                                    if isinstance(a, ast.Constant) and isinstance(a.value, str):
                                        if a.value.startswith("--"):
                                            opt_name = a.value.lstrip("-").replace("-", "_")
                                            break

                                if opt_name:
                                    arg = OperationArg(name=opt_name, required=False)
                                    for kw in decorator.keywords:
                                        if kw.arg == "help" and isinstance(kw.value, ast.Constant):
                                            arg.description = kw.value.value
                                        elif kw.arg == "default" and isinstance(kw.value, ast.Constant):
                                            arg.default = str(kw.value.value)
                                        elif kw.arg == "type":
                                            if isinstance(kw.value, ast.Attribute):
                                                arg.arg_type = kw.value.attr
                                            elif isinstance(kw.value, ast.Name):
                                                arg.arg_type = kw.value.id
                                        elif kw.arg == "is_flag":
                                            arg.arg_type = "flag"
                                    args.append(arg)
        return args

    def _parse_operation_script(self, op_info: OperationInfo):
        """Parse an individual operation script for functions, env vars, error conditions."""
        script_path = os.path.join(self.repo_path, op_info.script_path)

        # Also check under service_console/
        if not os.path.exists(script_path):
            alt_path = os.path.join(self.repo_path, "service_console", op_info.script_path)
            if os.path.exists(alt_path):
                script_path = alt_path

        if not os.path.exists(script_path):
            print(f"[Scanner] Warning: Script not found: {script_path}")
            return

        with open(script_path, "r") as f:
            source = f.read()

        op_info.source_code = source

        # Parse AST
        tree = ast.parse(source)

        # Extract function names and docstrings
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                docstring = ast.get_docstring(node) or ""
                op_info.functions.append({
                    "name": node.name,
                    "docstring": docstring,
                    "args": [a.arg for a in node.args.args if a.arg != "self"],
                })

        # Extract environment variables (os.environ.get calls)
        env_pattern = re.compile(r'os\.environ\.get\(["\'](\w+)["\']')
        op_info.env_vars = env_pattern.findall(source)

        # Extract error conditions (sys.exit, raise, stderr prints)
        error_patterns = [
            (r'print\(.*"Error:.*"', "error_print"),
            (r"sys\.exit\((\d+)\)", "exit_code"),
            (r'file=sys\.stderr', "stderr_output"),
            (r'status.*error', "error_status"),
            (r'return 1', "failure_return"),
        ]

        for pattern, error_type in error_patterns:
            matches = re.findall(pattern, source)
            if matches:
                op_info.error_conditions.append({
                    "type": error_type,
                    "count": len(matches),
                    "pattern": pattern,
                })

        # Extract module docstring for additional description
        module_doc = ast.get_docstring(tree)
        if module_doc and not op_info.description:
            op_info.description = module_doc

    def get_scan_summary(self) -> str:
        """Return a human-readable summary of the scan results."""
        if not self.operations:
            return "No operations found. Run scan() first."

        lines = ["=" * 60, "Service Console Repository Scan Summary", "=" * 60]
        for name, op in self.operations.items():
            lines.append(f"\nOperation: {name}")
            lines.append(f"  Description: {op.description}")
            lines.append(f"  Script: {op.script_path}")
            lines.append(f"  Args: {[a.name for a in op.args]}")
            lines.append(f"  Env Vars: {op.env_vars}")
            lines.append(f"  Functions: {[f['name'] for f in op.functions]}")
            lines.append(f"  Error Conditions: {len(op.error_conditions)}")
        lines.append("=" * 60)
        return "\n".join(lines)

    def to_json(self) -> str:
        """Export scan results as JSON for LLM consumption."""
        return json.dumps(
            {name: op.to_dict() for name, op in self.operations.items()},
            indent=2,
            default=str,
        )
