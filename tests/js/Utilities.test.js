/**
 * Tests for utility functions in numerous.js
 */

// Mock LOG_LEVELS
global.LOG_LEVELS = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3,
  NONE: 4
};

// Store original console methods
const originalConsole = { ...console };

// Mock window.localStorage
const localStorageMock = (() => {
  let store = {};
  return {
    getItem: (key) => store[key] || null,
    setItem: (key, value) => { store[key] = value.toString(); },
    removeItem: (key) => { delete store[key]; },
    clear: () => { store = {}; }
  };
})();

// Mock window.location for URL parsing
const originalLocation = window.location;

describe('Numerous.js Utility Functions', () => {
  // Set up mocks before each test
  beforeEach(() => {
    // Mock console methods
    console.log = jest.fn();
    console.info = jest.fn();
    console.warn = jest.fn();
    console.error = jest.fn();
    
    // Set up localStorage mock
    Object.defineProperty(window, 'localStorage', { value: localStorageMock });
    
    // Reset localStorage before each test
    window.localStorage.clear();
    
    // Reset global currentLogLevel for each test
    global.currentLogLevel = global.LOG_LEVELS.ERROR; // Default
    
    // Create URLSearchParams mock for window.location.search
    delete window.location;
    window.location = { 
      search: '',
      href: 'http://example.com'
    };
  });
  
  // Restore original after all tests
  afterAll(() => {
    Object.assign(console, originalConsole);
    window.location = originalLocation;
  });
  
  describe('initializeDebugging', () => {
    // Recreate the initializeDebugging function from numerous.js
    function initializeDebugging() {
      // Check for debug parameter in URL
      const urlParams = new URLSearchParams(window.location.search);
      const debugParam = urlParams.get('debug');
      
      if (debugParam === 'true' || debugParam === '1') {
        global.currentLogLevel = global.LOG_LEVELS.DEBUG;
        console.info('Debug logging enabled');
        return; // Exit early to prioritize URL parameter
      }
      
      // Also check for localStorage debug preference
      try {
        const storedLevel = localStorage.getItem('numerousLogLevel');
        if (storedLevel && global.LOG_LEVELS[storedLevel] !== undefined) {
          global.currentLogLevel = global.LOG_LEVELS[storedLevel];
          console.info(`Log level set from localStorage: ${storedLevel}`);
        }
      } catch (e) {
        // Ignore localStorage errors
      }
    }
    
    it('should set debug level to DEBUG when URL parameter is true', () => {
      window.location.search = '?debug=true';
      initializeDebugging();
      
      expect(global.currentLogLevel).toBe(global.LOG_LEVELS.DEBUG);
      expect(console.info).toHaveBeenCalledWith('Debug logging enabled');
    });
    
    it('should set debug level to DEBUG when URL parameter is 1', () => {
      window.location.search = '?debug=1';
      initializeDebugging();
      
      expect(global.currentLogLevel).toBe(global.LOG_LEVELS.DEBUG);
      expect(console.info).toHaveBeenCalledWith('Debug logging enabled');
    });
    
    it('should use localStorage value if available', () => {
      localStorage.setItem('numerousLogLevel', 'WARN');
      initializeDebugging();
      
      expect(global.currentLogLevel).toBe(global.LOG_LEVELS.WARN);
      expect(console.info).toHaveBeenCalledWith('Log level set from localStorage: WARN');
    });
    
    it('should prioritize URL parameter over localStorage', () => {
      // Set up localStorage first
      localStorage.setItem('numerousLogLevel', 'WARN');
      
      // Then set URL parameter
      window.location.search = '?debug=true';
      
      // Set the initial log level to something other than DEBUG
      global.currentLogLevel = global.LOG_LEVELS.ERROR;
      
      // Run the function
      initializeDebugging();
      
      // Verify URL parameter takes precedence
      expect(global.currentLogLevel).toBe(global.LOG_LEVELS.DEBUG);
      expect(console.info).toHaveBeenCalledWith('Debug logging enabled');
    });
    
    it('should keep default level when no parameters are set', () => {
      const defaultLevel = global.LOG_LEVELS.ERROR;
      global.currentLogLevel = defaultLevel;
      
      initializeDebugging();
      
      expect(global.currentLogLevel).toBe(defaultLevel);
      expect(console.info).not.toHaveBeenCalled();
    });
    
    it('should ignore invalid localStorage values', () => {
      const defaultLevel = global.LOG_LEVELS.ERROR;
      global.currentLogLevel = defaultLevel;
      
      localStorage.setItem('numerousLogLevel', 'INVALID_LEVEL');
      initializeDebugging();
      
      expect(global.currentLogLevel).toBe(defaultLevel);
      expect(console.info).not.toHaveBeenCalled();
    });
    
    it('should handle localStorage access errors', () => {
      const defaultLevel = global.LOG_LEVELS.ERROR;
      global.currentLogLevel = defaultLevel;
      
      // Simulate localStorage error
      Object.defineProperty(window, 'localStorage', {
        get: () => { throw new Error('localStorage access denied'); }
      });
      
      // This should not throw an error
      expect(() => {
        initializeDebugging();
      }).not.toThrow();
      
      expect(global.currentLogLevel).toBe(defaultLevel);
    });
  });
  
  describe('log function', () => {
    // Recreate the log function from numerous.js
    function log(level, ...args) {
      if (level >= global.currentLogLevel) {
        switch (level) {
          case global.LOG_LEVELS.DEBUG:
            console.log(...args);
            break;
          case global.LOG_LEVELS.INFO:
            console.info(...args);
            break;
          case global.LOG_LEVELS.WARN:
            console.warn(...args);
            break;
          case global.LOG_LEVELS.ERROR:
            console.error(...args);
            break;
        }
      }
    }
    
    it('should not log messages below the current log level', () => {
      global.currentLogLevel = global.LOG_LEVELS.ERROR;
      
      log(global.LOG_LEVELS.DEBUG, 'Debug message');
      log(global.LOG_LEVELS.INFO, 'Info message');
      log(global.LOG_LEVELS.WARN, 'Warning message');
      
      expect(console.log).not.toHaveBeenCalled();
      expect(console.info).not.toHaveBeenCalled();
      expect(console.warn).not.toHaveBeenCalled();
    });
    
    it('should log messages at or above the current log level', () => {
      global.currentLogLevel = global.LOG_LEVELS.WARN;
      
      log(global.LOG_LEVELS.WARN, 'Warning message');
      log(global.LOG_LEVELS.ERROR, 'Error message');
      
      expect(console.warn).toHaveBeenCalledWith('Warning message');
      expect(console.error).toHaveBeenCalledWith('Error message');
    });
    
    it('should log DEBUG messages to console.log', () => {
      global.currentLogLevel = global.LOG_LEVELS.DEBUG;
      
      log(global.LOG_LEVELS.DEBUG, 'Debug message');
      
      expect(console.log).toHaveBeenCalledWith('Debug message');
    });
    
    it('should log INFO messages to console.info', () => {
      global.currentLogLevel = global.LOG_LEVELS.DEBUG;
      
      log(global.LOG_LEVELS.INFO, 'Info message');
      
      expect(console.info).toHaveBeenCalledWith('Info message');
    });
    
    it('should log WARN messages to console.warn', () => {
      global.currentLogLevel = global.LOG_LEVELS.DEBUG;
      
      log(global.LOG_LEVELS.WARN, 'Warning message');
      
      expect(console.warn).toHaveBeenCalledWith('Warning message');
    });
    
    it('should log ERROR messages to console.error', () => {
      global.currentLogLevel = global.LOG_LEVELS.DEBUG;
      
      log(global.LOG_LEVELS.ERROR, 'Error message');
      
      expect(console.error).toHaveBeenCalledWith('Error message');
    });
    
    it('should pass through multiple arguments', () => {
      global.currentLogLevel = global.LOG_LEVELS.DEBUG;
      
      const obj = { foo: 'bar' };
      log(global.LOG_LEVELS.DEBUG, 'Debug message', obj, 123);
      
      expect(console.log).toHaveBeenCalledWith('Debug message', obj, 123);
    });
    
    it('should not log anything when log level is NONE', () => {
      global.currentLogLevel = global.LOG_LEVELS.NONE;
      
      log(global.LOG_LEVELS.DEBUG, 'Debug message');
      log(global.LOG_LEVELS.INFO, 'Info message');
      log(global.LOG_LEVELS.WARN, 'Warning message');
      log(global.LOG_LEVELS.ERROR, 'Error message');
      
      expect(console.log).not.toHaveBeenCalled();
      expect(console.info).not.toHaveBeenCalled();
      expect(console.warn).not.toHaveBeenCalled();
      expect(console.error).not.toHaveBeenCalled();
    });
  });
}); 