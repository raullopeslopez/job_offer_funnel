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
| Portal (fuente) | `Source` |
| Perfil de búsqueda | `SearchProfile` |
| Búsqueda guardada | `SavedSearch` |
| Oferta descubierta (bandeja) | `DiscoveredOffer` |

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
