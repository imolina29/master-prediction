import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-20 text-center">
      <h1 className="text-4xl font-bold text-accent mb-4">404</h1>
      <p className="text-gray-400 mb-6">Página no encontrada.</p>
      <Link
        href="/"
        className="inline-block rounded-lg border border-accent px-4 py-2 text-sm text-accent hover:bg-accent/10 transition-colors"
      >
        Volver al inicio
      </Link>
    </div>
  );
}
