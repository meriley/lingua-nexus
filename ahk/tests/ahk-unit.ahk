; ===================================================
; Simple Unit Testing Framework for AutoHotkey
; ===================================================

class Assert {
    static Equal(actual, expected, message := "") {
        if (actual != expected) {
            message := message ? message : "Expected '" . expected . "' but got '" . actual . "'"
            throw Exception(message)
        }
        return true
    }
    
    static NotEqual(actual, expected, message := "") {
        if (actual == expected) {
            message := message ? message : "Expected values to be different, but both are '" . actual . "'"
            throw Exception(message)
        }
        return true
    }
    
    static True(actual, message := "") {
        if (!actual) {
            message := message ? message : "Expected true but got false"
            throw Exception(message)
        }
        return true
    }
    
    static False(actual, message := "") {
        if (actual) {
            message := message ? message : "Expected false but got true"
            throw Exception(message)
        }
        return true
    }
    
    static Contains(haystack, needle, message := "") {
        if (!InStr(haystack, needle)) {
            message := message ? message : "Expected '" . haystack . "' to contain '" . needle . "'"
            throw Exception(message)
        }
        return true
    }
}

; Global test suite tracking
global TestSuiteName := ""
global TestResults := {}
global TestCount := 0
global TestPassed := 0
global TestFailed := 0

; Initialize a test suite
TestSuite(name) {
    global TestSuiteName, TestResults, TestCount, TestPassed, TestFailed
    TestSuiteName := name
    TestResults := {}
    TestCount := 0
    TestPassed := 0
    TestFailed := 0
    
    ; Initialize console output
    FileAppend, `n============================================`n, *, UTF-8
    FileAppend, % "Test Suite: " . TestSuiteName . "`n", *, UTF-8
    FileAppend, ============================================`n`n, *, UTF-8
}

; Run all the tests and report results
RunTests() {
    global TestSuiteName, TestCount, TestPassed, TestFailed
    
    ; Report results
    FileAppend, `n============================================`n, *, UTF-8
    FileAppend, % "Results for: " . TestSuiteName . "`n", *, UTF-8
    FileAppend, ============================================`n, *, UTF-8
    FileAppend, % "Tests: " . TestCount . ", Passed: " . TestPassed . ", Failed: " . TestFailed . "`n", *, UTF-8
    
    if (TestFailed > 0) {
        FileAppend, `nFailed Tests:`n, *, UTF-8
        for testName, result in TestResults {
            if (!result.passed) {
                FileAppend, % "- " . testName . ": " . result.message . "`n", *, UTF-8
            }
        }
    }
    
    ; Exit with appropriate code
    if (TestFailed > 0) {
        ExitApp, 1
    } else {
        ExitApp, 0
    }
}