const USE_SHADOW_DOM = false;  // Set to false to avoid issues with Marked.js and other libraries
const LOG_LEVELS = {
    DEBUG: 0,
    INFO: 1,
    WARN: 2,
    ERROR: 3,
    NONE: 4
};
let currentLogLevel = LOG_LEVELS.ERROR; // Default log level

// Set debug level based on URL parameters
function initializeDebugging() {
    // Check for debug parameter in URL
    const urlParams = new URLSearchParams(window.location.search);
    const debugParam = urlParams.get('debug');
    
    if (debugParam === 'true' || debugParam === '1') {
        currentLogLevel = LOG_LEVELS.DEBUG;
        console.info('Debug logging enabled');
    }
    
    // Also check for localStorage debug preference
    try {
        const storedLevel = localStorage.getItem('numerousLogLevel');
        if (storedLevel && LOG_LEVELS[storedLevel] !== undefined) {
            currentLogLevel = LOG_LEVELS[storedLevel];
            console.info(`Log level set from localStorage: ${storedLevel}`);
        }
    } catch (e) {
        // Ignore localStorage errors
    }
}

// Initialize debugging
initializeDebugging();

// Add this logging utility function
function log(level, ...args) {
    if (level >= currentLogLevel) {
        switch (level) {
            case LOG_LEVELS.DEBUG:
                console.log(...args);
                break;
            case LOG_LEVELS.INFO:
                console.info(...args);
                break;
            case LOG_LEVELS.WARN:
                console.warn(...args);
                break;
            case LOG_LEVELS.ERROR:
                console.error(...args);
                break;
        }
    }
}

// Add MessageType enum at the top of the file
const MessageType = {
    WIDGET_UPDATE: 'widget-update',
    GET_STATE: 'get-state',
    GET_WIDGET_STATES: 'get-widget-states',
    ACTION_REQUEST: 'action-request',
    ACTION_RESPONSE: 'action-response',
    ERROR: 'error',
    INIT_CONFIG: 'init-config',
    SESSION_ERROR: 'session-error',
    WIDGET_BATCH_UPDATE: 'widget-batch-update'  // Add batch update type
};

// Add this near the top of the file, after MessageType definition
let observerRegistrations = new Map(); // Store observer registration functions

// Create a Model class instead of a single model object
class WidgetModel {
    constructor(widgetId) {
        this.widgetId = widgetId;
        this.data = {};
        this._callbacks = {};
        this._initializing = true; // Flag to indicate initial setup
        this._pendingChanges = new Map(); // Store changes that happen during initialization
        this._lastSyncedValues = {}; // Track last synced values
        this._changedProperties = new Set(); // Track properties that have changed since last sync
        this._pendingRequests = new Map(); // Track pending update requests by property
        this._lastRequestId = 0; // Counter for generating request IDs
        this._lockUpdates = false; // Lock for preventing overlapping batch operations
        log(LOG_LEVELS.DEBUG, `[WidgetModel] Created for widget ${widgetId}`);
    }
    
    // Generate a unique request ID for tracking updates
    _generateRequestId() {
        return `${this.widgetId}-${++this._lastRequestId}-${Date.now()}`;
    }
    
