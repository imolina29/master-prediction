import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { fetchAPI } from "@/lib/api";
import type { Prediction, AccuracyStats, LeagueInfo } from "@/lib/types";
import { SLUG_TO_DIVISION, DIVISIONS } from "@/lib/constants";
import { MatchCard } from "@/components/match-card";

export async function generateStaticParams() {
  return [];
}

export async function generateMetadata({
  params,
}: {
  params: { slug: string };
}): Promise<Metadata> {
  const code = SLUG_TO_DIVISION[params.slug];
  if (!code) return { title: "Liga no encontrada" };
  const div = DIVISIONS[code];
  return {
    title: `Predicciones ${div.name}`,
    description: `Predicciones de fútbol para ${div.name} basadas en inteligencia artificial.`,
  };
}

export default async function LeaguePage({
  params,
}: {
  params: { slug: string };
}) {
  const code = SLUG_TO_DIVISION[params.slug];
  if (!code) notFound();

  const div = DIVISIONS[code];

  const [leagueData, stats] = await Promise.all([
    fetchAPI<{ league: LeagueInfo; predictions: Prediction[] }>(
      `/api/public/league/${params.slug}/upcoming`
    ),
    fetchAPI<AccuracyStats>("/api/public/predictions/stats"),
  ]);

  if (!leagueData) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-20 text-center">
        <p className="text-gray-400">Datos temporalmente no disponibles.</p>
      </div>
    );
  }

  const predictions = leagueData.predictions.map((p) => ({
    ...p,
    match_slug: p.match_slug || `${p.home_team}-vs-${p.away_team}`,
    league_name: div.name,
    league_flag: div.flag,
    league_slug: params.slug,
  }));

  const divStats = stats?.by_division?.[code];

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl md:text-3xl font-bold">
          {div.flag} {div.name}
        </h1>
        {divStats && (
          <p className="mt-2 text-sm text-gray-400">
            Precisión:{" "}
            <span className="text-accent tabular-nums">
              {(divStats.accuracy * 100).toFixed(1)}%
            </span>{" "}
            en {divStats.total} predicciones
          </p>
        )}
      </div>

      <h2 className="text-lg font-bold mb-4">Próximos Partidos</h2>
      {predictions.length === 0 ? (
        <p className="text-gray-400">
          No hay partidos programados para {div.name} próximamente.
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {predictions.map((p) => (
            <MatchCard
              key={`${p.match_date}-${p.home_team}-${p.away_team}`}
              prediction={p}
            />
          ))}
        </div>
      )}
    </div>
  );
}
