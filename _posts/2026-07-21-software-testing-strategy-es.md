---
title: "Una estrategia de verificación de software basada en riesgos más allá de la pirámide de pruebas"
date: 2026-07-21 10:40:00 +0900
categories: [Software Engineering, Testing]
tags: [testing, pytest, contract-testing, property-testing, integration-testing, quality]
description: Cómo combinar pruebas unitarias, de integración, de contrato y E2E según el riesgo y diseñar oráculos e invariantes sólidos.
lang: es
translation_key: software-testing-strategy
hidden: true
---

{% include language-switcher.html %}

El propósito de las pruebas no es ejecutar líneas de código, sino **encontrar fallas importantes antes del lanzamiento y producir evidencia de que los contratos permanecen intactos después de los cambios**. Incluso una cobertura alta proporciona poca confianza si las afirmaciones son débiles o las pruebas no abordan riesgos reales.

## Trabajar hacia atrás desde el riesgo hasta las pruebas de diseño

Comience anotando los modos de falla.

| Modo de falla | Impacto | Verificación adecuada |
|---|---|---|
| Error de clasificación de valores límite | Decisión incorrecta | Pruebas unitarias y de valores límite |
| DB el esquema no coincide | Error al completar la solicitud | Pruebas de integración y migración |
| Contrato cliente/servidor roto | Fallo de integración después de la implementación | Pruebas de contrato |
| Omisión de autenticación | Acceso no autorizado | Pruebas de seguridad e integración |
| Falta configuración de implementación | Fallo de inicio del servicio | Prueba de humo |
| Flujo de usuarios largo roto | Interrupción crítica del flujo de trabajo | Una pequeña cantidad de pruebas E2E |

Automatiza primero los elementos con alta probabilidad, impacto y dificultad de detección. El dinero, los permisos, las transiciones de estado y las rutas de pérdida de datos tienen prioridad sobre los captadores triviales.

## Las capas de prueba responden diferentes preguntas

### Pruebas unitarias

Responda rápidamente: "¿Es correcta una pequeña regla para cada entrada importante?" Aísle I/O y céntrese en valores límite, excepciones e invariantes.

### Pruebas de integración

Responda: "¿Los componentes reales se comunican bajo el mismo contrato?" Verifique las diferencias que las simulaciones pueden ocultar utilizando el motor de base de datos real, el formato de archivo, el serializador y el adaptador HTTP.

### Pruebas de contrato

Responda: "¿Siguen intactos el esquema y la semántica acordados entre el proveedor y el consumidor?" Verifique los tipos de campos, campos obligatorios y opcionales, códigos de error y compatibilidad con versiones anteriores.

### E2E Pruebas

Responda: "¿Pueden los usuarios lograr sus resultados críticos en el sistema implementado?" Debido a que estas pruebas son lentas y frágiles, comience con de tres a cinco rutas de alto valor en lugar de automatizar cada pantalla.

### Verificación posterior a la implementación

No se detenga después de comprobar que un punto final de estado devuelve 200. Utilice transacciones sintéticas seguras para comprobar las conexiones a dependencias críticas, lecturas y escrituras mínimas, permisos, versiones y estado del trabajador en segundo plano.

## Las buenas pruebas tienen fases claras de organizar, actuar y afirmar

```python
def test_cancelled_job_cannot_restart() -> None:
    # Arrange
    job = Job.cancelled(id="job-example")

    # Act
    result = job.start()

    # Assert
    assert result.is_error
    assert result.code == "INVALID_STATE_TRANSITION"
    assert job.status == "cancelled"
```

Demasiadas acciones en una prueba hacen que no quede claro dónde ocurrió la falla. En el otro extremo, fijar métodos de implementación privados hace que incluso la refactorización válida rompa las pruebas. Verificar resultados observables externamente e invariantes críticas.

## Combine pruebas basadas en ejemplos y basadas en propiedades

Las pruebas de ejemplo son fáciles de leer, pero cubren sólo los casos que el desarrollador anticipó. Las pruebas basadas en propiedades verifican propiedades que siempre deben mantenerse en un amplio espacio de entrada.

Por ejemplo, considere estas propiedades para una función de normalización.

