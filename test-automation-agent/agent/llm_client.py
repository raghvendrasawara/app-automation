"""
LLM Client - Interfaces with OpenAI (or compatible) API to generate Robot Framework tests.
Supports OpenAI, Azure OpenAI, and any OpenAI-compatible endpoint (e.g., Ollama, LM Studio).
"""

import os
import json
from typing import Optional

from openai import OpenAI


SYSTEM_PROMPT = """You are an expert test automation engineer specializing in Robot Framework.
Your job is to generate comprehensive Robot Framework test suites for service-console operations.

For each operation, you must generate:
1. **Positive tests**: Valid invocations that should succeed
2. **Negative tests**: Invalid inputs, missing required args, boundary conditions, timeouts
3. **Edge case tests**: Empty values, special characters, concurrent operations

Follow these Robot Framework conventions:
- Use the *** Settings ***, *** Variables ***, *** Test Cases ***, *** Keywords *** sections
- Use descriptive test case names
- Include [Documentation] for each test
- Include [Tags] for categorization (positive, negative, edge_case, smoke, regression)
- Use proper setup/teardown
- Use the Process library to invoke service-console commands
- Check return codes, stdout, and stderr

Output ONLY valid Robot Framework (.robot) file content. No markdown, no explanations.
"""


class LLMClient:
    """Client for generating Robot Framework tests using an LLM."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o",
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL")
        self.model = model or os.environ.get("LLM_MODEL", "gpt-4o")

        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self.client = OpenAI(**client_kwargs)

    def generate_tests(self, operation_info: dict) -> str:
        """Generate Robot Framework tests for a single operation.

        Args:
            operation_info: Dictionary containing operation metadata from the scanner.

        Returns:
            Robot Framework test file content as a string.
        """
        prompt = self._build_prompt(operation_info)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=4096,
        )

        content = response.choices[0].message.content

        # Strip markdown code fences if present
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first and last lines (code fences)
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)

        return content.strip()

    def _build_prompt(self, operation_info: dict) -> str:
        """Build the prompt for test generation."""
        op_name = operation_info.get("name", "Unknown")
        description = operation_info.get("description", "")
        args = operation_info.get("args", [])
        functions = operation_info.get("functions", [])
        env_vars = operation_info.get("env_vars", [])
        error_conditions = operation_info.get("error_conditions", [])
        source_code = operation_info.get("source_code", "")

        prompt = f"""Generate a comprehensive Robot Framework test suite for the following service-console operation:

## Operation: {op_name}
**Description**: {description}

## CLI Usage
```
service-console run {op_name}
```

## Arguments
{json.dumps(args, indent=2, default=str)}

## Internal Functions
{json.dumps(functions, indent=2)}

## Environment Variables Used
{json.dumps(env_vars, indent=2)}

## Error Conditions Found in Source
{json.dumps(error_conditions, indent=2)}

## Source Code
```python
{source_code}
```

## Requirements
Generate tests covering:
1. **Positive/Smoke tests**: Basic successful invocation with valid arguments
2. **Positive tests with variations**: Different valid argument combinations
3. **Negative tests - Missing required args**: Omit each required argument
4. **Negative tests - Invalid values**: Wrong types, out-of-range values
5. **Negative tests - Unknown operation**: Test with non-existent operation name
6. **Edge cases**: Empty strings, very large values, special characters
7. **Dry run tests**: Verify --dry-run flag works correctly
8. **Timeout tests**: Verify --timeout parameter behavior

Use `service-console run` as the command to invoke operations.
Include proper [Setup] and [Teardown] keywords.
Use [Tags] to categorize each test (positive, negative, edge_case, smoke).
"""
        return prompt


class MockLLMClient(LLMClient):
    """Mock LLM client that generates tests using templates (no API key needed).

    This is useful for demos and testing when no LLM API is available.
    """

    def __init__(self, **kwargs):
        # Don't call super().__init__ to avoid needing an API key
        self.model = "mock-template-engine"

    def generate_tests(self, operation_info: dict) -> str:
        """Generate Robot Framework tests using templates instead of LLM."""
        from agent.template_generator import TemplateGenerator
        generator = TemplateGenerator()
        return generator.generate(operation_info)
