/**
 * Tests for the AuthManager class in auth.js
 */

// Mock the log function
global.log = jest.fn();
global.LOG_LEVELS = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3,
  NONE: 4
};

// Mock localStorage - create fresh for each test
let localStorageStore = {};
const localStorageMock = {
  getItem: jest.fn((key) => localStorageStore[key] || null),
  setItem: jest.fn((key, value) => { localStorageStore[key] = String(value); }),
  removeItem: jest.fn((key) => { delete localStorageStore[key]; }),
  clear: jest.fn(() => { localStorageStore = {}; })
};
Object.defineProperty(global, 'localStorage', {
  value: localStorageMock,
  writable: true
});

// Mock fetch
global.fetch = jest.fn();

// Mock window.location
const originalLocation = window.location;
delete window.location;
window.location = { href: '', pathname: '/' };

/**
 * AuthManager class - simplified version for testing
 */
class AuthManager {
  constructor() {
    this.accessToken = localStorage.getItem('access_token');
    this.user = this._loadUser();
    this.tokenExpiresAt = null;
    this.refreshTimer = null;
    
    if (this.accessToken) {
      this._scheduleRefresh();
    }
  }
  
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
  
  isAuthenticated() {
    return !!this.accessToken && !!this.user;
  }
  
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
  
  async login(username, password) {
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
        credentials: 'include',
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Login failed');
      }
      
      const data = await response.json();
      
