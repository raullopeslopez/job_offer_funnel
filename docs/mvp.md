# Alcance del MVP

**Pregunta que responde**: ¿dónde se me caen las candidaturas y qué tengo en curso?

**Interfaz**: solo la API del backend, usada desde Swagger UI (`/docs`). El frontend se define después, con la API ya estable.

## Dentro

| # | Capacidad | Detalle mínimo |
|---|-----------|----------------|
| 1 | Candidaturas | Crear, editar, ver y listar con filtros (fase, outcome, canal). Campos: empresa, puesto, URL, canal, prioridad, notas |
| 2 | Transiciones de fase | Máquina de estados con historial fechado |
| 3 | Salidas | `rejected`, `ghosted`, `withdrawn`, `offer_declined`, guardando la fase alcanzada. El ghosting se marca a mano |
| 4 | Empresas | Entidad mínima (nombre + web opcional), módulo CRUD. Una empresa puede tener varias candidaturas |
| 5 | Métricas | Conversión por fase, conversión por canal, pipeline activo |
| 6 | Auth | Un token fijo por config (`AUTH_TOKEN`) |

Fases incluidas: de `evaluated` a `accepted`. Una candidatura se crea en `evaluated` o en `applied`.

## Specs, en orden

1. `specs/applications/stage_transitions.feature`: transiciones válidas e inválidas, y salidas. Aquí se decide si se pueden saltar fases.
2. `specs/applications/manage_applications.feature`: alta, edición, detalle con historial, listado con filtros.
3. `specs/companies/manage_companies.feature`: alta y listado.
4. `specs/metrics/funnel_metrics.feature`: conversión por fase y por canal, pipeline activo.

## Fuera (con disparador)

| Fuera | Entra cuando... |
|-------|-----------------|
| Frontend / dashboard | La API del MVP esté estable |
| Fase 0 (descubrimiento, portales, búsquedas) | Meter ofertas a mano sea el cuello de botella |
| Contactos, documentos y versiones de CV | Se quiera medir la conversión por versión de CV o por referido |
| Eventos y rondas de entrevista | Las notas no basten para preparar entrevistas |
| Tareas y follow-ups | Se olviden los seguimientos |
| Ghosting automático (jobs, procrastinate) | Marcarlo a mano se haga pesado |
| Banco de preguntas, comparador de ofertas | Haya ofertas reales que comparar |
| Tiempo medio por fase | Se pida (es barato: el historial ya existe) |
