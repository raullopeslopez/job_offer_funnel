# language: es
Característica: Transiciones de fase de una candidatura
  Como candidato
  Quiero registrar cómo avanza o se cierra cada candidatura
  Para saber en qué punto del funnel está y dónde se me caen

  Fases, en orden: Evaluada, Aplicada, Screening, Entrevistas, Oferta, Aceptada.
  Estados de salida: Rechazado, Ghosted, Retirado, Oferta rechazada.
  Una candidatura cerrada con un estado de salida conserva la fase alcanzada.

  Antecedentes:
    Dado que hoy es 2026-03-10

  # --- Avanzar ---

  Esquema del escenario: Avanzar a cualquier fase posterior, saltando fases si hace falta
    Dada una candidatura en fase "<origen>"
    Cuando la muevo a la fase "<destino>"
    Entonces la candidatura está en fase "<destino>" y sigue abierta

    Ejemplos:
      | origen      | destino     |
      | Evaluada    | Aplicada    |
      | Evaluada    | Screening   |
      | Aplicada    | Screening   |
      | Aplicada    | Entrevistas |
      | Screening   | Entrevistas |
      | Entrevistas | Oferta      |
      | Oferta      | Aceptada    |

  Esquema del escenario: No se puede retroceder ni repetir la fase actual
    Dada una candidatura en fase "<origen>"
    Cuando la muevo a la fase "<destino>"
    Entonces se rechaza por transición inválida
    Y la candidatura sigue en fase "<origen>"

    Ejemplos:
      | origen      | destino     |
      | Screening   | Aplicada    |
      | Oferta      | Entrevistas |
      | Aplicada    | Evaluada    |
      | Aplicada    | Aplicada    |

  # --- Cerrar con un estado de salida ---

  Esquema del escenario: Cerrar una candidatura con un estado de salida permitido en su fase
    Dada una candidatura en fase "<fase>"
    Cuando la cierro como "<salida>"
    Entonces la candidatura está cerrada como "<salida>" con fase alcanzada "<fase>"

    Ejemplos:
      | fase        | salida           |
      | Evaluada    | Retirado         |
      | Entrevistas | Retirado         |
      | Aplicada    | Rechazado        |
      | Oferta      | Rechazado        |
      | Aplicada    | Ghosted          |
      | Entrevistas | Ghosted          |
      | Oferta      | Oferta rechazada |

  Esquema del escenario: No se puede cerrar con un estado de salida que no tiene sentido en la fase
    Dada una candidatura en fase "<fase>"
    Cuando la cierro como "<salida>"
    Entonces se rechaza por transición inválida
    Y la candidatura sigue en fase "<fase>" y abierta

    Ejemplos:
      | fase        | salida           |
      | Evaluada    | Rechazado        |
      | Evaluada    | Ghosted          |
      | Aplicada    | Oferta rechazada |
      | Entrevistas | Oferta rechazada |

  # --- Candidaturas terminadas ---

  Esquema del escenario: Una candidatura aceptada o cerrada (salvo Ghosted) no admite más cambios
    Dada una candidatura cerrada como "<salida>" con fase alcanzada "<fase>"
    Cuando la muevo a la fase "<destino>"
    Entonces se rechaza por transición inválida

    Ejemplos:
      | salida           | fase        | destino     |
      | Rechazado        | Screening   | Entrevistas |
      | Retirado         | Aplicada    | Screening   |
      | Oferta rechazada | Oferta      | Aceptada    |

  Escenario: Una candidatura aceptada no se puede cerrar con un estado de salida
    Dada una candidatura en fase "Aceptada"
    Cuando la cierro como "Retirado"
    Entonces se rechaza por transición inválida

  # --- Reactivar una candidatura Ghosted ---

  Esquema del escenario: Una candidatura Ghosted se reactiva al moverla a su fase alcanzada o a una posterior
    Dada una candidatura cerrada como "Ghosted" con fase alcanzada "Screening"
    Cuando la muevo a la fase "<destino>"
    Entonces la candidatura está en fase "<destino>" y sigue abierta

    Ejemplos:
      | destino     |
      | Screening   |
      | Entrevistas |

  Escenario: Una candidatura Ghosted no se reactiva en una fase anterior a la alcanzada
    Dada una candidatura cerrada como "Ghosted" con fase alcanzada "Entrevistas"
    Cuando la muevo a la fase "Screening"
    Entonces se rechaza por transición inválida

  # --- Fecha de la transición ---

  Escenario: Sin fecha, la transición se registra con la fecha de hoy
    Dada una candidatura en fase "Aplicada"
    Cuando la muevo a la fase "Screening"
    Entonces la última transición tiene fecha 2026-03-10

  Escenario: Se puede registrar una transición con fecha pasada
    Dada una candidatura que pasó a fase "Aplicada" el 2026-03-01
    Cuando la muevo a la fase "Screening" con fecha 2026-03-04
    Entonces la última transición tiene fecha 2026-03-04

  Esquema del escenario: La fecha no puede ser futura ni anterior a la transición previa
    Dada una candidatura que pasó a fase "Aplicada" el 2026-03-05
    Cuando la muevo a la fase "Screening" con fecha <fecha>
    Entonces se rechaza por fecha inválida
    Y la candidatura sigue en fase "Aplicada"

    Ejemplos:
      | fecha      |
      | 2026-03-11 |
      | 2026-03-04 |

  # --- Historial ---

  Escenario: Cada transición queda en el historial, en orden
    Dada una candidatura que pasó a fase "Aplicada" el 2026-03-01
    Y la muevo a la fase "Screening" con fecha 2026-03-03 y la nota "Llamada con recruiter"
    Y la cierro como "Ghosted" con fecha 2026-03-09
    Cuando consulto su historial de transiciones
    Entonces el historial es:
      | desde     | hacia     | salida  | fecha      | nota                  |
      |           | Aplicada  |         | 2026-03-01 |                       |
      | Aplicada  | Screening |         | 2026-03-03 | Llamada con recruiter |
      | Screening | Screening | Ghosted | 2026-03-09 |                       |

  # --- Errores ---

  Escenario: No se puede mover una candidatura que no existe
    Cuando muevo una candidatura inexistente a la fase "Screening"
    Entonces se rechaza porque la candidatura no existe
