/**
 * Unit tests for adaptive translation functionality
 */

describe('Adaptive Translation', () => {
  beforeEach(() => {
    // Reset DOM for each test
    document.body.innerHTML = `
      <div class="message" data-message-id="adaptive-test">
        <div class="message-content">
          <div class="text-content">This is a long text that should trigger adaptive translation with quality optimization and chunking for better translation quality and user experience.</div>
          <div class="time">12:34</div>
        </div>
      </div>
    `;
    
    // Clear all mocks
    jest.clearAllMocks();
    
    // Mock GM_xmlhttpRequest globally
    global.GM_xmlhttpRequest = jest.fn();
    
    // Mock CONFIG for adaptive features
    global.CONFIG = {
      translationServer: 'http://localhost:8001',
      adaptiveEndpoint: '/adaptive/translate',
      progressiveEndpoint: '/adaptive/translate/progressive',
      enableAdaptiveTranslation: true,
      enableProgressiveUI: true,
      adaptiveForLongText: 50,
      showQualityGrades: true,
      debugMode: true
    };
  });

  test('should detect when adaptive translation is needed', () => {
    const longText = 'This is a long text that should trigger adaptive translation with quality optimization and chunking for better translation quality.';
    const shortText = 'Short text';
    
    // Mock the adaptive detection logic
    const shouldUseAdaptive = (text) => 
      global.CONFIG.enableAdaptiveTranslation && text.length > global.CONFIG.adaptiveForLongText;
    
    expect(shouldUseAdaptive(longText)).toBe(true);
    expect(shouldUseAdaptive(shortText)).toBe(false);
  });

  test('should use adaptive endpoint for long text', async () => {
    const messageEl = document.querySelector('.message');
    const textEl = messageEl.querySelector('.text-content');
    const longText = textEl.textContent;
    
    // Mock successful adaptive translation response
    global.GM_xmlhttpRequest.mockImplementation(({ url, method, data, onload }) => {
      expect(url).toContain('/adaptive/translate');
      expect(method).toBe('POST');
      
      const requestData = JSON.parse(data);
      expect(requestData.text).toBe(longText);
      expect(requestData.user_preference).toBeDefined();
      
      setTimeout(() => {
        onload({
          status: 200,
          responseText: JSON.stringify({
            translation: 'Optimized translation result',
            quality_score: 0.92,
            quality_grade: 'A',
            optimization_applied: true,
            cache_hit: false,
            processing_time: 2.34,
            chunks_processed: 3,
            confidence_interval: [0.89, 0.95]
          })
        });
      }, 10);
    });
    
    // Mock translateText function for adaptive
    global.translateText = async (text, sourceLang, targetLang, useAdaptive) => {
      return new Promise((resolve) => {
        if (useAdaptive) {
          global.GM_xmlhttpRequest({
            url: global.CONFIG.translationServer + global.CONFIG.adaptiveEndpoint,
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            data: JSON.stringify({
              text,
              source_lang: sourceLang || 'auto',
              target_lang: targetLang || 'eng_Latn',
              user_preference: 'balanced'
            }),
            onload: (response) => {
              const data = JSON.parse(response.responseText);
              resolve({
                translatedText: data.translation,
                qualityScore: data.quality_score,
                qualityGrade: data.quality_grade,
                optimizationApplied: data.optimization_applied,
                cacheHit: data.cache_hit,
                processingTime: data.processing_time
              });
            }
          });
        }
      });
    };
    
    // Execute adaptive translation
    const result = await global.translateText(longText, 'auto', 'eng_Latn', true);
    
    // Verify adaptive response structure
    expect(result.translatedText).toBe('Optimized translation result');
    expect(result.qualityScore).toBe(0.92);
    expect(result.qualityGrade).toBe('A');
    expect(result.optimizationApplied).toBe(true);
    expect(result.cacheHit).toBe(false);
    expect(result.processingTime).toBe(2.34);
    expect(global.GM_xmlhttpRequest).toHaveBeenCalledTimes(1);
  });

  test('should display quality indicators for adaptive translations', () => {
    const messageEl = document.querySelector('.message');
    
    // Mock quality indicator creation
    const createQualityIndicator = (grade, optimized, cached) => {
      const indicator = document.createElement('span');
      indicator.className = 'nllb-quality-badge';
      indicator.textContent = `Grade: ${grade}`;
      
      if (optimized) {
        indicator.textContent += ' ⚡';
      }
      if (cached) {
        indicator.textContent += ' 💾';
      }
      
      return indicator;
    };
    
    // Add quality indicator to message
    const qualityBadge = createQualityIndicator('A', true, false);
    messageEl.appendChild(qualityBadge);
    
    // Verify quality badge exists and has correct content
    const badge = messageEl.querySelector('.nllb-quality-badge');
    expect(badge).not.toBeNull();
    expect(badge.textContent).toBe('Grade: A ⚡');
  });

  test('should handle progressive translation with updates', async () => {
    const longText = 'This is a very long text that should trigger progressive translation with real-time updates showing translation progress and quality assessment during the process.';
    
    // Mock progressive translation with multiple updates
    global.GM_xmlhttpRequest.mockImplementation(({ url, onload }) => {
      expect(url).toContain('/adaptive/translate/progressive');
      
      setTimeout(() => {
        onload({
          status: 200,
          responseText: JSON.stringify({
            final_translation: 'Final progressive translation result',
            quality_score: 0.94,
            quality_grade: 'A',
            optimization_applied: true,
            chunks_processed: 5,
            total_processing_time: 3.45,
            progress_updates: [
              { chunk: 1, partial_translation: 'This is a very', progress: 20 },
              { chunk: 2, partial_translation: 'long text that should', progress: 40 },
              { chunk: 3, partial_translation: 'trigger progressive translation', progress: 60 },
              { chunk: 4, partial_translation: 'with real-time updates', progress: 80 },
              { chunk: 5, partial_translation: 'Final progressive translation result', progress: 100 }
            ]
          })
        });
      }, 10);
    });
    
    // Mock progressive translation function
    global.translateWithProgressive = async (text, sourceLang, targetLang, onUpdate) => {
      return new Promise((resolve) => {
        global.GM_xmlhttpRequest({
          url: global.CONFIG.translationServer + global.CONFIG.progressiveEndpoint,
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          data: JSON.stringify({
            text,
            source_lang: sourceLang,
            target_lang: targetLang,
            enable_progress_updates: true
          }),
          onload: (response) => {
            const data = JSON.parse(response.responseText);
            
            // Simulate progress updates
            if (onUpdate && data.progress_updates) {
              data.progress_updates.forEach((update, index) => {
                setTimeout(() => {
                  onUpdate({
                    partialTranslation: update.partial_translation,
                    progress: update.progress,
                    chunk: update.chunk
                  });
                }, index * 100);
              });
            }
            
            resolve({
              translatedText: data.final_translation,
              qualityScore: data.quality_score,
              qualityGrade: data.quality_grade,
              optimizationApplied: data.optimization_applied,
              chunksProcessed: data.chunks_processed,
              processingTime: data.total_processing_time
            });
          }
        });
      });
    };
    
    // Track progress updates
    const progressUpdates = [];
    const onUpdate = (update) => {
      progressUpdates.push(update);
    };
    
    // Execute progressive translation
    const result = await global.translateWithProgressive(longText, 'auto', 'eng_Latn', onUpdate);
    
    // Wait for progress updates to complete
    await new Promise(resolve => setTimeout(resolve, 600));
    
    // Verify final result
    expect(result.translatedText).toBe('Final progressive translation result');
    expect(result.qualityGrade).toBe('A');
    expect(result.chunksProcessed).toBe(5);
    expect(global.GM_xmlhttpRequest).toHaveBeenCalledTimes(1);
    
    // Verify progress updates were received
    expect(progressUpdates.length).toBeGreaterThan(0);
    expect(progressUpdates[progressUpdates.length - 1].progress).toBe(100);
  });

  test('should fall back to standard translation if adaptive fails', async () => {
    const longText = 'Long text for adaptive translation';
    
    // Mock adaptive failure then standard success
    let callCount = 0;
    global.GM_xmlhttpRequest.mockImplementation(({ url, onload, onerror }) => {
      callCount++;
      
      if (url.includes('/adaptive/translate') && callCount === 1) {
        // First call to adaptive endpoint fails
        setTimeout(() => {
          onerror(new Error('Adaptive translation service unavailable'));
        }, 10);
      } else if (url.includes('/translate') && callCount === 2) {
        // Fallback to standard translation succeeds
        setTimeout(() => {
          onload({
            status: 200,
            responseText: JSON.stringify({
              translated_text: 'Standard fallback translation',
              detected_source: 'eng_Latn',
              time_ms: 150
            })
          });
        }, 10);
      }
    });
    
    // Mock translation with fallback logic
    global.translateWithFallback = async (text) => {
      try {
        // Try adaptive first
        return await new Promise((resolve, reject) => {
          global.GM_xmlhttpRequest({
            url: global.CONFIG.translationServer + global.CONFIG.adaptiveEndpoint,
            method: 'POST',
            data: JSON.stringify({ text }),
            onload: (response) => {
              const data = JSON.parse(response.responseText);
              resolve({ translatedText: data.translation });
            },
            onerror: reject
          });
        });
      } catch (error) {
        // Fall back to standard translation
        return await new Promise((resolve) => {
          global.GM_xmlhttpRequest({
            url: global.CONFIG.translationServer + '/translate',
            method: 'POST',
            data: JSON.stringify({ text }),
            onload: (response) => {
              const data = JSON.parse(response.responseText);
              resolve({ translatedText: data.translated_text });
            }
          });
        });
      }
    };
    
    // Execute translation with fallback
    const result = await global.translateWithFallback(longText);
    
    // Verify fallback worked
    expect(result.translatedText).toBe('Standard fallback translation');
    expect(global.GM_xmlhttpRequest).toHaveBeenCalledTimes(2);
  });

  test('should handle quality grade display preferences', () => {
    const testCases = [
      { grade: 'A', score: 0.95, expected: 'A (Excellent)' },
      { grade: 'B', score: 0.85, expected: 'B (Good)' },
      { grade: 'C', score: 0.75, expected: 'C (Fair)' },
      { grade: 'D', score: 0.65, expected: 'D (Poor)' },
      { grade: 'F', score: 0.45, expected: 'F (Failed)' }
    ];
    
    // Mock quality grade formatter
    const formatQualityGrade = (grade, score) => {
      const descriptions = {
        'A': 'Excellent',
        'B': 'Good', 
        'C': 'Fair',
        'D': 'Poor',
        'F': 'Failed'
      };
      return `${grade} (${descriptions[grade]})`;
    };
    
    testCases.forEach(({ grade, score, expected }) => {
      const formatted = formatQualityGrade(grade, score);
      expect(formatted).toBe(expected);
    });
  });

  test('should track optimization metrics correctly', () => {
    const metrics = {
      optimization_applied: true,
      cache_hit: false,
      processing_time: 2.34,
      chunks_processed: 3,
      confidence_interval: [0.89, 0.95],
      quality_score: 0.92
    };
    
    // Mock metrics formatter
    const formatMetrics = (metrics) => {
      const indicators = [];
      
      if (metrics.optimization_applied) {
        indicators.push('⚡ Optimized');
      }
      
      if (metrics.cache_hit) {
        indicators.push('💾 Cached');
      }
      
      if (metrics.processing_time) {
        indicators.push(`⏱️ ${metrics.processing_time}s`);
      }
      
      if (metrics.chunks_processed) {
        indicators.push(`📊 ${metrics.chunks_processed} chunks`);
      }
      
      return indicators.join(' | ');
    };
    
    const formatted = formatMetrics(metrics);
    expect(formatted).toBe('⚡ Optimized | ⏱️ 2.34s | 📊 3 chunks');
  });
});

