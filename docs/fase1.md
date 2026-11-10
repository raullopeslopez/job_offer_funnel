# Alcance de la fase 1: ofertas que llegan solas y CVs por oferta

**Pregunta que responde**: ¿qué ofertas nuevas de varios portales encajan conmigo, sin lanzar nada a mano, y con qué CV me presento a cada una?

**Interfaz**: la app web (local con `just up` y en Render). Dominio: `docs/funnel.md` (fases 0 y 1).

## Decisiones

- **Importar amplio, filtrar en la app**: la importación guarda todas las ofertas que devuelve cada fuente (sin duplicados) y el encaje con los perfiles se calcula en la app. Las que no encajan quedan como filtradas, visibles en su propia pestaña, y se recalculan al editar un perfil. Así una query mal puesta oculta ofertas, pero no las pierde. Donde las condiciones de una fuente prohíben descargar el feed entero (Himalayas), se le sigue pidiendo por títulos.
- **Importación periódica fuera de la app**: un workflow programado de GitHub Actions llama a la API de Render cada 6 h. Ni el planificador dentro de la API (el plan free de Render la duerme) ni un Cron Job de Render (de pago).
- **Fuentes nuevas solo por API oficial** o por alertas por email. Sin scraping de portales (términos de uso). Antes de integrar cada fuente se verifican sus condiciones y se anotan en `docs/fase0.md`.
- **CV maestro rellenado en la app, sin importar el PDF**: hay un solo usuario y un solo CV, y lo rellena una vez. La importación (con pdf_oxide: MIT/Apache, extrae Markdown con títulos de sección) queda aplazada.
- **CVs por oferta sin IA**: la app compara las palabras clave de la oferta con el CV maestro, preselecciona y ordena los logros que encajan, y el usuario retoca el texto. Nunca añade nada que no esté en el CV maestro.
- **Formato Harvard con una plantilla fija**: una columna, orden cronológico inverso, secciones fijas y sin tablas, iconos ni columnas, para que lo lean bien los ATS. Salida en PDF y en DOCX. El contenido varía según la oferta; el formato, nunca.
- **Cada CV generado es una versión** ligada a su candidatura, para medir la tasa de respuesta por versión (`docs/funnel.md`, fase 1).

## Plan, en orden (un PR por fila)

| # | PR | Para qué |
|---|----|----------|
| 0 | Poblar producción (sin PR): seed de portales contra Render, perfiles y empresas vigiladas | Sin perfiles no hay nada que importar |
| 1 | Importación amplia: guardar todo lo importado, encaje calculado en la app, pestaña de filtradas | Que una mala query no haga perder ofertas |
| 2 | Importación periódica: script + workflow de GitHub Actions cada 6 h contra Render | Que la Bandeja se llene sola |
| 3 | Fuente Adzuna (API oficial) | Volumen: agrega muchos portales de Reino Unido y Europa |
| 4 | Fuente Reed (API oficial) | Volumen en Reino Unido |
| 5 | Alertas por email de LinkedIn e Indeed | Los dos portales grandes, que no tienen API para candidatos |
| 6 | CV maestro: contacto, experiencias con logros, educación y habilidades | La única fuente de verdad de los CVs |
| 7 | CV para una oferta: encaje de palabras clave y selección de logros | Adaptar el CV sin reescribirlo desde cero |
| 8 | Plantilla Harvard en PDF y DOCX, con versión ligada a la candidatura | El documento que se envía, y medir qué versión convierte |

Las filas 1 a 5 son de ofertas y van antes que las de CVs (6 a 8). Cada fila sigue el ciclo SDD (spec → contrato → rojo → verde).

## Fuera (con disparador)

| Fuera | Entra cuando... |
|-------|-----------------|
| Importar el CV desde PDF o DOCX (pdf_oxide) | Mantener el CV maestro a mano se haga pesado |
| Reescritura del CV con IA (API de Claude) | Retocar a mano los CVs por oferta se haga pesado; implica coste por uso y enviar datos del CV a un tercero |
| Puntuación de encaje en lugar de filtro | La Bandeja tenga más ofertas de las que se revisan |
| Filtro por ubicación y modalidad en el encaje | Lleguen ofertas que no sirven solo por ubicación o modalidad |
