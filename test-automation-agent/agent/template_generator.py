"""
Template-based Robot Framework test generator.
Used as a fallback when no LLM API key is available, and also as a
baseline that the LLM can improve upon.
"""

from jinja2 import Template


ROBOT_TEMPLATE = Template("""*** Settings ***
Documentation     Test suite for {{ op_name }} operation
Library           Process
Library           OperatingSystem
Library           String
Suite Setup       Verify Service Console Is Available
Suite Teardown    Cleanup Test Artifacts

*** Variables ***
${SERVICE_CONSOLE}    service-console
${TIMEOUT}            120
{% for arg in args %}
${DEFAULT_{{ arg.name | upper }}}    {{ arg.default or 'test-value' }}
{% endfor %}

*** Test Cases ***
# ============================================================
# POSITIVE TESTS
# ============================================================

{{ op_name }} Smoke Test
    [Documentation]    Verify {{ op_name }} operation runs successfully with valid arguments
    [Tags]    smoke    positive    {{ op_name | lower }}
    ${result}=    Run Process    ${SERVICE_CONSOLE}    run    {{ op_name }}{% for arg in required_args %}    --{{ arg.name | replace('_', '-') }}    ${DEFAULT_{{ arg.name | upper }}}{% endfor %}    --dry-run
    Should Be Equal As Integers    ${result.rc}    0
    Should Contain    ${result.stdout}    {{ op_name }}

{{ op_name }} With Dry Run Flag
    [Documentation]    Verify {{ op_name }} operation works with --dry-run flag
    [Tags]    positive    dry_run    {{ op_name | lower }}
    ${result}=    Run Process    ${SERVICE_CONSOLE}    run    {{ op_name }}{% for arg in required_args %}    --{{ arg.name | replace('_', '-') }}    ${DEFAULT_{{ arg.name | upper }}}{% endfor %}    --dry-run
    Should Be Equal As Integers    ${result.rc}    0
    Should Contain    ${result.stdout}    DRY RUN

{{ op_name }} With Custom Timeout
    [Documentation]    Verify {{ op_name }} operation accepts custom timeout
    [Tags]    positive    {{ op_name | lower }}
    ${result}=    Run Process    ${SERVICE_CONSOLE}    run    {{ op_name }}{% for arg in required_args %}    --{{ arg.name | replace('_', '-') }}    ${DEFAULT_{{ arg.name | upper }}}{% endfor %}    --timeout    60    --dry-run
    Should Be Equal As Integers    ${result.rc}    0

{% for arg in optional_args %}
{{ op_name }} With Optional Arg {{ arg.name }}
    [Documentation]    Verify {{ op_name }} works with optional argument --{{ arg.name | replace('_', '-') }}
    [Tags]    positive    {{ op_name | lower }}
    ${result}=    Run Process    ${SERVICE_CONSOLE}    run    {{ op_name }}{% for ra in required_args %}    --{{ ra.name | replace('_', '-') }}    ${DEFAULT_{{ ra.name | upper }}}{% endfor %}    --{{ arg.name | replace('_', '-') }}    {{ arg.default or 'test-value' }}    --dry-run
    Should Be Equal As Integers    ${result.rc}    0

{% endfor %}
# ============================================================
# NEGATIVE TESTS
# ============================================================

{% for arg in required_args %}
{{ op_name }} Fails Without Required Arg {{ arg.name }}
    [Documentation]    Verify {{ op_name }} fails when required argument --{{ arg.name | replace('_', '-') }} is missing
    [Tags]    negative    {{ op_name | lower }}
    ${result}=    Run Process    ${SERVICE_CONSOLE}    run    {{ op_name }}{% for other in required_args if other.name != arg.name %}    --{{ other.name | replace('_', '-') }}    ${DEFAULT_{{ other.name | upper }}}{% endfor %}
    Should Not Be Equal As Integers    ${result.rc}    0
    Should Contain    ${result.stderr}    Error

{% endfor %}
{{ op_name }} Fails With Unknown Operation Name
    [Documentation]    Verify service-console rejects unknown operation names
    [Tags]    negative    {{ op_name | lower }}
    ${result}=    Run Process    ${SERVICE_CONSOLE}    run    Invalid_Operation_XYZ
    Should Not Be Equal As Integers    ${result.rc}    0
    Should Contain    ${result.stderr}    Unknown operation

{{ op_name }} Fails With Empty Operation Name
    [Documentation]    Verify service-console handles empty operation name
    [Tags]    negative    edge_case    {{ op_name | lower }}
    ${result}=    Run Process    ${SERVICE_CONSOLE}    run
    Should Not Be Equal As Integers    ${result.rc}    0

{% for arg in required_args %}
{{ op_name }} Fails With Empty Value For {{ arg.name }}
    [Documentation]    Verify {{ op_name }} rejects empty value for --{{ arg.name | replace('_', '-') }}
    [Tags]    negative    edge_case    {{ op_name | lower }}
    ${result}=    Run Process    ${SERVICE_CONSOLE}    run    {{ op_name }}    --{{ arg.name | replace('_', '-') }}    ${EMPTY}
    Should Not Be Equal As Integers    ${result.rc}    0

{% endfor %}
{% for arg in args if arg.arg_type == 'int' %}
{{ op_name }} Fails With Non Numeric {{ arg.name }}
    [Documentation]    Verify {{ op_name }} rejects non-numeric value for --{{ arg.name | replace('_', '-') }}
    [Tags]    negative    {{ op_name | lower }}
    ${result}=    Run Process    ${SERVICE_CONSOLE}    run    {{ op_name }}{% for ra in required_args %}    --{{ ra.name | replace('_', '-') }}    ${DEFAULT_{{ ra.name | upper }}}{% endfor %}    --{{ arg.name | replace('_', '-') }}    not_a_number
    Should Not Be Equal As Integers    ${result.rc}    0

{{ op_name }} Fails With Negative {{ arg.name }}
    [Documentation]    Verify {{ op_name }} rejects negative value for --{{ arg.name | replace('_', '-') }}
    [Tags]    negative    edge_case    {{ op_name | lower }}
    ${result}=    Run Process    ${SERVICE_CONSOLE}    run    {{ op_name }}{% for ra in required_args %}    --{{ ra.name | replace('_', '-') }}    ${DEFAULT_{{ ra.name | upper }}}{% endfor %}    --{{ arg.name | replace('_', '-') }}    -1
    Should Not Be Equal As Integers    ${result.rc}    0

{% endfor %}
# ============================================================
# EDGE CASE TESTS
# ============================================================

{% for arg in required_args %}
{{ op_name }} With Special Characters In {{ arg.name }}
    [Documentation]    Verify {{ op_name }} handles special characters in --{{ arg.name | replace('_', '-') }}
    [Tags]    edge_case    {{ op_name | lower }}
    ${result}=    Run Process    ${SERVICE_CONSOLE}    run    {{ op_name }}    --{{ arg.name | replace('_', '-') }}    t€st!@#$%
    # Should either succeed or fail gracefully (no crash)
    Should Be True    ${result.rc} >= 0

{% endfor %}
{{ op_name }} Help Flag
    [Documentation]    Verify --help flag works for the run command
    [Tags]    positive    {{ op_name | lower }}
    ${result}=    Run Process    ${SERVICE_CONSOLE}    run    --help
    Should Be Equal As Integers    ${result.rc}    0
    Should Contain    ${result.stdout}    {{ op_name }}

*** Keywords ***
Verify Service Console Is Available
    [Documentation]    Verify the service-console CLI is installed and accessible
    ${result}=    Run Process    ${SERVICE_CONSOLE}    --version
    Should Be Equal As Integers    ${result.rc}    0
    Log    Service console version: ${result.stdout}

Cleanup Test Artifacts
    [Documentation]    Clean up any test artifacts created during the test run
    Log    Cleanup complete
""")


class TemplateGenerator:
    """Generates Robot Framework tests from templates using operation metadata."""

    def generate(self, operation_info: dict) -> str:
        """Generate a Robot Framework test file from operation info dict."""
        op_name = operation_info.get("name", "Unknown")
        args = operation_info.get("args", [])

        # Classify args
        required_args = [a for a in args if a.get("required", False) or (isinstance(a, dict) and a.get("required", False))]
        optional_args = [a for a in args if not (a.get("required", False) if isinstance(a, dict) else False)]

        # Normalize args to dicts
        def normalize_arg(a):
            if isinstance(a, dict):
                return a
            # Handle dataclass-like objects
            return {
                "name": getattr(a, "name", str(a)),
                "required": getattr(a, "required", False),
                "arg_type": getattr(a, "arg_type", "string"),
                "default": getattr(a, "default", None),
                "description": getattr(a, "description", ""),
            }

        args_normalized = [normalize_arg(a) for a in args]
        required_normalized = [normalize_arg(a) for a in required_args]
        optional_normalized = [normalize_arg(a) for a in optional_args]

        return ROBOT_TEMPLATE.render(
            op_name=op_name,
            args=args_normalized,
            required_args=required_normalized,
            optional_args=optional_normalized,
        )
