# Contributing to Numerous Apps

Thank you for your interest in contributing to Numerous Apps! This document provides guidelines and instructions for contributing to this project.

## Development Setup

1. Clone the repository
2. Install the development dependencies:

```bash
pip install -e ".[dev]"
```

## Testing

### Python Tests

To run the Python tests:

```bash
pytest
```

For coverage information:

```bash
pytest --cov=numerous
```

### JavaScript Tests

The client-side JavaScript code (`numerous.js`) can be tested using Jest. To run the JavaScript tests:

1. Install Node.js if you don't have it already
2. Install the required npm dependencies:

```bash
npm install
```

3. Run the tests:

```bash
npm test
```

For coverage information:

```bash
npm test -- --coverage
```

The JavaScript tests cover the following functionality:
- `WidgetModel` class for managing widget state
- `WebSocketManager` for handling WebSocket communication
- Utility functions for logging and debugging

JavaScript tests are automatically run:
- As part of the pre-commit hooks when pushing code
- In the GitHub CI/CD pipeline for every push to the repository
- Coverage reports are generated and archived as artifacts in GitHub Actions

For more details on the JavaScript testing setup, see [tests/js/README.md](tests/js/README.md).

### Pre-commit Hooks

Both Python and JavaScript tests are included in the pre-commit workflow:

- Python tests run automatically before pushing code
- JavaScript tests run automatically before pushing code

To install the pre-commit hooks:

```bash
pre-commit install --hook-type pre-commit --hook-type pre-push
```

This ensures that all tests pass before code is pushed to the repository.

## Code Style

This project uses:
- **Ruff** for Python linting and formatting
- **Black** for Python code formatting
- **ESLint** and **Prettier** for JavaScript code style

## Submitting Changes

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes
4. Ensure all tests pass
5. Submit a pull request

## Commit Messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/) for commit messages. This enables automatic changelog generation and semantic versioning.

Format: `<type>(<scope>): <description>`

Examples:
- `feat: add new dropdown widget`
- `fix(websocket): resolve connection timeout issue`
- `docs: update installation instructions`

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
