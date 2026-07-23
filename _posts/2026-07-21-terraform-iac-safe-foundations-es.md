---
title: "Diseño seguro de IaC Terraform: límites para módulos, entornos, estados y secretos"
date: 2026-07-21 09:30:00 +0900
categories: [Platform Engineering, Infrastructure]
tags: [terraform, infrastructure-as-code, state-management, security, devops]
description: Comprenda Terraform como un sistema de cambio declarativo y contratos de módulos de diseño, aislamiento del entorno, estado remoto, gestión de secretos y procedimientos de verificación de planificación/aplicación.
lang: es
translation_key: terraform-iac-safe-foundations
hidden: true
---

{% include language-switcher.html %}

## El problema: convertir la infraestructura en código no la hace segura automáticamente

Terraform convierte los clics manuales en código reproducible, pero al mismo tiempo concentra los permisos de cambio de infraestructura y el estado real de los recursos en un único flujo de trabajo. Si comienza sin estructura, un pequeño módulo raíz terminará asumiendo cada entorno, permiso, secreto y configuración del proveedor.

Las fallas comunes incluyen las siguientes.

- El desarrollo y la producción comparten el mismo estado y credenciales.
- Un módulo expone tantas opciones que efectivamente se convierte en otra plataforma.
- El estado local se pierde o varios corredores lo modifican al mismo tiempo.
- `sensitive = true` se confunde con cifrado, lo que deja los secretos en estado.
- Cambio de código, proveedores o estado entre el plan revisado y la aplicación real.
- `-target` y los cambios manuales de la consola se convierten en una práctica operativa estándar.

El objetivo de IaC no es aumentar la cantidad de archivos. Se trata de **convertir la intención del cambio, el estado real, los límites de los permisos y los resultados de la verificación en un único flujo auditable**.

## Modelo mental: conciliar configuración, estado, proveedores e infraestructura real

Una ejecución Terraform tiene cuatro elementos.

- **configuración**: HCL que expresa el estado deseado
- **estado**: información de asignación entre direcciones Terraform y atributos e ID de objetos remotos reales
- **proveedor**: un complemento que lee y cambia las API
- **infraestructura real**: recursos reales en la nube, sistemas SaaS y entornos locales

`terraform plan` no es una simple diferenciación de archivos. Crea un plan de ejecución comparando la configuración, el estado anterior y el estado real leído por los proveedores. `apply` llama a las API según el gráfico de dependencia y registra los resultados exitosos en el estado.

Por tanto, el estado no es un caché. Se trata de datos operativos críticos que contienen elementos tales como:

- Identificadores de recursos reales
- Dependencias e instantáneas de atributos.
- Salidas y algunos valores de retorno del proveedor.
- Entradas y resultados calculados que pueden ser secretos.

La pérdida del estado no hace que desaparezca la infraestructura real, pero Terraform pierde su mapeo de propiedad. Por el contrario, alguien que sólo tenga el archivo estatal aún puede conocer información confidencial y la estructura de la infraestructura.

### Declarativo no significa "desordenado"

Una referencia de recurso crea una ventaja de dependencia. Terraform paraleliza las operaciones siempre que sea posible respetando el orden del gráfico. Agregar muchas declaraciones `depends_on` sin sentido crea un acoplamiento oculto y planes más lentos. Exprese el flujo de datos a través de referencias y utilice `depends_on` solo cuando un API imponga una restricción implícita.

### Un módulo es un contrato de política más que un mecanismo de reutilización de código

Un buen módulo reduce las opciones que permite la organización.

- entrada: qué pueden decidir las personas que llaman
- local: Nombres, etiquetas y políticas estandarizadas por el módulo
- recurso: detalles de implementación
- resultado: Contratos estables de los que pueden depender otros componentes

Una “envoltura delgada” que expone cada argumento del proveedor sin cambios como una variable ofrece poco valor de abstracción. En el otro extremo, si un módulo posee la red, la base de datos, la aplicación y el monitoreo, su radio de cambio se vuelve grande.

## Patrón práctico: raíces pequeñas, módulos estables y estado independiente por entorno

