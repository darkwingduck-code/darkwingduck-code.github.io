---
title: "Uso correcto de mínimos cuadrados: proyección, condicionamiento, QR y SVD"
date: 2026-07-21 09:10:00 +0900
categories: [Mathematics, Numerical Linear Algebra]
tags: [least-squares, projection, conditioning, qr, svd, pseudoinverse, regularization]
description: "Interprete los mínimos cuadrados como un problema de proyección ortogonal y conecte números de condición, QR, SVD, pseudoinversos y regularización desde la perspectiva de la estabilidad numérica."
math: true
lang: es
translation_key: least-squares-projection-conditioning-svd
hidden: true
---

{% include language-switcher.html %}

Cuando la ecuación de observación \(Ax=b\) no se puede resolver exactamente, a menudo se nos enseña a "multiplicar ambos lados por \(A^\mathsf T\)". Pero la esencia de los mínimos cuadrados no es memorizar una fórmula; se basa en tres preguntas.

1. ¿Qué estamos minimizando?
2. ¿Por qué la solución está relacionada con la proyección ortogonal sobre el espacio de la columna?
3. ¿Qué algoritmo calculará la misma solución matemática de manera estable?

Este artículo organiza la geometría de mínimos cuadrados, el peligro de las ecuaciones normales, las funciones de QR y SVD, la deficiencia de rango y la regularización en una progresión coherente.

## 1. Definición del problema de mínimos cuadrados

Para \(A\in\mathbb R^{m\times n}\) y \(b\in\mathbb R^m\), el sistema sobredeterminado \(Ax=b\) generalmente no tiene una solución exacta. Los mínimos cuadrados minimizan la norma euclidiana del residual

$$
r(x)=b-Ax
$$

como sigue.

$$
x_\star
=
\arg\min_x \|Ax-b\|_2^2.
$$

\(Ax\) siempre se encuentra en \(\mathcal C(A)\), el espacio de columna de \(A\). Por lo tanto, el problema es encontrar el elemento del espacio de columnas \(\hat b=Ax_\star\) más cercano a \(b\).

## 2. Proyección ortogonal y ecuaciones normales

En el punto más cercano, el residual \(r_\star=b-Ax_\star\) es ortogonal a todas las direcciones en el espacio de la columna.

$$
A^\mathsf T r_\star=0.
$$

Al expandir esta expresión se obtienen las ecuaciones normales.

$$
A^\mathsf T A x_\star=A^\mathsf T b.
$$

Si \(A\) tiene el rango de columna completo, \(A^\mathsf T A\) es positivo definido y la solución es única.

$$
x_\star=(A^\mathsf T A)^{-1}A^\mathsf T b.
$$

Esta ecuación, sin embargo, es una **expresión matemática**, no un procedimiento computacional recomendado. En el código real, generalmente es mejor evitar construir explícitamente una inversa y resolver incondicionalmente las ecuaciones normales cuando la precisión es importante.

La matriz de proyección es

$$
P=A(A^\mathsf T A)^{-1}A^\mathsf T
$$

y \(\hat b=Pb\). Con rango de columna completo, \(P\) satisface

$$
P^\mathsf T=P,\qquad P^2=P
$$

Simetría significa que la proyección es ortogonal, mientras que idempotencia significa que proyectar un valor ya proyectado lo deja sin cambios.

## 3. Un ejemplo de regresión simple

Supongamos que ajustamos un modelo lineal \(y\approx\beta_0+\beta_1t\) a varios puntos. La matriz de diseño es

$$
A=
\begin{bmatrix}
1&t_1\\
1&t_2\\
\vdots&\vdots\\
1&t_m
\end{bmatrix},
\qquad
x=
\begin{bmatrix}\beta_0\\\beta_1\end{bmatrix},
\qquad
b=
\begin{bmatrix}y_1\\y_2\\\vdots\\y_m\end{bmatrix}.
$$

