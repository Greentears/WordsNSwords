// Add words: type a word list -> copy the prompt for an AI -> paste its answer -> check -> add on this phone.
import { h, clear } from "./h";
import type { Shell } from "./shell";
import { kvGet, kvSet } from "../store";
import { combineAdditions } from "../core/newwords";
import { sendForReview, GITHUB_REPO } from "../core/github";

const TOKEN_KEY = "github-token";   // this phone only: never part of a backup, the repository or the site

/** Word list lines as the prompt wants them: "- word". Accepts "- x", "* x", "1. x" or plain lines. */
export function wordLines(text: string): string {
  return text.split(/\r?\n/).map((l) => l.replace(/^\s*(?:[-*•]|\d+[.)])\s*/, "").trim()).filter(Boolean).map((l) => `- ${l}`).join("\n");
}

export async function copyText(text: string, fallbackEl?: HTMLTextAreaElement): Promise<boolean> {
  try { await navigator.clipboard.writeText(text); return true; } catch { /* fall through */ }
  const ta = fallbackEl ?? h("textarea", { style: { position: "fixed", opacity: "0" } });
  if (!fallbackEl) document.body.append(ta);
  const old = ta.value;
  if (!fallbackEl) ta.value = text;
  ta.select();
  let ok = false;
  try { ok = document.execCommand("copy"); } catch { /* ignore */ }
  if (!fallbackEl) ta.remove(); else ta.value = old;
  return ok;
}

export function addWordsSheet(shell: Shell): void {
  const { app } = shell;
  const list = h("textarea", { class: "field", rows: 5, placeholder: "One word per line, e.g.\nbać się\nbiletomat\nkwaśny / kwaśno", spellcheck: false });
  const answer = h("textarea", { class: "field", rows: 6, placeholder: "Paste the AI's answer here", spellcheck: false });
  const result = h("div", { class: "aw-result" });
  const checkBtn = h("button", { class: "btn primary", type: "button" }, "Check and add");

  async function copyPrompt() {
    const lines = wordLines(list.value);
    if (!lines) { shell.toast("Type the words you want to add first."); return; }
    let prompt = "";
    try { const res = await fetch(`languages/${app.deckId}/prompt.txt`); if (res.ok) prompt = await res.text(); } catch { /* offline */ }
    if (!prompt) { shell.toast("The prompt could not be loaded (no connection and not cached yet)."); return; }
    const text = prompt.replace("{WORDS}", lines);
    shell.toast((await copyText(text)) ? "Prompt copied. Paste it into your AI." : "Could not copy automatically.");
  }

  async function check() {
    const text = answer.value.trim();
    if (!text) { shell.toast("Paste the AI's answer first."); return; }
    checkBtn.disabled = true;
    const r = await app.addWords(text);
    checkBtn.disabled = false;
    clear(result);
    if (!("counts" in r)) {
      const message = `Your answer has problems. Fix them and send the complete JSON again, with nothing else:\n${r.errors.map((e) => `- ${e}`).join("\n")}`;
      result.append(
        h("p", { class: "aw-bad" }, `${r.errors.length} problem${r.errors.length > 1 ? "s" : ""} found. Nothing was added.`),
        h("ul", { class: "plain" }, r.errors.slice(0, 12).map((e) => h("li", null, e)), r.errors.length > 12 ? h("li", null, `… and ${r.errors.length - 12} more`) : null),
        h("button", { class: "btn", type: "button", onclick: async () => shell.toast((await copyText(message)) ? "Copied. Paste it back to the AI." : "Could not copy automatically.") }, "Copy the problems for the AI"));
      return;
    }
    const c = r.counts;
    const bits = [
      c.words && `${c.words} new word${c.words > 1 ? "s" : ""}`, c.skipped && `${c.skipped} already there`,
      c.verbs && `${c.verbs} verb table${c.verbs > 1 ? "s" : ""}`, c.nouns && `${c.nouns} noun table${c.nouns > 1 ? "s" : ""}`,
      c.adjectives && `${c.adjectives} adjective table${c.adjectives > 1 ? "s" : ""}`,
      c.examples && `${c.examples} example${c.examples > 1 ? "s" : ""}`, c.sentences && `${c.sentences} sentence${c.sentences > 1 ? "s" : ""}`,
    ].filter(Boolean);
    result.append(h("p", { class: "aw-ok" }, `Added: ${bits.join(", ") || "nothing new"}.`));
    answer.value = ""; list.value = "";
    shell.refreshBadges();
    void renderSend();
  }

  // ------------------------------------------------------------ send for review
  const send = h("div", { class: "aw-send" });
  async function renderSend() {
    clear(send);
    const n = app.unsent.length;
    if (!n) return;
    const token = (await kvGet<string>(TOKEN_KEY)) ?? "";
    const out = h("div", { class: "aw-result" });
    const sendBtn = h("button", { class: "btn primary", type: "button" }, "Send for review");
    sendBtn.addEventListener("click", async () => {
      sendBtn.disabled = true; clear(out); out.append(h("p", { class: "muted" }, "Sending…"));
      const r = await sendForReview({ token, slug: app.userSlug, deck: app.deckId, additions: app.unsent });
      sendBtn.disabled = false; clear(out);
      if (r.ok) {
        app.clearPending();
        out.append(h("p", { class: "aw-ok" }, "Sent! A pull request is open on GitHub."), h("a", { href: r.url, target: "_blank", rel: "noopener" }, r.url));
        send.querySelector(".aw-pending")?.remove(); sendBtn.hidden = true;
      } else {
        if (r.nothingNew) app.clearPending();
        out.append(h("p", { class: "aw-bad" }, r.error));
      }
    });
    send.append(
      h("p", { class: "section-title aw-pending" }, `${n} answer${n > 1 ? "s" : ""} added here, not sent yet`),
      token ? h("div", { class: "btn-row" }, sendBtn, h("button", { class: "btn", type: "button", onclick: async () => { await kvSet(TOKEN_KEY, ""); void renderSend(); shell.toast("Token removed from this phone."); } }, "Remove token")) : tokenBox(),
      h("button", { class: "btn ghost", type: "button", onclick: async () => shell.toast((await copyText(JSON.stringify(combineAdditions(app.unsent), null, 2))) ? "Copied. Send it to the owner of the repository." : "Could not copy automatically.") }, "Copy what I added instead"),
      out);
    function tokenBox() {
      const input = h("input", { class: "field", type: "password", placeholder: "GitHub token (kept on this phone only)", autocomplete: "off", spellcheck: false, style: { width: "100%", minHeight: "44px", padding: "0 12px", borderRadius: "12px", border: "1px solid var(--line)", background: "var(--surface)" } });
      return h("div", { class: "aw-result" },
        h("p", { class: "muted" }, `Needs a fine-grained token for ${GITHUB_REPO} with Contents and Pull requests read & write. It is stored only on this phone.`),
        input,
        h("button", { class: "btn", type: "button", onclick: async () => { const v = input.value.trim(); if (!v) return; await kvSet(TOKEN_KEY, v); void renderSend(); } }, "Save token"));
    }
  }
  checkBtn.addEventListener("click", check);

  shell.sheet(h("div", { class: "sheet-body" },
    h("h2", null, "Add words"),
    h("p", { class: "muted" }, "1. Type the words. 2. Copy the prompt into an AI chat. 3. Paste its answer below."),
    list,
    h("button", { class: "btn", type: "button", onclick: copyPrompt }, "Copy the prompt"),
    answer, checkBtn, result, send));
  void renderSend();
}
