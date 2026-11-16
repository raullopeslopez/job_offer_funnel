# Pendientes

Lo que quedó abierto al cerrar un PR y no está en ninguna spec ni issue. Cada punto dice qué falta para decidirlo. Se borra cuando se hace o se descarta.

## Ofertas «repetidas» en la Bandeja (análisis del 2026-11-15)

**Qué se vio**: la Bandeja parece tener ofertas repetidas. Agrupando producción por empresa + arranque del título salieron 50 grupos, todos de las empresas vigiladas (ElevenLabs, Camunda, Alan) y de Jobicy.

**Conclusión**: no son duplicados. Son vacantes distintas que la empresa publica una por país («Technical Account Manager - Spain / Benelux / Israel») o una por equipo («Full-Stack Engineer - ElevenAPI / Ads Engine»). La deduplicación (empresa + título, o URL) hace lo que dice `specs/inbox/inbox.feature` y **no se endurece**: fundir esas filas perdería vacantes reales y rompería «nada se pierde». De los 50 grupos solo uno era la misma oferta dos veces.

**Hecho**: las entidades HTML de los feeds («&#038;» por «&»), en el PR #139, con migración para las ofertas ya importadas.

**Comprobado después con producción (2026-11-15)**: la regla de ubicación funciona. De las ofertas de las empresas vigiladas solo 33 encajan por título y están leídas; el lector acertó en 32: filtró las variantes de otro país (Argentina, México, USA, North Africa) y admitió las remotas. No hay cola del lector. Lo que se ve repetido son unas 21 variantes por equipo de cuatro empresas (ElevenLabs «Full-Stack Engineer» ×9, Alan «Fullstack Software Engineer» ×6, Camunda «Software Engineer, Backend» ×3), todas vacantes distintas y bien admitidas: es un problema de presentación.

**Hecho**: agrupar las variantes en la Bandeja, en el PR #141.

**En curso**: los puntos 1 y 2, juntos (sección «Offers imported before this feature» de `specs/inbox/offer_countries.feature` y la relectura en `specs/inbox/offer_readings.feature`). Decidido: la oferta pendiente que recibe ubicación se vuelve a leer; la que ya no está pendiente conserva sus lecturas.

**Abierto**, por orden recomendado:

1. **Ubicación vacía en las ofertas antiguas.** Las importadas antes del 2026-11-14 no tienen `location`, y al reimportar se saltan por duplicadas, así que nunca la reciben: no muestran país y el lector las lee sin la ubicación publicada. Arreglo pequeño: al importar una oferta que ya existe y no tiene ubicación, guardarle la que publica la fuente. Con su escenario.
2. **Ubicaciones secundarias de Ashby.** La app guarda solo la principal: «Full-Stack Engineer» de ElevenLabs llega como `United Kingdom` aunque el tablón lista también Spain, Dublin y más (81 de sus 128 ofertas tienen secundarias). El lector entiende que un remoto cuya ubicación nombra un sitio solo se hace viviendo allí, así que puede filtrar por error una oferta buena. Hoy no ha afectado a ninguna (las antiguas no tienen ubicación); pasará al arreglar el punto 1, así que van juntos.
3. **«Anywhere in France» se muestra como «Worldwide».** `Anywhere in France, Belgium, Spain` (Alan) sale con las etiquetas Worldwide, France, Belgium y Spain. «Anywhere» solo debería ser Worldwide cuando no le sigue «in {lugar}».
4. **Camunda admite cualquier ubicación por su frase genérica.** «Senior Forward Deployed Engineer - Canada» se admitió por «Fully remote and global», que Camunda pone en todas sus ofertas. Un solo caso: se descarta a mano. Disparador para tocar el prompt del lector: el tercero.
5. **Empresas y candidaturas con «&#038;».** La migración del PR #139 solo corrige ofertas. Si se promovió alguna con la entidad, el nombre de la empresa y el puesto de la candidatura siguen mal. Falta: contarlas (`SELECT name FROM companies WHERE name LIKE '%&#%' OR name LIKE '%&amp;%'`, y lo mismo sobre el puesto de las candidaturas). Si son pocas, se editan a mano en la app.
6. **Copias tras la migración.** Si una oferta con «&amp;» quedó igual que otra que ya existía con «&», las dos siguen en la Bandeja con el mismo texto. Se descarta una a mano; no hay nada que programar.
7. **El mismo puesto en dos fuentes con un sufijo** (Askable «Software Engineer, AI Coding Tasks» y la misma con «(Contract)», en Himalayas y Remotive). Un solo caso: no se toca. Disparador: el tercero (regla de tres), y entonces se mira qué sufijos se repiten antes de normalizar nada.
8. **Que el país publicado filtre sin IA.** Descartado por ahora: el lector ya filtra bien las variantes de otro país. Disparador: que el lector deje de estar disponible o empiece a fallar en ellas.
