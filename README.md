# WordsNSwords

Vocabulary flashcards with a small dungeon game, as a PC app and as a phone app, sharing one set of word lists.

```
users/<name>/<deck>/     your cards: words.json, verbs.json, nouns.json, adjectives.json, sentences.json, examples.json
users/_template/<deck>/  the starter deck a new name begins with
desktop/                 the PC app (Python, PySide6)
web/                     the phone app (TypeScript, installable PWA)
tests/fixtures/pl-en/    a frozen copy of a word list, used by the tests of both apps
local/                   your progress on THIS computer (levels, dungeon save). Not in git.
```

* **Names.** Both apps ask for a name on first start. It is your hero's name and picks the folder `users/<name>`
  (lower case, no accents or spaces: "Devoriah" -> `users/devoriah`). A name without a folder can start from the
  starter deck.
* **Decks.** Today there is one: `pl-en` (Polish -> English). A deck is a folder, so `fr-en` is a new folder
  next to it.
* **Progress stays local.** Levels, fail counts, statistics and the dungeon save (each deck has its own hero) live
  on each device. To move them between phone and PC: *More -> Export backup* on one, then
  *More -> Import* (phone) or *File -> Import backup* (PC) on the other. The two use the same file format.
* **Words come from the repository.** Edit `users/<name>/pl-en/words.json`, commit, push. The phone shows the new
  version after the next publish: *More -> Update words from the repository*; levels are kept.

## Adding words with an AI

> **In the apps:** phone → More → *Add words*; PC → File → *Add words…*. Type the words, copy the prompt (built from
> `languages/<deck>/prompt.txt`, the same file the blocks below show), paste the AI's answer and press *Check and add*.
> Problems are listed and can be copied back to the AI. The prompt blocks below are generated:
> edit `languages/<deck>/prompt.txt`, then run `python tools/sync_readme_prompts.py`.

**Send for review (pull request).** After *Check and add*, a *Send for review* button appears. It opens a pull request
on GitHub with your new cards and tables, so you can look at them and merge. Anyone without a token can use
*Copy what I added instead* and send you the text.
- The token is typed into the app once and stays on that device only (phone: private app storage; PC:
  `local/github_token.txt`, which git ignores). It is never in the code, the repository, the published site or a backup.
- Make a fine-grained token at GitHub -> Settings -> Developer settings -> Personal access tokens: only the
  `WordsNSwords` repository, an expiry date, permissions **Contents: read & write** and **Pull requests: read & write**.
- If the token is lost or leaked, delete it on GitHub; nothing else needs to change.


The cards, the sentences and the grammar tables are JSON files in `users/<name>/<deck>/`. An AI chat (any
assistant) can write them for you if you give it the format. The **tables depend on the language**: Polish has
conjugation and seven-case declension tables; French needs other tables, which the apps don't show yet.

1. Copy the prompt below into the AI chat and replace the word list at the end.
2. Save the AI's answer (only the JSON) as a text file, for example `answer.json`.
3. Check it and add it to your deck:
   `python tools/add_words.py devoriah answer.json`
   The script checks every field (number of forms, genders, aspects, cards that match) and adds only what is
   new. Words that already exist are skipped, so your own edits stay. If something is wrong it lists the
   problems and changes nothing: paste the list back to the AI and ask for a corrected answer.
4. Look at the changes in GitHub Desktop, **skim the grammar tables** (the script checks the shape, not the
   grammar: an AI can get a rare declension wrong), then commit and push. On the phone: *More -> Update words*.

### Prompt for a Polish -> English deck (`pl-en`)

<!-- prompt:pl-en -->
````text
You are helping me build a Polish -> English vocabulary deck. For the words at the end, write ONE JSON object
and nothing else: no explanation, no markdown fence. Leave out a key that has no entries.

"words": one entry per word:
  {"word": "<Polish card text>", "translation": "<short English meaning>",
   "sentence": "<one natural Polish sentence using the word, level A2-B1>",
   "sentence_translation": "<its English translation>"}
  - The card text is the dictionary form: verbs in the infinitive (reflexive verbs keep "się", e.g. "bać się"),
    nouns in the nominative singular, adjectives in the masculine nominative singular. If I wrote alternatives
    with " / " (for example "kwaśny / kwaśno"), keep them exactly.
  - translation: concise; alternatives separated by " / "; verbs start with "to ".

