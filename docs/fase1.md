# Alcance de la fase 1: ofertas que llegan solas y CVs por oferta

**Pregunta que responde**: ¿qué ofertas nuevas de varios portales encajan conmigo, sin lanzar nada a mano, y con qué CV me presento a cada una?

**Interfaz**: la app web (local con `just up` y en Render). Dominio: `docs/funnel.md` (fases 0 y 1).

## Decisiones

- **Importar amplio, filtrar en la app**: la importación guarda todas las ofertas que devuelve cada fuente (sin duplicados) y el encaje con los perfiles se calcula en la app. Las que no encajan quedan como filtradas, visibles en su propia pestaña, y se recalculan al editar un perfil. Así una query mal puesta oculta ofertas, pero no las pierde. Donde las condiciones de una fuente prohíben descargar el feed entero (Himalayas), se le sigue pidiendo por títulos.
- **Importación periódica fuera de la app**: un workflow programado de GitHub Actions llama a la API de Render cada 6 h. Ni el planificador dentro de la API (el plan free de Render la duerme) ni un Cron Job de Render (de pago).
- **El portal es el único catálogo de fuentes**: cada portal (`job_boards`) declara cómo se importa: `none` (búsqueda asistida), `rss` (la fila guarda la plantilla de la URL del RSS y la lee un parser genérico), `api` (adaptador en código, como los cuatro feeds actuales) o `email` (un parser por remitente sobre las alertas de un buzón). Toda oferta de un portal lleva su `job_board_id`, llegue a mano o importada, y desaparece la columna `feed` de las ofertas. Así ningún portal existe dos veces (hoy RemoteOK, Remotive, Himalayas y Jobicy son portal y feed sin vínculo), el origen deja de deducirse de tres columnas opcionales y añadir un portal con RSS no requiere código. Los ATS no cambian: su fuente es la empresa vigilada, no un portal.
- **Fuentes nuevas por RSS o por alertas por email, antes que por API con clave**. Sin scraping de portales (términos de uso). La comprobación del 2026-11-10 (`docs/fase0.md`, "Vías automáticas por portal") encontró 6 portales nuevos con RSS de ofertas y 32 con alertas por email. Antes de integrar cada fuente se verifican sus condiciones y se anotan en `docs/fase0.md`.
- **Alertas por email en un buzón dedicado**: una cuenta de correo solo para alertas, que lee el mismo workflow de cada 6 h, para no dar acceso al correo personal. Las alertas se crean a mano en cada portal. Cómo se lee el buzón se decide en la spec.
- **Segundo filtro, por el cuerpo de la oferta** (2026-11-12): el título no dice si un puesto es remoto de verdad ni desde dónde se puede hacer. Un lector externo (un modelo de lenguaje en Groq, plan gratuito) lee la descripción de las ofertas que ya encajan por sus palabras y saca tres hechos: modalidad, si se puede hacer viviendo en la ubicación del perfil y si es un puesto estable. Cada respuesta va con la frase literal de la descripción que la justifica; sin ella se descarta, así el modelo no puede inventar. El modelo extrae hechos y la app decide el encaje: editar un perfil recalcula sin volver a leer. Solo filtra lo que el texto dice expresamente; lo que no dice, o no se ha leído, se queda. Sin `GROQ_API_KEY` no se lee nada y la app funciona igual. Límites comprobados en la documentación de Groq ese día para `openai/gpt-oss-20b`: 30 peticiones y 8.000 tokens por minuto, 1.000 peticiones y 200.000 tokens al día; de ahí el lote de 5 y la pausa de un minuto del script. Una auditoría previa en producción midió que el filtro por título solo fallaba en un 1,9 % de las filtradas, y que el ruido venía de modalidad y ubicación.
- **CV maestro rellenado en la app, sin importar el PDF**: hay un solo usuario y un solo CV, y lo rellena una vez. La importación (con pdf_oxide: MIT/Apache, extrae Markdown con títulos de sección) queda aplazada.
- **CVs por oferta sin IA**: la app compara las palabras clave de la oferta con el CV maestro, preselecciona y ordena los logros que encajan, y el usuario retoca el texto. Nunca añade nada que no esté en el CV maestro.
- **Formato Harvard con una plantilla fija**: una columna, orden cronológico inverso, secciones fijas y sin tablas, iconos ni columnas, para que lo lean bien los ATS. Salida en PDF y en DOCX. El contenido varía según la oferta; el formato, nunca.
- **Cada CV generado es una versión** ligada a su candidatura, para medir la tasa de respuesta por versión (`docs/funnel.md`, fase 1).

