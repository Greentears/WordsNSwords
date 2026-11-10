/**
 * "Send for review": put the words added on this device into a GitHub pull request.
 * The token is only ever passed in from the device's own storage; nothing here stores or logs it.
 * Same steps as desktop/github_pr.py (both are tested against a fake GitHub).
 */
import { languageOf, merge, validate, type DeckData, type Json } from "./newwords";

export const GITHUB_REPO = "Greentears/WordsNSwords";
const API = "https://api.github.com";
const PARTS = ["words", "verbs", "nouns", "adjectives", "examples", "sentences"] as const;

export type FetchFn = (url: string, init?: RequestInit) => Promise<Pick<Response, "ok" | "status" | "json">>;
export interface SendOptions {
  token: string;
  slug: string;
  deck: string;
  additions: Json[];
  repo?: string;
  base?: string;
  fetchFn?: FetchFn;
  now?: Date;
}
export type SendResult = { ok: true; url: string; branch: string; files: string[] } | { ok: false; error: string; nothingNew?: boolean };

const toBase64 = (text: string) => {
  const bytes = new TextEncoder().encode(text);
  let bin = "";
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(bin);
};
const fromBase64 = (b64: string) => {
  const bin = atob(b64.replace(/\s+/g, ""));
  return new TextDecoder().decode(Uint8Array.from(bin, (c) => c.charCodeAt(0)));
};
const stamp = (d: Date) => d.toISOString().slice(0, 16).replace(/[-:]/g, "").replace("T", "-");
const indent = (part: string) => (part === "words" ? 4 : 2);

class ApiError extends Error { constructor(public status: number, msg: string) { super(msg); } }

function explain(status: number, what: string): string {
  if (status === 401) return "GitHub refused the token (wrong, expired or revoked). Make a new one and enter it again.";
  if (status === 403) return `GitHub says the token may not do this (${what}). It needs Contents and Pull requests read & write on this repository.`;
  if (status === 404) return `GitHub could not find ${what}. Check the repository name, and that the token has access to it.`;
  if (status === 422) return `GitHub did not accept the request (${what}).`;
  return `GitHub answered ${status} (${what}).`;
}

export async function sendForReview(o: SendOptions): Promise<SendResult> {
  const repo = o.repo ?? GITHUB_REPO, f = o.fetchFn ?? ((u, i) => fetch(u, i));
  const folder = `users/${o.slug}/${o.deck}`;
  const call = async (method: string, path: string, body?: unknown, okStatuses: number[] = []) => {
    let res;
    try {
      res = await f(`${API}/repos/${repo}${path}`, {
        method,
        headers: { Authorization: `Bearer ${o.token}`, Accept: "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", ...(body ? { "Content-Type": "application/json" } : {}) },
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch { throw new ApiError(0, "No connection to GitHub."); }
    if (!res.ok && !okStatuses.includes(res.status)) throw new ApiError(res.status, explain(res.status, `${method} ${path.split("?")[0]}`));
    return { status: res.status, data: (await res.json().catch(() => ({}))) as any };
  };
  try {
    if (!o.token.trim()) return { ok: false, error: "No token entered." };
    if (!o.additions.length) return { ok: false, error: "Nothing to send: no words were added on this device.", nothingNew: true };
    // 1. the repository's main branch (it may be called main or master) and its files as they are now
    const base = o.base ?? ((await call("GET", "")).data.default_branch as string | undefined) ?? "main";
    const deck: DeckData = { words: [], verbs: [], nouns: [], adjectives: [], examples: {}, sentences: [] };
    const shas: Record<string, string> = {}, original: Record<string, string> = {};
    for (const part of PARTS) {
      const r = await call("GET", `/contents/${folder}/${part}.json?ref=${encodeURIComponent(base)}`, undefined, [404]);
      if (r.status === 404) {
        if (part === "words") return { ok: false, error: `There is no folder ${folder} in the repository yet. Push your words there first.` };
        continue;
      }
      const text = fromBase64(r.data.content);
      shas[part] = r.data.sha; original[part] = text;
      (deck as any)[part] = JSON.parse(text);
    }
    // 2. add what was added here (cards that are already there are skipped)
    let cur = deck;
    for (const a of o.additions) {
      const errors = validate(a, cur.words.map((w) => w.word as string), languageOf(o.deck));
      if (errors.length) return { ok: false, error: `An addition is no longer valid against the repository: ${errors[0]}` };
      cur = merge(cur, a).deck;
    }
    const changed: { part: string; text: string }[] = [];
    for (const part of PARTS) {
      const text = JSON.stringify((cur as any)[part], null, indent(part));
      const empty = Array.isArray((cur as any)[part]) ? (cur as any)[part].length === 0 : Object.keys((cur as any)[part]).length === 0;
      if (part in original ? JSON.stringify(JSON.parse(original[part])) !== JSON.stringify((cur as any)[part]) : !empty) changed.push({ part, text });
    }
    if (!changed.length) return { ok: false, error: "Everything you added is already in the repository.", nothingNew: true };
    // 3. branch, commits, pull request
    const head = (await call("GET", `/git/ref/heads/${base}`)).data.object.sha as string;
    const now = o.now ?? new Date();
    let branch = `add-words-${stamp(now)}-${o.slug}`;
    for (let n = 2; ; n++) {
      const r = await call("POST", "/git/refs", { ref: `refs/heads/${branch}`, sha: head }, [422]);
      if (r.status !== 422) break;
      if (n > 5) return { ok: false, error: "Could not make a branch name that is free." };
      branch = `add-words-${stamp(now)}-${o.slug}-${n}`;
    }
    const wordsAdded = cur.words.length - deck.words.length;
    for (const c of changed) {
      await call("PUT", `/contents/${folder}/${c.part}.json`, {
        message: `Add words for ${o.slug} (${c.part})`, content: toBase64(c.text), branch, ...(shas[c.part] ? { sha: shas[c.part] } : {}),
      });
    }
    const pr = await call("POST", "/pulls", {
      title: `Add ${wordsAdded} word${wordsAdded === 1 ? "" : "s"} for ${o.slug}`, head: branch, base,
      body: `Words added from the WordsNSwords app by ${o.slug} (${o.deck}).\n\nFiles: ${changed.map((c) => `${c.part}.json`).join(", ")}.`,
    });
    return { ok: true, url: pr.data.html_url, branch, files: changed.map((c) => `${c.part}.json`) };
  } catch (e) {
    return { ok: false, error: e instanceof ApiError ? e.message : `Unexpected problem: ${(e as Error).message}` };
  }
}
