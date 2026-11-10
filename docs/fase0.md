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
| Welcome to the Jungle, Glassdoor | `keywords` | En el seed. Plantillas sacadas de URLs indexadas (`?query=`, `?sc.keyword=`) |
| Wellfound | — | La búsqueda va en la ruta como slug (`/role/r/software-engineer`), no como texto libre: no encaja en `{query}` |
| RemoteOK | `keywords` | En el seed con `?search=` (comprobado el 2026-11-09; filtra por etiquetas y descripción, resultados poco precisos). API JSON pública (`remoteok.com/api`) por la spec 6 |

**Candidatos encontrados** (búsqueda del 2026-11-08; condiciones de uso sin verificar):

| Portal | Vía automática | Notas |
|--------|----------------|-------|
| We Work Remotely | RSS por categoría | El tablero remoto más grande según varias fuentes. Plantilla confirmada: `https://weworkremotely.com/remote-jobs/search?term={query}` (`keywords`) |
| Remotive | RSS público (24 h de retraso) | Pide no republicar sus ofertas en otros portales |
| Himalayas | API pública | Exige atribución y enlace a la fuente. En el seed con `?search=` (de un ejemplo de terceros) |
| Jobicy | API pública | Filtro por región APAC y zona horaria. Plantilla probable: `https://jobicy.com/jobs?search_keywords={query}` (`keywords`) |
| Remote Rocketship | No (de pago) | Ofertas que no salen en LinkedIn; filtro por Asia |
| Jobgether | No | Ofertas remotas por región (Asia) |
| Working Nomads | Feed JSON sin documentar | Términos restrictivos: evitar la ingesta automática |
| Remote.co, NoDesk, Jobspresso, Arc.dev | Sin comprobar | Citados en listas de portales remotos (Remote.co ya está en el seed) |

**Revisión del 2026-11-09** (listas del usuario y la tabla pública de Move, *Job boards, Marketplaces & Communities*). Cada plantilla se comprobó en el navegador: búsqueda real y la URL cargada directamente filtra (título, número de resultados o buscador relleno). La URL que se guarda en la lista de origen rara vez es la de búsqueda. 43 portales entran en el seed, todos `keywords` salvo Indeed UK (`minus`). Matices:

- Por ruta: VanHack (`/jobs/{query}-jobs`) busca por habilidad: con una sola palabra funciona y con varias suele dar 0. IT Jobs, Totaljobs, CWJobs, EuroTechJobs y jobvector sí aceptan varias palabras en la ruta.
- Resultados poco precisos: Remote OK y Dynamite Jobs. Para graduados: Bright Network. De nicho: Cryptocurrency Jobs, LGBT Jobs y BME Jobs (pocas ofertas).
- Delante de Startup Jobs, ZipRecruiter, jobvector, jobtensor y Bright Network hay Cloudflare: al abrirlos desde el navegador del usuario pasa la comprobación.

No encajan en `{query}` (no se añaden):

| Portal | Motivo |
|--------|--------|
| We Are Distributed, Working Nomads, LaraJobs, web3.career, GermanTechJobs, get in IT | Solo categorías o etiquetas fijas, sin búsqueda por texto en la URL |
| Wellfound, F6S | Roles o regiones predefinidos; el texto libre da 404 o no se refleja en la URL |
| IT-Treff | Acepta `?posi=` pero apenas devuelve resultados |
| Work In Startups | CAPTCHA; plantilla probable `https://workinstartups.com/search?q={query}`, por confirmar a mano |
| Dev IT Jobs, Technojobs, Boolerang | Ya no existen (redirigen a un registro, dominio aparcado o no cargan) |
| SynergisticIT | El enlace es una página de contacto, no de ofertas |
| Otta, Honeypot, Talent.io, Cord, Hackajob, Haystack, HackerEarth | Marketplaces inversos: la empresa encuentra al candidato por su perfil (Otta es hoy Welcome to the Jungle) |

**Agencias de selección (2026-11-09)**, de la tabla Notion del usuario, con el mismo método. Entran 5, todas `keywords`: Client Server (`?term=`, 147 → 60 con "python developer"), Understanding Recruitment, Hunter Bond y 3Search (el mismo motor, `/job-search/?keyword=`) y Durlston Partners (búsqueda de WordPress `?s=`, devuelve sus ofertas; "fpga" → 2). Hunter Bond filtra poco con varias palabras (287 → 197). No entran:

| Agencia | Motivo |
|---------|--------|
| Formula Recruitment | El buscador filtra en la página sin cambiar la URL (`formularecruitment.co.uk`; `formularecruitment.com` es un dominio aparcado) |
| Oliver Bernard | Sin bolsa de ofertas en su web: enlaza a LinkedIn |
| The Tech Talent Co. | Solo su página de empleo propio (careers-page.com) |
| Ad Hoc Minds | Lista de vacantes sin búsqueda |
| Avanti Recruitment | Web oficial no localizada; sus ofertas salen en IT Jobs y otros portales del seed |

## Vías automáticas por portal

Comprobación del 2026-11-10 sobre los 55 portales del seed: una petición real al buscador y al RSS de cada uno, después un navegador y, para los que bloquean ambos, su ayuda oficial. **Las condiciones de uso de los RSS están sin verificar**: se revisan antes de integrar cada uno (`docs/fase1.md`, fila 4).

**RSS de ofertas** (descargados, con ofertas reales):

