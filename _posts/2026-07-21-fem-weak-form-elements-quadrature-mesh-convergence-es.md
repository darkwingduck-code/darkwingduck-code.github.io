---
title: "La columna vertebral del método de los elementos finitos: formas débiles, elementos, cuadratura y convergencia de mallas"
date: 2026-07-21 12:43:00 +0900
categories: [Scientific Computing, Finite Element Method]
tags: [fem, weak-form, galerkin, finite-element, quadrature, mesh-convergence]
description: "Conecte la estructura central de FEM, derivando la forma débil de la forma fuerte a través de espacios funcionales, condiciones de contorno, interpolación de elementos, cuadratura, ensamblaje, solucionadores lineales y convergencia de malla."
math: true
mermaid: true
lang: es
translation_key: fem-weak-form-elements-quadrature-mesh-convergence
hidden: true
---

{% include language-switcher.html %}

El método de elementos finitos (FEM) es más que una técnica para dividir una geometría en piezas pequeñas.
Transforma una ecuación diferencial en una forma débil integrable y proyecta un problema en un espacio funcional de dimensión infinita en un subespacio de dimensión finita.
Una vez que esta perspectiva está clara, los tipos de elementos y las opciones de resolución se conectan a través de una única estructura matemática.

## 1. Empezar desde la forma fuerte

Consideremos el problema de Poisson.

$$
-\nabla\cdot(k\nabla u)=f \quad \text{in }\Omega,
$$

$$
u=g_D \quad \text{on }\Gamma_D,
\qquad
-k\nabla u\cdot n=g_N \quad \text{on }\Gamma_N.
$$

La forma fuerte requiere que (u) sea suficientemente diferenciable punto por punto y satisfaga la ecuación y las condiciones de frontera punto por punto.
Para coeficientes complejos, materiales discontinuos y dominios no lisos, este requisito puede ser demasiado estricto.

## 2. Funciones de prueba e integración por partes

Multiplique por una función de prueba (v) que sea cero en el límite de Dirichlet e integre.

$$
\int_\Omega -v\nabla\cdot(k\nabla u)\,d\Omega
=\int_\Omega vf\,d\Omega.
$$

Aplicando la integración por partes, o la identidad de Green, se obtiene

$$
\int_\Omega k\nabla v\cdot\nabla u\,d\Omega
-\int_{\partial\Omega}v k\nabla u\cdot n\,d\Gamma
=\int_\Omega vf\,d\Omega.
$$

Sustituyendo la condición de Neumann se obtiene la forma débil

$$
a(u,v)=\ell(v)
$$

con

$$
a(u,v)=\int_\Omega k\nabla v\cdot\nabla u\,d\Omega,
$$

$$
\ell(v)=\int_\Omega vf\,d\Omega+\int_{\Gamma_N}vg_N\,d\Gamma
$$

El orden de la derivada de (u) ha caído del segundo al primero y la condición de frontera natural ha entrado como una integral de frontera.

## 3. Condiciones de contorno esenciales y naturales.

- Una condición de Dirichlet restringe el espacio de prueba en sí, por eso se llama condición esencial.
- Una condición de Neumann aparece naturalmente en el lado derecho de la forma débil, por lo que se llama condición natural.

Esta distinción también es importante en la implementación.
Al eliminar los grados de libertad de Dirichlet de la matriz o manejarlos como restricciones, preserve la simetría y el cálculo de reacciones.

Un problema puro de Neumann tiene un espacio nulo porque toda solución desplazada por una constante también es posible.
Requiere la condición de compatibilidad

$$
\int_\Omega f\,d\Omega+\int_{\Gamma_N}g_N\,d\Gamma=0
$$

y una restricción o referencia de valor medio.

## 4. El significado de los espacios funcionales.

El espacio natural para el problema de Poisson es el espacio de Sobolev (H^1(\Omega)).

$$
H^1(\Omega)=
\{v\in L^2(\Omega):\nabla v\in[L^2(\Omega)]^d\}.
$$

En otras palabras, la función y su primera derivada débil sólo necesitan ser integrables al cuadrado.
El requisito central es una norma energética integrable, no una suavidad puntual.

Galerkin FEM utiliza el mismo subespacio de dimensión finita para los espacios de prueba y de prueba.

$$
V_h=\mathrm{span}\{N_1,\ldots,N_n\}.
$$

## 5. Interpolación de elementos y grados de libertad.

Representar la solución aproximada como

