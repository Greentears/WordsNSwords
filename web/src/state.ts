// App state: deck, settings, stats, reference tables; everything saved through store.ts.
import { FlashcardDeck, parseWords, wordToJson } from "./core/deck";
import { updateSession, type Stats } from "./core/stats";
import {
  knownForms, loadAdjectives, loadConjugations, loadDeclensions, loadExamples, loadSentences,
  type Adjective, type Example, type Noun, type SentenceItem, type Verb,
} from "./core/tables";
import { GameManager, type Repository } from "./dungeon";
import { kvGet, kvSet } from "./store";
import { mergeWords } from "./core/backup";

export interface Settings { theme: "system" | "light" | "dark"; englishFirst: boolean; showExamples: boolean; showGrammar: boolean; user: string }
export const DEFAULT_SETTINGS: Settings = { theme: "system", englishFirst: false, showExamples: true, showGrammar: true, user: "" };
export interface Meta { lastBackup: number | null; changes: number }

/** The folder name for a name: lower case, no accents, letters / digits / - only (same rule as the PC app). */
export const userSlug = (name: string): string =>
  name.trim().toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9_-]+/g, "-").replace(/^[-_]+|[-_]+$/g, "");

export const NUDGE_AFTER_CHANGES = 40;

export class App {
  deck!: FlashcardDeck;
  settings: Settings = { ...DEFAULT_SETTINGS };
  stats: Stats = {};
  meta: Meta = { lastBackup: null, changes: 0 };
  conj: Record<string, Verb[]> = {};
  decl: Record<string, Noun[]> = {};
  adj: Record<string, Adjective[]> = {};
  examples: Record<string, Example[]> = {};
  sentences: SentenceItem[] = [];
  forms: Record<string, string[]> = {};
  /** Resolves when the last write has reached storage (used by tests). */
  pending: Promise<void> = Promise.resolve();
  listeners = new Set<() => void>();
  deckId = "pl-en";
  userSlug = "";
  /** Folder (on the site) the word tables come from. */
  source = "";
  /** The dungeon save (same schema as the desktop dungeon_progress.json); stays on this phone. */
  dungeonSave: unknown = null;
  private gameInstance: GameManager | null = null;
  private dungeonRepo: Repository = {
    load: () => this.dungeonSave,
    save: (state) => { const copy = JSON.parse(JSON.stringify(state)); this.dungeonSave = copy; this.chain(() => kvSet(this.ns("dungeon"), copy)); },
  };

  /** The Vocabulary Dungeon game. It only reads the cards; it never changes a level or a fail count. */
  get game(): GameManager {
    if (!this.gameInstance) {
      this.gameInstance = new GameManager(this.deck, this.examples, this.dungeonRepo, Math.random);
      if (this.settings.user.trim()) this.gameInstance.player.name = this.settings.user.trim();   // the hero has your name
    }
    return this.gameInstance;
  }

  /** Throw the running game away and start from `save` (null = a brand new adventurer). */
  resetGame(save: unknown = null): void {
    this.dungeonSave = save;
    this.gameInstance = null;
    this.chain(() => kvSet(this.ns("dungeon"), save));
  }

  /** Storage key for the current name and language (each language has its own cards, progress and hero). */
  ns(key: string): string { return `u/${this.userSlug}/${this.deckId}/${key}`; }

  static async load(): Promise<App> {
    const app = new App();
    app.settings = { ...DEFAULT_SETTINGS, ...((await kvGet<Partial<Settings>>("settings")) ?? {}) };
    if (app.settings.user.trim()) await app.openUser(app.settings.user, false);
    return app;
  }

  private async fetchJson(url: string): Promise<any> {
    try { const res = await fetch(url, { cache: "no-cache" }); return res.ok ? await res.json() : null; } catch { return null; }
  }

  private async loadTables(base: string): Promise<void> {
    const [verbs, nouns, adjs, ex, sents] = await Promise.all(["verbs", "nouns", "adjectives", "examples", "sentences"].map((n) => this.fetchJson(`${base}/${n}.json`)));
    this.conj = loadConjugations(verbs);
    this.decl = loadDeclensions(nouns);
    this.adj = loadAdjectives(adjs);
    this.examples = loadExamples(ex);
    try { this.sentences = loadSentences(sents); } catch { this.sentences = []; }
    this.forms = knownForms(this.conj, this.decl, this.adj);
    this.gameInstance = null;
  }

