// More: settings, statistics, archived / failed views, backup and import.
import { h, clear } from "./h";
import { ARCHIVED, LEVELS } from "../core/deck";
import { makeBackup, mergeWords, parseImport, type MergeStrategy } from "../core/backup";
import { DEFAULT_SETTINGS, type Settings } from "../state";
import { kvClearAll } from "../store";
import type { Shell } from "./shell";
import { seg, toggleRow } from "./shell";
import { addWordsSheet } from "./addwords";

const fmtDate = (t: number | null) => (t ? new Date(t).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "never");

export function moreScreen(shell: Shell): HTMLElement {
  const { app } = shell;
  const root = h("section", { class: "screen" });
  const body = h("div", { class: "scroll-body" });
  root.append(h("header", { class: "top" }, h("h1", null, "More")), body);

  // ----------------------------------------------------------------- backup
  async function exportBackup() {
    const data = makeBackup(app.deck.words, { ...app.settings }, app.stats, new Date(), app.dungeonSave);
    const name = `fiszki-backup-${new Date().toISOString().slice(0, 10)}.json`;
    const file = new File([JSON.stringify(data, null, 2)], name, { type: "application/json" });
    let done = false;
    try {
      if (navigator.canShare?.({ files: [file] })) { await navigator.share({ files: [file], title: "Fiszki backup" }); done = true; }
    } catch (e) { if ((e as Error).name === "AbortError") return; }
    if (!done) {
      const a = h("a", { href: URL.createObjectURL(file), download: name });
      document.body.append(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 10_000);
    }
    app.meta.lastBackup = Date.now(); app.meta.changes = 0; app.saveMeta();
    shell.toast("Backup saved.");
    render();
  }

  function importFile(file: File) {
    file.text().then((text) => {
      let parsed;
      try { parsed = parseImport(text); } catch (e) { shell.toast((e as Error).message); return; }
      const apply = (strategy: MergeStrategy | "everything") => {
        close();
        if (strategy === "everything") {
          app.replaceWords(parsed.words);
          if (parsed.settings) { app.settings = { ...DEFAULT_SETTINGS, ...(parsed.settings as Partial<Settings>), user: app.settings.user }; app.saveSettings(); }
          if (parsed.stats) app.setStats(parsed.stats);
          if (parsed.dungeon) app.resetGame(parsed.dungeon);
          shell.toast(`Restored ${parsed.words.length} cards.`);
        } else {
          const r = mergeWords(app.deck.words, parsed.words, strategy);
          app.replaceWords(r.words);
          shell.toast(`Added ${r.added}, updated ${r.updated}, unchanged ${r.unchanged}.`);
        }
        shell.refreshBadges(); render();
      };
      const opt = (title: string, sub: string, s: MergeStrategy | "everything") =>
        h("button", { class: "list-btn", style: { flexDirection: "column", alignItems: "flex-start", padding: "10px 14px" }, onclick: () => apply(s) }, h("b", null, title), h("span", { class: "muted", style: { fontSize: "13px" } }, sub));
      const close = shell.sheet(h("div", { class: "sheet-body" },
        h("h2", null, `Import ${parsed.words.length} cards`),
        h("p", { class: "muted" }, parsed.kind === "backup" ? "This is a backup file." : "This is a plain words.json. Cards are matched by their word."),
        h("div", { class: "list" },
          opt("Merge, keep the higher progress", "Recommended. New words are added.", "higher"),
          opt("Merge, use the progress from the file", "Levels and fails from the file win.", "replace"),
          opt("Merge, keep my progress", "Only add new words and update texts.", "keep"),
          parsed.kind === "backup" && opt("Replace everything with this backup", "Cards, settings and statistics.", "everything")),
        h("button", { class: "btn ghost", onclick: () => close() }, "Cancel")));
    });
  }

  function statsSheet() {
    const d = app.deck, s = app.stats;
    const reviewed = s.cards_reviewed ?? 0;
    const pct = reviewed ? Math.round(((s.known ?? 0) / reviewed) * 100) : 0;
    const colors = ["var(--lv-0)", "var(--lv-1)", "var(--lv-2)", "var(--lv-3)"];
    const segs = [...LEVELS.map((l) => d.levelCount(l.level)), d.newCount];
    const sum = Math.max(1, segs.reduce((a, b) => a + b, 0));
    shell.sheet(h("div", { class: "sheet-body" },
      h("h2", null, "Statistics"),
      h("div", { class: "stack-bar", role: "img", "aria-label": "Cards per level" }, segs.map((n, i) => h("i", { style: { width: `${(n / sum) * 100}%`, background: colors[i] ?? "var(--lv-n)" } }))),
      h("ul", { class: "plain" }, [...LEVELS.map((l) => `${l.icon} ${l.name}: ${d.levelCount(l.level)}`), `● New: ${d.newCount}`, `▣ Archived: ${d.levelCount(ARCHIVED)}`].map((t) => h("li", null, t))),
      h("div", { class: "statgrid" },
        h("div", { class: "stat" }, h("b", null, String(s.sessions ?? 0)), h("span", null, "sessions")),
        h("div", { class: "stat" }, h("b", null, String(reviewed)), h("span", null, "cards reviewed")),
        h("div", { class: "stat" }, h("b", null, String(s.known ?? 0)), h("span", null, "marked Known")),
        h("div", { class: "stat" }, h("b", null, `${pct}%`), h("span", null, "known rate"))),
      h("p", { class: "muted" }, `${d.overallTotal} cards in total.`)));
  }

  function row(title: string, hint: string | null, value: string, onclick: () => void) {
    return h("button", { class: "row link", onclick }, h("span", { class: "row-text" }, h("span", { class: "row-title" }, title), hint && h("span", { class: "row-hint" }, hint)), h("span", { class: "val" }, value + "  ›"));
  }

  function render() {
    const d = app.deck;
    const failed = d.words.filter((w) => w.fails > 0 && w.level !== ARCHIVED).length;
    clear(body);
    body.append(
      h("p", { class: "section-title" }, "Name and words"),
      h("div", { class: "group" },
        h("div", { class: "row" }, h("span", { style: { flex: "1" } }, `Name: ${app.settings.user}`),
          h("button", { class: "btn small", type: "button", onclick: async () => { if (await shell.confirm("Change name?", "You go back to the start screen. Your progress for this name stays on this phone.", "Change")) { app.settings.user = ""; app.saveSettings(); await app.pending; location.reload(); } } }, "Change")),
        h("div", { class: "row" }, h("button", { class: "btn", style: { flex: "1" }, onclick: async (e: Event) => {
          const b = e.currentTarget as HTMLButtonElement; b.disabled = true;
          const r = await app.updateWords(); b.disabled = false;
          if (!r.ok) { shell.toast(`No word list for "${app.settings.user}" in the repository (or no connection).`); return; }
          shell.toast(r.added || r.updated ? `Added ${r.added}, updated ${r.updated}. Your progress is kept.` : "Your words are up to date.");
          shell.refreshBadges(); render();
        } }, "Update words from the repository")),
        h("div", { class: "row" }, h("button", { class: "btn", style: { flex: "1" }, onclick: () => addWordsSheet(shell) }, "Add words"))),
      h("p", { class: "section-title" }, "Appearance"),
      h("div", { class: "group" }, h("div", { class: "row" }, seg<Settings["theme"]>([["system", "System"], ["light", "Light"], ["dark", "Dark"]], app.settings.theme, (v) => { app.settings.theme = v; app.saveSettings(); }))),

      h("p", { class: "section-title" }, "Study"),
      h("div", { class: "group" },
        toggleRow("English first", "Show the English side first", app.settings.englishFirst, (v) => { app.settings.englishFirst = v; app.saveSettings(); }),
        toggleRow("Show extra sentences", "Under a revealed card and in the blank quiz", app.settings.showExamples, (v) => { app.settings.showExamples = v; app.saveSettings(); }),
        toggleRow("Show grammar tables", "Verbs, nouns, adjectives", app.settings.showGrammar, (v) => { app.settings.showGrammar = v; app.saveSettings(); })),

      h("p", { class: "section-title" }, "Cards"),
      h("div", { class: "group" },
        row("Archived", "Known cards you put away", String(d.levelCount(ARCHIVED)), () => shell.studyView(() => d.setMode("level4"))),
        row("Failed words", "Missed in a quiz, worst first", String(failed), () => shell.studyView(() => d.setMode("failed"))),
        row("Statistics", null, "", statsSheet)),

      h("p", { class: "section-title" }, "Backup"),
      h("div", { class: "group" },
        h("div", { class: "row" }, h("span", { class: "row-text" }, h("span", { class: "row-title" }, "Last backup"), h("span", { class: "row-hint" }, app.needsBackup ? `${app.meta.changes} changes since. Back up now!` : `${app.meta.changes} changes since`)), h("span", { class: "val" }, fmtDate(app.meta.lastBackup))),
        h("div", { class: "row" }, h("button", { class: "btn primary", style: { flex: "1" }, onclick: exportBackup }, "Export backup"), h("button", { class: "btn", style: { flex: "1" }, onclick: () => fileIn.click() }, "Import…"))),
      h("p", { class: "muted", style: { fontSize: "13px", padding: "6px 4px" } }, "Your progress lives only on this phone. On iPhone, Safari can erase it after weeks without use, so export a backup now and then. Import also accepts a plain words.json from the desktop app."),

      h("p", { class: "section-title" }, "Danger zone"),
      h("div", { class: "group" },
        h("div", { class: "row" }, h("button", { class: "btn", style: { flex: "1" }, onclick: async () => { if (await shell.confirm("Reset saved progress?", "All levels and fail counts are removed. Your cards stay.", "Reset", true)) { d.resetProgress(); shell.toast("Progress reset."); render(); } } }, "Reset progress")),
        h("div", { class: "row" }, h("button", { class: "btn", style: { flex: "1" }, onclick: async () => { if (await shell.confirm("Start the dungeon over?", "Your adventurer, gear, coins and dungeon progress are deleted. Your cards are not touched.", "Start over", true)) { app.resetGame(); shell.toast("Dungeon reset."); } } }, "Reset dungeon progress")),
        h("div", { class: "row" }, h("button", { class: "btn danger", style: { flex: "1" }, onclick: async () => { if (await shell.confirm("Erase all data?", "Cards, progress, settings and statistics on this device are deleted and the original word list is loaded again. Export a backup first.", "Erase", true)) { await app.pending; await kvClearAll(); location.reload(); } } }, "Erase all data"))),
      h("p", { class: "section-title" }, "About"),
      h("p", { class: "muted", style: { fontSize: "13px", padding: "0 4px 24px" } }, `Fiszki · ${d.overallTotal} cards · works offline. Add it to your home screen: Android Chrome → menu → Install app; iPhone Safari → Share → Add to Home Screen.`));
  }

  const fileIn = h("input", { type: "file", accept: ".json,application/json", hidden: true }) as HTMLInputElement;
  fileIn.addEventListener("change", () => { const f = fileIn.files?.[0]; fileIn.value = ""; if (f) importFile(f); });
  root.append(fileIn);
  render();
  (root as any).render = render;
  return root;
}
