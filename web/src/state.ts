// App state: deck, settings, stats, reference tables; everything saved through store.ts.
import { FlashcardDeck, parseWords, wordToJson } from "./core/deck";
import { updateSession, type Stats } from "./core/stats";
import {
  knownForms, loadAdjectives, loadConjugations, loadDeclensions, loadExamples, loadSentences,
  loadFrAdjectives, loadFrNouns, loadFrVerbs, frKnownForms, type FrAdjective, type FrNoun, type FrVerb, type Adjective, type Example, type Noun, type SentenceItem, type Verb,
} from "./core/tables";
import { GameManager, type Repository } from "./dungeon";
import { kvGet, kvSet } from "./store";
import { isHeroGender, type HeroGender } from "./art";
import { mergeWords } from "./core/backup";
import { checkAndMerge, emptyDeck, languageOf, merge as mergeNewWords, type Counts, type DeckData, type Json } from "./core/newwords";

export interface Settings { theme: "system" | "light" | "dark"; englishFirst: boolean; showExamples: boolean; showGrammar: boolean; user: string; deck: string }
export const DEFAULT_SETTINGS: Settings = { theme: "system", englishFirst: false, showExamples: true, showGrammar: true, user: "", deck: "" };

export const DEFAULT_DECK = "pl-en";
const DECK_NAMES: Record<string, string> = { "pl-en": "Polish → English", "fr-en": "French → English" };
/** The language you learn in a deck: its name, its code and the special letters for the answer box. */
export function languageInfo(deckId: string): { name: string; code: string; letters: string[] } {
  const code = deckId.split("-")[0];
  if (code === "fr") return { name: "French", code: "fr", letters: ["é", "è", "ê", "à", "â", "ç", "î", "ï", "ô", "ù", "û", "ë", "œ"] };
  return { name: "Polish", code: "pl", letters: ["ą", "ć", "ę", "ł", "ń", "ó", "ś", "ź", "ż"] };
}
/** Readable name of a deck id such as "fr-en". */
export const deckLabel = (id: string): string => DECK_NAMES[id] ?? id;
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
  /** French decks: tenses / nouns / adjectives in their own shape. */
  frConj: Record<string, FrVerb[]> = {};
  frDecl: Record<string, FrNoun[]> = {};
  frAdj: Record<string, FrAdjective[]> = {};
  examples: Record<string, Example[]> = {};
  sentences: SentenceItem[] = [];
  forms: Record<string, string[]> = {};
  /** Resolves when the last write has reached storage (used by tests). */
  pending: Promise<void> = Promise.resolve();
  listeners = new Set<() => void>();
  deckId = DEFAULT_DECK;
  /** The decks (languages) this name has in the repository. */
  availableDecks: string[] = [DEFAULT_DECK];
  userSlug = "";
  /** Folder (on the site) the word tables come from. */
  source = "";
  /** Which hero (female/male) this name chose the first time in the dungeon; final. */
  hero: HeroGender | null = null;
  /** The dungeon save (same schema as the desktop dungeon_progress.json); stays on this phone. */
  dungeonSave: unknown = null;
  /** Answers added with "Add words" on this phone (checked and merged); replayed over the repo tables. */
  additions: Json[] = [];
  /** The part of `additions` that has not been sent for review yet. */
  unsent: Json[] = [];
  /** The tables exactly as the site delivers them (without the additions). */
  private repoTables: DeckData = emptyDeck();
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
  /** The first choice stays: a hero can't be changed afterwards. */
  chooseHero(gender: HeroGender): void {
    if (this.hero) return;
    this.hero = gender;
    const key = `u/${this.userSlug}/hero`;
    this.chain(() => kvSet(key, gender));
    this.emit();
  }

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
    // Grammar tables exist for Polish and French; other languages show cards, examples and sentences only.
    const grammar = this.deckId === DEFAULT_DECK || languageOf(this.deckId) === "fr";
    const [verbs, nouns, adjs, ex, sents] = await Promise.all(["verbs", "nouns", "adjectives", "examples", "sentences"].map((n) => (!grammar && ["verbs", "nouns", "adjectives"].includes(n) ? null : this.fetchJson(`${base}/${n}.json`))));
    const list = (v: unknown) => (Array.isArray(v) ? (v as Json[]) : []);
    this.repoTables = {
      words: [], verbs: list(verbs), nouns: list(nouns), adjectives: list(adjs),
      examples: ex && typeof ex === "object" && !Array.isArray(ex) ? (ex as DeckData["examples"]) : {},
      sentences: list(sents),
    };
    this.applyTables();
  }

  private saveAdditions(): void {
    const adds = JSON.parse(JSON.stringify(this.additions)), pend = JSON.parse(JSON.stringify(this.unsent));
    this.chain(async () => { await kvSet(this.ns("additions"), adds); await kvSet(this.ns("pending"), pend); });
  }

  /** Forget what was sent for review (the cards stay on this phone). */
  clearPending(): void { this.unsent = []; this.saveAdditions(); }

  /** Repo tables + the additions made on this phone. */
  private applyTables(): void {
    let t = this.repoTables;
    for (const a of this.additions) t = mergeNewWords(t, a).deck;
    const french = languageOf(this.deckId) === "fr";
    this.conj = french ? {} : loadConjugations(t.verbs.length ? t.verbs : null);
    this.decl = french ? {} : loadDeclensions(t.nouns.length ? t.nouns : null);
    this.adj = french ? {} : loadAdjectives(t.adjectives.length ? t.adjectives : null);
    this.frConj = french ? loadFrVerbs(t.verbs) : {};
    this.frDecl = french ? loadFrNouns(t.nouns) : {};
    this.frAdj = french ? loadFrAdjectives(t.adjectives) : {};
    this.examples = loadExamples(t.examples);
    try { this.sentences = loadSentences(t.sentences); } catch { this.sentences = []; }
    this.forms = french ? frKnownForms(this.frConj, this.frDecl, this.frAdj) : knownForms(this.conj, this.decl, this.adj);
    this.gameInstance = null;
  }

  /** Check an AI answer and, if it is fine, add the new cards and tables on this phone. */
  async addWords(text: string): Promise<{ errors: string[] } | { errors: []; counts: Counts }> {
    const current: DeckData = { ...this.repoTables, words: this.deck.words.map((w) => wordToJson(w)) };
    let t = current;
    for (const a of this.additions) t = mergeNewWords(t, a).deck;
    const r = checkAndMerge({ ...t, words: current.words }, text, languageOf(this.deckId));
    if (r.errors.length || !r.data || !r.counts) return { errors: r.errors };
    const have = new Set(this.deck.words.map((w) => w.word));
    const freshJson = r.deck!.words.filter((w) => !have.has(w.word as string));
    const fresh = freshJson.length ? parseWords(freshJson) : [];
    this.additions = [...this.additions, r.data];
    this.unsent = [...this.unsent, r.data];
    this.saveAdditions();
    this.applyTables();
    this.replaceWords([...this.deck.words, ...fresh]);
    return { errors: [], counts: r.counts };
  }

  /**
   * Load this name's cards and progress. "missing": the repo has no folder for this name (call again with
   * useStarter to begin with the starter deck); "offline": nothing stored yet and the site could not be reached.
   */
  /** The languages that have a starter deck (users/_template/<deck>), for a name the repository doesn't know. */
  async templateDecks(): Promise<string[]> {
    const index = await this.fetchJson("users/index.json");
    const listed = index && Array.isArray(index["_template"]) ? (index["_template"] as string[]) : [];
    return listed.length ? listed : [DEFAULT_DECK];
  }

  async openUser(name: string, useStarter: boolean, deck?: string): Promise<"ok" | "missing" | "offline" | "choose"> {
    const slug = userSlug(name);
    if (!slug) return "missing";
    this.userSlug = slug;
    // which languages does the repository have for this name? (users/index.json is written when the site is built)
    const index = await this.fetchJson("users/index.json");
    const listed: string[] | null = index && Array.isArray(index[slug]) ? (index[slug] as string[]) : null;
    if (listed && listed.length) {
      this.availableDecks = listed;
      const wanted = deck ?? this.settings.deck;
      if (listed.includes(wanted)) this.deckId = wanted;
      else if (listed.length === 1) this.deckId = listed[0];
      else return "choose";
    } else {
      this.deckId = deck || this.settings.deck || DEFAULT_DECK;
      this.availableDecks = [this.deckId];
    }
    this.settings.deck = this.deckId;
    let stored = await kvGet<Record<string, unknown>[]>(this.ns("words"));
    let base = (await kvGet<string>(this.ns("source"))) ?? `users/${slug}/${this.deckId}`;
    if (!stored) {
      const legacy = await kvGet<Record<string, unknown>[]>("words");          // data from before names existed
      if (legacy && this.deckId === DEFAULT_DECK && !(await kvGet("legacy-claimed"))) {
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
    const hero = await kvGet<unknown>(`u/${slug}/hero`);
    this.hero = isHeroGender(hero) ? hero : null;
    this.additions = (await kvGet<Json[]>(this.ns("additions"))) ?? [];
    this.unsent = (await kvGet<Json[]>(this.ns("pending"))) ?? [];
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
