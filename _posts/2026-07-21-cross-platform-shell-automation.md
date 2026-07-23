---
title: "PowerShell·Bash·Windows·WSL 크로스플랫폼 자동화와 장애 진단"
date: 2026-07-21 09:50:00 +0900
categories: [Platform Engineering, Automation]
tags: [powershell, bash, windows, wsl, scripting, troubleshooting]
description: shell·프로세스·경로·인코딩의 차이를 분리하고 Bash와 PowerShell 자동화를 실패 즉시 중단되고 재실행 가능한 형태로 설계합니다.
lang: ko-KR
translation_key: cross-platform-shell-automation
---

{% include language-switcher.html %}

## 문제: 같은 명령처럼 보여도 실행 주체와 데이터 규칙이 다르다

Windows, WSL, Linux CI를 오가면 “경로만 바꾸면 된다”는 접근이 자주 깨진다. 문제의 원인은 보통 네 층 중 하나다.

- 어느 shell이 문법을 해석하는가?
- 어떤 executable이 실제로 선택됐는가?
- argument가 문자열에서 어떻게 분리·인용됐는가?
- filesystem, encoding, line ending, 권한의 의미가 어떻게 다른가?

예를 들어 PowerShell의 pipeline은 객체를 전달하지만 Bash pipeline은 byte stream을 전달한다. PowerShell alias `curl`의 의미가 version에 따라 달랐던 적도 있고, WSL의 `/mnt/c/...`는 Linux filesystem과 성능·권한 semantics가 다르다.

크로스플랫폼 자동화의 목표는 모든 shell에서 같은 파일 하나를 억지로 실행하는 것이 아니다. **공통된 command contract를 정의하고 각 shell에서 그 계약을 정확하게 구현하는 것**이다.

## Mental model: shell은 process 실행기이자 자체 언어다

명령 한 줄은 다음 단계를 거친다.

```text
source text
  -> shell parsing/expansion
  -> executable resolution
  -> argument vector + environment + working directory
  -> process exit code + stdout + stderr
```

장애를 진단할 때 어느 단계가 틀렸는지 분리한다.

### Bash는 text stream 중심이다

```bash
producer | filter | consumer
```

각 process는 보통 stdout byte stream을 다음 process의 stdin으로 보낸다. 공백, newline, NUL, locale에 따라 parsing이 달라질 수 있다. 파일 이름을 line 단위 text로 다루면 newline이 든 이름을 깨뜨릴 수 있다.

### PowerShell은 object pipeline 중심이다

```powershell
Get-Process | Where-Object CPU -gt 10 | Select-Object Name, CPU
```

native command가 아니라 cmdlet 사이에서는 구조화된 .NET 객체가 흐른다. 너무 일찍 `Format-Table`이나 문자열로 바꾸면 이후 filtering과 serialization이 어려워진다. 출력 formatting은 pipeline의 마지막에 둔다.

### 성공과 실패의 계약을 명시한다

자동화 가능한 명령은 최소한 다음 계약을 가져야 한다.

- 성공 시 exit code `0`, 실패 시 non-zero
- 정상 결과는 stdout, 진단은 stderr
- machine-readable output은 JSON 등 안정된 schema
- destructive 동작은 명시적 flag와 검증된 target 요구
- 재실행해도 같은 최종 상태가 되는 idempotency
- timeout과 취소 시 정리 동작

log에 “ERROR” 문자열이 있는지 찾는 대신 exit code를 사용한다. 반대로 exit code `0`인데 부분 실패를 log에만 쓰는 CLI는 자동화하기 어렵다.

## 실전 패턴: shell별 strict mode와 공통 command contract

### Bash script 기본 골격

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

각 strict option의 의미:

- `-e`: 처리하지 않은 단순 command 실패에서 종료. 조건문 등 예외 문맥이 있으므로 만능은 아니다.
- `-u`: 설정되지 않은 variable 참조를 오류로 처리.
- `-o pipefail`: pipeline 중간 command 실패도 pipeline 실패로 전달.
- `-E`: function·subshell에서도 `ERR` trap 상속을 돕는다.

variable을 기본적으로 double quote하고, option과 path를 구분하는 `--`를 지원하는 command에는 사용한다. shell command를 문자열로 조립해 `eval`하지 말고 array를 사용한다.

```bash
command=(python -m pytest -q)
if [[ "${RUN_SLOW_TESTS:-0}" == '1' ]]; then
  command+=(--runslow)
fi
command+=(-- "$workspace/tests")

"${command[@]}"
```

array는 path에 공백이나 wildcard 문자가 있어도 argument 경계를 보존한다.

### PowerShell script 기본 골격

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

핵심 차이:

