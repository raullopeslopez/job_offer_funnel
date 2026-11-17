# Pendientes

Lo que quedó abierto al cerrar un PR y no está en ninguna spec ni issue. Cada punto dice qué falta para decidirlo. Se borra cuando se hace o se descarta.

## Ofertas «repetidas» en la Bandeja (análisis del 2026-11-15)

**Qué se vio**: la Bandeja parece tener ofertas repetidas. Agrupando producción por empresa + arranque del título salieron 50 grupos, todos de las empresas vigiladas (ElevenLabs, Camunda, Alan) y de Jobicy.

**Conclusión**: no son duplicados. Son vacantes distintas que la empresa publica una por país («Technical Account Manager - Spain / Benelux / Israel») o una por equipo («Full-Stack Engineer - ElevenAPI / Ads Engine»). La deduplicación (empresa + título, o URL) hace lo que dice `specs/inbox/inbox.feature` y **no se endurece**: fundir esas filas perdería vacantes reales y rompería «nada se pierde». De los 50 grupos solo uno era la misma oferta dos veces.

**Hecho**: las entidades HTML de los feeds («&#038;» por «&»), en el PR #139, con migración para las ofertas ya importadas.

**Comprobado después con producción (2026-11-15)**: la regla de ubicación funciona. De las ofertas de las empresas vigiladas solo 33 encajan por título y están leídas; el lector acertó en 32: filtró las variantes de otro país (Argentina, México, USA, North Africa) y admitió las remotas. No hay cola del lector. Lo que se ve repetido son unas 21 variantes por equipo de cuatro empresas (ElevenLabs «Full-Stack Engineer» ×9, Alan «Fullstack Software Engineer» ×6, Camunda «Software Engineer, Backend» ×3), todas vacantes distintas y bien admitidas: es un problema de presentación.

**Hecho**: agrupar las variantes en la Bandeja, en el PR #141.

**Hecho**: los antiguos puntos 1 y 2 (ubicación vacía en las ofertas antiguas y ubicaciones secundarias de Ashby), en este PR: la oferta pendiente que recibe ubicación se vuelve a leer; la que ya no está pendiente conserva sus lecturas. Las antiguas solo la reciben cuando su fuente la vuelve a publicar: las que ya no se publican se quedan sin ella.

**Hecho** (2026-11-16): los antiguos puntos 1 y 6. «Anywhere in France, Belgium, Spain» ya no sale como Worldwide, y la ubicación publicada filtra sin IA cuando solo nombra países conocidos y ninguno es el del perfil («USA», «Canada, USA»). El disparador del punto 6 se cumplió: el lector no daba abasto (Jobicy tenía 424 ofertas pendientes con país publicado y ninguna leída).

**Abierto**, por orden recomendado:

1. **Camunda admite cualquier ubicación por su frase genérica.** «Senior Forward Deployed Engineer - Canada» se admitió por «Fully remote and global», que Camunda pone en todas sus ofertas. Un solo caso: se descarta a mano. Disparador para tocar el prompt del lector: el tercero.
2. **Empresas y candidaturas con «&#038;».** La migración del PR #139 solo corrige ofertas. Si se promovió alguna con la entidad, el nombre de la empresa y el puesto de la candidatura siguen mal. Falta: contarlas (`SELECT name FROM companies WHERE name LIKE '%&#%' OR name LIKE '%&amp;%'`, y lo mismo sobre el puesto de las candidaturas). Si son pocas, se editan a mano en la app.
3. **Copias tras la migración.** Si una oferta con «&amp;» quedó igual que otra que ya existía con «&», las dos siguen en la Bandeja con el mismo texto. Se descarta una a mano; no hay nada que programar.
4. **El mismo puesto en dos fuentes con un sufijo** (Askable «Software Engineer, AI Coding Tasks» y la misma con «(Contract)», en Himalayas y Remotive). Un solo caso: no se toca. Disparador: el tercero (regla de tres), y entonces se mira qué sufijos se repiten antes de normalizar nada.
5. **Cobertura del lector**: hecho el lector con Claude Code en local (`OFFER_READER=claude-code`, 20 por petición; `just dev-prod` + `just read-prod`). Falta: vaciar la cola de prod con él y comparar sus lecturas con las de Groq (sobre todo modalidad y ubicación). Ligado al issue #135, que sigue abierto para medir la cola de Groq en Render.
6. **Ubicaciones con texto además de países** («Remote - UK», «EMEA, UK», «Trinidad and Tobago») no filtran por la regla nueva: las decide el lector. Disparador para ampliar la regla: que se vean en Pending tres o más que debían haber caído.

## Triaje con Claude Code en el uso diario (pregunta del 2026-11-15)

**Abierto**: ¿cómo se traslada el triaje con Claude Code (solo en local, `just dev-prod`) al uso diario, para que los veredictos y las sugerencias de criterio alimenten el ciclo de mejora sin pasos de más? Falta: decidir cómo se lanza y dónde quedan sus resultados.
