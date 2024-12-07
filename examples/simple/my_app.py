import numerous.widgets as wi
from numerous.apps import app, ParentVisibility

    

number_input = wi.Number(default=2, label="Number Input", fit_to_content=True)

def increment_number(event): 
    print("incrementing number")
    number_input.value += 1

button = wi.Button(label="Increment", on_click=increment_number)

tab1 = ParentVisibility()

tab_button = wi.Button(label="Tab 1", on_click=tab1.toggle_visibility)

widgets = {
    "number_input": number_input,
    "button": button,
    "tab_button": tab_button,
    "tab1": tab1
}

app = app(widgets, template="index.html.j2", dev=True)

if __name__ == "__main__":
    app.run()

