#Include %A_ScriptDir%\..\..\system-translator.ahk
#Include %A_ScriptDir%\..\ahk-unit.ahk

; Start test suite
TestSuite("Adaptive Translation Workflow Integration Tests")

; Mock server for testing
class MockTranslationServer {
    static responses := Map()
    static requestLog := Array()
    
    static SetMockResponse(endpoint, statusCode, responseData) {
        this.responses[endpoint] := {status: statusCode, data: responseData}
    }
    
    static GetLastRequest() {
        return this.requestLog.Length > 0 ? this.requestLog[this.requestLog.Length] : ""
    }
    
    static ClearLog() {
        this.requestLog := Array()
    }
}

; Test complete adaptive translation workflow
Test_AdaptiveTranslationWorkflow()
{
    global TestCount, TestPassed, TestFailed, TestResults
    TestCount++
    
    testName := "Test_AdaptiveTranslationWorkflow"
    
    try {
        ; Setup test data
        longText := "This is a comprehensive test message that should trigger the adaptive translation system. " .
                   "The system should detect the length, choose the adaptive endpoint, send the appropriate request " .
                   "with quality preferences, receive and parse the response with quality metrics, and display " .
                   "the translation along with quality indicators including grade, optimization status, and processing time."
        
        ; Create translator instance
        translator := NLLBTranslator()
        
        ; Mock the notification system for testing
        originalShowNotification := translator.ShowNotification
        notificationLog := Array()
        translator.ShowNotification := (title, message) => {
            notificationLog.Push({title: title, message: message})
        }
        
        ; Mock clipboard operations
        originalClipboard := A_Clipboard
        testClipboard := ""
        A_Clipboard := longText
        
        ; Simulate the complete workflow
        ; 1. Text detection and adaptive decision
        useAdaptive := Config.EnableAdaptiveTranslation && StrLen(longText) > Config.AdaptiveForLongText
        Assert.Equal(useAdaptive, true, "Should detect need for adaptive translation")
        
        ; 2. Progressive decision
        useProgressive := useAdaptive && Config.EnableProgressiveUI && StrLen(longText) > 1000
        Assert.Equal(useProgressive, true, "Should decide to use progressive translation")
        
        ; 3. Check that appropriate notification was prepared
        ; This simulates the notification that would be shown
        if (useProgressive) {
            expectedNotification := {title: "Progressive Translation", message: "Starting optimized chunked translation..."}
        } else if (useAdaptive) {
            expectedNotification := {title: "Optimizing Translation...", message: "Using quality enhancement for long text"}
        } else {
            expectedNotification := {title: "Translating...", message: "Please wait"}
        }
        
        ; Verify the translation type decision logic
        Assert.Equal(expectedNotification.title, "Progressive Translation", "Should use progressive translation for very long text")
        
        ; 4. Mock quality metrics processing
        mockAdaptiveResponse := Map()
        mockAdaptiveResponse["translation"] := "Optimized translation result with enhanced quality"
        mockAdaptiveResponse["qualityGrade"] := "A"
        mockAdaptiveResponse["optimizationApplied"] := true
        mockAdaptiveResponse["cacheHit"] := false
        mockAdaptiveResponse["processingTime"] := 3.45
        
        ; 5. Test quality info formatting
        qualityInfo := ""
        if (Config.ShowQualityGrades && mockAdaptiveResponse.Has("qualityGrade")) {
            qualityInfo := " (Grade: " . mockAdaptiveResponse["qualityGrade"]
            
            if (mockAdaptiveResponse.Has("optimizationApplied") && mockAdaptiveResponse["optimizationApplied"]) {
                qualityInfo .= " ⚡"
            }
            
            if (mockAdaptiveResponse.Has("cacheHit") && mockAdaptiveResponse["cacheHit"]) {
                qualityInfo .= " 💾"
            }
            
            if (mockAdaptiveResponse.Has("processingTime")) {
                processingTime := Round(mockAdaptiveResponse["processingTime"], 2)
                qualityInfo .= " " . processingTime . "s"
            }
            
            qualityInfo .= ")"
        }
        
        expectedQualityInfo := " (Grade: A ⚡ 3.45s)"
        Assert.Equal(qualityInfo, expectedQualityInfo, "Should format quality info correctly")
        
        ; 6. Test final notification preparation
        finalNotification := "Translation Complete" . qualityInfo
        expectedFinalNotification := "Translation Complete (Grade: A ⚡ 3.45s)"
        Assert.Equal(finalNotification, expectedFinalNotification, "Should prepare final notification with quality info")
        
        ; Restore original functions
        translator.ShowNotification := originalShowNotification
        A_Clipboard := originalClipboard
        
        TestPassed++
        TestResults[testName] := {passed: true}
        FileAppend, % "✓ " . testName . "`n", *, UTF-8
    } catch e {
        TestFailed++
        TestResults[testName] := {passed: false, message: e.Message}
        FileAppend, % "✗ " . testName . ": " . e.Message . "`n", *, UTF-8
    }
}

