#Include %A_ScriptDir%\..\..\system-translator.ahk
#Include %A_ScriptDir%\..\ahk-unit.ahk

; Start test suite
TestSuite("Adaptive Translation Tests")

; Mock HTTP class for testing
class MockHttp {
    __New() {
        this.Status := 200
        this.ResponseText := ""
        this.LastUrl := ""
        this.LastData := ""
        this.LastHeaders := Map()
    }
    
    Open(method, url, async) {
        this.LastUrl := url
    }
    
    SetRequestHeader(name, value) {
        this.LastHeaders[name] := value
    }
    
    Send(data) {
        this.LastData := data
    }
}

; Test adaptive translation detection
Test_AdaptiveTranslationDetection()
{
    global TestCount, TestPassed, TestFailed, TestResults
    TestCount++
    
    testName := "Test_AdaptiveTranslationDetection"
    
    try {
        ; Test short text (should not use adaptive)
        shortText := "Hello world"
        useAdaptive := Config.EnableAdaptiveTranslation && StrLen(shortText) > Config.AdaptiveForLongText
        Assert.Equal(useAdaptive, false, "Short text should not trigger adaptive translation")
        
        ; Test long text (should use adaptive)
        longText := "This is a very long text that exceeds the adaptive threshold and should trigger adaptive translation with quality optimization features. " .
                   "The system should detect this and use the adaptive endpoint for better translation quality with semantic chunking and quality assessment."
        useAdaptive := Config.EnableAdaptiveTranslation && StrLen(longText) > Config.AdaptiveForLongText
        Assert.Equal(useAdaptive, true, "Long text should trigger adaptive translation")
        
        ; Test with adaptive disabled
        originalSetting := Config.EnableAdaptiveTranslation
        Config.EnableAdaptiveTranslation := false
        useAdaptive := Config.EnableAdaptiveTranslation && StrLen(longText) > Config.AdaptiveForLongText
        Assert.Equal(useAdaptive, false, "Should not use adaptive when disabled")
        
        ; Restore setting
        Config.EnableAdaptiveTranslation := originalSetting
        
        TestPassed++
        TestResults[testName] := {passed: true}
        FileAppend, % "✓ " . testName . "`n", *, UTF-8
    } catch e {
        TestFailed++
        TestResults[testName] := {passed: false, message: e.Message}
        FileAppend, % "✗ " . testName . ": " . e.Message . "`n", *, UTF-8
    }
}

; Test adaptive request formatting
Test_AdaptiveRequestFormat()
{
    global TestCount, TestPassed, TestFailed, TestResults
    TestCount++
    
    testName := "Test_AdaptiveRequestFormat"
    
    try {
        ; Create a test instance
        translator := NLLBTranslator()
        
        ; Mock the HTTP request to capture the data
        originalComObject := ComObject
        mockHttp := MockHttp()
        
        ; Override ComObject creation for this test
        ComObject := (progid) => mockHttp
        
        ; Test adaptive request data
        text := "Test text for adaptive translation"
        sourceLang := "auto"
        targetLang := "eng_Latn"
        
        try {
            result := translator.SendAdaptiveTranslationRequest(text, sourceLang, targetLang)
        } catch {
            ; Expected to fail since we're mocking, but we can check the data
        }
        
        ; Verify URL
        Assert.Contains(mockHttp.LastUrl, "/adaptive/translate", "Should use adaptive endpoint")
        
        ; Verify request data contains required fields
        Assert.Contains(mockHttp.LastData, '"text":"' . translator.EscapeJSON(text) . '"', "Should contain escaped text")
        Assert.Contains(mockHttp.LastData, '"source_lang":"' . sourceLang . '"', "Should contain source language")
        Assert.Contains(mockHttp.LastData, '"target_lang":"' . targetLang . '"', "Should contain target language")
        Assert.Contains(mockHttp.LastData, '"user_preference":"' . Config.UserPreference . '"', "Should contain user preference")
        Assert.Contains(mockHttp.LastData, '"max_optimization_time":' . Config.MaxOptimizationTime, "Should contain max optimization time")
        
        ; Restore ComObject
        ComObject := originalComObject
        
        TestPassed++
        TestResults[testName] := {passed: true}
        FileAppend, % "✓ " . testName . "`n", *, UTF-8
    } catch e {
        TestFailed++
        TestResults[testName] := {passed: false, message: e.Message}
        FileAppend, % "✗ " . testName . ": " . e.Message . "`n", *, UTF-8
        
        ; Restore ComObject on error
        ComObject := originalComObject
    }
}

