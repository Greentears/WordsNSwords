import { App } from "./state";
import { requestPersistence } from "./store";
import { h } from "./ui/h";
import { makeSheet, type Shell, type Tab } from "./ui/shell";
import { studyScreen } from "./ui/study";
import { reviewScreen } from "./ui/review";
import { dungeonScreen } from "./ui/dungeon";
import { searchScreen } from "./ui/search";
import { moreScreen } from "./ui/more";
import { welcome } from "./ui/welcome";

const TABS: [Tab, string, string][] = [["study", "Study", "🗂"], ["review", "Review", "✍️"], ["dungeon", "Dungeon", "⚔️"], ["search", "Search", "🔍"], ["more", "More", "⚙️"]];

async function boot() {
  const root = document.getElementById("app")!;
  let app: App;
  try { app = await App.load(); } catch (e) {
    root.replaceChildren(h("p", { class: "boot" }, `Could not start: ${(e as Error).message}`));
    return;
  }
  app.applyTheme();
  if (!app.deck) await new Promise<void>((done) => welcome(root, app, done));   // first start: ask for a name
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => app.applyTheme());
  requestPersistence();

  const screensHost = h("div", { class: "screens" });
  const tabbar = h("nav", { class: "tabbar", "aria-label": "Main" });
  root.replaceChildren(screensHost, tabbar);

  let current: Tab = "study";
  const screens = {} as Record<Tab, HTMLElement>;
  const tabButtons = {} as Record<Tab, HTMLElement>;

  const shell: Shell = {
    app,
    go(tab) {
      const previous = current;
      current = tab;
      if (previous === "dungeon" && tab !== "dungeon") (screens.dungeon as any).pause();
      for (const t of TABS) { screens[t[0]].hidden = t[0] !== tab; tabButtons[t[0]].classList.toggle("on", t[0] === tab); tabButtons[t[0]].setAttribute("aria-current", t[0] === tab ? "page" : "false"); }
      if (tab === "more") (screens.more as any).render();
      if (tab === "search") (screens.search as any).render();
      if (tab === "dungeon") (screens.dungeon as any).show();
      if (tab === "study" || tab === "more") shell.fullscreen(false);
    },
    toast(msg) {
      document.querySelector(".toast")?.remove();
      const t = h("div", { class: "toast", role: "status" }, msg);
      document.body.append(t);
      setTimeout(() => t.remove(), 2600);
    },
    sheet: makeSheet(document.body),
    confirm(title, text, okLabel, danger = false) {
      return new Promise<boolean>((resolve) => {
        let answered = false;
        const done = (v: boolean) => { if (answered) return; answered = true; close(); resolve(v); };
        const close = shell.sheet(h("div", { class: "sheet-body" }, h("h2", null, title), h("p", { class: "muted" }, text),
          h("div", { class: "btn-row" }, h("button", { class: "btn", onclick: () => done(false) }, "Cancel"), h("button", { class: "btn " + (danger ? "danger" : "primary"), onclick: () => done(true) }, okLabel))),
        { onClose: () => done(false) });
      });
    },
    fullscreen(on) { tabbar.hidden = on; },
    studyView(prepare, label = "") {
      prepare();
      shell.go("study");
      (screens.study as any).refresh(label);
    },
    refreshBadges() {
      tabButtons.more.querySelector(".dot")?.remove();
      if (app.needsBackup) tabButtons.more.append(h("span", { class: "dot", title: "Back up your progress" }));
    },
  };

  screens.study = studyScreen(shell);
  screens.review = reviewScreen(shell);
  screens.dungeon = dungeonScreen(shell);
  screens.search = searchScreen(shell);
  screens.more = moreScreen(shell);
  for (const [tab, label, ico] of TABS) {
    screensHost.append(screens[tab]);
    const b = h("button", { class: "tab", type: "button", onclick: () => { if (tab === current && tab === "review") (screens[tab] as any).reset(); shell.go(tab); } },
      h("span", { class: "ico", "aria-hidden": "true" }, ico), label);
    tabButtons[tab] = b;
    tabbar.append(b);
  }
  app.listeners.add(() => shell.refreshBadges());
  shell.go("study");
  shell.refreshBadges();

  // Keep the layout above the on-screen keyboard (iOS does not resize the page for it).
  const vv = window.visualViewport;
  if (vv) {
    const fit = () => { document.documentElement.style.setProperty("--vh", `${vv.height}px`); if (vv.offsetTop) window.scrollTo(0, 0); };
    vv.addEventListener("resize", fit); vv.addEventListener("scroll", fit); fit();
  }

  (window as any).__app = app; // handy for tests and debugging
  if ("serviceWorker" in navigator && location.protocol !== "file:") navigator.serviceWorker.register("sw.js").catch(() => {});
}

boot();
