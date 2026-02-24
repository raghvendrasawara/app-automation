*** Settings ***
Suite Name: Upgrade Operation Tests
Test Suite Mode: Depends
Timeout: 10m

*** Variables ***
${PACKAGE_PATH} = /path/to/package
${TIMEOUT} = 3600
${DRY_RUN} = false

*** Test Cases ***
*** Positive/Smoke Test ***
[Documentation]    Basic successful invocation with valid arguments
[Tags]              positive smoke
Test Upgrade Operation
    :Args - ${PACKAGE_PATH}
    Run Keyword If 'Dry Run' == '${DRY_RUN}'    run_upgrade dry_run=True
    Run Keyword If 'Timeout' > 0    set timeout ${TIMEOUT}
    Call Method Name service_console.run Upgrade

*** Positive Test with Variations ***
[Documentation]    Different valid argument combinations
[Tags]              positive variation
Test Upgrade Operation
    :Args - ${PACKAGE_PATH} --timeout=30
    Run Keyword If 'Dry Run' == '${DRY_RUN}'    run_upgrade dry_run=True
    Call Method Name service_console.run Upgrade

*** Negative Test - Missing Required Args ***
[Documentation]    Omit each required argument
[Tags]              negative missing_args
Test Upgrade Operation Without Package Path
    Run Keyword If 'Dry Run' == '${DRY_RUN}'    run_upgrade dry_run=True
    Call Method Name service_console.run Upgrade --timeout=30

*** Negative Test - Invalid Values ***
[Documentation]    Wrong types, out-of-range values
[Tags]              negative invalid_values
Test Upgrade Operation With Invalid Package Path
    Set Environment Variable PACKAGE_PATH ${PACKAGE_PATH}+invalid_value
    Run Keyword If 'Dry Run' == '${DRY_RUN}'    run_upgrade dry_run=True
    Call Method Name service_console.run Upgrade --timeout=30

*** Negative Test - Unknown Operation ***
[Documentation]    Test with non-existent operation name
[Tags]              negative unknown_operation
Test Unknown Operation
    Run Keyword If 'Dry Run' == '${DRY_RUN}'    run_upgrade dry_run=True
    Call Method Name service_console.run unknown_operation --timeout=30

*** Edge Case Test - Empty Strings ***
[Documentation]    Verify empty strings do not cause errors
[Tags]              edge_case empty_strings
Test Upgrade Operation With Empty Package Path
    Set Environment Variable PACKAGE_PATH ${PACKAGE_PATH}=
    Run Keyword If 'Dry Run' == '${DRY_RUN}'    run_upgrade dry_run=True
    Call Method Name service_console.run Upgrade --timeout=30

*** Edge Case Test - Very Large Values ***
[Documentation]    Verify large values do not cause errors
[Tags]              edge_case large_values
Test Upgrade Operation With Large Package Path
    Set Environment Variable PACKAGE_PATH ${PACKAGE_PATH}large_value
    Run Keyword If 'Dry Run' == '${DRY_RUN}'    run_upgrade dry_run=True
    Call Method Name service_console.run Upgrade --timeout=30

*** Edge Case Test - Special Characters ***
[Documentation]    Verify special characters do not cause errors
[Tags]              edge_case special_characters
Test Upgrade Operation With Special Package Path
    Set Environment Variable PACKAGE_PATH ${PACKAGE_PATH}!@#
    Run Keyword If 'Dry Run' == '${DRY_RUN}'    run_upgrade dry_run=True
    Call Method Name service_console.run Upgrade --timeout=30

*** Dry Run Test ***
[Documentation]    Verify --dry-run flag works correctly
[Tags]              positive dry_run
Test Upgrade Operation With Dry Run
    Set Environment Variable DRY_RUN true
    Run Keyword If 'Dry Run' == '${DRY_RUN}'    run_upgrade dry_run=True
    Call Method Name service_console.run Upgrade

*** Timeout Test ***
[Documentation]    Verify --timeout parameter behavior
[Tags]              positive timeout
Test Upgrade Operation With Timeout
    Set Environment Variable TIMEOUT 10
    Run Keyword If 'Dry Run' == '${DRY_RUN}'    run_upgrade dry_run=True
    Call Method Name service_console.run Upgrade