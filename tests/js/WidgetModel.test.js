/**
 * Tests for the WidgetModel class in numerous.js
 */

// Import the WidgetModel class
// Since numerous.js is not set up as a module, we'll need to mock it
// We'll create a simplified version of the class for testing

// Mock the log function to avoid console spam during tests
global.log = jest.fn();
global.LOG_LEVELS = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3,
  NONE: 4
};

// This is a simplified version of the WidgetModel class for testing
class WidgetModel {
  constructor(widgetId) {
    this.widgetId = widgetId;
    this.data = {};
    this._callbacks = {};
    this._initializing = true;
    this._pendingChanges = new Map();
    this._lastSyncedValues = {};
    this._changedProperties = new Set();
    this._pendingRequests = new Map();
    this._lastRequestId = 0;
    this._lockUpdates = false;
    this._suppressSync = false;
  }
  
  _generateRequestId() {
    return `${this.widgetId}-${++this._lastRequestId}-${Date.now()}`;
  }
  
  set(key, value, suppressSync = false) {
    const oldValue = this.data[key];
    const valueChanged = oldValue !== value;
    
    this.data[key] = value;
    
    if (valueChanged) {
      this.trigger('change:' + key, value);
      this.trigger('change', { key, value, oldValue });
      this._changedProperties.add(key);
    }
    
    // Handle different sync scenarios
    if (this._initializing && !suppressSync) {
      // If we're initializing and not suppressing sync, store for later
      this._pendingChanges.set(key, value);
    } else if (!suppressSync && !this._suppressSync && !this._lockUpdates) {
      // If we're not suppressing sync and not locked, send to server
      if (global.wsManager) {
        const requestId = this._generateRequestId();
        this._pendingRequests.set(key, requestId);
        global.wsManager.sendUpdate(this.widgetId, key, value, requestId);
      }
    }
  }
  
  completeInitialization() {
    if (!this._initializing) return;
    
    this._initializing = false;
    
    if (this._pendingChanges.size > 0) {
      // Create a batch update for pending changes
      const batchData = {};
      for (const [key, value] of this._pendingChanges.entries()) {
        batchData[key] = value;
        this._lastSyncedValues[key] = value;
      }
      
      // Send batch update if we have multiple changes
      if (Object.keys(batchData).length > 1 && global.wsManager && global.wsManager.batchUpdate) {
        const batchRequestId = this._generateRequestId();
        for (const key of Object.keys(batchData)) {
          this._pendingRequests.set(key, batchRequestId);
        }
        global.wsManager.batchUpdate(this.widgetId, batchData, batchRequestId);
      } else {
        // Fall back to individual updates
        for (const [key, value] of this._pendingChanges.entries()) {
          const requestId = this._generateRequestId();
          this._pendingRequests.set(key, requestId);
          if (global.wsManager) {
            global.wsManager.sendUpdate(this.widgetId, key, value, requestId);
          }
        }
      }
    }
    
    this._pendingChanges.clear();
    this._changedProperties.clear();
  }
  
  confirmUpdate(key, value, requestId) {
    if (this._pendingRequests.get(key) === requestId) {
      this._lastSyncedValues[key] = value;
      this._pendingRequests.delete(key);
    }
  }
  
  confirmBatchUpdate(properties, requestId) {
    for (const [key, value] of Object.entries(properties)) {
      this.confirmUpdate(key, value, requestId);
    }
  }
  
  get(key) {
    return this.data[key];
  }
  
