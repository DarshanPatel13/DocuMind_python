import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge conditional class names, with later Tailwind utilities winning
 * conflicts (e.g. cn("px-2", isBig && "px-4") → "px-4"). The standard shadcn/ui
 * helper. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
