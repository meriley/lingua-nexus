; ===================================================
; NLLB Translator - AutoHotkey v2.0
; ===================================================

#SingleInstance Force
SendMode("Input")
SetWorkingDir(A_ScriptDir)

; Configuration class with bidirectional support and adaptive translation
class Config {
    static TranslationServer := "http://localhost:8001"
    static TranslationEndpoint := "/translate"
    static AdaptiveEndpoint := "/adaptive/translate"
    static ProgressiveEndpoint := "/adaptive/translate/progressive"
    static LanguagesEndpoint := "/languages"
    static APIKey := ""
    static SourceLang := "auto"
    static TargetLang := "eng_Latn"
    static LanguageSelectionMode := "single" ; "single" or "pair"
    static HotkeyTranslateSelection := "^!t"
    static HotkeyTranslateClipboard := "^+c"
    static HotkeyTranslateSourceToTarget := "^+1"
    static HotkeyTranslateTargetToSource := "^+2"
    static HotkeySelectLanguage := "^+l"
    static HotkeySelectLanguagePair := "^+p"
    static HotkeySwapLanguages := "^+s"
    static HotkeyQuickLanguage1 := "^!1"
    static HotkeyQuickLanguage2 := "^!2"
    static HotkeyQuickLanguage3 := "^!3"
    static HotkeyQuickLanguage4 := "^!4"
    static HotkeyQuickLanguage5 := "^!5"
    static ShowNotifications := true
    static TryDirectInput := true
    static UseFallbackClipboard := true
    static MaxRecentLanguages := 5
    static CacheLanguagesForMinutes := 60
    
    ; Adaptive translation settings
    static EnableAdaptiveTranslation := true
    static UserPreference := "balanced" ; "fast", "balanced", "quality"
    static EnableProgressiveUI := true
    static QualityThreshold := 0.8
    static AdaptiveForLongText := 500 ; Enable adaptive for text longer than 500 chars
    static MaxOptimizationTime := 5.0
    static ShowQualityGrades := true
    
    ; NLLB Supported Languages (most common ones)
    static Languages := Map(
        "Auto-Detect", "auto",
        "English", "eng_Latn",
        "Russian", "rus_Cyrl", 
        "Spanish", "spa_Latn",
        "French", "fra_Latn",
        "German", "deu_Latn",
        "Italian", "ita_Latn",
        "Portuguese", "por_Latn",
        "Chinese (Simplified)", "zho_Hans",
        "Chinese (Traditional)", "zho_Hant",
        "Japanese", "jpn_Jpan",
        "Korean", "kor_Hang",
        "Arabic", "arb_Arab",
        "Hindi", "hin_Deva",
        "Turkish", "tur_Latn",
        "Polish", "pol_Latn",
        "Dutch", "nld_Latn",
        "Swedish", "swe_Latn",
        "Norwegian", "nor_Latn",
        "Danish", "dan_Latn",
        "Finnish", "fin_Latn",
        "Czech", "ces_Latn",
        "Hungarian", "hun_Latn",
        "Romanian", "ron_Latn",
        "Greek", "ell_Grek",
        "Hebrew", "heb_Hebr",
        "Thai", "tha_Thai",
        "Vietnamese", "vie_Latn",
        "Indonesian", "ind_Latn",
        "Malay", "zsm_Latn",
        "Ukrainian", "ukr_Cyrl",
        "Bulgarian", "bul_Cyrl",
        "Croatian", "hrv_Latn",
        "Serbian", "srp_Cyrl",
        "Slovak", "slk_Latn",
        "Slovenian", "slv_Latn",
        "Lithuanian", "lit_Latn",
        "Latvian", "lav_Latn",
        "Estonian", "est_Latn"
    )
}
}

; Language Manager for API-based language loading
class LanguageManager {
    static Languages := Map()
    static LanguageMetadata := Map()
    static RecentLanguages := Array()
    static RecentLanguagePairs := Array()
    static LastApiCall := 0
    static CacheExpiry := 0
    
    static LoadLanguagesFromAPI() {
        ; Check if we need to refresh cache
        currentTime := A_TickCount
        if (this.LastApiCall > 0 && currentTime < this.CacheExpiry) {
            return true ; Use cached data
        }
        
        try {
            url := Config.TranslationServer . Config.LanguagesEndpoint
            headers := "X-API-Key: " . Config.APIKey . "`nContent-Type: application/json"
            
            ; Make HTTP request using ComObject
            http := ComObject("WinHttp.WinHttpRequest.5.1")
            http.Open("GET", url, false)
            http.SetRequestHeader("X-API-Key", Config.APIKey)
            http.SetRequestHeader("Content-Type", "application/json")
            http.Send()
            
            if (http.Status == 200) {
                responseText := http.ResponseText
                
                ; Parse JSON response
                languageData := this.ParseLanguageResponse(responseText)
                
                ; Update cache
                this.LastApiCall := currentTime
                this.CacheExpiry := currentTime + (Config.CacheLanguagesForMinutes * 60 * 1000)
                
                return true
            } else {
                this.ShowError("Failed to load languages from API: HTTP " . http.Status)
                return false
            }
        } catch error {
            this.ShowError("Error loading languages: " . error.Message)
            return false
        }
    }
    
    static ParseLanguageResponse(jsonText) {
        ; Simple JSON parsing for language data
        ; This is a basic implementation - in production, you'd want a proper JSON parser
        
        ; Clear existing languages
        this.Languages := Map()
        this.LanguageMetadata := Map()
        
        ; Add fallback languages
        this.AddLanguage("auto", "Auto-detect", "Auto-detect", "Auto", true)
        this.AddLanguage("eng_Latn", "English", "English", "Germanic", true)
        this.AddLanguage("rus_Cyrl", "Russian", "Русский", "Slavic", true)
        this.AddLanguage("spa_Latn", "Spanish", "Español", "Romance", true)
        this.AddLanguage("fra_Latn", "French", "Français", "Romance", true)
        this.AddLanguage("deu_Latn", "German", "Deutsch", "Germanic", true)
        
        ; TODO: Implement proper JSON parsing for full language list
        ; For now, using the fallback languages above
        
        return true
    }
    