La solución de mínimos cuadrados no minimiza la **distancia perpendicular** entre los puntos de datos y la línea. Minimiza la suma de residuos cuadrados en la dirección \(y\) especificada. Si ambos ejes contienen errores, puede ser más apropiado una regresión de distancia ortogonal o un modelo de errores en variables.

Además, si los valores absolutos de \(t\) son muy grandes o su rango está concentrado en un lado, distinguir numéricamente la columna de intersección de la columna de pendiente puede resultar difícil. Centrar y escalar adecuadamente \(t\) mejora tanto el número de condición como la interpretación del coeficiente.

## 4. Números de condición: cuánto error de entrada se amplifica en la solución

El número de condición de 2 normas de una matriz cuadrada invertible es

$$
\kappa_2(A)
=
\|A\|_2\|A^{-1}\|_2
=
\frac{\sigma_{\max}}{\sigma_{\min}}
$$

Para una matriz rectangular de rango de columnas completas, la relación entre el valor singular más grande y el valor singular más pequeño distinto de cero tiene el mismo significado.

Un número de condición grande provoca los siguientes fenómenos.

- Los pequeños errores en la entrada \(b\) se amplifican enormemente en \(x\).
- Las columnas casi idénticas hacen que los coeficientes fluctúen marcadamente.
- Las estimaciones de los parámetros pueden ser inestables incluso cuando el residual es pequeño.
- Los errores de redondeo en coma flotante tienen un mayor efecto.

Las ecuaciones normales tienen un problema decisivo.

$$
\kappa_2(A^\mathsf T A)=\kappa_2(A)^2.
$$

Se eleva al cuadrado un número que ya estaba en malas condiciones. Al formar \(A^\mathsf T A\) también se pueden perder dígitos significativos.

> Un pequeño residuo y parámetros precisos no son lo mismo. Incluso si \(b\) está cerca del espacio de la columna, las columnas casi dependientes pueden permitir que coeficientes muy diferentes produzcan predicciones similares.

## 5. Resolviendo mínimos cuadrados con QR

Supongamos que \(A\) tiene el rango de columna completo y

$$
A=QR,
$$

donde las columnas de \(Q\in\mathbb R^{m\times n}\) son ortonormales y \(R\in\mathbb R^{n\times n}\) es triangular superior. Entonces

$$
\|Ax-b\|_2^2
=
\|Rx-Q^\mathsf Tb\|_2^2
+\|(I-QQ^\mathsf T)b\|_2^2.
$$

Como el segundo término es independiente de \(x\), podemos resolver

$$
Rx=Q^\mathsf T b
$$

por sustitución hacia atrás.

En la práctica, Householder QR es generalmente más estable que el clásico Gram-Schmidt. Si tiene dudas sobre la clasificación, utilice la columna dinámica QR

$$
AP=QR
$$

para presentar columnas importantes y diagnosticar la clasificación efectiva.

## 6. SVD y el pseudoinverso

SVD descompone una matriz como

$$
A=U\Sigma V^\mathsf T
$$

Las columnas de \(U\) y \(V\) son ortonormales y las entradas diagonales \(\sigma_i\) de \(\Sigma\) son los valores singulares.

La pseudoinversa de Moore-Penrose es

$$
A^+=V\Sigma^+U^\mathsf T
$$

y la solución de norma mínima entre todas las soluciones de mínimos cuadrados es

$$
x_\star=A^+b
=
\sum_{\sigma_i>0}
\frac{u_i^\mathsf Tb}{\sigma_i}v_i
$$

Esta ecuación revela directamente la fuente del mal condicionamiento. En direcciones con \(\sigma_i\) pequeño, incluso el ruido pequeño en \(u_i^\mathsf Tb\) se amplifica con \(1/\sigma_i\).

### Cuando SVD es especialmente útil

- Cuando existe o se sospecha deficiencia de rango
- Cuando quieras inspeccionar el espacio nulo y las direcciones identificables.
- Cuando necesitas una solución de norma mínima
- Al diagnosticar el condicionamiento del espectro singular.
- Al aplicar regularización como SVD truncado

