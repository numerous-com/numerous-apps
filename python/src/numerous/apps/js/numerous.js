// Add this at the top of the file
const USE_SHADOW_DOM = false;  // Set to true to enable Shadow DOM

// Create a Model class instead of a single model object
class WidgetModel {
    constructor(widgetId) {
        this.widgetId = widgetId;
        this.data = {};
        this._callbacks = {};
        this._suppressSync = false;
        console.log(`[WidgetModel] Created for widget ${widgetId}`);
    }
    
    set(key, value) {
        console.log(`[WidgetModel] Setting ${key}=${value} for widget ${this.widgetId}`);
        this.data[key] = value;
        console.log(`[WidgetModel] Triggering change:${key} event`);
        this.trigger('change:' + key, value);
        
        // Sync with server if not suppressed
        if (!this._suppressSync) {
            console.log(`[WidgetModel] Sending update to server`);
            wsManager.sendUpdate(this.widgetId, key, value);
        }
    }
    
    get(key) {
        return this.data[key];
    }
    
    save_changes() {
        console.log('Saving changes:', this.data);
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
        console.log(`[WidgetModel ${this.widgetId}] Triggering ${eventName} with data:`, data);
        if (this._callbacks[eventName]) {
            console.log(`[WidgetModel ${this.widgetId}] Found ${this._callbacks[eventName].length} callbacks for ${eventName}`);
            this._callbacks[eventName].forEach(callback => callback(data));
        } else {
            console.log(`[WidgetModel ${this.widgetId}] No callbacks found for ${eventName}`);
        }
    }

    send(content, callbacks, buffers) {
        console.log(`[WidgetModel ${this.widgetId}] Sending message:`, content);
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
        console.error(`Failed to load widget from ${moduleSource.substring(0, 100)}...:`, error);
        return null;
    }
}

// Function to fetch widget configurations from the server
async function fetchWidgetConfigs() {
    try {
        const response = await fetch('/api/widgets');
        return await response.json();
    } catch (error) {
        console.error('Failed to fetch widget configs:', error);
        return {};
    }
}

// Updated initialize widgets function to create individual models
async function initializeWidgets() {
    const widgetConfigs = await fetchWidgetConfigs();
    
    for (const [widgetId, config] of Object.entries(widgetConfigs)) {
        const container = document.getElementById(widgetId);
        if (!container) {
            console.warn(`Element with id ${widgetId} not found`);
            continue;
        }

        let element;
        // Add debug logging for Plotly detection
        console.log(`[Widget ${widgetId}] Module URL:`, config.moduleUrl);
        const isPlotlyWidget = config.moduleUrl?.toLowerCase().includes('plotly');
        console.log(`[Widget ${widgetId}] Is Plotly widget:`, isPlotlyWidget);
        
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
                console.log(`[WidgetModel ${widgetId}] Setting default value for ${key}=${value}`);
                widgetModel.set(key, value);
            }
            widgetModel.save_changes();
            
            try {
                // Render the widget with its own model inside the shadow DOM
                await widgetModule.default.render({
                    model: widgetModel,
                    el: element
                });
            } catch (error) {
                console.error(`Failed to render widget ${widgetId}:`, error);
            }
        }
    }
}

// Initialize widgets when the document is loaded
document.addEventListener('DOMContentLoaded', initializeWidgets); 

// Add WebSocket connection management
class WebSocketManager {
    constructor() {
        this.clientId = Math.random().toString(36).substr(2, 9);
        this.sessionId = document.cookie.split('; ')
            .find(row => row.startsWith('session_id='))
            ?.split('=')[1];
        console.log(`[WebSocketManager] Created with clientId ${this.clientId} and sessionId ${this.sessionId}`);
        this.connect();
        this.widgetModels = new Map();
    }

    connect() {
        console.log(`[WebSocketManager ${this.clientId}] Connecting to WebSocket...`);
        this.ws = new WebSocket(`ws://${window.location.host}/ws/${this.clientId}/${this.sessionId}`);
        
        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            console.log(`[WebSocketManager ${this.clientId}] Received message:`, message);
            
            const model = this.widgetModels.get(message.widget_id);
            if (model) {
                console.log(`[WebSocketManager ${this.clientId}] Found model for widget ${message.widget_id}`);
                // Update the model without triggering a send back to server
                model._suppressSync = true;
                model.set(message.property, message.value);
                model._suppressSync = false;
                
                // Trigger the general 'change' event
                console.log(`[WebSocketManager ${this.clientId}] Triggering general change event`);
                model.trigger('change', {
                    property: message.property,
                    value: message.value
                });
            } else {
                console.warn(`[WebSocketManager ${this.clientId}] No model found for widget ${message.widget_id}`);
            }
        };

        this.ws.onopen = () => {
            console.log(`[WebSocketManager] WebSocket connection established`);
        };

        this.ws.onclose = () => {
            console.log(`[WebSocketManager] WebSocket connection closed, attempting to reconnect...`);
            setTimeout(() => this.connect(), 1000);
        };

        this.ws.onerror = (error) => {
            console.error(`[WebSocketManager] WebSocket error:`, error);
        };
    }

    sendUpdate(widgetId, property, value) {
        if (this.ws.readyState === WebSocket.OPEN) {
            const message = {
                widget_id: widgetId,
                property: property,
                value: value
            };
            console.log(`[WebSocketManager] Sending update:`, message);
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn(`[WebSocketManager] Cannot send update - WebSocket not open`);
        }
    }
}

const wsManager = new WebSocketManager();