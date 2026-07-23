---
title: "De DOE a UQ y calibración: un mapa completo para el diseño de estudios de simulación"
date: 2026-07-21 09:30:00 +0900
categories: [Scientific Computing, Research Methods]
tags: [doe, sensitivity-analysis, uncertainty-quantification, calibration, identifiability, surrogate-model]
description: "Distinga el diseño de experimentos, la sensibilidad local y global, la propagación de la incertidumbre y la calibración de parámetros, y luego conéctelos en un flujo de trabajo de estudio de simulación reproducible."
math: true
lang: es
translation_key: doe-sensitivity-uq-calibration
hidden: true
---

{% include language-switcher.html %}

Cambiar algunos datos de la simulación y comparar las curvas de producción no es suficiente para sustentar conclusiones sólidas. Los efectos variables, las interacciones, la incertidumbre de los insumos, la estimación de parámetros y el error del modelo se entrelazan.

Para separarlas, primero distinguimos las funciones de cuatro herramientas.

- **Diseño de experimentos (DOE)**: decide qué combinaciones de entradas calcular o medir.
- **Análisis de sensibilidad (SA)**: pregunta qué parte de la variación de salida se explica por cada entrada.
- **Cuantificación de la incertidumbre (UQ)**: pregunta cómo la incertidumbre en las entradas y los modelos se propaga a la incertidumbre de la salida.
- **Calibración**: utiliza observaciones para estimar parámetros desconocidos.

Se complementan pero no se sustituyen. Un buen DOE no cuantifica automáticamente la incertidumbre y un buen ajuste de calibración no significa que la validación esté completa.

## 1. La primera tabla a construir: clasificación de insumos e incertidumbre

No trate todas las entradas \(x=(x_1,\dots,x_d)\) como del mismo tipo.

| Clase | Significado | Tratamiento típico |
|---|---|---|
| factor controlable | El diseñador selecciona sus niveles | diseño factorial óptimo |
| variable de escenario/contexto | Tiene una gama de intereses pero no está controlado directamente | bloqueo, estratificación |
| variable aleatoria | Modelado como variación inherente | distribución de probabilidad y propagación directa |
| parámetro epistémico | Incierto debido a conocimientos insuficientes | calibración, intervalo/actualización previa |
| parámetro molesto | No es de interés en sí mismo pero afecta a los resultados | marginación, elaboración de perfiles |
| discrepancia del modelo | Donde la estructura de la ecuación difiere de la realidad | modelo de discrepancia separado o presupuesto sesgado |

Incluso una misma cantidad física puede clasificarse de forma diferente según el objetivo. Más importante que su nombre es decidir de antemano **qué información se utilizará para actualizarlo y cómo**.

Cada entrada necesita al menos los siguientes metadatos:

- definición y unidades
- rango permitido y su justificación
- niveles de distribución o diseño
- correlaciones y limitaciones entre entradas
- si es fijo o estimado
- si es mensurable
- donde entra el modelo

## 2. DOE: convertir un presupuesto de ejecución en información

### Limitaciones de un factor a la vez

OFAT, que cambia una variable a la vez, es fácil de entender pero omite interacciones. Por ejemplo,

$$
y=\beta_0+\beta_1x_1+\beta_2x_2+\beta_{12}x_1x_2
$$

cuando \(\beta_{12}\) es grande, el efecto de \(x_1\) cambia con el nivel de \(x_2\). OFAT alrededor de un único punto de referencia hace que esta estructura sea difícil de identificar.

### Tipos de diseño y objetivos

| Diseño | Ventaja | Precaución |
|---|---|---|
| factorial completo | Estima sistemáticamente los principales efectos e interacciones | El recuento de ejecuciones se dispara a medida que crece la dimensión |
| factorial fraccional | Cribas con menos tiradas | Se debe interpretar la estructura del alias |
| compuesto central / Caja–Behnken | Eficiente para una superficie de respuesta cuadrática | Vulnerable a la extrapolación fuera de la región especificada |
| Hipercubo latino | Estratifica uniformemente cada eje | Comprobar la calidad y correlación de las proyecciones |
| secuencia de baja discrepancia | Muy adecuado para la integración y SA global | Distinguirlo de réplicas aleatorias independientes |
| D-/I-Diseño óptimo | Optimizado para el objetivo de un modelo de regresión particular | La eficiencia cae si el modelo supuesto es incorrecto |
| diseño adaptativo/secuencial | Concentra el presupuesto en regiones inciertas o importantes | Gestionar la regla de detención y el sesgo de selección |

DOE no significa sólo “llenar el espacio de manera uniforme”. Un buen diseño depende de si el objetivo es la detección, el entrenamiento de sustitutos, la optimización, la identificación de parámetros o la validación.

