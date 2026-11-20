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

## Rendimiento de la Bandeja (revisión del 2026-11-20)

Medido en local con datos sintéticos (3 perfiles, descripciones de ~3 KB, 60 % pendientes), no con producción.

**Hecho**: el JIT de Postgres desactivado en las conexiones de la API (PR #147). Compilaba en cada lectura ~2 s de una consulta que tarda ~0,1 s.

**Hecho**: los casi de la vista Filtered en una sola respuesta (`GET /offers/near-misses`). Cada carga y cada clic recalculaban los motivos de filtrado de todas las pendientes 7 veces; ahora 2 (la lista y los grupos). Con 20.000 ofertas sintéticas, la vista pasó de ~13 s a ~6,5 s. Los ids de los casi van a SQL como un solo array: sin el tope de 32.767 parámetros de asyncpg.

**Lo que queda en esa vista** (~6,5 s con 20.000): la lista y los grupos (~2 s cada uno, casi todo el cálculo del motivo en Python, que bloquea el único worker), `frequent-titles` y los recuentos de las pestañas, que se sirven uno detrás de otro por la CPU. Son los puntos 4, 5 y 7 de abajo.

**Abierto**, por orden recomendado:

1. **Región de la BD.** Cada petición de la Bandeja lanza de 4 a 6 consultas seguidas: la BD debe estar en la misma región que la API. Falta: comprobarlo en el host de `DATABASE_URL`, y elegir la misma región si cambia el proveedor.
2. **Conexiones cortadas tras una pausa.** El engine no usa `pool_pre_ping`; si la BD suspende la base o corta las conexiones inactivas, la primera petición tras una pausa puede dar 500. Disparador: ver un «connection closed» en los logs de Render. Arreglo: `pool_pre_ping=True` en el engine.
3. **Pooler de conexiones.** `jit=off` va como parámetro de arranque; un pooler en modo transacción (PgBouncer) puede rechazarlo, y asyncpg necesitaría `statement_cache_size=0`. Disparador: pasar a una URL con pooler. Entonces, `SET LOCAL jit = off` por transacción.
4. **Recuentos de las pestañas.** Piden `limit=1` a la lista completa, con sus funciones de ventana y el motivo de filtrado de esa fila. Disparador: que un recuento pase de ~0,5 s en producción.
5. **Vistas previas en bucle.** `frequent-titles` y `suggestions` hacen una vista previa (dos recorridos de todas las importadas) por cada candidato. Disparador: que alguna de las dos pase de ~2 s en producción.
6. **Crecimiento sin límite.** Las alertas por email y los feeds de solo lo último nunca caducan ofertas, así que Pending crece y con él todo lo que recalcula el filtro. Falta: decidir si caducan por antigüedad (cambio de spec).
7. **Guardar el motivo de filtrado** en vez de recalcularlo en cada lectura. Choca con «recalculadas al instante»: solo si, hecho lo anterior, la vista Filtered sigue por encima de ~2 s en producción.
