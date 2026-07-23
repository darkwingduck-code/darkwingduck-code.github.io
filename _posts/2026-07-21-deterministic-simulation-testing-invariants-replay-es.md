---
title: "Prueba de simulaciones deterministas: invariantes, pruebas basadas en propiedades y reproducción"
date: 2026-07-21 09:40:00 +0900
categories: [Software Engineering, Simulation Testing]
tags: [determinism, simulation-testing, invariants, property-based-testing, replay, regression-testing, reproducibility]
description: "Aprenda a validar simuladores deterministas con invariantes, pruebas de propiedades generativas, hashes de estado y reproducción de eventos en lugar de un puñado de ejemplos."
math: true
lang: es
hidden: true
translation_key: deterministic-simulation-testing-invariants-replay
---

{% include language-switcher.html %}

Si las pruebas de simulación se detienen en "ejecutar una entrada representativa y ver si el gráfico se ve similar", es difícil saber qué ley violó un pequeño cambio. Por el contrario, congelar un archivo de salida completo como un archivo dorado hace que las pruebas fallen en diferencias inofensivas de punto flotante y puede preservar un resultado heredado incorrecto para siempre.

Una estrategia más sólida combina tres capas.

1. **Invariantes y relaciones** que toda ejecución correcta debe satisfacer
2. **Pruebas basadas en propiedades** que exploran automáticamente un amplio espacio de entrada
3. **Repetición de semilla, evento y estado** que reproduce una falla exactamente

## 1. Distinga primero tres términos

### Determinismo

La propiedad de obtener las mismas transiciones de estado desde el mismo estado inicial, entrada, configuración y entorno de ejecución.

$$
s_{t+1}=F(s_t,u_t;\theta)
$$

debe producir el mismo \(s_{t+1}\) para el mismo \(s_t,u_t,\theta\).

### Reproducibilidad

La capacidad de recrear un resultado dentro de un rango permitido en un momento diferente o en otro entorno. Es más amplio que el determinismo bit a bit y requiere información sobre la fuente, las dependencias, la configuración, los datos, el compilador y el hardware.

### Robustez

Propiedad de que una conclusión permanece estable ante cambios aceptables en los datos de entrada o en el entorno. Un programa que siempre da la misma respuesta incorrecta para la misma entrada es determinista, pero no es robusto ni correcto.

## 2. Entradas ocultas que rompen el determinismo

Los argumentos de función en el código no son las únicas entradas. Lo siguiente también puede afectar las transiciones de estado.

- semilla y algoritmo del generador de números pseudoaleatorios
- hora y ubicación del reloj de pared
- orden de iteración del mapa hash
- programación de subprocesos y orden de reducción
- operaciones atómicas en núcleos GPU
- indicadores del compilador y matemáticas rápidas
- BLAS, tiempo de ejecución y controlador
- orden de enumeración de archivos
- variables de entorno y valores de configuración predeterminados
- respuestas de servicios externos
- memoria no inicializada

En consecuencia, “nosotros fijamos la semilla” no completa el determinismo. Es mejor separar los flujos aleatorios por subsistema para que un cambio en el orden de ejecución no altere el consumo de números aleatorios de otro subsistema.

## 3. Una red de prueba en lugar de una pirámide de prueba

Un simulador necesita varios tipos de oráculos.

| Tipo de prueba | Pregunta | Fallos que revela bien |
|---|---|---|
| prueba unitaria | ¿Se comporta una pequeña operación como se define? | signos, unidades, índices, manejo de límites |
| prueba analítica/de referencia | ¿Converge a una solución conocida? | implementación de ecuación o esquema |
| prueba invariante | ¿Obedece leyes que deben preservarse? | deriva acumulativa, fuentes faltantes |
| prueba basada en propiedades | ¿Las propiedades se mantienen sobre entradas válidas amplias? | casos inesperados |
| prueba metamórfica | ¿Son correctas las relaciones de salida bajo transformaciones de entrada? | errores lógicos en problemas sin oráculo |
| prueba diferencial | ¿Está de acuerdo con una implementación independiente? | divergencia específica de la implementación |
| regresión/prueba de oro | ¿El comportamiento aprobado permaneció sin cambios? | cambios no deseados |
| prueba de repetición | ¿Se puede reproducir exactamente un fracaso pasado? | no determinismo, estado omitido |

