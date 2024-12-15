# Numerous Apps

A new Python framework in development, aiming to provide a powerful yet simple approach for building reactive web applications. Numerous Apps will empower developers to create modern, scalable web applications using familiar Python patterns while maintaining clean separation between business logic and presentation.

Our framework will not keep everything in one file, but instead will be modular and allow for easy separation of concerns. We do believe that the boilerplate introduced to separate the business logic from the presentation is worth it, but we want to make it as easy as possible to use.

---

## Planned Features

### 🚀 **Simple Yet Powerful**
- **Simple Syntax:** Write reactive web apps using standard Python and HTML 
- **Get Started Quickly:** Use numerous-bootstrap command to create a new app in seconds
- **Lightweight Core:** Built on top of FastAPI, Uvicorn, Jinja2 and AnyWidget keeps the core lightweight and simple.

### 🔧 **Modern Architecture**
- **Component-Based:** Built on [AnyWidgets](https://anywidgets.dev/) for reusable, framework-agnostic components
- **Clean Separation:** Python for logic, CSS for styling, Jinja2 for templates
- **Process Isolation:** Each session runs independently for better stability and scaling

### 🎨 **Full Creative Control**
- **Framework-Agnostic UI:** No imposed styling or components - complete freedom in design
- **Custom Widget Support:** Easy integration of your own HTML/CSS/JS components and static files
- **Flexible Templating:** Jinja2 for powerful layout composition

### 💪 **Built for Scale**
- **Multi-Client Ready:** The framework is designed to be scalable and can handle multiple clients simultaneously. Communication and execution logic can be added to support distributed app instances.
- **AI-Integration:** Seamless integration with AI agents and models
- **Developer-Friendly:** Use your favorite IDE and development tools - no special IDE or notebook needed

## Getting Started

This is a guide on how to get started with Numerous Apps. Since a numerous app is composed of multiple files, we will use the bootstrap app to get started. The bootstrap app is a minimal app that will help you get started with Numerous Apps by providing a basic structure and some example widgets.

First install the framework:

```bash
pip install numerous-apps
```

Then bootstrap your first app:

```bash
numerous-bootstrap my_app   
```

This will create a new directory called `my_app` with the basic structure of a Numerous App. The command will boostrap the necessary files and folders, and install the dependencies. Finally the app server (uvicorn) will be started, and you can access the app at `http://127.0.0.1:8000`.

You can try out the app and then start making changes to the code.

## App File Structure

The minimal app consists of the following files:

- `app.py`: The main app file defining the widgets, business logic and reactivity.
- `index.html.j2`: The main template file which will be used to define the layout of the app.
- `static/`: A folder for static files, which will be served as-is by the server. Use it for images, css, js, etc.
- `requirements.txt`: The dependencies for the app.

## How to build your app from scratch

You can use the bootstrap app as a starting point, but here is a walkthrough on how to build your app from scratch you can read if you want to understand how the framework works and how to use it to develop your own apps.

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

## How it works

The numerous apps framework is built on FastAPI and using uvicorn to serve the app. The app is served as a static file server, which means that the html template is served as a static file. 
When the browser requests the root url, the server will serve the html content created by inserting a div with the id of each widget into the html template using jinja2.

The framework includes a numerous.js file which is a javascript library fetch the widgets from the server and render them. This javascript also acts as a websocket client to the server, connecting the widgets with the server and further to the Python app code. The widgets are passed the div with corresponding id, and then the widget renders itself into the div.

Each new instance or session of the app is created by launching running 'app.py' in a new process or thread. The client obtains a session id from the server, and then uses this id to connect to the server. The server then uses this id to route the client requests to the correct process or thread.
