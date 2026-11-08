---
paths:
  - "backend/tests/**"
---

# Tests

## Tipos

| Tipo | Marker | Qué prueba | BD | xdist | Ubicación |
|------|--------|------------|----|-------|-----------|
| Unit | `unit` | Lógica sin BD ni red: dominio y `core` (con la app de prueba de `support/probe.py`) | No | No | `tests/unit/` |
| Integration | `integration` | Repositories, queries no triviales, jobs, `/health` | Sí | Sí | `tests/integration/` |
| BDD | `bdd` | Escenarios Gherkin end-to-end por HTTP (fixture `client`) | Sí | Sí | `tests/bdd/` + `specs/` |
| Migraciones | `migrations` | `upgrade → downgrade base → upgrade`; ORM == esquema migrado | Sí | Sí | `tests/migrations/` |
| Contrato | `contract` | OpenAPI generado == `openapi.json` versionado | No | Sí | `tests/contract/` |

- Pirámide: muchos unit, BDD por escenario, pocos integration.
- Todo test lleva su marker (`--strict-markers`).
- pytest-bdd: `bdd_features_base_dir = ../specs`. Steps compartidos en `tests/bdd/conftest.py`; los propios en `tests/bdd/test_<modulo>_<nombre>.py`.

## Datos

- Fixtures existentes (`tests/conftest.py`): `client` (TestClient autenticado contra la BD del worker; trunca las tablas al terminar), `settings`, `database_url`, `empty_database_url` (sin migrar), `postgres_server_url`. En `tests/unit/`: `probe_client`.
- Helpers importables en `tests/support/` (`from support.postgres import ...`); un conftest no se importa.
- Se añaden cuando haga falta el primero que las use: `db_session` (sesión async con rollback para los tests de repositories) y `clock` (reloj fijo).
- `filterwarnings = error`: un aviso de deprecación rompe el test. Se arregla la causa; no se silencia el aviso.
- **Factories** (`make_application(stage=...)`) con defaults válidos. Prohibidas las fixtures gigantes compartidas.

## Parametrización

- Prohibidos los micro-tests que solo cambian en entrada o resultado esperado: se usa `@pytest.mark.parametrize` con `pytest.param(..., id="legible")`.
- En Gherkin: `Scenario Outline` + `Examples`.
- No se parametriza si el Arrange o el Assert cambian de estructura: son tests distintos.

## Arrange-Act-Assert

- Bloques `# Arrange` / `# Act` / `# Assert` (sin `# Arrange` si no hay preparación).
- Un solo Act y un solo comportamiento por test.
- Sin `if`, bucles ni `try` en los tests.
- En BDD: `Given` = Arrange, `When` (uno solo) = Act, `Then` = Assert.
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

- Un único contenedor Postgres por ejecución. Con xdist lo arranca el proceso controlador (`pytest_configure`) y pasa la URL a los workers (`pytest_configure_node`). En serie arranca de forma perezosa en la primera fixture que lo pide, así que `just test-unit` no necesita Docker.
- BD template migrada una vez; cada worker clona `test_<worker_id>` (clonación serializada con `filelock`).
- Aislamiento: los tests HTTP hacen commit real, y `client` hace `TRUNCATE` de todas las tablas al terminar. Los de repository usarán rollback (`db_session`, cuando exista).
- Para depurar con pdb: `just test-one "expr"` (sin xdist).
- `just test-bdd` sale con código 5 ("no tests") hasta que exista la primera feature. Es esperado.