    set(key, value, suppressSync = false) {
        log(LOG_LEVELS.DEBUG, `[WidgetModel] Setting ${key}=${value} for widget ${this.widgetId}`);
        const oldValue = this.data[key];
        
        // Only trigger if value actually changed
        const valueChanged = oldValue !== value;
        
        // Always update the value
        this.data[key] = value;

        // Check if this is a form control property like 'val', 'checked', etc.
        const isFormControl = ['val', 'checked', 'value', 'selected'].includes(key);

        // Trigger change event if the value changed
        if (valueChanged) {
            log(LOG_LEVELS.DEBUG, `[WidgetModel] Value changed, triggering event for ${key}`);
            this.trigger('change:' + key, value);
            // Also trigger a general change event
            this.trigger('change', { key, value, oldValue });
            
            // Mark property as changed for batching
            this._changedProperties.add(key);
            
            // For form controls, ensure a more aggressive event triggering to handle checkbox issues
            if (isFormControl) {
                // Use setTimeout to ensure DOM is updated before triggering another event
                setTimeout(() => {
                    this.trigger('change:' + key, value); 
                    this.trigger('change', { key, value, oldValue });
                }, 0);
            }
        } else {
            log(LOG_LEVELS.DEBUG, `[WidgetModel] Value unchanged for ${key}`);
        }
        
        // Sync with server if not suppressed
        if (!suppressSync && !this._suppressSync && !this._lockUpdates) {
            log(LOG_LEVELS.DEBUG, `[WidgetModel] Sending update to server for ${key}=${value}`);
            if (typeof wsManager !== 'undefined' && wsManager) {
                // Generate request ID for tracking this update
                const requestId = this._generateRequestId();
                this._pendingRequests.set(key, requestId);
                
                wsManager.sendUpdate(this.widgetId, key, value, requestId);
                // Update last synced value - only when confirmed by server
                // this._lastSyncedValues[key] = value;
            } else {
                log(LOG_LEVELS.WARN, `[WidgetModel] Cannot send update - wsManager is not defined`);
            }
        } else if (this._initializing && !suppressSync) {
            // If we're initializing and change isn't suppressed, store for later sync
            log(LOG_LEVELS.DEBUG, `[WidgetModel] Queuing change for later: ${key}=${value}`);
            this._pendingChanges.set(key, value);
        } else {
            log(LOG_LEVELS.DEBUG, `[WidgetModel] Skipping server sync for ${key}=${value} (suppressSync=${suppressSync}, _suppressSync=${this._suppressSync}, _lockUpdates=${this._lockUpdates})`);
        }
    }
    
    // Mark initialization complete and send any pending changes
    completeInitialization() {
        if (!this._initializing) return;
        
        log(LOG_LEVELS.DEBUG, `[WidgetModel ${this.widgetId}] Completing initialization, processing ${this._pendingChanges.size} pending changes`);
        this._initializing = false;
        
        if (this._pendingChanges.size > 0) {
            // Create a batch update for pending changes
            const batchData = {};
            for (const [key, value] of this._pendingChanges.entries()) {
                batchData[key] = value;
                this._lastSyncedValues[key] = value;
            }
            
            // Send batch update if we have multiple changes
            if (Object.keys(batchData).length > 1 && typeof wsManager !== 'undefined' && wsManager.batchUpdate) {
                const batchRequestId = this._generateRequestId();
                // Track all properties in this batch with the same request ID
                for (const key of Object.keys(batchData)) {
                    this._pendingRequests.set(key, batchRequestId);
                }
                wsManager.batchUpdate(this.widgetId, batchData, batchRequestId);
            } else {
                // Fall back to individual updates
                for (const [key, value] of this._pendingChanges.entries()) {
                    const requestId = this._generateRequestId();
                    this._pendingRequests.set(key, requestId);
                    wsManager.sendUpdate(this.widgetId, key, value, requestId);
                }
            }
        }
        
        this._pendingChanges.clear();
        this._changedProperties.clear();
    }
    
    // Handle update confirmation from server
    confirmUpdate(key, value, requestId) {
        // Check if this is the most recent request for this property
        if (this._pendingRequests.get(key) === requestId) {
            // Update the last synced value
            this._lastSyncedValues[key] = value;
            // Remove from pending requests
            this._pendingRequests.delete(key);
            log(LOG_LEVELS.DEBUG, `[WidgetModel ${this.widgetId}] Confirmed update for ${key} (request ${requestId})`);
        } else {
            log(LOG_LEVELS.DEBUG, `[WidgetModel ${this.widgetId}] Ignoring outdated confirmation for ${key} (request ${requestId})`);
        }
    }
    
    // Confirm a batch update
    confirmBatchUpdate(properties, requestId) {
        for (const [key, value] of Object.entries(properties)) {
            this.confirmUpdate(key, value, requestId);
        }
    }
    
    get(key) {
        return this.data[key];
    }
    