Ningún tipo reemplaza a otro. Una prueba de conservación puede pasar mientras la distribución espacial sea incorrecta, y una salida dorada puede coincidir aunque la referencia en sí sea incorrecta.

## 4. Convierta las invariantes en especificaciones ejecutables

Una invariante no debería ser simplemente una oración en la documentación; debería ser una afirmación evaluada en cada ejecución.

### Ecuación de conservación

Dado un equilibrio general

$$
M_{t+1}
=
M_t+\Delta t\,(I_t-O_t+S_t)+e_t
$$

el defecto

$$
d_t=M_{t+1}-M_t-\Delta t\,(I_t-O_t+S_t)
$$

debe permanecer dentro de la tolerancia numérica.

### Límites y positividad

Los estados con dominios restringidos, como probabilidades, concentraciones y fracciones de masa, deben satisfacer límites como

$$
0\le x_i\le 1
$$

Al mismo tiempo, compruebe si el esquema permite un pequeño subimpulso y si el recorte altera la conservación. Simplemente reemplazar los valores negativos con cero puede ocultar un error.

### Simetría y Equivarianza

Si rotar, reflejar o permutar las coordenadas de entrada debe inducir la misma transformación física en la salida, pruebe

$$
f(Tx)=Tf(x)
$$

Esta relación proporciona un oráculo sólido incluso cuando se desconocen los valores de salida correctos.

### Consistencia dimensional y relaciones de escala

Cuando un cambio de unidad expresa el mismo estado físico, las salidas adimensionales deben permanecer iguales. Primero, deduzca si la invariancia de escala realmente se cumple para la ecuación gobernante y las condiciones de contorno.

### Invariantes de máquina de estados

- No eliminar dos veces una entidad inexistente.
- No volver a procesar un evento completado.
- Los recuentos de recursos nunca se vuelven negativos.
- Las marcas de tiempo no disminuyen contra el orden causal.
- El ciclo de vida de cada entidad ID sigue únicamente transiciones de estado válidas.

## 5. Utilice tolerancias absolutas y relativas juntas

La forma básica de una comparación de punto flotante es

$$
|a-b|
\le
\mathrm{atol}
+\mathrm{rtol}\cdot s
$$

donde \(s\) es una escala de referencia adecuada al problema.

~~~python
def assert_close(actual, expected, *, atol, rtol, scale=None):
    reference_scale = abs(expected) if scale is None else abs(scale)
    error = abs(actual - expected)
    limit = atol + rtol * reference_scale
    assert error <= limit, {
        "actual": actual,
        "expected": expected,
        "error": error,
        "limit": limit,
    }
~~~

El error relativo por sí solo no se puede utilizar cuando el valor esperado es cercano a cero, mientras que el error absoluto por sí solo es difícil de interpretar para valores grandes. Una tolerancia no es un número ajustado a posteriori para aprobar una prueba; debería ser un presupuesto de error basado en:

- error de truncamiento de discretización
- tolerancia al solucionador iterativo
- límites de acumulación de punto flotante
- precisión de medición o entrada
- umbrales de decisión posteriores

## 6. Pruebas basadas en propiedades: generar propiedades, no ejemplos

Una prueba basada en ejemplos comprueba sólo los puntos en los que pensó una persona. Las pruebas basadas en propiedades generan entradas válidas y reducen un error a un contraejemplo más simple.

El siguiente es un ejemplo conceptual.

~~~python
from hypothesis import given, strategies as st

@given(
    total=st.floats(min_value=0.0, max_value=1.0e3,
                    allow_nan=False, allow_infinity=False),
    fraction=st.floats(min_value=0.0, max_value=1.0,
                       allow_nan=False, allow_infinity=False),
)
def test_partition_conserves_total(total, fraction):
    left, right = partition(total, fraction)

    assert left >= 0.0
    assert right >= 0.0
    assert_close(
        left + right,
        total,
        atol=1.0e-12,
        rtol=1.0e-12,
    )
~~~

Estos números ilustran la forma del código; no son criterios para un proyecto en particular. Establezca tolerancias reales a partir de la precisión computacional y el presupuesto de error.

### Cualidades de un buen generador

