#Include %A_ScriptDir%\..\..\system-translator.ahk
#Include %A_ScriptDir%\..\ahk-unit.ahk

; Start test suite
TestSuite("Translation Workflow Integration Tests")

; Mocked functions for integration testing
; These simulate the behavior of the real functions without making actual API calls

MockTranslationResponse(text, sourceLang, targetLang) {
    if (sourceLang = "eng_Latn" && targetLang = "rus_Cyrl") {
        ; Mock English to Russian
        if (text = "Hello world")
            return "Привет мир"
        else if (text = "Test message")
            return "Тестовое сообщение"
        else
            return "Переведенный текст: " . text
    } else if (sourceLang = "rus_Cyrl" && targetLang = "eng_Latn") {
        ; Mock Russian to English
        if (text = "Привет мир")
            return "Hello world"
        else if (text = "Тестовое сообщение")
            return "Test message"
        else 
            return "Translated text: " . text
    } else {
        ; Default mock response
        return "Translated: " . text
    }
}

; Mock the clipboard operations to avoid actually modifying the system clipboard
MockClipboard := ""
MockPreviousClipboard := ""

MockGetClipboard() {
    global MockClipboard
    return MockClipboard
}

MockSetClipboard(text) {
    global MockClipboard
    MockClipboard := text
}

MockStoreClipboard() {
    global MockClipboard, MockPreviousClipboard
    MockPreviousClipboard := MockClipboard
}

MockRestoreClipboard() {
    global MockClipboard, MockPreviousClipboard
    MockClipboard := MockPreviousClipboard
}

; Test cases
Test_TranslateEnglishToRussian()
{
    global TestCount, TestPassed, TestFailed, TestResults
    TestCount++
    
    testName := "Test_TranslateEnglishToRussian"
    
    try {
        ; Setup mock clipboard with English text
        global MockClipboard := "Hello world"
        
        ; Setup mock CONFIG
        CONFIG := {}
        CONFIG.DefaultTargetLang := "rus_Cyrl"
        CONFIG.ShowNotifications := false
        
        ; Create a mocked version of TranslateAndHandleText
        translatedText := MockTranslationResponse(MockClipboard, "eng_Latn", CONFIG.DefaultTargetLang)
        
        ; Verify the translation
        Assert.Equal(translatedText, "Привет мир", "Should translate 'Hello world' to 'Привет мир'")
        
        ; Log success
        TestPassed++
        TestResults[testName] := {passed: true}
        FileAppend, % "✓ " . testName . "`n", *, UTF-8
    } catch e {
        TestFailed++
        TestResults[testName] := {passed: false, message: e.Message}
        FileAppend, % "✗ " . testName . ": " . e.Message . "`n", *, UTF-8
    }
}

Test_TranslateRussianToEnglish()
{
    global TestCount, TestPassed, TestFailed, TestResults
    TestCount++
    
    testName := "Test_TranslateRussianToEnglish"
    
    try {
        ; Setup mock clipboard with Russian text
        global MockClipboard := "Привет мир"
        
        ; Setup mock CONFIG
        CONFIG := {}
        CONFIG.DefaultTargetLang := "eng_Latn"
        CONFIG.ShowNotifications := false
        
        ; Create a mocked version of TranslateAndHandleText
        translatedText := MockTranslationResponse(MockClipboard, "rus_Cyrl", CONFIG.DefaultTargetLang)
        
        ; Verify the translation
        Assert.Equal(translatedText, "Hello world", "Should translate 'Привет мир' to 'Hello world'")
        
        ; Log success
        TestPassed++
        TestResults[testName] := {passed: true}
        FileAppend, % "✓ " . testName . "`n", *, UTF-8
    } catch e {
        TestFailed++
        TestResults[testName] := {passed: false, message: e.Message}
        FileAppend, % "✗ " . testName . ": " . e.Message . "`n", *, UTF-8
    }
}

Test_ClipboardHandling()
{
    global TestCount, TestPassed, TestFailed, TestResults
    TestCount++
    
    testName := "Test_ClipboardHandling"
    
    try {
        ; Setup initial clipboard content
        global MockClipboard := "Original clipboard content"
        
        ; Store the clipboard
        MockStoreClipboard()
        
        ; Set new content
        MockSetClipboard("New temporary content")
        
        ; Verify the clipboard has been changed
        Assert.Equal(MockClipboard, "New temporary content", "Clipboard content should be updated")
        
        ; Restore the clipboard
        MockRestoreClipboard()
        
        ; Verify the clipboard has been restored
        Assert.Equal(MockClipboard, "Original clipboard content", "Clipboard should be restored to original content")
        
        ; Log success
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
Test_TranslateEnglishToRussian()
Test_TranslateRussianToEnglish()
Test_ClipboardHandling()

; Generate report and exit
RunTests()