; Test progressive translation detection
Test_ProgressiveTranslationDetection()
{
    global TestCount, TestPassed, TestFailed, TestResults
    TestCount++
    
    testName := "Test_ProgressiveTranslationDetection"
    
    try {
        ; Test text length thresholds for progressive translation
        mediumText := "This is a medium length text that should trigger adaptive but not progressive translation features."
        veryLongText := "This is a very long text that should trigger both adaptive and progressive translation features with real-time updates. " .
                       "The progressive system should break this text into semantic chunks and provide incremental translation updates to enhance " .
                       "user experience and translation quality through advanced optimization algorithms and contextual analysis techniques that " .
                       "maintain semantic coherence across chunk boundaries while delivering superior translation results."
        
        ; Test medium text (adaptive but not progressive)
        useAdaptive := Config.EnableAdaptiveTranslation && StrLen(mediumText) > Config.AdaptiveForLongText
        useProgressive := useAdaptive && Config.EnableProgressiveUI && StrLen(mediumText) > 1000
        
        Assert.Equal(useAdaptive, true, "Medium text should trigger adaptive")
        Assert.Equal(useProgressive, false, "Medium text should not trigger progressive")
        
        ; Test very long text (both adaptive and progressive)
        useAdaptive := Config.EnableAdaptiveTranslation && StrLen(veryLongText) > Config.AdaptiveForLongText
        useProgressive := useAdaptive && Config.EnableProgressiveUI && StrLen(veryLongText) > 1000
        
        Assert.Equal(useAdaptive, true, "Very long text should trigger adaptive")
        Assert.Equal(useProgressive, true, "Very long text should trigger progressive")
        
        TestPassed++
        TestResults[testName] := {passed: true}
        FileAppend, % "✓ " . testName . "`n", *, UTF-8
    } catch e {
        TestFailed++
        TestResults[testName] := {passed: false, message: e.Message}
        FileAppend, % "✗ " . testName . ": " . e.Message . "`n", *, UTF-8
    }
}

; Test quality metrics parsing
Test_QualityMetricsParsing()
{
    global TestCount, TestPassed, TestFailed, TestResults
    TestCount++
    
    testName := "Test_QualityMetricsParsing"
    
    try {
        ; Mock adaptive response JSON
        responseJson := '{'
        responseJson .= '"translation":"Test translation result",'
        responseJson .= '"quality_score":0.92,'
        responseJson .= '"quality_grade":"A",'
        responseJson .= '"optimization_applied":true,'
        responseJson .= '"cache_hit":false,'
        responseJson .= '"processing_time":2.34,'
        responseJson .= '"chunks_processed":3,'
        responseJson .= '"semantic_coherence":0.96'
        responseJson .= '}'
        
        ; Test regex parsing for each field
        if (RegExMatch(responseJson, '"translation"\s*:\s*"(.+?)"', &match)) {
            translation := match[1]
            Assert.Equal(translation, "Test translation result", "Should extract translation correctly")
        }
        
        if (RegExMatch(responseJson, '"quality_score"\s*:\s*([0-9.]+)', &match)) {
            qualityScore := Float(match[1])
            Assert.Equal(qualityScore, 0.92, "Should extract quality score correctly")
        }
        
        if (RegExMatch(responseJson, '"quality_grade"\s*:\s*"([A-F])"', &match)) {
            qualityGrade := match[1]
            Assert.Equal(qualityGrade, "A", "Should extract quality grade correctly")
        }
        
        if (RegExMatch(responseJson, '"optimization_applied"\s*:\s*(true|false)', &match)) {
            optimizationApplied := (match[1] == "true")
            Assert.Equal(optimizationApplied, true, "Should extract optimization status correctly")
        }
        
        if (RegExMatch(responseJson, '"cache_hit"\s*:\s*(true|false)', &match)) {
            cacheHit := (match[1] == "true")
            Assert.Equal(cacheHit, false, "Should extract cache hit status correctly")
        }
        
        if (RegExMatch(responseJson, '"processing_time"\s*:\s*([0-9.]+)', &match)) {
            processingTime := Float(match[1])
            Assert.Equal(processingTime, 2.34, "Should extract processing time correctly")
        }
        
        TestPassed++
        TestResults[testName] := {passed: true}
        FileAppend, % "✓ " . testName . "`n", *, UTF-8
    } catch e {
        TestFailed++
        TestResults[testName] := {passed: false, message: e.Message}
        FileAppend, % "✗ " . testName . ": " . e.Message . "`n", *, UTF-8
    }
}

