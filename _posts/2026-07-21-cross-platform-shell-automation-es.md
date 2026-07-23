---
title: "Automatización multiplataforma y solución de problemas con PowerShell, Bash, Windows y WSL"
date: 2026-07-21 09:50:00 +0900
categories: [Platform Engineering, Automation]
tags: [powershell, bash, windows, wsl, scripting, troubleshooting]
description: Separe las diferencias en shells, procesos, rutas y codificaciones, y diseñe una automatización Bash y PowerShell que falle inmediatamente y pueda volver a ejecutarse de forma segura.
lang: es
hidden: true
translation_key: cross-platform-shell-automation
---

{% include language-switcher.html %}

## El problema: los comandos que parecen iguales tienen diferentes ejecutores y reglas de datos

Al moverse entre Windows, WSL y Linux CI, la idea de que “solo es necesario cambiar la ruta” a menudo falla. La causa suele encontrarse en una de cuatro capas.

- ¿Qué shell interpreta la sintaxis?
- ¿Qué ejecutable está realmente seleccionado?
- ¿Cómo se dividen y citan los argumentos de una cadena?
- ¿En qué se diferencian la semántica del sistema de archivos, la codificación, el final de línea y los permisos?

Por ejemplo, una canalización PowerShell pasa objetos, mientras que una canalización Bash pasa flujos de bytes. El significado del alias PowerShell `curl` también difiere según la versión, y `/mnt/c/...` de WSL tiene una semántica de rendimiento y permisos diferente a la de un sistema de archivos Linux.

El objetivo de la automatización multiplataforma no es forzar la ejecución de un archivo en cada shell. Se trata de **definir un contrato de comando compartido e implementar ese contrato con precisión en cada shell**.

## Modelo mental: un shell es a la vez un iniciador de procesos y un lenguaje

Una línea de comando pasa por estas etapas.

```text
source text
  -> shell parsing/expansion
  -> executable resolution
  -> argument vector + environment + working directory
  -> process exit code + stdout + stderr
```

Al diagnosticar una falla, aísle qué etapa está incorrecta.

### Bash se centra en secuencias de texto

```bash
producer | filter | consumer
```

Cada proceso normalmente envía un flujo de bytes de salida estándar a la entrada estándar del siguiente proceso. El análisis puede cambiar con espacios, nuevas líneas, caracteres NUL y configuración regional. Tratar los nombres de archivos como texto orientado a líneas puede dañar los nombres que contienen nuevas líneas.

### PowerShell se centra en canalizaciones de objetos

```powershell
Get-Process | Where-Object CPU -gt 10 | Select-Object Name, CPU
```

Entre cmdlets, en lugar de comandos nativos, los objetos estructurados .NET fluyen a través de la canalización. Convertirlos a cadenas o salidas `Format-Table` demasiado pronto dificulta el filtrado y la serialización posteriores. Coloque el formato de salida al final del proceso.

### Hacer explícito el contrato de éxito y fracaso.

Un comando automatizable necesita al menos el siguiente contrato.

- Código de salida `0` en caso de éxito y distinto de cero en caso de error
- Resultados normales en stdout y diagnóstico en stderr.
- Salida legible por máquina con un esquema estable, como JSON
- Las operaciones destructivas requieren una bandera explícita y un objetivo validado.
- Idempotencia por lo que volver a ejecutar produce el mismo estado final.
- Comportamiento de limpieza en tiempo de espera y cancelación.

Utilice el código de salida en lugar de buscar en los registros la cadena "ERROR". Por el contrario, un CLI que sale con `0` mientras registra fallas parciales solo en registros es difícil de automatizar.

## Patrones prácticos: modos estrictos por capa y un contrato de comando compartido

### Esqueleto del script básico de Bash

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

readonly SCRIPT_NAME="${0##*/}"

