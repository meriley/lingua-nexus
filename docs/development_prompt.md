# NLLB Translation System Development Prompt

As a Senior Engineer, your task is to implement the NLLB Translation System according to the architecture specifications and implementation plan. This prompt will guide your development process.

## Project Context

You're implementing a self-hosted NLLB (No Language Left Behind) translation system with browser and desktop integration for Telegram. The system consists of three main components:

1. **Server Component**: A FastAPI-based server hosting the NLLB translation model
2. **Browser UserScript**: A JavaScript userscript for web.telegram.org/k integration
3. **AutoHotkey Component**: A Windows script for system-wide translation

The architecture and implementation plan have been prepared. Your job is to write the actual code and implement the system step by step.

## Your Tasks

1. Start with the **Server Component** (highest priority):
   - Implement the FastAPI server with NLLB model integration
   - Focus on optimizing translation performance and memory usage
   - Implement proper error handling and API security measures

2. Progress to the **Browser UserScript**:
   - Create a userscript that integrates with Telegram Web
   - Implement dynamic message detection and translation buttons
   - Ensure reliable communication with the translation server

3. Develop the **AutoHotkey Component**:
   - Create a Windows script for system-wide translation
   - Implement hotkeys for text selection and translation
   - Add proper error handling and user notifications

## Development Guidelines

1. **Follow the Implementation Plan**: Prioritize tasks as specified in the implementation plan
2. **Write Production-Quality Code**: Include proper error handling, logging, and documentation
3. **Focus on Performance**: Optimize for low latency in translations
4. **Consider Security**: Implement API authentication and input validation
5. **Test Thoroughly**: Write tests for each component
6. **Document Your Work**: Add clear documentation for each component

## Getting Started

Begin with the Server Component tasks:

1. Set up the project structure
2. Implement the FastAPI server skeleton
3. Integrate the NLLB model
4. Add the translation endpoint with error handling
5. Implement optimization techniques

For each component, follow this workflow:
1. Create the basic structure
2. Implement core functionality
3. Add error handling and edge cases
4. Optimize performance
5. Ensure security measures
6. Write tests and documentation

## Technical Considerations

### Server Component
- Use PyTorch with optimization techniques (quantization, caching)
- Consider ONNX runtime for better performance
- Balance memory usage with translation quality
- Implement proper API security (keys, rate limiting)

### Browser UserScript
- Use MutationObserver for dynamic content detection
- Ensure non-intrusive UI integration
- Handle Telegram's DOM structure changes gracefully
- Optimize API communication for low latency

### AutoHotkey Component
- Implement robust text selection methods
- Add configurable hotkeys
- Create unobtrusive notification system
- Ensure secure API communication

## Expected Outputs

For each component, provide:
1. Complete source code
2. Installation instructions
3. Configuration guidance
4. Testing procedures
5. Performance benchmarks

Your final deliverables should include a fully functional, optimized translation system that meets all the requirements specified in the architecture document and implementation plan.