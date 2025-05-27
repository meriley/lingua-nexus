// Debug script to analyze Telegram Web DOM structure
// Copy and paste this into your browser console (F12) while on Telegram Web

console.log('=== Telegram DOM Structure Analysis ===');

// Basic page info
console.log('URL:', window.location.href);
console.log('Title:', document.title);
console.log('Telegram version detected:', 
  window.location.pathname.includes('/k/') ? 'K version' :
  window.location.pathname.includes('/a/') ? 'A version' :
  window.location.pathname.includes('/z/') ? 'Z version' : 'Unknown');

// Check for common container elements
const containers = [
  '.messages-container',
  '.chat-messages',
  '.messages-layout',
  '.messages-wrapper',
  '#messages',
  '[class*="messages"]',
  '[class*="chat"]'
];

console.log('\n=== Message Containers ===');
containers.forEach(selector => {
  const elements = document.querySelectorAll(selector);
  if (elements.length > 0) {
    console.log(`✓ Found ${elements.length} elements for: ${selector}`);
    elements.forEach((el, i) => {
      console.log(`  [${i}] Classes:`, el.className);
      console.log(`  [${i}] Children:`, el.children.length);
    });
  } else {
    console.log(`✗ No elements found for: ${selector}`);
  }
});

// Check for message elements
const messageSelectors = [
  '.message',
  '.Message',
  '[class*="message"]',
  '[data-message-id]',
  '[data-mid]'
];

console.log('\n=== Message Elements ===');
messageSelectors.forEach(selector => {
  const elements = document.querySelectorAll(selector);
  if (elements.length > 0) {
    console.log(`✓ Found ${elements.length} messages for: ${selector}`);
    // Show first 3 messages as examples
    Array.from(elements).slice(0, 3).forEach((el, i) => {
      console.log(`  Message ${i}:`);
      console.log(`    Classes: ${el.className}`);
      console.log(`    ID: ${el.id}`);
      console.log(`    Data attributes:`, Object.keys(el.dataset));
      console.log(`    Text content preview:`, el.textContent.substring(0, 100) + '...');
      
      // Check for text content elements
      const textSelectors = [
        '.text-content',
        '.message-text',
        '.text',
        '[class*="text"]'
      ];
      
      textSelectors.forEach(textSel => {
        const textEl = el.querySelector(textSel);
        if (textEl) {
          console.log(`    Text element (${textSel}): "${textEl.textContent.substring(0, 50)}..."`);
          console.log(`    Text element classes: ${textEl.className}`);
        }
      });
    });
  } else {
    console.log(`✗ No messages found for: ${selector}`);
  }
});

// Check for input elements
const inputSelectors = [
  '.input-message-input',
  '.input-field-input',
  '[contenteditable="true"]',
  'textarea',
  'input[type="text"]'
];

console.log('\n=== Input Elements ===');
inputSelectors.forEach(selector => {
  const elements = document.querySelectorAll(selector);
  if (elements.length > 0) {
    console.log(`✓ Found ${elements.length} inputs for: ${selector}`);
    Array.from(elements).slice(0, 2).forEach((el, i) => {
      console.log(`  Input ${i}:`);
      console.log(`    Classes: ${el.className}`);
      console.log(`    Tag: ${el.tagName}`);
      console.log(`    Contenteditable: ${el.contentEditable}`);
      console.log(`    Parent classes: ${el.parentElement?.className}`);
    });
  } else {
    console.log(`✗ No inputs found for: ${selector}`);
  }
});

// Check for time/metadata elements (where we might place buttons)
const metadataSelectors = [
  '.time',
  '.message-time',
  '[class*="time"]',
  '.message-meta',
  '.message-footer'
];

console.log('\n=== Metadata Elements ===');
metadataSelectors.forEach(selector => {
  const elements = document.querySelectorAll(selector);
  if (elements.length > 0) {
    console.log(`✓ Found ${elements.length} metadata for: ${selector}`);
    Array.from(elements).slice(0, 2).forEach((el, i) => {
      console.log(`  Metadata ${i}:`);
      console.log(`    Classes: ${el.className}`);
      console.log(`    Parent classes: ${el.parentElement?.className}`);
    });
  }
});

// Try to find the active chat area specifically
console.log('\n=== Active Chat Detection ===');
const chatArea = document.querySelector('.chat-container, .chat-content, [class*="chat-"]');
if (chatArea) {
  console.log('Chat area found:', chatArea.className);
  const messagesInChat = chatArea.querySelectorAll('[class*="message"]');
  console.log('Messages in chat area:', messagesInChat.length);
} else {
  console.log('No specific chat area found');
}

// Dump the overall DOM structure for context
console.log('\n=== Overall DOM Structure ===');
const bodyClasses = document.body.className;
console.log('Body classes:', bodyClasses);

const mainContent = document.querySelector('main, #app, .app, [class*="app"]');
if (mainContent) {
  console.log('Main content element:', mainContent.tagName, mainContent.className);
}

// Check if there are any existing translation buttons
const existingButtons = document.querySelectorAll('.nllb-translate-button, [class*="translate"]');
console.log('\n=== Existing Translation Elements ===');
console.log('Existing buttons found:', existingButtons.length);

// Sample the first message structure completely
console.log('\n=== Sample Message Structure ===');
const firstMessage = document.querySelector('[class*="message"]');
if (firstMessage) {
  console.log('First message HTML structure:');
  console.log(firstMessage.outerHTML.substring(0, 500) + '...');
  
  // Walk through the children
  console.log('Message children:');
  Array.from(firstMessage.children).forEach((child, i) => {
    console.log(`  Child ${i}: ${child.tagName}.${child.className}`);
    if (child.children.length > 0) {
      Array.from(child.children).slice(0, 3).forEach((grandchild, j) => {
        console.log(`    Grandchild ${j}: ${grandchild.tagName}.${grandchild.className}`);
      });
    }
  });
} else {
  console.log('No messages found to sample');
}

console.log('\n=== Analysis Complete ===');
console.log('Please copy this entire output and share it!');