- La potencia se encuentra dentro del rango permitido.
- Normalizar la misma entrada dos veces produce el mismo resultado.
- Reordenar la entrada no cambia un resultado agregado independiente del orden.
- Serializar y luego deserializar conserva el significado.

Los cálculos numéricos necesitan una tolerancia de error justificada. Un `epsilon` arbitrariamente grande oculta errores, mientras que requerir igualdad bit a bit hace que las pruebas sean inestables en todas las plataformas. Combine el error absoluto y relativo según la escala del valor y las condiciones del problema.

## Elija los dobles de prueba con precisión

- stub: Devuelve un valor predeterminado.
- falso: una implementación de reemplazo simplificada pero funcional.
- espía: observa el historial de llamadas.
- simulado: especifica las interacciones esperadas.

Un simulacro de red es útil al probar reglas de dominio. Sin embargo, al burlarse de límites reales como SQL dialectos, transacciones y serialización se pasan por alto errores de integración. Separe "¿qué se debe aislar para la velocidad?" de "¿qué debe verificarse con lo real?"

## Controlar el no determinismo

Las pruebas inestables destruyen la confianza. Haga que el tiempo, la aleatoriedad, la red, el paralelismo y el estado global sean dependencias controlables.

```python
from datetime import datetime, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 1, 1, tzinfo=timezone.utc)
```

Registrar una semilla aleatoria por sí solo no garantiza un determinismo completo. Las versiones de la biblioteca, la ejecución paralela, las operaciones específicas del hardware y el orden de entrada también pueden afectar los resultados. Primero defina el nivel requerido de reproducibilidad.

## Conceptos básicos de las pruebas de bases de datos

- Cada prueba utiliza datos independientes y un espacio de nombres separado.
- Aplicar migraciones tanto a un DB vacío como a un DB de la versión anterior.
- Verificar que las restricciones únicas, de clave externa y de verificación realmente eviten fallas.
- No confiar únicamente en la reversión de transacciones; cuenta para los trabajadores en segundo plano y las conexiones separadas.
- No copiar datos de producción en dispositivos de prueba.

## Hacer que las fallas sean investigables

Cuando CI falla, conserve al menos lo siguiente.

- Nombre de la prueba y semilla.
- Dispositivo de entrada o entrada de reproducción mínima
- Aplicación/versión lógica
- Información sobre el entorno y el bloqueo de dependencias.
- Registros, seguimientos y capturas de pantalla relevantes.
- Distinción entre la causa inicial y los fallos posteriores.

Una política de repetir incondicionalmente las pruebas hasta que se pongan verdes oculta pruebas deficientes. Necesitan aislamiento, clasificación de causas, propietario y plazo para su corrección.

## Lista de verificación de verificación

- [ ] Los modos de falla más costosos se asignan a las pruebas que los detectan.
- [ ] Se verifican los valores inmediatamente debajo, en e inmediatamente encima de los límites.
- [] Las pruebas verifican no solo las excepciones sino también si el estado se conserva después de una falla.
- [] Las pruebas de integración cubren límites reales de DB, serializador y HTTP.
- [] Se detectan cambios que rompen el esquema en CI.
- [ ] Solo los flujos de usuarios críticos se mantienen como pruebas estables E2E.
- [ ] Se controla el no determinismo en el tiempo, la aleatoriedad y las dependencias externas.
- [] Las pruebas inestables no se ocultan únicamente mediante repeticiones automáticas.
- [ ] Se han implementado pruebas de humo y criterios de reversión posteriores al despliegue.

## Fallos comunes

- Tratar el número de cobertura como un objetivo de calidad.
- Repetir el mismo caso de camino feliz sin tener límites, errores y concurrencia.
- Fijar incluso el recuento de llamadas de implementación interna, lo que aumenta los costos de refactorización.
- Pruebas que comparten orden y estado global entre sí.
- Burlarse de todos los límites externos y omitir errores reales de esquema y transacción.
- Dependiendo de sueño arbitrario y coordenadas de pantalla en pruebas E2E.

La pregunta final para una estrategia de prueba no es "¿Cuántas pruebas escribimos?" pero **“¿Qué riesgos controlamos y con qué evidencia?”**
