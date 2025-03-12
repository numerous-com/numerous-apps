module.exports = {
  // Use jsdom environment for DOM-related testing
  testEnvironment: 'jsdom',

  // Test files pattern
  testMatch: ['**/tests/js/**/*.test.js'],

  // Transform files with Babel
  transform: {
    '^.+\\.js$': 'babel-jest',
  },

  // Setup file for global test setup
  setupFilesAfterEnv: ['./tests/js/setupTests.js'],

  // Coverage configuration
  coverageDirectory: 'js-coverage',
  collectCoverageFrom: [
    'src/numerous/apps/js/**/*.js',
    '!**/node_modules/**',
  ],

  // Mock files and directories
  moduleNameMapper: {
    // Mock static assets
    '\\.(css|less|sass|scss)$': '<rootDir>/tests/js/__mocks__/styleMock.js',
    '\\.(png|jpg|jpeg|gif|svg)$': '<rootDir>/tests/js/__mocks__/fileMock.js',
  },
}; 