    save_changes() {
        log(LOG_LEVELS.DEBUG, `[WidgetModel ${this.widgetId}] Saving changes`);
        
        // If we're still initializing, mark initialization as complete
        if (this._initializing) {
            this.completeInitialization();
            return;
        }
        
        // Check if we have any changed properties that need syncing
        if (this._changedProperties.size > 0) {
            // Set lock to prevent individual updates during batch operation
            this._lockUpdates = true;
            
            try {
                log(LOG_LEVELS.DEBUG, `[WidgetModel ${this.widgetId}] Found ${this._changedProperties.size} changed properties to sync`);
                
                // Prepare batch update if supported
                const changedData = {};
                let changesDetected = false;
                
                // Only send values that have changed since last sync
                for (const key of this._changedProperties) {
                    const value = this.data[key];
                    // Double check if it actually differs from last synced value
                    if (this._lastSyncedValues[key] !== value) {
                        changedData[key] = value;
                        changesDetected = true;
                    }
                }
                
                if (changesDetected) {
                    // Use batch update for efficiency when multiple properties are changed
                    if (Object.keys(changedData).length > 1 && typeof wsManager !== 'undefined' && wsManager.batchUpdate) {
                        const batchRequestId = this._generateRequestId();
                        // Track all properties in this batch with the same request ID
                        for (const key of Object.keys(changedData)) {
                            this._pendingRequests.set(key, batchRequestId);
                        }
                        wsManager.batchUpdate(this.widgetId, changedData, batchRequestId);
                    } else {
                        // Fall back to individual updates for compatibility or single property changes
                        for (const [key, value] of Object.entries(changedData)) {
                            const requestId = this._generateRequestId();
                            this._pendingRequests.set(key, requestId);
                            wsManager.sendUpdate(this.widgetId, key, value, requestId);
                        }
                    }
                } else {
                    log(LOG_LEVELS.DEBUG, `[WidgetModel ${this.widgetId}] No actual changes to sync after checking`);
                }
            } finally {
                // Clear changed properties after sync
                this._changedProperties.clear();
                // Release the lock
                this._lockUpdates = false;
            }
        } else {
            log(LOG_LEVELS.DEBUG, `[WidgetModel ${this.widgetId}] No changed properties to sync`);
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
        log(LOG_LEVELS.DEBUG, `[WidgetModel ${this.widgetId}] Triggering ${eventName} with data:`, data);
        if (this._callbacks[eventName]) {
            log(LOG_LEVELS.DEBUG, `[WidgetModel ${this.widgetId}] Found ${this._callbacks[eventName].length} callbacks for ${eventName}`);
            this._callbacks[eventName].forEach(callback => callback(data));
        } else {
            log(LOG_LEVELS.DEBUG, `[WidgetModel ${this.widgetId}] No callbacks found for ${eventName}`);
        }
    }

    send(content, callbacks, buffers) {
        log(LOG_LEVELS.DEBUG, `[WidgetModel ${this.widgetId}] Sending message:`, content);
        // Implement message sending if needed
    }

    // Add a method to WidgetModel to register observers in a way they can be re-registered later
    registerObservers(registerFn) {
        observerRegistrations.set(this.widgetId, registerFn);
        // Execute the registration function now
        registerFn();
        log(LOG_LEVELS.DEBUG, `[WidgetModel ${this.widgetId}] Registered observers with re-registration capability`);
    }
}

// Create a function to dynamically load ESM modules
async function loadWidget(moduleSource) {
    try {
        // Check if the source is a URL or a JavaScript string
        if (moduleSource.startsWith('http') || moduleSource.startsWith('./') || moduleSource.startsWith('/')) {
            return await import(moduleSource);
        } else {
            // Create a Blob with the JavaScript code
            const blob = new Blob([moduleSource], { type: 'text/javascript' });
            const blobUrl = URL.createObjectURL(blob);
            
            // Import the blob URL and then clean it up
            const module = await import(blobUrl);
            URL.revokeObjectURL(blobUrl);
            
            return module;
        }
    } catch (error) {
        log(LOG_LEVELS.ERROR, `Failed to load widget from ${moduleSource.substring(0, 100)}...:`, error);
        return null;
    }
}
var wsManager;
// Function to fetch widget configurations and states from the server
async function fetchWidgetConfigs() {
    try {
        console.log("Fetching widget configs and states");

        let sessionId = sessionStorage.getItem('session_id');
        const response = await fetch(`/api/widgets?session_id=${sessionId}`);
        const data = await response.json();

        sessionStorage.setItem('session_id', data.session_id);
        sessionId = data.session_id;

        wsManager = new WebSocketManager(sessionId);
        
        // Set log level if provided in the response
        if (data.logLevel !== undefined) {
            currentLogLevel = LOG_LEVELS[data.logLevel] ?? LOG_LEVELS.INFO;
            log(LOG_LEVELS.INFO, `Log level set to: ${data.logLevel}`);
        }
        
        return data.widgets; 
    } catch (error) {
        log(LOG_LEVELS.ERROR, 'Failed to fetch widget configs:', error);
        return {};
    }
}

// Add these near the top with other state variables
let renderedWidgets = 0;
let totalWidgets = 0;
let statesReceived = false;

// Add this function to handle manual dismissal
function dismissLoadingOverlay() {
    const splashScreen = document.getElementById('splash-screen');
    if (splashScreen) {
        splashScreen.classList.add('hidden');
        // Remove from DOM after transition
        setTimeout(() => {
            splashScreen.remove();
        }, 300);
    }
}

// Modify checkAllWidgetsReady to add a minimum display time
let loadingStartTime = Date.now();
const MIN_LOADING_TIME = 1000; // Minimum time to show loading overlay (1 second)

// Modify the initializeWidgets function
async function initializeWidgets() {
    console.log("Initializing widgets");
    loadingStartTime = Date.now();
    const widgetConfigs = await fetchWidgetConfigs();
    
    // Reset tracking variables
    totalWidgets = Object.keys(widgetConfigs).length;
    renderedWidgets = 0;
    statesReceived = false;
    
    // Wait for WebSocket connection to be established before initializing widgets
    await wsManager.connectionReady();
    log(LOG_LEVELS.INFO, "WebSocket connection ready, initializing widgets");
    
    const widgetModels = new Map();
    
    // First phase: Create all models and set default values
    for (const [widgetId, config] of Object.entries(widgetConfigs)) {
        // Create a new model instance for this widget
        const widgetModel = new WidgetModel(widgetId);
        
        // Store in our local map and the WebSocket manager
        widgetModels.set(widgetId, widgetModel);
        wsManager.widgetModels.set(widgetId, widgetModel);
        
        // Initialize default values for this widget
        for (const [key, value] of Object.entries(config.defaults || {})) {
            if (!widgetModel.get(key)) {    
                log(LOG_LEVELS.DEBUG, `[WidgetModel ${widgetId}] Setting default value for ${key}=${value}`);
                widgetModel.set(key, value, true); // Suppress sync during initialization
            }
        }
    }
    
    // Second phase: Render all widgets
    for (const [widgetId, config] of Object.entries(widgetConfigs)) {
        const container = document.getElementById(widgetId);
        if (!container) {
            log(LOG_LEVELS.WARN, `Element with id ${widgetId} not found`);
            renderedWidgets++; // Count failed widgets to maintain accurate tracking
            continue;
        }

        let element;
        const isPlotlyWidget = config.moduleUrl?.toLowerCase().includes('plotly');
        
        if (USE_SHADOW_DOM && !isPlotlyWidget) {
            // Use Shadow DOM for non-Plotly widgets
            const shadowRoot = container.attachShadow({ mode: 'open' });
            
            if (config.css) {
                const styleElement = document.createElement('style');
                styleElement.textContent = config.css;
                shadowRoot.appendChild(styleElement);
            }
            
            element = document.createElement('div');
            element.id = widgetId;
            element.classList.add('widget-wrapper');
            shadowRoot.appendChild(element);
        } else {
            // Use regular DOM for Plotly widgets or when Shadow DOM is disabled
            element = container;
            if (config.css) {
                const styleElement = document.createElement('style');
                styleElement.textContent = config.css;
                document.head.appendChild(styleElement);
            }
        }

        const widgetModel = widgetModels.get(widgetId);
        const widgetModule = await loadWidget(config.moduleUrl);
        
        if (widgetModule && widgetModel) {
            try {
                // Render the widget with its model
                await widgetModule.default.render({
                    model: widgetModel,
                    el: element
                });
                
                log(LOG_LEVELS.DEBUG, `Widget ${widgetId} rendered successfully`);
            } catch (error) {
                log(LOG_LEVELS.ERROR, `Failed to render widget ${widgetId}:`, error);
            }
        }
    }
    
    // Third phase: Complete initialization for all models to send pending changes
    log(LOG_LEVELS.INFO, "All widgets rendered, completing initialization");
    for (const widgetModel of widgetModels.values()) {
        widgetModel.completeInitialization();
    }

    dismissLoadingOverlay();
}

// Initialize widgets when the document is loaded
document.addEventListener('DOMContentLoaded', initializeWidgets); 

// Expose our refresh functions to the window object for external use
window.numerousRefresh = {
    refreshWidget: refreshWidgetState,
    
    // Function to re-register observers for a specific widget
    reregisterObservers: function(widgetId) {
        if (widgetId && observerRegistrations.has(widgetId)) {
            log(LOG_LEVELS.INFO, `Manually re-registering observers for widget ${widgetId}`);
            observerRegistrations.get(widgetId)();
            return true;
        } else if (!widgetId) {
            // Re-register all observers
            log(LOG_LEVELS.INFO, "Re-registering all observers");
            let count = 0;
            for (const [widgetId, registerFn] of observerRegistrations.entries()) {
                registerFn();
                count++;
            }
            return count > 0;
        }
        return false;
    },
    
    // Force full reload of widget data from server
    reloadWidgetData: function(widgetId) {
        log(LOG_LEVELS.INFO, `Forcing reload of data for widget ${widgetId || 'all'}`);
        return refreshWidgetState(widgetId);
    }
};

// Add WebSocket connection management
class WebSocketManager {
    constructor(sessionId) {
        this.clientId = Math.random().toString(36).substr(2, 9);
        this.sessionId = sessionId;
        this.widgetModels = new Map();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.messageQueue = [];
        
        // Create a promise to track connection state
        this.connectionPromise = new Promise((resolve) => {
            this.resolveConnection = resolve;
        });
        
        log(LOG_LEVELS.INFO, `[WebSocketManager] Created with clientId ${this.clientId} and sessionId ${this.sessionId}`);
        this.connect();
    }

