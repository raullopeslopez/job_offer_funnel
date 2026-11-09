import { useEffect, useRef, useState } from "react";

/** Grid width (not viewport width) below which listings hide their secondary columns. */
export const NARROW_GRID_PX = 640;

/** A ref for the grid's container and whether it is narrower than `NARROW_GRID_PX`. */
export function useNarrowGrid<T extends HTMLElement = HTMLDivElement>() {
  const ref = useRef<T>(null);
  const [narrow, setNarrow] = useState(false);
  useEffect(() => {
    const element = ref.current;
    if (!element || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(([entry]) => {
      if (entry) setNarrow(entry.contentRect.width < NARROW_GRID_PX);
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  return [ref, narrow] as const;
}
