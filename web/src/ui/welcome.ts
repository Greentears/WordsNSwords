// First start (or "Change name"): ask for a name, then load that name's words from the repository.
import { h } from "./h";
import { deckLabel, userSlug, type App } from "../state";

export function welcome(root: HTMLElement, app: App, done: () => void): void {
  const message = h("p", { class: "muted", role: "status" });
  const actions = h("div", { class: "stack" });
  const input = h("input", { class: "text-in", type: "text", placeholder: "Your name", autocomplete: "given-name", autocapitalize: "words", "aria-label": "Your name" }) as HTMLInputElement;
  const go = h("button", { class: "btn primary wide", type: "button" }, "Start") as HTMLButtonElement;

  const busy = (on: boolean) => { go.disabled = on; input.disabled = on; };

  const showStart = (on: boolean) => { go.hidden = !on; };

  async function open(useStarter: boolean, deck?: string) {
    const name = input.value.trim();
    if (!userSlug(name)) { message.textContent = "Please type a name (letters or numbers)."; return; }
    busy(true); showStart(true); actions.replaceChildren(); message.textContent = "Loading your words…";
    app.settings.user = name;
    const result = await app.openUser(name, useStarter, deck);
    if (result === "ok") { app.saveSettings(); await app.pending; done(); return; }
    app.settings.user = "";
    busy(false);
    if (result === "choose") {
      showStart(false);       // picking a language starts it
      message.textContent = `Which language do you want to learn, ${name}?`;
      actions.replaceChildren(...app.availableDecks.map((d) => h("button", { class: "btn primary wide", type: "button", onclick: () => open(false, d) }, deckLabel(d))));
      return;
    }
    if (result === "offline") { message.textContent = "Could not reach the word lists. Connect to the internet for the first start, then try again."; return; }
    // a name the repository doesn't know yet: ask the language, then begin with that language's starter deck
    const decks = await app.templateDecks();
    showStart(false);         // picking a language starts it
    message.textContent = `Welcome, ${name}! Which language do you want to learn? You start with a small starter deck of 20 words and can add your own later.`;
    actions.replaceChildren(...decks.map((d) => h("button", { class: "btn primary wide", type: "button", onclick: () => open(true, d) }, deckLabel(d))),
      h("button", { class: "btn wide", type: "button", onclick: () => { actions.replaceChildren(); message.textContent = ""; showStart(true); input.focus(); } }, "Try another name"));
  }

  go.addEventListener("click", () => open(false));
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); open(false); } });
  root.replaceChildren(h("div", { class: "welcome" },
    h("h1", null, "WordsNSwords"),
    h("p", { class: "muted" }, "Type your name. It is also your hero's name, and it picks your word list in the repository (users/<name>)."),
    input, go, message, actions));
  setTimeout(() => input.focus(), 0);
}