    static AddLanguage(code, name, nativeName, family, popular := false) {
        this.Languages[name] := code
        this.LanguageMetadata[code] := {
            code: code,
            name: name,
            nativeName: nativeName,
            family: family,
            popular: popular
        }
    }
    
    static GetLanguageNames() {
        names := Array()
        for name, code in this.Languages {
            names.Push(name)
        }
        return names
    }
    
    static GetLanguageCode(name) {
        return this.Languages.Has(name) ? this.Languages[name] : ""
    }
    
    static GetLanguageName(code) {
        for name, langCode in this.Languages {
            if (langCode == code) {
                return name
            }
        }
        return code
    }
    
    static AddToRecentLanguages(code) {
        ; Remove if already exists
        for i, lang in this.RecentLanguages {
            if (lang == code) {
                this.RecentLanguages.RemoveAt(i)
                break
            }
        }
        
        ; Add to front
        this.RecentLanguages.InsertAt(1, code)
        
        ; Keep only max recent languages
        while (this.RecentLanguages.Length > Config.MaxRecentLanguages) {
            this.RecentLanguages.Pop()
        }
        
        this.SaveRecentLanguages()
    }
    
    static AddToRecentLanguagePairs(sourceCode, targetCode) {
        pairKey := sourceCode . "|" . targetCode
        
        ; Remove if already exists
        for i, pair in this.RecentLanguagePairs {
            if (pair == pairKey) {
                this.RecentLanguagePairs.RemoveAt(i)
                break
            }
        }
        
        ; Add to front
        this.RecentLanguagePairs.InsertAt(1, pairKey)
        
        ; Keep only max recent pairs
        while (this.RecentLanguagePairs.Length > Config.MaxRecentLanguages) {
            this.RecentLanguagePairs.Pop()
        }
        
        this.SaveRecentLanguagePairs()
    }
    
    static LoadRecentLanguages() {
        settingsFile := A_ScriptDir . "\settings.ini"
        recentStr := IniRead(settingsFile, "Recent", "Languages", "")
        
        this.RecentLanguages := Array()
        if (recentStr != "") {
            parts := StrSplit(recentStr, ",")
            for part in parts {
                if (Trim(part) != "") {
                    this.RecentLanguages.Push(Trim(part))
                }
            }
        }
    }
    
    static SaveRecentLanguages() {
        settingsFile := A_ScriptDir . "\settings.ini"
        recentStr := ""
        
        for i, lang in this.RecentLanguages {
            if (i > 1) {
                recentStr .= ","
            }
            recentStr .= lang
        }
        
        IniWrite(recentStr, settingsFile, "Recent", "Languages")
    }
    
    static LoadRecentLanguagePairs() {
        settingsFile := A_ScriptDir . "\settings.ini"
        recentStr := IniRead(settingsFile, "Recent", "LanguagePairs", "")
        
        this.RecentLanguagePairs := Array()
        if (recentStr != "") {
            parts := StrSplit(recentStr, ";")
            for part in parts {
                if (Trim(part) != "") {
                    this.RecentLanguagePairs.Push(Trim(part))
                }
            }
        }
    }
    
    static SaveRecentLanguagePairs() {
        settingsFile := A_ScriptDir . "\settings.ini"
        recentStr := ""
        
        for i, pair in this.RecentLanguagePairs {
            if (i > 1) {
                recentStr .= ";"
            }
            recentStr .= pair
        }
        
        IniWrite(recentStr, settingsFile, "Recent", "LanguagePairs")
    }
    
    static ShowError(message) {
        MsgBox(message, "Language Manager Error", 16)
    }
}

; Initialize application
class NLLBTranslator {
    __New() {
        this.LoadSettings()
        
        ; Initialize Language Manager
        LanguageManager.LoadRecentLanguages()
        LanguageManager.LoadRecentLanguagePairs()
        LanguageManager.LoadLanguagesFromAPI()
        
        this.SetupTrayMenu()
        this.SetupHotkeys()
        this.ShowNotification("NLLB Translator Ready", "Press " . Config.HotkeyTranslateSelection . " to translate, " . Config.HotkeySelectLanguage . " to change language")
    }
    
    LoadSettings() {
        settingsFile := A_ScriptDir . "\settings.ini"
        
        if (FileExist(settingsFile)) {
            Config.TranslationServer := IniRead(settingsFile, "Server", "TranslationServer", Config.TranslationServer)
            Config.APIKey := IniRead(settingsFile, "Server", "APIKey", Config.APIKey)
            Config.SourceLang := IniRead(settingsFile, "Translation", "SourceLang", Config.SourceLang)
            Config.TargetLang := IniRead(settingsFile, "Translation", "TargetLang", Config.TargetLang)
            Config.HotkeyTranslateSelection := IniRead(settingsFile, "Hotkeys", "TranslateSelection", Config.HotkeyTranslateSelection)
            Config.HotkeyTranslateClipboard := IniRead(settingsFile, "Hotkeys", "TranslateClipboard", Config.HotkeyTranslateClipboard)
            Config.HotkeyTranslateSourceToTarget := IniRead(settingsFile, "Hotkeys", "TranslateSourceToTarget", Config.HotkeyTranslateSourceToTarget)
            Config.HotkeyTranslateTargetToSource := IniRead(settingsFile, "Hotkeys", "TranslateTargetToSource", Config.HotkeyTranslateTargetToSource)
            Config.HotkeySelectLanguage := IniRead(settingsFile, "Hotkeys", "SelectLanguage", Config.HotkeySelectLanguage)
            Config.HotkeySwapLanguages := IniRead(settingsFile, "Hotkeys", "SwapLanguages", Config.HotkeySwapLanguages)
            Config.ShowNotifications := IniRead(settingsFile, "UI", "ShowNotifications", Config.ShowNotifications)
            Config.TryDirectInput := IniRead(settingsFile, "Advanced", "TryDirectInput", Config.TryDirectInput)
            Config.UseFallbackClipboard := IniRead(settingsFile, "Advanced", "UseFallbackClipboard", Config.UseFallbackClipboard)
        }
    }
    