### Una estructura inicial recomendada

```text
infrastructure/
├── modules/
│   └── service/
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       └── versions.tf
└── live/
    ├── development/
    │   ├── backend.hcl
    │   ├── main.tf
    │   └── terraform.tfvars.example
    └── production/
        ├── backend.hcl
        ├── main.tf
        └── terraform.tfvars.example
```

Duplicar un directorio de entorno no es la única respuesta correcta. También son posibles repositorios separados, una capa de orquestación o canales por cuenta. Las invariantes importantes son:

- Cada entorno tiene una clave de estado independiente y aplica permisos.
- La producción utiliza una cuenta o proyecto separado y un límite de aprobación independiente.
- La versión o confirmación del módulo compartido se fija explícitamente.
- Las diferencias ambientales son insumos explícitos, no un bosque de condicionales.

Los espacios de trabajo Terraform son convenientes para operar múltiples estados desde la misma configuración, pero no proporcionan automáticamente un fuerte aislamiento de seguridad ni estructuras de entorno sustancialmente diferentes. Si necesita límites de cuentas y credenciales, separe las identidades de ejecución, así como los directorios y el estado.

### Proporcionar módulos con contratos estrechos y verificables

Un ejemplo `variables.tf`:

```hcl
variable "name" {
  description = "서비스를 식별하는 짧은 이름"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,30}$", var.name))
    error_message = "name은 소문자로 시작하고 소문자, 숫자, 하이픈만 사용해야 합니다."
  }
}

variable "environment" {
  description = "배포 환경"
  type        = string

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "허용된 environment 값을 사용해야 합니다."
  }
}

variable "labels" {
  description = "추가 공통 label"
  type        = map(string)
  default     = {}
}
```

Mantenga los valores estandarizados dentro del módulo en `main.tf`.

```hcl
locals {
  required_labels = {
    managed-by  = "terraform"
    environment = var.environment
    service     = var.name
  }

  labels = merge(var.labels, local.required_labels)
}

# provider에 독립적인 예시를 위해 실제 resource는 생략했다.
# 각 resource는 local.labels를 사용해 소유권과 환경을 표시한다.
```

Debido a que los mapas posteriores en `merge` anulan los anteriores, colocar las etiquetas requeridas al final evita que las personas que llaman las cambien. Este es un pequeño ejemplo de cómo un módulo encapsula la política.

Exponer únicamente el contrato mínimo requerido a través de salidas.

```hcl
output "service_id" {
  description = "다른 module이 참조할 안정된 서비스 ID"
  value       = <RESOURCE_ADDRESS>.id
}
```

La salida del objeto de recurso completo une a las personas que llaman con los detalles de implementación. Devuelve solo lo que los consumidores realmente necesitan, como un ID, un punto final o un identificador de función.

### Administrar las restricciones de versión y el bloqueo del proveedor juntos

```hcl
terraform {
  required_version = ">= 1.8, < 2.0"

  required_providers {
    <PROVIDER_NAME> = {
      source  = "<PROVIDER_NAMESPACE>/<PROVIDER_NAME>"
      version = "~> <REVIEWED_MAJOR.MINOR>"
    }
  }
}
```

Reemplace los marcadores de posición en este ejemplo con el proveedor real. Establezca restricciones de versión en el módulo raíz y confirme el `.terraform.lock.hcl` producido por `terraform init`. Un módulo debe declarar la versión mínima del proveedor que necesita, mientras que la raíz generalmente es responsable de la selección final y el bloqueo.

El archivo de bloqueo fija la selección binaria del proveedor y las sumas de verificación. Si la ejecución abarca múltiples sistemas operativos o arquitecturas, administre deliberadamente las sumas de verificación de la plataforma requeridas por CI y los entornos de desarrollo.

### Separe el acceso al backend y al estado del acceso al código

No escriba secretos directamente en el bloque backend.

```hcl
terraform {
  backend "<REMOTE_BACKEND_TYPE>" {}
}
```

Puede proporcionar configuraciones por entorno no confidenciales a través de un archivo separado.

