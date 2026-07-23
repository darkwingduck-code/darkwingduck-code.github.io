---
title: "V&V para resultados numéricos confiables: convergencia, malla e independencia de pasos de tiempo, y conservación"
date: 2026-07-21 09:20:00 +0900
categories: [Scientific Computing, Verification and Validation]
tags: [verification, validation, convergence, mesh-independence, time-step, conservation, numerical-error]
description: Un procedimiento práctico para distinguir la verificación de código, la verificación de soluciones y la validación experimental, y luego evaluar la confiabilidad de los resultados numéricos a través de la convergencia, la malla y la independencia de pasos de tiempo, y la conservación.
math: true
lang: es
translation_key: numerical-verification-validation-convergence
hidden: true
---

{% include language-switcher.html %}

Un contorno plausible y una curva suave no son evidencia de exactitud. Para que una simulación numérica sea confiable, al menos las siguientes preguntas deben considerarse por separado.

- ¿El código resuelve las ecuaciones correctamente?
- ¿Son suficientemente pequeños los errores de discretización y de iteración en este cálculo?
- ¿Las ecuaciones y los insumos elegidos explican adecuadamente las cantidades de interés en la realidad?
- ¿Es válida esta conclusión dentro del uso previsto y el error permitido?

Si estas preguntas se agrupan bajo la sola palabra “verificación”, resulta imposible saber qué se ha verificado y qué queda. Por eso se distinguen verificación y validación.

## 1. El límite entre verificación y validación

| Nivel | Pregunta central | Pruebas típicas |
|---|---|---|
| verificación de código | ¿Se implementaron las ecuaciones según lo previsto? | solución exacta, solución fabricada, punto de referencia, prueba unitaria |
| verificación de solución | ¿Qué tan grande es el error numérico en el cálculo actual? | convergencia iterativa, refinamiento de malla/paso de tiempo, estimación de error |
| validación | ¿El modelo reproduce adecuadamente cantidades de interés del mundo real para su propósito? | comparación con mediciones independientes, incertidumbre de validación, aplicabilidad |
| calibración | ¿Se estimaron los parámetros desconocidos a partir de los datos? | objetivo/probabilidad, posterior, identificabilidad |

En resumen, la verificación está cerca de preguntar "¿estamos resolviendo correctamente las ecuaciones?" mientras que la validación pregunta "¿estamos resolviendo las ecuaciones correctas?" Sin embargo, la validación no prueba que un modelo sea absolutamente cierto. Acumula **evidencia de un uso específico previsto, rango de condiciones y cantidad de interés**.

Usar los mismos datos para la calibración y validación equivale a pedirle al modelo que se ajuste a los datos que ya ha visto. Sepárelos siempre que sea posible; Si los datos limitados requieren reutilización, indique explícitamente que el resultado no es una validación independiente.

## 2. Descomponga el error primero

La diferencia entre un resultado computacional y la realidad combina varias causas.

$$
\text{total discrepancy}
=
\text{model-form error}
+\text{parameter/input uncertainty}
+\text{discretization error}
+\text{iterative error}
+\text{implementation error}
+\text{measurement error}.
$$

Esta ecuación no es un modelo probabilístico riguroso en el que cada término sea simplemente aditivo e independiente; es una descomposición conceptual destinada a evitar que se pasen por alto las causas. Las causas pueden interactuar entre sí y es posible que no sean completamente separables de las observaciones únicamente.

Un buen plan de V&V define primero la cantidad de interés (QoI). En lugar de referirse a todo el campo, indique qué promedio, máximo, integral, tiempo de llegada o flujo límite se utilizará en la toma de decisiones. Los resultados de validación y convergencia de malla pueden diferir según la QoI.

## 3. Verificación de código: la etapa para encontrar errores de implementación

### Soluciones exactas y puntos de referencia

Cuando existe una solución analítica para condiciones de contorno o geometría simplificadas, el error computacional se puede comparar directamente. Incluso si difiere de un caso de producción complejo, es valioso para aislar y probar la implementación de operadores, condiciones de contorno y términos fuente.