SVD ofrece la mayor potencia de diagnóstico, pero puede costar más cálculo y memoria que QR. Elija según el tamaño del problema, la escasez y la precisión requerida.

## 7. Deficiencia de rango y soluciones no únicas

Si es \(\operatorname{rank}(A)<n\), valores distintos de \(x\) pueden producir el mismo \(Ax\). Para \(z\in\mathcal N(A)\),

$$
A(x+z)=Ax
$$

entonces, si \(x\) es una solución de mínimos cuadrados, \(x+z\) tiene el mismo residuo. La solución pseudoinversa selecciona la que tiene el \(\|x\|_2\) más pequeño.

El rango no es binario en datos numéricos. Dado un límite de valor singular \(\tau\), se pueden descartar direcciones que satisfagan

$$
\sigma_i\le\tau
$$

pero \(\tau\) no es un mero detalle de implementación. Es una elección de modelado sobre qué direcciones considerar como no identificables y debe reflejar la escala, el nivel de ruido y el propósito.

## 8. Mínimos cuadrados ponderados y covarianza

Si los componentes residuales tienen varianzas diferentes o están correlacionados, el supuesto de igual ponderación de mínimos cuadrados ordinarios es inapropiado. Si la covarianza del error es \(\Sigma_b\), entonces

$$
x_\star
=
\arg\min_x
(Ax-b)^\mathsf T\Sigma_b^{-1}(Ax-b).
$$

El uso de una matriz blanqueadora que satisfaga \(W^\mathsf TW=\Sigma_b^{-1}\) transforma el problema en

$$
\min_x\|W(Ax-b)\|_2^2
$$

En este caso, las ponderaciones no deben ser puntuaciones arbitrarias elegidas por conveniencia; deben estar conectados a la estructura de probabilidad de los residuos.

## 9. La regularización es una suposición adicional, no un truco numérico.

La regularización de Tikhonov se puede escribir como

$$
x_\lambda
=
\arg\min_x
\left(
\|Ax-b\|_2^2
+\lambda^2\|L(x-x_0)\|_2^2
\right)
$$

- \(x_0\): Solución previa o de referencia
- \(L\): Estructura para penalizar
- \(\lambda\): Equilibrio entre ajuste de datos y anterior

Con \(L=I\) y \(x_0=0\), esto se convierte en la forma de cresta. La regularización reduce la variación a costa de introducir sesgos. Por lo tanto, debe tratarse como un paso de modelado que establece qué soluciones son más plausibles, no como "agregar un valor pequeño arbitrario porque el número de condición es malo".

\(\lambda\) se puede seleccionar con validación cruzada, el principio de discrepancia, una curva L-, validación cruzada generalizada y otros métodos. Cualquiera que sea el método que utilice, registre el criterio de selección y la independencia de los datos de evaluación.

## 10. Guía de selección de algoritmos

| Situación | Primera opción a considerar | Razón |
|---|---|---|
| Acondicionamiento denso, de rango completo y ordinario | Jefe de familia QR | Equilibra estabilidad y costo |
| Clasificación poco clara, diagnóstico importante | SVD | Revela el espectro singular y el espacio nulo |
| Necesidad de determinar el rango de la columna | Pivotado QR o SVD | Estima el rango efectivo |
| Problema disperso muy grande | Solucionador iterativo de mínimos cuadrados | Evita el costo de factorización matricial |
| Estructura de covarianza presente | Mínimos cuadrados blanqueados/ponderados | Refleja el modelo de error |
| Problema inverso mal planteado | Solucionador regularizado | Suprime direcciones inestables |
| La velocidad es primordial y el acondicionamiento es bueno | Consideremos atentamente a Cholesky sobre las ecuaciones normales. Rápido, pero corre el riesgo de elevar al cuadrado el número de la condición |

El valor predeterminado debería ser una función que resuelva el sistema lineal directamente en lugar de "calcular la inversa y multiplicar". Las funciones de biblioteca como `solve`, `lstsq` y los solucionadores dispersos aprovechan las factorizaciones internas y el manejo de excepciones.