```hcl
# live/production/backend.hcl
bucket         = "<REMOTE_STATE_BUCKET>"
key            = "<SERVICE>/production/terraform.tfstate"
region         = "<REGION>"
encrypt        = true
use_lockfile   = true
```

Estos argumentos varían según el tipo de backend y la versión Terraform, así que consulte la documentación oficial y las capacidades reales del backend. Los requisitos básicos son:

- Cifrado en tránsito y en reposo.
- Se aplica bloqueo que evita la concurrencia.
- Versionado y política de recuperación.
- Una identidad con privilegios mínimos
- Claves separadas y políticas de acceso para cada entorno.
- Registros de auditoría y alertas de acceso anómalo.

Ejecute la inicialización explícitamente desde el directorio del entorno.

```bash
terraform init -backend-config=backend.hcl
terraform providers
```

No coloque credenciales de backend en archivos; Emita credenciales de corta duración a través de CI OIDC o una cadena de credenciales estándar. Escribir una clave de acceso en `backend.hcl` puede dejarla atrás a través de varias rutas, incluidos los metadatos `.terraform` y el historial del shell.

### Vincular el plan y aplicarlo en un cambio revisable

El flujo de verificación básico es:

```bash
terraform fmt -check -recursive
terraform init -input=false -backend=false
terraform validate
```

Ejecute un plan que utilice API de proveedor y de estado remoto real desde una identidad y un entorno aprobados.

```bash
terraform init -input=false -backend-config=backend.hcl
terraform plan -input=false -out=tfplan
terraform show -no-color tfplan
```

Un archivo de plan guardado es binario y puede contener valores confidenciales. No lo conserve indefinidamente como un artefacto público CI; aplicar cifrado, control de acceso y retención breve. Aplique solo un plan producido a partir del mismo compromiso, archivo de bloqueo y linaje de estado.

```bash
terraform apply -input=false tfplan
```

Si una persona aprueba un plan textual y el proceso aplica automáticamente un nuevo plan de otra confirmación, esa aprobación pierde su significado. La canalización debe vincular la fuente SHA al resumen del artefacto del plan.

### Pasar referencias secretas en lugar de valores secretos

La siguiente declaración oculta el valor en UI y algunos resultados, pero no cifra el estado.

```hcl
variable "bootstrap_secret" {
  type        = string
  sensitive   = true
  description = "초기 구성에만 필요한 비밀값"
}
```

Si un proveedor API acepta el valor como atributo de recurso, ese valor puede almacenarse en estado. Un posible diseño es:

1. Cree el secreto en un administrador de secretos con un ciclo de vida independiente.
2. Terraform conecta solo el secreto ID o ruta y permisos de lectura.
3. La carga de trabajo lee el valor del administrador secreto utilizando su identidad de tiempo de ejecución.
4. No pase el secreto de texto sin formato a planes, resultados o registros.

Si Terraform también debe crear el secreto, reconozca que el estado se ha convertido en un almacén de secretos y opere el acceso, el cifrado y la rotación del estado según ese estándar. Quitar el marcador con `nonsensitive()` no es una solución de seguridad.

### La detección de derivas no termina con un plan nocturno

Detecte la desviación de los cambios de la consola y la automatización externa con planes regulares de solo lectura. Cuando encuentre una desviación, elija explícitamente una de las tres respuestas.

- El cambio real fue incorrecto: restaurar el estado declarado originalmente con Terraform.
- El cambio real fue legítimo: reflejarlo en la configuración y aplicarlo mediante el proceso normal PR.
- La propiedad era incorrecta: revise `import`, `moved` y las operaciones estatales para corregir el límite de responsabilidad.

Al cambiar la dirección de un recurso, utilice un bloque `moved` para que Terraform no confunda el cambio con eliminación y recreación.

```hcl
moved {
  from = <OLD_RESOURCE_ADDRESS>
  to   = <NEW_RESOURCE_ADDRESS>
}
```

Las importaciones y los comandos estatales cambian la comprensión de propiedad de Terraform incluso cuando no cambian el recurso real. Verificar el estado de las versiones antes de la operación; después, verifique siempre que el plan esté vacío como se esperaba o que contenga solo la diferencia deseada.

