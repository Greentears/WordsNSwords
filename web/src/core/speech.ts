// Reading a word aloud with the device's built-in voice (the browser's speech synthesis).
// Nothing is downloaded or sent anywhere; which languages work depends on the voices installed on the phone.

const LANGUAGE_TAGS: Record<string, string> = { pl: "pl-PL", fr: "fr-FR", en: "en-GB", de: "de-DE", es: "es-ES", it: "it-IT", nl: "nl-NL" };

/** BCP-47 tag for a deck id like "pl-en": the language being learned (the first part). */
export const languageTag = (deckId: string): string => LANGUAGE_TAGS[deckId.split("-")[0]] ?? deckId.split("-")[0];

/** What to say for a card's word: parentheses are dropped ("pochodzić (z)" -> "pochodzić z"). */
export const spokenText = (word: string): string => word.replace(/[()]/g, " ").replace(/\s+/g, " ").trim();

export const speechSupported = (): boolean => typeof window !== "undefined" && "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;

function voices(): Promise<SpeechSynthesisVoice[]> {
  const synth = window.speechSynthesis;
  const now = synth.getVoices();
  if (now.length) return Promise.resolve(now);
  return new Promise((resolve) => {   // some browsers load the voice list a moment later
    const done = () => { synth.removeEventListener("voiceschanged", done); resolve(synth.getVoices()); };
    synth.addEventListener("voiceschanged", done);
    setTimeout(done, 700);
  });
}

/** Say the word. Returns a short message when it can't be spoken, otherwise null. */
export async function speak(word: string, deckId: string): Promise<string | null> {
  if (!speechSupported()) return "This browser can't read aloud.";
  const text = spokenText(word);
  if (!text) return null;
  const lang = languageTag(deckId);
  const prefix = lang.split("-")[0].toLowerCase();
  const list = await voices();
  const voice = list.find((v) => v.lang.toLowerCase() === lang.toLowerCase()) ?? list.find((v) => v.lang.toLowerCase().startsWith(prefix));
  if (list.length && !voice) return `No ${lang} voice on this device. Add one in the phone's text-to-speech settings.`;
  const synth = window.speechSynthesis;
  synth.cancel();
  const say = new SpeechSynthesisUtterance(text);
  say.lang = lang;
  if (voice) say.voice = voice;
  say.rate = 0.85;                    // a little slower, easier to catch while learning
  synth.speak(say);
  return null;
}
