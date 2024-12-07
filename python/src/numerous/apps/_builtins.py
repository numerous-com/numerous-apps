import anywidget, traitlets

class ParentVisibility(anywidget.AnyWidget):
    _esm = """
    function render({ model, el }) {
      let parent_el = el.parentElement;
      el.style.display = "none";
      

      function set_visibility(visible) {
      
        if (visible) {

          parent_el.classList.remove("numerous-apps-hidden");
          parent_el.classList.add(`numerous-apps-visible-${model.get('display')}`);
        } else {
          parent_el.classList.add("numerous-apps-hidden");
          parent_el.classList.remove(`numerous-apps-visible-${model.get('display')}`);
        }
      }
      console.log("model.get('visible')", model.get("visible"));
      set_visibility(model.get("visible"));

      model.on("change:visible", set_visibility);
    }
    export default { render };
    """
    _css = """
    .numerous-apps-hidden {
      display: none;
    }
    .numerous-apps-visible-block {
      display: block;
    }
    .numerous-apps-visible-inline {
      display: inline;
    }
    .numerous-apps-visible-inline-block {
      display: inline-block;
    }
    .numerous-apps-visible-flex {
      display: flex;
    }
    .numerous-apps-visible-grid {
      display: grid;
    }
    """

    visible = traitlets.Bool(default_value=True).tag(sync=True)
    display = traitlets.Enum(values=["block", "inline", "inline-block", "flex", "grid"], default_value="block").tag(sync=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self._visible = True

        self.observe(self.toggle_visibility, names="visible")
        self.observe(self._update_visibility, names="visible")
    
    def toggle_visibility(self, event):
        print("toggle_visibility", event)
        self.visible = not self._visible

    def _update_visibility(self, event):
        print("_update_visibility", event)
        self._visible = self.visible

