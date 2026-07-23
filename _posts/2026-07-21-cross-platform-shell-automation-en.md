---
title: "Cross-Platform Automation and Troubleshooting with PowerShell, Bash, Windows, and WSL"
date: 2026-07-21 09:50:00 +0900
categories: [Platform Engineering, Automation]
tags: [powershell, bash, windows, wsl, scripting, troubleshooting]
description: Separate differences in shells, processes, paths, and encodings, and design Bash and PowerShell automation that fails immediately and can be rerun safely.
lang: en
hidden: true
translation_key: cross-platform-shell-automation
---

{% include language-switcher.html %}

## The Problem: Commands That Look the Same Have Different Executors and Data Rules

When moving among Windows, WSL, and Linux CI, the idea that “only the path needs to change” often breaks down. The cause usually lies in one of four layers.

- Which shell interprets the syntax?
- Which executable is actually selected?
- How are arguments split and quoted from a string?
- How do filesystem, encoding, line-ending, and permission semantics differ?

For example, a PowerShell pipeline passes objects, while a Bash pipeline passes byte streams. The meaning of the PowerShell alias `curl` has also differed by version, and WSL's `/mnt/c/...` has different performance and permission semantics from a Linux filesystem.

The goal of cross-platform automation is not to force one file to run in every shell. It is to **define a shared command contract and implement that contract precisely in each shell**.

## Mental Model: A Shell Is Both a Process Launcher and a Language

A command line passes through these stages.

```text
source text
  -> shell parsing/expansion
  -> executable resolution
  -> argument vector + environment + working directory
  -> process exit code + stdout + stderr
```

When diagnosing a failure, isolate which stage is wrong.

### Bash centers on text streams

```bash
producer | filter | consumer
```

Each process normally sends a stdout byte stream to the next process's stdin. Parsing may change with spaces, newlines, NUL characters, and locale. Treating file names as line-oriented text can corrupt names containing newlines.

### PowerShell centers on object pipelines

```powershell
Get-Process | Where-Object CPU -gt 10 | Select-Object Name, CPU
```

Between cmdlets rather than native commands, structured .NET objects flow through the pipeline. Converting them to `Format-Table` output or strings too early makes subsequent filtering and serialization difficult. Put output formatting at the end of the pipeline.

### Make the success and failure contract explicit

An automatable command needs at least the following contract.

- Exit code `0` on success and nonzero on failure
- Normal results on stdout and diagnostics on stderr
- Machine-readable output with a stable schema, such as JSON
- Destructive operations require an explicit flag and a validated target
- Idempotency so rerunning produces the same final state
- Cleanup behavior on timeout and cancellation

Use the exit code instead of searching logs for the string “ERROR.” Conversely, a CLI that exits with `0` while recording partial failures only in logs is difficult to automate.

## Practical Patterns: Per-Shell Strict Modes and a Shared Command Contract

### Basic Bash script skeleton

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

Meaning of each strict option:

- `-e`: exit on an unhandled failure of a simple command. It is not universal because conditional expressions and other contexts are exceptions.
- `-u`: treat a reference to an unset variable as an error.
- `-o pipefail`: propagate failure of an intermediate command as failure of the pipeline.
- `-E`: helps functions and subshells inherit the `ERR` trap.

Double-quote variables by default, and use `--` with commands that support it to distinguish options from paths. Use an array instead of constructing a shell command as a string and passing it to `eval`.

```bash
command=(python -m pytest -q)
if [[ "${RUN_SLOW_TESTS:-0}" == '1' ]]; then
  command+=(--runslow)
fi
command+=(-- "$workspace/tests")

"${command[@]}"
```

An array preserves argument boundaries even when paths contain spaces or wildcard characters.

### Basic PowerShell script skeleton

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

Key differences:

