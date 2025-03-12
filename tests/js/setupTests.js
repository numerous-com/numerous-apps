/**
 * Setup file for Jest tests
 * This file runs before each test file
 */

// Mock browser globals that might not be available in JSDOM
if (typeof window !== 'undefined') {
  // Mock WebSocket
  global.WebSocket = class MockWebSocket {
    constructor(url) {
      this.url = url;
      this.readyState = 0; // CONNECTING
      this.CONNECTING = 0;
      this.OPEN = 1;
      this.CLOSING = 2;
      this.CLOSED = 3;
      
      // Auto connect for testing
      setTimeout(() => {
        this.readyState = 1; // OPEN
        this.onopen && this.onopen();
      }, 0);
    }
    
    send(data) {
      // Mock implementation
      this.lastSentData = data;
    }
    
    close() {
      this.readyState = 3; // CLOSED
      this.onclose && this.onclose({ code: 1000 });
    }
  };
  
  // Mock localStorage
  if (!window.localStorage) {
    const localStorageMock = (function() {
      let store = {};
      return {
        getItem: function(key) {
          return store[key] || null;
        },
        setItem: function(key, value) {
          store[key] = value.toString();
        },
        removeItem: function(key) {
          delete store[key];
        },
        clear: function() {
          store = {};
        }
      };
    })();
    
    Object.defineProperty(window, 'localStorage', {
      value: localStorageMock
    });
  }
  
  // Mock sessionStorage
  if (!window.sessionStorage) {
    const sessionStorageMock = (function() {
      let store = {};
      return {
        getItem: function(key) {
          return store[key] || null;
        },
        setItem: function(key, value) {
          store[key] = value.toString();
        },
        removeItem: function(key) {
          delete store[key];
        },
        clear: function() {
          store = {};
        }
      };
    })();
    
    Object.defineProperty(window, 'sessionStorage', {
      value: sessionStorageMock
    });
  }
  
  // Add fetch mock if not available
  if (!window.fetch) {
    window.fetch = jest.fn().mockImplementation(() => {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
        text: () => Promise.resolve(''),
      });
    });
  }
}

// Global afterEach to clear all mocks
afterEach(() => {
  jest.clearAllMocks();
}); 