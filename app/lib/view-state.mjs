const STUDENT_VIEWS = new Set(["planet", "works", "treasure"]);
const ADULT_VIEWS = new Set(["report", "showcase", "timeline"]);

export function getViewFromUrl(input, role = "student") {
  const url = new URL(input, "http://localhost");
  const fallback = role === "adult" ? "report" : "planet";
  const requested = url.searchParams.get("view") ?? fallback;
  const allowed = role === "adult" ? ADULT_VIEWS : STUDENT_VIEWS;
  return allowed.has(requested) ? requested : fallback;
}

export function urlForView(view, role = "student") {
  const fallback = role === "adult" ? "report" : "planet";
  return view === fallback ? "/" : `/?view=${view}`;
}