## Lista de verificación de verificación

Revisión del módulo:

- [ ] El módulo tiene un ciclo de vida y un propietario coherentes.
- [] Los tipos de entrada, descripciones, validación y valores predeterminados son claros.
- [] Las personas que llaman no pueden eludir las etiquetas de seguridad y propiedad requeridas.
- [ ] Los resultados forman un contrato mínimo estable en lugar de exponer la implementación completa.
- [ ] Se especifican los rangos de versión de proveedor y Terraform.
- [ ] Las actualizaciones y los cambios de dirección tienen `moved` bloques y documentación de migración.

Revisión ambiental y estatal:

- [ ] Las identidades de estado y ejecución de desarrollo, puesta en escena y producción están separadas.
- [] El backend remoto proporciona cifrado, bloqueo, control de versiones y auditoría.
- [] El acceso a los artefactos del estado y del plan es más limitado que el permiso para leer el código.
- [ ] `.terraform/`, `*.tfstate*`, `*.tfvars` real y los archivos del plan no están confirmados.
- [ ] `.terraform.lock.hcl` se confirma después de la revisión.
- [ ] La producción se aplica únicamente en un ambiente protegido y una tubería aprobada.

Revisión de cambios:

- [ ] `fmt`, `validate`, linting y comprobaciones de políticas pasan.
- [ ] Las acciones de agregar, cambiar, destruir y reemplazar del plan se han leído recurso por recurso.
- [ ] Se han comprobado los reemplazos forzados, la pérdida de datos y las posibles interrupciones de la red.
- [ ] El plan revisado y el plan binario a aplicar provinieron de la misma fuente y estado.
- [] Existe una manera de verificar la funcionalidad crítica y las métricas de observabilidad después de la aplicación.
- [ ] Para los cambios que no se pueden revertir, se han probado el procedimiento de avance y la restauración de la copia de seguridad.

## Casos de falla y limitaciones

### Un estado enorme

Las referencias son convenientes, pero incluso un pequeño cambio requiere actualizar todo el gráfico y permisos amplios. Agrupa los recursos en el mismo estado cuando cambian juntos, comparten un propietario y deben tener el mismo radio de explosión. Por el contrario, una división demasiado fina del Estado aumenta la carga de los resultados, el ordenamiento y la orquestación entre estados.

### Absorber cada diferencia ambiental en condicionales

Poner todos los entornos en una raíz con `count`, `for_each` y expresiones ternarias dificulta la lectura de los planes. Coloque políticas compartidas en módulos y composición específica del entorno en raíces finas.

### Uso de `-target` como herramienta de implementación diaria

`-target` es una herramienta limitada para recuperación y situaciones especiales. Aplicar solo una parte del gráfico puede perder coherencia entre la configuración completa y el estado real. Ejecute siempre un plan completo después de usarlo.

### Tratar `prevent_destroy` como copia de seguridad

Una protección del ciclo de vida evita algunos errores, pero un usuario privilegiado puede eliminarla y no puede evitar la eliminación fuera del proveedor. Los recursos de datos necesitan copias de seguridad independientes, ejercicios de recuperación, retención y protección contra eliminación.

### Tratar una solicitud exitosa como un servicio saludable

El hecho de que un API haya creado un recurso no es lo mismo que que la aplicación esté en buen estado. Después de la implementación, verifique DNS, permisos, conectividad, estado y métricas SLO. IaC no reemplaza la verificación operativa ni la respuesta a incidentes.

### Gestionando todo con Terraform

Terraform destaca en recursos declarativos con ciclos de vida largos. Forzar implementaciones de aplicaciones de alta frecuencia, migraciones de datos imperativas y un arranque único puede desestabilizar el estado y el gráfico. Elija herramientas que se ajusten al ciclo de vida y las características de reversión de cada cambio.

La seguridad Terraform proviene del diseño de límites, no de la inteligencia HCL. Trate los módulos como límites de políticas, el estado como un activo de seguridad, los planes como contratos de cambio y las identidades de canalización como autoridad de ejecución.