    showErrorModal(message) {
        const modal = document.getElementById('error-modal');
        const messageElement = document.getElementById('error-modal-message');
        messageElement.textContent = message;
        modal.style.display = 'block';
    }

    showSessionLostBanner() {
        const banner = document.getElementById('session-lost-banner');
        log(LOG_LEVELS.DEBUG, `[WebSocketManager] Banner element exists: ${!!banner}`);
        if (banner) {
            banner.classList.remove('hidden');
            log(LOG_LEVELS.DEBUG, `[WebSocketManager] Banner classes after show: ${banner.className}`);
        } else {
            log(LOG_LEVELS.ERROR, `[WebSocketManager] Session lost banner element not found in DOM`);
        }
    }

    connect() {
        log(LOG_LEVELS.DEBUG, `[WebSocketManager ${this.clientId}] Connecting to WebSocket...`);
        
        // Create new connection promise for this connection attempt
        this.connectionPromise = new Promise((resolve) => {
            this.resolveConnection = resolve;
        });
        
        // Update connection status
        this.updateConnectionStatus('Connecting to server...');
        
        // Determine protocol (ws or wss)
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${window.location.host}/ws/${this.clientId}/${this.sessionId}`;
        
        // Create WebSocket
        this.ws = new WebSocket(url);
        
        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                log(LOG_LEVELS.DEBUG, `[WebSocketManager ${this.clientId}] Received message:`, message);
                
                // Process message based on type
                if (message && message.type) {
                    switch (message.type) {
                        case MessageType.SESSION_ERROR:
                            log(LOG_LEVELS.INFO, `[WebSocketManager ${this.clientId}] Session error received`);
                            this.showSessionLostBanner();
                            
                            // Don't attempt to reconnect on session errors
                            this.reconnectAttempts = this.maxReconnectAttempts;
                            
                            // Hide the connection status overlay since this is a session error
                            const connectionStatus = document.getElementById('connection-status');
                            if (connectionStatus) {
                                connectionStatus.classList.add('hidden');
                            }
                            break;

                        case 'widget-update':
                            // Handle widget updates from both actions and direct changes
                            const model = this.widgetModels.get(message.widget_id);
                            if (model) {
                                log(LOG_LEVELS.INFO, `[WebSocketManager ${this.clientId}] Updating widget ${message.widget_id}: ${message.property} = ${message.value}`);
                                
                                // Set a flag to prevent recursive updates
                                model._suppressSync = true;
                                try {
                                    // Update the model without triggering a send back to server
                                    model.set(message.property, message.value, true);
                                    
                                    // Confirm the update if this is a response to our request
                                    if (message.request_id) {
                                        model.confirmUpdate(message.property, message.value, message.request_id);
                                    }
                                    
                                    // Also trigger a general update event that widgets can listen to
                                    model.trigger('update', {
                                        property: message.property,
                                        value: message.value,
                                        request_id: message.request_id
                                    });
                                    
                                    // Special handling for checkbox and form elements which often lose observers
                                    // This improves reliability of checkboxes like GDPR consent buttons
                                    const isFormElement = ['val', 'checked', 'value', 'selected'].includes(message.property);
                                    
                                    // Call any registered observer setup functions for this widget
                                    if (observerRegistrations.has(message.widget_id)) {
                                        if (isFormElement) {
                                            log(LOG_LEVELS.DEBUG, `Re-registering observers for form element ${message.widget_id}.${message.property}`);
                                            // Use setTimeout to ensure the DOM is updated before re-registering
                                            setTimeout(() => {
                                                observerRegistrations.get(message.widget_id)();
                                            }, 0);
                                        } else {
                                            log(LOG_LEVELS.DEBUG, `Re-registering observers for widget ${message.widget_id}`);
                                            observerRegistrations.get(message.widget_id)();
                                        }
                                    }
                                } finally {
                                    // Always remove the flag
                                    model._suppressSync = false;
                                }
                            } else {
                                log(LOG_LEVELS.WARN, `[WebSocketManager ${this.clientId}] Received update for unknown widget: ${message.widget_id}`);
                                // Dump the current widget models for debugging
                                log(LOG_LEVELS.DEBUG, "Current widget models:", 
                                    Array.from(this.widgetModels.keys()));
                            }
                            break;

                        case MessageType.WIDGET_BATCH_UPDATE:
                            // Handle batch update responses
                            const batchModel = this.widgetModels.get(message.widget_id);
                            if (batchModel) {
                                log(LOG_LEVELS.INFO, `[WebSocketManager ${this.clientId}] Received batch update confirmation for ${message.widget_id}`);
                                
                                // Confirm all properties in the batch
                                if (message.request_id && message.properties) {
                                    batchModel.confirmBatchUpdate(message.properties, message.request_id);
                                }
                            }
                            break;

                        case 'init-config':
                            log(LOG_LEVELS.INFO, `[WebSocketManager ${this.clientId}] Received init config`);
                            // When we get a full config, we may need to re-register observers for all widgets
                            for (const widgetId of observerRegistrations.keys()) {
                                const registerFn = observerRegistrations.get(widgetId);
                                if (registerFn) {
                                    log(LOG_LEVELS.DEBUG, `Re-registering observers for widget ${widgetId} after init-config`);
                                    registerFn();
                                }
                            }
                            break;

                        case 'error':
                            log(LOG_LEVELS.ERROR, `[WebSocketManager ${this.clientId}] Error from backend:`, message);
                            this.showErrorModal(message.error || 'Unknown error occurred');
                            break;

                        default:
                            log(LOG_LEVELS.DEBUG, `[WebSocketManager ${this.clientId}] Unhandled message type: ${message.type}`);
                    }
                }
            } catch (error) {
                log(LOG_LEVELS.ERROR, `[WebSocketManager ${this.clientId}] Error processing message:`, error, "Raw data:", event.data);
            }
        };

        this.ws.onopen = () => {
            log(LOG_LEVELS.INFO, `[WebSocketManager] WebSocket connection established`);
            this.hideConnectionStatus();
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000; // Reset delay on successful connection
            
            // Add a small delay before requesting widget states to ensure server is ready
            setTimeout(() => {
                // Request all widget states after connection is fully established
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(JSON.stringify({
                        type: 'get-widget-states',
                        client_id: this.clientId
                    }));
                    
                    // Process any queued messages
                    this.flushMessageQueue();
                }
                
                // Resolve the connection promise to indicate the connection is ready
                this.resolveConnection();
            }, 100); // Short delay to ensure server connection is ready
        };

        this.ws.onclose = (event) => {
            log(LOG_LEVELS.INFO, `[WebSocketManager ${this.clientId}] WebSocket connection closed`);
            
            // Only show connection status if it's not a session error
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.showConnectionStatus();
                this.reconnectAttempts++;
                setTimeout(() => this.connect(), this.reconnectDelay);
                this.reconnectDelay *= 2;
            }
        };

        this.ws.onerror = (error) => {
            log(LOG_LEVELS.ERROR, `[WebSocketManager ${this.clientId}] WebSocket error:`, error);
            // Only show connection status for non-session errors
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.showConnectionStatus();
            }
        };
    }

    // Method to wait for connection to be established
    async connectionReady() {
        return this.connectionPromise;
    }
    
    // Send all queued messages once connection is established
    flushMessageQueue() {
        if (this.messageQueue.length === 0) return;
        
        log(LOG_LEVELS.DEBUG, `[WebSocketManager] Sending ${this.messageQueue.length} queued messages`);
        
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            this.ws.send(JSON.stringify(message));
        }
    }

    sendUpdate(widgetId, property, value, requestId) {
        const message = {
            type: "widget-update",
            widget_id: widgetId,
            property: property,
            value: value,
            request_id: requestId
        };
        
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            log(LOG_LEVELS.DEBUG, `[WebSocketManager] Sending update:`, message);
            this.ws.send(JSON.stringify(message));
        } else {
            log(LOG_LEVELS.DEBUG, `[WebSocketManager] Queuing update message for later:`, message);
            this.messageQueue.push(message);
        }
    }

    // Add batch update method for more efficient updates
    batchUpdate(widgetId, properties, requestId) {
        // If no properties to update, skip
        if (!properties || Object.keys(properties).length === 0) {
            log(LOG_LEVELS.DEBUG, `[WebSocketManager] No properties to batch update for ${widgetId}`);
            return;
        }
        
        log(LOG_LEVELS.INFO, `[WebSocketManager] Batch updating ${Object.keys(properties).length} properties for widget ${widgetId}`);
        
        // Create a batch update message
        const message = {
            type: "widget-batch-update",
            widget_id: widgetId,
            properties: properties,
            request_id: requestId
        };
        
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            log(LOG_LEVELS.DEBUG, `[WebSocketManager] Sending batch update:`, message);
            this.ws.send(JSON.stringify(message));
        } else {
            log(LOG_LEVELS.DEBUG, `[WebSocketManager] Queuing batch update message for later:`, message);
            this.messageQueue.push(message);
        }
    }

    showConnectionStatus() {
        const statusOverlay = document.getElementById('connection-status');
        if (statusOverlay) {
            statusOverlay.classList.remove('hidden');
        }
    }

    hideConnectionStatus() {
        const statusOverlay = document.getElementById('connection-status');
        if (statusOverlay) {
            statusOverlay.classList.add('hidden');
        }
    }

    updateConnectionStatus(message) {
        const statusOverlay = document.getElementById('connection-status');
        if (statusOverlay) {
            const messageElement = statusOverlay.querySelector('.loading-content div:last-child');
            if (messageElement) {
                messageElement.textContent = message;
            }
        }
    }

    // Add to WebSocketManager class
    sendMessage(message) {
        message.client_id = this.clientId;
        
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            log(LOG_LEVELS.DEBUG, `[WebSocketManager] Sending message:`, message);
            this.ws.send(JSON.stringify(message));
        } else {
            log(LOG_LEVELS.DEBUG, `[WebSocketManager] Queuing message for later:`, message);
            this.messageQueue.push(message);
        }
    }
}

// Add this function to refresh widget state from the server
async function refreshWidgetState(widgetId) {
    if (!wsManager || !wsManager.sessionId) {
        log(LOG_LEVELS.ERROR, "Cannot refresh widget state: no active session");
        return;
    }
    
    log(LOG_LEVELS.INFO, `Requesting refresh for widget ${widgetId}`);
    
    // If widgetId is provided, refresh just that widget
    if (widgetId) {
        wsManager.sendMessage({
            type: "get-widget-state",
            widget_id: widgetId
        });
    } else {
        // Otherwise, refresh all widgets
        wsManager.sendMessage({
            type: "get-widget-states"
        });
    }
}