- Satisface restricciones físicamente válidas.
- Genera suficientes valores límite, ceros, valores muy pequeños y amplios rangos dinámicos.
- No genera variables correlacionadas de forma independiente.
- Separa las pruebas de entradas no válidas de las pruebas de propiedades de dominio válido.
- Guarda no sólo la semilla defectuosa sino también la entrada mínima reducida.

A diferencia de la fuzzing que simplemente arroja muchas entradas aleatorias a un programa, las pruebas basadas en propiedades establecen **lo que debe ser cierto**.

## 7. Pruebas metamórficas: conozca la relación incluso cuando se desconoce la respuesta

Para una simulación compleja, es difícil saber la salida exacta de una entrada arbitraria. En su lugar, pruebe la relación esperada entre las salidas cuando se transforma la entrada.

Por ejemplo:

- Cambiar el orden de las entidades deja sin cambios los agregados invariantes de permutación.
- Traducir el dominio y la fuente por la misma simetría traduce la salida de manera idéntica.
- Un caso límite con fuente cero alcanza un estado simple conocido.
- El total de dos subsistemas combinados independientes es igual a la suma de sus totales individuales.
- Ejecutar dos intervalos de tiempo consecutivos coincide con una ejecución ininterrumpida dentro del punto de control de error.

La relación final prueba tanto la propiedad del semigrupo como la serialización del punto de control.

$$
F_{t_2}\left(F_{t_1}(s_0)\right)
\approx
F_{t_1+t_2}(s_0).
$$

Los solucionadores adaptativos o la localización de eventos pueden tomar diferentes rutas de ejecución, por lo que se debe definir explícitamente el nivel de equivalencia requerido.

## 8. Registros mínimos necesarios para la reproducción

Reproducir una falla requiere **eventos de entrada y linaje de estado**, no simplemente registrar mensajes.

### Ejecutar manifiesto

~~~yaml
schema_version: 1
run_id: "<opaque-run-id>"
source_revision: "<commit>"
configuration_digest: "<hash>"
input_digest: "<hash>"
dependency_lock_digest: "<hash>"
random_streams:
  initialization: "<seed>"
  events: "<seed>"
execution:
  worker_count: "<count>"
  numeric_mode: "<mode>"
~~~

Reemplace los marcadores de posición con valores reales, pero no incluya secretos, rutas de usuario ni nombres de host internos.

### Registro de eventos

En un diseño de abastecimiento de eventos, proporcione a cada evento:

- un número de secuencia que aumenta monótonamente;
- tiempo de simulación y tiempo lógico;
- tipo de evento y versión del esquema;
- una carga útil canónica;
- un resumen anterior o posterior al estado; y
- un padre causal o clave de correlación.

El motor de reproducción reemplaza el I/O externo con respuestas grabadas y aplica la secuencia de eventos en el mismo orden.

### Punto de control

Repetir una tanda larga desde el principio es caro. Almacene un punto de control versionado junto con el registro de eventos posterior. El cargador de puntos de control debe probar la migración desde esquemas anteriores o fallar claramente cuando una versión no es compatible.

## 9. Errores de los hashes estatales

Un hash de estado ayuda a localizar el paso donde comienza la divergencia, pero no es confiable sin canonicalización.

- Ordenar claves de mapas.
- Corregir el formato de serialización y la versión del esquema.
- Excluir cachés transitorios y marcas de tiempo.
- Definir políticas de representación de NaN y cero firmado.
- No haga hash de flotadores después de redondearlos arbitrariamente en cadenas.

Separe un núcleo discreto que requiera igualdad bit a bit de los campos numéricos adecuados para comparaciones de tolerancia. Por ejemplo, compare exactamente el orden de los eventos y el recuento de entidades, mientras compara campos continuos con normas e invariantes.

## 10. Computación paralela y reducción reproducible

La suma de punto flotante no es exactamente asociativa.

$$
(a+b)+c\neq a+(b+c)
$$

por lo que los resultados de la reducción pueden variar según la programación del subproceso. Las opciones incluyen:

- un árbol fijo de partición y reducción
- suma por pares o compensada
- un modo de biblioteca determinista
- un acumulador exacto de totales críticos
- un criterio numéricamente equivalente en lugar de bit a bit

Se podrá permitir una reducción no determinista del rendimiento. En ese caso, utilice pruebas estadísticas o basadas en tolerancia para verificar que los resultados se mantengan dentro del sobre permitido y documente el contrato de que la repetición exacta no está disponible.

