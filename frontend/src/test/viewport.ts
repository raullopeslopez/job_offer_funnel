// jsdom has no matchMedia: the width queries are answered from a width, wide (a desktop) unless a test
// calls setViewportWidth before rendering.
const WIDE = 1280;
let viewportWidth = WIDE;

export const setViewportWidth = (width: number) => {
  viewportWidth = width;
};
export const resetViewport = () => setViewportWidth(WIDE);

const holds = (query: string) => {
  const min = /\(min-width:\s*([\d.]+)px\)/.exec(query);
  const max = /\(max-width:\s*([\d.]+)px\)/.exec(query);
  // Other queries (a color scheme, a pointer) do not hold, as without matchMedia.
  if (!min && !max) return false;
  return (!min || viewportWidth >= Number(min[1])) && (!max || viewportWidth <= Number(max[1]));
};

export const matchMedia = (query: string) =>
  ({
    matches: holds(query),
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  }) as MediaQueryList;