    SaveSettings() {
        settingsFile := A_ScriptDir . "\settings.ini"
        
        IniWrite(Config.TranslationServer, settingsFile, "Server", "TranslationServer")
        IniWrite(Config.APIKey, settingsFile, "Server", "APIKey")
        IniWrite(Config.SourceLang, settingsFile, "Translation", "SourceLang")
        IniWrite(Config.TargetLang, settingsFile, "Translation", "TargetLang")
        IniWrite(Config.HotkeyTranslateSelection, settingsFile, "Hotkeys", "TranslateSelection")
        IniWrite(Config.HotkeyTranslateClipboard, settingsFile, "Hotkeys", "TranslateClipboard")
        IniWrite(Config.HotkeyTranslateSourceToTarget, settingsFile, "Hotkeys", "TranslateSourceToTarget")
        IniWrite(Config.HotkeyTranslateTargetToSource, settingsFile, "Hotkeys", "TranslateTargetToSource")
        IniWrite(Config.HotkeySelectLanguage, settingsFile, "Hotkeys", "SelectLanguage")
        IniWrite(Config.HotkeySwapLanguages, settingsFile, "Hotkeys", "SwapLanguages")
        IniWrite(Config.ShowNotifications, settingsFile, "UI", "ShowNotifications")
        IniWrite(Config.TryDirectInput, settingsFile, "Advanced", "TryDirectInput")
        IniWrite(Config.UseFallbackClipboard, settingsFile, "Advanced", "UseFallbackClipboard")
    }
    
    SetupTrayMenu() {
        A_TrayMenu.Delete()
        A_TrayMenu.Add("Translate Selection", (*) => this.TranslateSelection())
        A_TrayMenu.Add("Translate Clipboard", (*) => this.TranslateClipboard())
        A_TrayMenu.Add()
        A_TrayMenu.Add("Source → Target", (*) => this.TranslateSourceToTarget())
        A_TrayMenu.Add("Target → Source", (*) => this.TranslateTargetToSource())
        A_TrayMenu.Add()
        A_TrayMenu.Add("Select Languages", (*) => this.ShowLanguageSelector())
        A_TrayMenu.Add("Swap Languages", (*) => this.SwapLanguages())
        A_TrayMenu.Add()
        A_TrayMenu.Add("Settings", (*) => this.ShowSettings())
        A_TrayMenu.Add("About", (*) => this.ShowAbout())
        A_TrayMenu.Add()
        A_TrayMenu.Add("Exit", (*) => ExitApp())
        A_TrayMenu.Default := "Translate Selection"
    }
    
    SetupHotkeys() {
        Hotkey(Config.HotkeyTranslateSelection, (*) => this.TranslateSelection())
        Hotkey(Config.HotkeyTranslateClipboard, (*) => this.TranslateClipboard())
        Hotkey(Config.HotkeyTranslateSourceToTarget, (*) => this.TranslateSourceToTarget())
        Hotkey(Config.HotkeyTranslateTargetToSource, (*) => this.TranslateTargetToSource())
        Hotkey(Config.HotkeySelectLanguage, (*) => this.ShowLanguageSelector())
        Hotkey(Config.HotkeySelectLanguagePair, (*) => this.ShowLanguagePairSelector())
        Hotkey(Config.HotkeySwapLanguages, (*) => this.SwapLanguages())
        
        ; Quick language hotkeys
        Hotkey(Config.HotkeyQuickLanguage1, (*) => this.SetQuickTargetLanguage(1))
        Hotkey(Config.HotkeyQuickLanguage2, (*) => this.SetQuickTargetLanguage(2))
        Hotkey(Config.HotkeyQuickLanguage3, (*) => this.SetQuickTargetLanguage(3))
        Hotkey(Config.HotkeyQuickLanguage4, (*) => this.SetQuickTargetLanguage(4))
        Hotkey(Config.HotkeyQuickLanguage5, (*) => this.SetQuickTargetLanguage(5))
    }
    
    TranslateSelection() {
        previousClipboard := A_Clipboard
        A_Clipboard := ""
        Send("^c")
        
        if (!ClipWait(2)) {
            this.ShowNotification("Error", "No text selected")
            return
        }
        
        textToTranslate := A_Clipboard
        A_Clipboard := previousClipboard
        
        this.TranslateAndHandleText(textToTranslate, true)
    }
    
    TranslateClipboard() {
        if (!A_Clipboard) {
            this.ShowNotification("Error", "Clipboard is empty")
            return
        }
        
        this.TranslateAndHandleText(A_Clipboard, false)
    }
    
    TranslateSourceToTarget() {
        ; Get selected text or use clipboard
        previousClipboard := A_Clipboard
        A_Clipboard := ""
        Send("^c")
        
        if (!ClipWait(1)) {
            ; No selection, use clipboard
            A_Clipboard := previousClipboard
            if (!A_Clipboard) {
                this.ShowNotification("Error", "No text selected or in clipboard")
                return
            }
        }
        
        textToTranslate := A_Clipboard
        A_Clipboard := previousClipboard
        
        this.ShowNotification("Translating...", this.GetLanguageName(Config.SourceLang) . " → " . this.GetLanguageName(Config.TargetLang))
        
        translatedText := this.SendTranslationRequest(textToTranslate, Config.SourceLang, Config.TargetLang)
        
        if (InStr(translatedText, "ERROR:") == 1) {
            this.ShowNotification("Translation Error", SubStr(translatedText, 7))
            return
        }
        
        this.HandleTranslatedText(translatedText)
    }
    
