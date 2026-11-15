import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Aviso Legal",
  description: "Aviso legal y descargo de responsabilidad de Master Prediction.",
};

export default function DisclaimerPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-2xl md:text-3xl font-bold mb-6">Aviso Legal</h1>

      <div className="space-y-6 text-gray-300 leading-relaxed">
        <section>
          <h2 className="text-lg font-bold text-white mb-2">
            Naturaleza Informativa
          </h2>
          <p>
            Todo el contenido proporcionado por Master Prediction tiene carácter
            exclusivamente informativo y educativo. Las predicciones,
            estadísticas y análisis presentados son generados por modelos de
            inteligencia artificial y no constituyen asesoramiento financiero,
            de inversión ni de apuestas deportivas.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-bold text-white mb-2">
            Sin Garantías
          </h2>
          <p>
            Los resultados pasados no garantizan resultados futuros. A pesar de
            que nuestro modelo ha demostrado tasas de precisión verificables en
            nuestro track record, el fútbol es inherentemente impredecible y
            ningún modelo puede garantizar predicciones correctas.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-bold text-white mb-2">
            Responsabilidad del Usuario
          </h2>
          <p>
            Las decisiones que el usuario tome basándose en la información
            proporcionada por Master Prediction son responsabilidad exclusiva
            del usuario. Master Prediction no se hace responsable de ninguna
            pérdida económica o de otro tipo derivada del uso de esta
            información.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-bold text-white mb-2">
            Independencia
          </h2>
          <p>
            Master Prediction no está afiliado, patrocinado ni asociado con
            ninguna casa de apuestas, organización deportiva, liga, equipo o
            entidad deportiva. Las marcas y nombres de equipos mencionados son
            propiedad de sus respectivos titulares.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-bold text-white mb-2">
            Uso de Datos
          </h2>
          <p>
            Los datos estadísticos utilizados provienen de fuentes públicas y
            son procesados por nuestros modelos de inteligencia artificial. No
            recopilamos datos personales de los usuarios más allá de los
            necesarios para el funcionamiento básico del servicio.
          </p>
        </section>
      </div>
    </div>
  );
}
