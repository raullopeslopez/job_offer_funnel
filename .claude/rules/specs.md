---
paths:
  - "specs/**"
---

# Specs (Gherkin)

- Antes de escribir una spec, leer `docs/funnel.md` (comportamiento de cada fase) y `docs/glossary.md` (términos).
- `# language: es` en la primera línea. Palabras clave en español: `Característica`, `Escenario`, `Esquema del escenario`, `Ejemplos`, `Dado`, `Cuando`, `Entonces`, `Y`.
- Ruta: `specs/<modulo>/<nombre>.feature`, con el módulo en inglés y en snake_case.
- Describir comportamiento observable desde fuera (qué pasa), nunca la implementación (tablas, clases, endpoints).
- Un `Cuando` por escenario.
- Casos que solo cambian en los datos: `Esquema del escenario` + `Ejemplos`, no escenarios copiados.
- Usar los términos del glosario (columna ES). Si falta un término, añadirlo antes al glosario.
- Incluir los caminos de error (transición inválida, recurso inexistente), no solo el camino feliz.
- Una spec nueva o modificada siempre pasa por revisión del usuario antes de implementar.
