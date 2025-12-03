# CHANGELOG



## v0.4.1 (2025-12-03)

### Fix

* fix(e2e): add Playwright browser tests for UI verification ([`0cfbacc`](https://github.com/numerous-com/numerous-apps/commit/0cfbacc3178dace02fa50372a4a0b3100267ea92))

* fix(e2e): increase timeouts to allow pip install to complete ([`6700618`](https://github.com/numerous-com/numerous-apps/commit/6700618d676940b7cbf7dc9a9561f56f8d9b56a3))


## v0.4.0 (2025-03-13)

### Feature

* feat(session_management): Enhance session handling and connection tracking

- Introduce a grace period for new sessions to prevent premature stale detection
- Improve stale session detection criteria by considering session age and active connections
- Add methods to track active connections in SessionManager
- Update WebSocket message handling to ensure safe processing of messages for connected clients
- Refactor tests to validate new session management logic and connection states ([`6d000f6`](https://github.com/numerous-com/numerous-apps/commit/6d000f633fad099b83f5351ef763ce9cee238c1d))


## v0.3.0 (2025-03-12)

### Feature

* feat(testing): Add comprehensive JavaScript testing infrastructure

- Implement Jest testing framework for client-side JavaScript
- Add pre-commit hooks for running JavaScript tests
- Update GitHub CI/CD workflow to include JavaScript test stage
- Enhance documentation with JavaScript testing instructions
- Improve code quality and reliability through test-driven development ([`6983a6d`](https://github.com/numerous-com/numerous-apps/commit/6983a6d63e5e3a083eabf42d5349dfa572b9e5b0))


## v0.2.4 (2025-03-12)

### Fix

* fix(app_server): Enhance app initialization with improved logging and error handling

- Add detailed debug logging in app initialization process
- Increase retry attempts and timeout for app definition retrieval
- Implement comprehensive error message handling
- Improve error tracking and logging in backend process
- Add more robust error reporting with full traceback ([`29727f0`](https://github.com/numerous-com/numerous-apps/commit/29727f0220ed20590b03d159f9539ba933c75949))


## v0.2.3 (2025-03-11)

### Fix

* fix(logging): Reduce verbosity by changing log levels from info to debug

Modify logging statements in app_server.py to use debug level instead of info, reducing unnecessary log output while maintaining detailed tracing for troubleshooting ([`9ba92fc`](https://github.com/numerous-com/numerous-apps/commit/9ba92fce1e3b24388b1403c21083ad91ab356139))


## v0.2.2 (2025-03-11)

### Fix

* fix(websocket): Implement advanced message handling and batch updates

Enhance WebSocket communication with:
- Comprehensive message type handling
- Batch update support for multiple widget properties
- Improved request tracking with unique request IDs
- More robust logging and error handling
- Added client-side observer re-registration mechanism ([`dfca464`](https://github.com/numerous-com/numerous-apps/commit/dfca464048240bd98ae0f45c6a600afd48dc2a99))


## v0.2.1 (2025-03-11)

### Fix

* fix(app_server): Improve widget configuration retrieval with robust error handling

Add retry mechanism and enhanced error handling for fetching app definitions, including:
- Configurable retry attempts with increasing timeouts
- Detailed logging for initialization failures
- Graceful error responses for timeout and initialization issues
- Improved exception handling and logging ([`77d804b`](https://github.com/numerous-com/numerous-apps/commit/77d804b6f92584040c09fa75c0210fec0fb803ef))


## v0.2.0 (2025-03-11)

### Feature

* feat(websocket): Enhance session management and connection handling

Implement robust session lifecycle management with:
- Periodic session cleanup
- Timeout handling for inactive sessions
- Improved WebSocket connection state tracking
- Better error handling and connection recovery
- Queuing messages during connection establishment ([`5083ca3`](https://github.com/numerous-com/numerous-apps/commit/5083ca3b5db3850702ab009e8f83ac84676c1a3d))


## v0.1.7 (2025-03-06)

### Fix

* fix(websocket): Improve error handling and connection state checks ([`dc8085b`](https://github.com/numerous-com/numerous-apps/commit/dc8085bef4c0f7cd6b12f428e636794b22b9e465))


## v0.1.6 (2025-01-29)

### Fix

* fix(server): set widget div display: flex 100% ([`f9711aa`](https://github.com/numerous-com/numerous-apps/commit/f9711aaec09df19dbc2243cbe53f3b92c6bdeb3d))

### Unknown

* Update README with quick start guide and framework details. ([`e87fe0a`](https://github.com/numerous-com/numerous-apps/commit/e87fe0a6a5b01b186ab400c850ce433b01ee32e3))


## v0.1.5 (2025-01-19)

### Fix

* fix(app): Enhance session management and UI feedback

- Added support for session error handling in the app server, including a new `SessionErrorMessage` model to communicate session issues.
- Implemented a session lost banner in the UI to inform users when their session has expired, improving user experience and feedback.
- Introduced a splash screen to provide visual feedback during loading, enhancing the overall application responsiveness.
- Updated the JavaScript client to handle new message types related to session management and improve connection status handling.
- Refactored the session management logic to utilize a global session manager, streamlining session lifecycle management and cleanup.

These changes improve the robustness of session handling and enhance user interaction with the application. ([`a0a8312`](https://github.com/numerous-com/numerous-apps/commit/a0a8312906d07f1b3d734c8a9322f6c7512ab7fc))


## v0.1.4 (2025-01-16)

### Fix

* fix(app): Enhance widget response with log level configuration

- Updated the app server to include a `logLevel` field in the widget response, dynamically set to &#34;DEBUG&#34; or &#34;ERROR&#34; based on the development environment.
- Modified the default log level in the JavaScript client from `DEBUG` to `ERROR` to align with the new logging strategy.
- Cleaned up console logging in the widget configuration fetch function for improved clarity.

These changes improve logging consistency and provide better control over log levels in the application. ([`b271dc9`](https://github.com/numerous-com/numerous-apps/commit/b271dc90642d4250c1fb35b117966bc223c8a4cd))

* fix(app): Update widget action handling and message types

- Changed the `numpy` dependency in `pyproject.toml` to allow for a wider range of versions.
- Refactored the `e-e-test-script.py` to improve process management and ensure compatibility with the updated project structure.
- Introduced a new `action` decorator in the app framework to facilitate the definition of widget actions.
- Enhanced message handling in the app server to support new message types and improve error handling.
- Updated the JavaScript client to handle new message types for widget updates and action responses.
- Improved test coverage for widget actions and message handling, ensuring robust functionality and error management.

These changes enhance the app&#39;s interactivity and maintainability, providing a more flexible framework for widget actions and communication. ([`e0a90ed`](https://github.com/numerous-com/numerous-apps/commit/e0a90ed37673512892285d7c7c898278c0ca6f42))

* fix(app): Add API endpoints for app and widget trait management

- Introduced new API endpoints to describe the app and retrieve/set widget trait values, enhancing the app&#39;s interactivity and usability.
- Implemented the `describe_app` endpoint to return comprehensive app details, including widget descriptions and template context.
- Added `get_trait_value` and `set_trait_value` endpoints for managing widget traits, with appropriate error handling for non-existent widgets and traits.
- Updated models to include new data structures for app and widget descriptions, improving the overall architecture and maintainability of the codebase. ([`65b6517`](https://github.com/numerous-com/numerous-apps/commit/65b6517a027f3997cfeb2cba6d3b96f8aab87a28))

* fix(app): Enhance widget response with log level configuration

- Updated the app server to include a `logLevel` field in the widget response, dynamically set to &#34;DEBUG&#34; or &#34;ERROR&#34; based on the development environment.
- Modified the default log level in the JavaScript client from `DEBUG` to `ERROR` to align with the new logging strategy.
- Cleaned up console logging in the widget configuration fetch function for improved clarity.

These changes improve logging consistency and provide better control over log levels in the application. ([`f65f93f`](https://github.com/numerous-com/numerous-apps/commit/f65f93f22f3d55d5059de7b17ea6c9f01674b0ec))

* fix(app): Update widget action handling and message types

- Changed the `numpy` dependency in `pyproject.toml` to allow for a wider range of versions.
- Refactored the `e-e-test-script.py` to improve process management and ensure compatibility with the updated project structure.
- Introduced a new `action` decorator in the app framework to facilitate the definition of widget actions.
- Enhanced message handling in the app server to support new message types and improve error handling.
- Updated the JavaScript client to handle new message types for widget updates and action responses.
- Improved test coverage for widget actions and message handling, ensuring robust functionality and error management.

These changes enhance the app&#39;s interactivity and maintainability, providing a more flexible framework for widget actions and communication. ([`bb61008`](https://github.com/numerous-com/numerous-apps/commit/bb610081d4c3220f6d37b29b301f2e348e71e6bc))

* fix(app): Add API endpoints for app and widget trait management

- Introduced new API endpoints to describe the app and retrieve/set widget trait values, enhancing the app&#39;s interactivity and usability.
- Implemented the `describe_app` endpoint to return comprehensive app details, including widget descriptions and template context.
- Added `get_trait_value` and `set_trait_value` endpoints for managing widget traits, with appropriate error handling for non-existent widgets and traits.
- Updated models to include new data structures for app and widget descriptions, improving the overall architecture and maintainability of the codebase. ([`11db5e8`](https://github.com/numerous-com/numerous-apps/commit/11db5e8bd8c431d0fe1ed78705e00f5199fde1b1))


## v0.1.3 (2025-01-04)

### Fix

* fix(ci): Correct end-to-end test script path in release workflow

- Updated the command for executing the end-to-end test script in the GitHub Actions workflow to use the correct file path, ensuring proper execution.
- This change enhances the reliability of the CI/CD pipeline by aligning with the project&#39;s updated structure. ([`7afe396`](https://github.com/numerous-com/numerous-apps/commit/7afe396dde1a9de93b78af6d2c1e570ff03634b6))

* fix(ci): Update end-to-end test script execution in release workflow

- Modified the command for running the end-to-end test script in the GitHub Actions workflow to remove the redundant path specification.
- This change streamlines the execution process and ensures compatibility with the updated project structure.

These updates contribute to a more efficient CI/CD pipeline by simplifying the testing step. ([`b3a2e27`](https://github.com/numerous-com/numerous-apps/commit/b3a2e27b99486d4e5e9572b1b9be7e10785ba56b))

* fix(ci): Enhance end-to-end testing in release workflow

- Added a timeout of 5 minutes for the end-to-end test job to prevent long-running processes.
- Included steps to check out the repository and set up Python 3.12 with pip caching for improved efficiency.
- Installed development dependencies before running the end-to-end test script.

These updates improve the reliability and performance of the CI/CD pipeline by ensuring a more robust testing environment. ([`756412e`](https://github.com/numerous-com/numerous-apps/commit/756412e6fbe955f75b01d44f2f628902119a3688))

* fix(ci): Add end-to-end testing step to release workflow

- Introduced a new job for end-to-end testing in the GitHub Actions workflow.
- Updated the build job to depend on both the test and end-to-end test jobs, ensuring comprehensive testing before the build process.

These changes enhance the CI/CD pipeline by incorporating end-to-end tests, improving the overall reliability of the release process. ([`38350a8`](https://github.com/numerous-com/numerous-apps/commit/38350a8b9a7dd4404eedcbf39f0e53b2bc398f28))

* fix(config): Update pre-commit configuration and coverage settings

- Changed `always_run` in `.pre-commit-config.yaml` to `true` to ensure tests are always executed.
- Updated `branch` setting in `pyproject.toml` under the coverage configuration from `true` to `false`, disabling branch coverage.

These adjustments enhance the testing process and coverage reporting for the project. ([`585b3f1`](https://github.com/numerous-com/numerous-apps/commit/585b3f142315f98b2c88f7bc72cf2782d1a2df6b))

* fix(app): Restructure Numerous app components and update imports

- Removed deprecated modules and files, including `_bootstrap.py`, `_builtins.py`, `_communication.py`, `_execution.py`, `_server.py`, and `app.py`, to streamline the codebase.
- Updated import paths in various files to reflect the new structure, ensuring proper functionality.
- Adjusted `pyproject.toml` to remove specific version pinning for `numerous-widgets` and added package data for `numerous.apps`.
- Enhanced the `bootstrap_app` module by correcting import statements and ensuring consistent package structure.

These changes improve the organization of the Numerous app, making it more maintainable and easier to navigate. ([`b33b0f7`](https://github.com/numerous-com/numerous-apps/commit/b33b0f7037bcc14827731d8214d2ee3a68a7be7a))

* fix(tests): Refactor communication manager tests for improved clarity and synchronization ([`910751e`](https://github.com/numerous-com/numerous-apps/commit/910751eba793eb3d22521339a1fb3312aed51f26))


## v0.1.2 (2025-01-04)

### Fix

* fix(app): Update footer year and pin package versions in requirements.txt

- Updated the footer year in index.html.j2 from 2024 to 2025 for accuracy.
- Specified versions for numpy and numerous-widgets in requirements.txt to ensure consistent behavior across environments.
- Added numerous-apps to requirements.txt for improved dependency management.

These changes enhance the application&#39;s reliability and maintain up-to-date information in the user interface. ([`75d72a5`](https://github.com/numerous-com/numerous-apps/commit/75d72a50d893ba00752270794dfa1c504958913d))

* fix(dependencies): Pin package versions in pyproject.toml for stability

- Updated dependencies in `pyproject.toml` to specific versions to ensure consistent behavior across environments.
- This includes pinning versions for `fastapi`, `uvicorn`, `jinja2`, `anywidget`, `numpy`, `pydantic`, and several development dependencies.

These changes enhance the reliability of the application by preventing unexpected issues due to version discrepancies. ([`e7a3b5a`](https://github.com/numerous-com/numerous-apps/commit/e7a3b5aff9b9cda2b578867475e07ca55e518ffd))


## v0.1.1 (2025-01-04)

### Fix

* fix(apps): Enhance WebSocket message handling and remove unused charts module

- Introduced `encode_model` function for improved serialization of Pydantic models in WebSocket communication.
- Updated message handling in `app.py` to utilize `encode_model` for sending messages, enhancing data integrity.
- Removed the unused `charts.py` module from the bootstrap app, streamlining the codebase.
- Adjusted import statements in `app.py` to handle potential import errors more gracefully.

These changes improve the clarity and reliability of the application&#39;s WebSocket communication and reduce unnecessary code. ([`3e7add2`](https://github.com/numerous-com/numerous-apps/commit/3e7add2080eda486196f4f1ecdc5db2e0b98ccb1))


## v0.1.0 (2025-01-04)

### Feature

* feat(apps): Enhance communication and configuration management

- Added `pydantic` as a new dependency in `pyproject.toml` for improved data validation.
- Refactored message handling in `_communication.py` and `_execution.py` to utilize Pydantic models for structured messaging, enhancing error reporting and data integrity.
- Updated the `send` and `receive_nowait` methods in `CommunicationChannel` to use typed dictionaries for better type safety.
- Improved the WebSocket message handling in `app.py` by introducing dedicated functions for receiving and sending messages, streamlining the communication flow.
- Added tests for communication channels and execution managers to ensure reliability and correctness.

These changes improve the overall robustness and maintainability of the application&#39;s communication framework. ([`1f4c524`](https://github.com/numerous-com/numerous-apps/commit/1f4c5240187302fff193b0d25231d39d39657f90))

### Fix

* fix(communication): Set multiprocessing start method to &#39;spawn&#39; and improve test synchronization

- Added a module-level setting for the multiprocessing start method to &#39;spawn&#39; to ensure compatibility across platforms.
- Introduced a small delay in the test for the communication channel to ensure the queue state is synchronized before assertions.

These changes enhance the reliability of the communication channel in a multiprocessing context and improve test stability. ([`1830ed4`](https://github.com/numerous-com/numerous-apps/commit/1830ed4ade76c51f0a25b23bab777625d78723b6))

* fix(communication): Improve non-blocking queue handling in QueueCommunicationChannel

- Added handling for Empty exception in receive_nowait method to prevent runtime errors when the queue is empty.
- Updated import statement to include Empty from queue module for better error management.
- Minor adjustments in test_app.py to skip multiprocessing tests during coverage runs.

These changes enhance the robustness of the communication channel by ensuring that it gracefully handles empty queue scenarios. ([`fc249d9`](https://github.com/numerous-com/numerous-apps/commit/fc249d93311702bd3e186173b98aa5bd27d8bfa6))

* fix(apps): Multiprocessing mode processes are daemons. ([`f7949a8`](https://github.com/numerous-com/numerous-apps/commit/f7949a801744c2ee43b714bc4158be495f2979c8))

* fix(apps): Fixed issue with queues and events for multiprocess communication ([`f6591d8`](https://github.com/numerous-com/numerous-apps/commit/f6591d87a735be1200d289fb91ca10c7d201132f))

* fix(apps): Fix logic for raising runtime error in ThreadExecutionManager ([`57ea0ca`](https://github.com/numerous-com/numerous-apps/commit/57ea0ca0507d14aa550e1e5fefd83b65a7c8ffdc))


## v0.0.11 (2024-12-28)

### Fix

* fix(apps): Fix small issue in app.py added more tests ([`063b2d8`](https://github.com/numerous-com/numerous-apps/commit/063b2d8f7c1a4f54b5381230c260d79e5175878e))


## v0.0.10 (2024-12-28)

### Fix

* fix(apps): missing httpx dev dep ([`c8f1399`](https://github.com/numerous-com/numerous-apps/commit/c8f1399d043e38ea42006b9c4e3d781e3ff3cbf1))

* fix(apps): Enhance project configuration, testing and logging

- Added new classifiers to pyproject.toml for better package categorization.
- Updated .gitignore to exclude htmlcov directory.
- Improved logging in _bootstrap.py for better visibility during template copying and dependency installation.
- Enhanced communication management in _communication.py and _execution.py to streamline message handling and improve error reporting.
- Refactored widget handling in app.py to ensure consistent session management and improved error handling in template rendering.

These changes improve the overall configuration, logging, and communication flow within the application, enhancing maintainability and user experience. ([`c0dbc53`](https://github.com/numerous-com/numerous-apps/commit/c0dbc53fccc41d091a927067dcbf6d78f8e56632))

### Unknown

* Update README.md

Fixed a typo in the AnyWidget URL ([`1716070`](https://github.com/numerous-com/numerous-apps/commit/1716070a942708d23d769b2ac1cb9ca210038b46))


## v0.0.9 (2024-12-15)

### Fix

* fix(apps): Enhance widget state management and threading behavior

- Updated ThreadedExecutionManager to run threads as daemon threads, ensuring they terminate when the main program exits.
- Added functionality in _execution.py to handle &#39;get_widget_states&#39; messages, allowing the server to send current widget states to clients.
- Modified websocket_endpoint in app.py to conditionally broadcast messages based on client ID, improving message handling.
- Enhanced numerous.js to request widget states upon WebSocket connection establishment, ensuring clients receive the latest widget information.

These changes improve the responsiveness and reliability of widget state communication in the application. ([`ef8bae6`](https://github.com/numerous-com/numerous-apps/commit/ef8bae67556494e1be82fa72ad1f476f2b281f60))


## v0.0.8 (2024-12-15)

### Fix

* fix(apps): Simplify session handling and improve widget configuration retrieval

- Removed redundant session validation logic in app.py, streamlining the session creation process.
- Updated the home endpoint to directly use the application configuration for template rendering.
- Enhanced the get_widgets API to return session ID alongside widget configurations, improving client-side session management.
- Modified numerous.js to fetch widget configurations using the session ID from session storage, ensuring consistent session handling across requests.

These changes enhance the clarity and efficiency of session management and widget communication in the application. ([`aab16ac`](https://github.com/numerous-com/numerous-apps/commit/aab16acb469bced0e7589396c62e55c8525e8266))


## v0.0.7 (2024-12-15)

### Fix

* fix(docs): Improve writing in readme ([`d0c7102`](https://github.com/numerous-com/numerous-apps/commit/d0c7102f4d035f4d05dbc7a489fd50b874b978bd))


## v0.0.6 (2024-12-15)

### Fix

* fix(apps): First working version.

Update project configuration and documentation

- Added &#39;build&#39; to .gitignore to exclude build artifacts.
- Removed the unused &#39;apps.md&#39; documentation file.
- Updated &#39;mkdocs.yml&#39; to remove the API Reference section.
- Added &#39;numpy&#39; to the dependencies in &#39;pyproject.toml&#39;.
- Enhanced the &#39;README.md&#39; with a clearer description of the framework and its features, including a new section on getting started and app structure.
- Changed the Uvicorn host in &#39;app.py&#39; to &#39;127.0.0.1&#39; for better local development compatibility.

These changes improve project organization, documentation clarity, and dependency management. ([`1ea4411`](https://github.com/numerous-com/numerous-apps/commit/1ea4411bc9da34723c30594f9aef075b32575052))


## v0.0.5 (2024-12-14)

### Fix

* fix(apps): threaded apps ([`1a56352`](https://github.com/numerous-com/numerous-apps/commit/1a563526005eba2c5e3d044c2a2bc8317f9300dc))


## v0.0.4 (2024-12-13)

### Fix

* fix(apps): Change to relative paths in template ([`98dd711`](https://github.com/numerous-com/numerous-apps/commit/98dd711f9764efba007437136832d52a6bee8e70))


## v0.0.3 (2024-12-12)

### Fix

* fix(apps): Update backend initialization and WebSocket connection handling

- Modified the Backend class to accept customizable host and port parameters during initialization, enhancing flexibility for server configuration.
- Updated the run method in Backend to utilize the new host and port attributes for starting the FastAPI server.
- Adjusted the numerous_server.py main function to pass host and port arguments from command line options to the Backend instance.
- Enhanced WebSocket connection logic in numerous.js to dynamically determine the protocol (ws or wss) based on the current page&#39;s security context.

These changes improve the configurability of the backend server and ensure secure WebSocket connections. ([`ca028fc`](https://github.com/numerous-com/numerous-apps/commit/ca028fcbd898ccffff50ff8381ae5afd85afa7fe))


## v0.0.2 (2024-12-12)

### Fix

* fix(apps): Implement logging utility and enhance debug information in numerous.js

- Introduced a logging utility with adjustable log levels (DEBUG, INFO, WARN, ERROR, NONE) to standardize logging across the application.
- Replaced console.log statements with the new logging utility for better control over log output.
- Added functionality to set log levels dynamically based on widget configuration.
- Improved error handling and debug information throughout the WidgetModel and WebSocketManager classes.

These changes enhance the maintainability of the code and provide clearer insights during development and debugging. ([`c9a1ffe`](https://github.com/numerous-com/numerous-apps/commit/c9a1ffe6f5c1f0df5397dc379f091bb063fb86b2))

### Unknown

* Refactor project structure and update documentation

- Changed project name from &#34;numerous-app&#34; to &#34;numerous-apps&#34; in pyproject.toml.
- Deleted the empty README.md file.
- Updated docs/apps.md to reflect the new project name and added a new title.
- Expanded docs/README.md with a comprehensive overview of the Numerous Apps framework, including key features and benefits.

These changes improve project clarity and enhance the documentation for better user understanding. ([`70663a5`](https://github.com/numerous-com/numerous-apps/commit/70663a59abc06894291be671e9b24d40d7406789))


## v0.0.1 (2024-12-11)

### Fix

* fix(apps): updated pyproject ([`b19dca0`](https://github.com/numerous-com/numerous-apps/commit/b19dca0b288146ae5bdf9de32aac7f31a686beff))

* fix(apps): Add mock test ([`4511e52`](https://github.com/numerous-com/numerous-apps/commit/4511e523584ef5a7804e3f2bd462c9a13b245a4a))

* fix(apps): First release ([`f431127`](https://github.com/numerous-com/numerous-apps/commit/f4311276bf3c9654c6103ce9437b7e46178e525e))

### Unknown

* Update project configuration and clean up widget handling

- Updated .gitignore to include additional cache files and environment configurations.
- Modified pyproject.toml to change the Python version requirement to 3.12 and updated the author information.
- Refactored app.py to remove the Plotly tab and associated visibility logic, simplifying the UI.
- Cleaned up charts.py by removing unused code related to data generation and plotting.
- Deleted unused files and templates related to error handling and backend processes, streamlining the project structure.

These changes enhance project organization, improve maintainability, and ensure compatibility with the latest Python version. ([`6f16840`](https://github.com/numerous-com/numerous-apps/commit/6f1684069ff2368383fd2df340c1dfe3fccaf4fb))

* Enhance type annotations and refactor widget handling in App and ParentVisibility classes

- Added type hints for method parameters and return types across multiple files, improving code clarity and maintainability.
- Introduced WidgetConfig TypedDict in the backend for better widget configuration management.
- Updated transform_widgets and App class initialization to use more specific type annotations.
- Refactored the _update_visibility method in ParentVisibility to include type hints for event handling.

These changes contribute to a more robust, maintainable, and type-safe codebase. ([`f6b7a4f`](https://github.com/numerous-com/numerous-apps/commit/f6b7a4f432bc9bb3934f9e4d72c4548fd2d92f59))

* Enhance type annotations and refactor widget handling in App and Backend classes:

- Added type hints for better clarity and maintainability, including return types for methods.
- Improved widget detection logic in the App class to streamline widget management.
- Updated the Backend class to utilize a QueueType alias for clearer type definitions.
- Introduced a new create_handler method for better encapsulation of widget message handling.

These changes contribute to a more robust, maintainable, and type-safe codebase. ([`8ac31ff`](https://github.com/numerous-com/numerous-apps/commit/8ac31ff2317d4ac91cc5f368483541a1b4cb1d3c))

* Refactor backend and app initialization: Removed debug print statement from App class to clean up output. Enhanced type annotations in backend for better clarity and maintainability, including the addition of TypedDicts for widget configuration and session data. Updated method signatures to include return types, improving code readability and type safety. These changes contribute to a more robust and maintainable codebase. ([`4d3f154`](https://github.com/numerous-com/numerous-apps/commit/4d3f154df48211f140b2caa01a7d695127f6a69b))

* Refactor app.py and backend structure: Removed unused imports and redundant code in app.py, enhancing clarity and maintainability. Updated the App class to sort widgets for better visibility and improved logging in the Backend class. Streamlined the backend process handling by adjusting argument passing and ensuring proper path management. These changes contribute to a cleaner codebase and improved application performance. ([`40f7e20`](https://github.com/numerous-com/numerous-apps/commit/40f7e20b04d4539d9cbace7a273252f41c843791))

* Add error modal functionality and improve template handling in backend

- Introduced a new error modal in the CSS for better user feedback on errors.
- Updated the backend to load and render the error modal template within the HTML response.
- Enhanced error handling in the WebSocketManager to display error messages using the new modal.
- Removed redundant error modal initialization code from the frontend JavaScript.

These changes improve the user experience by providing clear error notifications and streamline the integration of error handling across the application. ([`5c1d35b`](https://github.com/numerous-com/numerous-apps/commit/5c1d35b98c4d051165d8345cb58065f5a783263f))

* Enhance error handling and logging in backend and frontend: Introduced robust error handling in the App and Backend classes, logging detailed error messages and stack traces. Updated the frontend WebSocketManager to display error modals for better user feedback. Removed unnecessary parameters from the Backend constructor to simplify initialization. This improves overall application stability and user experience. ([`3a3827e`](https://github.com/numerous-com/numerous-apps/commit/3a3827edf07aaa58d3fc12df342a06b07a0b4690))

* Remove numerous_demo_app.py and enhance error handling in backend: Deleted the demo application file to streamline the project structure. Improved error handling in the backend by introducing custom exceptions for app process and initialization errors, and enhanced logging for better debugging. Updated the backend to support development mode, providing more informative error responses during session initialization. ([`fe65ac1`](https://github.com/numerous-com/numerous-apps/commit/fe65ac12f3e9f202df3096c1962a076a8975f49f))

* Cleanup numerous_demo_app.py: Removed unused imports to streamline the code and improve readability. This change enhances maintainability by eliminating unnecessary dependencies. ([`1ed89c1`](https://github.com/numerous-com/numerous-apps/commit/1ed89c14b1012099d5de4963566ea2cb82ecd0a4))

* Refactor backend template processing: Removed CSS link insertion from HTML head and deleted unused static CSS file. This streamlines the template handling and reduces clutter in the project, enhancing maintainability. ([`282db0e`](https://github.com/numerous-com/numerous-apps/commit/282db0e773e0a9f9f66ccc28f526393c722bc8b8))

* Refactor numerous app structure: Updated the App class to accept widgets as keyword arguments, enhancing flexibility in widget management. Modified the demo app to utilize the new App initialization method. Improved backend template handling by ensuring CSS links are correctly inserted into the HTML head. This update streamlines widget integration and enhances the overall maintainability of the application. ([`27dbe53`](https://github.com/numerous-com/numerous-apps/commit/27dbe53cc565af1af5cc470e6fc90ddd43ee5bbb))

* Fix formatting in numerous_server.py: added a blank line before the main check for improved readability and adherence to PEP 8 style guidelines. ([`9db6193`](https://github.com/numerous-com/numerous-apps/commit/9db619355be68ba99f05f8de4ac3d476c980ad80))

* Enhance styling and layout management: Added Google Fonts for improved typography in CSS, introduced new CSS rules for display properties in the backend, and removed outdated styles from the static CSS file. This update improves the visual consistency and maintainability of the application. ([`b29b188`](https://github.com/numerous-com/numerous-apps/commit/b29b188d6aec21971dd1e6899bc1150925471550))

* Refactor frontend and backend integration: removed inline styles from HTML template, added external CSS link for improved styling, and established a new static file mount for package assets. This enhances maintainability and separation of concerns in the project structure. ([`ae3a9f1`](https://github.com/numerous-com/numerous-apps/commit/ae3a9f196eee992babf29678d1e15a1a54ae7a44))

* Remove run from app ([`838e591`](https://github.com/numerous-com/numerous-apps/commit/838e59101831b7b84f791c46fcf6514b57cc8265))

* Improve error handling in backend template processing: added exception handling for missing templates and enhanced logging for undefined variables. Now returns a user-friendly error response when templates are not found or contain unmatched variables. ([`dd721ed`](https://github.com/numerous-com/numerous-apps/commit/dd721edc6e2e3ff41dc9ca74f38d9a3ddcd37a1d))

* Refactor backend template handling: added package directory support and improved error handling for template loading. Now includes a fallback error template for better user feedback. ([`5855c1f`](https://github.com/numerous-com/numerous-apps/commit/5855c1faf8df6f0eb4d355575500c32a4440eb88))

* Enhance template validation in backend: added checks for undefined variables in templates and ensured they match widget keys. This prevents runtime errors due to mismatched template variables. ([`91b4659`](https://github.com/numerous-com/numerous-apps/commit/91b4659c69f2c8a8dd461da992e5a297c44fa197))

* Added a second counter widget to the demo app and improved template context handling in the backend. The backend now checks for missing widget placeholders in the template and logs a warning if any are found. ([`880e816`](https://github.com/numerous-com/numerous-apps/commit/880e8161e95bd09af59d43b13c08f387445684d5))

* removed js from remplate ([`88dd743`](https://github.com/numerous-com/numerous-apps/commit/88dd7438c0e9d205326b2c2ba40095027b2a11c1))

* moved maim js out of apps static folder ([`9669dc0`](https://github.com/numerous-com/numerous-apps/commit/9669dc089d3fcbc32e27ae435f559959875e4f49))

* fixes to disconnect logic ([`6cf8901`](https://github.com/numerous-com/numerous-apps/commit/6cf890158a21b51276a43da95c13c53c50eb579f))

* fixes ([`9312038`](https://github.com/numerous-com/numerous-apps/commit/9312038278be99dea4c1549803c769f4ba460ef1))

* fixes with shadow DoM ([`8835757`](https://github.com/numerous-com/numerous-apps/commit/88357571c608a16781b4f878e5f6ecfa8045636f))

* added shadow doms to scope css to each widget ([`a21493a`](https://github.com/numerous-com/numerous-apps/commit/a21493abbe38f3c4682403335a8e944aace3159a))

* some fixe ([`5a28841`](https://github.com/numerous-com/numerous-apps/commit/5a28841c8fef12883aca6b1649555a7eabef8e0e))

* fixes ([`0786ec4`](https://github.com/numerous-com/numerous-apps/commit/0786ec43320dc2f1054b7926b137fe8909b5a6fd))

* Added Numerous demo app ([`9ab37d0`](https://github.com/numerous-com/numerous-apps/commit/9ab37d0150be50a7a623e4b9eab9ad4f7c5731be))

* fixes to process and debug instead of print ([`f597bb2`](https://github.com/numerous-com/numerous-apps/commit/f597bb26ad21e442b154b54e04f0be08495bed3d))

* processes working ish ([`60e971f`](https://github.com/numerous-com/numerous-apps/commit/60e971fa60c850b15ee21d27294b2015d34494d8))
