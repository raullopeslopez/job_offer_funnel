# Glosario de dominio (ES → EN)

Fuente única de nombres. El producto (specs, código, API, BD) usa solo la columna EN; la columna ES es para la documentación interna. Un concepto nuevo se añade aquí **antes** de usarlo.

## Fases (`Stage`)

| ES | EN (`Stage`) |
|----|--------------|
| Descubierta | `discovered` |
| Evaluada | `evaluated` |
| Aplicada | `applied` |
| Screening | `screening` |
| Entrevistas | `interviewing` |
| Oferta | `offer` |
| Aceptada | `accepted` |

## Estados de salida (`Outcome`)

| ES | EN (`Outcome`) |
|----|----------------|
| Rechazado | `rejected` |
| Ghosted | `ghosted` |
| Retirado | `withdrawn` |
| Oferta rechazada | `offer_declined` |

## Entidades

| ES | EN |
|----|----|
| Candidatura (oferta en el funnel) | `Application` |
| Empresa | `Company` |
| Contacto | `Contact` |
| Documento (CV, carta) | `Document` |
| Evento | `Event` |
| Tarea / recordatorio | `Task` |
| Transición (cambio de fase) | `Transition` |
| Banco de preguntas / pregunta | `Question` |
| Portal de empleo | `JobBoard` |
| Perfil de búsqueda | `SearchProfile` |
| Búsqueda generada (perfil + portal) | `GeneratedSearch` |
| Oferta descubierta | `DiscoveredOffer` |

## Atributos

| ES | EN |
|----|----|
| Canal de origen | `channel` |
| Puesto | `role` |
| URL de la oferta | `url` |
| Notas | `notes` |
| Fase alcanzada | `reached_stage` |
| Estado final | `outcome` |
| Prioridad | `priority` |
| Encaje (score) | `fit_score` |

## Canales de origen (`Channel`)

| ES | EN (`Channel`) |
|----|------------------|
| Portal | `portal` |
| Referido | `referral` |
| Recruiter inbound | `recruiter_inbound` |
| Candidatura directa en la web | `direct` |
| Networking | `networking` |

## Prioridad (`Priority`)

| ES | EN (`Priority`) |
|----|-------------------|
| A | `high` |
| B | `medium` |
| C | `low` |

## Métricas

| ES | EN |
|----|----|
| Conversión (de una fase a la siguiente) | `conversion` |
| Tasa de conversión | `rate` |
| Pipeline activo | `active pipeline` / `pipeline` |

## Descubrimiento

| ES | EN |
|----|----|
| Título del puesto (en un perfil) | `titles` |
| Palabras clave obligatorias | `keywords` |
| Palabras excluidas | `excluded_keywords` |
| Ubicación | `location` |
| Modalidad | `work_mode`: `remote` · `hybrid` · `onsite` |
| Sintaxis de búsqueda | `syntax`: `boolean` · `minus` · `keywords` |
| Plantilla de URL de búsqueda | `search_url_template` |
| Método de importación de un portal (cómo llegan sus ofertas a la Bandeja) | `import_method`: `none` (a mano, con su búsqueda generada) · `api` (por su feed) · `rss` (por su RSS) |

## Bandeja

| ES | EN |
|----|----|
| Estado de una oferta descubierta | `status`: `pending` · `discarded` · `promoted` |
| Motivo de descarte (lista cerrada; `title_word` lleva la palabra del título) | `discard_reason`: `title_word` · `stack` · `location` · `contract` · `company` · `none` · `expired` |
| Pasar a candidatura | `promote` |
| Devolver a pendiente | `restore` |
| Feed público (API de un portal, con un adaptador en el código; lo declara el portal) | `feed`: `remoteok` · `remotive` · `himalayas` · `jobicy` |
| Plantilla de la URL del RSS de un portal (con `{query}`, donde va cada título de los perfiles) | `rss_url_template` |
| Importación de un portal | `import` |
| Oferta filtrada (importada, pendiente y sin encaje con ningún perfil) | `filtered` |
| Regla del encaje con un perfil | `rule`: `title` · `keywords` · `excluded` · `work_mode` · `location` · `stable` |
| Resultado de una regla | `passed` · `unknown` (la lectura no lo dice o no hay lectura) · `failed` |
| Perfil de referencia de una oferta (el que menos reglas incumple; empate: el primero por nombre) | `reference profile` |
| Motivo del filtrado (resultado de cada regla frente al perfil de referencia) | `filter reason` |
| Casi: filtrada que pasa el título y falla una sola regla | `near miss` (`near_miss`) |
| Revisión de una filtrada: rescate (promoverla) o bien filtrada (dejarla filtrada) | `review`: `rescued` · `rightly_filtered` |
| Empresa vigilada (por su ATS) | `watched company` |
| Alerta por email (método de importación `email` de un portal) | `email alert`: `linkedin` |
| Lectura de una oferta (lo que dice su descripción, para una ubicación de un perfil) | `reading` |
| Lector de ofertas (servicio externo que lee la descripción) | `offer reader` |
| Triaje de una pendiente (un modelo la compara con mis decisiones, leyendo su descripción; no confundir con la fase `screening`) | `triage` |
| Triador de ofertas (servicio externo que hace el triaje) | `offer triager` |
| Veredicto del triaje (OK: merece mi tiempo; KO: falso positivo, pasó mis filtros y la descartaría) | `verdict`: `ok` · `ko` |
| Porqué del veredicto (una frase del triador, con sus palabras) | `why` |
| Descarte sugerido (veredicto `ko` con motivo y evidencia que se sostiene; nunca se aplica solo) | `suggested discard` |
| Sugerencia rechazada (descarte sugerido de una oferta que promoví) | `rejected suggestion` |
| Descarte no visto (oferta que el triador marcó OK y que descarté) | `missed discard` |
| Relajar una regla (cambio de criterio que deja entrar más ofertas: dejar de excluir una palabra, añadir una palabra clave, aceptar una modalidad) | `relax` |
| Rescate perdido (casi que el triador marcó KO y que rescaté) | `lost rescue` |
| Modalidad que dice la oferta | `work_mode` (los mismos valores que en el perfil) |
| Se puede hacer viviendo en la ubicación del perfil | `admits_location` (sí o no; en las specs `yes` · `no`) |
| Puesto estable (jornada completa y sin fecha de fin, como empleado o como contractor; no por tareas, por horas, temporal ni a media jornada) | `stable` (sí o no; en las specs `yes` · `no`) |
| Frase literal de la descripción que justifica una respuesta | `evidence` |
| ATS (sistema de selección de la empresa) | `ats`: `greenhouse` · `lever` · `ashby` |
| Tablero de la empresa en su ATS (nombre en la URL pública de empleo) | `board` |
