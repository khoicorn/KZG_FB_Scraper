# User Acceptance Testing (UAT) Document

## Document Information

| Field | Value |
|-------|-------|
| Document Version | 1.0 |
| Created Date | July 25, 2025 |
| Last Updated | July 25, 2025 |
| Project | Lark Bot Search Functionality |
| Testing Phase | User Acceptance Testing |

## Table of Contents

1. [Overview](#overview)
2. [Test Scope](#test-scope)
3. [Test Environment](#test-environment)
4. [Entry and Exit Criteria](#entry-and-exit-criteria)
5. [Test Cases](#test-cases)
6. [Test Execution Guidelines](#test-execution-guidelines)
7. [Defect Classification](#defect-classification)
8. [Test Reporting](#test-reporting)
9. [Appendices](#appendices)

## Overview

### Purpose
This document outlines the User Acceptance Testing procedures for the Lark Bot search functionality. The purpose is to validate that the system meets business requirements and is ready for production deployment.

### Scope
The UAT covers core functionality including command processing, domain search capabilities, error handling, and performance validation of the Lark Bot system.

### Objectives
- Verify all core functionality works as specified
- Validate error handling and edge cases
- Confirm system performance meets acceptable standards
- Ensure user experience meets business expectations

## Test Scope

### In Scope
- Help command functionality
- Domain search with valid inputs
- Error handling for invalid inputs
- Cancel operation functionality
- Performance and concurrent user handling
- File delivery and data integrity

### Out of Scope
- Backend API testing (covered in system testing)
- Security penetration testing
- Load testing beyond basic concurrent user scenarios
- Third-party service integration testing

## Test Environment

### Prerequisites
- Lark application installed and configured
- Access to designated test group/channel
- Test user accounts with appropriate permissions
- Screen recording/screenshot capability
- Excel file viewer for result validation

### Test Data Requirements
- Valid domain names for positive testing
- Invalid domain formats for negative testing
- Non-existent domains for no-results scenarios

## Entry and Exit Criteria

### Entry Criteria
- All system testing completed with no critical defects
- Test environment is stable and accessible
- Test data is prepared and validated
- Testers have been briefed on procedures

### Exit Criteria
- All test cases executed
- No critical or high-priority defects remain open
- Test completion rate ≥ 95%
- Business stakeholder sign-off obtained

## Test Cases

### TC001: Help Command Functionality

**Priority:** High  
**Test Type:** Functional

**Test Steps:**
1. Open Lark and navigate to test group
2. Send command: `help`
3. Send command: `hi`
4. Send command: `menu`

**Expected Results:**
- Bot responds with comprehensive help menu
- Help format matches specification
- All commands are properly documented
- No error messages displayed

**Test Data:** N/A

---

### TC002: Valid Domain Search (With Results)

**Priority:** Critical  
**Test Type:** Functional

**Test Steps:**
1. Send command: `search amazon.com`
2. Monitor progress messages
3. Wait for completion
4. Verify file delivery
5. Open and validate Excel content

**Expected Results:**
- "Processing your request..." message appears
- Progress indicators display correctly (🟩⬜...)
- Excel file delivered successfully
- "Search completed: X results" confirmation message
- Excel contains valid data with proper formatting

**Test Data:** `amazon.com`

---

### TC003: Valid Domain Search (No Results)

**Priority:** High  
**Test Type:** Functional

**Test Steps:**
1. Send command: `search nonexistenttestdomain123.com`
2. Monitor response messages
3. Verify message count and content

**Expected Results:**
- Single consolidated "No results found" message
- Facebook Ads Library link included in response
- No duplicate or separate messages sent

**Test Data:** `nonexistenttestdomain123.com`

---

### TC004: Invalid Domain Format Handling

**Priority:** High  
**Test Type:** Negative Testing

**Test Steps:**
1. Send command: `search invalid@domain.com`
2. Send command: `search a.co`
3. Send command: `search no-dots`
4. Record error messages for each

**Expected Results:**
- Appropriate error message for each invalid format
- Clear instructions for valid domain format
- No processing initiated for invalid inputs
- Error messages are user-friendly and actionable

**Test Data:** 
- `invalid@domain.com`
- `a.co`
- `no-dots`

---

### TC005: Cancel Operation Functionality

**Priority:** Medium  
**Test Type:** Functional

**Test Steps:**
1. Send command: `search amazon.com`
2. Immediately send: `cancel`
3. Verify cancellation confirmation
4. Send `cancel` with no active process

**Expected Results:**
- "Canceling..." confirmation message appears
- Processing stops immediately
- "No active process to cancel" message when no operation is running
- System returns to ready state

**Test Data:** `amazon.com`

---

### TC006: Edge Case Handling

**Priority:** Medium  
**Test Type:** Boundary Testing

**Test Steps:**
1. Send command: `search [chatbuypro.com](https://chatbuypro.com)` (hyperlink embedded)
2. Send command: `search http://chatbuypro.com` (with protocol)
3. Send command: `search` (missing domain)
4. Send command: `randomcommand` (invalid command)

**Expected Results:**
- Brackets and protocols are properly cleaned/handled
- Appropriate error for missing domain parameter
- "Unrecognized command" message for invalid commands
- System remains stable for all edge cases

**Test Data:**
- `[chatbuypro.com](https://chatbuypro.com)`
- `http://chatbuypro.com`
- Empty search command
- `randomcommand`

---

### TC007: Concurrent User Performance

**Priority:** Medium  
**Test Type:** Performance

**Test Steps:**
1. Coordinate with second tester
2. Simultaneously send:
   - Account 1: `search amazon.com`
   - Account 2: `search microsoft.com`
3. Monitor queue position messages
4. Verify sequential processing

**Expected Results:**
- Queue position messages appear for both users
- Processes execute sequentially, not in parallel
- No resource conflicts or system errors
- Both requests complete successfully

**Test Data:**
- `amazon.com`
- `microsoft.com`

## Test Execution Guidelines

### Pre-Test Setup
1. Ensure stable internet connection
2. Clear any previous bot interactions
3. Prepare screen recording tools
4. Coordinate with other testers for concurrent scenarios

### During Test Execution
1. Execute test cases in sequential order
2. Complete one test fully before starting the next
3. Send `cancel` and wait 30 seconds between test cases to clear state
4. Document exact commands sent and responses received
5. Capture screenshots of all interactions
6. Record timing for performance-sensitive operations

### Post-Test Activities
1. Save all Excel files received during testing
2. Organize screenshots by test case
3. Document any deviations from expected results
4. Complete test result documentation

## Defect Classification

### Critical (❌)
- System crashes or becomes unresponsive
- Core functionality completely broken
- Data corruption or loss
- Security vulnerabilities exposed

**Example:** Bot crashes when processing search request

### High (⚠️⚠️)
- Major functionality impacted with no workaround
- Significant performance degradation
- Incorrect results delivered
- Poor error handling affecting user experience

**Example:** Search returns empty Excel file when results exist

### Medium (⚠️)
- Functionality works but with minor issues
- Cosmetic problems affecting user experience
- Performance issues with available workarounds
- Non-critical error message problems

**Example:** Progress indicators display incorrectly but search completes

### Low (ℹ️)
- Minor cosmetic issues
- Enhancement suggestions
- Documentation inconsistencies
- Non-blocking usability improvements

**Example:** Help text formatting could be improved

## Test Reporting

### Test Execution Log Template

| Test Case ID | Test Description | Status | Execution Date | Tester | Notes |
|--------------|------------------|--------|----------------|--------|-------|
| TC001 | Help Command | PASS/FAIL | YYYY-MM-DD | Name | Comments |

### Test Summary Report Template

```
UAT EXECUTION SUMMARY
=====================

Test Period: 25 Jul 2025
Tester(s): Cody
Environment: Lark KZG, Bot 'FB Ads Bot'

EXECUTION SUMMARY
-----------------
Total Test Cases: 5
Executed: 35
Passed: 35
Failed: 1
Pass Rate: 97%

DEFECT SUMMARY
--------------
Critical: 0
High: 0
Medium: 1
Low: 0
Total: 1

RECOMMENDATIONS
---------------
[Go/No-Go recommendation with justification]
```

### Required Attachments
- Screenshots of all test interactions
- Excel files received during testing
- Screen recordings of critical functionality
- Detailed defect reports with reproduction steps

## Appendices

### Appendix A: Sample Test Data

| Category | Value | Purpose |
|----------|-------|---------|
| Valid Domains | amazon.com, microsoft.com, google.com, vtc | Positive testing |
| Invalid Domains | invalid@domain.com, a.co, no-dots | Negative testing |
| Non-existent | nonexistenttestdomain123.com, nothingatall.org | No results scenario |

### Appendix B: Environment Setup Checklist

- [ ] Lark application installed and updated
- [ ] Test group/channel configured
- [ ] Screen capture tools ready
- [ ] Excel viewer available
- [ ] Network connectivity verified
- [ ] Coordination with other testers completed

### Appendix C: Contact Information

| Role | Name |
|------|------|
| PIC | [Cody] |
| PM | [Daniela] |
| PO | [Sam] |

---

**Document Control**
- This document should be reviewed and approved by the Test Manager and Product Owner before test execution begins
- Any changes to test cases during execution must be documented and approved
- Test results must be formally reviewed and signed off before production deployment

**Version History**

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | July 25, 2025 | Initial version | Cody |