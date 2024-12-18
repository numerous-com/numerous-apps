# Numerous Apps

A new Python framework in development, aiming to provide a powerful yet simple approach for building reactive web applications. **Numerous Apps** empowers developers to create modern, scalable web applications using familiar Python patterns while maintaining a clean separation between business logic and presentation.

## Who is this for?

This framework is for teams who want to build fantastic apps with a modular approach and a powerful Python backend. It is for apps exposing functionality built using Python requiring a reactive UI tightly integrated with the backend.

If you are:

- Using standard development tools and languages.
- Seeking to have full control over the layout, components and styling for your apps.
- OK with a bit of boilerplate to keep your code clean and organized.
- Creating a library of your own AnyWidgets that you can use in other Python app frameworks or React apps.

This framework is for you.

Our framework emphasizes modularity, allowing for easy separation of concerns. While we acknowledge that the boilerplate introduced to separate business logic from presentation is a trade-off, we strive to make it as easy as possible to use.

---

## Planned Features

### 🚀 **Simple Yet Powerful**
- **Intuitive Syntax:** Develop reactive web apps using standard Python and HTML.
- **Quick Start:** Utilize the `numerous-bootstrap` command to create a new app in seconds.
- **Lightweight Core:** Built atop FastAPI, Uvicorn, Jinja2, and AnyWidget to keep the core lightweight and simple.

### 🔧 **Modern Architecture**
- **Component-Based:** Leverage [AnyWidget](https://anywidget.dev/) for reusable, framework-agnostic components.
- **Clear Separation:** Use Python for logic, CSS for styling, and Jinja2 for templates.
- **Process Isolation:** Each session runs independently, enhancing stability and scalability.

### 🎨 **Full Creative Control**
- **Framework-Agnostic UI:** No enforced styling or components from our side — You have complete freedom in design.
- **Custom Widget Support:** Easily integrate your own HTML, CSS, JS components, and static files.
- **Flexible Templating:** Utilize Jinja2 and HTML for powerful layout composition.

### 💪 **Built for Scale**
- **Multi-Client Ready:** Designed to scale and handle multiple clients simultaneously, with support for distributed app instances.
- **AI Integration:** Seamless integration with AI agents and models.
- **Developer-Friendly:** Compatible with your favorite IDE and development tools—no special IDE or notebook needed.

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

...

counter = wi.Number(default=0, label="Counter:", fit_to_content=True)

def on_click(event):
    # Increment the counter
    counter.value += 1

button = wi.Button(label="Click me", on_click=on_click)
```

You can also use the `observe` method to create reactivity which is provided directly by the AnyWidget framework.

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

The concept of the numerous app framework is to support AnyWidget and not have our own widget specification. We are adding the minimum amount of functionality to AnyWidget to make it work in the numerous app framework, which is basically to collect widgets, link them with your html template and then serve them.

To get started, We do supply a set of AnyWidgets in the numerous-widgets package. This package is used by the bootstrap app and will be installed when you bootstrap your app.

## HTML Template

The html template is the main template file which will be used to define the layout of the app. It is a Jinja2 template file, which means you can use Jinja2 syntax to define the layout of the app. This allows you to compose the layout of the app using widgets, but keep it clean and separate from the business logic and reactivity.

When you have exported your widgets from you app.py file, you can include them in your html template by using the `{{ widget_key }}` to insert the widget into the layout.

You can include CSS, JS and image files in the static folder, and reference them in the html template like this: `<link href="static/css/styles.css" rel="stylesheet">`

## How It Works

The **Numerous Apps** framework is built on FastAPI and uses Uvicorn to serve the app.

When the browser requests the root URL, the server serves the HTML content by inserting a `div` with each widget's corresponding key as the ID into the HTML template using Jinja2.

The framework includes a `numerous.js` file, a JavaScript library that fetches widgets from the server and renders them. This JavaScript also acts as a WebSocket client, connecting widgets with the server and the Python app code. Widgets are passed the corresponding `div` and then render themselves within it.

Each new instance or session of the app is created by running `app.py` in a new process or thread. The client obtains a session ID from the server and uses this ID to connect. The server uses this ID to route client requests to the correct process or thread.
