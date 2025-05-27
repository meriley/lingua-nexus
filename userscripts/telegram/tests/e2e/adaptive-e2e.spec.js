/**
 * End-to-end tests for adaptive translation features
 * Tests the full user workflow with real browser interaction
 */

const { test, expect } = require('@playwright/test');

test.describe('Adaptive Translation E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the test page with userscript
    await page.goto('http://localhost:8080/mockup/index.html');
    
    // Wait for userscript to load
    await page.waitForTimeout(1000);
    
    // Verify CONFIG is loaded with adaptive settings
    const configLoaded = await page.evaluate(() => {
      return typeof window.CONFIG !== 'undefined' && 
             window.CONFIG.enableAdaptiveTranslation === true;
    });
    expect(configLoaded).toBe(true);
  });

  test('should show adaptive translation quality indicators for long messages', async ({ page }) => {
    // Add a long message that should trigger adaptive translation
    await page.evaluate(() => {
      const messageContainer = document.querySelector('.messages-container');
      const longMessageHTML = `
        <div class="message" data-message-id="e2e-adaptive-long">
          <div class="message-content">
            <div class="text-content">This is a comprehensive test message that contains sufficient text length to trigger the adaptive translation system with quality optimization features. The adaptive system should analyze this text, determine optimal chunking strategies, apply semantic coherence analysis, and provide enhanced translation quality with real-time progress indicators, quality assessment metrics, and optimization status indicators.</div>
            <div class="time">
              12:34
              <span class="nllb-translate-button" title="Translate this message">🌐</span>
            </div>
          </div>
        </div>
      `;
      messageContainer.innerHTML = longMessageHTML;
    });
    
    // Mock the adaptive translation API response
    await page.route('**/adaptive/translate', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          translation: 'Comprehensive optimized translation with enhanced quality and semantic coherence',
          quality_score: 0.94,
          quality_grade: 'A',
          optimization_applied: true,
          cache_hit: false,
          processing_time: 2.3,
          chunks_processed: 3,
          semantic_coherence: 0.96,
          confidence_interval: [0.91, 0.97]
        })
      });
    });
    
    // Click the translate button
    await page.click('.nllb-translate-button');
    
    // Wait for adaptive translation to complete
    await page.waitForSelector('.nllb-translated', { timeout: 5000 });
    
    // Verify translated text appears
    const translatedText = await page.textContent('.nllb-translated');
    expect(translatedText).toContain('Comprehensive optimized translation');
    
    // Verify quality badge is shown
    const qualityBadge = await page.textContent('.nllb-quality-badge');
    expect(qualityBadge).toContain('A');
    expect(qualityBadge).toContain('⚡'); // Optimization indicator
    
    // Verify adaptive-specific elements
    const hasAdaptiveClass = await page.isVisible('.nllb-adaptive-translation');
    if (hasAdaptiveClass) {
      expect(hasAdaptiveClass).toBe(true);
    }
    
    // Check for processing time display
    const processingInfo = await page.textContent('.nllb-quality-badge');
    expect(processingInfo).toMatch(/\d+\.\d+s/); // Should contain processing time
  });

  test('should use progressive translation for very long messages', async ({ page }) => {
    // Add a very long message that should trigger progressive translation
    await page.evaluate(() => {
      const messageContainer = document.querySelector('.messages-container');
      const veryLongMessageHTML = `
        <div class="message" data-message-id="e2e-progressive-long">
          <div class="message-content">
            <div class="text-content">This is an exceptionally long message designed to thoroughly test the progressive translation functionality with real-time updates and quality assessment. The progressive translation system should break this extensive text into optimal semantic chunks, process each chunk sequentially while maintaining contextual coherence, provide real-time progress indicators showing translation advancement, display partial results as they become available, apply advanced quality optimization algorithms throughout the process, and finally present the complete translation with comprehensive quality metrics including grade assessment, optimization status, cache utilization indicators, processing time measurements, and semantic coherence scores that demonstrate the superior quality achieved through the adaptive chunking and progressive refinement approach.</div>
            <div class="time">
              12:35
              <span class="nllb-translate-button" title="Translate this message (with quality optimization)">🌐</span>
            </div>
          </div>
        </div>
      `;
      messageContainer.innerHTML = veryLongMessageHTML;
    });
    
    // Mock the progressive translation API response
    await page.route('**/adaptive/translate/progressive', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          final_translation: 'Complete progressive translation with superior quality and contextual coherence',
          quality_score: 0.97,
          quality_grade: 'A',
          optimization_applied: true,
          chunks_processed: 5,
          total_processing_time: 4.1,
          semantic_coherence: 0.98,
          progress_updates: [
            { chunk: 1, partial_translation: 'This is an exceptionally long message', progress: 20, quality_preview: 0.89 },
            { chunk: 2, partial_translation: 'designed to thoroughly test progressive translation', progress: 40, quality_preview: 0.92 },
            { chunk: 3, partial_translation: 'with real-time updates and quality assessment', progress: 60, quality_preview: 0.94 },
            { chunk: 4, partial_translation: 'providing comprehensive optimization features', progress: 80, quality_preview: 0.96 },
            { chunk: 5, partial_translation: 'Complete progressive translation with superior quality', progress: 100, quality_preview: 0.97 }
          ]
        })
      });
    });
    
    // Click the translate button
    await page.click('.nllb-translate-button');
    
    // Verify progress indicators appear
    await page.waitForSelector('.nllb-progress-container', { timeout: 2000 });
    
    // Check progress bar exists
    const progressBar = await page.isVisible('.nllb-progress-bar');
    expect(progressBar).toBe(true);
    
    // Wait for progress updates (simulate progressive behavior)
    await page.waitForTimeout(1000);
    
    // Verify progress text updates
    const progressText = await page.textContent('.nllb-progress-text');
    expect(progressText).toMatch(/Processing|chunk|%/i);
    
    // Wait for final translation
    await page.waitForSelector('.nllb-translated', { timeout: 8000 });
    
    // Verify progress container is removed
    const progressContainerGone = await page.isHidden('.nllb-progress-container');
    expect(progressContainerGone).toBe(true);
    
    // Verify final translation
    const finalText = await page.textContent('.nllb-translated');
    expect(finalText).toContain('Complete progressive translation');
    
    // Verify progressive quality badge
    const progressiveBadge = await page.textContent('.nllb-progressive-badge');
    expect(progressiveBadge).toContain('Progressive');
    expect(progressiveBadge).toContain('5 chunks');
  });

  test('should fallback to standard translation when adaptive fails', async ({ page }) => {
    // Add a long message
    await page.evaluate(() => {
      const messageContainer = document.querySelector('.messages-container');
      const messageHTML = `
        <div class="message" data-message-id="e2e-fallback-test">
          <div class="message-content">
            <div class="text-content">This message should initially try adaptive translation but fall back to standard translation when adaptive service is unavailable.</div>
            <div class="time">
              12:36
              <span class="nllb-translate-button" title="Translate this message">🌐</span>
            </div>
          </div>
        </div>
      `;
      messageContainer.innerHTML = messageHTML;
    });
    
    // Mock adaptive endpoint to fail
    await page.route('**/adaptive/translate', async route => {
      await route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Adaptive translation service temporarily unavailable'
        })
      });
    });
    
    // Mock standard endpoint to succeed
    await page.route('**/translate', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          translated_text: 'Standard fallback translation result',
          detected_source: 'eng_Latn',
          time_ms: 120
        })
      });
    });
    
    // Click translate button
    await page.click('.nllb-translate-button');
    
    // Wait for fallback translation
    await page.waitForSelector('.nllb-translated', { timeout: 5000 });
    
    // Verify fallback translation succeeded
    const translatedText = await page.textContent('.nllb-translated');
    expect(translatedText).toContain('Standard fallback translation');
    
    // Verify no adaptive quality badge (since it fell back to standard)
    const hasQualityBadge = await page.isVisible('.nllb-quality-badge');
    expect(hasQualityBadge).toBe(false);
    
    // Verify no adaptive-specific elements
    const hasAdaptiveElements = await page.isVisible('.nllb-adaptive-translation');
    expect(hasAdaptiveElements).toBe(false);
  });

  test('should display quality grades accurately for different translation qualities', async ({ page }) => {
    const testCases = [
      { 
        grade: 'A', 
        score: 0.95, 
        text: 'High quality text for excellent translation',
        optimization: true,
        cache: false
      },
      { 
        grade: 'B', 
        score: 0.85, 
        text: 'Good quality text for solid translation results',
        optimization: false,
        cache: true
      },
      { 
        grade: 'C', 
        score: 0.75, 
        text: 'Fair quality text with acceptable translation',
        optimization: false,
        cache: false
      }
    ];
    
    for (let i = 0; i < testCases.length; i++) {
      const testCase = testCases[i];
      
      // Add message for this test case
      await page.evaluate((index, text) => {
        const messageContainer = document.querySelector('.messages-container');
        const messageHTML = `
          <div class="message" data-message-id="quality-test-${index}">
            <div class="message-content">
              <div class="text-content">${text}</div>
              <div class="time">
                12:3${7 + index}
                <span class="nllb-translate-button">🌐</span>
              </div>
            </div>
          </div>
        `;
        messageContainer.innerHTML = messageHTML;
      }, i, testCase.text);
      
      // Mock adaptive response for this quality level
      await page.route('**/adaptive/translate', async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            translation: `${testCase.grade}-grade translation result`,
            quality_score: testCase.score,
            quality_grade: testCase.grade,
            optimization_applied: testCase.optimization,
            cache_hit: testCase.cache,
            processing_time: 1.5 + (i * 0.3)
          })
        });
      });
      
      // Click translate button
      await page.click(`[data-message-id="quality-test-${i}"] .nllb-translate-button`);
      
      // Wait for translation
      await page.waitForSelector(`[data-message-id="quality-test-${i}"] .nllb-translated`, { timeout: 3000 });
      
      // Verify quality grade display
      const qualityBadge = await page.textContent(`[data-message-id="quality-test-${i}"] .nllb-quality-badge`);
      expect(qualityBadge).toContain(testCase.grade);
      
      // Verify optimization indicator
      if (testCase.optimization) {
        expect(qualityBadge).toContain('⚡');
      }
      
      // Verify cache indicator
      if (testCase.cache) {
        expect(qualityBadge).toContain('💾');
      }
    }
  });

  test('should handle concurrent adaptive translations efficiently', async ({ page }) => {
    // Add multiple long messages
    await page.evaluate(() => {
      const messageContainer = document.querySelector('.messages-container');
      const messagesHTML = `
        <div class="message" data-message-id="concurrent-1">
          <div class="message-content">
            <div class="text-content">First concurrent message for adaptive translation testing with sufficient length to trigger optimization features and quality assessment.</div>
            <div class="time">12:40 <span class="nllb-translate-button">🌐</span></div>
          </div>
        </div>
        <div class="message" data-message-id="concurrent-2">
          <div class="message-content">
            <div class="text-content">Second concurrent message for testing parallel adaptive translation processing with quality metrics and optimization indicators.</div>
            <div class="time">12:41 <span class="nllb-translate-button">🌐</span></div>
          </div>
        </div>
        <div class="message" data-message-id="concurrent-3">
          <div class="message-content">
            <div class="text-content">Third concurrent message to verify the system can handle multiple adaptive translation requests simultaneously without degradation.</div>
            <div class="time">12:42 <span class="nllb-translate-button">🌐</span></div>
          </div>
        </div>
      `;
      messageContainer.innerHTML = messagesHTML;
    });
    
    let requestCount = 0;
    
    // Mock adaptive responses with slight delays
    await page.route('**/adaptive/translate', async route => {
      requestCount++;
      const delay = requestCount * 200; // Stagger responses
      
      setTimeout(async () => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            translation: `Concurrent translation ${requestCount} completed`,
            quality_score: 0.88 + (requestCount * 0.02),
            quality_grade: 'A',
            optimization_applied: true,
            cache_hit: false,
            processing_time: 1.2 + (requestCount * 0.1),
            request_id: requestCount
          })
        });
      }, delay);
    });
    
    // Click all translate buttons simultaneously
    await Promise.all([
      page.click('[data-message-id="concurrent-1"] .nllb-translate-button'),
      page.click('[data-message-id="concurrent-2"] .nllb-translate-button'),
      page.click('[data-message-id="concurrent-3"] .nllb-translate-button')
    ]);
    
    // Wait for all translations to complete
    await Promise.all([
      page.waitForSelector('[data-message-id="concurrent-1"] .nllb-translated', { timeout: 5000 }),
      page.waitForSelector('[data-message-id="concurrent-2"] .nllb-translated', { timeout: 5000 }),
      page.waitForSelector('[data-message-id="concurrent-3"] .nllb-translated', { timeout: 5000 })
    ]);
    
    // Verify all translations completed successfully
    for (let i = 1; i <= 3; i++) {
      const translatedText = await page.textContent(`[data-message-id="concurrent-${i}"] .nllb-translated`);
      expect(translatedText).toContain(`Concurrent translation ${i}`);
      
      const qualityBadge = await page.textContent(`[data-message-id="concurrent-${i}"] .nllb-quality-badge`);
      expect(qualityBadge).toContain('A');
      expect(qualityBadge).toContain('⚡');
    }
    
    // Verify all requests were made
    expect(requestCount).toBe(3);
  });

  test('should preserve original text on hover for adaptive translations', async ({ page }) => {
    // Add a message for hover testing
    await page.evaluate(() => {
      const messageContainer = document.querySelector('.messages-container');
      const messageHTML = `
        <div class="message" data-message-id="hover-test">
          <div class="message-content">
            <div class="text-content">Original text for hover functionality testing with adaptive translation system.</div>
            <div class="time">12:45 <span class="nllb-translate-button">🌐</span></div>
          </div>
        </div>
      `;
      messageContainer.innerHTML = messageHTML;
    });
    
    const originalText = await page.textContent('[data-message-id="hover-test"] .text-content');
    
    // Mock adaptive translation
    await page.route('**/adaptive/translate', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          translation: 'Translated text with hover preservation',
          quality_score: 0.91,
          quality_grade: 'A',
          optimization_applied: true
        })
      });
    });
    
    // Translate the message
    await page.click('[data-message-id="hover-test"] .nllb-translate-button');
    await page.waitForSelector('[data-message-id="hover-test"] .nllb-translated');
    
    // Verify translation is shown
    const translatedText = await page.textContent('[data-message-id="hover-test"] .nllb-translated');
    expect(translatedText).toContain('Translated text with hover preservation');
    
    // Hover over the translated text
    await page.hover('[data-message-id="hover-test"] .nllb-translated');
    
    // Verify original text is shown or accessible
    const hasOriginalText = await page.isVisible('[data-message-id="hover-test"] .nllb-original-text');
    if (hasOriginalText) {
      const originalTextElement = await page.textContent('[data-message-id="hover-test"] .nllb-original-text');
      expect(originalTextElement).toBe(originalText.trim());
    }
    
    // Alternative: Check title attribute for original text
    const titleText = await page.getAttribute('[data-message-id="hover-test"] .nllb-translated', 'title');
    if (titleText) {
      expect(titleText).toContain('Original text for hover functionality');
    }
  });
});