## 11. Flujo de trabajo práctico

1. **Defina el objetivo**: ¿Es importante la predicción o la interpretación de los parámetros?
2. **Comprueba las dimensiones y las unidades**: Anota las formas y las unidades físicas de \(A\), \(x\) y \(b\).
3. **Escala**: inspecciona las normas de las columnas, los rangos de variables y las unidades; centrar y estandarizar si es necesario.
4. **Diagnosticar rango**: inspeccionar QR pivotes o el espectro singular.
5. **Elija un solucionador**: use QR de forma predeterminada; Considere SVD para diagnósticos de rango y mal estado.
6. **Analizar residuos**: examinar la estructura, el sesgo, la heterocedasticidad y la correlación, no solo una norma.
7. **Verificar ortogonalidad**: compruebe si \(A^\mathsf Tr\) es cero dentro de la tolerancia.
8. **Verifique la sensibilidad**: Perturbe la entrada dentro de su rango admisible y observe cuánto cambian los coeficientes y las predicciones.
9. **Informar incertidumbre**: Calcule la incertidumbre de los parámetros cuando el modelo de ruido y los supuestos de covarianza sean válidos.
10. **Registrar detalles de reproducibilidad**: conserve el solucionador, la tolerancia, el escalado, el límite de clasificación y el método de selección de regularización.

## 12. Lista de verificación de verificación

- [ ] ¿Se especifican la norma minimizada y los pesos?
- [] ¿\(Ax_\star\) se encuentra en el espacio de la columna y es \(A^\mathsf Tr\approx0\)?
- [ ] Si se asumió el rango completo, ¿se verificó realmente?
- [] ¿Se evitó una inversa de \(A^\mathsf TA\)?
- [] ¿Se compararon los números de condición antes y después del escalado de columnas?
- [ ] ¿Se registraron juntos los valores singulares y el límite?
- [ ] ¿Se evaluaron por separado la magnitud residual y la estabilidad de los parámetros?
- [ ] ¿Se evitó sobreajustar el parámetro de regularización a los datos de evaluación?
- [] ¿Las ponderaciones en mínimos cuadrados ponderados coinciden con el modelo de error?
- [ ] ¿Se mantuvieron distintos los intervalos de predicción de los intervalos de confianza de los parámetros?

## 13. Escollos y limitaciones

### Confundir un \(R^2\) alto con un problema bien resuelto

Un alto poder explicativo no garantiza independencia residual, adecuación del modelo o identificabilidad de parámetros. Es especialmente peligroso en la extrapolación.

### Cambiar unidades de entrada y comparar directamente magnitudes de coeficientes

La magnitud del coeficiente depende de la escala variable. Alinear unidades y escalar antes de comparar importancia.

### Creer que el pseudoinverso recupera la “verdadera solución”

La pseudoinversa simplemente selecciona una solución representativa de acuerdo con un criterio de optimización claro; no puede restaurar la información de espacio nulo perdida de los datos.

### Ocultar errores de estructura del modelo con regularización

La regularización mitiga las malas posturas, pero no corrige las variables omitidas, un operador de observación incorrecto o un sesgo sistemático.

### Límites de mínimos cuadrados linealizados

Un modelo no lineal \(f(x)\) requiere linealización local y optimización iterativa. Los valores iniciales, los mínimos locales y el condicionamiento jacobiano se convierten en preocupaciones adicionales.

## Conclusión

Los mínimos cuadrados no son simplemente una “fórmula que reduce la suma de errores al cuadrado”; es un **problema de proyección en un subespacio**. QR es la herramienta fundamental para calcular esa proyección de manera estable, mientras que SVD es la herramienta de diagnóstico que expone direcciones clasificadas e inestables. El número de condición pregunta si el cálculo es confiable y la regularización establece explícitamente qué suposiciones se agregaron en lugar de la información faltante.

Los mínimos cuadrados se convierten en un análisis reproducible cuando se preserva la ortogonalidad residual, el espectro singular, la escala, el solucionador y la tolerancia junto con los números finales.
