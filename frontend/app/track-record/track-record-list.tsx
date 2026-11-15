"use client";

import { useEffect, useState } from "react";
import { DIVISIONS } from "@/lib/constants";
import { ConfidenceBadge } from "@/components/confidence-badge";
import { ResultBadge } from "@/components/result-badge";

interface TrackRecordRow {
  match_date: string;
  home_team: string;
  away_team: string;
  division: string;
  predicted_result: string;
  ft_result: string;
  confidence: "alta" | "media" | "baja";
  correct: boolean;
}

interface TrackRecordResponse {
  predictions: TrackRecordRow[];
  page: number;
  total: number;
  pages: number;
}

const RESULT_LABELS: Record<string, string> = {
  H: "Local",
  D: "Empate",
  A: "Visitante",
};

export function TrackRecordList() {
  const [data, setData] = useState<TrackRecordResponse | null>(null);
  const [page, setPage] = useState(1);
  const [division, setDivision] = useState("");
  const [confidence, setConfidence] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams({
      page: String(page),
      per_page: "50",
    });
    if (division) params.set("division", division);
    if (confidence) params.set("confidence", confidence);

    fetch(`/api/public/predictions/track-record?${params}`)
      .then((r) => r.json())
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [page, division, confidence]);

  return (
    <div>
      <div className="flex flex-wrap gap-3 mb-4">
        <select
          value={division}
          onChange={(e) => {
            setDivision(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-edge bg-surface px-3 py-1.5 text-sm text-white"
        >
          <option value="">Todas las ligas</option>
          {Object.entries(DIVISIONS).map(([code, { name }]) => (
            <option key={code} value={code}>
              {name}
            </option>
          ))}
        </select>

        <select
          value={confidence}
          onChange={(e) => {
            setConfidence(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-edge bg-surface px-3 py-1.5 text-sm text-white"
        >
          <option value="">Toda confianza</option>
          <option value="alta">Alta</option>
          <option value="media">Media</option>
          <option value="baja">Baja</option>
        </select>
      </div>

      {loading ? (
        <p className="text-gray-400 py-8 text-center">Cargando...</p>
      ) : !data || data.predictions.length === 0 ? (
        <p className="text-gray-400 py-8 text-center">
          No hay resultados con estos filtros.
        </p>
      ) : (
        <>
          <div className="space-y-2">
            {data.predictions.map((p, i) => (
              <div
                key={i}
                className="flex flex-wrap items-center gap-3 rounded-lg border border-edge/50 bg-surface px-4 py-2.5 text-sm"
              >
                <span className="text-gray-500 tabular-nums w-20 shrink-0">
                  {p.match_date}
                </span>
                <span className="flex-1 min-w-0">
                  {p.home_team} vs {p.away_team}
                </span>
                <span className="text-gray-400 w-16 text-center">
                  {RESULT_LABELS[p.predicted_result]}
                </span>
                <span className="text-gray-400 w-16 text-center">
                  {RESULT_LABELS[p.ft_result] ?? "—"}
                </span>
                <ResultBadge
                  predicted={p.predicted_result}
                  actual={p.ft_result}
                />
                <ConfidenceBadge confidence={p.confidence} />
              </div>
            ))}
          </div>

          {data.pages > 1 && (
            <div className="flex items-center justify-center gap-4 mt-6">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page <= 1}
                className="rounded-lg border border-edge px-3 py-1.5 text-sm disabled:opacity-30 hover:border-accent/40 transition-colors"
              >
                Anterior
              </button>
              <span className="text-sm text-gray-400 tabular-nums">
                {data.page} / {data.pages}
              </span>
              <button
                onClick={() => setPage(Math.min(data.pages, page + 1))}
                disabled={page >= data.pages}
                className="rounded-lg border border-edge px-3 py-1.5 text-sm disabled:opacity-30 hover:border-accent/40 transition-colors"
              >
                Siguiente
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
