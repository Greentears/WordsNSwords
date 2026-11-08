# Fiszki: Polish ↔ English flashcards (phone web app)

Installable offline web app (PWA). Part of the WordsNSwords repository: the word lists come from `../users/<name>/<deck>/` (published next to the app and fetched by name), the tests use `../tests/fixtures/pl-en/`.
Phase 1 = everything except the Vocabulary Dungeon.

```bash
npm install            # esbuild, tsx, typescript, playwright, sharp
npm run build          # -> dist/ (static site: host it anywhere with HTTPS)
npm run serve          # http://localhost:4173 (service worker works on localhost)
npm test               # logic tests vs. golden.json made from the Python code
npm run golden         # regenerate tests/golden.json (needs the ../flashcards Python project)
node tests/e2e/step2.mjs [screenshot-dir]    # phone-emulation: study, reload, offline, swipe
node tests/e2e/step34.mjs [screenshot-dir]   # quizzes, sentences, search, backup round trip
```

Install: Android Chrome → menu → Install app. iPhone Safari → Share → Add to Home Screen.
Progress lives on the device (IndexedDB); use More → Export backup regularly (iPhone can evict data).
