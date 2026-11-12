// Review tab: typed quiz, fill-in-the-blank quiz, sentence practice and grammar quiz behind one tab.
import { h } from "./h";
import type { Shell, ReviewHost, ReviewMode } from "./shell";
import { quizScreen } from "./quiz";
import { sentencesScreen } from "./sentences";
import { grammarScreen } from "./grammar";

export function reviewScreen(shell: Shell): HTMLElement {
  let mode: ReviewMode = "typed";
  const host: ReviewHost = {
    mode: () => mode,
    setMode(m) {
      mode = m;
      sentences.hidden = m !== "sentences";
      grammar.hidden = m !== "grammar";
      quiz.hidden = m === "sentences" || m === "grammar";
      if (m === "sentences") (sentences as any).reset();
      else if (m === "grammar") (grammar as any).reset();
      else (quiz as any).setKind(m);
    },
  };
  const quiz = quizScreen(shell, host);
  const sentences = sentencesScreen(shell, host);
  const grammar = grammarScreen(shell, host);
  sentences.hidden = true;
  grammar.hidden = true;
  const root = h("div", { style: { height: "100%" } }, quiz, sentences, grammar);
  (root as any).reset = () => (mode === "sentences" ? (sentences as any).reset() : mode === "grammar" ? (grammar as any).reset() : (quiz as any).reset());
  return root;
}
