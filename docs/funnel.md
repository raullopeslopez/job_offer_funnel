# Funnel de búsqueda de empleo

Punto de vista: **candidato**. El funnel sigue cada candidatura desde que se descubre la oferta hasta que se firma.

Para cada fase: objetivo · datos · flujo · matices · métricas.

---

## Fase 0: Descubierta

**Objetivo**: encontrar ofertas en distintos portales con búsquedas adaptadas a cada uno.

**Conceptos**
- **Portal (fuente)**: cada uno tiene su propia sintaxis de búsqueda, sus filtros y su forma de sacar los datos.
- **Perfil de búsqueda (abstracto)**: la intención se define una vez (rol, stack, ubicación, modalidad, seniority, salario mínimo, exclusiones) y se traduce a cada portal.
- **Búsqueda guardada**: `portal + query + filtros + frecuencia`.

**Portales (ejemplos)**

| Portal | Búsqueda | Filtros clave | Ingesta |
|--------|----------|---------------|---------|
| LinkedIn | Booleana completa: `AND OR NOT`, `"comillas"`, `()` | Fecha de publicación, remoto/híbrido, seniority, Easy Apply | Sin API pública: alertas por email o URL guardada. Scraping contra sus términos de uso |
| InfoJobs | Keywords | Provincia, categoría, salario, contrato | API oficial |
| Indeed | Semi-booleana: `OR`, `-excluir`, `title:` | Fecha, salario, jornada | Alertas por email |
| ATS de empresas (Greenhouse, Lever, Ashby) | — | — | Endpoints JSON públicos |
| Portales de nicho | Varía | Varía | RSS, email o manual |

**Flujo**
```
Perfil → Búsquedas por portal → Ingesta → Normalizar → Deduplicar → Scoring → Bandeja → [descartar | Evaluada]
```

**Matices**
- Deduplicar por empresa + título normalizado + fecha (la misma oferta sale en varios portales).
- El método de ingesta es un atributo del portal: empezar manual/email y automatizar solo donde haya API.
- Es un backlog separado: no infla las métricas del funnel.

**Métricas**: qué búsqueda o portal genera ofertas que llegan lejos en el funnel, no solo volumen.

---

## Fase 1: Evaluada

**Objetivo**: decidir si la oferta merece tu tiempo.

**Datos**: score automático + score manual · info de empresa (tamaño, sector, financiación, stack, reviews) · salario publicado o estimado · contactos en la empresa (posible referido) · prioridad A/B/C · fecha límite.

**Flujo**: `Bandeja → Investigar empresa → Buscar contacto → Go / No-go → Prioridad`

**Matices**
- La empresa es una entidad aparte; su research se reutiliza entre ofertas.
- El no-go se registra con su motivo (sirve para afinar el scoring).
- Si hay referido, cambia el canal de la fase 2.

**Métricas**: % que pasa el filtro · motivos de descarte · tiempo de evaluación.

---

## Fase 2: Aplicada

**Objetivo**: enviar la mejor candidatura por el mejor canal.

**Datos**: versión de CV usada · carta (sí/no, versión) · canal (Easy Apply, web/ATS, referido, email al recruiter) · respuestas del formulario · match de keywords · fecha de envío · recordatorio de seguimiento.

**Flujo**: `Adaptar CV → (pedir referido) → Enviar → Follow-up a +7 días → Esperar`

**Matices**
- A/B testing de CV gracias a la versión guardada.
- Follow-up automático: X días sin respuesta → tarea.
- Ghosting automático tras N días (14-21) sin respuesta.

**Métricas**: tasa de respuesta por versión de CV y por canal · tiempo hasta la primera respuesta · candidaturas por semana.

---

## Fase 3: Screening

**Objetivo**: superar el filtro de RRHH y sacar información del proceso.

**Datos**: recruiter (nombre, email, LinkedIn) · tipo (llamada, cuestionario, test automático) · info obtenida (nº de rondas, timeline, banda salarial, motivo de la vacante, equipo) · cifra salarial que diste · notas.