- `Set-StrictMode` catches undefined variables and some invalid property access.
- `$ErrorActionPreference = 'Stop'` makes non-terminating PowerShell errors behave as terminating errors.
- PowerShell 7.3+'s `$PSNativeCommandUseErrorActionPreference` connects a native command's nonzero exit to PowerShell's error flow.
- `-LiteralPath` treats characters such as `[` and `*` as literal path characters rather than wildcards.
- Run an external process with the call operator `&` and pass arguments as individual values.

If older PowerShell versions must be supported, explicitly inspect the exit code immediately after a native command.

```powershell
& <NATIVE_COMMAND> <ARGUMENT_1> <ARGUMENT_2>
if ($LASTEXITCODE -ne 0) {
    throw "native command failed with exit code $LASTEXITCODE"
}
```

Replace `<...>` with the actual command and arguments. `$?` and `$LASTEXITCODE` have different meanings, with behavioral differences among versions, so pin and test the target PowerShell version for native automation.

### Give the shared CLI a JSON contract

If Bash and PowerShell wrappers each implement complex business logic, they will soon diverge. Put the core logic in a testable CLI written in Python, Go, .NET, or another general-purpose language, and let the shell handle only environment setup and invocation.

```text
tool inspect --workspace <PATH> --format json
```

Example successful output:

```json
{
  "schema_version": 1,
  "status": "ok",
  "checks": [
    {"name": "configuration", "passed": true}
  ]
}
```

Parse it as an object in PowerShell.

```powershell
$result = & tool inspect --workspace $resolvedWorkspace --format json |
    ConvertFrom-Json

if ($result.schema_version -ne 1 -or $result.status -ne 'ok') {
    throw 'inspection failed or returned an unsupported schema'
}
```

If Bash needs to read a field, use a validated JSON parser. Do not parse JSON with `grep` and `sed`.

### Convert Windows and WSL paths only at the boundary

| Meaning | Windows | WSL |
|---|---|---|
| Example user project | `C:\work\project` | `/mnt/c/work/project` |
| Project in Linux home | Not applicable | `/home/<USER>/project` |
| Path separator | `\` or, depending on the API, `/` | `/` |
| Example executable | `tool.exe` | Linux ELF `tool` |

When a Windows path is needed in WSL, use `wslpath` instead of manual string replacement.

```bash
windows_path='C:\work\project'
linux_path="$(wslpath -u -- "$windows_path")"
printf '%s\n' "$linux_path"
```

In the other direction:

```bash
windows_path="$(wslpath -w -- "$PWD")"
printf '%s\n' "$windows_path"
```

Do not repeatedly convert paths back and forth. Convert once at the adapter boundary where a Windows process is called. Linux workloads with many builds, package installations, and Git operations are usually more stable in metadata I/O and permission behavior when run inside WSL's Linux filesystem. Validate Windows IDE access and backup policies separately.

### Define line endings and executable bits in the repository

Example `.gitattributes`:

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

PowerShell 7 can also process LF, so choose CRLF for `.ps1` according to compatibility with team tools. The essential point is to define a consistent repository policy instead of leaving it to each developer's `core.autocrlf` setting.

A script's executable bit on Linux is also Git metadata.

```bash
git update-index --chmod=+x scripts/check.sh
git diff --summary
```

Because the executable bit is less visible on Windows filesystems, verify actual execution in Linux CI. Testing only with `bash script.sh` can hide shebang or executable-bit problems.

### Specify encoding and locale

Use UTF-8 by default for structured files, and specify the encoding in both producer and consumer. Do not rely on differences in the default output encoding among PowerShell versions.

```powershell
$data | ConvertTo-Json -Depth 10 |
    Set-Content -LiteralPath $OutputPath -Encoding utf8NoBOM