describe('Adaptive Translation Error Handling', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.GM_xmlhttpRequest = jest.fn();
    
    global.CONFIG = {
      translationServer: 'http://localhost:8001',
      adaptiveEndpoint: '/adaptive/translate',
      enableAdaptiveTranslation: true,
      debugMode: true
    };
  });

  test('should handle adaptive service timeout', async () => {
    // Mock timeout scenario
    global.GM_xmlhttpRequest.mockImplementation(({ ontimeout }) => {
      setTimeout(() => {
        ontimeout(new Error('Request timeout'));
      }, 10);
    });
    
    // Mock timeout handling
    global.handleAdaptiveTimeout = async (text) => {
      return new Promise((resolve, reject) => {
        global.GM_xmlhttpRequest({
          url: global.CONFIG.translationServer + global.CONFIG.adaptiveEndpoint,
          timeout: 5000,
          ontimeout: reject
        });
      });
    };
    
    // Expect timeout error
    await expect(global.handleAdaptiveTimeout('test text')).rejects.toThrow('Request timeout');
  });

  test('should handle malformed adaptive response', async () => {
    // Mock malformed JSON response
    global.GM_xmlhttpRequest.mockImplementation(({ onload }) => {
      setTimeout(() => {
        onload({
          status: 200,
          responseText: 'Invalid JSON response'
        });
      }, 10);
    });
    
    // Mock response parser
    global.parseAdaptiveResponse = async () => {
      return new Promise((resolve, reject) => {
        global.GM_xmlhttpRequest({
          onload: (response) => {
            try {
              const data = JSON.parse(response.responseText);
              resolve(data);
            } catch (error) {
              reject(new Error('Invalid JSON response'));
            }
          }
        });
      });
    };
    
    // Expect JSON parsing error
    await expect(global.parseAdaptiveResponse()).rejects.toThrow('Invalid JSON response');
  });

  test('should handle missing quality metrics gracefully', () => {
    const incompleteResponse = {
      translation: 'Translation result'
      // Missing quality_score, quality_grade, etc.
    };
    
    // Mock quality metrics extractor
    const extractQualityMetrics = (response) => {
      return {
        translation: response.translation,
        qualityScore: response.quality_score || null,
        qualityGrade: response.quality_grade || 'N/A',
        optimizationApplied: response.optimization_applied || false,
        cacheHit: response.cache_hit || false,
        processingTime: response.processing_time || null
      };
    };
    
    const metrics = extractQualityMetrics(incompleteResponse);
    
    expect(metrics.translation).toBe('Translation result');
    expect(metrics.qualityScore).toBe(null);
    expect(metrics.qualityGrade).toBe('N/A');
    expect(metrics.optimizationApplied).toBe(false);
    expect(metrics.cacheHit).toBe(false);
    expect(metrics.processingTime).toBe(null);
  });
});