---
title: "Estándares mínimos para convertir el código Python en software listo para producción"
date: 2026-07-21 10:10:00 +0900
categories: [Software Engineering, Python]
tags: [python, packaging, testing, typing, logging, reproducibility]
description: Estándares prácticos para convertir scripts en aplicaciones Python reproducibles, comprobables y observables.
lang: es
translation_key: python-production-baseline
hidden: true
---

{% include language-switcher.html %}

Lograr que un archivo Python se ejecute una vez y convertirlo en un software que se ejecute de forma segura y repetida en otros entornos son desafíos completamente diferentes. La esencia del código listo para producción no es un marco elaborado, sino si **las entradas, salidas, dependencias y fallas son explícitas**.

## 1. Establezca límites primero

El código más difícil de mantener combina computación, acceso a archivos, solicitudes de red, lecturas de variables de entorno y salida de registros en una sola función. Dividirlo en las siguientes tres capas facilita las pruebas y el reemplazo.

1. **Lógica de dominio**: Computación pura que produce la misma salida para la misma entrada
2. **Adaptadores**: comunicación con archivos, bases de datos, servicios HTTP y colas de mensajes
3. **Punto de entrada**: leer la configuración, ensamblar objetos y determinar códigos de salida

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Reading:
    value: float
    lower: float
    upper: float


def classify(reading: Reading) -> str:
    if reading.lower > reading.upper:
        raise ValueError("lower must not exceed upper")
    if reading.value < reading.lower:
        return "low"
    if reading.value > reading.upper:
        return "high"
    return "normal"
```

Esta función no accede a archivos, relojes ni redes. De este modo se pueden comprobar rápidamente los valores límite y se limitan las posibles causas de fallo.

## 2. Comience con una estructura de proyecto pequeña, pero con responsabilidades separadas

```text
project/
├── pyproject.toml
├── README.md
├── src/
│   └── app/
│       ├── __init__.py
│       ├── domain.py
│       ├── adapters.py
│       └── cli.py
└── tests/
    ├── unit/
    └── integration/
```

El diseño `src` reduce la posibilidad de que la raíz del repositorio se convierta accidentalmente en una ruta de importación y oculte errores de empaquetado. `pyproject.toml` reúne el sistema de compilación, los metadatos del proyecto, las dependencias del tiempo de ejecución y la configuración de la herramienta de desarrollo.

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "example-app"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["httpx>=0.27,<1"]

[project.optional-dependencies]
dev = ["pytest>=8,<9", "ruff>=0.5,<1", "mypy>=1.10,<2"]
```

Las gamas de versiones son sólo ejemplos. En un proyecto real, elija una política de versión de Python compatible y una estrategia de bloqueo de archivos, luego úselas de manera consistente en CI y en la implementación.

## 3. Configuración separada de los secretos

La configuración se divide en tres categorías.

| Categoría | Ejemplos | Ubicación de almacenamiento |
|---|---|---|
| Valores predeterminados del código | Tamaño de lote, tiempo de espera predeterminado | Código o un archivo de configuración público |
| Configuración específica del entorno | API dirección, nivel de registro | Variables de entorno o configuración de implementación |
| Secretos | Tokens, contraseñas, claves privadas | Administrador de secretos |

Incluso un valor como `DEBUG=true` es una cadena. Valídelo una vez al inicio en lugar de depender de la conversión de tipos implícita.

```python
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    api_base_url: str
    timeout_seconds: float


def load_settings() -> Settings:
    base_url = os.environ["API_BASE_URL"]
    timeout = float(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))
    if timeout <= 0:
        raise ValueError("HTTP_TIMEOUT_SECONDS must be positive")
    return Settings(api_base_url=base_url, timeout_seconds=timeout)
```

No deje valores secretos en mensajes de excepción, argumentos CLI, Git, dispositivos de prueba o resultados del cuaderno. Simplemente enmascararlos con `***` no es suficiente; En primer lugar, es más seguro no colocarlos nunca en los campos de registro.

## 4. Los tipos explican los contratos; No reemplazan la ejecución

Las sugerencias de tipo comunican rápidamente la intención de las entradas y salidas y reducen los errores de refactorización. Sin embargo, JSON, CSV y las variables de entorno recibidas desde el exterior no se validan únicamente mediante sugerencias de tipo. Se necesitan dos capas: **validación en tiempo de ejecución en límites de confianza** y verificación de tipos internamente.

