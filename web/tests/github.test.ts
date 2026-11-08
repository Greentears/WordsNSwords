import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { sendForReview, type FetchFn } from "../src/core/github";

const FIX = new URL("../../tests/fixtures/pl-en/", import.meta.url);
const files: Record<string, string> = {};
for (const p of ["words", "verbs", "nouns", "adjectives", "examples", "sentences"]) {
  if (existsSync(new URL(`${p}.json`, FIX))) files[`users/anna/pl-en/${p}.json`] = readFileSync(new URL(`${p}.json`, FIX), "utf8");
}
const Q7 = ["a", "b", "c", "d", "e", "f", "g"];
const addition = { words: [{ word: "kot", translation: "cat" }], nouns: [{ card: "kot", nouns: [{ lemma: "kot", gender: "m", singular: Q7, plural: Q7 }] }] };

function fakeGithub(opts: { token?: string; takenBranches?: string[]; missingFolder?: boolean } = {}) {
  const log: { method: string; path: string; body?: any; auth?: string }[] = [];
  const puts: Record<string, string> = {};
  const taken = new Set(opts.takenBranches ?? []);
  const fetchFn: FetchFn = async (url, init) => {
    const method = init?.method ?? "GET";
    const path = url.replace("https://api.github.com/repos/Greentears/WordsNSwords", "");
    const body = init?.body ? JSON.parse(init.body as string) : undefined;
    const auth = (init?.headers as Record<string, string>).Authorization;
    log.push({ method, path, body, auth });
    const reply = (status: number, data: unknown = {}) => ({ ok: status < 300, status, json: async () => data });
    if (auth !== `Bearer ${opts.token ?? "tok"}`) return reply(401);
    let m;
    if (method === "GET" && (m = path.match(/^\/contents\/(.+?)\?ref=main$/))) {
      const text = files[m[1]];
      if (opts.missingFolder || text === undefined) return reply(404);
      return reply(200, { sha: "sha-" + m[1], content: Buffer.from(text).toString("base64").replace(/(.{60})/g, "$1\n") });
    }
    if (method === "GET" && path === "/git/ref/heads/main") return reply(200, { object: { sha: "HEAD1" } });
    if (method === "POST" && path === "/git/refs") {
      if (taken.has(body.ref)) return reply(422);
      taken.add(body.ref);
      return reply(201);
    }
    if (method === "PUT" && (m = path.match(/^\/contents\/(.+)$/))) { puts[m[1]] = Buffer.from(body.content, "base64").toString("utf8"); return reply(200); }
    if (method === "POST" && path === "/pulls") return reply(201, { html_url: "https://github.com/Greentears/WordsNSwords/pull/7" });
    return reply(500);
  };
  return { fetchFn, log, puts };
}
const base = { slug: "anna", deck: "pl-en", now: new Date("2026-11-08T15:49:00Z") };

test("send for review: commits the changed files to a new branch and opens a PR", async () => {
  const g = fakeGithub();
  const r = await sendForReview({ ...base, token: "tok", additions: [addition], fetchFn: g.fetchFn });
  assert.ok(r.ok, JSON.stringify(r));
  if (!r.ok) return;
  assert.equal(r.url, "https://github.com/Greentears/WordsNSwords/pull/7");
  assert.equal(r.branch, "add-words-20261108-1549-anna");
  assert.deepEqual(r.files.sort(), ["nouns.json", "words.json"]);
  const words = JSON.parse(g.puts["users/anna/pl-en/words.json"]);
  assert.equal(words.at(-1).word, "kot");
  assert.ok(g.puts["users/anna/pl-en/words.json"].includes('\n        "word"'), "words.json keeps its 4-space indent");
  assert.ok(g.log.find((l) => l.method === "PUT" && l.path.endsWith("words.json"))!.body.sha, "updates carry the file's sha");
  assert.ok(!g.log.some((l) => l.path.includes("verbs.json") && l.method === "PUT"), "unchanged files are not committed");
  const pr = g.log.find((l) => l.path === "/pulls")!;
  assert.equal(pr.body.base, "main");
  assert.equal(pr.body.title, "Add 1 word for anna");
});

test("send for review: non-ASCII text survives the round trip", async () => {
  const g = fakeGithub();
  const r = await sendForReview({ ...base, token: "tok", additions: [{ words: [{ word: "źdźbło", translation: "blade of grass" }] }], fetchFn: g.fetchFn });
  assert.ok(r.ok);
  assert.ok(g.puts["users/anna/pl-en/words.json"].includes("źdźbło"));
});

test("send for review: a taken branch name gets a suffix", async () => {
  const g = fakeGithub({ takenBranches: ["refs/heads/add-words-20261108-1549-anna"] });
  const r = await sendForReview({ ...base, token: "tok", additions: [addition], fetchFn: g.fetchFn });
  assert.ok(r.ok && r.branch === "add-words-20261108-1549-anna-2");
});

test("send for review: explains a refused token and sends nothing", async () => {
  const g = fakeGithub({ token: "other" });
  const r = await sendForReview({ ...base, token: "tok", additions: [addition], fetchFn: g.fetchFn });
  assert.ok(!r.ok && /refused the token/.test(r.error));
  assert.ok(!g.log.some((l) => l.method !== "GET"), "no write was attempted");
});

test("send for review: words already in the repo are not sent again", async () => {
  const first = JSON.parse(files["users/anna/pl-en/words.json"])[0];
  const g = fakeGithub();
  const r = await sendForReview({ ...base, token: "tok", additions: [{ words: [{ word: first.word, translation: "x" }] }], fetchFn: g.fetchFn });
  assert.ok(!r.ok && r.nothingNew);
});

test("send for review: needs a token, additions and a folder in the repo", async () => {
  assert.match((await sendForReview({ ...base, token: " ", additions: [addition] }) as any).error, /No token/);
  assert.ok((await sendForReview({ ...base, token: "tok", additions: [] }) as any).nothingNew);
  const g = fakeGithub({ missingFolder: true });
  assert.match((await sendForReview({ ...base, token: "tok", additions: [addition], fetchFn: g.fetchFn }) as any).error, /no folder users\/anna\/pl-en/);
});

test("send for review: a network failure is reported plainly", async () => {
  const r = await sendForReview({ ...base, token: "tok", additions: [addition], fetchFn: async () => { throw new TypeError("x"); } });
  assert.ok(!r.ok && r.error === "No connection to GitHub.");
});
