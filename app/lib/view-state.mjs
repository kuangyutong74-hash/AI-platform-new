const PERSONAL_VIEWS = new Set(["planet", "works", "timeline"]);

export function getViewFromUrl(input) {
  const url = new URL(input, "http://localhost");
  const requested = url.searchParams.get("view") ?? "planet";
  return PERSONAL_VIEWS.has(requested) ? requested : "planet";
}

export function urlForView(view) {
  return view === "planet" ? "/" : `/?view=${view}`;
}
