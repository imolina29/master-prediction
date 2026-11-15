import Link from "next/link";

export function LeagueCard({
  slug,
  name,
  flag,
}: {
  slug: string;
  name: string;
  flag: string;
}) {
  return (
    <Link href={`/liga/${slug}`} className="block group">
      <div className="rounded-xl border border-edge bg-surface p-4 text-center transition-colors group-hover:border-accent/40">
        <span className="text-2xl">{flag}</span>
        <p className="mt-2 text-sm font-medium">{name}</p>
      </div>
    </Link>
  );
}
