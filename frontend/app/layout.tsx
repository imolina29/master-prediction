import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import Script from "next/script";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

const SITE_URL = process.env.SITE_URL || "https://masterprediction.up.railway.app";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Master Prediction — Predicciones de Fútbol con IA",
    template: "%s | Master Prediction",
  },
  description:
    "Predicciones de fútbol europeo basadas en inteligencia artificial y análisis estadístico avanzado. Cobertura de Premier League, La Liga, Serie A, Bundesliga, Ligue 1 y Champions League.",
  keywords: [
    "predicciones fútbol",
    "pronósticos fútbol",
    "inteligencia artificial fútbol",
    "predicciones La Liga",
    "predicciones Premier League",
    "predicciones Champions League",
    "análisis estadístico fútbol",
    "Master Prediction",
  ],
  robots: "index, follow",
  alternates: {
    canonical: SITE_URL,
  },
  openGraph: {
    type: "website",
    locale: "es_ES",
    url: SITE_URL,
    siteName: "Master Prediction",
    title: "Master Prediction — Predicciones de Fútbol con IA",
    description:
      "Análisis estadístico avanzado con IA para las principales ligas europeas. 80%+ precisión en alta confianza.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Master Prediction — Predicciones de Fútbol con IA",
    description:
      "Predicciones de fútbol europeo con inteligencia artificial. 80%+ precisión en alta confianza.",
  },
};

const GA_ID = process.env.NEXT_PUBLIC_GA_ID;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" className={inter.className}>
      <body className="min-h-screen flex flex-col bg-bg text-white">
        {GA_ID && (
          <>
            <Script
              src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`}
              strategy="afterInteractive"
            />
            <Script id="ga4" strategy="afterInteractive">
              {`window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','${GA_ID}');`}
            </Script>
          </>
        )}

        <header className="sticky top-0 z-50 border-b border-edge bg-bg/95 backdrop-blur">
          <nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
            <Link href="/" className="text-xl font-bold text-accent">
              MP
            </Link>
            <div className="flex items-center gap-6 text-sm">
              <Link
                href="/liga/premier-league"
                className="text-gray-300 hover:text-white transition-colors"
              >
                Ligas
              </Link>
              <Link
                href="/track-record"
                className="text-gray-300 hover:text-white transition-colors"
              >
                Track Record
              </Link>
              <Link
                href="/acerca-de"
                className="text-gray-300 hover:text-white transition-colors"
              >
                Acerca de
              </Link>
            </div>
          </nav>
        </header>

        <main className="flex-1">{children}</main>

        <footer className="border-t border-edge py-8 mt-12">
          <div className="mx-auto max-w-6xl px-4 text-center text-xs text-gray-500">
            <p className="mb-2">
              Análisis informativo. Las decisiones de apuesta son
              responsabilidad exclusiva del usuario.{" "}
              <a href="/aviso-legal" className="underline hover:text-gray-300">
                Aviso Legal
              </a>
            </p>
            <p>© {new Date().getFullYear()} Master Prediction</p>
            <div id="ad-slot-footer" />
          </div>
        </footer>
      </body>
    </html>
  );
}
