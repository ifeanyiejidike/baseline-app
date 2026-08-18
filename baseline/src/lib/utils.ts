import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merges Tailwind class lists safely — clsx handles conditional class
 * composition, tailwind-merge resolves conflicts between classes that
 * target the same CSS property (e.g. `px-2` and a later `px-4` won't both
 * apply — the later one wins, as intended, instead of both landing in the
 * DOM and depending on source-order luck).
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
