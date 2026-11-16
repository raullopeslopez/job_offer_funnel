# Pendientes

Lo que quedó abierto al cerrar un PR y no está en ninguna spec ni issue. Cada punto dice qué falta para decidirlo. Se borra cuando se hace o se descarta.

## Ofertas «repetidas» en la Bandeja (análisis del 2026-11-15)

**Qué se vio**: la Bandeja parece tener ofertas repetidas. Agrupando producción por empresa + arranque del título salieron 50 grupos, todos de las empresas vigiladas (ElevenLabs, Camunda, Alan) y de Jobicy.

**Conclusión**: no son duplicados. Son vacantes distintas que la empresa publica una por país («Technical Account Manager - Spain / Benelux / Israel») o una por equipo («Full-Stack Engineer - ElevenAPI / Ads Engine»). La deduplicación (empresa + título, o URL) hace lo que dice `specs/inbox/inbox.feature` y **no se endurece**: fundir esas filas perdería vacantes reales y rompería «nada se pierde». De los 50 grupos solo uno era la misma oferta dos veces.

**Hecho**: las entidades HTML de los feeds («&#038;» por «&»), en el PR #139, con migración para las ofertas ya importadas.

**Comprobado después con producción (2026-11-15)**: la regla de ubicación funciona. De las ofertas de las empresas vigiladas solo 33 encajan por título y están leídas; el lector acertó en 32: filtró las variantes de otro país (Argentina, México, USA, North Africa) y admitió las remotas. No hay cola del lector. Lo que se ve repetido son unas 21 variantes por equipo de cuatro empresas (ElevenLabs «Full-Stack Engineer» ×9, Alan «Fullstack Software Engineer» ×6, Camunda «Software Engineer, Backend» ×3), todas vacantes distintas y bien admitidas: es un problema de presentación.

**Hecho**: agrupar las variantes en la Bandeja, en el PR #141.

**Hecho**: los antiguos puntos 1 y 2 (ubicación vacía en las ofertas antiguas y ubicaciones secundarias de Ashby), en este PR: la oferta pendiente que recibe ubicación se vuelve a leer; la que ya no está pendiente conserva sus lecturas. Las antiguas solo la reciben cuando su fuente la vuelve a publicar: las que ya no se publican se quedan sin ella.

**Abierto**, por orden recomendado:

1. **«Anywhere in France» se muestra como «Worldwide».** `Anywhere in France, Belgium, Spain` (Alan) sale con las etiquetas Worldwide, France, Belgium y Spain. «Anywhere» solo debería ser Worldwide cuando no le sigue «in {lugar}».
2. **Camunda admite cualquier ubicación por su frase genérica.** «Senior Forward Deployed Engineer - Canada» se admitió por «Fully remote and global», que Camunda pone en todas sus ofertas. Un solo caso: se descarta a mano. Disparador para tocar el prompt del lector: el tercero.
3. **Empresas y candidaturas con «&#038;».** La migración del PR #139 solo corrige ofertas. Si se promovió alguna con la entidad, el nombre de la empresa y el puesto de la candidatura siguen mal. Falta: contarlas (`SELECT name FROM companies WHERE name LIKE '%&#%' OR name LIKE '%&amp;%'`, y lo mismo sobre el puesto de las candidaturas). Si son pocas, se editan a mano en la app.
4. **Copias tras la migración.** Si una oferta con «&amp;» quedó igual que otra que ya existía con «&», las dos siguen en la Bandeja con el mismo texto. Se descarta una a mano; no hay nada que programar.
5. **El mismo puesto en dos fuentes con un sufijo** (Askable «Software Engineer, AI Coding Tasks» y la misma con «(Contract)», en Himalayas y Remotive). Un solo caso: no se toca. Disparador: el tercero (regla de tres), y entonces se mira qué sufijos se repiten antes de normalizar nada.
6. **Que el país publicado filtre sin IA.** Descartado por ahora: el lector ya filtra bien las variantes de otro país. Disparador: que el lector deje de estar disponible o empiece a fallar en ellas.
