const USE_SHADOW_DOM = false;  // Set to true to enable Shadow DOM
const LOG_LEVELS = {
    DEBUG: 0,
    INFO: 1,
    WARN: 2,
    ERROR: 3,
    NONE: 4
};
let currentLogLevel = LOG_LEVELS.DEBUG; // Default log level

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

// Create a Model class instead of a single model object
class WidgetModel {
    constructor(widgetId) {
        this.widgetId = widgetId;
        this.data = {};
        this._callbacks = {};
        log(LOG_LEVELS.DEBUG, `[WidgetModel] Created for widget ${widgetId}`);
    }
    
    set(key, value, suppressSync = false) {
        log(LOG_LEVELS.DEBUG, `[WidgetModel] Setting ${key}=${value} for widget ${this.widgetId}`);
        this.data[key] = value;

        this.trigger('change:' + key, value);
        
        // Sync with server if not suppressed
        if (!suppressSync && !this._suppressSync) {
            log(LOG_LEVELS.DEBUG, `[WidgetModel] Sending update to server`);
            wsManager.sendUpdate(this.widgetId, key, value);
        }
    }
    
    get(key) {
        return this.data[key];
    }
    
    save_changes() {
        log('Saving changes:', this.data);
        for (const [key, value] of Object.entries(this.data)) {
            
            //console.log(`[WidgetModel] Saving change: ${key}=${value}`);
            //wsManager.sendUpdate(this.widgetId, key, value);
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
// Function to fetch widget configurations from the server
async function fetchWidgetConfigs() {
    try {
        console.log("Fetching widget configs");

        let sessionId = sessionStorage.getItem('session_id');
        const response = await fetch(`/api/widgets?session_id=${sessionId}`);

        const data = await response.json();
        console.log("Data:", data);
        
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

// Updated initialize widgets function to create individual models
async function initializeWidgets() {
    console.log("Initializing widgets");
    const widgetConfigs = await fetchWidgetConfigs();
    
    for (const [widgetId, config] of Object.entries(widgetConfigs)) {
        const container = document.getElementById(widgetId);
        if (!container) {
            log(LOG_LEVELS.WARN, `Element with id ${widgetId} not found`);
            continue;
        }

        let element;
        // Add debug logging for Plotly detection
        // log(LOG_LEVELS.DEBUG, `[Widget ${widgetId}] Module URL:`, config.moduleUrl);
        const isPlotlyWidget = config.moduleUrl?.toLowerCase().includes('plotly');
        // log(LOG_LEVELS.DEBUG, `[Widget ${widgetId}] Is Plotly widget:`, isPlotlyWidget);
        
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

        const widgetModule = await loadWidget(config.moduleUrl);
        if (widgetModule) {
            // Create a new model instance for this widget
            const widgetModel = new WidgetModel(widgetId);
            
            // Store the model in the WebSocket manager
            wsManager.widgetModels.set(widgetId, widgetModel);

            // Initialize default values for this widget
            for (const [key, value] of Object.entries(config.defaults || {})) {
                if (!widgetModel.get(key)) {    
                    log(LOG_LEVELS.DEBUG, `[WidgetModel ${widgetId}] Setting default value for ${key}=${value}`);
                    widgetModel.set(key, value, true);
                }
            }
            // widgetModel.save_changes();
            
            try {
                // Render the widget with its own model inside the shadow DOM
                await widgetModule.default.render({
                    model: widgetModel,
                    el: element
                });
            } catch (error) {
                log(LOG_LEVELS.ERROR, `Failed to render widget ${widgetId}:`, error);
            }
        }
    }
}

// Initialize widgets when the document is loaded
document.addEventListener('DOMContentLoaded', initializeWidgets); 

// Add WebSocket connection management
class WebSocketManager {
    constructor(sessionId) {
        this.clientId = Math.random().toString(36).substr(2, 9);
        this.sessionId = sessionId;
        
            
        log(LOG_LEVELS.INFO, `[WebSocketManager] Created with clientId ${this.clientId} and sessionId ${this.sessionId}`);
        this.connect();
        this.widgetModels = new Map();
    }

    showErrorModal(message) {
        const modal = document.getElementById('error-modal');
        const messageElement = document.getElementById('error-modal-message');
        messageElement.textContent = message;
        modal.style.display = 'block';
    }

    connect() {
        log(LOG_LEVELS.DEBUG, `[WebSocketManager ${this.clientId}] Connecting to WebSocket...`);
        // Detect if is secure  
        const isSecure = window.location.protocol === 'https:';
        const wsProtocol = isSecure ? 'wss:' : 'ws:';
        this.ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/${this.clientId}/${this.sessionId}`);
        
        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            log(LOG_LEVELS.DEBUG, `[WebSocketManager ${this.clientId}] Received message:`, message);
            
            if (message.type === 'error') {
                log(LOG_LEVELS.ERROR, `[WebSocketManager ${this.clientId}] Error from backend:`, message);
                const errorMessage = `Error: ${message.error_type}\n${message.message}\n\nTraceback:\n${message.traceback || 'No traceback available'}`;
                this.showErrorModal(errorMessage);
                return;
            }
            
            const model = this.widgetModels.get(message.widget_id);
            if (model) {
                log(LOG_LEVELS.DEBUG, `[WebSocketManager ${this.clientId}] Found model for widget ${message.widget_id}`);
                // Update the model without triggering a send back to server
                
                model.set(message.property, message.value, true);
                
                // Trigger the general 'change' event
                //log(LOG_LEVELS.DEBUG, `[WebSocketManager ${this.clientId}] Triggering general change event`);
                //model.trigger('change', {
                //    property: message.property,
                //    value: message.value
                //});
            } else {
                log(LOG_LEVELS.WARN, `[WebSocketManager ${this.clientId}] No model found for widget ${message.widget_id}`);
            }
        };

        this.ws.onopen = () => {
            log(LOG_LEVELS.INFO, `[WebSocketManager] WebSocket connection established`);
            this.ws.send(JSON.stringify({type: 'get_widget_states', client_id: this.clientId}));
        };

        this.ws.onclose = () => {
            log(LOG_LEVELS.INFO, `[WebSocketManager] WebSocket connection closed, attempting to reconnect...`);
            setTimeout(() => this.connect(), 1000);
        };

        this.ws.onerror = (error) => {
            log(LOG_LEVELS.ERROR, `[WebSocketManager] WebSocket error:`, error);
        };
    }

    sendUpdate(widgetId, property, value) {
        if (this.ws.readyState === WebSocket.OPEN) {
            const message = {
                widget_id: widgetId,
                property: property,
                value: value
            };
            log(LOG_LEVELS.DEBUG, `[WebSocketManager] Sending update:`, message);
            this.ws.send(JSON.stringify(message));
        } else {
            log(LOG_LEVELS.WARN, `[WebSocketManager] Cannot send update - WebSocket not open`);
        }
    }
}

