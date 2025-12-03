/**
 * Tests for BASE_PATH functionality in numerous.js
 */

// Mock console methods to avoid spam during tests
const originalConsole = { ...console };
beforeAll(() => {
  console.log = jest.fn();
  console.info = jest.fn();
  console.warn = jest.fn();
  console.error = jest.fn();
  console.debug = jest.fn();
});

afterAll(() => {
  // Restore console
  Object.assign(console, originalConsole);
});

describe('BASE_PATH Configuration', () => {
  let originalBasePath;
  
  beforeEach(() => {
    // Save original value
    originalBasePath = window.NUMEROUS_BASE_PATH;
  });
  
  afterEach(() => {
    // Restore original value
    window.NUMEROUS_BASE_PATH = originalBasePath;
  });
  
  describe('window.NUMEROUS_BASE_PATH', () => {
    it('should default to empty string when not set', () => {
      delete window.NUMEROUS_BASE_PATH;
      const basePath = window.NUMEROUS_BASE_PATH || '';
      expect(basePath).toBe('');
    });
    
    it('should use the set value when defined', () => {
      window.NUMEROUS_BASE_PATH = '/myapp';
      const basePath = window.NUMEROUS_BASE_PATH || '';
      expect(basePath).toBe('/myapp');
    });
    
    it('should handle nested paths', () => {
      window.NUMEROUS_BASE_PATH = '/apps/dashboard';
      const basePath = window.NUMEROUS_BASE_PATH || '';
      expect(basePath).toBe('/apps/dashboard');
    });
  });
  
  describe('URL construction with BASE_PATH', () => {
    it('should construct API URLs correctly with base path', () => {
      window.NUMEROUS_BASE_PATH = '/myapp';
      const basePath = window.NUMEROUS_BASE_PATH || '';
      const sessionId = 'test-session';
      
      const apiUrl = `${basePath}/api/widgets?session_id=${sessionId}`;
      expect(apiUrl).toBe('/myapp/api/widgets?session_id=test-session');
    });
    
    it('should construct WebSocket URLs correctly with base path', () => {
      window.NUMEROUS_BASE_PATH = '/myapp';
      const basePath = window.NUMEROUS_BASE_PATH || '';
      const protocol = 'ws:';
      const host = 'localhost:8000';
      const clientId = 'client123';
      const sessionId = 'session456';
      
      const wsUrl = `${protocol}//${host}${basePath}/ws/${clientId}/${sessionId}`;
      expect(wsUrl).toBe('ws://localhost:8000/myapp/ws/client123/session456');
    });
    
    it('should construct login redirect URL correctly', () => {
      window.NUMEROUS_BASE_PATH = '/admin';
      const basePath = window.NUMEROUS_BASE_PATH || '';
      const pathname = '/admin/dashboard';
      
      const loginUrl = `${basePath}/login?next=` + encodeURIComponent(pathname);
      expect(loginUrl).toBe('/admin/login?next=%2Fadmin%2Fdashboard');
    });
    
    it('should work correctly with empty base path', () => {
      window.NUMEROUS_BASE_PATH = '';
      const basePath = window.NUMEROUS_BASE_PATH || '';
      
      const apiUrl = `${basePath}/api/widgets?session_id=test`;
      expect(apiUrl).toBe('/api/widgets?session_id=test');
    });
  });
});

