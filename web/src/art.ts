// Which pictures exist (src/art.json, written by tools/import_art.py) and where they are on the site.
// Every picture is optional: without one the game draws its pixel sprite or an emoji.
import index from "./art.json";

export type ArtKind = "monsters" | "companions" | "items" | "heroes" | "backgrounds" | "ui";
const have = index as Record<ArtKind, string[]>;

export const hasArt = (kind: ArtKind, key: string): boolean => (have[kind] ?? []).includes(key);
export const artUrl = (kind: ArtKind, key: string): string => `art/${kind}/${key}.webp`;
export const HERO_GENDERS = ["f", "m"] as const;
export type HeroGender = (typeof HERO_GENDERS)[number];
export const heroChoiceAvailable = (): boolean => HERO_GENDERS.every((g) => hasArt("heroes", g));
export const isHeroGender = (v: unknown): v is HeroGender => v === "f" || v === "m";

/** The hero picture for his gear: bare, with a sword, with armour, or both (null if there is none). */
export function heroArt(gender: string | null, weapon: boolean, armor: boolean): string | null {
  if (!gender) return null;
  const look = gender + (armor ? "_armour" : "") + (weapon ? "_sword" : "");
  if (hasArt("heroes", look)) return artUrl("heroes", look);
  return hasArt("heroes", gender) ? artUrl("heroes", gender) : null;
}

const OUTDOOR_DUNGEONS = ["forest", "citadel"]; // every other dungeon is indoors
/** The picture for a rest or treasure room, indoor or outdoor like its dungeon (null if there is none). */
export function sceneKey(kind: "rest" | "treasure", dungeon: string | undefined): string | null {
  const key = `${kind}_${dungeon && OUTDOOR_DUNGEONS.includes(dungeon) ? "outdoor" : "indoor"}`;
  return hasArt("backgrounds", key) ? key : null;
}
