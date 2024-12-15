# CHANGELOG



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
