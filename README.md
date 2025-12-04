<p align="center">
  <img src="logo-with-text.svg" alt="Numerous Apps" width="320">
</p>

<p align="center">
  <strong>Build reactive Python web apps with full creative control</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/numerous-apps/"><img src="https://img.shields.io/pypi/v/numerous-apps" alt="PyPI version"></a>
  <a href="https://github.com/numerous-com/numerous-app/blob/main/LICENSE.md"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python 3.12+"></a>
</p>

---

**Numerous Apps** is a Python framework for building modern, reactive web applications. Create powerful apps using familiar Python patterns while maintaining complete control over your UI design.

## ✨ Features

- **🐍 Pure Python** — Write your app logic in Python, no JavaScript required
- **🎨 Full Creative Control** — No enforced styling; use any CSS framework or custom design
- **⚡ Reactive** — Real-time updates via WebSocket communication
- **🧩 Component-Based** — Built on [anywidget](https://anywidget.dev/) for reusable, framework-agnostic components
- **🚀 Quick Start** — Bootstrap a new app in seconds with the CLI
- **📦 Lightweight** — Built on FastAPI, Uvicorn, and Jinja2
- **🔐 Authentication** — Pluggable auth system with ENV or database providers
- **🏗️ Multi-App Support** — Combine multiple apps into a single server with shared resources

## 🚀 Quick Start

Install the framework and create your first app in seconds:

```bash
pip install numerous-apps
numerous-bootstrap my_app
```

This creates a new app in `my_app/`, installs dependencies, and starts the server at http://127.0.0.1:8000.

To run your app again:

```bash
cd my_app
python app.py
```

## 📖 How It Works

A Numerous App consists of:

| File | Purpose |
|------|---------|
| `app.py` | Define widgets, business logic, and reactivity |
| `index.html.j2` | Jinja2 template for your app layout |
| `static/` | CSS, JavaScript, and images |
| `requirements.txt` | App dependencies |

### Example App

**app.py**
```python
import numerous.widgets as wi
from numerous.apps import create_app

def run_app():
    counter = wi.Number(default=0, label="Counter:")
    
    def on_click(event):
        counter.value += 1
    
    button = wi.Button(label="Click me", on_click=on_click)
    
    return {"counter": counter, "button": button}

app = create_app(template="index.html.j2", dev=True, app_generator=run_app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

**index.html.j2**
```html
<!DOCTYPE html>
<html>
<head>
    <title>My App</title>
</head>
<body>
    <h1>Counter App</h1>
    <div style="display: flex; gap: 10px; align-items: center;">
        {{ counter }}
        {{ button }}
    </div>
</body>
</html>
```

## 🎯 Who Is This For?

Numerous Apps is perfect if you:

- Want to build Python web apps with **full control over styling and layout**
- Need **tight integration** between a Python backend and reactive UI
- Prefer using **standard development tools** (no special IDE or notebook required)
- Want to create **reusable anywidget components** that work across frameworks

## 🧩 Widgets

Use widgets from the companion [numerous-widgets](https://github.com/numerous-com/numerous-widgets) package, or create your own using the [anywidget](https://anywidget.dev/) specification.

```python
import numerous.widgets as wi

# Available widgets
counter = wi.Number(default=0, label="Value:")
button = wi.Button(label="Submit", on_click=handler)
dropdown = wi.DropDown(["A", "B", "C"], label="Select:")
tabs = wi.Tabs(["Tab 1", "Tab 2", "Tab 3"])
# ... and more
```

## 🔐 Authentication

Protect your apps with built-in authentication. Bootstrap with auth enabled:

```bash
# Environment variable-based auth (simple)
numerous-bootstrap my_app --with-auth

# Database-based auth (SQLite)
numerous-bootstrap my_app --with-db-auth

# Export internal templates for customization
numerous-bootstrap my_app --export-templates
```

Or add authentication to an existing app:

```python
from numerous.apps import create_app
from numerous.apps.auth.providers.env_auth import EnvAuthProvider

auth_provider = EnvAuthProvider()
app = create_app(
    template="index.html.j2",
    app_generator=run_app,
    auth_provider=auth_provider,
)
```

Configure users via environment variables:

```bash
export NUMEROUS_JWT_SECRET="your-secret-key"
export NUMEROUS_AUTH_USERS='[{"username": "admin", "password": "admin123", "is_admin": true}]'
```

See [Authentication Documentation](docs/README.md#authentication) for full details including database auth, custom providers, and security best practices.

## 🏗️ Multi-App Support

Deploy multiple apps on a single server, each with its own authentication and configuration:

```python
from numerous.apps import create_app, combine_apps

# Create individual apps with path prefixes
public_app = create_app(
    template="public/index.html.j2",
    path_prefix="/public",
    app_generator=run_public_app,
)

admin_app = create_app(
    template="admin/index.html.j2",
    path_prefix="/admin",
    app_generator=run_admin_app,
    auth_provider=auth_provider,
)

# Combine into a single server
main_app = combine_apps(
    apps={"/public": public_app, "/admin": admin_app},
    root_redirect="/public",
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(main_app, host="127.0.0.1", port=8000)
```

See [Multi-App Documentation](docs/README.md#multi-app-support) for details on shared authentication, static files, and themes.

## 📚 Documentation

For detailed documentation, visit the [docs](docs/README.md) or check out:

- [Building from Scratch](docs/README.md#building-your-app-from-scratch) — Step-by-step guide
- [Widget Reference](docs/README.md#widgets) — Available widgets and customization
- [Authentication](docs/README.md#authentication) — Protect your apps with user login
- [Multi-App Support](docs/README.md#multi-app-support) — Combine multiple apps into one server
- [Template Customization](docs/README.md#template-customization) — Customize login pages, error screens, and more
- [How It Works](docs/README.md#how-it-works) — Architecture overview

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- Setting up your development environment
- Running tests
- Submitting pull requests

## 📄 License

[MIT License](LICENSE.md) — Numerous ApS
