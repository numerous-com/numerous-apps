import anywidget, traitlets
from .backend import Backend
import uvicorn
from fastapi import Request
from ._builtins import ParentVisibility

ignored_traits = [
            "comm",
            "layout",
            "log",
            "tabbable",
            "tooltip",
            "keys",
            "_esm",
            "_css",
            "_anywidget_id",
            "_msg_callbacks",
            "_dom_classes",
            "_model_module",
            "_model_module_version",
            "_model_name",
            "_property_lock",
            "_states_to_send",
            "_view_count",
            "_view_module",
            "_view_module_version",
            "_view_name",
        ]

def transform_widgets(widgets: dict[str, anywidget.AnyWidget]):
    transformed = {}
    for key, widget in widgets.items():
        widget_key = f"{key}"

        # Get all the traits of the widget
        args = widget.trait_values()
        traits = widget.traits()
        
        # Remove ignored traits
        for trait_name in ignored_traits:
            args.pop(trait_name, None)
            traits.pop(trait_name, None)

        # Handle both URL-based and string-based widget definitions
        module_source = widget._esm
        if isinstance(module_source, str) and not (module_source.startswith('http') or 
                                                 module_source.startswith('./') or 
                                                 module_source.startswith('/')):
            # If it's a string and not a URL, ensure it's a valid ES module
            if not 'export default' in module_source:
                module_source = f"{module_source}\nexport default {{ render }};"

        transformed[widget_key] = {
            "moduleUrl": module_source,  # Now this can be either a URL or a JS string
            "defaults": args,
        }
    return transformed

class App:
    def __init__(self, widgets: dict, template: str, dev: bool):
        self.widgets = widgets
        self.transformed_widgets = transform_widgets(widgets)

        self.backend = Backend(self.widgets, self.transformed_widgets, template, dev)

    def run(self):
        self.backend.run()

def app(widgets: dict, template: str, dev: bool):
    return App(widgets, template, dev)