### Método de soluciones fabricadas

Primero elija una función suave deseada \(u_m(x,t)\), luego sustitúyala en el operador de la ecuación gobernante \(\mathcal L\) para construir la fuente

$$
f_m=\mathcal L(u_m)
$$

Si el código está configurado para resolver

$$
\mathcal L(u)=f_m
$$

la respuesta conocida \(u_m\) se puede utilizar para probar el operador interior, las condiciones de contorno, la integración temporal y el orden observado juntos.

Una solución fabricada no tiene por qué representar un fenómeno real. En cambio, debería satisfacer las siguientes condiciones.

- Activa todos los términos principales en la ruta del código.
- No enmascara los insectos mediante una simetría excesiva.
- Tiene la diferenciabilidad requerida.
- Sus condiciones de contorno y fuente se derivan de manera consistente.

### Implementaciones independientes y casos límite

Diferentes códigos que producen la misma respuesta son pruebas útiles, pero pueden compartir suposiciones o errores comunes. Combine este resultado con otros tipos de evidencia, como límites en los que un término se aproxima a cero, simetría, análisis dimensional y leyes de conservación.

## 4. Verificación de la solución: error numérico en el cálculo actual

### Separar el error iterativo del error de discretización

Cambiar la malla antes de que un solucionador lineal o no lineal haya convergido lo suficiente mezcla el error iterativo con el error de discretización. En cada malla, haga que la tolerancia residual sea suficientemente menor que la diferencia de discretización y verifique la estabilidad del QoI y del residual.

Una disminución del residuo algebraico no garantiza necesariamente una disminución del error de solución. En un sistema mal acondicionado puede coexistir un pequeño error residual y un gran error de solución.

### El rango de convergencia asintótica

Si el espaciado de la malla es \(h\) y el orden teórico es \(p\), entonces en un rango suficientemente fino se espera

$$
\phi(h)=\phi_0+Ch^p+\mathcal O(h^{p+1})
$$

donde \(\phi\) es una QoI. Cuando la relación de refinamiento es constante y

$$
h_3=rh_2=r^2h_1,\qquad r>1
$$

con \(h_1\) el espaciado más fino, el orden observado se puede estimar como

$$
p_{\mathrm{obs}}
=
\frac{
\ln\left|
(\phi_3-\phi_2)/(\phi_2-\phi_1)
\right|
}{
\ln r
}
$$

Si la secuencia está en el rango asintótico y converge monótonamente, la extrapolación de Richardson da

$$
\phi_{\mathrm{ext}}
=
\phi_1+
\frac{\phi_1-\phi_2}{r^{p_{\mathrm{obs}}}-1}
$$

Esta fórmula se vuelve inestable si los tres valores convergen oscilacionalmente o si sus diferencias están en el nivel de ruido. En lugar de informar incondicionalmente un único orden aparente, primero informe el patrón de convergencia y si se cumplen los supuestos.

## 5. Por qué la frase "independiente de malla" requiere precaución

El error de discretización rara vez es exactamente cero en una malla finita. Por lo tanto, es mejor informar los siguientes detalles en lugar de simplemente afirmar “independencia”.

- La familia de refinamiento y la característica \(h\) utilizada
- Relación de refinamiento
- Escala de celda/DOF de cada malla
- Calidad de malla y resolución de capa límite.
- Valores y cambios relativos para cada QoI
- Orden observado o estimación de error.
- Criterio de aceptación utilizado para seleccionar la malla final.

El mero hecho de que los valores de dos mallas sean similares es insuficiente. Puede haber una cancelación accidental de errores, una convergencia no monótona o el mismo cuello de botella en la resolución. Cuando sea posible, utilice al menos tres niveles y verifique que las mallas formen una familia de refinamiento sistemática que comparta una topología y una regla de estiramiento.

### Las cantidades locales e integrales convergen de manera diferente

