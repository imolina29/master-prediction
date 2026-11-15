import Link from "next/link";
import type { Prediction } from "@/lib/types";
import { ConfidenceBadge } from "./confidence-badge";
import { ProbabilityBar } from "./probability-bar";

const RESULT_LABELS: Record<string, string> = {
  H: "Local",
  D: "Empate",
  A: "Visitante",
};

export function MatchCard({ prediction }: { prediction: Prediction }) {
  const p = prediction;
  const dateStr = new Intl.DateTimeFormat("es-ES", {
    weekday: "short",
    day: "numeric",
    month: "short",
  }).format(new Date(p.match_date + "T12:00:00"));

  const href = `/partido/${p.match_date}/${p.match_slug}`;

  return (
    <Link href={href} className="block group">
      <div className="rounded-xl border border-edge bg-surface p-4 transition-colors group-hover:border-accent/40">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs text-gray-400">
            {p.league_flag} {p.league_name}
          </span>
          <span className="text-xs text-gray-500">{dateStr}</span>
        </div>

        <div className="flex items-center justify-between mb-3">
          <span className="font-medium">{p.home_team}</span>
          <span className="text-xs text-gray-500 mx-2">vs</span>
          <span className="font-medium text-right">{p.away_team}</span>
        </div>

        <ProbabilityBar
          probHome={p.prob_home}
          probDraw={p.prob_draw}
          probAway={p.prob_away}
        />

        <div className="flex items-center justify-between mt-3">
          <span className="text-sm text-accent font-medium">
            {RESULT_LABELS[p.predicted_result]}
          </span>
          <ConfidenceBadge confidence={p.confidence} />
        </div>
      </div>
    </Link>
  );
}