$$
u_h(\mathbf x)=\sum_{j=1}^{n}N_j(\mathbf x)U_j
$$

Cada (N_j) es una función de forma y cada (U_j) es un valor nodal o grado de libertad generalizado.

El uso de cada función base (N_i) como función de prueba da

$$
K_{ij}=\int_\Omega k\nabla N_i\cdot\nabla N_j\,d\Omega,
\qquad
F_i=\ell(N_i)
$$

y el sistema global se vuelve

$$
\mathbf K\mathbf U=\mathbf F
$$

## 6. El elemento de referencia y el mapeo.

Asigne el elemento físico (Omega_e) del elemento de referencia (hat\Omega).

$$
\mathbf x(\boldsymbol\xi)=
\sum_a N_a(\boldsymbol\xi)\mathbf x_a.
$$

El jacobiano es

$$
J=\frac{\partial\mathbf x}{\partial\boldsymbol\xi}
$$

y transforma tanto el gradiente como el elemento de volumen.

$$
\nabla_x N=J^{-T}\nabla_\xi N,
\qquad
d\Omega=|\det J|d\hat\Omega.
$$

Un elemento con (det J\le0) está invertido o degenerado.
Un determinante pequeño y un número de condición grande degradan los cálculos de gradiente y el acondicionamiento de rigidez.

## 7. La cuadratura es parte del modelo.

Aproxima la integral del elemento por cuadratura.

$$
\int_{\hat\Omega}g(\xi)d\xi
\approx
\sum_{q=1}^{n_q}w_q g(\xi_q).
$$

Si el orden de integración es demasiado bajo, es posible que la rigidez y las fuerzas internas no se construyan con precisión, lo que produce modos de reloj de arena o de energía cero.
Por el contrario, una cuadratura excesiva sólo puede aumentar el costo sin resolver el bloqueo.

### Integración reducida e integración selectiva

Una integración reducida puede mitigar el bloqueo, pero conlleva el riesgo de modos espurios.
Comprobar que la estabilización no contamina la energía física.

### Materiales no lineales y puntos de cuadratura.

Las variables de estado internas generalmente se actualizan en puntos de cuadratura.
Usar una tangente consistente puede mejorar enormemente la convergencia de Newton.
Es importante la coherencia entre las actualizaciones de estado, las reversiones y los reintentos de pasos de carga.

## 8. La Asamblea es una convención de conservación que va de lo local a lo global.

Agregue cada elemento de matriz (mathbf K^e) y vector (mathbf F^e) al sistema global utilizando el mapeo de grados de libertad.

```mermaid
flowchart LR
  A[reference element] --> B[geometry mapping]
  B --> C[quadrature point evaluation]
  C --> D[element matrix/vector]
  D --> E[local-to-global assembly]
  E --> F[constraints and boundary terms]
  F --> G[linear/nonlinear solve]
  G --> H[error and balance checks]
```

Los grados de libertad en un nodo compartido combinan contribuciones de elementos adyacentes.
Para elementos de borde o cara con signos y orientaciones, alinee la orientación local con la convención global.

## 9. Conformidad, estabilidad y bloqueo

Simplemente aumentar el orden del polinomio no resuelve todos los problemas.

- **Conformidad**: ¿El espacio de aproximación satisface la continuidad requerida?
- **Coercitividad/estabilidad inf-sup**: ¿Es estable el problema discreto?
- **Bloqueo**: ¿La formulación se vuelve excesivamente rígida para estructuras delgadas o condiciones casi incompresibles?
- **Modo espurio**: ¿Existe algún modo que se deforme sin energía física?

En problemas mixtos, la combinación de espacios de desplazamiento y presión debe satisfacer la condición inf-sup.
El uso incondicional de la interpolación de igual orden puede producir oscilaciones de presión.

## 10. Refinamiento h, p y hp

- refinamiento h: Reduce el tamaño del elemento.
- p-refinamiento: aumenta el orden base.
- hp-refinement: Combina los dos según la suavidad.

Con suficiente regularidad, un error típico de norma energética tiene la forma

$$
\|u-u_h\|_{H^1}\le C h^p|u|_{H^{p+1}}
$$

En singularidades de esquina, coeficientes discontinuos o contacto, la baja regularidad puede impedir que aparezca el orden nominal.

## 11. Error a priori y a posteriori

Una estimación a priori explica la tasa de convergencia utilizando la regularidad de la solución y el tamaño de malla.
Un estimador a posteriori utiliza residuos y saltos de la solución calculada para decidir dónde refinar.