Un flujo integral o promedio de dominio puede ser estable mientras que una ubicación de punto máximo, gradiente o discontinuidad converge lentamente. Realice el estudio de malla por separado para cada QoI que se informará. Si la "ubicación máxima" se mueve entre mallas, no compare directamente los valores en el mismo índice de celda.

## 6. Independencia de pasos de tiempo y acoplamiento de errores espaciales y Temporal

También se puede realizar un estudio de refinamiento para el paso de tiempo \(\Delta t\) en el formulario

$$
\phi(\Delta t)=\phi_0+C_t(\Delta t)^q+\cdots
$$

Sin embargo, si el error espacial es grande, reducir el paso del tiempo puede no producir ningún cambio visible, y lo contrario también es cierto.

Una secuencia práctica es la siguiente.

1. Evalúe el refinamiento espacial utilizando un \(\Delta t\) suficientemente pequeño.
2. Evalúe el refinamiento \(\Delta t\) en la malla fina seleccionada.
3. Alrededor de la combinación final, varíe la malla y \(\Delta t\) juntos para comprobar su interacción.
4. Con pasos de tiempo adaptables, tolerancias de registro, historial de pasos aceptados y pasos rechazados en lugar de un único paso nominal.

Satisfacer una condición de estabilidad es diferente a lograr una precisión suficiente. El hecho de que un método implícito no diverja en un paso de tiempo grande no significa que haya resuelto con precisión la fase transitoria y el tiempo pico.

## 7. Conservación: evidencia sólida independiente de una trama de convergencia

Para un volumen de control \(\Omega\) en un problema conservador, un equilibrio general es

$$
\frac{d}{dt}\int_{\Omega}U\,d\Omega
+
\int_{\partial\Omega}F\cdot n\,dS
=
\int_{\Omega}S\,d\Omega
$$

Para un cálculo discreto durante un intervalo de tiempo fijo, calcule

$$
\Delta \text{storage}
+\text{net outflow}
-\text{source}
=
\text{balance defect}
$$

Informar sólo el defecto absoluto hace que sea difícil comparar casos de diferentes escalas. Examine también un error de equilibrio normalizado dividido por un flujo representativo o un cambio de almacenamiento. Sin embargo, si el denominador está cerca de cero, el error relativo explota, así que presente el valor absoluto y la escala juntos.

La conservación es una condición necesaria, no suficiente. La conservación global aún puede mantenerse cuando el mismo total se distribuye incorrectamente entre diferentes lugares. Por tanto, distinga los siguientes niveles.

- Equilibrio celular local
- Equilibrio de flujo por límite
- Saldo de dominio global
- Equilibrio por especie o por componente
- Equilibrios acoplados como energía, masa y momento.

## 8. Cómo diseñar comparaciones de validación

### Definir métricas de validación por adelantado

No mires una trama y juzgues que es “similar”; defina primero la QoI y la métrica. Los ejemplos incluyen:

- Sesgo y error normalizado.
- Norma de perfil
- Magnitud y ubicación del pico
- Cantidad integral
- Error de fase Temporal
- Cobertura o puntuación probabilística

### Combinar incertidumbres

Al interpretar la diferencia simulación-medición

$$
E=S-D
$$

considere la incertidumbre numérica de la simulación, la incertidumbre de entrada y la incertidumbre de medición juntas. Un pequeño \(|E|\) por sí solo no prueba que el modelo sea correcto; También determine si una banda de incertidumbre muy amplia simplemente oscurece la diferencia.

### Indique el dominio de validación

La extrapolación fuera del rango de condiciones validadas debilita la evidencia. Registre el espacio de entrada, el régimen de límites, los grupos adimensionales y los rangos de material/estado, y evalúe qué tan lejos se encuentra el punto de predicción del dominio de validación.

## 9. Flujo de trabajo de V&V recomendado

