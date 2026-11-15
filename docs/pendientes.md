# Pendientes

Lo que quedó abierto al cerrar un PR y no está en ninguna spec ni issue. Cada punto dice qué falta para decidirlo. Se borra cuando se hace o se descarta.

## Ofertas «repetidas» en la Bandeja (análisis del 2026-11-15)

**Qué se vio**: la Bandeja parece tener ofertas repetidas. Agrupando producción por empresa + arranque del título salieron 50 grupos, todos de las empresas vigiladas (ElevenLabs, Camunda, Alan) y de Jobicy.

**Conclusión**: no son duplicados. Son vacantes distintas que la empresa publica una por país («Technical Account Manager - Spain / Benelux / Israel») o una por equipo («Full-Stack Engineer - ElevenAPI / Ads Engine»). La deduplicación (empresa + título, o URL) hace lo que dice `specs/inbox/inbox.feature` y **no se endurece**: fundir esas filas perdería vacantes reales y rompería «nada se pierde». De los 50 grupos solo uno era la misma oferta dos veces.

**Hecho**: las entidades HTML de los feeds («&#038;» por «&»), en el PR #139, con migración para las ofertas ya importadas.

**Abierto**, por orden recomendado:

1. **Variantes por país que llegan a Pending.** Si la de Israel o la de Canadá aparecen en Pending, la regla de ubicación del perfil no las filtra y eso es un fallo del filtro, no de presentación. Falta: dos o tres ejemplos reales (título, empresa, ubicación publicada, perfil). Va antes que el punto 2 porque puede dejarlo sin sentido.
2. **Agrupar variantes en la Bandeja** por empresa + título base («ElevenLabs · Full-Stack Engineer · 10 variantes», con las filas dentro). Es presentación: no cambia qué se guarda ni qué se filtra. Pieza nueva con su spec. Disparador: que tras resolver el punto 1 sigan quedando en Pending grupos de 3 o más variantes de forma habitual.
3. **Empresas y candidaturas con «&#038;».** La migración del PR #139 solo corrige ofertas. Si se promovió alguna con la entidad, el nombre de la empresa y el puesto de la candidatura siguen mal. Falta: contarlas (`SELECT name FROM companies WHERE name LIKE '%&#%' OR name LIKE '%&amp;%'`, y lo mismo sobre el puesto de las candidaturas). Si son pocas, se editan a mano en la app.
4. **Copias tras la migración.** Si una oferta con «&amp;» quedó igual que otra que ya existía con «&», las dos siguen en la Bandeja con el mismo texto. Se descarta una a mano; no hay nada que programar.
5. **El mismo puesto en dos fuentes con un sufijo** (Askable «Software Engineer, AI Coding Tasks» y la misma con «(Contract)», en Himalayas y Remotive). Un solo caso: no se toca. Disparador: el tercero (regla de tres), y entonces se mira qué sufijos se repiten antes de normalizar nada.