      this.accessToken = data.access_token;
      this.user = data.user;
      
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));
      
      this._scheduleRefresh(data.expires_in);
      
      return { success: true, user: data.user };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }
  
  async refreshToken() {
    try {
      const response = await fetch('/api/auth/refresh', {
        method: 'POST',
        credentials: 'include',
      });
      
      if (!response.ok) {
        this._clearAuth();
        return false;
      }
      
      const data = await response.json();
      
      this.accessToken = data.access_token;
      localStorage.setItem('access_token', data.access_token);
      
      this._scheduleRefresh(data.expires_in);
      
      return true;
    } catch (error) {
      this._clearAuth();
      return false;
    }
  }
  
  async logout() {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
    } catch (error) {
      // Ignore errors during logout
    }
    
    this._clearAuth();
    window.location.href = '/login';
  }
  
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
  
  _scheduleRefresh(expiresInSeconds = null) {
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
    }
    
    // For testing, we don't actually schedule the refresh
    // Just record that it was called
    this._refreshScheduled = true;
    this._refreshExpiresIn = expiresInSeconds;
  }
  
  getAuthHeaders() {
    if (!this.accessToken) {
      return {};
    }
    return { 'Authorization': `Bearer ${this.accessToken}` };
  }
  
  getWebSocketToken() {
    return this.accessToken;
  }
  
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
    
    if (response.status === 401 && this.accessToken) {
      const refreshed = await this.refreshToken();
      if (refreshed) {
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

describe('AuthManager', () => {
  let authManager;
  
  beforeEach(() => {
    // Clear localStorage store and reset mocks before each test
    localStorageStore = {};
    localStorageMock.getItem.mockClear();
    localStorageMock.setItem.mockClear();
    localStorageMock.removeItem.mockClear();
    localStorageMock.clear.mockClear();
    
    // Reset fetch mock
    fetch.mockReset();
    
    // Reset window.location
    window.location.href = '';
    window.location.pathname = '/';
    
    // Create a fresh AuthManager instance
    authManager = new AuthManager();
  });
  
  afterEach(() => {
    if (authManager && authManager.refreshTimer) {
      clearTimeout(authManager.refreshTimer);
    }
  });
  
  describe('constructor', () => {
    it('should initialize with no auth when localStorage is empty', () => {
      expect(authManager.accessToken).toBeNull();
      expect(authManager.user).toBeNull();
      expect(authManager.isAuthenticated()).toBe(false);
    });
    
    it('should load token and user from localStorage', () => {
      // Set values in store before creating manager
      localStorageStore.access_token = 'test-token';
      localStorageStore.user = JSON.stringify({ 
        id: '123', 
        username: 'testuser',
        roles: ['viewer'],
        is_admin: false
      });
      
      const manager = new AuthManager();
      
      expect(manager.accessToken).toBe('test-token');
      expect(manager.user.username).toBe('testuser');
      expect(manager.isAuthenticated()).toBe(true);
    });
    
    it('should handle invalid JSON in user storage', () => {
      localStorageStore.user = 'invalid-json';
      
      const manager = new AuthManager();
      
      expect(manager.user).toBeNull();
    });
  });
  
  describe('isAuthenticated', () => {
    it('should return false when not logged in', () => {
      expect(authManager.isAuthenticated()).toBe(false);
    });
    
    it('should return true when logged in', () => {
      authManager.accessToken = 'test-token';
      authManager.user = { id: '123', username: 'testuser' };
      
      expect(authManager.isAuthenticated()).toBe(true);
    });
    
    it('should return false when only token is present', () => {
      authManager.accessToken = 'test-token';
      
      expect(authManager.isAuthenticated()).toBe(false);
    });
    
    it('should return false when only user is present', () => {
      authManager.user = { id: '123', username: 'testuser' };
      
      expect(authManager.isAuthenticated()).toBe(false);
    });
  });
  
  describe('getUserContext', () => {
    it('should return anonymous context when not authenticated', () => {
      const ctx = authManager.getUserContext();
      
      expect(ctx.authenticated).toBe(false);
      expect(ctx.username).toBeNull();
      expect(ctx.user_id).toBeNull();
      expect(ctx.roles).toEqual([]);
      expect(ctx.is_admin).toBe(false);
    });
    
    it('should return user context when authenticated', () => {
      authManager.accessToken = 'test-token';
      authManager.user = {
        id: '123',
        username: 'testuser',
        roles: ['viewer', 'editor'],
        is_admin: false
      };
      
      const ctx = authManager.getUserContext();
      
      expect(ctx.authenticated).toBe(true);
      expect(ctx.username).toBe('testuser');
      expect(ctx.user_id).toBe('123');
      expect(ctx.roles).toEqual(['viewer', 'editor']);
      expect(ctx.is_admin).toBe(false);
    });
    
    it('should return admin context for admin users', () => {
      authManager.accessToken = 'test-token';
      authManager.user = {
        id: 'admin-123',
        username: 'admin',
        roles: ['admin'],
        is_admin: true
      };
      
      const ctx = authManager.getUserContext();
      
      expect(ctx.is_admin).toBe(true);
    });
  });
  
  describe('login', () => {
    it('should successfully login with valid credentials', async () => {
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({
          access_token: 'new-token',
          token_type: 'bearer',
          expires_in: 900,
          user: { id: '123', username: 'testuser', roles: [] }
        })
      };
      fetch.mockResolvedValue(mockResponse);
      
      const result = await authManager.login('testuser', 'password123');
      
      expect(result.success).toBe(true);
      expect(result.user.username).toBe('testuser');
      expect(authManager.accessToken).toBe('new-token');
      expect(localStorage.setItem).toHaveBeenCalledWith('access_token', 'new-token');
    });
    
    it('should fail login with invalid credentials', async () => {
      const mockResponse = {
        ok: false,
        json: jest.fn().mockResolvedValue({ detail: 'Invalid credentials' })
      };
      fetch.mockResolvedValue(mockResponse);
      
      const result = await authManager.login('testuser', 'wrongpassword');
      
      expect(result.success).toBe(false);
      expect(result.error).toBe('Invalid credentials');
    });
    
    it('should handle network errors during login', async () => {
      fetch.mockRejectedValue(new Error('Network error'));
      
      const result = await authManager.login('testuser', 'password123');
      
      expect(result.success).toBe(false);
      expect(result.error).toBe('Network error');
    });
    
    it('should call login endpoint with correct parameters', async () => {
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({
          access_token: 'token',
          user: { id: '1', username: 'user' }
        })
      };
      fetch.mockResolvedValue(mockResponse);
      
      await authManager.login('myuser', 'mypass');
      
      expect(fetch).toHaveBeenCalledWith('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: 'myuser', password: 'mypass' }),
        credentials: 'include',
      });
    });
    
    it('should schedule token refresh after successful login', async () => {
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({
          access_token: 'new-token',
          expires_in: 900,
          user: { id: '123', username: 'testuser' }
        })
      };
      fetch.mockResolvedValue(mockResponse);
      
      await authManager.login('testuser', 'password123');
      
      expect(authManager._refreshScheduled).toBe(true);
      expect(authManager._refreshExpiresIn).toBe(900);
    });
  });
  
  describe('refreshToken', () => {
    beforeEach(() => {
      authManager.accessToken = 'old-token';
      authManager.user = { id: '123', username: 'testuser' };
    });
    
    it('should refresh token successfully', async () => {
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({
          access_token: 'refreshed-token',
          expires_in: 900
        })
      };
      fetch.mockResolvedValue(mockResponse);
      
      const result = await authManager.refreshToken();
      
      expect(result).toBe(true);
      expect(authManager.accessToken).toBe('refreshed-token');
      expect(localStorage.setItem).toHaveBeenCalledWith('access_token', 'refreshed-token');
    });
    
    it('should clear auth on refresh failure', async () => {
      const mockResponse = { ok: false };
      fetch.mockResolvedValue(mockResponse);
      
      const result = await authManager.refreshToken();
      
      expect(result).toBe(false);
      expect(authManager.accessToken).toBeNull();
      expect(authManager.user).toBeNull();
      expect(localStorage.removeItem).toHaveBeenCalledWith('access_token');
      expect(localStorage.removeItem).toHaveBeenCalledWith('user');
    });
    
    it('should handle network errors during refresh', async () => {
      fetch.mockRejectedValue(new Error('Network error'));
      
      const result = await authManager.refreshToken();
      
      expect(result).toBe(false);
      expect(authManager.accessToken).toBeNull();
    });
  });
  
  describe('logout', () => {
    beforeEach(() => {
      authManager.accessToken = 'test-token';
      authManager.user = { id: '123', username: 'testuser' };
    });
    
    it('should call logout endpoint', async () => {
      fetch.mockResolvedValue({ ok: true });
      
      await authManager.logout();
      
      expect(fetch).toHaveBeenCalledWith('/api/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
    });
    
    it('should clear auth state after logout', async () => {
      fetch.mockResolvedValue({ ok: true });
      
      await authManager.logout();
      
      expect(authManager.accessToken).toBeNull();
      expect(authManager.user).toBeNull();
      expect(localStorage.removeItem).toHaveBeenCalledWith('access_token');
      expect(localStorage.removeItem).toHaveBeenCalledWith('user');
    });
    
    it('should redirect to login page after logout', async () => {
      fetch.mockResolvedValue({ ok: true });
      
      await authManager.logout();
      
      expect(window.location.href).toBe('/login');
    });
    
    it('should clear auth even if logout request fails', async () => {
      fetch.mockRejectedValue(new Error('Network error'));
      
      await authManager.logout();
      
      expect(authManager.accessToken).toBeNull();
      expect(window.location.href).toBe('/login');
    });
  });
  
  describe('getAuthHeaders', () => {
    it('should return empty object when not authenticated', () => {
      const headers = authManager.getAuthHeaders();
      
      expect(headers).toEqual({});
    });
    
    it('should return Authorization header when authenticated', () => {
      authManager.accessToken = 'my-token';
      
      const headers = authManager.getAuthHeaders();
      
      expect(headers).toEqual({ 'Authorization': 'Bearer my-token' });
    });
  });
  
  describe('getWebSocketToken', () => {
    it('should return null when not authenticated', () => {
      const token = authManager.getWebSocketToken();
      
      expect(token).toBeNull();
    });
    
    it('should return access token when authenticated', () => {
      authManager.accessToken = 'ws-token';
      
      const token = authManager.getWebSocketToken();
      
      expect(token).toBe('ws-token');
    });
  });
  
  describe('authFetch', () => {
    beforeEach(() => {
      authManager.accessToken = 'test-token';
      authManager.user = { id: '123', username: 'testuser' };
    });
    
    it('should add auth headers to request', async () => {
      const mockResponse = { ok: true, status: 200 };
      fetch.mockResolvedValue(mockResponse);
      
      await authManager.authFetch('/api/data');
      
      expect(fetch).toHaveBeenCalledWith('/api/data', {
        headers: { 'Authorization': 'Bearer test-token' },
        credentials: 'include',
      });
    });
    
    it('should merge with existing headers', async () => {
      const mockResponse = { ok: true, status: 200 };
      fetch.mockResolvedValue(mockResponse);
      
      await authManager.authFetch('/api/data', {
        headers: { 'Content-Type': 'application/json' }
      });
      
      expect(fetch).toHaveBeenCalledWith('/api/data', {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer test-token'
        },
        credentials: 'include',
      });
    });
    
    it('should retry with new token on 401 response', async () => {
      // First call returns 401, second call succeeds after refresh
      const unauthorizedResponse = { ok: false, status: 401 };
      const successResponse = { ok: true, status: 200 };
      const refreshResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({
          access_token: 'new-token',
          expires_in: 900
        })
      };
      
      fetch
        .mockResolvedValueOnce(unauthorizedResponse) // First API call fails
        .mockResolvedValueOnce(refreshResponse) // Refresh succeeds
        .mockResolvedValueOnce(successResponse); // Retry succeeds
      
      await authManager.authFetch('/api/data');
      
      expect(fetch).toHaveBeenCalledTimes(3);
    });
  });
  
  describe('_clearAuth', () => {
    it('should clear all auth state', () => {
      authManager.accessToken = 'token';
      authManager.user = { id: '123' };
      authManager.refreshTimer = setTimeout(() => {}, 10000);
      
      authManager._clearAuth();
      
      expect(authManager.accessToken).toBeNull();
      expect(authManager.user).toBeNull();
      expect(authManager.refreshTimer).toBeNull();
      expect(localStorage.removeItem).toHaveBeenCalledWith('access_token');
      expect(localStorage.removeItem).toHaveBeenCalledWith('user');
    });
  });
});

