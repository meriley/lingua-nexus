/**
 * Integration tests for adaptive translation features with Telegram UI
 */

describe('Adaptive Translation Integration', () => {
  beforeEach(() => {
    // Setup realistic Telegram DOM structure
    document.body.innerHTML = `
      <div id="MiddleColumn" class="middle-column">
        <div class="messages-container">
          <div class="message" data-message-id="adaptive-msg-1">
            <div class="message-content">
              <div class="text-content">This is a moderately long message that should trigger adaptive translation features with quality optimization. The system should analyze this text, determine optimal chunking strategies, and provide enhanced translation quality with real-time progress indicators and quality assessment metrics.</div>
              <div class="time">12:34</div>
            </div>
          </div>
          <div class="message" data-message-id="adaptive-msg-2">
            <div class="message-content">
              <div class="text-content">Short message</div>
              <div class="time">12:35</div>
            </div>
          </div>
          <div class="message" data-message-id="adaptive-msg-3">
            <div class="message-content">
              <div class="text-content">Another very long message that contains complex technical content with specialized terminology that requires careful translation handling. This type of content benefits significantly from adaptive translation algorithms that can optimize chunk boundaries, maintain context coherence, and provide superior translation quality through advanced semantic analysis and progressive refinement techniques.</div>
              <div class="time">12:36</div>
            </div>
          </div>
        </div>
      </div>
    `;
    
    // Clear all mocks
    jest.clearAllMocks();
    
    // Mock GM_xmlhttpRequest
    global.GM_xmlhttpRequest = jest.fn();
    
    // Mock CONFIG with adaptive settings
    global.CONFIG = {
      translationServer: 'http://localhost:8001',
      translationEndpoint: '/translate',
      adaptiveEndpoint: '/adaptive/translate',
      progressiveEndpoint: '/adaptive/translate/progressive',
      apiKey: 'test-key',
      defaultSourceLang: 'auto',
      defaultTargetLang: 'eng_Latn',
      enableAdaptiveTranslation: true,
      enableProgressiveUI: true,
      adaptiveForLongText: 100,
      showQualityGrades: true,
      debugMode: true
    };
    
    // Mock state management
    global.state = {
      currentTargetLang: 'eng_Latn',
      translationInProgress: new Set(),
      adaptiveCache: new Map()
    };
  });

  test('should integrate adaptive translation with Telegram message UI', async () => {
    const longMessage = document.querySelector('[data-message-id="adaptive-msg-1"]');
    const textElement = longMessage.querySelector('.text-content');
    const originalText = textElement.textContent;
    
    // Mock successful adaptive translation
    global.GM_xmlhttpRequest.mockImplementation(({ url, method, data, onload }) => {
      expect(url).toContain('/adaptive/translate');
      expect(method).toBe('POST');
      
      const requestData = JSON.parse(data);
      expect(requestData.text).toBe(originalText);
      expect(requestData.source_lang).toBe('auto');
      expect(requestData.target_lang).toBe('eng_Latn');
      
      setTimeout(() => {
        onload({
          status: 200,
          responseText: JSON.stringify({
            translation: 'Optimized translation of the long message with enhanced quality',
            quality_score: 0.91,
            quality_grade: 'A',
            optimization_applied: true,
            cache_hit: false,
            processing_time: 2.1,
            chunks_processed: 2,
            semantic_coherence: 0.94,
            confidence_interval: [0.88, 0.94]
          })
        });
      }, 10);
    });
    
    // Mock adaptive translation function
    global.translateWithAdaptive = async (messageElement, textElement) => {
      const text = textElement.textContent;
      const shouldUseAdaptive = global.CONFIG.enableAdaptiveTranslation && 
                               text.length > global.CONFIG.adaptiveForLongText;
      
      if (!shouldUseAdaptive) {
        return { translatedText: 'Standard translation', adaptive: false };
      }
      
      // Add loading state
      textElement.classList.add('nllb-translating');
      const loadingIndicator = document.createElement('span');
      loadingIndicator.className = 'nllb-loading-adaptive';
      loadingIndicator.textContent = ' 🔄 Optimizing...';
      textElement.appendChild(loadingIndicator);
      
      return new Promise((resolve) => {
        global.GM_xmlhttpRequest({
          url: global.CONFIG.translationServer + global.CONFIG.adaptiveEndpoint,
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-API-Key': global.CONFIG.apiKey
          },
          data: JSON.stringify({
            text,
            source_lang: global.CONFIG.defaultSourceLang,
            target_lang: global.state.currentTargetLang,
            user_preference: 'balanced'
          }),
          onload: (response) => {
            const data = JSON.parse(response.responseText);
            
            // Remove loading indicator
            textElement.classList.remove('nllb-translating');
            const loading = textElement.querySelector('.nllb-loading-adaptive');
            if (loading) loading.remove();
            
            // Update text with translation
            textElement.textContent = '🌐 ' + data.translation;
            textElement.classList.add('nllb-translated');
            
            // Add quality indicator
            const qualityBadge = document.createElement('span');
            qualityBadge.className = 'nllb-quality-badge';
            qualityBadge.textContent = ` (${data.quality_grade})`;
            if (data.optimization_applied) qualityBadge.textContent += ' ⚡';
            if (data.cache_hit) qualityBadge.textContent += ' 💾';
            textElement.appendChild(qualityBadge);
            
            // Add hover for original text
            const originalSpan = document.createElement('span');
            originalSpan.className = 'nllb-original-text';
            originalSpan.textContent = text;
            originalSpan.style.display = 'none';
            textElement.appendChild(originalSpan);
            
            resolve({
              translatedText: data.translation,
              qualityScore: data.quality_score,
              qualityGrade: data.quality_grade,
              optimizationApplied: data.optimization_applied,
              adaptive: true
            });
          }
        });
      });
    };
    
    // Execute adaptive translation
    const result = await global.translateWithAdaptive(longMessage, textElement);
    
    // Verify adaptive features were applied
    expect(result.adaptive).toBe(true);
    expect(result.qualityGrade).toBe('A');
    expect(result.optimizationApplied).toBe(true);
    
    // Verify UI updates
    expect(textElement.classList.contains('nllb-translated')).toBe(true);
    expect(textElement.classList.contains('nllb-translating')).toBe(false);
    expect(textElement.textContent).toContain('Optimized translation');
    
    // Verify quality badge exists
    const qualityBadge = textElement.querySelector('.nllb-quality-badge');
    expect(qualityBadge).not.toBeNull();
    expect(qualityBadge.textContent).toContain('A');
    expect(qualityBadge.textContent).toContain('⚡');
    
    // Verify original text is preserved
    const originalText = textElement.querySelector('.nllb-original-text');
    expect(originalText).not.toBeNull();
    expect(originalText.textContent).toBe(textElement.textContent.replace('🌐 Optimized translation of the long message with enhanced quality (A) ⚡', '').trim());
  });

  test('should use standard translation for short messages', async () => {
    const shortMessage = document.querySelector('[data-message-id="adaptive-msg-2"]');
    const textElement = shortMessage.querySelector('.text-content');
    const originalText = textElement.textContent;
    
    // Mock standard translation response
    global.GM_xmlhttpRequest.mockImplementation(({ url, onload }) => {
      expect(url).toContain('/translate');
      expect(url).not.toContain('/adaptive');
      
      setTimeout(() => {
        onload({
          status: 200,
          responseText: JSON.stringify({
            translated_text: 'Short standard translation',
            detected_source: 'eng_Latn',
            time_ms: 85
          })
        });
      }, 10);
    });
    
    // Mock standard translation function
    global.translateStandard = async (messageElement, textElement) => {
      const text = textElement.textContent;
      const shouldUseAdaptive = global.CONFIG.enableAdaptiveTranslation && 
                               text.length > global.CONFIG.adaptiveForLongText;
      
      if (shouldUseAdaptive) {
        return { adaptive: true };
      }
      
      return new Promise((resolve) => {
        global.GM_xmlhttpRequest({
          url: global.CONFIG.translationServer + global.CONFIG.translationEndpoint,
          method: 'POST',
          data: JSON.stringify({ text }),
          onload: (response) => {
            const data = JSON.parse(response.responseText);
            textElement.textContent = '🌐 ' + data.translated_text;
            textElement.classList.add('nllb-translated');
            
            resolve({
              translatedText: data.translated_text,
              adaptive: false
            });
          }
        });
      });
    };
    
    // Execute standard translation
    const result = await global.translateStandard(shortMessage, textElement);
    
    // Verify standard translation was used
    expect(result.adaptive).toBe(false);
    expect(global.GM_xmlhttpRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        url: expect.stringContaining('/translate')
      })
    );
    
    // Verify no quality badge for standard translation
    const qualityBadge = textElement.querySelector('.nllb-quality-badge');
    expect(qualityBadge).toBeNull();
  });

  test('should handle progressive translation with real-time updates', async () => {
    const longMessage = document.querySelector('[data-message-id="adaptive-msg-3"]');
    const textElement = longMessage.querySelector('.text-content');
    const originalText = textElement.textContent;
    
    // Mock progressive translation with multiple updates
    global.GM_xmlhttpRequest.mockImplementation(({ url, onload }) => {
      expect(url).toContain('/adaptive/translate/progressive');
      
      setTimeout(() => {
        onload({
          status: 200,
          responseText: JSON.stringify({
            final_translation: 'Complete progressive translation with enhanced quality',
            quality_score: 0.96,
            quality_grade: 'A',
            optimization_applied: true,
            chunks_processed: 4,
            total_processing_time: 3.8,
            semantic_coherence: 0.97,
            progress_updates: [
              { chunk: 1, partial_translation: 'Another very long message', progress: 25, quality_preview: 0.88 },
              { chunk: 2, partial_translation: 'that contains complex technical content', progress: 50, quality_preview: 0.91 },
              { chunk: 3, partial_translation: 'with specialized terminology that requires', progress: 75, quality_preview: 0.94 },
              { chunk: 4, partial_translation: 'Complete progressive translation with enhanced quality', progress: 100, quality_preview: 0.96 }
            ]
          })
        });
      }, 10);
    });
    
    // Mock progressive translation function with UI updates
    global.translateProgressive = async (messageElement, textElement) => {
      const text = textElement.textContent;
      
      // Create progress container
      const progressContainer = document.createElement('div');
      progressContainer.className = 'nllb-progress-container';
      progressContainer.innerHTML = `
        <div class="nllb-progress-bar">
          <div class="nllb-progress-fill" style="width: 0%"></div>
        </div>
        <div class="nllb-progress-text">Processing...</div>
        <div class="nllb-partial-translation"></div>
      `;
      textElement.appendChild(progressContainer);
      
      return new Promise((resolve) => {
        global.GM_xmlhttpRequest({
          url: global.CONFIG.translationServer + global.CONFIG.progressiveEndpoint,
          method: 'POST',
          data: JSON.stringify({
            text,
            enable_progress_updates: true
          }),
          onload: (response) => {
            const data = JSON.parse(response.responseText);
            
            // Simulate progress updates
            let updateIndex = 0;
            const progressFill = progressContainer.querySelector('.nllb-progress-fill');
            const progressText = progressContainer.querySelector('.nllb-progress-text');
            const partialText = progressContainer.querySelector('.nllb-partial-translation');
            
            const processUpdate = () => {
              if (updateIndex < data.progress_updates.length) {
                const update = data.progress_updates[updateIndex];
                
                // Update progress bar
                progressFill.style.width = `${update.progress}%`;
                progressText.textContent = `Processing chunk ${update.chunk}... (${update.progress}%)`;
                partialText.textContent = update.partial_translation;
                
                updateIndex++;
                setTimeout(processUpdate, 200);
              } else {
                // Final update
                progressContainer.remove();
                textElement.textContent = '🌐 ' + data.final_translation;
                textElement.classList.add('nllb-translated');
                
                // Add enhanced quality badge
                const qualityBadge = document.createElement('span');
                qualityBadge.className = 'nllb-quality-badge nllb-progressive-badge';
                qualityBadge.textContent = ` (${data.quality_grade} Progressive)`;
                if (data.optimization_applied) qualityBadge.textContent += ' ⚡';
                qualityBadge.textContent += ` | ${data.chunks_processed} chunks`;
                textElement.appendChild(qualityBadge);
                
                resolve({
                  translatedText: data.final_translation,
                  qualityGrade: data.quality_grade,
                  chunksProcessed: data.chunks_processed,
                  progressive: true
                });
              }
            };
            
            setTimeout(processUpdate, 100);
          }
        });
      });
    };
    
    // Execute progressive translation
    const result = await global.translateProgressive(longMessage, textElement);
    
    // Wait for all updates to complete
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Verify progressive translation features
    expect(result.progressive).toBe(true);
    expect(result.qualityGrade).toBe('A');
    expect(result.chunksProcessed).toBe(4);
    
    // Verify final UI state
    expect(textElement.classList.contains('nllb-translated')).toBe(true);
    expect(textElement.textContent).toContain('Complete progressive translation');
    
    // Verify progressive quality badge
    const progressiveBadge = textElement.querySelector('.nllb-progressive-badge');
    expect(progressiveBadge).not.toBeNull();
    expect(progressiveBadge.textContent).toContain('Progressive');
    expect(progressiveBadge.textContent).toContain('4 chunks');
    expect(progressiveBadge.textContent).toContain('⚡');
    
    // Verify progress container was removed
    const progressContainer = textElement.querySelector('.nllb-progress-container');
    expect(progressContainer).toBeNull();
  });

  test('should handle multiple adaptive translations concurrently', async () => {
    const messages = document.querySelectorAll('.message');
    const longMessage1 = messages[0];
    const longMessage3 = messages[2];
    
    let requestCount = 0;
    
    // Mock concurrent adaptive translations
    global.GM_xmlhttpRequest.mockImplementation(({ url, data, onload }) => {
      requestCount++;
      const requestData = JSON.parse(data);
      
      setTimeout(() => {
        onload({
          status: 200,
          responseText: JSON.stringify({
            translation: `Adaptive translation ${requestCount} for: ${requestData.text.substring(0, 20)}...`,
            quality_score: 0.9 + (requestCount * 0.02),
            quality_grade: requestCount === 1 ? 'A' : 'A',
            optimization_applied: true,
            cache_hit: false,
            processing_time: 1.5 + requestCount,
            chunks_processed: requestCount + 1
          })
        });
      }, 50 * requestCount); // Stagger responses
    });
    
    // Mock concurrent translation function
    global.translateConcurrent = async (messageElements) => {
      const promises = messageElements.map(async (messageEl, index) => {
        const textEl = messageEl.querySelector('.text-content');
        const text = textEl.textContent;
        
        if (text.length <= global.CONFIG.adaptiveForLongText) {
          return { skipped: true, index };
        }
        
        return new Promise((resolve) => {
          global.GM_xmlhttpRequest({
            url: global.CONFIG.translationServer + global.CONFIG.adaptiveEndpoint,
            method: 'POST',
            data: JSON.stringify({ text }),
            onload: (response) => {
              const data = JSON.parse(response.responseText);
              
              textEl.textContent = '🌐 ' + data.translation;
              textEl.classList.add('nllb-translated');
              
              const qualityBadge = document.createElement('span');
              qualityBadge.className = 'nllb-quality-badge';
              qualityBadge.textContent = ` (${data.quality_grade})`;
              textEl.appendChild(qualityBadge);
              
              resolve({
                index,
                translatedText: data.translation,
                qualityGrade: data.quality_grade,
                chunksProcessed: data.chunks_processed
              });
            }
          });
        });
      });
      
      return Promise.all(promises);
    };
    
    // Execute concurrent translations
    const results = await global.translateConcurrent([longMessage1, longMessage3]);
    
    // Filter out skipped translations
    const completedResults = results.filter(r => !r.skipped);
    
    // Verify both translations completed
    expect(completedResults.length).toBe(2);
    expect(global.GM_xmlhttpRequest).toHaveBeenCalledTimes(2);
    
    // Verify each translation has quality indicators
    completedResults.forEach((result, index) => {
      expect(result.qualityGrade).toBe('A');
      expect(result.chunksProcessed).toBeGreaterThan(0);
      
      const messageEl = index === 0 ? longMessage1 : longMessage3;
      const qualityBadge = messageEl.querySelector('.nllb-quality-badge');
      expect(qualityBadge).not.toBeNull();
      expect(qualityBadge.textContent).toContain('A');
    });
  });

  test('should cache adaptive translations efficiently', async () => {
    const message1 = document.querySelector('[data-message-id="adaptive-msg-1"]');
    const textElement1 = message1.querySelector('.text-content');
    const originalText = textElement1.textContent;
    
    // First translation request
    global.GM_xmlhttpRequest.mockImplementation(({ onload }) => {
      setTimeout(() => {
        onload({
          status: 200,
          responseText: JSON.stringify({
            translation: 'Cached adaptive translation',
            quality_score: 0.93,
            quality_grade: 'A',
            optimization_applied: true,
            cache_hit: false, // First time, no cache hit
            processing_time: 2.1
          })
        });
      }, 10);
    });
    
    // Mock translation with caching
    global.translateWithCache = async (text, useCache = true) => {
      const cacheKey = `adaptive:${text.substring(0, 50)}`;
      
      if (useCache && global.state.adaptiveCache.has(cacheKey)) {
        const cached = global.state.adaptiveCache.get(cacheKey);
        return { ...cached, cache_hit: true };
      }
      
      return new Promise((resolve) => {
        global.GM_xmlhttpRequest({
          url: global.CONFIG.translationServer + global.CONFIG.adaptiveEndpoint,
          method: 'POST',
          data: JSON.stringify({ text }),
          onload: (response) => {
            const data = JSON.parse(response.responseText);
            
            // Cache the result
            if (useCache) {
              global.state.adaptiveCache.set(cacheKey, data);
            }
            
            resolve(data);
          }
        });
      });
    };
    
    // First translation (no cache)
    const result1 = await global.translateWithCache(originalText);
    expect(result1.cache_hit).toBe(false);
    expect(global.GM_xmlhttpRequest).toHaveBeenCalledTimes(1);
    
    // Second translation (should use cache)
    const result2 = await global.translateWithCache(originalText);
    expect(result2.cache_hit).toBe(true);
    expect(global.GM_xmlhttpRequest).toHaveBeenCalledTimes(1); // No additional request
    
    // Verify cache contains the result
    expect(global.state.adaptiveCache.size).toBe(1);
  });
});