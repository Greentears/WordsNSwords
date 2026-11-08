// Persistent overall statistics: port of progress.ProgressStore.update_session.
export interface Stats { sessions?: number; cards_reviewed?: number; known?: number; unknown?: number }

export function updateSession(stats: Stats, total: number, known: number, unknown: number): Stats {
  return {
    ...stats,
    sessions: (stats.sessions ?? 0) + 1,
    cards_reviewed: (stats.cards_reviewed ?? 0) + total,
    known: (stats.known ?? 0) + known,
    unknown: (stats.unknown ?? 0) + unknown,
  };
}