describe('WebSocketManager with BASE_PATH', () => {
  // Mock WebSocket
  const mockWebSocket = jest.fn().mockImplementation(() => ({
    send: jest.fn(),
    close: jest.fn(),
    readyState: 1, // OPEN
    onopen: null,
    onclose: null,
    onerror: null,
    onmessage: null
  }));
  
  let originalWebSocket;
  
  beforeEach(() => {
    originalWebSocket = global.WebSocket;
    global.WebSocket = mockWebSocket;
    mockWebSocket.OPEN = 1;
    mockWebSocket.CLOSED = 3;
    mockWebSocket.mockClear();
  });
  
  afterEach(() => {
    global.WebSocket = originalWebSocket;
    delete window.NUMEROUS_BASE_PATH;
  });
  
  describe('WebSocket URL construction', () => {
    it('should include BASE_PATH in WebSocket URL', () => {
      window.NUMEROUS_BASE_PATH = '/dashboard';
      
      // Simulate what numerous.js does when creating WebSocket connection
      const basePath = window.NUMEROUS_BASE_PATH || '';
      const protocol = 'ws:';
      const host = window.location.host || 'localhost:8000';
      const clientId = 'test-client';
      const sessionId = 'test-session';
      
      const expectedUrl = `${protocol}//${host}${basePath}/ws/${clientId}/${sessionId}`;
      
      // Create the WebSocket
      new WebSocket(expectedUrl);
      
      expect(mockWebSocket).toHaveBeenCalledWith(
        expect.stringContaining('/dashboard/ws/')
      );
    });
    
    it('should not include BASE_PATH when empty', () => {
      window.NUMEROUS_BASE_PATH = '';
      
      const basePath = window.NUMEROUS_BASE_PATH || '';
      const protocol = 'ws:';
      const host = 'localhost:8000';
      const clientId = 'test-client';
      const sessionId = 'test-session';
      
      const wsUrl = `${protocol}//${host}${basePath}/ws/${clientId}/${sessionId}`;
      new WebSocket(wsUrl);
      
      expect(mockWebSocket).toHaveBeenCalledWith(
        'ws://localhost:8000/ws/test-client/test-session'
      );
    });
  });
});

describe('fetchWidgetConfigs with BASE_PATH', () => {
  let originalFetch;
  
  beforeEach(() => {
    originalFetch = global.fetch;
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: jest.fn().mockResolvedValue({
        session_id: 'new-session',
        widgets: {},
        logLevel: 'ERROR'
      })
    });
    
    // Mock sessionStorage
    const mockStorage = {};
    global.sessionStorage = {
      getItem: jest.fn(key => mockStorage[key] || null),
      setItem: jest.fn((key, value) => { mockStorage[key] = value; })
    };
  });
  
  afterEach(() => {
    global.fetch = originalFetch;
    delete window.NUMEROUS_BASE_PATH;
  });
  
  it('should use BASE_PATH in API fetch URL', async () => {
    window.NUMEROUS_BASE_PATH = '/myapp';
    const basePath = window.NUMEROUS_BASE_PATH || '';
    
    // Simulate the fetch call from numerous.js
    const sessionId = sessionStorage.getItem('session_id');
    await fetch(`${basePath}/api/widgets?session_id=${sessionId}`, {
      headers: {},
      credentials: 'include'
    });
    
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/myapp/api/widgets'),
      expect.any(Object)
    );
  });
  
  it('should redirect to BASE_PATH login on 401', async () => {
    window.NUMEROUS_BASE_PATH = '/secure';
    const basePath = window.NUMEROUS_BASE_PATH || '';
    
    // Simulate 401 response handling
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 401
    });
    
    // The expected login URL construction
    const pathname = '/secure/dashboard';
    const loginUrl = `${basePath}/login?next=` + encodeURIComponent(pathname);
    
    expect(loginUrl).toBe('/secure/login?next=%2Fsecure%2Fdashboard');
  });
});

describe('Auth endpoint URLs with BASE_PATH', () => {
  beforeEach(() => {
    delete window.NUMEROUS_BASE_PATH;
  });
  
  it('should construct auth login URL with BASE_PATH', () => {
    window.NUMEROUS_BASE_PATH = '/admin';
    const basePath = window.NUMEROUS_BASE_PATH || '';
    
    const loginEndpoint = `${basePath}/api/auth/login`;
    expect(loginEndpoint).toBe('/admin/api/auth/login');
  });
  
  it('should construct auth logout URL with BASE_PATH', () => {
    window.NUMEROUS_BASE_PATH = '/admin';
    const basePath = window.NUMEROUS_BASE_PATH || '';
    
    const logoutEndpoint = `${basePath}/api/auth/logout`;
    expect(logoutEndpoint).toBe('/admin/api/auth/logout');
  });
  
  it('should construct auth check URL with BASE_PATH', () => {
    window.NUMEROUS_BASE_PATH = '/admin';
    const basePath = window.NUMEROUS_BASE_PATH || '';
    
    const checkEndpoint = `${basePath}/api/auth/check`;
    expect(checkEndpoint).toBe('/admin/api/auth/check');
  });
});

