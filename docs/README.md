# Numerous Apps

## Quick Start

To install the framework and bootstrap your first app, run the following commands:

```bash
pip install numerous-apps
numerous-bootstrap my_app
```

This will copy a simple bootstrap app to the `my_app` directory, install the dependencies and start the app server on 127.0.0.1:8000.
To run the app subsequently, run the following command:

```bash
cd my_app
python app.py
```

To edit the python reactivity, edit the `app.py` file.

To edit the html template, edit the `index.html.j2` file. Its a jinja2 template file, so you can use the jinja2 syntax to define the layout of the app.

## Introduction

A new Python framework in development, aiming to provide a powerful yet simple approach for building reactive web applications. **Numerous Apps** empowers developers to create modern, scalable web applications using familiar Python patterns while maintaining a clean separation between business logic and presentation.

## Who is this for?

This framework is for teams who want to build fantastic apps with a modular approach and a powerful Python backend. It is for apps exposing functionality built using Python requiring a reactive UI tightly integrated with the backend.

If you are:

- Using standard development tools and languages.
- Seeking to have full control over the layout, components and styling for your apps.
- OK with a bit of boilerplate to keep your code clean and organized.
- Creating a library of your own anywidgets that you can use in other Python app frameworks or React apps.

This framework is for you.

Our framework emphasizes modularity, allowing for easy separation of concerns. While we acknowledge that the boilerplate introduced to separate business logic from presentation is a trade-off, we strive to make it as easy as possible to use.

---

## Features

### **Simple Yet Powerful**
- **Intuitive Syntax:** Develop reactive web apps using standard Python and HTML.
- **Quick Start:** Utilize the `numerous-bootstrap` command to create a new app in seconds.
- **Lightweight Core:** Built atop FastAPI, Uvicorn, Jinja2, and anywidget to keep the core lightweight and simple.

