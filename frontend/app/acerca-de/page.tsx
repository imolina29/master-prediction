import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Acerca de",
  description: "Sobre Master Prediction: análisis deportivo con inteligencia artificial.",
};

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-2xl md:text-3xl font-bold mb-6">
        Acerca de Master Prediction
      </h1>

      <div className="space-y-6 text-gray-300 leading-relaxed">
        <p>
          Master Prediction es una plataforma de análisis deportivo que utiliza
          inteligencia artificial para generar predicciones de fútbol europeo.
          Nuestro modelo de machine learning (XGBoost) ha sido entrenado con más
          de 100.000 partidos históricos de las principales ligas europeas.
        </p>

        <h2 className="text-lg font-bold text-white">Ligas Cubiertas</h2>
        <ul className="list-disc list-inside space-y-1 text-gray-400">
          <li>🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League (Inglaterra)</li>
          <li>🇪🇸 La Liga (España)</li>
          <li>🇮🇹 Serie A (Italia)</li>
          <li>🇩🇪 Bundesliga (Alemania)</li>
          <li>🇫🇷 Ligue 1 (Francia)</li>
          <li>🏆 Champions League</li>
        </ul>

        <h2 className="text-lg font-bold text-white">Qué Ofrecemos</h2>
        <ul className="list-disc list-inside space-y-1 text-gray-400">
          <li>
            Predicciones con probabilidades para cada resultado (local, empate,
            visitante)
          </li>
          <li>
            Estadísticas detalladas de equipos: goles, xG, tasas de victoria,
            ELO
          </li>
          <li>
            Niveles de confianza transparentes: alta (82% precisión), media
            (54%), baja (36%)
          </li>
          <li>
            Track record completo y verificable de todas nuestras predicciones
          </li>
          <li>Comparación estadística entre equipos para cada partido</li>
        </ul>

        <h2 className="text-lg font-bold text-white">Tecnología</h2>
        <p>
          Nuestro sistema combina múltiples fuentes de datos — resultados
          históricos, estadísticas avanzadas (xG), ratings ELO, y tendencias
          recientes — para generar predicciones fundamentadas. El modelo se
          actualiza continuamente con los últimos resultados y estadísticas.
        </p>

        <h2 className="text-lg font-bold text-white">Nuestro Enfoque</h2>
        <p>
          Master Prediction se enfoca exclusivamente en el análisis deportivo con
          inteligencia artificial. Creemos en la transparencia: todas nuestras
          predicciones pasadas están disponibles en el track record para que
          cualquiera pueda verificar nuestro rendimiento.
        </p>
      </div>
    </div>
  );
}
