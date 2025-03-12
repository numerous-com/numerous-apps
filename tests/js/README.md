# JavaScript Tests for Numerous.js

This directory contains Jest-based unit tests for the client-side JavaScript code (`numerous.js`) used in the Numerous apps framework.

## Setup

The testing infrastructure uses [Jest](https://jestjs.io/) with JSDOM to provide a browser-like environment. The setup includes:

- Mock implementations for browser APIs (WebSocket, localStorage, etc.)
- Test utilities for simulating events and interactions
- Coverage reporting

## Running the Tests

To run the JavaScript tests, make sure you're in the project root directory and have installed the npm dependencies:

```bash
npm install
```

Then run the tests using:

```bash
npm test
```

To run the tests with coverage:

```bash
npm run test:coverage
```

To run the tests in watch mode (useful during development):

```bash
npm run test:watch
```

## Test Structure

The tests are organized by functionality:

- **WidgetModel.test.js** - Tests for the WidgetModel class, which manages widget state and synchronization
- **WebSocketManager.test.js** - Tests for the WebSocketManager class, which handles communication with the server
- **Utilities.test.js** - Tests for utility functions like logging and debugging

## Writing New Tests

When adding tests for new functionality in `numerous.js`, follow these guidelines:

1. Create a new test file or add to existing files based on functionality
2. Use the Jest testing syntax (`describe`, `it`, `expect`)
3. Mock any browser APIs that your code interacts with
4. Structure tests with clear, descriptive names
5. Include tests for both success and failure cases

### Example Test Structure

```javascript
describe('ComponentName', () => {
  let component;
  
  beforeEach(() => {
    // Setup code
    component = new Component();
  });
  
  afterEach(() => {
    // Cleanup code
  });
  
  describe('methodName', () => {
    it('should do something specific', () => {
      // Arrange
      const input = 'test';
      
      // Act
      const result = component.methodName(input);
      
      // Assert
      expect(result).toBe('expected output');
    });
    
    it('should handle error cases', () => {
      // Test error handling
      expect(() => {
        component.methodName(null);
      }).toThrow();
    });
  });
});
```

## Coverage Requirements

Aim for at least 80% test coverage for new JavaScript code. Important features like state management, communication, and error handling should have near 100% coverage.

## Mocking Approach

Since `numerous.js` is not structured as modules, we use a simplified approach where we recreate the key classes and functions for testing. This allows us to test the logic without needing to import the actual file.

The approach includes:

1. Recreating key classes and functions with the same API
2. Using Jest's spies to track function calls and verify behavior
3. Mocking browser APIs like WebSocket and localStorage

## Troubleshooting

If you encounter issues while running tests:

- Ensure the mock implementations match the actual code
- Check that DOM elements used in tests match the structure used in the application
- Verify that async behaviors are properly handled with async/await or Promise expectations 