### **Modern Architecture**
- **Component-Based:** Leverage [anywidget](https://anywidget.dev/) for reusable, framework-agnostic components.
- **Clear Separation:** Use Python for logic, CSS for styling, and Jinja2 for templates.
- **Process Isolation:** Each session runs independently, enhancing stability and scalability.

### **Full Creative Control**
- **Framework-Agnostic UI:** No enforced styling or components from our side — You have complete freedom in design.
- **Custom Widget Support:** Easily integrate your own HTML, CSS, JS components, and static files.
- **Flexible Templating:** Utilize Jinja2 and HTML for powerful layout composition.

### **Built for Scale**
- **Multi-Client Ready:** Designed to scale and handle multiple clients simultaneously, with support for distributed app instances.
- **AI Integration:** Seamless integration with AI agents and models.
- **Developer-Friendly:** Compatible with your favorite IDE and development tools—no special IDE or notebook needed.

### **Secure by Design**
- **Pluggable Authentication:** Built-in support for user authentication with multiple providers.
- **JWT Tokens:** Secure session management with access and refresh tokens.
- **Role-Based Access:** Support for user roles and admin privileges.
- **Custom Providers:** Easily extend with your own authentication backend.

## Getting Started

This guide will help you get started with **Numerous Apps**. Since a Numerous App comprises multiple files, we'll use the bootstrap app as a foundation. The bootstrap app provides a minimal structure and example widgets to help you begin.

### Installation

First, install the framework:

```bash
pip install numerous-apps
```

### Bootstrapping Your First App

Then, bootstrap your first app:

```bash
numerous-bootstrap my_app   
```

This command creates a new directory called `my_app` with the basic structure of a Numerous App. It initializes the necessary files and folders, installs dependencies, and starts the app server (`uvicorn`). You can access the app at [http://127.0.0.1:8000](http://127.0.0.1:8000).

Try out the app and start making changes to the code.

#### Bootstrap Options

| Option | Description |
|--------|-------------|
| `--with-auth` | Enable environment variable-based authentication |
| `--with-db-auth` | Enable database-based authentication (SQLite) |
| `--export-templates` | Export internal templates (login, error pages, etc.) for customization |
| `--skip-deps` | Skip installing dependencies |
| `--run-skip` | Skip running the app after creation |
| `--port PORT` | Specify the port (default: 8000) |
| `--host HOST` | Specify the host (default: 127.0.0.1) |

Example with authentication:

```bash
numerous-bootstrap my_secure_app --with-auth
```

Example with template customization:

```bash
numerous-bootstrap my_app --export-templates
```

This exports internal templates (login page, error pages, splash screen) and CSS files to your project, allowing full customization of the framework's built-in UI components.

## App File Structure

The minimal app consists of the following files:

- `app.py`: The main application file defining widgets, business logic, and reactivity.
- `index.html.j2`: The primary template file used to define the app's layout.
- `static/`: A directory for static files (images, CSS, JS, etc.), served as-is by the server.
- `requirements.txt`: Lists the app's dependencies.

## Building Your App from Scratch

While the bootstrap app is a helpful starting point, here's a walkthrough on building your app from scratch. This guide helps you understand the framework's workings and how to leverage it to develop your own apps.

- Create a Python file for your app eg. `app.py`.

- In the app file, create a function called `run_app()` which will be used to run the app.
```python
def run_app():
    ...
```

- In the `run_app()` function, you define your widgets and create reactivity by using callbacks passed to the widgets.

```python
import numerous.widgets as wi
<>
...

counter = wi.Number(default=0, label="Counter:", fit_to_content=True)

def on_click(event):
    # Increment the counter
    counter.value += 1

button = wi.Button(label="Click me", on_click=on_click)
```

You can also use the `observe` method to create reactivity which is provided directly by the anywidget framework.

```python
def callback(event):
    # Do something when the widget value changes
    ...

widget.observe(callback, names='value')
```

- At the end of the `run_app()` function, you export the widgets by returning them from the function as a dictionary where the key is the name of the widget and the value is the widget instance.
```python
return {
    "counter": counter,
    "button": button
}
```

- You then create an html template file called `index.html.j2` in the same directory as your app file.

- In the html template file, you can include the widgets by using the `{{ widget_key }}` syntax. Refer to the jinja2 documentation for more information on how to use jinja2 syntax in the html template.

```html
<div style="display: flex; flex-direction: column; gap: 10px;">
    {{ counter }}
    {{ button }}
</div>
```

- You can also include CSS, JS and image files in the static folder, and reference them in the html template like this: `<link href="static/css/styles.css" rel="stylesheet">`

- Now return to the app Python file and import the create_app function from the numerous.apps package and call it with your template file name and the run_app function as arguments.

```python
from numerous.apps import create_app
...
app = create_app(template="index.html.j2", dev=True, app_generator=run_app)
```

- Finally, run the app by calling the app variable in the if `__name__ == "__main__"` block.

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

You can now run your app by running the app.py file and accessing it at `http://127.0.0.1:8000`.


## Widgets

Widgets are the building blocks of the app. They are the components that will be used to build the app. Widgets are defined in the `app.py` file.

The concept of the numerous app framework is to support anywidget and not have our own widget specification. We are adding the minimum amount of functionality to anywidget to make it work in the numerous app framework, which is basically to collect widgets, link them with your html template and then serve them.

To get started, We do supply a set of anywidgets in the numerous-widgets package. This package is used by the bootstrap app and will be installed when you bootstrap your app.

## HTML Template

The html template is the main template file which will be used to define the layout of the app. It is a Jinja2 template file, which means you can use Jinja2 syntax to define the layout of the app. This allows you to compose the layout of the app using widgets, but keep it clean and separate from the business logic and reactivity.

When you have exported your widgets from you app.py file, you can include them in your html template by using the `{{ widget_key }}` to insert the widget into the layout.

You can include CSS, JS and image files in the static folder, and reference them in the html template like this: `<link href="static/css/styles.css" rel="stylesheet">`

## Testing

### Python Tests

The framework includes a comprehensive test suite for Python code using pytest. To run the tests:

```bash
pytest
```

For coverage information:

```bash
pytest --cov=numerous.apps
```

### JavaScript Tests

The client-side JavaScript (`numerous.js`) can be tested using Jest. The test suite is located in the `tests/js` directory.

To run the JavaScript tests:

1. Make sure you have Node.js installed
2. Install the required npm dependencies:
   ```bash
   npm install
   ```
3. Run the tests:
   ```bash
   npm test
   ```

For JavaScript test coverage:

```bash
npm run test:coverage
```

The JavaScript tests cover key functionality:
- The `WidgetModel` class for state management
- The `WebSocketManager` for client-server communication
- Utility functions for logging and debugging

To add new JavaScript tests, follow the examples in the `tests/js` directory.

JavaScript tests are automatically run:
- As part of the pre-commit hooks when pushing code
- In the GitHub CI/CD pipeline for every push to the repository
- Coverage reports are generated and archived as artifacts in GitHub Actions

### Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality and prevent issues before they're committed. Both Python and JavaScript tests are included in the pre-commit workflow:

- Python tests run automatically before pushing code
- JavaScript tests run automatically before pushing code

To install the pre-commit hooks:

```bash
pre-commit install --hook-type pre-commit --hook-type pre-push
```

This ensures that all tests pass before code is pushed to the repository.

## Authentication

Numerous Apps includes a pluggable authentication system that allows you to protect your apps with user authentication. The framework supports multiple authentication providers out of the box and allows you to create custom providers.

### Quick Start with Authentication

Bootstrap an app with authentication enabled:

```bash
# Environment variable-based authentication (simple, good for development)
numerous-bootstrap my_app --with-auth

# Database-based authentication (SQLite, good for production)
numerous-bootstrap my_app --with-db-auth
```

### Adding Authentication to an Existing App

If you have an existing Numerous App without authentication and want to add it, follow these steps:

**1. Original app without authentication:**

```python
from numerous.apps import create_app
import numerous.widgets as wi

def run_app():
    counter = wi.Number(default=0, label="Counter:")
    
    def on_click(event):
        counter.value += 1
    
    button = wi.Button(label="Click me", on_click=on_click)
    return {"counter": counter, "button": button}

app = create_app(
    template="index.html.j2",
    dev=True,
    app_generator=run_app,
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

**2. Add authentication by importing a provider and passing it to `create_app`:**

```python
from numerous.apps import create_app
from numerous.apps.auth.providers.env_auth import EnvAuthProvider
import numerous.widgets as wi

def run_app():
    counter = wi.Number(default=0, label="Counter:")
    
    def on_click(event):
        counter.value += 1
    
    button = wi.Button(label="Click me", on_click=on_click)
    return {"counter": counter, "button": button}

# Create the authentication provider
auth_provider = EnvAuthProvider()

app = create_app(
    template="index.html.j2",
    dev=True,
    app_generator=run_app,
    auth_provider=auth_provider,  # Add this line
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

**3. Configure users via environment variables:**

```bash
# Set the JWT secret (required for production)
export NUMEROUS_JWT_SECRET="your-secure-secret-key"

# Configure users
export NUMEROUS_AUTH_USERS='[
  {"username": "admin", "password": "admin123", "is_admin": true},
  {"username": "user", "password": "userpass123", "roles": ["viewer"]}
]'

# Run your app
python app.py
```

That's it! Your app now requires authentication. Users will be redirected to a login page when accessing protected routes.

**Alternative: Use Database Authentication**

For production apps or when you need user management features, use the database provider instead:

```python
from numerous.apps import create_app
from numerous.apps.auth.providers.database_auth import DatabaseAuthProvider

# Install dependencies first: pip install numerous-apps[auth-db]

auth_provider = DatabaseAuthProvider(
    database_url="sqlite+aiosqlite:///./app_auth.db",
    jwt_secret="your-secure-secret-key",
)

app = create_app(
    template="index.html.j2",
    dev=True,
    app_generator=run_app,
    auth_provider=auth_provider,
)
```

Then create users programmatically or via a management script:

```python
import asyncio
from numerous.apps.auth.models import CreateUserRequest

async def setup_users():
    await auth_provider.create_user(CreateUserRequest(
        username="admin",
        password="securepassword123",
        email="admin@example.com",
        is_admin=True,
    ))

asyncio.run(setup_users())
```

### Authentication Providers

#### 1. Environment Variable Authentication (`EnvAuthProvider`)

Simple authentication using environment variables. Perfect for development or single-user deployments.

**Setup:**

```python
from numerous.apps import create_app
from numerous.apps.auth.providers.env_auth import EnvAuthProvider

auth_provider = EnvAuthProvider()

app = create_app(
    template="index.html.j2",
    dev=True,
    app_generator=run_app,
    auth_provider=auth_provider,
)
```

**Configuration (environment variables):**

```bash
# JWT secret for token signing (required for production)
export NUMEROUS_JWT_SECRET="your-secure-secret-key"

# Users configuration (JSON array)
export NUMEROUS_AUTH_USERS='[
  {"username": "admin", "password": "admin123", "is_admin": true},
  {"username": "user", "password": "userpass123", "roles": ["viewer"]}
]'
```

**User configuration options:**
- `username` (required): The login username
- `password` (required): The login password
- `is_admin` (optional): Whether the user has admin privileges
- `roles` (optional): Array of role names for role-based access control
- `email` (optional): User's email address

#### 2. Database Authentication (`DatabaseAuthProvider`)

Full-featured authentication with database storage. Supports PostgreSQL (production) and SQLite (development).

**Installation:**

```bash
pip install numerous-apps[auth-db]
```

**Setup with SQLite (development):**

```python
from numerous.apps import create_app
from numerous.apps.auth.providers.database_auth import DatabaseAuthProvider

auth_provider = DatabaseAuthProvider(
    database_url="sqlite+aiosqlite:///./app_auth.db",
    jwt_secret="your-secure-secret-key",
)

app = create_app(
    template="index.html.j2",
    dev=True,
    app_generator=run_app,
    auth_provider=auth_provider,
)
```

**Setup with PostgreSQL (production):**

```python
auth_provider = DatabaseAuthProvider(
    database_url="postgresql+asyncpg://user:password@localhost/mydb",
    jwt_secret="your-secure-secret-key",
)
```

**Creating users programmatically:**

```python
from numerous.apps.auth.models import CreateUserRequest

# Create a user
await auth_provider.create_user(CreateUserRequest(
    username="newuser",
    password="securepassword123",
    email="user@example.com",
    roles=["editor"],
    is_admin=False,
))
```

### Authentication Flow

1. **Unauthenticated Access**: Users accessing protected routes are redirected to `/login`
2. **Login**: Users submit credentials via the login form
3. **Token Generation**: On successful auth, the server returns:
   - Access token (short-lived, stored in cookie)
   - Refresh token (long-lived, httpOnly cookie)
4. **Authenticated Requests**: Browser automatically sends tokens with requests
5. **Token Refresh**: Access tokens are automatically refreshed using the refresh token
6. **Logout**: Tokens are revoked and cookies cleared

### Configuring Protected Routes

By default, all routes except `/login` and auth API endpoints are protected. You can customize this:

```python
app = create_app(
    template="index.html.j2",
    auth_provider=auth_provider,
    # Routes that don't require authentication
    public_routes=["/public", "/api/public/*"],
    # Only protect specific routes (None = protect all non-public)
    protected_routes=None,
)
```

### Accessing User Information

#### In Python (server-side)

Use FastAPI dependencies to access the current user:

```python
from fastapi import Depends
from numerous.apps.auth.dependencies import CurrentUser, OptionalUser

@app.get("/api/profile")
async def get_profile(user: CurrentUser):
    return {"username": user.username, "roles": user.roles}

@app.get("/api/data")
async def get_data(user: OptionalUser):
    if user:
        return {"data": "authenticated data"}
    return {"data": "public data"}
```

#### In JavaScript (client-side)

The auth state is available via `window.numerousAuth`:

```javascript
// Check if authenticated
if (window.numerousAuth && window.numerousAuth.isAuthenticated()) {
    const user = window.numerousAuth.getUserContext();
    console.log(`Logged in as: ${user.username}`);
    console.log(`Is admin: ${user.is_admin}`);
    console.log(`Roles: ${user.roles.join(', ')}`);
}

// Logout
window.numerousAuth.logout();
```

### Custom Login Page

You can provide a custom login template:

```python
app = create_app(
    template="index.html.j2",
    auth_provider=auth_provider,
    login_template="my_custom_login.html.j2",
)
```

Your custom template should include a form that POSTs to `/api/auth/login` with `username` and `password` fields.

### Creating a Custom Auth Provider

Implement the `AuthProvider` protocol to create custom authentication:

```python
from numerous.apps.auth.base import BaseAuthProvider
from numerous.apps.auth.models import AuthResult, User

class MyCustomAuthProvider(BaseAuthProvider):
    async def authenticate(self, username: str, password: str) -> AuthResult:
        # Your authentication logic
        user = await self._verify_credentials(username, password)
        if user:
            return AuthResult.ok(user)
        return AuthResult.fail("Invalid credentials")
    
    async def get_user(self, user_id: str) -> User | None:
        # Retrieve user by ID
        return await self._fetch_user(user_id)
    
    async def get_user_by_username(self, username: str) -> User | None:
        # Retrieve user by username
        return await self._fetch_user_by_username(username)
```

### Security Considerations

1. **JWT Secret**: Always use a strong, unique secret in production
   ```bash
   # Generate a secure secret
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **HTTPS**: In production, always use HTTPS. Set `secure=True` for cookies.

3. **Password Requirements**: The `CreateUserRequest` model enforces minimum 8-character passwords.

4. **Token Expiry**: Default settings:
   - Access tokens: 15 minutes
   - Refresh tokens: 7 days

5. **Rate Limiting**: Consider adding rate limiting to the login endpoint in production.

## Template Customization

The framework uses internal templates for login pages, error screens, splash screens, and other UI elements. You can export and customize these templates to match your application's branding.

### Exporting Templates

Use the `--export-templates` flag when bootstrapping:

```bash
numerous-bootstrap my_app --export-templates
```

Or export templates to an existing project:

```bash
numerous-bootstrap existing_app --export-templates --skip-deps --run-skip
```

### Exported Files

The following files are exported to your project:

| Directory | Files | Purpose |
|-----------|-------|---------|
| `templates/` | `login.html.j2` | Login page template |
| `templates/` | `error.html.j2` | Error page template |
| `templates/` | `error_modal.html.j2` | Error modal template |
| `templates/` | `splash_screen.html.j2` | Loading splash screen |
| `templates/` | `session_lost_banner.html.j2` | Session disconnection banner |
| `static/css/` | `numerous-base.css` | Base CSS styles for all templates |

### Customization Tips

1. **Maintain Template Variables**: Keep the existing Jinja2 variables (like `{{ error_message }}`) as the framework passes these values.

2. **CSS Variables**: The `numerous-base.css` uses CSS custom properties for easy theming:
   ```css
   :root {
       --numerous-primary: #4f46e5;
       --numerous-background: #f8fafc;
       /* ... */
   }
   ```

3. **Partial Customization**: You only need to export the templates you want to customize. The framework will use its internal versions for any missing templates.

## Multi-App Support

Numerous Apps supports combining multiple applications into a single server. This is useful for:

- Deploying multiple related apps under one domain
- Separating public and authenticated areas
- Sharing resources (static files, themes, authentication) across apps

### Basic Multi-App Setup

```python
from numerous.apps import create_app, combine_apps

# Create individual apps with path prefixes
app1 = create_app(
    template="app1/index.html.j2",
    path_prefix="/app1",
    app_generator=run_app1,
)

app2 = create_app(
    template="app2/index.html.j2",
    path_prefix="/app2",
    app_generator=run_app2,
)

# Combine into a single server
main_app = combine_apps(
    apps={"/app1": app1, "/app2": app2},
    root_redirect="/app1",  # Redirect "/" to "/app1"
    title="My Multi-App Server",
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(main_app, host="127.0.0.1", port=8000)
```

### Path Prefix Configuration

When creating apps for multi-app deployment, always specify the `path_prefix` parameter:

```python
app = create_app(
    template="index.html.j2",
    path_prefix="/myapp",  # Must match the key in combine_apps
    app_generator=run_app,
)
```

### Mixed Authentication

Apps can have different authentication requirements:

```python
from numerous.apps import create_app, combine_apps
from numerous.apps.auth.providers.database_auth import DatabaseAuthProvider

# Public app - no authentication
public_app = create_app(
    template="public/index.html.j2",
    path_prefix="/public",
    app_generator=run_public_app,
)

# Admin app - requires authentication
auth_provider = DatabaseAuthProvider(
    database_url="sqlite+aiosqlite:///./auth.db",
    jwt_secret="your-secret-key",
)

admin_app = create_app(
    template="admin/index.html.j2",
    path_prefix="/admin",
    app_generator=run_admin_app,
    auth_provider=auth_provider,
)

# Combine apps
main_app = combine_apps(
    apps={
        "/public": public_app,
        "/admin": admin_app,
    },
    root_redirect="/public",
)
```

### Shared Static Files

Share static files across all apps:

```python
main_app = combine_apps(
    apps={"/app1": app1, "/app2": app2},
    shared_static_dir="./shared_static",  # Mounted at /shared-static/
)
```

Access shared files in templates:
```html
<link href="/shared-static/css/theme.css" rel="stylesheet">
```

### Shared Theme CSS

Provide a shared CSS theme as a string:

```python
theme_css = """
:root {
    --primary-color: #4f46e5;
    --background-color: #f8fafc;
}
"""

main_app = combine_apps(
    apps={"/app1": app1, "/app2": app2},
    shared_theme_css=theme_css,  # Available at /shared-static/css/theme.css
)
```

### Shared Authentication

Use a single authentication provider across all apps:

```python
shared_auth = DatabaseAuthProvider(
    database_url="sqlite+aiosqlite:///./shared_auth.db",
    jwt_secret="shared-secret-key",
)

main_app = combine_apps(
    apps={"/app1": app1, "/app2": app2},
    shared_auth_provider=shared_auth,
)
```

### combine_apps Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `apps` | `dict[str, NumerousApp]` | Dictionary mapping path prefixes to app instances |
| `shared_static_dir` | `Path \| str \| None` | Path to shared static files directory |
| `shared_theme_css` | `str \| None` | CSS string for shared theme |
| `root_redirect` | `str \| None` | Path to redirect "/" to (e.g., "/app1") |
| `shared_auth_provider` | `AuthProvider \| None` | Shared authentication provider |
| `title` | `str` | Title for the combined application |

### Health Check Endpoint

Combined apps automatically include a health check endpoint at `/health`:

```bash
curl http://localhost:8000/health
# {"status": "healthy", "apps": "['/app1', '/app2']"}
```

## How It Works

The **Numerous Apps** framework is built on FastAPI and uses uvicorn to serve the app.

When the browser requests the root URL, the server serves the HTML content by inserting a `div` with each widget's corresponding key as the ID into the HTML template using Jinja2.

The framework includes a `numerous.js` file, a JavaScript library that fetches widgets from the server and renders them. This JavaScript also acts as a WebSocket client, connecting widgets with the server and the Python app code. Widgets are passed the corresponding `div` and then render themselves within it.

Each new instance or session of the app is created by running `app.py` in a new process or thread. The client obtains a session ID from the server and uses this ID to connect. The server uses this ID to route client requests to the correct process or thread.