## 11. Utilice la regresión y las limas doradas de forma segura

Las pruebas de oro son útiles para detectar cambios en las API, los formatos y las trayectorias representativas, pero requieren estos principios.

1. Controle también la versión del procedimiento de generación dorada.
2. Durante la aprobación, presente un resumen legible por humanos de la diferencia.
3. Prefiera cantidades clave de interés e invariantes a un binario grande completo.
4. Especificar tolerancias y pedidos.
5. Separe las actualizaciones de referencias de la ejecución de pruebas ordinarias.
6. No confíe en las pruebas de oro sin pruebas analíticas o invariantes.

"Sobrescribir automáticamente el archivo de referencia con la nueva salida" desactiva las pruebas de regresión.

## 12. Un flujo de trabajo que convierte los fracasos en activos

1. Detectar una falla en producción o una prueba generativa.
2. Conserve la revisión de origen, el manifiesto, la entrada mínima, el registro de eventos y el punto de control.
3. Confirme que la repetición reproduce el error.
4. Encuentre el primer resumen de estado en el que comienza la divergencia.
5. Agregue la invariante o prueba de propiedad más pequeña que explique la causa.
6. Después de la corrección, pase tanto la nueva prueba como la suite existente.
7. Conserve el caso mínimo en el corpus del contraejemplo.
8. Si el no determinismo en sí mismo causó la falla, agregue una prueba separada de programación repetida.

## 13. Lista de verificación de verificación

- [ ] ¿Se distinguieron determinismo, reproducibilidad y corrección?
- [ ] ¿Se registraron las entradas ocultas y el entorno de ejecución además de la semilla?
- [] ¿Las transmisiones aleatorias estaban separadas por subsistema?
- [] ¿Las ecuaciones de conservación críticas y los límites son afirmaciones o pruebas de tiempo de ejecución?
- [] ¿El generador de propiedades maneja restricciones físicas y valores límite?
- [ ] ¿Se derivaron relaciones metamórficas de reglas rectoras?
- [ ] ¿Las tolerancias tienen justificación numérica y unidades?
- [ ] ¿Se separaron los objetivos de comparación exactos y aproximados?
- [ ] ¿Se guardaron los insumos reducidos y las semillas de cada falla?
- [] ¿Están versionados los esquemas de eventos y puntos de control?
- [] ¿Se arregló o grabó el I/O externo durante la reproducción?
- [ ] ¿Es explícito el contrato de determinismo para la reducción paralela?
- [] ¿Se impide que las actualizaciones doradas se ejecuten automáticamente sin revisión?

## 14. Errores y limitaciones

### Una propiedad incorrecta hace que el código correcto falle

La monotonicidad, la simetría y la positividad pueden fallar según el modelo, las condiciones de contorno o el esquema numérico. Derive propiedades de la especificación y ecuaciones, no de la intuición.

### La reproducción exacta no es posible en todas las plataformas

Diferentes compiladores, conjuntos de instrucciones, funciones trascendentales y programación GPU pueden cambiar los resultados bit a bit. Definir niveles de reproducibilidad admitidos es más realista.

- Nivel A: igualdad bit a bit en binario y hardware idénticos
- Nivel B: tolerancia numérica en la misma arquitectura
- Nivel C: equivalencia de cantidades de interés e invariantes entre plataformas

### Registrar todo el estado aumenta los costos y la exposición de la información

Combine registros de eventos, puntos de control periódicos y resúmenes de estado con políticas de retención y redacción. Evite que secretos o datos personales entren en cargas útiles a nivel de esquema.

### El modo determinista puede diferir de la ruta de producción real

Un modo de subproceso único de solo prueba puede pasar mientras la ruta paralela de producción permanece sin verificar. Compare el modo de referencia determinista y el modo de ejecución real con pruebas diferenciales.

## Conclusión

Las pruebas de simulación sólidas no memorizan valores de salida particulares. Codifican **lo que nunca debe romperse**, **qué relaciones deben mantenerse cuando las entradas cambian** y **cómo reiniciar una falla desde el mismo estado**.

Las invariantes convierten la física y el conocimiento del dominio en especificaciones ejecutables, las pruebas basadas en propiedades descubren entradas que la gente pasó por alto y la repetición transforma una falla accidental única en un activo de regresión permanente.