- Restringir `Any` a áreas en proceso de migración gradual.
- Prefiera `dataclass`, `TypedDict` o tipos de modelo significativos a `dict[str, object]`.
- Deje claro si `None` es un estado normal o un estado de error.
- Distinguir números con distintas unidades mediante nombres o tipos separados.

## 5. Los registros son eventos estructurados, no oraciones

Los registros de producción deben poder filtrarse y agregarse más adelante.

```python
import logging

logger = logging.getLogger(__name__)


def handle(job_id: str) -> None:
    logger.info("job_started", extra={"job_id": job_id})
    try:
        run_job(job_id)
    except TimeoutError:
        logger.exception("job_timed_out", extra={"job_id": job_id})
        raise
```

Los campos comunes mínimos son `event`, `timestamp`, `severity`, `service`, `request_id` o `job_id`, `duration` y `outcome`. No registre cuerpos completos de solicitudes sin procesar ni encabezados de autenticación.

## 6. Organizar las pruebas según los niveles de riesgo

```python
import pytest

from app.domain import Reading, classify


@pytest.mark.parametrize(
    ("value", "expected"),
    [(9.0, "low"), (10.0, "normal"), (20.0, "normal"), (21.0, "high")],
)
def test_classify_boundaries(value: float, expected: str) -> None:
    assert classify(Reading(value=value, lower=10.0, upper=20.0)) == expected
```

- Pruebas unitarias: lógica pura, valores límite e invariantes
- Pruebas de integración: base de datos, archivos y adaptadores HTTP
- Pruebas de contrato: Esquemas de solicitud/respuesta y formatos de error.
- Pruebas de humo: si las rutas críticas siguen operativas después del despliegue

Burlarse de cada detalle de implementación puede ocultar errores de integración reales. Por el contrario, realizar cada prueba E2E hace que la suite sea lenta y las fallas sean difíciles de diagnosticar. Divida las capas según el costo del fracaso y la frecuencia del cambio.

## 7. Las salidas y los reintentos también son API

Las CLI y los trabajos por lotes deben distinguir el éxito del fracaso mediante códigos de salida. Los reintentos de red requieren un recuento máximo de intentos, un retroceso exponencial, fluctuaciones y una fecha límite general. No reintente automáticamente operaciones con efectos secundarios a menos que se garantice la idempotencia.

```python
def main() -> int:
    try:
        settings = load_settings()
        execute(settings)
    except ConfigurationError as exc:
        logger.error("invalid_configuration", extra={"reason": str(exc)})
        return 2
    except Exception:
        logger.exception("unhandled_failure")
        return 1
    return 0
```

## Lista de verificación de preproducción

- [] La aplicación se puede instalar y ejecutar en un nuevo entorno utilizando únicamente los comandos documentados.
- [] Se declaran la versión y las dependencias de Python y existe una estrategia de bloqueo.
- [ ] Se validan los esquemas de entrada, unidades, rangos y políticas de valores faltantes.
- [] No aparecen secretos en el código, el historial de Git, los registros ni los datos de prueba.
- [] La lógica del dominio principal se prueba sin I/O externo.
- [ ] Los tiempos de espera, el presupuesto de reintentos y los códigos de salida son explícitos.
- [] Se puede rastrear una solicitud o trabajo a través de registros estructurados.
- [] Los artefactos liberados se pueden reconstruir en un entorno limpio.

## Fallos comunes

- El código funciona correctamente solo en un cuaderno, mientras que las importaciones de paquetes y CLI no funcionan.
- Los efectos secundarios del estado global y del tiempo de importación hacen que los resultados dependan del orden de la prueba.
- `except Exception: pass` hace que el fracaso parezca un éxito.
- Instalar siempre las últimas versiones hace que el entorno de ayer sea imposible de reproducir.
- Se generan muchos registros, pero sin identificadores o nombres de eventos no se pueden buscar.

La preparación para la producción no debe juzgarse por las líneas de código, sino por **la confiabilidad con la que se puede reinstalar el software, reproducir las fallas y realizar la recuperación de manera segura**.

## Referencias

- [Guía del usuario de Python Packaging: escritura `pyproject.toml`](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [Guía del usuario de empaquetado de Python: empaquetado de proyectos de Python](https://packaging.python.org/tutorials/packaging-projects/)
