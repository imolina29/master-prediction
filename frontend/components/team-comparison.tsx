import type { TeamFeatures } from "@/lib/types";

interface Props {
  home: TeamFeatures | null;
  away: TeamFeatures | null;
  division: string;
  elo: { home: number; away: number } | null;
}

type Row = {
  label: string;
  homeVal: number | null | undefined;
  awayVal: number | null | undefined;
  format: (v: number) => string;
  higherBetter: boolean;
};

export function TeamComparison({ home, away, division, elo }: Props) {
  const pct = (v: number) => `${(v * 100).toFixed(0)}%`;
  const dec = (v: number) => v.toFixed(2);
  const int = (v: number) => v.toFixed(0);

  const rows: Row[] = [
    ...(elo
      ? [
          {
            label: "ELO",
            homeVal: elo.home,
            awayVal: elo.away,
            format: int,
            higherBetter: true,
          },
        ]
      : []),
    {
      label: "Goles anotados (temp.)",
      homeVal: home?.goals_scored_avg,
      awayVal: away?.goals_scored_avg,
      format: dec,
      higherBetter: true,
    },
    {
      label: "Goles anotados (últ. 3)",
      homeVal: home?.goals_scored_avg_3,
      awayVal: away?.goals_scored_avg_3,
      format: dec,
      higherBetter: true,
    },
    {
      label: "Goles recibidos (temp.)",
      homeVal: home?.goals_conceded_avg,
      awayVal: away?.goals_conceded_avg,
      format: dec,
      higherBetter: false,
    },
    {
      label: "Goles recibidos (últ. 3)",
      homeVal: home?.goals_conceded_avg_3,
      awayVal: away?.goals_conceded_avg_3,
      format: dec,
      higherBetter: false,
    },
    {
      label: "% Victorias (temp.)",
      homeVal: home?.win_rate,
      awayVal: away?.win_rate,
      format: pct,
      higherBetter: true,
    },
    {
      label: "% Victorias (últ. 3)",
      homeVal: home?.win_rate_3,
      awayVal: away?.win_rate_3,
      format: pct,
      higherBetter: true,
    },
    {
      label: "xG a favor",
      homeVal: home?.xg_for_avg,
      awayVal: away?.xg_for_avg,
      format: dec,
      higherBetter: true,
    },
    {
      label: "xG en contra",
      homeVal: home?.xg_against_avg,
      awayVal: away?.xg_against_avg,
      format: dec,
      higherBetter: false,
    },
    {
      label: "BTTS",
      homeVal: home?.btts_rate,
      awayVal: away?.btts_rate,
      format: pct,
      higherBetter: true,
    },
    {
      label: "Over 2.5",
      homeVal: home?.over25_rate,
      awayVal: away?.over25_rate,
      format: pct,
      higherBetter: true,
    },
    ...(division !== "EC"
      ? [
          {
            label: "Posición en liga",
            homeVal: home?.league_pos,
            awayVal: away?.league_pos,
            format: int,
            higherBetter: false,
          },
        ]
      : []),
    {
      label: "H2H % Victorias",
      homeVal: home?.h2h_win_rate,
      awayVal: away?.h2h_win_rate,
      format: pct,
      higherBetter: true,
    },
    {
      label: "H2H Goles prom.",
      homeVal: home?.h2h_avg_goals,
      awayVal: away?.h2h_avg_goals,
      format: dec,
      higherBetter: true,
    },
  ];

  const validRows = rows.filter(
    (r): r is Row & { homeVal: number; awayVal: number } =>
      r.homeVal != null && r.awayVal != null
  );

  if (validRows.length === 0) return null;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-edge text-gray-400">
            <th className="py-2 text-left font-normal">Estadística</th>
            <th className="py-2 text-right font-normal">Local</th>
            <th className="py-2 text-right font-normal">Visitante</th>
          </tr>
        </thead>
        <tbody>
          {validRows.map((r) => {
            const homeBetter = r.higherBetter
              ? r.homeVal > r.awayVal
              : r.homeVal < r.awayVal;
            const awayBetter = r.higherBetter
              ? r.awayVal > r.homeVal
              : r.awayVal < r.homeVal;
            return (
              <tr key={r.label} className="border-b border-edge/50">
                <td className="py-2 text-gray-300">{r.label}</td>
                <td
                  className={`py-2 text-right tabular-nums ${homeBetter ? "text-accent font-medium" : "text-gray-400"}`}
                >
                  {r.format(r.homeVal)}
                </td>
                <td
                  className={`py-2 text-right tabular-nums ${awayBetter ? "text-accent font-medium" : "text-gray-400"}`}
                >
                  {r.format(r.awayVal)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
