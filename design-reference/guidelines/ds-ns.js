// Resolves the compiled design-system namespace; falls back to compiling the component sources in-browser
// (needs React + Babel standalone loaded first) when _ds_bundle.js isn't available.
window.DS = (function () {
  for (const k of Object.getOwnPropertyNames(window)) {
    try { const v = window[k]; if (v && typeof v === "object" && v.Button && v.DataGrid && v.TextField) return v; } catch (e) {}
  }
  const root = new URL("..", document.currentScript.src).href;
  const files = ["inputs/Button", "inputs/TextField", "inputs/Link", "inputs/IconButton", "navigation/AppBar", "status/StageChip", "navigation/Tabs", "navigation/SideNav",
    "feedback/Alert", "feedback/Snackbar", "feedback/Dialog", "data/Table", "data/DataGrid", "data/BarChart",
    "data/FieldList", "surfaces/Paper", "surfaces/PageHeader"];
  const ns = {};
  for (const f of files) {
    const x = new XMLHttpRequest(); x.open("GET", root + "components/" + f + ".jsx", false); x.send();
    const name = f.split("/")[1];
    const src = x.responseText.replace(/^import .*$/gm, "").replace(/export function/g, "function");
    const code = Babel.transform(src + "\nreturn " + name + ";", { presets: ["react"], parserOpts: { allowReturnOutsideFunction: true } }).code;
    ns[name] = new Function("React", code)(React);
  }
  return ns;
})();