- `Set-StrictMode`는 정의되지 않은 variable과 일부 잘못된 property 접근을 잡는다.
- `$ErrorActionPreference = 'Stop'`은 non-terminating PowerShell error를 terminating error로 다루게 한다.
- PowerShell 7.3+의 `$PSNativeCommandUseErrorActionPreference`는 native command의 non-zero exit를 PowerShell error 흐름에 연결한다.
- `-LiteralPath`는 `[`와 `*` 같은 문자를 wildcard가 아니라 실제 path 문자로 취급한다.
- 외부 process는 call operator `&`로 실행하고 argument를 개별 값으로 전달한다.

구형 PowerShell을 지원해야 한다면 native command 직후 exit code를 명시적으로 확인한다.

```powershell
& <NATIVE_COMMAND> <ARGUMENT_1> <ARGUMENT_2>
if ($LASTEXITCODE -ne 0) {
    throw "native command failed with exit code $LASTEXITCODE"
}
```

`<...>`는 실제 command와 argument로 교체한다. `$?`와 `$LASTEXITCODE`는 의미가 다르고 version별 동작 차이가 있으므로 native automation에서는 대상 PowerShell version을 고정하고 테스트한다.

### 공통 CLI에 JSON 계약을 둔다

Bash와 PowerShell wrapper가 복잡한 business logic을 각각 구현하면 곧 달라진다. 핵심 로직은 Python, Go, .NET 등의 테스트 가능한 CLI에 두고 shell은 환경 준비와 호출만 담당한다.

```text
tool inspect --workspace <PATH> --format json
```

정상 출력 예시:

```json
{
  "schema_version": 1,
  "status": "ok",
  "checks": [
    {"name": "configuration", "passed": true}
  ]
}
```

PowerShell에서는 object로 파싱한다.

```powershell
$result = & tool inspect --workspace $resolvedWorkspace --format json |
    ConvertFrom-Json

if ($result.schema_version -ne 1 -or $result.status -ne 'ok') {
    throw 'inspection failed or returned an unsupported schema'
}
```

Bash에서 field를 읽어야 한다면 검증된 JSON parser를 사용한다. `grep`과 `sed`로 JSON을 파싱하지 않는다.

### Windows와 WSL 경로를 경계에서만 변환한다

| 의미 | Windows | WSL |
|---|---|---|
| 사용자 project 예 | `C:\work\project` | `/mnt/c/work/project` |
| Linux home project | 해당 없음 | `/home/<USER>/project` |
| path separator | `\` 또는 API에 따라 `/` | `/` |
| executable 예 | `tool.exe` | Linux ELF `tool` |

WSL에서 Windows path가 필요하면 수동 문자열 치환보다 `wslpath`를 사용한다.

```bash
windows_path='C:\work\project'
linux_path="$(wslpath -u -- "$windows_path")"
printf '%s\n' "$linux_path"
```

반대 방향:

```bash
windows_path="$(wslpath -w -- "$PWD")"
printf '%s\n' "$windows_path"
```

경로를 여러 번 왕복 변환하지 말고 Windows process를 호출하는 adapter 경계에서 한 번만 변환한다. build, package install, Git operation이 많은 Linux workload는 대개 WSL의 Linux filesystem 안에서 수행하는 편이 metadata I/O와 권한 동작이 안정적이다. Windows IDE 접근 방식과 backup 정책은 별도로 검증한다.

### line ending과 executable bit를 저장소에서 결정한다

`.gitattributes` 예시:

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

PowerShell 7은 LF도 처리할 수 있으므로 `.ps1`의 CRLF는 팀 도구 호환성에 따라 선택한다. 핵심은 개발자별 `core.autocrlf`에 맡기지 않고 repository policy로 일관되게 정하는 것이다.

Linux에서 script executable bit도 Git metadata다.

```bash
git update-index --chmod=+x scripts/check.sh
git diff --summary
```

Windows filesystem에서는 실행 bit 체감이 약하므로 Linux CI에서 실제 실행을 검증한다. `bash script.sh`로만 테스트하면 shebang이나 executable bit 문제를 숨길 수 있다.

### encoding과 locale을 명시한다

구조화된 파일은 UTF-8을 기본으로 하고, producer와 consumer 모두 encoding을 지정한다. PowerShell version별 기본 output encoding 차이에 기대지 않는다.

```powershell
$data | ConvertTo-Json -Depth 10 |
    Set-Content -LiteralPath $OutputPath -Encoding utf8NoBOM