### Aleatorización, replicación y bloqueo

- **La aleatorización** reduce la posibilidad de que la deriva del tiempo o los efectos del orden se confundan con un factor en particular.
- **Replicación** estima la variación en condiciones idénticas. Para un simulador totalmente determinista, la simple repetición con el mismo binario y entorno no proporciona información nueva, pero la replicación es necesaria para un solucionador estocástico o una ejecución no determinista.
- **El bloqueo** separa variaciones molestas que son difíciles de eliminar, como equipo, lote, fecha o familia de malla.

Incluso en una campaña de simulación, el orden de ejecución, el entorno informático y la versión del solucionador pueden ser variables de bloque o de procedencia.

## 3. Análisis de sensibilidad: elija primero la definición de influencia

La “variable más importante” cambia con la métrica.

### Sensibilidad local

La derivada alrededor de un punto de referencia \(x_0\),

$$
S_i^{\mathrm{local}}
=
\left.
\frac{\partial f}{\partial x_i}
\right|_{x=x_0}
$$

describe el efecto de una pequeña perturbación. Cuando las unidades difieren, considere un índice adimensional como

$$
S_i^{\mathrm{scaled}}
=
\frac{x_i}{f}
\frac{\partial f}{\partial x_i}
$$

Las derivadas locales son eficientes para la optimización basada en gradientes y la incertidumbre linealizada, pero pueden pasar por alto la no linealidad, los umbrales, las interacciones y la dependencia del punto de referencia.

### Proyección: la familia Morris

Cuando se recopilan los efectos elementales obtenidos al mover cada entrada una vez en varias ubicaciones, su valor absoluto medio indica una influencia general, mientras que su varianza indica una posible no linealidad o interacciones. Esto es útil para filtrar variables sin importancia en dimensiones altas, pero no es una descomposición de varianza exacta.

### Sensibilidad global basada en la varianza

Suponiendo entradas independientes, la variación de la salida se puede descomponer en la forma ANOVA.

$$
\operatorname{Var}(Y)
=
\sum_i V_i
+\sum_{i<j}V_{ij}
+\cdots
$$

El índice de Sobol de primer orden y el índice de efecto total se pueden escribir como

$$
S_i=\frac{V_i}{\operatorname{Var}(Y)},
\qquad
S_{T_i}
=
1-
\frac{
\operatorname{Var}_{X_{\sim i}}
\left(
\mathbb E[Y\mid X_{\sim i}]
\right)
}{
\operatorname{Var}(Y)
}
$$

\(S_i\) es el efecto de \(X_i\) solo, mientras que \(S_{T_i}\) incluye todas las interacciones que involucran a \(X_i\). Un \(S_{T_i}-S_i\) grande indica que las interacciones son importantes.

### La trampa de las entradas correlacionadas

La descomposición estándar de Sobol supone entradas independientes. Si las combinaciones de entradas físicamente viables tienen correlaciones o restricciones, el muestreo independiente puede crear estados imposibles. En este caso, considere métodos que respeten la estructura de dependencia, como el muestreo condicional, los índices agrupados y los efectos de Shapley, y establezca la distribución conjunta utilizada.

## 4. UQ: propagar la incertidumbre en una distribución de salida

El problema básico de UQ directo es estimar la distribución, la media, la varianza, los cuantiles y la probabilidad de falla de \(Y\) en

$$
X\sim p_X(x),\qquad Y=f(X)
$$

### Montecarlo

Genere muestras independientes \(x^{(j)}\) y calcule \(y^{(j)}=f(x^{(j)})\). Este enfoque es relativamente insensible a la dimensión y simple de implementar, pero costoso para eventos raros o simulaciones costosas. Informe el error estándar de Monte Carlo o el intervalo de confianza junto con el recuento de la muestra.

### UQ basado en sustituto

Cuando el modelo original es caro, utilice una superficie de respuesta, un proceso gaussiano, un caos polinomial, un sustituto neuronal o un modelo similar. Luego, el error total se separa en al menos los siguientes términos.

$$
\text{UQ error}
=
\text{sampling error}
+\text{surrogate error}
+\text{input-model error}
+\text{simulation numerical error}.
$$

Un pequeño error en la prueba sustituta por sí solo no garantiza probabilidades de cola o índices de sensibilidad precisos. Examine por separado el error en regiones importantes para el objetivo UQ, especialmente cerca de límites, colas y restricciones.

### Eventos raros

