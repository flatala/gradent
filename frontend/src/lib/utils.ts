import type { ClassValue } from "clsx";
import clsx from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Combine Tailwind classes with automatic conflict resolution.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(...inputs));
}


