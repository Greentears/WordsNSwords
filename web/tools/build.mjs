// Build: bundle the app, minify the CSS, copy static files, make icons, write the service worker.
import { build, transform } from "esbuild";
import { createHash } from "node:crypto";
import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { makeIcons } from "./icons.mjs";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const dist = join(root, "dist");
rmSync(dist, { recursive: true, force: true });
mkdirSync(dist, { recursive: true });

await build({ entryPoints: [join(root, "src/main.ts")], bundle: true, minify: true, target: "es2020", format: "iife", outfile: join(dist, "app.js"), legalComments: "none" });
const css = readFileSync(join(root, "src/styles.css"), "utf8");
writeFileSync(join(dist, "styles.css"), (await transform(css, { loader: "css", minify: true })).code);
cpSync(join(root, "public"), dist, { recursive: true });
const users = join(root, "..", "users");
if (existsSync(users)) cpSync(users, join(dist, "users"), { recursive: true });
await makeIcons(join(dist, "icons"));

const walk = (d) => readdirSync(d).flatMap((f) => (statSync(join(d, f)).isDirectory() ? walk(join(d, f)) : [join(d, f)]));
const files = walk(dist).map((f) => relative(dist, f).split("\\").join("/")).filter((f) => f !== "sw.js" && !f.startsWith("users/"));
const hash = createHash("sha1");
for (const f of files.sort()) hash.update(f).update(readFileSync(join(dist, f)));
const version = hash.digest("hex").slice(0, 10);
const precache = ["./", ...files];
writeFileSync(join(dist, "sw.js"), readFileSync(join(root, "src/pwa/sw.js"), "utf8").replace("__VERSION__", version).replace("__FILES__", JSON.stringify(precache)));
const kb = (n) => (n / 1024).toFixed(0) + " kB";
console.log(`built dist/ v${version}: ${files.length} files, app.js ${kb(statSync(join(dist, "app.js")).size)}`);
