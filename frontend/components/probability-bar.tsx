export function ProbabilityBar({
  probHome,
  probDraw,
  probAway,
}: {
  probHome: number;
  probDraw: number;
  probAway: number;
}) {
  const fmt = (v: number) => `${(v * 100).toFixed(0)}%`;
  return (
    <div className="w-full">
      <div className="flex text-xs text-gray-400 mb-1 justify-between">
        <span>Local {fmt(probHome)}</span>
        <span>Empate {fmt(probDraw)}</span>
        <span>Visitante {fmt(probAway)}</span>
      </div>
      <div className="flex h-2 rounded-full overflow-hidden gap-0.5">
        <div
          className="rounded-l-full"
          style={{ width: fmt(probHome), backgroundColor: "#d4a017" }}
        />
        <div style={{ width: fmt(probDraw), backgroundColor: "#4b5563" }} />
        <div
          className="rounded-r-full"
          style={{ width: fmt(probAway), backgroundColor: "#6b7280" }}
        />
      </div>
    </div>
  );
}
