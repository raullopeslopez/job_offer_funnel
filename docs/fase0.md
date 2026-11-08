# Alcance de la fase 0: descubrimiento

**Pregunta que responde**: ¿qué ofertas nuevas encajan con mi perfil, en todos los portales que uso, sin repetir búsquedas a mano?

**Interfaz**: la API, como el MVP. Dominio de la fase: `docs/funnel.md` (Fase 0).

## Decisiones

- **Búsqueda asistida**: la app genera la query y la URL de cada portal; tú abres la búsqueda y das de alta en la bandeja las ofertas que te interesan. Sin scraping de portales: lo prohíben sus términos de uso (LinkedIn bloquea cuentas).
- **Portales como datos**: cada portal es un registro (nombre, plantilla de URL con `{query}`, sintaxis `boolean`, `minus` o `keywords`). Añadir un portal no requiere código. Solo la ingesta automática de un portal concreto llevaría código propio.
- **Perfil definido por el usuario** a partir de su CV (sin extracción con IA).
- **Bandeja separada del funnel**: lo descubierto no cuenta en las métricas hasta que pasa a candidatura (`evaluated`).

## Dentro

| # | Capacidad | Detalle mínimo |
|---|-----------|----------------|
| 1 | Perfiles de búsqueda | Nombre, títulos de puesto (al menos uno), palabras clave obligatorias, palabras excluidas, ubicación y modalidades (`remote`, `hybrid`, `onsite`). Varios perfiles. CRUD |
| 2 | Portales | Nombre, plantilla de URL con `{query}` (y `{location}` opcional) y sintaxis (`boolean` · `minus` · `keywords`). CRUD |
| 3 | Búsquedas generadas | Para cada perfil y portal: la query con la sintaxis del portal y la URL lista para abrir |
| 4 | Bandeja | Alta manual de ofertas (URL, empresa, puesto, portal, perfil), deduplicación por empresa + título normalizado, descartar, pasar a candidatura en `evaluated` |
| 5 | ATS de empresas | Empresas vigiladas con su ATS (Greenhouse, Lever, Ashby): consulta a demanda de sus ofertas públicas, filtradas por perfil, a la bandeja. Primera integración externa: un adaptador por ATS |
| 6 | Feeds públicos | Portales remotos con API o RSS (RemoteOK, We Work Remotely, Remotive, Himalayas, Jobicy): consulta a demanda, filtrada por perfil, a la bandeja. Mismo patrón de adaptador que los ATS; antes, verificar las condiciones de cada feed |

## Specs, en orden

1. `specs/discovery/search_profiles.feature`: alta, edición, detalle, listado y borrado de perfiles.
2. `specs/discovery/job_boards.feature`: alta, edición, detalle, listado y borrado de portales.
3. `specs/discovery/generated_searches.feature`: query y URL por perfil y portal, según la sintaxis.
4. `specs/inbox/inbox.feature`: alta manual, deduplicación, descarte y paso a candidatura.
5. `specs/inbox/ats_companies.feature`: empresas vigiladas y consulta de su ATS.
6. `specs/inbox/public_feeds.feature`: ingesta a demanda de los feeds públicos.

## Portales

Se dan de alta con la API (spec 2); la plantilla sale de copiar la URL de una búsqueda real y cambiar el texto por `{query}`. Los de plantilla comprobada están en `backend/seeds/job_boards.json` y se registran con `just seed-job-boards` (no duplica: salta los que ya existen); para añadir uno, se añade al JSON y se vuelve a ejecutar.

**Del usuario** (sintaxis prevista, a confirmar al darlos de alta):

| Portal | Sintaxis | Notas |
|--------|----------|-------|
| LinkedIn | `boolean` | Sin scraping (términos de uso) |
| Indeed | `minus` | |
| Glints, Kalibrr, Dealls, Tech in Asia, Glassdoor, Snaphunt, Welcome to the Jungle | `keywords` | Sudeste asiático la mayoría |
| Wellfound | `keywords` | Filtra más por rol que por texto: puede no admitir bien `{query}` |
| RemoteOK | `keywords` | API JSON pública (`remoteok.com/api`): candidata a ingesta automática, con atribución |

**Candidatos encontrados** (búsqueda del 2026-11-08; condiciones de uso sin verificar):

| Portal | Vía automática | Notas |
|--------|----------------|-------|
| We Work Remotely | RSS por categoría | El tablero remoto más grande según varias fuentes. Plantilla confirmada: `https://weworkremotely.com/remote-jobs/search?term={query}` (`keywords`) |
| Remotive | RSS público (24 h de retraso) | Pide no republicar sus ofertas en otros portales |
| Himalayas | API pública | Exige atribución y enlace a la fuente. Plantilla de la web sin confirmar (`?search=` o `?q=`): copiarla de una búsqueda real |
| Jobicy | API pública | Filtro por región APAC y zona horaria. Plantilla probable: `https://jobicy.com/jobs?search_keywords={query}` (`keywords`) |
| Remote Rocketship | No (de pago) | Ofertas que no salen en LinkedIn; filtro por Asia |
| Jobgether | No | Ofertas remotas por región (Asia) |
| Working Nomads | Feed JSON sin documentar | Términos restrictivos: evitar la ingesta automática |
| Remote.co, NoDesk, Jobspresso, Arc.dev | Sin comprobar | Citados en listas de portales remotos |

## Fuera (con disparador)

| Fuera | Entra cuando... |
|-------|-----------------|
| Consulta periódica de los ATS (jobs, procrastinate) | Lanzarla a mano se haga pesado |
| Lectura de alertas por email | Dar de alta ofertas a mano sea el cuello de botella |
| Scoring de encaje | La bandeja tenga más ofertas de las que se revisan |
| Seniority y salario mínimo en el perfil | La seniority va hoy en los títulos ("Senior Backend Engineer"); el salario, con la fase de salarios |
| Salarios (bandas de mercado desde webs externas) | Fase propia, revisando antes las condiciones de cada web |
| Métrica de qué portal o búsqueda llega más lejos en el funnel | Haya varias semanas de datos |
