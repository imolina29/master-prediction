export function ResultBadge({
  predicted,
  actual,
}: {
  predicted: string;
  actual: string;
}) {
  const correct = predicted === actual;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
        correct
          ? "bg-green-900/30 text-green-400"
          : "bg-red-900/30 text-red-400"
      }`}
    >
      {correct ? "✓ Acierto" : "✗ Fallo"}
    </span>
  );
}
