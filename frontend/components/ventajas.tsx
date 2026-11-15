export function Ventajas({
  ventajas,
  homeTeam,
  awayTeam,
}: {
  ventajas: { home: string[]; away: string[] };
  homeTeam: string;
  awayTeam: string;
}) {
  if (ventajas.home.length === 0 && ventajas.away.length === 0) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div>
        <h3 className="text-sm font-medium text-accent mb-3">
          Ventajas {homeTeam}
        </h3>
        {ventajas.home.length > 0 ? (
          <ul className="space-y-2">
            {ventajas.home.map((v, i) => (
              <li key={i} className="text-sm text-gray-300 flex gap-2">
                <span className="text-accent mt-0.5">•</span>
                {v}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-500">Sin ventajas destacadas</p>
        )}
      </div>
      <div>
        <h3 className="text-sm font-medium text-gray-400 mb-3">
          Ventajas {awayTeam}
        </h3>
        {ventajas.away.length > 0 ? (
          <ul className="space-y-2">
            {ventajas.away.map((v, i) => (
              <li key={i} className="text-sm text-gray-300 flex gap-2">
                <span className="text-gray-500 mt-0.5">•</span>
                {v}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-500">Sin ventajas destacadas</p>
        )}
      </div>
    </div>
  );
}
