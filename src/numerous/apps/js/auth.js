/**
 * Authentication module for Numerous Apps
 * 
 * Handles:
 * - Access token storage (localStorage)
 * - Refresh token flow (via httpOnly cookie)
 * - Auto-refresh before expiry
 * - User context for app developers
 */

class AuthManager {
    constructor() {
        this.accessToken = localStorage.getItem('access_token');
        this.user = this._loadUser();
        this.tokenExpiresAt = null;
        this.refreshTimer = null;
        
        // Try to parse token expiry from JWT
        if (this.accessToken) {
            this._scheduleRefresh();
        }
    }
    
    /**
     * Load user from localStorage
     */
    _loadUser() {
        const userJson = localStorage.getItem('user');
        if (userJson) {
            try {
                return JSON.parse(userJson);
            } catch (e) {
                return null;
            }
        }
        return null;
    }
    
    /**
     * Parse JWT payload (without verification)
     */
    _parseJwt(token) {
        try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(
                atob(base64).split('').map(c => 
                    '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
                ).join('')
            );
            return JSON.parse(jsonPayload);
        } catch (e) {
            return null;
        }
    }
    
    /**
     * Check if user is authenticated
     */
    isAuthenticated() {
        return !!this.accessToken && !!this.user;
    }
    
    /**
     * Get the current user context (for app developers)
     */
    getUserContext() {
        if (!this.isAuthenticated()) {
            return {
                authenticated: false,
                username: null,
                user_id: null,
                roles: [],
                is_admin: false
            };
        }
        
        return {
            authenticated: true,
            username: this.user.username,
            user_id: this.user.id,
            roles: this.user.roles || [],
            is_admin: this.user.is_admin || false
        };
    }
    
    /**
     * Login with username and password
     */
    async login(username, password) {
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password }),
                credentials: 'include', // Include cookies for refresh token
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Login failed');
            }
            
            const data = await response.json();
            
            // Store access token and user
            this.accessToken = data.access_token;
            this.user = data.user;
            
            localStorage.setItem('access_token', data.access_token);
            localStorage.setItem('user', JSON.stringify(data.user));
            
            // Schedule token refresh
            this._scheduleRefresh(data.expires_in);
            
            return { success: true, user: data.user };
        } catch (error) {
            console.error('Login error:', error);
            return { success: false, error: error.message };
        }
    }
    
    /**
     * Refresh the access token using refresh token cookie
     */
    async refreshToken() {
        try {
            const response = await fetch('/api/auth/refresh', {
                method: 'POST',
                credentials: 'include', // Include refresh token cookie
            });
            
            if (!response.ok) {
                // Refresh failed - clear auth state
                this._clearAuth();
                return false;
            }
            
            const data = await response.json();
            
            // Update access token
            this.accessToken = data.access_token;
            localStorage.setItem('access_token', data.access_token);
            
            // Schedule next refresh
            this._scheduleRefresh(data.expires_in);
            
            return true;
        } catch (error) {
            console.error('Token refresh error:', error);
            this._clearAuth();
            return false;
        }
    }
    
    /**
     * Logout - revoke tokens and clear state
     */
    async logout() {
        try {
            await fetch('/api/auth/logout', {
                method: 'POST',
                credentials: 'include',
            });
        } catch (error) {
            console.error('Logout error:', error);
        }
        
        this._clearAuth();
        window.location.href = '/login';
    }
    
    /**
     * Clear all auth state
     */
    _clearAuth() {
        this.accessToken = null;
        this.user = null;
        this.tokenExpiresAt = null;
        
        if (this.refreshTimer) {
            clearTimeout(this.refreshTimer);
            this.refreshTimer = null;
        }
        
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
    }
    
    /**
     * Schedule token refresh before expiry
     */
    _scheduleRefresh(expiresInSeconds = null) {
        // Clear existing timer
        if (this.refreshTimer) {
            clearTimeout(this.refreshTimer);
        }
        
        // Calculate refresh time
        let refreshIn;
        
        if (expiresInSeconds) {
            // Refresh 1 minute before expiry, or at 80% of lifetime
            refreshIn = Math.max(
                (expiresInSeconds * 1000) - 60000,
                (expiresInSeconds * 1000) * 0.8
            );
        } else if (this.accessToken) {
            // Try to get expiry from token
            const payload = this._parseJwt(this.accessToken);
            if (payload && payload.exp) {
                const expiresAt = payload.exp * 1000;
                const now = Date.now();
                refreshIn = Math.max(expiresAt - now - 60000, 0);
            } else {
                // Default to 14 minutes (assuming 15 min token)
                refreshIn = 14 * 60 * 1000;
            }
        } else {
            return; // No token to refresh
        }
        
        // Schedule refresh
        this.refreshTimer = setTimeout(async () => {
            console.log('[Auth] Refreshing access token...');
            const success = await this.refreshToken();
            if (!success) {
                console.warn('[Auth] Token refresh failed - user may need to re-login');
            }
        }, Math.max(refreshIn, 0));
        
        console.log(`[Auth] Token refresh scheduled in ${Math.round(refreshIn / 1000)}s`);
    }
    
    /**
     * Get Authorization headers for API requests
     */
    getAuthHeaders() {
        if (!this.accessToken) {
            return {};
        }
        return {
            'Authorization': `Bearer ${this.accessToken}`
        };
    }
    
    /**
     * Get token for WebSocket connection (as query param)
     */
    getWebSocketToken() {
        return this.accessToken;
    }
    
    /**
     * Fetch with auth headers (convenience method)
     */
    async authFetch(url, options = {}) {
        const headers = {
            ...options.headers,
            ...this.getAuthHeaders(),
        };
        
        const response = await fetch(url, {
            ...options,
            headers,
            credentials: 'include',
        });
        
        // If we get a 401, try to refresh and retry once
        if (response.status === 401 && this.accessToken) {
            const refreshed = await this.refreshToken();
            if (refreshed) {
                // Retry with new token
                return fetch(url, {
                    ...options,
                    headers: {
                        ...options.headers,
                        ...this.getAuthHeaders(),
                    },
                    credentials: 'include',
                });
            }
        }
        
        return response;
    }
}

// Create singleton instance
const authManager = new AuthManager();

// Expose to window for use by numerous.js and app code
window.numerousAuth = authManager;

// Also expose user context getter for easy access in widgets
window.getNumerousUserContext = () => authManager.getUserContext();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AuthManager, authManager };
}

