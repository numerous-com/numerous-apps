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