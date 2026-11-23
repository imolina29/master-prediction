import { fetchAPI } from "@/lib/api";
import type { Prediction, AccuracyStats } from "@/lib/types";
import { DIVISIONS } from "@/lib/constants";
import { MatchCard } from "@/components/match-card";
import { StatsGrid } from "@/components/stats-grid";
import { LeagueCard } from "@/components/league-card";

export default async function Home() {
  const [upcomingData, stats] = await Promise.all([
    fetchAPI<{ predictions: Prediction[] }>("/api/public/predictions/upcoming"),
    fetchAPI<AccuracyStats>("/api/public/predictions/stats"),
  ]);

  if (!upcomingData || !stats) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-20 text-center">
        <p className="text-gray-400">Datos temporalmente no disponibles.</p>
      </div>
    );
  }

  const predictions = upcomingData.predictions;
  const featured = [...predictions]
    .sort((a, b) => {
      const order = { alta: 0, media: 1, baja: 2 };
      return (order[a.confidence] ?? 2) - (order[b.confidence] ?? 2);
    })
    .slice(0, 6);

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "WebSite",
            name: "Master Prediction",
            url: process.env.SITE_URL || "https://masterprediction.up.railway.app",
            description:
              "Predicciones de fútbol europeo basadas en inteligencia artificial",
          }),
        }}
      />

      <section className="mx-auto max-w-6xl px-4 pt-12 pb-8">
        <h1 className="text-3xl md:text-4xl font-bold mb-2">
          Predicciones de Fútbol Europeo
        </h1>
        <p className="text-gray-400 mb-8 max-w-2xl">
          Análisis estadístico avanzado con inteligencia artificial para las
          principales ligas europeas.
        </p>
        <StatsGrid stats={stats} />
      </section>

      <section className="mx-auto max-w-6xl px-4 py-8">
        <h2 className="text-xl font-bold mb-6">Partidos Destacados</h2>
        {featured.length === 0 ? (
          <p className="text-gray-400">No hay partidos programados.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {featured.map((p) => (
              <MatchCard
                key={`${p.match_date}-${p.home_team}-${p.away_team}`}
                prediction={p}
              />
            ))}
          </div>
        )}
      </section>

      <section className="mx-auto max-w-6xl px-4 py-8">
        <h2 className="text-xl font-bold mb-6">Ligas</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {Object.entries(DIVISIONS).map(([code, { slug, name, flag }]) => (
            <LeagueCard key={code} slug={slug} name={name} flag={flag} />
          ))}
        </div>
      </section>
    </>
  );
}
