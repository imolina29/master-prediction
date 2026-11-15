import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://master-prediction.com";

const LEAGUE_SLUGS = [
  "premier-league",
  "la-liga",
  "serie-a",
  "bundesliga",
  "ligue-1",
  "champions-league",
];

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const entries: MetadataRoute.Sitemap = [
    { url: SITE_URL, lastModified: new Date(), changeFrequency: "daily", priority: 1 },
    { url: `${SITE_URL}/track-record`, lastModified: new Date(), changeFrequency: "daily", priority: 0.8 },
    { url: `${SITE_URL}/acerca-de`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.3 },
    { url: `${SITE_URL}/aviso-legal`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.2 },
  ];

  for (const slug of LEAGUE_SLUGS) {
    entries.push({
      url: `${SITE_URL}/liga/${slug}`,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 0.7,
    });
  }

  try {
    const apiBase = process.env.API_BASE_URL || "http://localhost:8080";
    const res = await fetch(`${apiBase}/api/public/predictions/upcoming`, {
      headers: { "X-Internal-Key": process.env.INTERNAL_API_KEY || "" },
      next: { revalidate: 300 },
    });
    if (res.ok) {
      const data = await res.json();
      for (const p of data.predictions ?? []) {
        const matchSlug = p.match_slug;
        if (matchSlug) {
          entries.push({
            url: `${SITE_URL}/partido/${p.match_date}/${matchSlug}`,
            lastModified: new Date(),
            changeFrequency: "weekly",
            priority: 0.6,
          });
        }
      }
    }
  } catch {
    // API unreachable — sitemap still includes static pages
  }

  return entries;
}
