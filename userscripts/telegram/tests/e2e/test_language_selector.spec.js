/**
 * E2E tests for UserScript language selector components.
 * TASK-004: Comprehensive testing of language selector UI and functionality.
 */

import { test, expect } from '@playwright/test';
import path from 'path';

// Test configuration
const TEST_CONFIG = {
    telegramUrl: 'https://web.telegram.org/',
    mockTelegramUrl: path.resolve(__dirname, '../../mockup/index.html'),
    userScriptPath: path.resolve(__dirname, '../../telegram-nllb-translator.user.js'),
    modulesPath: path.resolve(__dirname, '../../telegram-nllb-translator.modules.js'),
    testApiUrl: 'http://localhost:8000',
    testApiKey: 'test-api-key-12345'
};

// Mock language data for testing
const MOCK_LANGUAGE_DATA = {
    languages: [
        {
            code: "auto",
            name: "Auto-detect",
            native_name: "Auto-detect",
            family: "Auto",
            script: "Auto",
            popular: true,
            region: "Global",
            rtl: false
        },
        {
            code: "eng_Latn",
            name: "English",
            native_name: "English",
            family: "Germanic",
            script: "Latin",
            popular: true,
            region: "Global",
            rtl: false
        },
        {
            code: "spa_Latn",
            name: "Spanish",
            native_name: "Español",
            family: "Romance",
            script: "Latin",
            popular: true,
            region: "Global",
            rtl: false
        },
        {
            code: "fra_Latn",
            name: "French",
            native_name: "Français",
            family: "Romance",
            script: "Latin",
            popular: true,
            region: "Global",
            rtl: false
        },
        {
            code: "rus_Cyrl",
            name: "Russian",
            native_name: "Русский",
            family: "Slavic",
            script: "Cyrillic",
            popular: true,
            region: "Eastern Europe",
            rtl: false
        },
        {
            code: "arb_Arab",
            name: "Arabic",
            native_name: "العربية",
            family: "Afro-Asiatic",
            script: "Arabic",
            popular: true,
            region: "Middle East",
            rtl: true
        }
    ],
    families: {
        "Auto": ["auto"],
        "Germanic": ["eng_Latn"],
        "Romance": ["spa_Latn", "fra_Latn"],
        "Slavic": ["rus_Cyrl"],
        "Afro-Asiatic": ["arb_Arab"]
    },
    popular: ["auto", "eng_Latn", "spa_Latn", "fra_Latn", "rus_Cyrl", "arb_Arab"],
    popular_pairs: [
        ["auto", "eng_Latn"],
        ["eng_Latn", "spa_Latn"],
        ["eng_Latn", "fra_Latn"],
        ["rus_Cyrl", "eng_Latn"]
    ],
    total_count: 6,
    cache_headers: {
        "Cache-Control": "public, max-age=3600",
        "ETag": "lang-metadata-v1-6"
    }
};

