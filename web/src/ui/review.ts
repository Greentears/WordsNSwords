// Review tab: typed quiz, fill-in-the-blank quiz and sentence practice behind one tab.
import { h } from "./h";
import type { Shell, ReviewHost, ReviewMode } from "./shell";
import { quizScreen } from "./quiz";
import { sentencesScreen } from "./sentences";

export function reviewScreen(shell: Shell): HTMLElement {
  let mode: ReviewMode = "typed";
  const host: ReviewHost = {
    mode: () => mode,
    setMode(m) {
      mode = m;
      if (m === "sentences") { sentences.hidden = false; quiz.hidden = true; (sentences as any).reset(); }
      else { sentences.hidden = true; quiz.hidden = false; (quiz as any).setKind(m); }
    },
  };
  const quiz = quizScreen(shell, host);
  const sentences = sentencesScreen(shell, host);
  sentences.hidden = true;
  const root = h("div", { style: { height: "100%" } }, quiz, sentences);
  (root as any).reset = () => (mode === "sentences" ? (sentences as any).reset() : (quiz as any).reset());
  return root;
}