  save_changes() {
    if (this._initializing) {
      this.completeInitialization();
      return;
    }
    
    if (this._changedProperties.size > 0) {
      this._lockUpdates = true;
      
      try {
        const changedData = {};
        let changesDetected = false;
        
        for (const key of this._changedProperties) {
          const value = this.data[key];
          if (this._lastSyncedValues[key] !== value) {
            changedData[key] = value;
            changesDetected = true;
          }
        }
        
        if (changesDetected) {
          if (Object.keys(changedData).length > 1 && global.wsManager && global.wsManager.batchUpdate) {
            const batchRequestId = this._generateRequestId();
            for (const key of Object.keys(changedData)) {
              this._pendingRequests.set(key, batchRequestId);
            }
            global.wsManager.batchUpdate(this.widgetId, changedData, batchRequestId);
          } else {
            for (const [key, value] of Object.entries(changedData)) {
              const requestId = this._generateRequestId();
              this._pendingRequests.set(key, requestId);
              if (global.wsManager) {
                global.wsManager.sendUpdate(this.widgetId, key, value, requestId);
              }
            }
          }
        }
      } finally {
        this._changedProperties.clear();
        this._lockUpdates = false;
      }
    }
  }
  
  on(eventName, callback) {
    if (!this._callbacks[eventName]) {
      this._callbacks[eventName] = [];
    }
    this._callbacks[eventName].push(callback);
  }
  
  off(eventName, callback) {
    if (!eventName) {
      this._callbacks = {};
      return;
    }
    if (this._callbacks[eventName]) {
      if (!callback) {
        delete this._callbacks[eventName];
      } else {
        this._callbacks[eventName] = this._callbacks[eventName].filter(cb => cb !== callback);
      }
    }
  }
  
  trigger(eventName, data) {
    if (this._callbacks[eventName]) {
      this._callbacks[eventName].forEach(callback => callback(data));
    }
  }
  
  registerObservers(registerFn) {
    global.observerRegistrations = global.observerRegistrations || new Map();
    global.observerRegistrations.set(this.widgetId, registerFn);
    registerFn();
  }
}