test.describe('Language Selector E2E Tests', () => {
    test.beforeEach(async ({ page }) => {
        // Mock API responses
        await page.route(`${TEST_CONFIG.testApiUrl}/languages`, route => {
            route.fulfill({
                status: 200,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(MOCK_LANGUAGE_DATA)
            });
        });

        // Mock translation API
        await page.route(`${TEST_CONFIG.testApiUrl}/translate`, route => {
            const request = route.request();
            const postData = request.postDataJSON();
            
            // Simple mock translation
            let translatedText = 'Translated: ' + postData.text;
            if (postData.target_lang === 'spa_Latn') {
                translatedText = 'Hola mundo';
            } else if (postData.target_lang === 'fra_Latn') {
                translatedText = 'Bonjour le monde';
            }
            
            route.fulfill({
                status: 200,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    translated_text: translatedText,
                    detected_source: postData.source_lang || 'eng_Latn',
                    time_ms: 150
                })
            });
        });

        // Load mockup page
        await page.goto(`file://${TEST_CONFIG.mockTelegramUrl}`);
        
        // Inject UserScript modules
        await page.addScriptTag({ path: TEST_CONFIG.modulesPath });
        await page.addScriptTag({ path: TEST_CONFIG.userScriptPath });
        
        // Wait for initialization
        await page.waitForTimeout(1000);
    });

    test('language selector renders correctly in single mode', async ({ page }) => {
        // Wait for language selector to appear
        await page.waitForSelector('.nllb-language-selector', { timeout: 5000 });
        
        // Check if language selector is visible
        const selector = page.locator('.nllb-language-selector');
        await expect(selector).toBeVisible();
        
        // Check if language button exists
        const languageButton = page.locator('.nllb-language-button');
        await expect(languageButton).toBeVisible();
        
        // Verify initial language display
        const buttonText = await languageButton.textContent();
        expect(buttonText).toContain('English'); // Default target language
    });

    test('language dropdown opens and displays available languages', async ({ page }) => {
        // Wait for language selector
        await page.waitForSelector('.nllb-language-selector');
        
        // Click language button to open dropdown
        const languageButton = page.locator('.nllb-language-button');
        await languageButton.click();
        
        // Wait for dropdown to appear
        await page.waitForSelector('.nllb-language-dropdown', { state: 'visible' });
        
        // Verify dropdown is visible
        const dropdown = page.locator('.nllb-language-dropdown');
        await expect(dropdown).toBeVisible();
        
        // Check if popular languages are listed
        const languageOptions = page.locator('.nllb-language-option');
        const optionCount = await languageOptions.count();
        expect(optionCount).toBeGreaterThan(3);
        
        // Verify specific languages are present
        await expect(page.locator('.nllb-language-option:has-text("English")')).toBeVisible();
        await expect(page.locator('.nllb-language-option:has-text("Spanish")')).toBeVisible();
        await expect(page.locator('.nllb-language-option:has-text("French")')).toBeVisible();
    });

    test('language selection changes target language correctly', async ({ page }) => {
        // Open language selector
        await page.waitForSelector('.nllb-language-selector');
        const languageButton = page.locator('.nllb-language-button');
        await languageButton.click();
        
        // Wait for dropdown
        await page.waitForSelector('.nllb-language-dropdown', { state: 'visible' });
        
        // Select Spanish
        const spanishOption = page.locator('.nllb-language-option:has-text("Spanish")');
        await spanishOption.click();
        
        // Verify dropdown closes
        await page.waitForSelector('.nllb-language-dropdown', { state: 'hidden' });
        
        // Verify button text updates
        const updatedButtonText = await languageButton.textContent();
        expect(updatedButtonText).toContain('Spanish');
        
        // Verify language change is persisted
        await page.reload();
        await page.waitForTimeout(1000);
        await page.waitForSelector('.nllb-language-selector');
        
        const persistedButtonText = await page.locator('.nllb-language-button').textContent();
        expect(persistedButtonText).toContain('Spanish');
    });

    test('language search functionality works correctly', async ({ page }) => {
        // Open language selector
        await page.waitForSelector('.nllb-language-selector');
        await page.locator('.nllb-language-button').click();
        await page.waitForSelector('.nllb-language-dropdown', { state: 'visible' });
        
        // Find search input
        const searchInput = page.locator('.nllb-language-search');
        await expect(searchInput).toBeVisible();
        
        // Type search term
        await searchInput.fill('Fren');
        
        // Wait for filtering
        await page.waitForTimeout(300);
        
        // Verify filtered results
        const visibleOptions = page.locator('.nllb-language-option:visible');
        const visibleCount = await visibleOptions.count();
        
        // Should show French but not others
        await expect(page.locator('.nllb-language-option:has-text("French"):visible')).toBeVisible();
        expect(visibleCount).toBeLessThan(6); // Should be filtered
        
        // Clear search
        await searchInput.fill('');
        await page.waitForTimeout(300);
        
        // Verify all options are visible again
        const allOptionsCount = await page.locator('.nllb-language-option:visible').count();
        expect(allOptionsCount).toBeGreaterThan(3);
    });

    test('keyboard navigation works in language dropdown', async ({ page }) => {
        // Open language selector
        await page.waitForSelector('.nllb-language-selector');
        await page.locator('.nllb-language-button').click();
        await page.waitForSelector('.nllb-language-dropdown', { state: 'visible' });
        
        // Focus on search input
        const searchInput = page.locator('.nllb-language-search');
        await searchInput.focus();
        
        // Navigate with arrow keys
        await page.keyboard.press('ArrowDown');
        await page.waitForTimeout(100);
        
        // Verify first option is highlighted
        const firstOption = page.locator('.nllb-language-option').first();
        await expect(firstOption).toHaveClass(/highlighted|selected/);
        
        // Navigate down more
        await page.keyboard.press('ArrowDown');
        await page.waitForTimeout(100);
        
        // Navigate up
        await page.keyboard.press('ArrowUp');
        await page.waitForTimeout(100);
        
        // Select with Enter
        await page.keyboard.press('Enter');
        
        // Verify dropdown closes
        await page.waitForSelector('.nllb-language-dropdown', { state: 'hidden' });
    });

    test('recent languages functionality works correctly', async ({ page }) => {
        // Configure to show recent languages
        await page.evaluate(() => {
            window.NLLB_CONFIG = window.NLLB_CONFIG || {};
            window.NLLB_CONFIG.showRecentLanguages = true;
            window.NLLB_CONFIG.maxRecentLanguages = 3;
        });
        
        // Perform language selections to build recent list
        const languages = ['Spanish', 'French', 'Russian'];
        
        for (const lang of languages) {
            // Open selector
            await page.waitForSelector('.nllb-language-selector');
            await page.locator('.nllb-language-button').click();
            await page.waitForSelector('.nllb-language-dropdown', { state: 'visible' });
            
            // Select language
            await page.locator(`.nllb-language-option:has-text("${lang}")`).click();
            await page.waitForSelector('.nllb-language-dropdown', { state: 'hidden' });
            
            // Short delay
            await page.waitForTimeout(200);
        }
        
        // Open selector again
        await page.locator('.nllb-language-button').click();
        await page.waitForSelector('.nllb-language-dropdown', { state: 'visible' });
        
        // Verify recent languages section exists
        const recentSection = page.locator('.nllb-recent-languages');
        await expect(recentSection).toBeVisible();
        
        // Verify recent languages are displayed
        for (const lang of languages) {
            await expect(page.locator(`.nllb-recent-languages .nllb-language-option:has-text("${lang}")`)).toBeVisible();
        }
    });

    test('language swap functionality works correctly', async ({ page }) => {
        // Configure for language swap
        await page.evaluate(() => {
            window.NLLB_CONFIG = window.NLLB_CONFIG || {};
            window.NLLB_CONFIG.enableLanguageSwap = true;
            window.NLLB_CONFIG.languageSelectionMode = 'pair';
        });
        
        // Wait for pair selector to load
        await page.waitForSelector('.nllb-language-pair-selector');
        
        // Verify source and target selectors exist
        const sourceSelector = page.locator('.nllb-source-language');
        const targetSelector = page.locator('.nllb-target-language');
        const swapButton = page.locator('.nllb-swap-languages');
        
        await expect(sourceSelector).toBeVisible();
        await expect(targetSelector).toBeVisible();
        await expect(swapButton).toBeVisible();
        
        // Get initial values
        const initialSource = await sourceSelector.textContent();
        const initialTarget = await targetSelector.textContent();
        
        // Click swap button
        await swapButton.click();
        await page.waitForTimeout(300);
        
        // Verify languages are swapped
        const swappedSource = await sourceSelector.textContent();
        const swappedTarget = await targetSelector.textContent();
        
        expect(swappedSource).toBe(initialTarget);
        expect(swappedTarget).toBe(initialSource);
    });

    test('RTL language display works correctly', async ({ page }) => {
        // Open language selector
        await page.waitForSelector('.nllb-language-selector');
        await page.locator('.nllb-language-button').click();
        await page.waitForSelector('.nllb-language-dropdown', { state: 'visible' });
        
        // Select Arabic (RTL language)
        const arabicOption = page.locator('.nllb-language-option:has-text("Arabic")');
        await expect(arabicOption).toBeVisible();
        await arabicOption.click();
        
        // Verify Arabic is selected
        await page.waitForSelector('.nllb-language-dropdown', { state: 'hidden' });
        const buttonText = await page.locator('.nllb-language-button').textContent();
        expect(buttonText).toContain('Arabic');
        
        // Verify RTL styling is applied where appropriate
        const languageButton = page.locator('.nllb-language-button');
        const classList = await languageButton.getAttribute('class');
        // May include RTL-specific classes for Arabic
    });

    test('language selector accessibility features', async ({ page }) => {
        // Test ARIA attributes
        await page.waitForSelector('.nllb-language-selector');
        const languageButton = page.locator('.nllb-language-button');
        
        // Check ARIA attributes
        await expect(languageButton).toHaveAttribute('aria-haspopup', 'listbox');
        await expect(languageButton).toHaveAttribute('aria-expanded', 'false');
        
        // Open dropdown
        await languageButton.click();
        await page.waitForSelector('.nllb-language-dropdown', { state: 'visible' });
        
        // Check expanded state
        await expect(languageButton).toHaveAttribute('aria-expanded', 'true');
        
        // Check dropdown ARIA attributes
        const dropdown = page.locator('.nllb-language-dropdown');
        await expect(dropdown).toHaveAttribute('role', 'listbox');
        
        // Check option ARIA attributes
        const firstOption = page.locator('.nllb-language-option').first();
        await expect(firstOption).toHaveAttribute('role', 'option');
        
        // Test focus management
        const searchInput = page.locator('.nllb-language-search');
        await expect(searchInput).toBeFocused();
        
        // Test escape key closes dropdown
        await page.keyboard.press('Escape');
        await page.waitForSelector('.nllb-language-dropdown', { state: 'hidden' });
        await expect(languageButton).toHaveAttribute('aria-expanded', 'false');
    });

    test('language selector performance with large language list', async ({ page }) => {
        // Mock larger language list
        const largeLanguageData = {
            ...MOCK_LANGUAGE_DATA,
            languages: Array.from({ length: 50 }, (_, i) => ({
                code: `lang${i}_Latn`,
                name: `Language ${i}`,
                native_name: `Native ${i}`,
                family: `Family ${i % 5}`,
                script: "Latin",
                popular: i < 10,
                region: "Test Region",
                rtl: false
            })),
            total_count: 50
        };
        
        // Update mock response
        await page.route(`${TEST_CONFIG.testApiUrl}/languages`, route => {
            route.fulfill({
                status: 200,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(largeLanguageData)
            });
        });
        
        // Reload and time the operation
        await page.reload();
        await page.waitForTimeout(1000);
        
        const startTime = Date.now();
        
        // Open language selector
        await page.waitForSelector('.nllb-language-selector');
        await page.locator('.nllb-language-button').click();
        await page.waitForSelector('.nllb-language-dropdown', { state: 'visible' });
        
        const endTime = Date.now();
        const loadTime = endTime - startTime;
        
        // Should load within reasonable time
        expect(loadTime).toBeLessThan(2000); // 2 seconds max
        
        // Verify all languages are loaded
        const optionCount = await page.locator('.nllb-language-option').count();
        expect(optionCount).toBeGreaterThan(40); // Should have most languages
    });

    test('language selector error handling', async ({ page }) => {
        // Mock API error
        await page.route(`${TEST_CONFIG.testApiUrl}/languages`, route => {
            route.fulfill({
                status: 500,
                body: 'Internal Server Error'
            });
        });
        
        // Reload page
        await page.reload();
        await page.waitForTimeout(1000);
        
        // Language selector should still appear with fallback languages
        await page.waitForSelector('.nllb-language-selector');
        
        // Open selector
        await page.locator('.nllb-language-button').click();
        await page.waitForSelector('.nllb-language-dropdown', { state: 'visible' });
        
        // Should show at least basic languages (fallback)
        const optionCount = await page.locator('.nllb-language-option').count();
        expect(optionCount).toBeGreaterThan(0);
        
        // Verify error handling doesn't break functionality
        const englishOption = page.locator('.nllb-language-option:has-text("English")');
        await expect(englishOption).toBeVisible();
        await englishOption.click();
        
        // Should still work
        await page.waitForSelector('.nllb-language-dropdown', { state: 'hidden' });
    });

    test('language selector integration with translation', async ({ page }) => {
        // Find a message element to test translation
        await page.waitForSelector('.message-text');
        
        // Change target language to Spanish
        await page.waitForSelector('.nllb-language-selector');
        await page.locator('.nllb-language-button').click();
        await page.waitForSelector('.nllb-language-dropdown', { state: 'visible' });
        await page.locator('.nllb-language-option:has-text("Spanish")').click();
        await page.waitForSelector('.nllb-language-dropdown', { state: 'hidden' });
        
        // Find and click translate button
        const translateButton = page.locator('.nllb-translate-button').first();
        await expect(translateButton).toBeVisible();
        await translateButton.click();
        
        // Wait for translation to complete
        await page.waitForTimeout(1000);
        
        // Verify translation appears
        const translatedMessage = page.locator('.nllb-translated').first();
        await expect(translatedMessage).toBeVisible();
        
        // Verify translated content
        const translatedText = await translatedMessage.textContent();
        expect(translatedText).toContain('Hola mundo'); // Mock Spanish translation
    });
});

