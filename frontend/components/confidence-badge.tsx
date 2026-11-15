import { CONFIDENCE_COLORS } from "@/lib/constants";

export function ConfidenceBadge({
  confidence,
}: {
  confidence: "alta" | "media" | "baja";
}) {
  const labels: Record<string, string> = {
    alta: "Alta",
    media: "Media",
    baja: "Baja",
  };
  return (
    <span
      className="inline-block rounded-full px-2.5 py-0.5 text-xs font-medium text-white"
      style={{ backgroundColor: CONFIDENCE_COLORS[confidence] }}
    >
      {labels[confidence]}
    </span>
  );
}