    TranslateTargetToSource() {
        ; Only translate if source is not auto-detect
        if (Config.SourceLang == "auto") {
            this.ShowNotification("Error", "Cannot reverse translate with auto-detect source. Please set a specific source language.")
            return
        }
        
        ; Get selected text or use clipboard
        previousClipboard := A_Clipboard
        A_Clipboard := ""
        Send("^c")
        
        if (!ClipWait(1)) {
            ; No selection, use clipboard
            A_Clipboard := previousClipboard
            if (!A_Clipboard) {
                this.ShowNotification("Error", "No text selected or in clipboard")
                return
            }
        }
        
        textToTranslate := A_Clipboard
        A_Clipboard := previousClipboard
        
        this.ShowNotification("Translating...", this.GetLanguageName(Config.TargetLang) . " → " . this.GetLanguageName(Config.SourceLang))
        
        translatedText := this.SendTranslationRequest(textToTranslate, Config.TargetLang, Config.SourceLang)
        
        if (InStr(translatedText, "ERROR:") == 1) {
            this.ShowNotification("Translation Error", SubStr(translatedText, 7))
            return
        }
        
        this.HandleTranslatedText(translatedText)
    }
    
    SwapLanguages() {
        if (Config.SourceLang == "auto") {
            this.ShowNotification("Error", "Cannot swap with auto-detect source")
            return
        }
        
        ; Swap the languages
        tempLang := Config.SourceLang
        Config.SourceLang := Config.TargetLang
        Config.TargetLang := tempLang
        
        this.SaveSettings()
        this.ShowNotification("Languages Swapped", this.GetLanguageName(Config.SourceLang) . " ↔ " . this.GetLanguageName(Config.TargetLang))
    }
    
    HandleTranslatedText(translatedText) {
        if (Config.TryDirectInput) {
            this.PasteText(translatedText)
        } else if (Config.UseFallbackClipboard) {
            previousClipboard := A_Clipboard
            A_Clipboard := translatedText
            this.ShowNotification("Translation Complete", "Result copied to clipboard")
            
            ; Restore clipboard after delay
            SetTimer(() => A_Clipboard := previousClipboard, -10000)
        }
    }
    
    GetLanguageName(langCode) {
        for langName, code in Config.Languages {
            if (code == langCode) {
                return langName
            }
        }
        return langCode  ; Return code if name not found
    }
    
    TranslateAndHandleText(textToTranslate, replaceSelection := false) {
        ; Determine translation approach based on text length and settings
        useAdaptive := Config.EnableAdaptiveTranslation && StrLen(textToTranslate) > Config.AdaptiveForLongText
        useProgressive := useAdaptive && Config.EnableProgressiveUI && StrLen(textToTranslate) > 1000
        
        if (useProgressive) {
            this.ShowNotification("Progressive Translation", "Starting optimized chunked translation...")
            result := this.SendProgressiveTranslationRequest(textToTranslate, Config.SourceLang, Config.TargetLang)
        } else if (useAdaptive) {
            this.ShowNotification("Optimizing Translation...", "Using quality enhancement for long text")
            result := this.SendAdaptiveTranslationRequest(textToTranslate, Config.SourceLang, Config.TargetLang)
        } else {
            this.ShowNotification("Translating...", "Please wait")
            result := this.SendTranslationRequest(textToTranslate, Config.SourceLang, Config.TargetLang)
        }
        
        ; Handle adaptive/progressive response or standard string response
        if (IsObject(result)) {
            translatedText := result["translation"]
            qualityInfo := ""
            
            ; Build enhanced quality information display
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
        } else {
            translatedText := result
            qualityInfo := ""
        }
        
        if (InStr(translatedText, "ERROR:") == 1) {
            this.ShowNotification("Translation Error", SubStr(translatedText, 7))
            return
        }
        
        if (replaceSelection && Config.TryDirectInput) {
            this.PasteText(translatedText)
            if (qualityInfo) {
                this.ShowNotification("Translation Complete" . qualityInfo, "Text has been replaced")
            }
        } else if (Config.UseFallbackClipboard) {
            previousClipboard := A_Clipboard
            A_Clipboard := translatedText
            this.ShowNotification("Translation Complete" . qualityInfo, "Result copied to clipboard")
            
            ; Restore clipboard after delay
            SetTimer(() => A_Clipboard := previousClipboard, -10000)
        }
    }
    
    SendTranslationRequest(text, sourceLang, targetLang, serverUrl := "", apiKey := "") {
        ; Use config values if not provided
        useServer := serverUrl != "" ? serverUrl : Config.TranslationServer
        useKey := apiKey != "" ? apiKey : Config.APIKey
        
        jsonData := '{"text":"' . this.EscapeJSON(text) . '","source_lang":"' . sourceLang . '","target_lang":"' . targetLang . '"}'
        
        try {
            http := ComObject("WinHttp.WinHttpRequest.5.1")
            http.Open("POST", useServer . Config.TranslationEndpoint, false)
            http.SetRequestHeader("Content-Type", "application/json")
            
            if (useKey != "") {
                http.SetRequestHeader("X-API-Key", useKey)
            }
            
            http.Send(jsonData)
            
            if (http.Status == 200) {
                responseText := http.ResponseText
                if (RegExMatch(responseText, '"translated_text"\s*:\s*"(.+?)"', &match)) {
                    return this.UnescapeJSON(match[1])
                } else {
                    return "ERROR: Couldn't parse response"
                }
            } else {
                return "ERROR: Server returned status " . http.Status
            }
        } catch Error as e {
            return "ERROR: " . e.Message
        }
    }
    
