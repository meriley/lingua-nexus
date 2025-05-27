# AI Architect Prompt: NLLB Translation System API Test Design

## Context
You are designing comprehensive API tests for the NLLB (No Language Left Behind) Translation System server component. The system uses FastAPI with rate limiting, model loading, and translation endpoints.

## Your Task
Use chain of thought reasoning and extended thinking to design a robust API test suite. Consider the following:

### System Architecture
- FastAPI server with async endpoints
- NLLB model integration via HuggingFace transformers
- Rate limiting via SlowAPI
- Translation pipeline with text preprocessing
- Error handling for model loading failures

### Current Test Gaps
1. **Rate Limiting**: Async behavior not properly mocked
2. **Translation Format**: Missing "Translated: " prefix consistency
3. **Error Handling**: API key validation gaps
4. **Model Loading**: Startup event testing incomplete

### Chain of Thought Process
Walk through your reasoning for:

1. **Test Strategy**: How should API tests be structured?
2. **Mock Design**: What components need mocking and why?
3. **Edge Cases**: What failure scenarios must be covered?
4. **Async Handling**: How to properly test async endpoints?
5. **Coverage Goals**: Strategies to achieve 95% server coverage

### Extended Thinking Requirements
- Consider real-world usage patterns
- Think about integration vs unit test boundaries
- Analyze potential race conditions in async code
- Design for maintainable test fixtures
- Plan for CI/CD pipeline integration

### Deliverables
Design and document:
1. Test suite architecture
2. Mock strategy for NLLB components
3. Specific test cases for each endpoint
4. Error scenarios and edge cases
5. Performance and load testing approach

### Technical Constraints
- Use pytest framework
- Mock HuggingFace transformers pipeline
- Handle FastAPI TestClient limitations
- Ensure deterministic test execution

Save your complete design to `/mnt/dionysus/coding/tg-text-translate/docs/testing/api_test_architecture.md`