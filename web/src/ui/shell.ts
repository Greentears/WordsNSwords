import { h, clear } from "./h";
import type { App } from "../state";

export type Tab = "study" | "review" | "dungeon" | "search" | "more";
export type ReviewMode = "typed" | "cloze" | "sentences";
/** The Review tab hosts three practice modes; each mode panel asks the host to switch. */
export interface ReviewHost { mode(): ReviewMode; setMode(m: ReviewMode): void; }

export interface Shell {
  app: App;
  go(tab: Tab): void;
  toast(msg: string): void;
  /** Bottom sheet; returns a close function. */
  sheet(content: Node, opts?: { onClose?: () => void }): () => void;
  confirm(title: string, text: string, okLabel: string, danger?: boolean): Promise<boolean>;
  fullscreen(on: boolean): void;
  /** Show the Study tab on a list prepared by the caller (search, failed words, archived ...). */
  studyView(prepare: () => void, label?: string): void;
  refreshBadges(): void;
}

export function makeSheet(host: HTMLElement) {
  return (content: Node, opts?: { onClose?: () => void }) => {
    const backdrop = h("div", { class: "sheet-backdrop" });
    const panel = h("div", { class: "sheet", role: "dialog", "aria-modal": "true" }, h("div", { class: "sheet-grip" }), content);
    const close = () => { backdrop.remove(); panel.remove(); opts?.onClose?.(); };
    backdrop.addEventListener("click", close);
    host.append(backdrop, panel);
    requestAnimationFrame(() => { backdrop.classList.add("open"); panel.classList.add("open"); });
    return close;
  };
}

export const icon = (name: string) => h("span", { class: "ico", "aria-hidden": "true" }, name);

export function seg<T extends string>(options: [T, string][], value: T, onChange: (v: T) => void): HTMLElement {
  const wrap = h("div", { class: "seg", role: "group" });
  for (const [v, label] of options) {
    const b = h("button", { type: "button", class: "seg-btn" + (v === value ? " on" : ""), "aria-pressed": String(v === value) }, label);
    b.addEventListener("click", () => {
      wrap.querySelectorAll(".seg-btn").forEach((x) => { x.classList.remove("on"); x.setAttribute("aria-pressed", "false"); });
      b.classList.add("on"); b.setAttribute("aria-pressed", "true");
      onChange(v);
    });
    wrap.append(b);
  }
  return wrap;
}

export function toggleRow(label: string, hint: string | null, value: boolean, onChange: (v: boolean) => void): HTMLElement {
  const input = h("input", { type: "checkbox", class: "switch", checked: value });
  input.addEventListener("change", () => onChange(input.checked));
  return h("label", { class: "row toggle" }, h("span", { class: "row-text" }, h("span", { class: "row-title" }, label), hint && h("span", { class: "row-hint" }, hint)), input);
}

export { clear };