Cuando la probabilidad de falla es pequeña, el Monte Carlo crudo casi no produce muestras de falla. Es posible que se necesiten métodos como el muestreo de importancia, la simulación de subconjuntos, la división o los sustitutos adaptativos. Si la propuesta se ajustó arbitrariamente después de observar los resultados, inspeccione el sesgo del estimador y los cálculos de ponderación.

## 5. Calibración: estimación de parámetros como problema inverso

Dadas las observaciones \(d\), el simulador \(f(\theta,z)\), el parámetro \(\theta\) y las condiciones de observación \(z\), escriba

$$
d=f(\theta,z)+\delta(z)+\varepsilon
$$

- \(\delta(z)\): discrepancia de modelo
- \(\varepsilon\): ruido de medición

### Perspectiva de optimización

Los mínimos cuadrados ponderados se expresan como

$$
\hat\theta
=
\arg\min_\theta
(d-f(\theta))^\mathsf T
\Sigma^{-1}
(d-f(\theta))
$$

Podrán añadirse límites, regularización o penalización previa.

### Perspectiva bayesiana

$$
p(\theta\mid d)
\propto
p(d\mid\theta)p(\theta)
$$

Aquí la probabilidad representa la estructura residual de la medición y el modelo, mientras que la probabilidad representa la información disponible antes de la observación. El resultado es una distribución posterior, no una estimación puntual única.

Los métodos bayesianos no proporcionan automáticamente una incertidumbre correcta cuando el modelo de probabilidad o discrepancia es incorrecto. Un posterior estrecho significa que la información se concentra bajo los supuestos del modelo; no significa que cada error en la realidad sea pequeño.

## 6. Identificabilidad: el éxito de la optimización difiere del aprendizaje de parámetros

### Identificabilidad estructural

Si diferentes parámetros producen el mismo resultado incluso bajo el supuesto de cero ruido y observaciones continuas, los parámetros son estructuralmente no identificables.

### Identificabilidad práctica

Incluso los parámetros teóricamente identificables son difíciles de distinguir de los datos reales cuando las ubicaciones de observación, los rangos, el ruido o la excitación de entrada son inadecuados.

Los siguientes diagnósticos son útiles:

- espectro singular de la información jacobiana o de Fisher
- probabilidad del perfil de parámetros
- correlación posterior
- optimización a partir de múltiples valores iniciales
- prueba de recuperación sintética
- información esperada bajo nuevas condiciones de observación

Cuando los parámetros están fuertemente correlacionados, los valores individuales pueden ser inestables incluso aunque una combinación o predicción particular sea estable. Distinguir si el objetivo son los propios parámetros o la predicción.

## 7. Confusión entre la discrepancia del modelo y los parámetros

Si se ignora el error de estructura del modelo \(\delta(z)\), los parámetros pueden absorber ese error. Estos “parámetros efectivos” se ajustan bien a las condiciones de calibración, pero pueden perder su significado físico o poder predictivo en nuevas condiciones.

Por el contrario, si se permite un modelo de discrepancia altamente flexible, \(\delta\) puede explicar cualquier discrepancia e impedir el aprendizaje de los parámetros. Un problema que estima libremente los parámetros y la discrepancia al mismo tiempo puede generar confusión inherente.

Las estrategias de mitigación incluyen:

- incluir diversas condiciones y tipos de observación
- diseñar QoI sensibles a cada parámetro
- utilizar prioridades y límites físicamente justificados
- limitar la suavidad y la estructura de la discrepancia
- condiciones de calibración y validación separadas
- informar la incertidumbre de los parámetros y la discrepancia predictiva por separado

## 8. Un flujo de trabajo de un extremo a otro recomendado

### Paso 1: Definir el objetivo y los resultados

Primero corrija la decisión, la QoI, el error aceptable y el rango de interés de entrada. En lugar de decir "se ajusta bien al modelo", indique qué predicciones se respaldarán y en qué rango.

### Paso 2: Auditoría de entrada

Construya una tabla de unidades de entrada, rangos, distribuciones conjuntas, restricciones físicas y fuentes de información. Distinga la incertidumbre epistémica de la aleatoria, pero cuando el límite es ambiguo, trate las interpretaciones múltiples como escenarios.

### Paso 3: Detección DOE

Cuando la dimensión es alta, filtre las variables de bajo impacto con diseños factoriales/fraccionales, métodos de Morris, selección de derivadas o herramientas similares. Registre el umbral de detección y cualquier interacción que pueda pasarse por alto.

### Paso 4: Llenado de espacio o dirigido a objetivos DOE

Elija LHS, una secuencia de baja discrepancia o un diseño óptimo según el objetivo: modelado sustituto, SA global o calibración. Excluya combinaciones físicamente imposibles mediante un muestreo consciente de restricciones.

### Paso 5: Control de calidad numérico