    SendAdaptiveTranslationRequest(text, sourceLang, targetLang, serverUrl := "", apiKey := "") {
        ; Use config values if not provided
        useServer := serverUrl != "" ? serverUrl : Config.TranslationServer
        useKey := apiKey != "" ? apiKey : Config.APIKey
        
        jsonData := '{'
        jsonData .= '"text":"' . this.EscapeJSON(text) . '",'
        jsonData .= '"source_lang":"' . sourceLang . '",'
        jsonData .= '"target_lang":"' . targetLang . '",'
        jsonData .= '"api_key":"' . useKey . '",'
        jsonData .= '"user_preference":"' . Config.UserPreference . '",'
        jsonData .= '"force_optimization":false,'
        jsonData .= '"max_optimization_time":' . Config.MaxOptimizationTime
        jsonData .= '}'
        
        try {
            http := ComObject("WinHttp.WinHttpRequest.5.1")
            http.Open("POST", useServer . Config.AdaptiveEndpoint, false)
            http.SetRequestHeader("Content-Type", "application/json")
            
            if (useKey != "") {
                http.SetRequestHeader("X-API-Key", useKey)
            }
            
            http.Send(jsonData)
            
            if (http.Status == 200) {
                responseText := http.ResponseText
                
                ; Parse adaptive response with quality metrics
                result := Map()
                
                ; Extract translation
                if (RegExMatch(responseText, '"translation"\s*:\s*"(.+?)"', &match)) {
                    result["translation"] := this.UnescapeJSON(match[1])
                } else {
                    return "ERROR: Couldn't parse adaptive response"
                }
                
                ; Extract quality information
                if (RegExMatch(responseText, '"quality_score"\s*:\s*([0-9.]+)', &match)) {
                    result["qualityScore"] := Float(match[1])
                }
                
                if (RegExMatch(responseText, '"quality_grade"\s*:\s*"([A-F])"', &match)) {
                    result["qualityGrade"] := match[1]
                }
                
                if (RegExMatch(responseText, '"optimization_applied"\s*:\s*(true|false)', &match)) {
                    result["optimizationApplied"] := (match[1] == "true")
                }
                
                if (RegExMatch(responseText, '"cache_hit"\s*:\s*(true|false)', &match)) {
                    result["cacheHit"] := (match[1] == "true")
                }
                
                if (RegExMatch(responseText, '"processing_time"\s*:\s*([0-9.]+)', &match)) {
                    result["processingTime"] := Float(match[1])
                }
                
                return result
            } else {
                return "ERROR: Adaptive server returned status " . http.Status
            }
        } catch Error as e {
            return "ERROR: " . e.Message
        }
    }
    
    SendProgressiveTranslationRequest(text, sourceLang, targetLang, serverUrl := "", apiKey := "") {
        ; Use config values if not provided
        useServer := serverUrl != "" ? serverUrl : Config.TranslationServer
        useKey := apiKey != "" ? apiKey : Config.APIKey
        
        if (!Config.EnableProgressiveUI) {
            ; Fall back to adaptive translation
            return this.SendAdaptiveTranslationRequest(text, sourceLang, targetLang, serverUrl, apiKey)
        }
        
        jsonData := '{'
        jsonData .= '"text":"' . this.EscapeJSON(text) . '",'
        jsonData .= '"source_lang":"' . sourceLang . '",'
        jsonData .= '"target_lang":"' . targetLang . '",'
        jsonData .= '"api_key":"' . useKey . '",'
        jsonData .= '"user_preference":"' . Config.UserPreference . '",'
        jsonData .= '"enable_progress_updates":true'
        jsonData .= '}'
        
        try {
            ; Start progressive notification
            this.ShowNotification("Progressive Translation", "Starting optimized translation...")
            
            http := ComObject("WinHttp.WinHttpRequest.5.1")
            http.Open("POST", useServer . Config.ProgressiveEndpoint, false)
            http.SetRequestHeader("Content-Type", "application/json")
            
            if (useKey != "") {
                http.SetRequestHeader("X-API-Key", useKey)
            }
            
            ; Update notification for processing
            this.ShowNotification("Progressive Translation", "Processing chunks...")
            
            http.Send(jsonData)
            
            if (http.Status == 200) {
                ; Update notification for completion
                this.ShowNotification("Progressive Translation", "Finalizing translation...")
                
                responseText := http.ResponseText
                
                ; Parse response similar to adaptive request
                result := Map()
                
                ; Extract final translation
                if (RegExMatch(responseText, '"final_translation"\s*:\s*"(.+?)"', &match)) {
                    result["translation"] := this.UnescapeJSON(match[1])
                } else if (RegExMatch(responseText, '"translation"\s*:\s*"(.+?)"', &match)) {
                    result["translation"] := this.UnescapeJSON(match[1])
                } else {
                    return "ERROR: Couldn't parse progressive response"
                }
                
                ; Extract quality information
                if (RegExMatch(responseText, '"quality_score"\s*:\s*([0-9.]+)', &match)) {
                    result["qualityScore"] := Float(match[1])
                }
                
                if (RegExMatch(responseText, '"quality_grade"\s*:\s*"([A-F])"', &match)) {
                    result["qualityGrade"] := match[1]
                }
                
                if (RegExMatch(responseText, '"optimization_applied"\s*:\s*(true|false)', &match)) {
                    result["optimizationApplied"] := (match[1] == "true")
                }
                
                if (RegExMatch(responseText, '"cache_hit"\s*:\s*(true|false)', &match)) {
                    result["cacheHit"] := (match[1] == "true")
                }
                
                if (RegExMatch(responseText, '"processing_time"\s*:\s*([0-9.]+)', &match)) {
                    result["processingTime"] := Float(match[1])
                }
                
                return result
            } else {
                return "ERROR: Progressive server returned status " . http.Status
            }
        } catch Error as e {
            return "ERROR: " . e.Message
        }
    }
    
    PasteText(text) {
        previousClipboard := A_Clipboard
        A_Clipboard := text
        ClipWait(2)
        Send("^v")
        this.ShowNotification("Translation Complete", "Text has been replaced")
        
        Sleep(100)
        A_Clipboard := previousClipboard
    }
    
