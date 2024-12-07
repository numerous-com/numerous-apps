import anywidget, traitlets

class ParentVisibility(anywidget.AnyWidget):
    _esm = """
    function render({ model, el }) {
      // Get the host element (the shadow root's host)
      let shadow_host = el.getRootNode().host;
      // Get the real parent element outside the shadow DOM
      let parent_el = shadow_host.parentElement;
      
      el.style.display = "none";
      
      set_visibility(model.get('visible'));

      function set_visibility(visible) {
        if (!parent_el) return;
        
        if (visible) {
          parent_el.classList.remove("numerous-apps-hidden");
          parent_el.classList.add(`numerous-apps-visible-${model.get('display')}`);
        } else {
          parent_el.classList.add("numerous-apps-hidden");
          parent_el.classList.remove(`numerous-apps-visible-${model.get('display')}`);
        }
      }

      model.on("change:visible", (value) => set_visibility(value));
      model.on("change:display", () => {
        set_visibility(model.get('visible'));
      });
    }
    export default { render };
    """
    _css = """
    .numerous-apps-hidden {
      display: none !important;
    }
    .numerous-apps-visible-block {
      display: block !important;
    }
    .numerous-apps-visible-inline {
      display: inline !important;
    }
    .numerous-apps-visible-inline-block {
      display: inline-block !important;
    }
    .numerous-apps-visible-flex {
      display: flex !important;
    }
    .numerous-apps-visible-grid {
      display: grid !important;
    }
    """

    visible = traitlets.Bool(default_value=True).tag(sync=True)
    display = traitlets.Enum(values=["block", "inline", "inline-block", "flex", "grid"], default_value="block").tag(sync=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._visible = True
        self.observe(self._update_visibility, names="visible")
    
    def _update_visibility(self, event):
        self._visible = event.new