Registre la convergencia, la conservación, el código de falla y la procedencia de la malla/paso de tiempo de cada ejecución. Simplemente eliminar los fallos del solucionador puede distorsionar la región factible estimada, por lo que se debe gestionar el fallo en sí como resultado.

### Paso 6: Validación sustituta

Utilice un diseño de prueba independiente del entrenamiento. Verifique no solo el error promedio sino también la peor región, colas, derivadas y la región en la que se concentrará la calibración posterior.

### Paso 7: SA global y directo UQ

Establezca el modelo de entrada conjunto y calcule también la incertidumbre de Monte Carlo de los índices de sensibilidad. Compruebe si las clasificaciones de importancia de los insumos son estables con respecto al tamaño de la muestra y la elección del sustituto.

### Paso 8: Calibración

Registre la probabilidad, el previo, los límites, los supuestos de discrepancia y los diagnósticos del optimizador/muestreador. Verifique la identificabilidad mediante recuperación sintética y ejecuciones de inicio múltiple.

### Paso 9: Validación

Compare las observaciones con la distribución predictiva en condiciones y QoI que no se utilizaron. Evalúe la predicción fuera de la muestra en lugar de los residuos de calibración.

### Paso 10: Actualización secuencial

Seleccione la siguiente ejecución o medición que reducirá al máximo la incertidumbre actual. Defina la regla de adquisición y el criterio de parada de antemano para evitar una exploración interminable.

## 9. Lista de verificación de verificación

- [] ¿Se mantienen distintos los objetivos de DOE, sensibilidad, UQ y calibración?
- [ ] ¿Tienen justificación técnica los rangos y distribuciones de entrada?
- [ ] ¿Se reflejan las correlaciones y las limitaciones físicas en el muestreo conjunto?
- [ ] ¿Se evitó OFAT como única base para concluir que no existen interacciones?
- [] ¿La replicación está diseñada apropiadamente para un comportamiento determinista o estocástico?
- [ ] ¿Se establecen la definición y los supuestos de la métrica de sensibilidad?
- [ ] ¿Se informa la incertidumbre muestral del propio índice de sensibilidad?
- [] ¿El error sustituto se incluye en los resultados de UQ o se cuantifica por separado?
- [ ] ¿Se ha diagnosticado la identificabilidad de los parámetros de calibración?
- [ ] ¿Se examinó la posibilidad de que la discrepancia del modelo sea absorbida por los parámetros?
- [ ] ¿Están separados los datos de calibración y validación?
- [] ¿Se conservan la semilla aleatoria, el generador de diseño, el orden de ejecución y las ejecuciones fallidas?

## 10. Errores y limitaciones comunes

### La idea errónea de que los rangos más amplios son siempre más conservadores

Una distribución uniforme e independiente injustificadamente amplia puede crear combinaciones que son imposibles en la realidad y cambiar artificialmente las clasificaciones de sensibilidad. Un rango debería reflejar tanto la viabilidad conjunta como el conservadurismo.

### La idea errónea de que un coeficiente de correlación captura toda la estructura de dependencia

La correlación lineal puede no describir la dependencia de la cola, las restricciones no lineales o la multimodalidad.

### Confiar solo en el puntaje promedio de la prueba de la madre sustituta

Un RMSE global pequeño no garantiza precisión alrededor de un umbral, en las colas o en los gradientes. Las métricas de validación deben coincidir con la tarea posterior.

### Interpretar un parámetro posterior como una constante física

Un parámetro de calibración obtenido ignorando la discrepancia del modelo puede ser un valor de corrección dependiente de la condición.

### Eliminando todas las variables insensibles

Una variable es insensible sólo para la salida y el rango actuales; eso no garantiza que no sea importante para otro QoI, régimen o evento de cola.

### Dimensión excesiva con un presupuesto informático pequeño

Realizar SA global de alta dimensión y una calibración flexible simultáneamente con pocas ejecuciones hace que los estimadores sean inestables. Lo primero debe ser el cribado, la reducción de las dimensiones estructurales y las mediciones informativas.

## Conclusión

Un estudio de simulación sólido no surge de una gran cantidad de ejecuciones sino de **ejecuciones con flujos de información separados**. DOE determina dónde buscar, el análisis de sensibilidad explica lo que importa, UQ calcula la amplitud de la conclusión y la calibración actualiza los parámetros desconocidos con observaciones.

Finalmente, la validación pregunta si las predicciones bajo todos estos supuestos siguen siendo adecuadas para su propósito cuando se enfrentan a nueva información. Simplemente separar las preguntas y los datos de estas cuatro etapas reduce en gran medida el sobreajuste, la precisión falsa y los parámetros no interpretables.