describe('WidgetModel', () => {
  let model;
  let mockWsManager;
  
  beforeEach(() => {
    // Set up a mock WebSocketManager
    mockWsManager = {
      sendUpdate: jest.fn(),
      batchUpdate: jest.fn()
    };
    
    // Attach to global so the model can use it
    global.wsManager = mockWsManager;
    
    // Create a fresh model instance for each test
    model = new WidgetModel('test-widget');
  });
  
  afterEach(() => {
    // Clean up
    global.wsManager = undefined;
    if (global.observerRegistrations) {
      global.observerRegistrations.clear();
    }
  });
  
  describe('constructor', () => {
    it('should initialize with the correct widget ID', () => {
      expect(model.widgetId).toBe('test-widget');
    });
    
    it('should initialize with an empty data object', () => {
      expect(model.data).toEqual({});
    });
    
    it('should set the initializing flag to true', () => {
      expect(model._initializing).toBe(true);
    });
  });
  
  describe('set method', () => {
    it('should set a value in the data object', () => {
      model.set('testKey', 'testValue');
      expect(model.data.testKey).toBe('testValue');
    });
    
    it('should trigger a change event when value changes', () => {
      const callback = jest.fn();
      model.on('change:testKey', callback);
      
      model.set('testKey', 'testValue');
      
      expect(callback).toHaveBeenCalledWith('testValue');
    });
    
    it('should not trigger a change event when value does not change', () => {
      const callback = jest.fn();
      
      // Set the initial value
      model.set('testKey', 'testValue');
      
      // Register the callback after setting initial value
      model.on('change:testKey', callback);
      
      // Set the same value again
      model.set('testKey', 'testValue');
      
      expect(callback).not.toHaveBeenCalled();
    });
    
    it('should add the property to changedProperties when value changes', () => {
      model.set('testKey', 'testValue');
      expect(model._changedProperties.has('testKey')).toBe(true);
    });
    
    it('should send update to server when not suppressed', () => {
      model._initializing = false; // Disable initialization mode
      
      model.set('testKey', 'testValue');
      
      expect(mockWsManager.sendUpdate).toHaveBeenCalledWith(
        'test-widget',
        'testKey',
        'testValue',
        expect.any(String)
      );
    });
    
    it('should not send update to server when suppressSync is true', () => {
      model._initializing = false; // Disable initialization mode
      
      model.set('testKey', 'testValue', true); // suppressSync = true
      
      expect(mockWsManager.sendUpdate).not.toHaveBeenCalled();
    });
    
    it('should add to pendingChanges when in initialization mode', () => {
      // Create a fresh model instance for this test
      const testModel = new WidgetModel('test-widget');
      
      // Ensure we're in initialization mode
      testModel._initializing = true;
      
      // Set a value
      testModel.set('testKey', 'testValue');
      
      // Verify it was added to pendingChanges
      expect(testModel._pendingChanges.get('testKey')).toBe('testValue');
      expect(mockWsManager.sendUpdate).not.toHaveBeenCalled();
    });
  });
  
  describe('get method', () => {
    it('should retrieve a value from the data object', () => {
      model.data.testKey = 'testValue';
      expect(model.get('testKey')).toBe('testValue');
    });
    
    it('should return undefined for non-existent keys', () => {
      expect(model.get('nonExistentKey')).toBeUndefined();
    });
  });
  
  describe('completeInitialization method', () => {
    it('should set initializing flag to false', () => {
      model.completeInitialization();
      expect(model._initializing).toBe(false);
    });
    
    it('should clear pending changes', () => {
      model._pendingChanges.set('key1', 'value1');
      model._pendingChanges.set('key2', 'value2');
      
      model.completeInitialization();
      
      expect(model._pendingChanges.size).toBe(0);
    });
    
    it('should send a batch update if multiple changes are pending', () => {
      model._pendingChanges.set('key1', 'value1');
      model._pendingChanges.set('key2', 'value2');
      
      model.completeInitialization();
      
      expect(mockWsManager.batchUpdate).toHaveBeenCalledWith(
        'test-widget',
        expect.objectContaining({
          key1: 'value1',
          key2: 'value2'
        }),
        expect.any(String)
      );
    });
    
    it('should fall back to individual updates if batchUpdate is not available', () => {
      // Remove batchUpdate capability
      delete mockWsManager.batchUpdate;
      
      model._pendingChanges.set('key1', 'value1');
      model._pendingChanges.set('key2', 'value2');
      
      model.completeInitialization();
      
      expect(mockWsManager.sendUpdate).toHaveBeenCalledTimes(2);
      expect(mockWsManager.sendUpdate).toHaveBeenCalledWith(
        'test-widget',
        'key1',
        'value1',
        expect.any(String)
      );
      expect(mockWsManager.sendUpdate).toHaveBeenCalledWith(
        'test-widget',
        'key2',
        'value2',
        expect.any(String)
      );
    });
  });
  
  describe('event handling', () => {
    it('should register and trigger callbacks', () => {
      const callback = jest.fn();
      model.on('testEvent', callback);
      
      model.trigger('testEvent', 'testData');
      
      expect(callback).toHaveBeenCalledWith('testData');
    });
    
    it('should allow removing specific callbacks', () => {
      const callback1 = jest.fn();
      const callback2 = jest.fn();
      
      model.on('testEvent', callback1);
      model.on('testEvent', callback2);
      
      model.off('testEvent', callback1);
      model.trigger('testEvent', 'testData');
      
      expect(callback1).not.toHaveBeenCalled();
      expect(callback2).toHaveBeenCalledWith('testData');
    });
    
    it('should remove all callbacks for an event when callback is not provided', () => {
      const callback1 = jest.fn();
      const callback2 = jest.fn();
      
      model.on('testEvent', callback1);
      model.on('testEvent', callback2);
      
      model.off('testEvent');
      model.trigger('testEvent', 'testData');
      
      expect(callback1).not.toHaveBeenCalled();
      expect(callback2).not.toHaveBeenCalled();
    });
    
    it('should remove all callbacks when event name is not provided', () => {
      const callback1 = jest.fn();
      const callback2 = jest.fn();
      
      model.on('testEvent1', callback1);
      model.on('testEvent2', callback2);
      
      model.off();
      model.trigger('testEvent1', 'testData');
      model.trigger('testEvent2', 'testData');
      
      expect(callback1).not.toHaveBeenCalled();
      expect(callback2).not.toHaveBeenCalled();
    });
  });
  
  describe('save_changes method', () => {
    it('should call completeInitialization if still initializing', () => {
      const spy = jest.spyOn(model, 'completeInitialization');
      
      model.save_changes();
      
      expect(spy).toHaveBeenCalled();
    });
    
    it('should not send updates if no properties have changed', () => {
      model._initializing = false;
      model._changedProperties.clear();
      
      model.save_changes();
      
      expect(mockWsManager.sendUpdate).not.toHaveBeenCalled();
      expect(mockWsManager.batchUpdate).not.toHaveBeenCalled();
    });
    
    it('should send batch update when multiple properties have changed', () => {
      model._initializing = false;
      model.data.key1 = 'value1';
      model.data.key2 = 'value2';
      model._changedProperties.add('key1');
      model._changedProperties.add('key2');
      
      model.save_changes();
      
      expect(mockWsManager.batchUpdate).toHaveBeenCalledWith(
        'test-widget',
        expect.objectContaining({
          key1: 'value1',
          key2: 'value2'
        }),
        expect.any(String)
      );
    });
    
    it('should clear changed properties after saving', () => {
      model._initializing = false;
      model.data.key1 = 'value1';
      model._changedProperties.add('key1');
      
      model.save_changes();
      
      expect(model._changedProperties.size).toBe(0);
    });
    
    it('should only send properties that differ from last synced values', () => {
      model._initializing = false;
      
      // Set up a property that was already synced with the same value
      model.data.key1 = 'value1';
      model._lastSyncedValues.key1 = 'value1';
      model._changedProperties.add('key1');
      
      // Set up a property that has a different value from last sync
      model.data.key2 = 'value2-new';
      model._lastSyncedValues.key2 = 'value2-old';
      model._changedProperties.add('key2');
      
      model.save_changes();
      
      // Since only key2 has a different value, only it should be sent
      expect(mockWsManager.sendUpdate).toHaveBeenCalledWith(
        'test-widget',
        'key2',
        'value2-new',
        expect.any(String)
      );
      expect(mockWsManager.sendUpdate).not.toHaveBeenCalledWith(
        expect.anything(),
        'key1',
        expect.anything(),
        expect.anything()
      );
    });
  });
  
  describe('confirmUpdate method', () => {
    it('should update lastSyncedValues and remove from pendingRequests when request matches', () => {
      const requestId = 'test-request-id';
      model._pendingRequests.set('testKey', requestId);
      
      model.confirmUpdate('testKey', 'testValue', requestId);
      
      expect(model._lastSyncedValues.testKey).toBe('testValue');
      expect(model._pendingRequests.has('testKey')).toBe(false);
    });
    
    it('should not update when request ID does not match', () => {
      model._pendingRequests.set('testKey', 'request-id-1');
      
      model.confirmUpdate('testKey', 'testValue', 'request-id-2');
      
      expect(model._lastSyncedValues.testKey).toBeUndefined();
      expect(model._pendingRequests.get('testKey')).toBe('request-id-1');
    });
  });
  
  describe('confirmBatchUpdate method', () => {
    it('should confirm multiple updates at once', () => {
      const requestId = 'batch-request-id';
      model._pendingRequests.set('key1', requestId);
      model._pendingRequests.set('key2', requestId);
      
      model.confirmBatchUpdate({
        key1: 'value1',
        key2: 'value2'
      }, requestId);
      
      expect(model._lastSyncedValues.key1).toBe('value1');
      expect(model._lastSyncedValues.key2).toBe('value2');
      expect(model._pendingRequests.has('key1')).toBe(false);
      expect(model._pendingRequests.has('key2')).toBe(false);
    });
  });
  
  describe('registerObservers method', () => {
    it('should register and execute the observer registration function', () => {
      const registerFn = jest.fn();
      
      model.registerObservers(registerFn);
      
      expect(registerFn).toHaveBeenCalled();
      expect(global.observerRegistrations.get('test-widget')).toBe(registerFn);
    });
  });
}); 