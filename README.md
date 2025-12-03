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

## 📚 Documentation

For detailed documentation, visit the [docs](docs/README.md) or check out:

- [Building from Scratch](docs/README.md#building-your-app-from-scratch) — Step-by-step guide
- [Widget Reference](docs/README.md#widgets) — Available widgets and customization
- [How It Works](docs/README.md#how-it-works) — Architecture overview

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- Setting up your development environment
- Running tests
- Submitting pull requests

## 📄 License

[MIT License](LICENSE.md) — Numerous ApS
