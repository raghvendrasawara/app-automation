*** Settings ***
Documentation     Common keywords and variables for service-console tests
Library           Process
Library           OperatingSystem
Library           String
Library           Collections

*** Variables ***
${SERVICE_CONSOLE}      service-console
${DEFAULT_TIMEOUT}      120
${DOCKER_IMAGE}         service-console:latest
@{ALL_OPERATIONS}       Health_Check    Upgrade

*** Keywords ***
Run Service Console Operation
    [Documentation]    Run a service-console operation and return the result
    [Arguments]    ${operation}    @{args}
    ${result}=    Run Process    ${SERVICE_CONSOLE}    run    ${operation}    @{args}
    RETURN    ${result}

Run Service Console Operation With Dry Run
    [Documentation]    Run a service-console operation in dry-run mode
    [Arguments]    ${operation}    @{args}
    ${result}=    Run Process    ${SERVICE_CONSOLE}    run    ${operation}    @{args}    --dry-run
    RETURN    ${result}

Operation Should Succeed
    [Documentation]    Verify the operation completed successfully
    [Arguments]    ${result}
    Should Be Equal As Integers    ${result.rc}    0
    Should Not Contain    ${result.stderr}    Error

Operation Should Fail
    [Documentation]    Verify the operation failed as expected
    [Arguments]    ${result}
    Should Not Be Equal As Integers    ${result.rc}    0

Operation Should Fail With Message
    [Documentation]    Verify the operation failed with a specific error message
    [Arguments]    ${result}    ${message}
    Should Not Be Equal As Integers    ${result.rc}    0
    Should Contain    ${result.stderr}    ${message}

Verify Docker Is Available
    [Documentation]    Check that Docker is installed and running
    ${result}=    Run Process    docker    info
    Should Be Equal As Integers    ${result.rc}    0

Verify Service Console Is Installed
    [Documentation]    Check that service-console CLI is available
    ${result}=    Run Process    ${SERVICE_CONSOLE}    --version
    Should Be Equal As Integers    ${result.rc}    0
    RETURN    ${result.stdout}