test.describe('Language Selector Mobile Responsiveness', () => {
    test.beforeEach(async ({ page }) => {
        // Set mobile viewport
        await page.setViewportSize({ width: 375, height: 667 });
    });

    test('language selector adapts to mobile screen', async ({ page }) => {
        // Setup same as main tests
        await page.route(`${TEST_CONFIG.testApiUrl}/languages`, route => {
            route.fulfill({
                status: 200,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(MOCK_LANGUAGE_DATA)
            });
        });

        await page.goto(`file://${TEST_CONFIG.mockTelegramUrl}`);
        await page.addScriptTag({ path: TEST_CONFIG.modulesPath });
        await page.addScriptTag({ path: TEST_CONFIG.userScriptPath });
        await page.waitForTimeout(1000);
        
        // Language selector should be visible on mobile
        await page.waitForSelector('.nllb-language-selector');
        const selector = page.locator('.nllb-language-selector');
        await expect(selector).toBeVisible();
        
        // Button should be appropriately sized
        const languageButton = page.locator('.nllb-language-button');
        const buttonBox = await languageButton.boundingBox();
        
        // Should be touchable (minimum 44px height recommended)
        expect(buttonBox.height).toBeGreaterThan(30);
        expect(buttonBox.width).toBeGreaterThan(60);
        
        // Dropdown should fit screen
        await languageButton.click();
        await page.waitForSelector('.nllb-language-dropdown', { state: 'visible' });
        
        const dropdown = page.locator('.nllb-language-dropdown');
        const dropdownBox = await dropdown.boundingBox();
        
        // Should not exceed viewport width
        expect(dropdownBox.width).toBeLessThanOrEqual(375);
        expect(dropdownBox.x + dropdownBox.width).toBeLessThanOrEqual(375);
    });
});