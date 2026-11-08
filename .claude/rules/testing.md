---
paths:
  - "backend/tests/**"
---

# Tests

## Tipos

| Tipo | Marker | Qué prueba | BD | xdist | Ubicación |
|------|--------|------------|----|-------|-----------|
| Unit | `unit` | Dominio puro | No | No | `tests/unit/` |
| Integration | `integration` | Repositories, queries no triviales, jobs | Sí | Sí | `tests/integration/` |
| BDD | `bdd` | Escenarios Gherkin end-to-end por HTTP (httpx ASGI) | Sí | Sí | `tests/bdd/` + `specs/` |
| Migraciones | `migrations` | `upgrade → downgrade base → upgrade`; ORM == esquema migrado | Sí | Sí | `tests/migrations/` |
| Contrato | `contract` | OpenAPI generado == `openapi.json` versionado | No | Sí | `tests/contract/` |

- Pirámide: muchos unit, BDD por escenario, pocos integration.
- Todo test lleva su marker (`--strict-markers`).
- pytest-bdd: `bdd_features_base_dir = ../specs`. Steps compartidos en `tests/bdd/conftest.py`; los propios en `tests/bdd/test_<modulo>_<nombre>.py`.

## Datos

- Fixtures base: `db_session`, `client`, `clock` (reloj fijo), factories.
- **Factories** (`make_application(stage=...)`) con defaults válidos. Prohibidas las fixtures gigantes compartidas.

## Parametrización

- Prohibidos los micro-tests que solo cambian en entrada o resultado esperado: se usa `@pytest.mark.parametrize` con `pytest.param(..., id="legible")`.
- En Gherkin: `Esquema del escenario` + `Ejemplos`.
- No se parametriza si el Arrange o el Assert cambian de estructura: son tests distintos.

## Arrange-Act-Assert

- Bloques `# Arrange` / `# Act` / `# Assert` (sin `# Arrange` si no hay preparación).
- Un solo Act y un solo comportamiento por test.
- Sin `if`, bucles ni `try` en los tests.
- En BDD: `Dado` = Arrange, `Cuando` (uno solo) = Act, `Entonces` = Assert.
- Nombre = comportamiento: `test_rejects_transition_when_skipping_stages`.

```python
@pytest.mark.unit
@pytest.mark.parametrize(
    ("current", "target"),
    [
        pytest.param(Stage.APPLIED, Stage.OFFER, id="applied-to-offer"),
        pytest.param(Stage.DISCOVERED, Stage.INTERVIEWING, id="discovered-to-interviewing"),
    ],
)
def test_rejects_transition_when_skipping_stages(current: Stage, target: Stage) -> None:
    # Arrange
    application = make_application(stage=current)

    # Act
    with pytest.raises(InvalidTransitionError) as exc_info:
        application.transition_to(target)

    # Assert
    assert exc_info.value.target == target
```

## Paralelo (xdist)

- `pytest -n auto`. Un único contenedor Postgres compartido (testcontainers + `filelock`).
- BD template migrada una vez; cada worker crea `test_<worker>` con `CREATE DATABASE ... TEMPLATE funnel_template` (`PYTEST_XDIST_WORKER`).
- Aislamiento: transacción + rollback; `TRUNCATE` en los BDD que hacen commit.
- Para depurar con pdb: `just test-one` (sin xdist).