Un estimador residual conceptual combina el elemento residual (R_e) y el salto de flujo entre elementos (J_f), como en

$$
\eta^2=\sum_e h_e^2\|R_e\|^2
+\sum_f h_f\|J_f\|^2
$$

Utilice puntos de referencia para verificar que el índice de efectividad sea estable en toda la familia de problemas.

## 12. Problemas no lineales y método de Newton.

Si el vector residual es (mathbf R(\mathbf U)=0), el paso de Newton es

$$
\mathbf J(\mathbf U^k)\Delta\mathbf U
=-\mathbf R(\mathbf U^k),
$$

$$
\mathbf U^{k+1}=\mathbf U^k+\alpha\Delta\mathbf U
$$

Un jacobiano consistente, una búsqueda de líneas, un control de incremento de tiempo o carga y una reversión de estado determinan la robustez.

## 13. Flujo de trabajo recomendado

1. Especifique la forma segura, el dominio y la partición de límites.
2. Multiplicar por una función de prueba y derivar la forma débil manualmente mediante integración por partes.
3. Definir los espacios de prueba y prueba y las restricciones esenciales.
4. Verificar el elemento de referencia, el mapeo y las funciones de forma.
5. Haga coincidir el orden de la cuadratura con el integrando y la no linealidad.
6. Realice una prueba de parche a nivel de elemento y una prueba de solución fabricada.
7. Verificar el equilibrio global, las reacciones y la energía.
8. Realizar un refinamiento sistemático en tres o más niveles.
9. Informar estimadores de convergencia y error para cada QoI.

## 14. Lista de verificación de verificación

- [] Se volvió a derivar el signo del término límite de la forma débil.
- [ ] Se distinguieron las condiciones límite esenciales y naturales.
- [ ] Se manejó el espacio nulo puro de Neumann y la compatibilidad.
- [ ] La dirección del jacobiano de referencia al físico es consistente.
- [ ] Cada elemento determinante es positivo y suficientemente grande.
- [ ] Se comprobaron los modos de cuerpo rígido y el espacio nulo esperado.
- [] Se pasaron la prueba de parche y la prueba de estado constante.
- [ ] Se evaluó la sensibilidad al orden de cuadratura.
- [ ] La suma de reacciones y equilibrios de fuerzas externas.
- [ ] La energía de deformación y el trabajo son consistentes.
- [] El orden observado se calculó con refinamiento h o p.
- [] Un valor de singularidad de punto no se informa como si fuera una QoI convergente.

## 15. Patrones de falla comunes y limitaciones

### Solo haciendo la malla más fina

Agregar elementos distorsionados o aplicar solo un refinamiento uniforme en una singularidad proporciona pocos beneficios por el costo.

### Suponiendo que un contorno suave sea preciso

El posprocesamiento con promedio nodal puede hacer que la tensión discontinua parezca suave.
Verifique los valores originales de los puntos de cuadratura y el equilibrio.

### Utilizar la integración reducida como remedio universal

Puede reducir el bloqueo pero introducir modos de reloj de arena.
Examine la energía de estabilización y la sensibilidad de la malla juntas.

### Tolerancia confusa del solucionador con error de discretización

El error de malla puede seguir siendo grande incluso cuando el residual lineal es pequeño.
Por el contrario, comparar el refinamiento de la malla mientras el error algebraico es grande contamina el orden observado.

### Comparando solo la tensión máxima en un punto particular

La tensión puntual puede divergir en una esquina reentrante o en una carga concentrada.
Elija una QoI bien definida, como un parámetro integral, promedio o de fractura.

## 16. Referencias oficiales y primarias.

- Galerkin, B. G., “Solución en serie de algunos problemas de equilibrio elástico”, 1915.
- Courant, R., “Métodos variacionales para la solución de problemas de equilibrio y vibraciones”, 1943.
- Ciarlet, P. G., *El método de los elementos finitos para problemas elípticos*.
- NIST, [OOF documentación de análisis de elementos finitos](https://www.ctcms.nist.gov/oof/oof2/).
- PETSc, [Interfaces de elementos finitos y discretización](https://petsc.org/release/manual/dmplex/).
- El Proyecto FEniCS, [Documentación oficial](https://docs.fenicsproject.org/).

El corazón de FEM no es la forma de sus elementos, sino **si la forma débil, los espacios funcionales, la cuadratura, el ensamblaje y la estimación de errores forman un problema de aproximación consistente**.
