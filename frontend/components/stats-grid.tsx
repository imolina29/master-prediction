import type { AccuracyStats } from "@/lib/types";

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-edge bg-surface p-4">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className="text-2xl font-bold text-accent tabular-nums">{value}</p>
    </div>
  );
}

export function StatsGrid({ stats }: { stats: AccuracyStats }) {
  const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <StatCard
        label="Predicciones totales"
        value={stats.total.toLocaleString("es-ES")}
      />
      <StatCard label="Precisión general" value={pct(stats.accuracy)} />
      <StatCard
        label="Precisión alta confianza"
        value={pct(stats.by_confidence?.alta?.accuracy ?? 0)}
      />
      <StatCard
        label="Precisión media confianza"
        value={pct(stats.by_confidence?.media?.accuracy ?? 0)}
      />
    </div>
  );
}
