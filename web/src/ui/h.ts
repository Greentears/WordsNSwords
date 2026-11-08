// Tiny DOM helper: h("div", {class: "x", onclick: fn}, child, "text").
type Child = Node | string | number | null | false | undefined;
export function h<K extends keyof HTMLElementTagNameMap>(
  tag: K, props?: Record<string, any> | null, ...children: (Child | Child[])[]
): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props ?? {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
    else if (k === "value") (el as any).value = v;
    else if (k in el && k !== "list") (el as any)[k] = v;
    else el.setAttribute(k, v === true ? "" : String(v));
  }
  const add = (c: Child | Child[]) => {
    if (Array.isArray(c)) c.forEach(add);
    else if (c !== null && c !== false && c !== undefined) el.append(c instanceof Node ? c : String(c));
  };
  children.forEach(add);
  return el;
}
export const clear = (el: Element) => { while (el.firstChild) el.removeChild(el.firstChild); };
