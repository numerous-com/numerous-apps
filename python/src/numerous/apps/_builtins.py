import anywidget
import traitlets

class ParentVisibility(anywidget.AnyWidget):
    _esm = """
    function render({ model, el }) {
      // Get the parent element - handle both Shadow DOM and regular DOM cases
      let parent_el;
      if (el.getRootNode() instanceof ShadowRoot) {
        // Shadow DOM case
        let shadow_host = el.getRootNode().host;
        parent_el = shadow_host.parentElement;
      } else {
        // Regular DOM case
        parent_el = el.parentElement;
      }
      
      el.style.display = "none";
      
      set_visibility(model.get('visible'));

      function set_visibility(visible) {
        if (!parent_el) return;
        
        if (visible) {
          parent_el.classList.remove("numerous-apps-hidden");
          parent_el.classList.add("numerous-apps-visible");
        } else {
          parent_el.classList.add("numerous-apps-hidden");
          parent_el.classList.remove("numerous-apps-visible");
        }
      }

      model.on("change:visible", (value) => set_visibility(value));
    }
    export default { render };
    """
    _css = """
    .numerous-apps-visible {
        display: var(--display-value) !important;
    }
    .numerous-apps-hidden {
        display: none !important;
    }
    [data-display="block"] {
        --display-value: block;
    }
    [data-display="flex"] {
        --display-value: flex;
    }
    [data-display="inline"] {
      --display-value: inline;
    }
    [data-display="inline-block"] {
      --display-value: inline-block;
    }
    [data-display="grid"] {
      --display-value: grid;
    }
    """

    visible = traitlets.Bool(default_value=True).tag(sync=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._visible = True
        self.observe(self._update_visibility, names="visible")
    
    def _update_visibility(self, event):
        self._visible = event.new

def tab_visibility(tabs_widget):
    visibility_widgets = []
    for tab in tabs_widget.tabs:
        visibility_widgets.append(ParentVisibility(visible=tab == tabs_widget.active_tab))

    def on_tab_change(event):
        for i, tab in enumerate(tabs_widget.tabs):
            visibility_widgets[i].visible = tab == event.new

    tabs_widget.observe(on_tab_change, names='active_tab')
    return visibility_widgets



