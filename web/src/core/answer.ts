// Typed-answer checking: exact port of flashcards.accepted_answers / check_answer.
import { dropBrackets, normalise, stripAccents } from "./text";

export function acceptedAnswers(expected: string): string[] {
  const variants = [expected, ...expected.split(" / ").filter((p) => p.trim())];
  const result: string[] = [];
  for (const variant of variants) {
    const noBrackets = dropBrackets(variant);
    for (const candidate of [variant, noBrackets]) {
      const norm = normalise(candidate);
      if (!norm) continue;
      result.push(norm);
      if (norm.startsWith("to ")) result.push(norm.slice(3));
    }
  }
  return result;
}

/** Returns [correct, exact]. `exact` is false when only accepted because accents were ignored. */
export function checkAnswer(given: string, expected: string, ignoreAccents = true): [boolean, boolean] {
  const givenNorm = normalise(given);
  if (!givenNorm) return [false, false];
  const accepted = acceptedAnswers(expected);
  if (accepted.includes(givenNorm)) return [true, true];
  if (ignoreAccents) {
    const stripped = stripAccents(givenNorm);
    if (accepted.some((a) => stripped === stripAccents(a))) return [true, false];
  }
  return [false, false];
}