## Plan, en orden (un PR por fila)

| # | PR | Para qué |
|---|----|----------|
| 0 | Poblar producción (sin PR): seed de portales contra Render, perfiles y empresas vigiladas | Sin perfiles no hay nada que importar |
| 1 | Importación amplia: guardar todo lo importado, encaje calculado en la app, pestaña de filtradas (hecho) | Que una mala query no haga perder ofertas |
| 2 | Importación periódica: script + workflow de GitHub Actions cada 6 h contra Render (hecho; un feed o tablero caído se salta y se reintenta en la siguiente ejecución, no falla el workflow) | Que la Bandeja se llene sola |
| 3 | Método de importación en el portal y origen único de la oferta: `job_boards` gana el método, las ofertas importadas llevan `job_board_id`, se retira `feed` de las ofertas. Migración reversible que conserva el origen de las ya importadas (hecho; por ahora con los métodos `none` y `api`: `rss` y `email` entran con las filas 4 y 5) | Base de las filas 4 y 5; quita los portales duplicados y la búsqueda manual en los que ya se importan solos |
| 4 | Importación por RSS: método `rss` con la plantilla de la URL del RSS en el portal, leída por cada título de los perfiles. Solo Evenbreak: de los seis RSS, Landing.jobs y Cryptocurrency Jobs lo prohíben en sus condiciones y Reed, EuRemoteJobs y Durlston no traen la empresa (`docs/fase0.md`) (hecho) | Un portal más sin claves, y el método listo para el siguiente RSS |
| 5 | Alertas por email: método `email` con `email_alert` en el portal y el buzón dedicado leído por IMAP cada 6 h. Solo LinkedIn (hecho): Indeed solo manda recomendaciones, no alertas de búsqueda; entra cuando haya una alerta suya y muestras de su formato. Después, el resto de portales con alertas | El volumen: los portales grandes, que no tienen API ni RSS para candidatos |
| 6 | CV maestro: contacto, experiencias con logros, educación y habilidades | La única fuente de verdad de los CVs |
| 7 | CV para una oferta: encaje de palabras clave y selección de logros | Adaptar el CV sin reescribirlo desde cero |
| 8 | Plantilla Harvard en PDF y DOCX, con versión ligada a la candidatura | El documento que se envía, y medir qué versión convierte |

Las filas 1 a 5 son de ofertas y van antes que las de CVs (6 a 8). Cada fila sigue el ciclo SDD (spec → contrato → rojo → verde).

## Fuera (con disparador)

| Fuera | Entra cuando... |
|-------|-----------------|
| Fuente Adzuna por API oficial | Sus alertas por email (fila 5) se queden cortas; exige clave |
| Fuente Reed por API oficial | Sus alertas por email (fila 5) se queden cortas; su RSS no trae la empresa (fila 4); exige clave |
| Empresa del RSS por otra convención (`<author>`, `Título at Empresa`) | Aparezca un RSS permitido que la traiga así; hoy solo Evenbreak (`Empresa: Título`) |
| Importar el CV desde PDF o DOCX (pdf_oxide) | Mantener el CV maestro a mano se haga pesado |
| Reescritura del CV con IA (API de Claude) | Retocar a mano los CVs por oferta se haga pesado; implica coste por uso y enviar datos del CV a un tercero |
| Puntuación de encaje en lugar de filtro | La Bandeja tenga más ofertas de las que se revisan |
| Salario mínimo en el perfil y salario publicado en la lectura | Las ofertas leídas que no interesan lo sean sobre todo por sueldo; exige convertir monedas |
| Leer las ofertas de las alertas por email | Haya de dónde sacar su descripción sin scraping; hoy llegan sin ella y nunca se leen |
| Mostrar la lectura en la Bandeja | Se quiera ver por qué se filtró una oferta sin ir a la API; es una pantalla (`specs/ui/`) |
