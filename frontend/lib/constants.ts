export const DIVISIONS: Record<
  string,
  { slug: string; name: string; flag: string }
> = {
  E0: { slug: "premier-league", name: "Premier League", flag: "🏴󠁧󠁢󠁥󠁮󠁧󠁿" },
  SP1: { slug: "la-liga", name: "La Liga", flag: "🇪🇸" },
  I1: { slug: "serie-a", name: "Serie A", flag: "🇮🇹" },
  D1: { slug: "bundesliga", name: "Bundesliga", flag: "🇩🇪" },
  F1: { slug: "ligue-1", name: "Ligue 1", flag: "🇫🇷" },
  EC: { slug: "champions-league", name: "Champions League", flag: "🏆" },
};

export const SLUG_TO_DIVISION: Record<string, string> = Object.fromEntries(
  Object.entries(DIVISIONS).map(([code, { slug }]) => [slug, code])
);

export const CONFIDENCE_COLORS: Record<string, string> = {
  alta: "#d4a017",
  media: "#6b7280",
  baja: "#4b5563",
};