1. **Defina el uso previsto y el error permitido**: indique qué QoI informarán qué decisiones.
2. **Construir la jerarquía del modelo**: Distinguir ecuaciones rectoras, cierres, condiciones iniciales y de contorno, y fuentes de parámetros.
3. **Verificación de código**: Pruebe la implementación con pruebas unitarias, soluciones exactas o MMS, casos límite y puntos de referencia.
4. **Convergencia iterativa**: examine los residuos de ecuaciones y los historiales de QoI juntos.
5. **Refinamiento espacial**: compare al menos tres niveles en una familia de mallas sistemática.
6. **Temporal refinamiento**: incluya QoI temporales, fases y tiempos pico.
7. **Comprobaciones de conservación**: Calcula automáticamente los saldos locales, de límites y globales.
8. **Propagar la incertidumbre de entrada**: Refleja la incertidumbre de entrada en la comparación de validación.
9. **Validación independiente**: compare con datos no utilizados para la calibración con métricas predefinidas.
10. **Registre el rango de aplicabilidad y las limitaciones**: Identifique los regímenes no validados y las incertidumbres dominantes.

## 10. Lista de verificación de verificación

- [ ] ¿Se ha distinguido verificación, validación y calibración?
- [ ] ¿Se definieron primero las QoI y las tolerancias utilizadas en la toma de decisiones?
- [ ] ¿La prueba analítica/MMS activa los términos principales del código de producción?
- [] ¿Es el error iterativo suficientemente menor que las diferencias entre mallas?
- [ ] ¿Se utilizaron al menos tres niveles de refinamiento sistemático?
- [ ] ¿Se verificó el orden observado además del orden teórico?
- [ ] ¿Se distinguieron la convergencia monótona, oscilatoria y divergente?
- [ ] ¿Se realizaron el refinamiento espacial y temporal por separado?
- [ ] ¿Se verificó la conservación local y de límites además de la conservación global?
- [ ] ¿Se separaron los datos de calibración y validación?
- [ ] ¿Se informaron juntas la medición, la entrada y la incertidumbre numérica?
- [ ] ¿Se identificó una extrapolación fuera del dominio de validación?

## 11. Errores comunes

### Concluir que un pequeño residuo significa que la respuesta es correcta

Un residual indica únicamente qué tan bien se han resuelto las ecuaciones algebraicas discretas; no revela ni error de discretización ni error de forma del modelo.

### Comparando sólo dos mallas y declarando la independencia

La concordancia accidental entre dos valores no establece un orden de convergencia ni un rango asintótico. Se necesitan al menos tres niveles y el patrón de convergencia.

### Evaluación de cada campo con una métrica

Incluso si la media concuerda bien, el pico, el gradiente o la fase pueden estar equivocados. Se necesitan múltiples QoI adecuadas al propósito previsto.

### Informar el rendimiento de calibración como rendimiento de validación

Ajustar a los datos utilizados para ajustar los parámetros es un resultado de calibración. Se necesita información independiente para evaluar la adecuación predictiva.

### Suponiendo que una malla más fina siempre es más precisa

Con condiciones de contorno incorrectas, una tolerancia iterativa floja, una calidad de malla deficiente o un esquema inestable, aumentar DOF por sí solo no garantiza la precisión.

## 12. Limitaciones y principios de presentación de informes

En problemas complejos no lineales y de múltiples escalas, puede resultar imposible alcanzar un rango asintótico limpio. Las discontinuidades, las interfaces en movimiento, la dinámica caótica y las mallas adaptativas debilitan los supuestos del análisis simple de Richardson. En tales casos, en lugar de forzar una única estimación del “error exacto”, informe de manera transparente qué tan estable es la conclusión en múltiples resoluciones, qué fuente de error domina y qué no se pudo verificar.

El producto de V&V no es un sello de pase. Es **una red de evidencia que respalda una conclusión**. Esta es la razón por la que las tolerancias del solucionador, las familias de refinamiento, los defectos de equilibrio, las incertidumbres y los rangos de aplicabilidad importan más que los gráficos.
