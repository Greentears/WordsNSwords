// First start (or "Change name"): ask for a name, then load that name's words from the repository.
import { h } from "./h";
import { userSlug, type App } from "../state";

export function welcome(root: HTMLElement, app: App, done: () => void): void {
  const message = h("p", { class: "muted", role: "status" });
  const actions = h("div", { class: "stack" });
  const input = h("input", { class: "text-in", type: "text", placeholder: "Your name", autocomplete: "given-name", autocapitalize: "words", "aria-label": "Your name" }) as HTMLInputElement;
  const go = h("button", { class: "btn primary wide", type: "button" }, "Start") as HTMLButtonElement;

  const busy = (on: boolean) => { go.disabled = on; input.disabled = on; };

  async function open(useStarter: boolean) {
    const name = input.value.trim();
    if (!userSlug(name)) { message.textContent = "Please type a name (letters or numbers)."; return; }
    busy(true); actions.replaceChildren(); message.textContent = "Loading your words…";
    app.settings.user = name;
    const result = await app.openUser(name, useStarter);
    if (result === "ok") { app.saveSettings(); await app.pending; done(); return; }
    app.settings.user = "";
    busy(false);
    if (result === "offline") { message.textContent = "Could not reach the word lists. Connect to the internet for the first start, then try again."; return; }
    message.textContent = `No word list found for "${name}" in the repository (users/${userSlug(name)}/${app.deckId}). Start with the starter deck instead? You can add your own words to the repository later and press "Update words" in More.`;
    actions.replaceChildren(h("button", { class: "btn primary wide", type: "button", onclick: () => open(true) }, "Use the starter deck"),
      h("button", { class: "btn wide", type: "button", onclick: () => { actions.replaceChildren(); message.textContent = ""; input.focus(); } }, "Try another name"));
  }

  go.addEventListener("click", () => open(false));
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); open(false); } });
  root.replaceChildren(h("div", { class: "welcome" },
    h("h1", null, "WordsNSwords"),
    h("p", { class: "muted" }, "Type your name. It is also your hero's name, and it picks your word list in the repository (users/<name>)."),
    input, go, message, actions));
  setTimeout(() => input.focus(), 0);
}