  /**
   * Load this name's cards and progress. "missing": the repo has no folder for this name (call again with
   * useStarter to begin with the starter deck); "offline": nothing stored yet and the site could not be reached.
   */
  async openUser(name: string, useStarter: boolean): Promise<"ok" | "missing" | "offline"> {
    const slug = userSlug(name);
    if (!slug) return "missing";
    this.userSlug = slug;
    let stored = await kvGet<Record<string, unknown>[]>(this.ns("words"));
    let base = (await kvGet<string>(this.ns("source"))) ?? `users/${slug}/${this.deckId}`;
    if (!stored) {
      const legacy = await kvGet<Record<string, unknown>[]>("words");          // data from before names existed
      if (legacy && !(await kvGet("legacy-claimed"))) {
        stored = legacy;
        await kvSet(this.ns("words"), legacy);
        for (const k of ["stats", "meta", "dungeon"]) { const v = await kvGet(k); if (v !== undefined) await kvSet(this.ns(k), v); }
        await kvSet("legacy-claimed", slug);
        base = `users/${slug}/${this.deckId}`;
      }
    }
    if (!stored) {
      base = `users/${slug}/${this.deckId}`;
      let seed = await this.fetchJson(`${base}/words.json`);
      if (!seed) {
        if (!useStarter) return (await this.fetchJson(`users/_template/${this.deckId}/words.json`)) ? "missing" : "offline";
        base = `users/_template/${this.deckId}`;
        seed = await this.fetchJson(`${base}/words.json`);
        if (!seed) return "offline";
      }
      stored = seed;
      await kvSet(this.ns("words"), seed);
      await kvSet(this.ns("source"), base);
    }
    this.source = base;
    this.deck = new FlashcardDeck(parseWords(stored));
    this.deck.onSave = (words) => this.saveWords(words);
    this.stats = (await kvGet<Stats>(this.ns("stats"))) ?? {};
    this.meta = { ...this.meta, ...((await kvGet<Meta>(this.ns("meta"))) ?? {}) };
    this.dungeonSave = (await kvGet<unknown>(this.ns("dungeon"))) ?? null;
    await this.loadTables(base);
    return "ok";
  }

  /** Fetch the cards of this name from the repo and add / update them; levels and fails are kept. */
  async updateWords(): Promise<{ ok: false } | { ok: true; added: number; updated: number; unchanged: number }> {
    const base = `users/${this.userSlug}/${this.deckId}`;
    const cards = await this.fetchJson(`${base}/words.json`);
    if (!cards) return { ok: false };
    let incoming;
    try { incoming = parseWords(cards); } catch { return { ok: false }; }
    const r = mergeWords(this.deck.words, incoming, "keep");
    this.replaceWords(r.words);
    this.source = base;
    this.chain(() => kvSet(this.ns("source"), base));
    await this.loadTables(base);
    return { ok: true, added: r.added, updated: r.updated, unchanged: r.unchanged };
  }

  private chain(fn: () => Promise<void>) { this.pending = this.pending.then(fn, fn); }

  saveWords(words = this.deck.words): void {
    this.meta.changes++;
    const data = words.map(wordToJson);
    const meta = { ...this.meta };
    this.chain(async () => { await kvSet(this.ns("words"), data); await kvSet(this.ns("meta"), meta); });
    this.emit();
  }

  saveSettings(): void { const s = { ...this.settings }; this.chain(() => kvSet("settings", s)); this.applyTheme(); this.emit(); }
  saveMeta(): void { const m = { ...this.meta }; this.chain(() => kvSet(this.ns("meta"), m)); this.emit(); }

  recordSession(total: number, known: number, unknown: number): void {
    this.stats = updateSession(this.stats, total, known, unknown);
    const s = { ...this.stats };
    this.chain(() => kvSet(this.ns("stats"), s));
  }

  setStats(stats: Stats) { this.stats = stats; const s = { ...stats }; this.chain(() => kvSet(this.ns("stats"), s)); }

  applyTheme(): void {
    const t = this.settings.theme;
    if (t === "system") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", t);
    const dark = t === "dark" || (t === "system" && matchMedia("(prefers-color-scheme: dark)").matches);
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", dark ? "#15171c" : "#f6f4ef");
  }

  /** True when a backup is worth suggesting. */
  get needsBackup(): boolean {
    if (this.meta.changes < NUDGE_AFTER_CHANGES) return false;
    return true;
  }

  emit() { this.listeners.forEach((f) => f()); }

  /** Replace every card (import / reset). */
  replaceWords(words: ReturnType<typeof parseWords>): void {
    const mode = this.deck.mode;
    this.deck.words = words;
    this.deck.setMode(mode === "search" || mode === "quick" ? "all" : mode);
    this.saveWords();
  }
}