```

Locale can affect sorting and regular expressions in Bash tools. Restrict it to the command scope only when byte ordering is required for machine comparison.

```bash
LC_ALL=C sort -- input.txt > output.txt
```

Forcing all user-facing output into the `C` locale can change Unicode handling and messages, so apply it only to the commands that need it.

### Build rerunnable automation

An idempotent script treats “already exists” as a success state, compares current and desired states, and makes only the necessary changes.

PowerShell example:

```powershell
$directory = Join-Path $resolvedWorkspace 'reports'
if (-not (Test-Path -LiteralPath $directory -PathType Container)) {
    New-Item -ItemType Directory -Path $directory | Out-Null
}
```

Bash example:

```bash
install -d -- "$workspace/reports"
```

An external API creation operation needs an idempotency key, comparison of desired and current state, and classification of retryable errors. Retrying unconditionally repeats authentication or validation errors and consumes only the rate limit. Exponential backoff needs jitter and an overall deadline.

## Troubleshooting Sequence

Build a small evidence bundle before guessing. Do not print secret values.

### 1. Identify the execution environment

Bash:

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

### 2. Check inputs and boundaries

- Working directory and the base for configuration discovery
- Actual executable path and version
- Argument count and quoting
- Check only whether environment variables exist; do not print their values
- File existence, size, permissions, line endings, and encoding
- Whether the process is a Windows or WSL process

### 3. Create a minimal reproduction

Do not try to fix the wrapper, IDE task, and CI all at once. Run the same executable and arguments in a small temporary directory. If the minimal reproduction succeeds, add the environment and wrapper back one layer at a time.

### 4. Use tracing sparingly

Bash `set -x` and PowerShell `Set-PSDebug -Trace 1` can expose secrets by printing expanded arguments. Enable them only for the smallest section in a protected local environment, and turn them off before commands containing credentials. Do not enable CI debug logging alongside production secrets.

### 5. Preserve exit codes and stderr

Do not swallow failures with `|| true` at the end of a pipeline or a broad PowerShell `catch {}`. Classify only the specific errors that are acceptable, and propagate all others to the caller while preserving the original exit code and context.

## Verification Checklist

- [ ] Are supported operating systems, shells, and shell versions specified?
- [ ] Are Bash strict mode and PowerShell's terminating-error policy applied?
- [ ] Does a native command's nonzero exit propagate as a pipeline failure?
- [ ] Are paths and user input kept out of string-built commands and `eval`?
- [ ] Are stdout results separated from stderr diagnostics?
- [ ] Does machine output use JSON with a schema version?
- [ ] Are line endings defined with `.gitattributes`, and is the executable bit verified in Linux CI?
- [ ] Are UTF-8 encoding and any required locale scope specified?
- [ ] Is Windows/WSL path conversion performed at a single adapter boundary?
- [ ] Is the script rerunnable, and does it specifically validate destructive targets?
- [ ] Do retries have error classification, backoff, jitter, and a deadline?
- [ ] Are logs and traces free of tokens, credentials, and personal information?

Set the minimum test matrix according to the actual support contract. For example, test Linux+Bash and Windows+PowerShell, adding WSL integration only when needed. Separate failure boundaries instead of nesting every combination in one job.

## Failure Cases and Limitations

### Assuming `set -e` catches every Bash failure

Behavior can be unintuitive depending on contexts such as `if`, `while`, `&&`, and command substitution. Make conditions and error handling explicit for important commands, and use a shell linter and tests.

### Relying on string parsing in PowerShell

If cmdlet output is rendered as display text and then read back with a regular expression, locale and formatting will break it. Preserve object properties and serialize to JSON at an external handoff boundary.

### Randomly mixing WSL and Windows tools in the same working tree

Git configuration, file watchers, permissions, path case, and lock files can conflict. Choose the repository's primary execution environment and Git owner, and access it from other environments through explicit adapters.

### Implementing all logic in shell

Shells excel at short orchestration, but move to a general-purpose CLI when complex parsing, concurrency, domain validation, and unit tests are required. Keep the shell as a glue layer.

### Defining cross-platform as “the same command”

What matters is not identical syntax but an identical result contract. Even when OS-specific adapters differ, the system is easier to maintain if exit codes, JSON schemas, idempotency, and security rules remain the same.

The same principle applies to troubleshooting. Checking the shell, executable, arguments, filesystem, and process result one layer at a time turns the vague category of an “environment problem” into a reproducible cause.
