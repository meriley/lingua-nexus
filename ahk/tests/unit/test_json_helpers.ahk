#Include %A_ScriptDir%\..\..\system-translator.ahk
#Include %A_ScriptDir%\..\ahk-unit.ahk

; Start test suite
TestSuite("JSON Helper Functions Tests")

; Test cases
Test_EscapeJSON()
{
    global TestCount, TestPassed, TestFailed, TestResults
    TestCount++
    
    testName := "Test_EscapeJSON"
    
    try {
        ; Test escaping quotes
        result := EscapeJSON("Hello ""world""")
        Assert.Equal(result, "Hello \""world\""", "Should escape double quotes")
        
        ; Test escaping backslashes
        result := EscapeJSON("C:\\path\\to\\file")
        Assert.Equal(result, "C:\\\\path\\\\to\\\\file", "Should escape backslashes")
        
        ; Test escaping newlines and tabs
        result := EscapeJSON("Hello`nworld`twith tabs")
        Assert.Equal(result, "Hello\nworld\twith tabs", "Should escape newlines and tabs")
        
        ; Test escaping all special characters
        result := EscapeJSON("\"Hello\"`nWorld\\")
        Assert.Equal(result, "\""Hello\""\nWorld\\\\", "Should escape all special characters")
        
        TestPassed++
        TestResults[testName] := {passed: true}
        FileAppend, % "✓ " . testName . "`n", *, UTF-8
    } catch e {
        TestFailed++
        TestResults[testName] := {passed: false, message: e.Message}
        FileAppend, % "✗ " . testName . ": " . e.Message . "`n", *, UTF-8
    }
}

Test_UnescapeJSON()
{
    global TestCount, TestPassed, TestFailed, TestResults
    TestCount++
    
    testName := "Test_UnescapeJSON"
    
    try {
        ; Test unescaping quotes
        result := UnescapeJSON("Hello \""world\""")
        Assert.Equal(result, "Hello ""world""", "Should unescape double quotes")
        
        ; Test unescaping backslashes
        result := UnescapeJSON("C:\\\\path\\\\to\\\\file")
        Assert.Equal(result, "C:\\path\\to\\file", "Should unescape backslashes")
        
        ; Test unescaping newlines and tabs
        result := UnescapeJSON("Hello\nworld\twith tabs")
        Assert.Equal(result, "Hello`nworld`twith tabs", "Should unescape newlines and tabs")
        
        ; Test unescaping all special characters
        result := UnescapeJSON("\""Hello\""\nWorld\\\\")
        Assert.Equal(result, "\"Hello\"`nWorld\\", "Should unescape all special characters")
        
        TestPassed++
        TestResults[testName] := {passed: true}
        FileAppend, % "✓ " . testName . "`n", *, UTF-8
    } catch e {
        TestFailed++
        TestResults[testName] := {passed: false, message: e.Message}
        FileAppend, % "✗ " . testName . ": " . e.Message . "`n", *, UTF-8
    }
}

Test_JSON_Roundtrip()
{
    global TestCount, TestPassed, TestFailed, TestResults
    TestCount++
    
    testName := "Test_JSON_Roundtrip"
    
    try {
        ; Test round trip: original -> escaped -> unescaped
        original := "Complex string with ""quotes"", newlines`nand backslashes: C:\\path"
        escaped := EscapeJSON(original)
        unescaped := UnescapeJSON(escaped)
        
        Assert.Equal(unescaped, original, "Round trip should preserve the original string")
        
        TestPassed++
        TestResults[testName] := {passed: true}
        FileAppend, % "✓ " . testName . "`n", *, UTF-8
    } catch e {
        TestFailed++
        TestResults[testName] := {passed: false, message: e.Message}
        FileAppend, % "✗ " . testName . ": " . e.Message . "`n", *, UTF-8
    }
}

; Run all test functions
Test_EscapeJSON()
Test_UnescapeJSON()
Test_JSON_Roundtrip()

; Generate report and exit
RunTests()