    ShowLanguageSelector() {
        ; Load languages from API if possible
        LanguageManager.LoadLanguagesFromAPI()
        
        langGui := Gui("+AlwaysOnTop +ToolWindow", "Language Selection")
        langGui.MarginX := 15
        langGui.MarginY := 15
        
        ; Current language pair display
        sourceName := LanguageManager.GetLanguageName(Config.SourceLang)
        targetName := LanguageManager.GetLanguageName(Config.TargetLang)
        
        langGui.Add("Text", "Center w500 +Bold", "Current Language Pair")
        langGui.Add("Text", "Center w500", sourceName . " → " . targetName)
        langGui.Add("Text", "w500 h1 +0x10")  ; Separator line
        
        ; Recent language pairs section
        if (LanguageManager.RecentLanguagePairs.Length > 0) {
            langGui.Add("Text", "w500 +Bold", "Recent Language Pairs")
            
            recentPairsText := ""
            for i, pairKey in LanguageManager.RecentLanguagePairs {
                if (i > 5) break  ; Show max 5
                
                parts := StrSplit(pairKey, "|")
                if (parts.Length == 2) {
                    sourceName := LanguageManager.GetLanguageName(parts[1])
                    targetName := LanguageManager.GetLanguageName(parts[2])
                    
                    recentBtn := langGui.Add("Button", "w100 h25", sourceName . " → " . targetName)
                    recentBtn.pairKey := pairKey
                    recentBtn.OnEvent("Click", (*) => this.ApplyRecentLanguagePair(langGui, recentBtn.pairKey))
                    
                    if (Mod(i, 5) != 0) {
                        recentBtn.Opt("x+5")
                    }
                }
            }
            
            langGui.Add("Text", "w500 h1 +0x10")  ; Separator line
        }
        
        ; Source language selection
        langGui.Add("Text", "w220", "Source Language:")
        sourceList := LanguageManager.GetLanguageNames()
        
        sourceListBox := langGui.Add("ListBox", "x15 y+5 w220 h180", sourceList)
        sourceListBox.Choose(sourceName)
        
        ; Target language selection  
        langGui.Add("Text", "x250 ym+150 w220", "Target Language:")
        targetList := []
        for name in LanguageManager.GetLanguageNames() {
            code := LanguageManager.GetLanguageCode(name)
            if (code != "auto") {  ; Don't allow auto-detect as target
                targetList.Push(name)
            }
        }
        
        targetListBox := langGui.Add("ListBox", "x250 y+5 w220 h180", targetList)
        targetListBox.Choose(targetName)
        
        ; Quick access buttons for popular languages
        langGui.Add("Text", "x15 y+15 w460 +Bold", "Quick Access")
        
        popularLanguages := ["English", "Spanish", "French", "German", "Russian", "Chinese (Simplified)"]
        for i, langName in popularLanguages {
            if (LanguageManager.Languages.Has(langName)) {
                quickBtn := langGui.Add("Button", "w70 h25", langName)
                quickBtn.langName := langName
                quickBtn.OnEvent("Click", (*) => this.SetQuickLanguage(langGui, sourceListBox, targetListBox, quickBtn.langName))
                
                if (Mod(i, 6) != 0) {
                    quickBtn.Opt("x+5")
                }
            }
        }
        
        ; Action buttons
        langGui.Add("Text", "x15 y+15 w460 h1 +0x10")  ; Separator line
        
        swapBtn := langGui.Add("Button", "x15 y+10 w100", "Swap ⇄")
        selectBtn := langGui.Add("Button", "x+10 w100", "Apply")
        cancelBtn := langGui.Add("Button", "x+10 w100", "Cancel")
        refreshBtn := langGui.Add("Button", "x+10 w100", "Refresh API")
        
        swapBtn.OnEvent("Click", (*) => this.SwapLanguagesInDialog(sourceListBox, targetListBox))
        selectBtn.OnEvent("Click", (*) => this.ApplyLanguageSelection(langGui, sourceListBox, targetListBox))
        cancelBtn.OnEvent("Click", (*) => langGui.Destroy())
        refreshBtn.OnEvent("Click", (*) => this.RefreshLanguagesFromAPI(langGui))
        
        langGui.Show("AutoSize")
        sourceListBox.Focus()
    }
    
    ApplyRecentLanguagePair(gui, pairKey) {
        parts := StrSplit(pairKey, "|")
        if (parts.Length == 2) {
            Config.SourceLang := parts[1]
            Config.TargetLang := parts[2]
            this.SaveSettings()
            
            ; Update recent pairs
            LanguageManager.AddToRecentLanguagePairs(Config.SourceLang, Config.TargetLang)
            
            sourceName := LanguageManager.GetLanguageName(Config.SourceLang)
            targetName := LanguageManager.GetLanguageName(Config.TargetLang)
            
            this.ShowNotification("Language Pair Updated", sourceName . " → " . targetName)
            gui.Destroy()
        }
    }
    
    SetQuickLanguage(gui, sourceListBox, targetListBox, langName) {
        ; Set as target language
        targetListBox.Choose(langName)
        
        ; Show tooltip
        ToolTip("Set " . langName . " as target language")
        SetTimer(() => ToolTip(), -1000)
    }
    
    RefreshLanguagesFromAPI(gui) {
        ; Force refresh from API
        LanguageManager.LastApiCall := 0
        
        if (LanguageManager.LoadLanguagesFromAPI()) {
            this.ShowNotification("Languages Updated", "Language list refreshed from API")
            gui.Destroy()
            this.ShowLanguageSelector()  ; Reopen with updated data
        } else {
            this.ShowNotification("Refresh Failed", "Could not load languages from API")
        }
    }
    
    ShowLanguagePairSelector() {
        ; Alternative view focused on language pairs
        this.ShowLanguageSelector()
    }
    
