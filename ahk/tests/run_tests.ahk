#NoEnv
#SingleInstance Force
SetWorkingDir %A_ScriptDir%

; Simple test runner script to execute all tests

; Display banner
FileAppend, ===============================`n, *, UTF-8
FileAppend, NLLB Translator AutoHotkey Tests`n, *, UTF-8
FileAppend, ===============================`n`n, *, UTF-8

; Array of test scripts
testScripts := []
testScripts.Push("unit\test_detect_language.ahk")
testScripts.Push("unit\test_json_helpers.ahk")
testScripts.Push("unit\test_adaptive_translation.ahk")
testScripts.Push("integration\test_translation_workflow.ahk")
testScripts.Push("integration\test_adaptive_workflow.ahk")
testScripts.Push("e2e\test_adaptive_e2e.ahk")

; Run each test and collect results
totalTests := 0
passedTests := 0
failedTests := 0

for index, script in testScripts {
    FileAppend, % "Running test file: " . script . "`n", *, UTF-8
    
    ; Run the test script and capture exit code
    RunWait, "%A_AhkPath%" "%A_ScriptDir%\%script%", , UseErrorLevel
    
    ; Check if test failed
    if (ErrorLevel != 0) {
        failedTests++
        FileAppend, % "❌ Tests in " . script . " FAILED`n`n", *, UTF-8
    } else {
        passedTests++
        FileAppend, % "✅ Tests in " . script . " PASSED`n`n", *, UTF-8
    }
    totalTests++
}

; Display summary
FileAppend, ===============================`n, *, UTF-8
FileAppend, % "Test Summary:`n", *, UTF-8
FileAppend, % "- Total test files: " . totalTests . "`n", *, UTF-8
FileAppend, % "- Passed: " . passedTests . "`n", *, UTF-8
FileAppend, % "- Failed: " . failedTests . "`n", *, UTF-8
FileAppend, ===============================`n, *, UTF-8

; Exit with appropriate code
if (failedTests > 0) {
    ExitApp, 1
} else {
    ExitApp, 0
}