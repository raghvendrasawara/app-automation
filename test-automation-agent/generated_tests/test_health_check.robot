*** Settings ***
${timeout} = 3600
${dry_run} = false

*** Variables ***
${nodes} = node-1 node-2 node-3
${services} = api-server scheduler controller etcd

*** Test Cases ***
*** Positive/Smoke test: Basic successful invocation with valid arguments ***
[Documentation]    Test basic successful invocation of Health Check operation
[Tags]             positive smoke
Run Health Check

*** Positive tests with variations: Different valid argument combinations ***
[Documentation]    Test different valid argument combinations for Health Check operation
[Tags]             positive variation
Run Health Check with nodes=${nodes} and services=${services}

*** Negative tests - Missing required args: Omit each required argument ***
[Documentation]    Test missing required arguments for Health Check operation
[Tags]             negative missing_args
Run Health Check without nodes

*** Negative tests - Invalid values: Wrong types, out-of-range values ***
[Documentation]    Test invalid values for Health Check operation
[Tags]             negative invalid_values
Run Health Check with invalid nodes=${nodes} and services=${services}

*** Negative tests - Unknown operation: Test with non-existent operation name ***
[Documentation]    Test unknown operation name for Health Check
[Tags]             negative unknown_operation
Run Unknown Operation

*** Edge cases: Empty strings, very large values, special characters ***
[Documentation]    Test edge cases for Health Check operation
[Tags]             edge_case
Run Health Check with empty nodes=${} and services=${}

*** Dry run tests: Verify --dry-run flag works correctly ***
[Documentation]    Test dry run flag behavior for Health Check operation
[Tags]             positive dry_run
Run Health Check with ${dry_run}=true

*** Timeout tests: Verify --timeout parameter behavior ***
[Documentation]    Test timeout parameter behavior for Health Check operation
[Tags]             negative timeout
Run Health Check with ${timeout}=120

*** Keywords ***
*** Keyword to run Health Check operation ***
[Documentation]    Run Health Check operation
[Tags]             keyword
Run Health Check

*** Setup ***
[Documentation]    Setup before each test
[Tags]             setup
:setup
    os.environ['DRY_RUN'] = ${dry_run}

*** Teardown ***
[Documentation]    Teardown after each test
[Tags]             teardown
:teardown
    del os.environ['DRY_RUN']

*** Keyword to run Unknown Operation ***
[Documentation]    Run unknown operation
[Tags]             keyword unknown_operation
Run Unknown Operation
*** Keyword to run Unknown Operation ***
[Documentation]    Run unknown operation
[Tags]             keyword unknown_operation
Run Unknown Operation

*** Keyword to run Unknown Operation ***
[Documentation]    Run unknown operation
[Tags]             keyword unknown_operation
Run Unknown Operation