    SetQuickTargetLanguage(index) {
        ; Set target language from recent languages or popular languages
        popularLanguages := ["eng_Latn", "spa_Latn", "fra_Latn", "deu_Latn", "rus_Cyrl"]
        
        if (index <= LanguageManager.RecentLanguages.Length) {
            ; Use recent language
            Config.TargetLang := LanguageManager.RecentLanguages[index]
        } else if (index <= popularLanguages.Length) {
            ; Use popular language
            Config.TargetLang := popularLanguages[index]
        } else {
            return
        }
        
        this.SaveSettings()
        LanguageManager.AddToRecentLanguages(Config.TargetLang)
        
        langName := LanguageManager.GetLanguageName(Config.TargetLang)
        this.ShowNotification("Target Language", "Set to " . langName)
        
        ; Show current language pair with tooltip
        sourceName := LanguageManager.GetLanguageName(Config.SourceLang)
        targetName := LanguageManager.GetLanguageName(Config.TargetLang)
        ToolTip(sourceName . " → " . targetName)
        SetTimer(() => ToolTip(), -2000)
    }
    
    SwapLanguagesInDialog(sourceListBox, targetListBox) {
        if (sourceListBox.Text == "Auto-Detect") {
            this.ShowNotification("Error", "Cannot swap with auto-detect")
            return
        }
        
        ; Get current selections
        sourceSelection := sourceListBox.Text
        targetSelection := targetListBox.Text
        
        ; Swap them
        sourceListBox.Choose(targetSelection)
        targetListBox.Choose(sourceSelection)
    }
    
    ApplyLanguageSelection(gui, sourceListBox, targetListBox) {
        if (sourceListBox.Value == 0 || targetListBox.Value == 0) {
            this.ShowNotification("Error", "Please select both languages")
            return
        }
        
        sourceLangName := sourceListBox.Text
        targetLangName := targetListBox.Text
        
        if (sourceLangName == targetLangName) {
            this.ShowNotification("Error", "Source and target languages cannot be the same")
            return
        }
        
        Config.SourceLang := Config.Languages[sourceLangName]
        Config.TargetLang := Config.Languages[targetLangName]
        
        this.SaveSettings()
        this.ShowNotification("Language Pair Set", sourceLangName . " → " . targetLangName)
        gui.Destroy()
    }
    
    ShowSettings() {
        settingsGui := Gui("+AlwaysOnTop", "NLLB Translator Settings")
        settingsGui.MarginX := 15
        settingsGui.MarginY := 15
        
        ; Server Configuration Section
        settingsGui.Add("Text", "w300 +Bold", "Server Configuration")
        settingsGui.Add("Text", "w300 h1 +0x10")  ; Separator line
        
        settingsGui.Add("Text", , "Server URL:")
        serverEdit := settingsGui.Add("Edit", "w300", Config.TranslationServer)
        
        settingsGui.Add("Text", , "API Key (optional):")
        apiEdit := settingsGui.Add("Edit", "w300 Password", Config.APIKey)
        
        ; Language Configuration Section
        settingsGui.Add("Text", "w300 +Bold Section", "Language Configuration")
        settingsGui.Add("Text", "w300 h1 +0x10")
        
        ; Get current language names
        sourceLangName := this.GetLanguageName(Config.SourceLang)
        targetLangName := this.GetLanguageName(Config.TargetLang)
        
        settingsGui.Add("Text", , "Current Language Pair:")
        currentPairText := settingsGui.Add("Text", "w300 +Background", sourceLangName . " → " . targetLangName)
        
        changeLangBtn := settingsGui.Add("Button", "w120", "Configure Languages")
        swapLangBtn := settingsGui.Add("Button", "x+10 w120", "Swap Languages")
        
        changeLangBtn.OnEvent("Click", (*) => this.ShowLanguageSelector())
        swapLangBtn.OnEvent("Click", (*) => this.SwapLanguages())
        
        ; Hotkey Configuration Section
        settingsGui.Add("Text", "w300 +Bold Section", "Hotkey Configuration")
        settingsGui.Add("Text", "w300 h1 +0x10")
        
        settingsGui.Add("Text", , "General Translation:")
        selectionHK := settingsGui.Add("Hotkey", "w300", Config.HotkeyTranslateSelection)
        settingsGui.Add("Text", "x320 y-25 w100", "Selection")
        
        clipboardHK := settingsGui.Add("Hotkey", "w300", Config.HotkeyTranslateClipboard)
        settingsGui.Add("Text", "x320 y-25 w100", "Clipboard")
        
        settingsGui.Add("Text", "xm", "Directional Translation:")
        sourceToTargetHK := settingsGui.Add("Hotkey", "w300", Config.HotkeyTranslateSourceToTarget)
        settingsGui.Add("Text", "x320 y-25 w100", "Source → Target")
        
        targetToSourceHK := settingsGui.Add("Hotkey", "w300", Config.HotkeyTranslateTargetToSource)
        settingsGui.Add("Text", "x320 y-25 w100", "Target → Source")
        
        settingsGui.Add("Text", "xm", "Language Management:")
        languageHK := settingsGui.Add("Hotkey", "w300", Config.HotkeySelectLanguage)
        settingsGui.Add("Text", "x320 y-25 w100", "Select Languages")
        
        swapHK := settingsGui.Add("Hotkey", "w300", Config.HotkeySwapLanguages)
        settingsGui.Add("Text", "x320 y-25 w100", "Swap Languages")
        
        ; Behavior Configuration Section
        settingsGui.Add("Text", "w300 +Bold Section", "Behavior Options")
        settingsGui.Add("Text", "w300 h1 +0x10")
        
        notifCB := settingsGui.Add("Checkbox", Config.ShowNotifications ? "Checked" : "", "Show notifications")
        directCB := settingsGui.Add("Checkbox", Config.TryDirectInput ? "Checked" : "", "Try direct text replacement")
        fallbackCB := settingsGui.Add("Checkbox", Config.UseFallbackClipboard ? "Checked" : "", "Use clipboard as fallback")
        
        ; Buttons
        saveBtn := settingsGui.Add("Button", "Default w80 Section", "Save")
        cancelBtn := settingsGui.Add("Button", "x+10 w80", "Cancel")
        testBtn := settingsGui.Add("Button", "x+10 w80", "Test Connection")
        
        saveBtn.OnEvent("Click", (*) => this.SaveSettingsHandler(settingsGui, serverEdit, apiEdit, selectionHK, clipboardHK, sourceToTargetHK, targetToSourceHK, languageHK, swapHK, notifCB, directCB, fallbackCB))
        cancelBtn.OnEvent("Click", (*) => settingsGui.Destroy())
        testBtn.OnEvent("Click", (*) => this.TestConnection(serverEdit.Text, apiEdit.Text))
        
        settingsGui.Show("AutoSize")
    }
    