; Test quality information formatting
Test_QualityInfoFormatting()
{
    global TestCount, TestPassed, TestFailed, TestResults
    TestCount++
    
    testName := "Test_QualityInfoFormatting"
    
    try {
        ; Mock result object for quality formatting
        result := Map()
        result["qualityGrade"] := "A"
        result["optimizationApplied"] := true
        result["cacheHit"] := false
        result["processingTime"] := 2.34
        
        ; Test quality info building logic
        qualityInfo := ""
        if (Config.ShowQualityGrades && result.Has("qualityGrade")) {
            qualityInfo := " (Grade: " . result["qualityGrade"]
            
            if (result.Has("optimizationApplied") && result["optimizationApplied"]) {
                qualityInfo .= " ⚡"
            }
            
            if (result.Has("cacheHit") && result["cacheHit"]) {
                qualityInfo .= " 💾"
            }
            
            if (result.Has("processingTime")) {
                processingTime := Round(result["processingTime"], 2)
                qualityInfo .= " " . processingTime . "s"
            }
            
            qualityInfo .= ")"
        }
        
        expectedInfo := " (Grade: A ⚡ 2.34s)"
        Assert.Equal(qualityInfo, expectedInfo, "Should format quality info correctly")
        
        ; Test with cache hit
        result["cacheHit"] := true
        result["optimizationApplied"] := false
        
        qualityInfo := ""
        if (Config.ShowQualityGrades && result.Has("qualityGrade")) {
            qualityInfo := " (Grade: " . result["qualityGrade"]
            
            if (result.Has("optimizationApplied") && result["optimizationApplied"]) {
                qualityInfo .= " ⚡"
            }
            
            if (result.Has("cacheHit") && result["cacheHit"]) {
                qualityInfo .= " 💾"
            }
            
            if (result.Has("processingTime")) {
                processingTime := Round(result["processingTime"], 2)
                qualityInfo .= " " . processingTime . "s"
            }
            
            qualityInfo .= ")"
        }
        
        expectedInfo := " (Grade: A 💾 2.34s)"
        Assert.Equal(qualityInfo, expectedInfo, "Should show cache indicator when applicable")
        
        TestPassed++
        TestResults[testName] := {passed: true}
        FileAppend, % "✓ " . testName . "`n", *, UTF-8
    } catch e {
        TestFailed++
        TestResults[testName] := {passed: false, message: e.Message}
        FileAppend, % "✗ " . testName . ": " . e.Message . "`n", *, UTF-8
    }
}

; Test configuration validation
Test_AdaptiveConfigValidation()
{
    global TestCount, TestPassed, TestFailed, TestResults
    TestCount++
    
    testName := "Test_AdaptiveConfigValidation"
    
    try {
        ; Verify adaptive configuration exists and has correct types
        Assert.IsType(Config.EnableAdaptiveTranslation, "Boolean", "EnableAdaptiveTranslation should be boolean")
        Assert.IsType(Config.UserPreference, "String", "UserPreference should be string")
        Assert.IsType(Config.EnableProgressiveUI, "Boolean", "EnableProgressiveUI should be boolean")
        Assert.IsType(Config.QualityThreshold, "Number", "QualityThreshold should be number")
        Assert.IsType(Config.AdaptiveForLongText, "Integer", "AdaptiveForLongText should be integer")
        Assert.IsType(Config.MaxOptimizationTime, "Number", "MaxOptimizationTime should be number")
        Assert.IsType(Config.ShowQualityGrades, "Boolean", "ShowQualityGrades should be boolean")
        
        ; Verify endpoint configuration
        Assert.Equal(Config.AdaptiveEndpoint, "/adaptive/translate", "Adaptive endpoint should be correct")
        Assert.Equal(Config.ProgressiveEndpoint, "/adaptive/translate/progressive", "Progressive endpoint should be correct")
        
        ; Verify user preference is valid
        validPreferences := ["fast", "balanced", "quality"]
        Assert.Contains(validPreferences, Config.UserPreference, "UserPreference should be valid")
        
        ; Verify thresholds are reasonable
        Assert.GreaterThan(Config.AdaptiveForLongText, 0, "AdaptiveForLongText should be positive")
        Assert.GreaterThan(Config.QualityThreshold, 0, "QualityThreshold should be positive")
        Assert.LessThan(Config.QualityThreshold, 1, "QualityThreshold should be less than 1")
        Assert.GreaterThan(Config.MaxOptimizationTime, 0, "MaxOptimizationTime should be positive")
        
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
Test_AdaptiveTranslationDetection()
Test_AdaptiveRequestFormat()
Test_ProgressiveTranslationDetection()
Test_QualityMetricsParsing()
Test_QualityInfoFormatting()
Test_AdaptiveConfigValidation()

; Generate report and exit
RunTests()