| Portal | URL | Filtra por palabra clave |
|--------|-----|--------------------------|
| Reed | `https://www.reed.co.uk/jobs/rss?keywords={query}` | Sí |
| Evenbreak | `https://www.evenbreak.com/jobsrss/?keywords={query}` | Sí |
| EuRemoteJobs | `https://euremotejobs.com/search/{query}/feed/rss2/` | Sí |
| Durlston Partners | `https://durlstonpartners.com/search/{query}/feed/rss2/` | Sí |
| Jobicy | `https://jobicy.com/?feed=job_feed&search_keywords={query}` | Sí (ya se importa por API) |
| Cryptocurrency Jobs | `https://cryptocurrencyjobs.co/index.xml` | No |
| Landing.jobs | `https://landing.jobs/feed` | No |
| We Work Remotely | `https://weworkremotely.com/remote-jobs.rss` | No, solo por categoría. Sus condiciones prohíben guardar datos (ver abajo) |
| Himalayas | `https://himalayas.app/jobs/rss` | No (ya se importa por API) |
| Remotive | `https://remotive.com/remote-jobs/feed` | No (ya se importa por API) |
| ITJobBoard.net | `https://www.itjobboard.net/rss/` | No; 10 ofertas y algunas no son de IT: poco útil |

No sirven: el RSS de Remote OK devuelve 410 (retirado; queda la API) y el de Dynamite Jobs es de su blog.

**Alertas por email**:

| Estado | Portales |
|--------|----------|
| Vistas en la página (23) | LinkedIn, Reed, Adzuna, CV-Library, Talent.com UK, Jobrapido UK, Jobijoba UK, IT Jobs, ITJobBoard.net, EuroTechJobs, EuroJobs, JobsInNetwork, Escape the City, Built In, Jobicy, Remotive, EuRemoteJobs, Dynamite Jobs, Cryptocurrency Jobs, Hunter Bond, Evenbreak, LGBT Jobs, BME Jobs |
| Confirmadas en su ayuda oficial (9) | Indeed e Indeed UK (diarias o semanales), Welcome to the Jungle, Bright Network, Remote OK (por etiqueta), Himalayas (ligadas al perfil; semanales en la cuenta gratuita), Landing.jobs (máximo cinco búsquedas guardadas), jobvector ("Jobmail"), Women in Tech Jobs |
| Sin confirmar: bloquean el acceso automático (8) | Glassdoor, Monster, CareerBuilder, Totaljobs, CWJobs, ZipRecruiter UK, FlexJobs, Remote.co |
| Ni RSS ni alertas detectadas (13) | Signify Technology, Source Group International, Client Server, Understanding Recruitment, 3Search, Hiring Cafe, Startup Jobs, jobtensor, DiverseJobsMatter, VanHack, Workwise, RemoteJobs.io, Levels.fyi (solo "Save this search") |

"No detectadas" quiere decir que no salen en la página de búsqueda ni en resultados web: podrían existir tras iniciar sesión.

## Condiciones de los feeds (spec 6)

Verificadas el 2026-11-08 en las páginas oficiales. Para uso privado de una persona; ninguno lo prohíbe.

| Feed | Condiciones | Cómo se cumplen |
|------|-------------|-----------------|
| RemoteOK (`remoteok.com/api`) | Enlazar a la oferta en RemoteOK y citarlo como fuente; sin su logo ([legal](https://www.remoteok.com/legal)) | Cada oferta guarda su enlace y su feed |
| Remotive (`remotive.com/api/remote-jobs`) | Máx. 4 consultas al día y 2 por minuto; enlazar y citar a Remotive; 24 h de retraso; no reenviar a otros portales ([README](https://github.com/remotive-com/remote-jobs-api)) | Una importación cada 6 h por feed; enlace y feed guardados |
| Himalayas (`himalayas.app/jobs/api/search`) | Citar y enlazar a Himalayas; postular solo por `applicationLink`; retirar las caducadas; no recopilar en masa; no reenviar (cláusula 113 de sus [términos](https://himalayas.app/terms), [docs](https://himalayas.app/docs/remote-jobs-api)) | Se guarda `applicationLink`; búsqueda por títulos, no el feed entero; las caducadas se descartan |
| Jobicy (`jobicy.com/api/v2/remote-jobs`) | Citar la fuente; pocas consultas al día; no reenviar ([repo](https://github.com/Jobicy/remote-jobs-api)) | Una importación cada 6 h; feed guardado |
| We Work Remotely | Fuera de la primera versión: sus condiciones de API prohíben guardar datos | Sigue como portal con búsqueda asistida |

Común a todos: la app se identifica con el User-Agent `job-offer-funnel`, sin datos personales, y nada se publica ni se reenvía.

## Fuera (con disparador)

| Fuera | Entra cuando... |
|-------|-----------------|
| Portales asiáticos: Glints, Kalibrr, Tech in Asia, Snaphunt, Dealls | La búsqueda se centre en Asia; se añaden pegando la URL de una búsqueda real (su plantilla no se puede sacar de URLs indexadas) |
| Consulta periódica de los ATS y los feeds | En plan: ver `docs/fase1.md` (workflow programado contra Render) |
| Lectura de alertas por email | En plan: ver `docs/fase1.md` |
| Scoring de encaje | La bandeja tenga más ofertas de las que se revisan |
| Seniority y salario mínimo en el perfil | La seniority va hoy en los títulos ("Senior Backend Engineer"); el salario, con la fase de salarios |
| Salarios (bandas de mercado desde webs externas) | Fase propia, revisando antes las condiciones de cada web |
| Métrica de qué portal o búsqueda llega más lejos en el funnel | Haya varias semanas de datos |
