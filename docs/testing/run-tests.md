# Cómo correr los tests

## Método principal (Docker — para workflows de implementación)

```bash
./scripts/run-tests.sh
```

Usa Docker para garantizar resultados consistentes y reproducibles, independiente del entorno local.

> Si el script no existe todavía, ejecutar `/sdd.util.makeruntest` para generarlo.

## Fallback (solo para debugging local rápido)

> No usar en workflows de implementación. Solo para exploración local.

```bash
# Activar entorno virtual primero
source .venv/bin/activate

# Correr todos los tests
pytest tests/

# Correr un módulo específico
pytest tests/test_classifier.py

# Con output detallado
pytest tests/ -v

# Limpiar cache de pytest
./scripts/clean-test-cache.sh
```

## Estructura esperada de tests

Los tests viven en `tests/` en la raíz del proyecto (no dentro de `src/`):

```
tests/
├── conftest.py
├── test_classifier.py
├── test_planner.py
├── test_message_builder.py
├── test_memory.py
└── test_config.py
```

> **Nota**: El directorio `tests/` y los archivos de test aún no existen. Ver [testing-guidelines.md](testing-guidelines.md) para la estrategia y [test-conventions.md](test-conventions.md) para las convenciones al crearlos.