"verbs": for every verb card:
  {"card": "<the card text exactly>", "verbs": [{"infinitive": "...", "aspect": "imperfective" or "perfective",
   "forms": [6 strings: ja, ty, on/ona/ono, my, wy, oni/one] (present tense for imperfective, simple future for
   perfective), "past": [5 strings: on, ona, ono, oni (men plural), one (other plural)],
   "imperative": [3 strings: ty, my, wy]}]}
  If the card names an aspect pair, list both verbs in "verbs".

"nouns": for every noun and numeral card:
  {"card": "<exactly>", "nouns": [{"lemma": "...", "gender": "m" or "f" or "n" or "pl" or "num",
   "singular": [7 strings], "plural": [7 strings]}]}
  Case order: mianownik, dopełniacz, celownik, biernik, narzędnik, miejscownik, wołacz. Numerals: gender "num"
  and plural = 7 x null. A noun without a singular (or plural) gets 7 x null for it. Where two forms are
  correct, write "form1 / form2".

"adjectives": for every adjective card:
  {"card": "<exactly>", "adjectives": [{"lemma": "...", "forms": {"m": [7], "f": [7], "n": [7], "pl": [7]}}]}
  Same case order. Where two forms are correct, write "form1 / form2".

Adverbs, fixed phrases, conjunctions, prepositions and other words that do not change get NO entry in verbs,
nouns or adjectives.

"examples": {"<card text exactly>": [two more natural sentences {"pl": "...", "en": "..."} using the word in
  different situations]}

"sentences": 5 to 10 short practice sentences that combine several of the words:
  [{"pl": "...", "en": "...", "words": ["<card text of each word used>"]}]

Rules: valid JSON (double quotes, no trailing commas, no comments, Polish letters as normal UTF-8 text). Every
"card" and every item in "words" lists must be written exactly like the "word" of an entry in "words". Do not
invent forms; if unsure, give the most standard form.

WORDS:
- bać się
- biletomat
- kwaśny / kwaśno
````
<!-- /prompt:pl-en -->

### Prompt for a French -> English deck (`fr-en`)

French has no tables in the apps yet, so ask only for cards, examples and practice sentences. The keys of
`examples` and `sentences` are still called `pl` and `en` (they mean "the language you learn" and "English");
that will be renamed when French is added to the apps.

<!-- prompt:fr-en -->
````text
You are helping me build a French -> English vocabulary deck. For the words at the end, write ONE JSON object
and nothing else: no explanation, no markdown fence.

"words": [{"word": "<French card text>", "translation": "<short English meaning>",
           "sentence": "<one natural French sentence, level A2-B1>", "sentence_translation": "<English>"}]
  - Nouns with their article: "la maison", "le chat", "l'ami / l'amie". Verbs in the infinitive.
  - translation: concise; alternatives separated by " / "; verbs start with "to ".
"examples": {"<card text exactly>": [two more sentences {"pl": "<French>", "en": "<English>"}]}
"sentences": 5 to 10 short practice sentences combining several of the words:
  [{"pl": "<French>", "en": "<English>", "words": ["<card text of each word used>"]}]

Rules: valid JSON (double quotes, no trailing commas, no comments, accents as normal UTF-8 text). Every "card"
and every item in a "words" list must be written exactly like the "word" of an entry in "words".

WORDS:
- la maison
- manger
````
<!-- /prompt:fr-en -->

## Publishing the phone app (GitHub Pages)

1. Push this folder to GitHub (GitHub Desktop: *Add local repository*, Commit, Push).
2. Repository *Settings -> Pages -> Source: GitHub Actions*.
3. After the first run of *Publish the phone app* (Actions tab) the app is at
   `https://<your-account>.github.io/<repository>/`. Open it on the phone and choose *Install app* / *Add to Home screen*.

The workflow runs all tests first and only publishes if they pass.

**Moving from the Netlify version:** the phone keeps its data per website address, so the new address starts empty.
In the old app: *More -> Export backup*. In the new app: type your name, then *More -> Import -> Replace everything*.

## Running things

* PC: `desktop/run.bat` (Windows) or `python desktop/main.py` (needs `pip install -r desktop/requirements.txt`).
* Phone app in a browser: `cd web && npm install && npm run build && npm run serve`.
* Tests: `cd desktop && python -m unittest discover -s tests`, `cd web && npm test`.
* Add words from an AI answer: `python tools/add_words.py <name> answer.json` (see "Adding words with an AI").
* After changing a game rule in Python: `cd web && python tools/export_dungeon_data.py && python tools/make_dungeon_golden.py`,
  then `npm test` (the TypeScript port must give the same results).

See `desktop/README.md` and `web/README.md` for the details of each app.
