import type { Metadata } from "next";
import { fetchAPI } from "@/lib/api";
import type { MatchDetail } from "@/lib/types";
import { ConfidenceBadge } from "@/components/confidence-badge";
import { ProbabilityBar } from "@/components/probability-bar";
import { TeamComparison } from "@/components/team-comparison";
import { Ventajas } from "@/components/ventajas";

const RESULT_LABELS: Record<string, string> = {
  H: "Victoria Local",
  D: "Empate",
  A: "Victoria Visitante",
};

const CONFIDENCE_TEXTS: Record<string, string> = {
  alta: "El modelo acierta el 82% de las predicciones con este nivel de confianza.",
  media:
    "El modelo acierta el 54% de las predicciones con este nivel de confianza.",
  baja: "El modelo acierta el 36% de las predicciones con este nivel de confianza.",
};

export async function generateStaticParams() {
  return [];
}

export async function generateMetadata({
  params,
}: {
  params: { date: string; slug: string };
}): Promise<Metadata> {
  const data = await fetchAPI<MatchDetail>(
    `/api/public/match/${params.date}/${params.slug}`
  );
  if (!data) {
    return { title: "Partido no encontrado" };
  }
  const p = data.prediction;
  const title = `${p.home_team} vs ${p.away_team} — Predicción`;
  return {
    title,
    description: `Predicción y análisis estadístico de ${p.home_team} vs ${p.away_team}. ${data.league_name}.`,
    openGraph: {
      title,
      type: "website",
    },
  };
}

export default async function MatchDetailPage({
  params,
}: {
  params: { date: string; slug: string };
}) {
  const data = await fetchAPI<MatchDetail>(
    `/api/public/match/${params.date}/${params.slug}`
  );

  if (!data) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-20 text-center">
        <p className="text-gray-400">Datos temporalmente no disponibles.</p>
      </div>
    );
  }

  const p = data.prediction;
  const dateStr = new Intl.DateTimeFormat("es-ES", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(p.match_date + "T12:00:00"));

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "SportsEvent",
            name: `${p.home_team} vs ${p.away_team}`,
            startDate: p.match_date,
            homeTeam: { "@type": "SportsTeam", name: p.home_team },
            awayTeam: { "@type": "SportsTeam", name: p.away_team },
          }),
        }}
      />

      <div className="mx-auto max-w-4xl px-4 py-8">
        <div className="mb-2 text-sm text-gray-400">
          {data.league_flag} {data.league_name} · {dateStr}
        </div>

        <h1 className="text-2xl md:text-3xl font-bold mb-6">
          {p.home_team}{" "}
          <span className="text-gray-500 font-normal">vs</span>{" "}
          {p.away_team}
        </h1>

        <div className="rounded-xl border border-edge bg-surface p-6 mb-8">
          <div className="flex items-center gap-3 mb-4">
            <span className="text-lg font-bold text-accent">
              {RESULT_LABELS[p.predicted_result]}
            </span>
            <ConfidenceBadge confidence={p.confidence} />
          </div>

          <ProbabilityBar
            probHome={p.prob_home}
            probDraw={p.prob_draw}
            probAway={p.prob_away}
          />

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 text-center">
            <div>
              <p className="text-xs text-gray-400">Over 2.5</p>
              <p className="text-lg font-medium tabular-nums">
                {(p.prob_over25 * 100).toFixed(0)}%
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400">BTTS</p>
              <p className="text-lg font-medium tabular-nums">
                {(p.prob_btts * 100).toFixed(0)}%
              </p>
            </div>
            {data.elo && (
              <>
                <div>
                  <p className="text-xs text-gray-400">ELO Local</p>
                  <p className="text-lg font-medium tabular-nums">
                    {data.elo.home.toFixed(0)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">ELO Visitante</p>
                  <p className="text-lg font-medium tabular-nums">
                    {data.elo.away.toFixed(0)}
                  </p>
                </div>
              </>
            )}
          </div>

          <p className="mt-4 text-xs text-gray-500">
            {CONFIDENCE_TEXTS[p.confidence]}
          </p>
        </div>

        {data.ventajas && (
          <section className="mb-8">
            <h2 className="text-lg font-bold mb-4">Análisis de Ventajas</h2>
            <Ventajas
              ventajas={data.ventajas}
              homeTeam={p.home_team}
              awayTeam={p.away_team}
            />
          </section>
        )}

        <section className="mb-8">
          <h2 className="text-lg font-bold mb-4">Comparación Estadística</h2>
          <TeamComparison
            home={data.home_features}
            away={data.away_features}
            division={p.division}
            elo={data.elo}
          />
        </section>

        {data.h2h && data.h2h.length > 0 && (
          <section className="mb-8">
            <h2 className="text-lg font-bold mb-4">
              Historial Directo (últimos {data.h2h.length})
            </h2>
            <div className="space-y-2">
              {data.h2h.map((m, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between rounded-lg border border-edge/50 bg-surface px-4 py-2 text-sm"
                >
                  <span className="text-gray-400 tabular-nums">{m.date}</span>
                  <span className="tabular-nums">
                    {m.home_goals} - {m.away_goals}
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

        <p className="text-xs text-gray-500 text-center mt-12">
          Análisis informativo. Las decisiones de apuesta son responsabilidad
          exclusiva del usuario.
        </p>
      </div>
    </>
  );
}