**Flujo**: `Contacto → Agendar → Preparar pitch + preguntas → Llamada → Notas → Resultado`

**Matices**
- Registra siempre si diste cifra salarial: condiciona la fase 5.
- Plantillas de pitch reutilizables.
- Los tests automáticos se modelan como evento (pueden ir en la fase 3 o en la 4).

**Métricas**: conversión screening → entrevista · bandas salariales recogidas (dato de mercado).

---

## Fase 4: Entrevistas

**Objetivo**: superar N rondas.

**Datos (un evento por ronda)**: tipo (técnica, live coding, take-home, system design, manager, cultural, panel, final) · fecha, duración, modalidad · entrevistadores · checklist de preparación · preguntas que te hicieron · autoevaluación 1-5 · feedback · agradecimiento enviado · take-home: plazo + horas invertidas.

**Flujo**: `Agendar → Preparar → Entrevista → Notas → Agradecimiento → [Siguiente ronda | Oferta | Rechazo]`

**Matices**
- El banco de preguntas es transversal a todos los procesos.
- La conversión por tipo de ronda revela tu punto débil.
- Las horas de take-home son coste real.
- Riesgo de solapes con varios procesos en paralelo.

**Métricas**: conversión por tipo de ronda · autoevaluación vs resultado · rondas medias · duración del proceso.

---

## Fase 5: Oferta

**Objetivo**: evaluar, comparar, negociar y decidir.

**Datos**: base, variable, equity, bonus de entrada · modalidad, vacaciones, beneficios, fecha de incorporación · fecha límite de respuesta · historial de negociación · score ponderado.

**Flujo**: `Recibir → Desglosar → Comparar → (acelerar otros procesos) → Negociar → Decidir`

**Matices**
- Comparador de ofertas lado a lado con pesos propios.
- Alerta para avisar al resto de procesos activos y pedir que aceleren.
- Mostrar la cifra que diste en la fase 3.
- Comparar el total anual, no solo la base.

**Métricas**: oferta inicial vs final · ofertas vs bandas de mercado.

---

## Fase 6: Aceptada

**Objetivo**: cerrar bien.

**Datos**: fecha de firma · fecha de incorporación · procesos abiertos que hay que cerrar.

**Flujo**: `Firmar → Retirarse del resto de procesos → Preaviso empresa actual → Retro`

**Matices**: tarea "retirarse" automática para cada proceso activo · retro final (canal, CV y preparación que funcionaron) · archivar cerrándola con un outcome (borrar solo para corregir un alta por error).

---

## Estados de salida (desde cualquier fase)

| Estado | Datos | Matiz |
|--------|-------|-------|
| Rechazado | Fase alcanzada, motivo, feedback | Pedir feedback. Opción "reintentar en X meses" |
| Ghosted | Fase alcanzada, días sin respuesta | Automático; reactivable si contestan |
| Retirado | Fase alcanzada, motivo | Salario, cultura, otra oferta, proceso demasiado largo |
| Oferta rechazada | Motivo, oferta elegida | Mantener la relación |

Modelado: `estado_final` + `fase_alcanzada`.

---

## Dimensión: canal de origen

Portal · referido · recruiter inbound · candidatura directa en la web · networking. Se usa para medir la conversión por canal.

## Entidades transversales

- **Empresa**: research reutilizable, historial de procesos, opción de "no volver a aplicar".
- **Contacto**: mini-CRM con recruiters, entrevistadores y referidos.
- **Documento**: CVs y cartas versionados.
- **Evento**: cualquier interacción con fecha.
- **Tarea / recordatorio**: follow-ups, preparación, plazos.
- **Transición**: cada cambio de fase con fecha. Base de las métricas de tiempo.
- **Banco de preguntas**: transversal a todos los procesos.

## Métricas globales

Conversión por fase · tiempo medio en cada fase · tasa de ghosting · conversión por canal · volumen semanal · pipeline activo.
