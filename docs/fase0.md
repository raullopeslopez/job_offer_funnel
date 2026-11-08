# Alcance de la fase 0: descubrimiento

**Pregunta que responde**: ¿qué ofertas nuevas encajan con mi perfil, en todos los portales que uso, sin repetir búsquedas a mano?

**Interfaz**: la API, como el MVP. Dominio de la fase: `docs/funnel.md` (Fase 0).

## Decisiones

- **Búsqueda asistida**: la app genera la query y la URL de cada portal; tú abres la búsqueda y das de alta en la bandeja las ofertas que te interesan. Sin scraping de portales: lo prohíben sus términos de uso (LinkedIn bloquea cuentas).
- **Portales como datos**: cada portal es un registro (nombre, plantilla de URL con `{query}`, sintaxis `boolean` o `keywords`). Añadir un portal no requiere código. Solo la ingesta automática de un portal concreto llevaría código propio.
- **Perfil definido por el usuario** a partir de su CV (sin extracción con IA).
- **Bandeja separada del funnel**: lo descubierto no cuenta en las métricas hasta que pasa a candidatura (`evaluated`).

## Dentro

| # | Capacidad | Detalle mínimo |
|---|-----------|----------------|
| 1 | Perfiles de búsqueda | Nombre, títulos de puesto (al menos uno), palabras clave obligatorias, palabras excluidas, ubicación y modalidades (`remote`, `hybrid`, `onsite`). Varios perfiles. CRUD |
| 2 | Portales | Nombre, plantilla de URL con `{query}` (y `{location}` opcional) y sintaxis (`boolean` · `keywords`). CRUD |
| 3 | Búsquedas generadas | Para cada perfil y portal: la query con la sintaxis del portal y la URL lista para abrir |
| 4 | Bandeja | Alta manual de ofertas (URL, empresa, puesto, portal, perfil), deduplicación por empresa + título normalizado, descartar, pasar a candidatura en `evaluated` |
| 5 | ATS de empresas | Empresas vigiladas con su ATS (Greenhouse, Lever, Ashby): consulta a demanda de sus ofertas públicas, filtradas por perfil, a la bandeja. Primera integración externa: un adaptador por ATS |

## Specs, en orden

1. `specs/discovery/search_profiles.feature`: alta, edición, detalle, listado y borrado de perfiles.
2. `specs/discovery/job_boards.feature`: alta, edición, detalle, listado y borrado de portales.
3. `specs/discovery/generated_searches.feature`: query y URL por perfil y portal, según la sintaxis.
4. `specs/inbox/inbox.feature`: alta manual, deduplicación, descarte y paso a candidatura.
5. `specs/inbox/ats_companies.feature`: empresas vigiladas y consulta de su ATS.

## Fuera (con disparador)

| Fuera | Entra cuando... |
|-------|-----------------|
| Consulta periódica de los ATS (jobs, procrastinate) | Lanzarla a mano se haga pesado |
| Lectura de alertas por email | Dar de alta ofertas a mano sea el cuello de botella |
| Scoring de encaje | La bandeja tenga más ofertas de las que se revisan |
| Seniority y salario mínimo en el perfil | La seniority va hoy en los títulos ("Senior Backend Engineer"); el salario, con la fase de salarios |
| Salarios (bandas de mercado desde webs externas) | Fase propia, revisando antes las condiciones de cada web |
| Métrica de qué portal o búsqueda llega más lejos en el funnel | Haya varias semanas de datos |