    SaveSettingsHandler(gui, serverEdit, apiEdit, selectionHK, clipboardHK, sourceToTargetHK, targetToSourceHK, languageHK, swapHK, notifCB, directCB, fallbackCB) {
        ; Update hotkeys if changed
        newSelectionHK := selectionHK.Text
        newClipboardHK := clipboardHK.Text
        newSourceToTargetHK := sourceToTargetHK.Text
        newTargetToSourceHK := targetToSourceHK.Text
        newLanguageHK := languageHK.Text
        newSwapHK := swapHK.Text
        
        if (newSelectionHK != Config.HotkeyTranslateSelection && newSelectionHK != "") {
            Hotkey(Config.HotkeyTranslateSelection, "Off")
            Config.HotkeyTranslateSelection := newSelectionHK
            Hotkey(Config.HotkeyTranslateSelection, (*) => this.TranslateSelection())
        }
        
        if (newClipboardHK != Config.HotkeyTranslateClipboard && newClipboardHK != "") {
            Hotkey(Config.HotkeyTranslateClipboard, "Off")
            Config.HotkeyTranslateClipboard := newClipboardHK
            Hotkey(Config.HotkeyTranslateClipboard, (*) => this.TranslateClipboard())
        }
        
        if (newSourceToTargetHK != Config.HotkeyTranslateSourceToTarget && newSourceToTargetHK != "") {
            Hotkey(Config.HotkeyTranslateSourceToTarget, "Off")
            Config.HotkeyTranslateSourceToTarget := newSourceToTargetHK
            Hotkey(Config.HotkeyTranslateSourceToTarget, (*) => this.TranslateSourceToTarget())
        }
        
        if (newTargetToSourceHK != Config.HotkeyTranslateTargetToSource && newTargetToSourceHK != "") {
            Hotkey(Config.HotkeyTranslateTargetToSource, "Off")
            Config.HotkeyTranslateTargetToSource := newTargetToSourceHK
            Hotkey(Config.HotkeyTranslateTargetToSource, (*) => this.TranslateTargetToSource())
        }
        
        if (newLanguageHK != Config.HotkeySelectLanguage && newLanguageHK != "") {
            Hotkey(Config.HotkeySelectLanguage, "Off")
            Config.HotkeySelectLanguage := newLanguageHK
            Hotkey(Config.HotkeySelectLanguage, (*) => this.ShowLanguageSelector())
        }
        
        if (newSwapHK != Config.HotkeySwapLanguages && newSwapHK != "") {
            Hotkey(Config.HotkeySwapLanguages, "Off")
            Config.HotkeySwapLanguages := newSwapHK
            Hotkey(Config.HotkeySwapLanguages, (*) => this.SwapLanguages())
        }
        
        ; Update other settings
        Config.TranslationServer := serverEdit.Text
        Config.APIKey := apiEdit.Text
        Config.ShowNotifications := notifCB.Value
        Config.TryDirectInput := directCB.Value
        Config.UseFallbackClipboard := fallbackCB.Value
        
        this.SaveSettings()
        this.ShowNotification("Settings Saved", "Your settings have been updated")
        gui.Destroy()
    }
    
    TestConnection(serverUrl := "", apiKey := "") {
        ; Use current config if no parameters provided
        testServer := serverUrl != "" ? serverUrl : Config.TranslationServer
        testKey := apiKey != "" ? apiKey : Config.APIKey
        
        this.ShowNotification("Testing Connection...", "Please wait")
        
        testResult := this.SendTranslationRequest("Hello", "auto", "eng_Latn", testServer, testKey)
        
        if (InStr(testResult, "ERROR:") == 1) {
            this.ShowNotification("Connection Failed", SubStr(testResult, 7))
        } else {
            this.ShowNotification("Connection Successful", "Server is responding properly")
        }
    }
    
    ShowAbout() {
        MsgBox("NLLB Translator v2.0`n`nA system-wide translation tool for AutoHotkey v2.0`n`nHotkeys:`n• " . Config.HotkeyTranslateSelection . " - Translate selected text`n• " . Config.HotkeyTranslateClipboard . " - Translate clipboard content`n• " . Config.HotkeySelectLanguage . " - Select target language`n`nSupports " . Config.Languages.Count . " languages via NLLB!", "About NLLB Translator", "64")
    }
    
    ShowNotification(title, message) {
        if (Config.ShowNotifications) {
            TrayTip(message, title, "Iconi Mute")
            SetTimer(() => TrayTip(), -3000)
        }
    }
    
    EscapeJSON(str) {
        str := StrReplace(str, "\", "\\")
        str := StrReplace(str, '"', '\"')
        str := StrReplace(str, "`r", "\r")
        str := StrReplace(str, "`n", "\n")
        str := StrReplace(str, "`t", "\t")
        return str
    }
    
    UnescapeJSON(str) {
        str := StrReplace(str, '\"', '"')
        str := StrReplace(str, "\\", "\")
        str := StrReplace(str, "\r", "`r")
        str := StrReplace(str, "\n", "`n")
        str := StrReplace(str, "\t", "`t")
        return str
    }
}

; Initialize the application
translator := NLLBTranslator()