```

Bash 도구의 정렬과 정규식은 locale 영향을 받을 수 있다. machine comparison에서 byte-order가 필요할 때만 command scope에 제한한다.

```bash
LC_ALL=C sort -- input.txt > output.txt
```

사용자 표시 전체를 강제로 `C` locale로 바꾸면 Unicode 처리와 메시지가 달라질 수 있으므로 필요한 command에만 적용한다.

### 재실행 가능한 automation을 만든다

idempotent script는 “이미 존재”를 성공 상태로 해석하고, 현재와 원하는 상태를 비교한 뒤 필요한 변경만 한다.

PowerShell 예시:

```powershell
$directory = Join-Path $resolvedWorkspace 'reports'
if (-not (Test-Path -LiteralPath $directory -PathType Container)) {
    New-Item -ItemType Directory -Path $directory | Out-Null
}
```

Bash 예시:

```bash
install -d -- "$workspace/reports"
```

외부 API 생성 작업에는 idempotency key, desired/current state 비교, retry 가능한 오류 분류가 필요하다. 무조건 retry하면 인증 오류나 validation 오류를 반복하고 rate limit만 소모한다. 지수 backoff에는 jitter와 전체 deadline을 둔다.

## 장애 진단 순서

추측하기 전에 작은 증거 묶음을 만든다. 비밀값은 출력하지 않는다.

### 1. 실행 환경 식별

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

### 2. 입력과 경계 확인

- working directory와 config 탐색 기준
- 실제 executable path와 version
- argument 개수와 인용
- environment variable의 존재 여부만 확인하고 값은 출력하지 않기
- 파일 존재, 크기, 권한, line ending, encoding
- Windows process인지 WSL process인지

### 3. 최소 재현

wrapper, IDE task, CI를 한꺼번에 고치지 말고 같은 executable과 argument를 작은 임시 directory에서 실행한다. 최소 재현이 성공하면 environment와 wrapper를 한 층씩 다시 추가한다.

### 4. tracing은 제한적으로 사용

Bash `set -x`와 PowerShell `Set-PSDebug -Trace 1`은 expansion된 argument를 출력해 secret을 노출할 수 있다. 보호된 로컬 환경에서 최소 구간에만 켜고 credential이 있는 command 전에는 끈다. CI debug logging을 운영 secret과 함께 활성화하지 않는다.

### 5. exit code와 stderr를 보존

pipeline 끝에 `|| true`, PowerShell의 넓은 `catch {}`로 실패를 삼키지 않는다. 허용 가능한 특정 오류만 분류하고, 나머지는 원래 exit code와 context를 유지해 상위 호출자에 전달한다.

## 검증 체크리스트

- [ ] 지원할 OS, shell, shell version을 명시했다.
- [ ] Bash strict mode와 PowerShell terminating error 정책을 적용했다.
- [ ] native command의 non-zero exit가 pipeline 실패로 전달된다.
- [ ] path와 사용자 입력을 문자열 command로 조립하거나 `eval`하지 않는다.
- [ ] stdout 결과와 stderr 진단이 분리돼 있다.
- [ ] machine output에 schema version이 있는 JSON을 사용한다.
- [ ] `.gitattributes`로 line ending을 정하고 Linux CI에서 executable bit를 검증한다.
- [ ] UTF-8 encoding과 필요한 locale scope를 명시했다.
- [ ] Windows/WSL path 변환은 adapter 경계 한 곳에서 한다.
- [ ] script가 재실행 가능하고 destructive target을 구체적으로 검증한다.
- [ ] retry에 오류 분류, backoff, jitter, deadline이 있다.
- [ ] log와 trace에 token, credential, 개인정보가 없다.

최소 test matrix는 실제 지원 계약에 맞게 둔다. 예를 들어 Linux+Bash, Windows+PowerShell, 필요할 때만 WSL integration을 추가한다. 모든 조합을 한 job에서 중첩 실행하기보다 실패 경계를 분리한다.

## 실패 사례와 한계

### `set -e`만으로 모든 Bash 실패를 잡는다고 생각하기

`if`, `while`, `&&`, command substitution 등 문맥에 따라 동작이 직관과 다를 수 있다. 중요한 command는 조건과 오류 처리를 명시하고 shell linter와 test를 사용한다.

### PowerShell에서 문자열 parsing에 의존하기

cmdlet output을 화면 문자열로 만든 뒤 regex로 다시 읽으면 locale과 formatting에 깨진다. object property를 유지하고 외부 전달 경계에서 JSON으로 직렬화한다.

### WSL과 Windows 도구를 같은 작업 트리에서 무작위로 섞기

Git 설정, file watcher, permission, path case, lock file이 충돌할 수 있다. 저장소의 주 실행 환경과 Git 소유자를 정하고, 다른 환경은 명시적 adapter로 접근한다.

### 모든 로직을 shell로 구현하기

짧은 orchestration에는 shell이 뛰어나지만 복잡한 parsing, concurrency, domain validation, unit test가 필요하면 일반 언어의 CLI로 옮긴다. shell은 glue layer로 유지한다.

### 크로스플랫폼을 “동일한 명령어”로 정의하기

중요한 것은 문법 동일성이 아니라 결과 계약의 동일성이다. OS별 adapter가 달라도 exit code, JSON schema, idempotency, 보안 규칙이 같으면 더 유지보수하기 쉽다.

장애 진단 역시 같은 원리다. shell, executable, argument, filesystem, process result를 한 층씩 확인하면 “환경 문제”라는 모호한 범주를 재현 가능한 원인으로 바꿀 수 있다.