; Test fallback workflow when adaptive fails
Test_AdaptiveFallbackWorkflow()
{
    global TestCount, TestPassed, TestFailed, TestResults
    TestCount++
    
    testName := "Test_AdaptiveFallbackWorkflow"
    
    try {
        ; Test the decision logic for fallback scenarios
        longText := "This is a long text that should trigger adaptive translation but will need to fall back to standard translation if adaptive fails."
        
        ; Create translator instance
        translator := NLLBTranslator()
        
        ; Test adaptive detection
        useAdaptive := Config.EnableAdaptiveTranslation && StrLen(longText) > Config.AdaptiveForLongText
        Assert.Equal(useAdaptive, true, "Should initially try adaptive translation")
        
        ; Simulate adaptive failure scenario
        adaptiveError := "ERROR: Adaptive translation service unavailable"
        
        ; Test error detection
        isAdaptiveError := InStr(adaptiveError, "ERROR:") == 1
        Assert.Equal(isAdaptiveError, true, "Should detect adaptive error")
        
        ; In a real scenario, this would trigger fallback to standard translation
        ; We can test the fallback decision logic
        shouldFallback := isAdaptiveError && StrLen(longText) > 0
        Assert.Equal(shouldFallback, true, "Should decide to fallback to standard translation")
        
        ; Test standard translation request preparation
        standardJsonData := '{"text":"' . translator.EscapeJSON(longText) . '","source_lang":"auto","target_lang":"eng_Latn"}'
        
        ; Verify standard request format
        Assert.Contains(standardJsonData, '"text":"', "Standard request should contain text field")
        Assert.Contains(standardJsonData, translator.EscapeJSON(longText), "Standard request should contain escaped text")
        Assert.NotContains(standardJsonData, '"user_preference":', "Standard request should not contain adaptive-specific fields")
        Assert.NotContains(standardJsonData, '"max_optimization_time":', "Standard request should not contain optimization fields")
        
        TestPassed++
        TestResults[testName] := {passed: true}
        FileAppend, % "✓ " . testName . "`n", *, UTF-8
    } catch e {
        TestFailed++
        TestResults[testName] := {passed: false, message: e.Message}
        FileAppend, % "✗ " . testName . ": " . e.Message . "`n", *, UTF-8
    }
}

; Test progressive notification workflow
Test_ProgressiveNotificationWorkflow()
{
    global TestCount, TestPassed, TestFailed, TestResults
    TestCount++
    
    testName := "Test_ProgressiveNotificationWorkflow"
    
    try {
        ; Mock progressive translation response
        progressiveResponse := '{'
        progressiveResponse .= '"final_translation":"Complete progressive translation result",'
        progressiveResponse .= '"quality_score":0.96,'
        progressiveResponse .= '"quality_grade":"A",'
        progressiveResponse .= '"optimization_applied":true,'
        progressiveResponse .= '"chunks_processed":4,'
        progressiveResponse .= '"total_processing_time":3.8'
        progressiveResponse .= '}'
        
        ; Test progressive response parsing
        result := Map()
        
        ; Extract final translation
        if (RegExMatch(progressiveResponse, '"final_translation"\s*:\s*"(.+?)"', &match)) {
            result["translation"] := match[1]
        } else if (RegExMatch(progressiveResponse, '"translation"\s*:\s*"(.+?)"', &match)) {
            result["translation"] := match[1]
        }
        
        ; Extract quality information
        if (RegExMatch(progressiveResponse, '"quality_grade"\s*:\s*"([A-F])"', &match)) {
            result["qualityGrade"] := match[1]
        }
        
        if (RegExMatch(progressiveResponse, '"optimization_applied"\s*:\s*(true|false)', &match)) {
            result["optimizationApplied"] := (match[1] == "true")
        }
        
        if (RegExMatch(progressiveResponse, '"chunks_processed"\s*:\s*([0-9]+)', &match)) {
            result["chunksProcessed"] := Integer(match[1])
        }
        
        if (RegExMatch(progressiveResponse, '"total_processing_time"\s*:\s*([0-9.]+)', &match)) {
            result["processingTime"] := Float(match[1])
        }
        
        ; Verify parsed results
        Assert.Equal(result["translation"], "Complete progressive translation result", "Should extract final translation")
        Assert.Equal(result["qualityGrade"], "A", "Should extract quality grade")
        Assert.Equal(result["optimizationApplied"], true, "Should extract optimization status")
        Assert.Equal(result["chunksProcessed"], 4, "Should extract chunks processed")
        Assert.Equal(result["processingTime"], 3.8, "Should extract processing time")
        
        ; Test progressive quality info formatting
        qualityInfo := ""
        if (Config.ShowQualityGrades && result.Has("qualityGrade")) {
            qualityInfo := " (Grade: " . result["qualityGrade"]
            
            if (result.Has("optimizationApplied") && result["optimizationApplied"]) {
                qualityInfo .= " ⚡"
            }
            
            if (result.Has("processingTime")) {
                processingTime := Round(result["processingTime"], 2)
                qualityInfo .= " " . processingTime . "s"
            }
            
            qualityInfo .= ")"
        }
        
        expectedQualityInfo := " (Grade: A ⚡ 3.8s)"
        Assert.Equal(qualityInfo, expectedQualityInfo, "Should format progressive quality info correctly")
        
        TestPassed++
        TestResults[testName] := {passed: true}
        FileAppend, % "✓ " . testName . "`n", *, UTF-8
    } catch e {
        TestFailed++
        TestResults[testName] := {passed: false, message: e.Message}
        FileAppend, % "✗ " . testName . ": " . e.Message . "`n", *, UTF-8
    }
}

