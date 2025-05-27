#Include %A_ScriptDir%\..\..\system-translator.ahk
#Include %A_ScriptDir%\..\ahk-unit.ahk

; Start test suite
TestSuite("Language Detection Tests")

; Test function
DetectLanguage(text) {
    ; Count Cyrillic characters
    cyrillic_chars := 0
    Loop, Parse, text
    {
        char_code := Asc(A_LoopField)
        if (char_code >= 0x0400 && char_code <= 0x04FF)
            cyrillic_chars++
    }
    
    ; Simple heuristic: if more than 30% of characters are Cyrillic, assume Russian
    text_length := StrLen(text)
    is_russian := text_length > 0 ? (cyrillic_chars / text_length > 0.3) : false
    
    return is_russian ? "rus_Cyrl" : "eng_Latn"
}

; Test cases
Test_Detect_English()
{
    global TestCount, TestPassed, TestFailed, TestResults
    TestCount++
    
    testName := "Test_Detect_English"
    
    try {
        result := DetectLanguage("Hello world")
        Assert.Equal(result, "eng_Latn", "Should detect English language")
        TestPassed++
        TestResults[testName] := {passed: true}
        FileAppend, % "✓ " . testName . "`n", *, UTF-8
    } catch e {
        TestFailed++
        TestResults[testName] := {passed: false, message: e.Message}
        FileAppend, % "✗ " . testName . ": " . e.Message . "`n", *, UTF-8
    }
}

Test_Detect_Russian()
{
    global TestCount, TestPassed, TestFailed, TestResults
    TestCount++
    
    testName := "Test_Detect_Russian"
    
    try {
        result := DetectLanguage("Привет мир")
        Assert.Equal(result, "rus_Cyrl", "Should detect Russian language")
        TestPassed++
        TestResults[testName] := {passed: true}
        FileAppend, % "✓ " . testName . "`n", *, UTF-8
    } catch e {
        TestFailed++
        TestResults[testName] := {passed: false, message: e.Message}
        FileAppend, % "✗ " . testName . ": " . e.Message . "`n", *, UTF-8
    }
}

Test_Detect_Mixed_Predominantly_English()
{
    global TestCount, TestPassed, TestFailed, TestResults
    TestCount++
    
    testName := "Test_Detect_Mixed_Predominantly_English"
    
    try {
        result := DetectLanguage("Hello world with some Привет")
        Assert.Equal(result, "eng_Latn", "Should detect mixed text as English")
        TestPassed++
        TestResults[testName] := {passed: true}
        FileAppend, % "✓ " . testName . "`n", *, UTF-8
    } catch e {
        TestFailed++
        TestResults[testName] := {passed: false, message: e.Message}
        FileAppend, % "✗ " . testName . ": " . e.Message . "`n", *, UTF-8
    }
}

Test_Detect_Mixed_Predominantly_Russian()
{
    global TestCount, TestPassed, TestFailed, TestResults
    TestCount++
    
    testName := "Test_Detect_Mixed_Predominantly_Russian"
    
    try {
        result := DetectLanguage("Привет мир и hello world")
        Assert.Equal(result, "rus_Cyrl", "Should detect mixed text as Russian")
        TestPassed++
        TestResults[testName] := {passed: true}
        FileAppend, % "✓ " . testName . "`n", *, UTF-8
    } catch e {
        TestFailed++
        TestResults[testName] := {passed: false, message: e.Message}
        FileAppend, % "✗ " . testName . ": " . e.Message . "`n", *, UTF-8
    }
}

Test_Empty_String()
{
    global TestCount, TestPassed, TestFailed, TestResults
    TestCount++
    
    testName := "Test_Empty_String"
    
    try {
        result := DetectLanguage("")
        Assert.Equal(result, "eng_Latn", "Should default to English for empty string")
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
Test_Detect_English()
Test_Detect_Russian()
Test_Detect_Mixed_Predominantly_English()
Test_Detect_Mixed_Predominantly_Russian()
Test_Empty_String()

; Generate report and exit
RunTests()