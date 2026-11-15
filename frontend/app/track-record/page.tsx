import type { Metadata } from "next";
import { fetchAPI } from "@/lib/api";
import type { AccuracyStats } from "@/lib/types";
import { DIVISIONS } from "@/lib/constants";
import { StatsGrid } from "@/components/stats-grid";
import { TrackRecordList } from "./track-record-list";

export const metadata: Metadata = {
  title: "Track Record",
  description:
    "Historial completo de predicciones y precisión de Master Prediction.",
};

export default async function TrackRecordPage() {
  const stats = await fetchAPI<AccuracyStats>(
    "/api/public/predictions/stats"
  );

  if (!stats) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-20 text-center">
        <p className="text-gray-400">Datos temporalmente no disponibles.</p>
      </div>
    );
  }

  const divisionStats = Object.entries(stats.by_division)
    .map(([code, s]) => ({
      code,
      name: DIVISIONS[code]?.name ?? code,
      flag: DIVISIONS[code]?.flag ?? "",
      ...s,
    }))
    .sort((a, b) => b.accuracy - a.accuracy);

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="text-2xl md:text-3xl font-bold mb-6">Track Record</h1>

      <section className="mb-8">
        <StatsGrid stats={stats} />
      </section>

      <section className="mb-8">
        <h2 className="text-lg font-bold mb-4">Precisión por Liga</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-edge text-gray-400">
                <th className="py-2 text-left font-normal">Liga</th>
                <th className="py-2 text-right font-normal">Total</th>
                <th className="py-2 text-right font-normal">Aciertos</th>
                <th className="py-2 text-right font-normal">Precisión</th>
              </tr>
            </thead>
            <tbody>
              {divisionStats.map((d) => (
                <tr key={d.code} className="border-b border-edge/50">
                  <td className="py-2">
                    {d.flag} {d.name}
                  </td>
                  <td className="py-2 text-right tabular-nums text-gray-400">
                    {d.total}
                  </td>
                  <td className="py-2 text-right tabular-nums text-gray-400">
                    {d.correct}
                  </td>
                  <td className="py-2 text-right tabular-nums text-accent font-medium">
                    {(d.accuracy * 100).toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-bold mb-4">Resultados Recientes</h2>
        <TrackRecordList />
      </section>
    </div>
  );
}