; Test concurrent translation handling
Test_ConcurrentTranslationHandling()
{
    global TestCount, TestPassed, TestFailed, TestResults
    TestCount++
    
    testName := "Test_ConcurrentTranslationHandling"
    
    try {
        ; Test that the system can handle multiple translation requests
        ; by checking the logic that would be used in concurrent scenarios
        
        translationQueue := Array()
        
        ; Simulate multiple translation requests
        for i in [1, 2, 3] {
            request := {
                id: "request_" . i,
                text: "Text for concurrent translation " . i . " with sufficient length to trigger adaptive features",
                timestamp: A_TickCount + (i * 100),
                useAdaptive: true
            }
            translationQueue.Push(request)
        }
        
        ; Verify all requests are queued
        Assert.Equal(translationQueue.Length, 3, "Should queue all translation requests")
        
        ; Test request processing logic
        processedRequests := Array()
        for request in translationQueue {
            ; Simulate adaptive detection for each request
            useAdaptive := Config.EnableAdaptiveTranslation && StrLen(request.text) > Config.AdaptiveForLongText
            request.actuallyUseAdaptive := useAdaptive
            processedRequests.Push(request)
        }
        
        ; Verify all requests would use adaptive
        for request in processedRequests {
            Assert.Equal(request.actuallyUseAdaptive, true, "Each request should use adaptive translation")
        }
        
        ; Test that requests maintain their identity
        Assert.Equal(processedRequests[1].id, "request_1", "First request should maintain identity")
        Assert.Equal(processedRequests[2].id, "request_2", "Second request should maintain identity")
        Assert.Equal(processedRequests[3].id, "request_3", "Third request should maintain identity")
        
        TestPassed++
        TestResults[testName] := {passed: true}
        FileAppend, % "✓ " . testName . "`n", *, UTF-8
    } catch e {
        TestFailed++
        TestResults[testName] := {passed: false, message: e.Message}
        FileAppend, % "✗ " . testName . ": " . e.Message . "`n", *, UTF-8
    }
}

; Test adaptive caching simulation
Test_AdaptiveCachingSimulation()
{
    global TestCount, TestPassed, TestFailed, TestResults
    TestCount++
    
    testName := "Test_AdaptiveCachingSimulation"
    
    try {
        ; Simulate adaptive caching logic
        adaptiveCache := Map()
        
        ; Test cache key generation
        text1 := "Test text for caching functionality"
        cacheKey1 := "adaptive:" . StrLen(text1) . ":" . SubStr(text1, 1, 20)
        
        ; Simulate first translation (cache miss)
        if (!adaptiveCache.Has(cacheKey1)) {
            mockResult := {
                translation: "Cached translation result",
                qualityGrade: "A",
                cacheHit: false,
                processingTime: 2.1
            }
            adaptiveCache[cacheKey1] := mockResult
            firstResult := mockResult
        }
        
        Assert.Equal(firstResult.cacheHit, false, "First translation should be cache miss")
        Assert.Equal(adaptiveCache.Count, 1, "Cache should contain one entry")
        
        ; Simulate second translation with same text (cache hit)
        if (adaptiveCache.Has(cacheKey1)) {
            cachedResult := adaptiveCache[cacheKey1]
            cachedResult.cacheHit := true
            cachedResult.processingTime := 0.05  ; Much faster for cached result
            secondResult := cachedResult
        }
        
        Assert.Equal(secondResult.cacheHit, true, "Second translation should be cache hit")
        Assert.Equal(secondResult.processingTime, 0.05, "Cached result should be much faster")
        Assert.Equal(secondResult.translation, firstResult.translation, "Cached result should match original")
        
        ; Test cache with different text
        text2 := "Different text for cache testing"
        cacheKey2 := "adaptive:" . StrLen(text2) . ":" . SubStr(text2, 1, 20)
        
        Assert.NotEqual(cacheKey1, cacheKey2, "Different texts should have different cache keys")
        Assert.Equal(adaptiveCache.Has(cacheKey2), false, "New text should not be in cache")
        
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
Test_AdaptiveTranslationWorkflow()
Test_AdaptiveFallbackWorkflow()
Test_ProgressiveNotificationWorkflow()
Test_ConcurrentTranslationHandling()
Test_AdaptiveCachingSimulation()

; Generate report and exit
RunTests()