usage() {
  printf 'Usage: %s --workspace <directory>\n' "$SCRIPT_NAME" >&2
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

workspace=''
while (($# > 0)); do
  case "$1" in
    --workspace)
      (($# >= 2)) || die '--workspace requires a value'
      workspace="$2"
      shift 2
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

[[ -n "$workspace" ]] || { usage; exit 2; }
[[ -d "$workspace" ]] || die "workspace is not a directory: $workspace"

workspace="$(cd -- "$workspace" && pwd -P)"
printf 'workspace=%s\n' "$workspace"

python -m pytest -- "$workspace/tests"
```

Significado de cada opción estricta:

- `-e`: salir ante un fallo no controlado de un comando simple. No es universal porque las expresiones condicionales y otros contextos son excepciones.
- `-u`: trata una referencia a una variable no configurada como un error.
- `-o pipefail`: propaga el fallo de un comando intermedio como fallo de la canalización.
- `-E`: ayuda a que las funciones y subcapas hereden la trampa `ERR`.

De forma predeterminada, coloque comillas dobles en las variables y use `--` con comandos que lo admitan para distinguir las opciones de las rutas. Utilice una matriz en lugar de construir un comando de shell como una cadena y pasarlo a `eval`.

```bash
command=(python -m pytest -q)
if [[ "${RUN_SLOW_TESTS:-0}" == '1' ]]; then
  command+=(--runslow)
fi
command+=(-- "$workspace/tests")

"${command[@]}"
```

Una matriz conserva los límites de los argumentos incluso cuando las rutas contienen espacios o caracteres comodín.

### Esqueleto de script básico PowerShell

```powershell
#requires -Version 7.3
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Container })]
    [string] $Workspace
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

try {
    $resolvedWorkspace = (Resolve-Path -LiteralPath $Workspace).Path
    Write-Information "workspace=$resolvedWorkspace" -InformationAction Continue

    & python -m pytest -- (Join-Path $resolvedWorkspace 'tests')
}
catch {
    Write-Error -ErrorRecord $_
    exit 1
}
```

Diferencias clave:

- `Set-StrictMode` detecta variables no definidas y algunos accesos a propiedades no válidos.
- `$ErrorActionPreference = 'Stop'` hace que los errores PowerShell que no terminan se comporten como errores de terminación.
- PowerShell 7.3+ de `$PSNativeCommandUseErrorActionPreference` conecta la salida distinta de cero de un comando nativo al flujo de error de PowerShell.
- `-LiteralPath` trata caracteres como `[` y `*` como caracteres de ruta literal en lugar de comodines.
- Ejecutar un proceso externo con el operador de llamada `&` y pasar argumentos como valores individuales.

Si se deben admitir versiones anteriores de PowerShell, inspeccione explícitamente el código de salida inmediatamente después de un comando nativo.

```powershell
& <NATIVE_COMMAND> <ARGUMENT_1> <ARGUMENT_2>
if ($LASTEXITCODE -ne 0) {
    throw "native command failed with exit code $LASTEXITCODE"
}
```

Reemplace `<...>` con el comando y los argumentos reales. `$?` y `$LASTEXITCODE` tienen significados diferentes, con diferencias de comportamiento entre versiones, así que fije y pruebe la versión de destino PowerShell para la automatización nativa.

### Dar al CLI compartido un contrato JSON

Si los contenedores Bash y PowerShell implementan una lógica empresarial compleja, pronto divergirán. Coloque la lógica central en un CLI comprobable escrito en Python, Go, .NET u otro lenguaje de propósito general, y deje que el shell maneje solo la configuración e invocación del entorno.

```text
tool inspect --workspace <PATH> --format json
```

Ejemplo de resultado exitoso:

```json
{
  "schema_version": 1,
  "status": "ok",
  "checks": [
    {"name": "configuration", "passed": true}
  ]
}
```

Analícelo como un objeto en PowerShell.

```powershell
$result = & tool inspect --workspace $resolvedWorkspace --format json |
    ConvertFrom-Json

if ($result.schema_version -ne 1 -or $result.status -ne 'ok') {
    throw 'inspection failed or returned an unsupported schema'
}
```

Si Bash necesita leer un campo, utilice un analizador validado JSON. No analice JSON con `grep` y `sed`.

### Convertir rutas Windows y WSL solo en el límite

| Significado | Windows | WSL |
|---|---|---|
| Ejemplo de proyecto de usuario | `C:\work\project` | `/mnt/c/work/project` |
| Proyecto en Linux inicio | No aplicable | `/home/<USER>/project` |
| Separador de ruta | `\` o, según API, `/` | `/` |
| Ejemplo ejecutable | `tool.exe` | Linux ELF `tool` |

Cuando se necesita una ruta Windows en WSL, use `wslpath` en lugar del reemplazo manual de cadenas.

```bash
windows_path='C:\work\project'
linux_path="$(wslpath -u -- "$windows_path")"
printf '%s\n' "$linux_path"
```

En la otra dirección:

```bash
windows_path="$(wslpath -w -- "$PWD")"
printf '%s\n' "$windows_path"
```

No convierta repetidamente rutas de un lado a otro. Convierta una vez en el límite del adaptador donde se llama a un proceso Windows. Las cargas de trabajo de Linux con muchas compilaciones, instalaciones de paquetes y operaciones de Git suelen ser más estables en los metadatos I/O y el comportamiento de los permisos cuando se ejecutan dentro del sistema de archivos Linux de WSL. Valide las políticas de acceso y respaldo de Windows IDE por separado.

### Definir finales de línea y bits ejecutables en el repositorio

Ejemplo `.gitattributes`:

```gitattributes
* text=auto
*.sh text eol=lf
*.bash text eol=lf
*.ps1 text eol=crlf
*.psm1 text eol=crlf
*.yml text eol=lf
*.yaml text eol=lf
Dockerfile text eol=lf
```

PowerShell 7 también puede procesar LF, así que elija CRLF para `.ps1` según la compatibilidad con las herramientas del equipo. El punto esencial es definir una política de repositorio coherente en lugar de dejarla en manos de la configuración `core.autocrlf` de cada desarrollador.

El bit ejecutable de un script en Linux también son metadatos de Git.

```bash
git update-index --chmod=+x scripts/check.sh
git diff --summary
```

Debido a que el bit ejecutable es menos visible en los sistemas de archivos Windows, verifique la ejecución real en Linux CI. Probar solo con `bash script.sh` puede ocultar problemas de bits ejecutables o shebang.

### Especificar codificación y configuración regional

Utilice UTF-8 de forma predeterminada para archivos estructurados y especifique la codificación tanto en productor como en consumidor. No confíe en las diferencias en la codificación de salida predeterminada entre las versiones de PowerShell.

```powershell
$data | ConvertTo-Json -Depth 10 |
    Set-Content -LiteralPath $OutputPath -Encoding utf8NoBOM
```

La configuración regional puede afectar la clasificación y las expresiones regulares en las herramientas Bash. Restrinjalo al alcance del comando solo cuando se requiera el orden de bytes para la comparación de máquinas.

```bash
LC_ALL=C sort -- input.txt > output.txt
```

Forzar toda la salida de cara al usuario en la configuración regional `C` puede cambiar el manejo y los mensajes de Unicode, así que aplíquelo solo a los comandos que lo necesiten.

### Cree una automatización reutilizable

Un script idempotente trata "ya existe" como un estado de éxito, compara los estados actual y deseado y realiza solo los cambios necesarios.

Ejemplo de PowerShell:

```powershell
$directory = Join-Path $resolvedWorkspace 'reports'
if (-not (Test-Path -LiteralPath $directory -PathType Container)) {
    New-Item -ItemType Directory -Path $directory | Out-Null
}
```

Ejemplo de golpe:

```bash
install -d -- "$workspace/reports"
```

Una operación de creación externa de API necesita una clave de idempotencia, una comparación del estado actual y deseado y una clasificación de errores reintentables. Reintentar incondicionalmente repite los errores de autenticación o validación y consume solo el límite de velocidad. El retroceso exponencial necesita nerviosismo y una fecha límite general.

## Secuencia de resolución de problemas

Construya un pequeño paquete de evidencia antes de adivinar. No imprima valores secretos.

### 1. Identificar el entorno de ejecución.

Golpe:

```bash
printf 'shell=%s\n' "${BASH_VERSION:-not-bash}"
printf 'cwd=%s\n' "$PWD"
command -V git
git --version
uname -a
```

PowerShell:

```powershell
$PSVersionTable
Get-Location
Get-Command git -All | Select-Object CommandType, Name, Source, Version
git --version
```

### 2. Verifique las entradas y los límites

- Directorio de trabajo y base para el descubrimiento de configuraciones.
- Ruta y versión ejecutable real
- Recuento de argumentos y citas.
- Comprobar sólo si existen variables de entorno; no imprimir sus valores
- Existencia de archivos, tamaño, permisos, finales de línea y codificación.
- Si el proceso es un proceso Windows o WSL

### 3. Crea una reproducción mínima.

No intente arreglar el contenedor, la tarea IDE y CI todos a la vez. Ejecute el mismo ejecutable y argumentos en un pequeño directorio temporal. Si la reproducción mínima tiene éxito, agregue el entorno y el envoltorio una capa a la vez.

### 4. Utilice el rastreo con moderación

Bash `set -x` y PowerShell `Set-PSDebug -Trace 1` pueden exponer secretos imprimiendo argumentos ampliados. Habilítelos solo para la sección más pequeña en un entorno local protegido y desactívelos antes de los comandos que contengan credenciales. No habilite el registro de depuración CI junto con los secretos de producción.

### 5. Preservar códigos de salida y stderr

No se trague fallas con `|| true` al final de una tubería o PowerShell `catch {}` amplia. Clasifique solo los errores específicos que sean aceptables y propague todos los demás a la persona que llama conservando el código de salida y el contexto originales.

## Lista de verificación de verificación

- [] ¿Se especifican los sistemas operativos, shells y versiones de shell compatibles?
- [] ¿Se aplican el modo estricto de Bash y la política de error de terminación de PowerShell?
- [] ¿La salida distinta de cero de un comando nativo se propaga como una falla en la canalización?
- [] ¿Las rutas y las entradas del usuario se mantienen fuera de los comandos creados en cadenas y de `eval`?
- [] ¿Los resultados estándar están separados de los diagnósticos estándar?
- [] ¿La salida de la máquina utiliza JSON con una versión de esquema?
- [] ¿Se definen los finales de línea con `.gitattributes` y se verifica el bit ejecutable en Linux CI?
- [] ¿Se especifica la codificación UTF-8 y el alcance local requerido?
- [] ¿Se realiza la conversión de ruta Windows/WSL en un único límite de adaptador?
- [] ¿Se puede volver a ejecutar el script y valida específicamente objetivos destructivos?
- [] ¿Los reintentos tienen clasificación de errores, retroceso, fluctuación y fecha límite?
- [] ¿Los registros y rastreos están libres de tokens, credenciales e información personal?

Establezca la matriz de prueba mínima de acuerdo con el contrato de soporte real. Por ejemplo, pruebe Linux+Bash y Windows+PowerShell, agregando la integración de WSL solo cuando sea necesario. Separe los límites de falla en lugar de anidar cada combinación en un solo trabajo.

## Casos de falla y limitaciones

### Suponiendo que `set -e` detecte todos los fallos de Bash

El comportamiento puede ser poco intuitivo dependiendo de contextos como `if`, `while`, `&&` y la sustitución de comandos. Haga que las condiciones y el manejo de errores sean explícitos para los comandos importantes y utilice un linter de shell y pruebas.

### Confiando en el análisis de cadenas en PowerShell

Si la salida del cmdlet se representa como texto para mostrar y luego se vuelve a leer con una expresión regular, la configuración regional y el formato lo interrumpirán. Conserve las propiedades del objeto y serialícelo en JSON en un límite de transferencia externo.

### Mezclar aleatoriamente herramientas WSL y Windows en el mismo árbol de trabajo

La configuración de Git, los observadores de archivos, los permisos, la ruta y los archivos bloqueados pueden entrar en conflicto. Elija el entorno de ejecución principal del repositorio y el propietario de Git, y acceda a él desde otros entornos a través de adaptadores explícitos.

### Implementando toda la lógica en Shell

Los shells destacan en la orquestación breve, pero pasan a un CLI de uso general cuando se requieren análisis complejos, concurrencia, validación de dominio y pruebas unitarias. Mantenga la cáscara como una capa de pegamento.

### Definición multiplataforma como "el mismo comando"

Lo que importa no es una sintaxis idéntica sino un contrato de resultado idéntico. Incluso cuando los adaptadores específicos de OS- difieren, el sistema es más fácil de mantener si los códigos de salida, los esquemas de JSON, la idempotencia y las reglas de seguridad siguen siendo los mismos.

El mismo principio se aplica a la resolución de problemas. Verificar el shell, el ejecutable, los argumentos, el sistema de archivos y el resultado del proceso, una capa a la vez, convierte la categoría vaga de un "problema ambiental" en una causa reproducible.
