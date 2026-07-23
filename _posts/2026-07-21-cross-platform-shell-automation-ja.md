---
title: "PowerShell・Bash・Windows・WSLのクロスプラットフォーム自動化と障害診断"
date: 2026-07-21 09:50:00 +0900
categories: [Platform Engineering, Automation]
tags: [powershell, bash, windows, wsl, scripting, troubleshooting]
description: shell・process・path・encodingの違いを分離し、BashとPowerShellの自動化を、失敗時に直ちに停止して再実行できる形で設計します。
lang: ja-JP
translation_key: cross-platform-shell-automation
hidden: true
---

{% include language-switcher.html %}

## 問題：同じcommandに見えても実行主体とデータ規則は異なる

Windows、WSL、Linux CIを行き来すると、「pathだけ変えればよい」という方法は頻繁に破綻する。原因は通常、次の四層のいずれかにある。

- どのshellが構文を解釈するか。
- どのexecutableが実際に選ばれたか。
- argumentが文字列からどのように分割・引用されたか。
- filesystem、encoding、line ending、権限の意味がどう違うか。

たとえばPowerShellのpipelineはobjectを渡すが、Bash pipelineはbyte streamを渡す。PowerShell alias `curl` の意味はversionにより異なった時期があり、WSLの `/mnt/c/...` はLinux filesystemとは性能・権限semanticsが異なる。

クロスプラットフォーム自動化の目標は、すべてのshellで同じ一ファイルを無理に実行することではない。**共通のcommand contractを定義し、各shellでその契約を正確に実装すること**である。

## Mental model：shellはprocess実行器であり独自言語でもある

一行のcommandは次の段階を通る。

```text
source text
  -> shell parsing/expansion
  -> executable resolution
  -> argument vector + environment + working directory
  -> process exit code + stdout + stderr
```

障害診断では、どの段階が誤っているかを分離する。

### Bashはtext stream中心である

```bash
producer | filter | consumer
```

各processは通常、stdout byte streamを次のprocessのstdinへ送る。空白、newline、NUL、localeによりparsingは変わり得る。ファイル名を行単位textとして扱うと、newlineを含む名前を壊す可能性がある。

### PowerShellはobject pipeline中心である

```powershell
Get-Process | Where-Object CPU -gt 10 | Select-Object Name, CPU
```

native commandではなくcmdlet間では、構造化された.NET objectが流れる。早すぎる段階で `Format-Table` や文字列へ変えると、後続のfilteringとserializationが難しくなる。出力formattingはpipelineの末尾に置く。

### 成功と失敗の契約を明示する

自動化可能なcommandには最低でも次の契約が必要である。

- 成功時はexit code `0`、失敗時はnon-zero
- 正常結果はstdout、診断はstderr
- machine-readable outputはJSONなど安定したschema
- destructive操作には明示flagと検証済みtargetを要求
- 再実行しても同じ最終状態となるidempotency
- timeoutとcancel時のcleanup動作

log内の「ERROR」という文字列ではなくexit codeを使う。一方、exit code `0` のまま部分障害をlogにしか書かないCLIは自動化しにくい。

## 実践pattern：shell別strict modeと共通command contract

### Bash scriptの基本骨格

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

各strict optionの意味：

- `-e`：未処理の単純command失敗で終了する。条件文など例外contextがあり万能ではない。
- `-u`：未設定variable参照をエラーにする。
- `-o pipefail`：pipeline途中のcommand失敗もpipeline失敗として伝える。
- `-E`：function・subshellでも `ERR` trapの継承を助ける。

variableは原則double quoteし、optionとpathを分ける `--` に対応するcommandではそれを使う。shell commandを文字列で組み立てて `eval` せず、arrayを使う。

```bash
command=(python -m pytest -q)
if [[ "${RUN_SLOW_TESTS:-0}" == '1' ]]; then
  command+=(--runslow)
fi
command+=(-- "$workspace/tests")

"${command[@]}"
```

arrayはpathに空白やwildcard文字があってもargument境界を保つ。

### PowerShell scriptの基本骨格

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

主な違い：

- `Set-StrictMode` は未定義variableと一部の不正property accessを検出する。
- `$ErrorActionPreference = 'Stop'` はnon-terminating PowerShell errorをterminating errorとして扱う。
- PowerShell 7.3+の `$PSNativeCommandUseErrorActionPreference` はnative commandのnon-zero exitをPowerShell error flowへつなぐ。
- `-LiteralPath` は `[` や `*` をwildcardでなく実path文字として扱う。
- 外部processはcall operator `&` で実行し、argumentを個別値として渡す。

古いPowerShellも支援するなら、native command直後にexit codeを明示確認する。

```powershell
& <NATIVE_COMMAND> <ARGUMENT_1> <ARGUMENT_2>
if ($LASTEXITCODE -ne 0) {
    throw "native command failed with exit code $LASTEXITCODE"
}
```

`<...>` は実commandとargumentへ置換する。`$?` と `$LASTEXITCODE` は意味が異なり、version別の挙動差もあるため、native automationでは対象PowerShell versionを固定してテストする。

### 共通CLIへJSON契約を置く

BashとPowerShell wrapperが複雑なbusiness logicをそれぞれ実装すると、すぐに差異が生じる。中核ロジックはPython、Go、.NETなどのテスト可能なCLIへ置き、shellは環境準備と呼出しだけを担当する。

```text
tool inspect --workspace <PATH> --format json
```

正常出力例：

```json
{
  "schema_version": 1,
  "status": "ok",
  "checks": [
    {"name": "configuration", "passed": true}
  ]
}
```

PowerShellではobjectとしてparseする。

```powershell
$result = & tool inspect --workspace $resolvedWorkspace --format json |
    ConvertFrom-Json

if ($result.schema_version -ne 1 -or $result.status -ne 'ok') {
    throw 'inspection failed or returned an unsupported schema'
}
```

Bashでfieldを読むなら検証済みJSON parserを使う。`grep` と `sed` でJSONをparseしない。

### WindowsとWSLのpathは境界でのみ変換する

| 意味 | Windows | WSL |
|---|---|---|
| 利用者project例 | `C:\work\project` | `/mnt/c/work/project` |
| Linux home project | 該当なし | `/home/<USER>/project` |
| path separator | `\` またはAPIにより `/` | `/` |
| executable例 | `tool.exe` | Linux ELF `tool` |

WSLでWindows pathが必要なら、手作業の文字列置換より `wslpath` を使う。

```bash
windows_path='C:\work\project'
linux_path="$(wslpath -u -- "$windows_path")"
printf '%s\n' "$linux_path"
```

逆方向：

```bash
windows_path="$(wslpath -w -- "$PWD")"
printf '%s\n' "$windows_path"
```

pathを何度も往復変換せず、Windows processを呼ぶadapter境界で一度だけ変換する。build、package install、Git operationが多いLinux workloadは、通常WSLのLinux filesystem内で行う方がmetadata I/Oと権限動作が安定する。Windows IDEのアクセス方法とbackup policyは別途検証する。

### line endingとexecutable bitをリポジトリで決める

`.gitattributes` の例：

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

PowerShell 7はLFも処理できるため、`.ps1` のCRLFはteam tool互換性に応じて選ぶ。重要なのは、開発者ごとの `core.autocrlf` に任せずrepository policyで一貫して決めることである。

Linuxではscriptのexecutable bitもGit metadataである。

```bash
git update-index --chmod=+x scripts/check.sh
git diff --summary
```

Windows filesystemでは実行bitを意識しにくいため、Linux CIで実行自体を検証する。`bash script.sh` だけのテストはshebangやexecutable bit問題を隠し得る。

### encodingとlocaleを明示する

構造化fileはUTF-8を既定とし、producerとconsumerの双方でencodingを指定する。PowerShell version別のdefault output encodingに依存しない。

```powershell
$data | ConvertTo-Json -Depth 10 |
    Set-Content -LiteralPath $OutputPath -Encoding utf8NoBOM
```

Bash toolのsortと正規表現はlocaleの影響を受け得る。machine comparisonでbyte-orderが必要な場合だけcommand scopeへ限定する。

```bash
LC_ALL=C sort -- input.txt > output.txt
```

利用者表示全体を強制的に `C` localeへ変えるとUnicode処理とmessageが変わるため、必要なcommandだけに適用する。

### 再実行可能なautomationを作る

idempotent scriptは「すでに存在」を成功状態として解釈し、現在状態とdesired stateを比較して必要な変更だけを行う。

PowerShell例：

```powershell
$directory = Join-Path $resolvedWorkspace 'reports'
if (-not (Test-Path -LiteralPath $directory -PathType Container)) {
    New-Item -ItemType Directory -Path $directory | Out-Null
}
```

Bash例：

```bash
install -d -- "$workspace/reports"
```

外部APIの作成操作にはidempotency key、desired/current state比較、retry可能エラー分類が必要である。無条件retryは認証・validationエラーを反復しrate limitだけを消費する。exponential backoffにはjitterと全体deadlineを置く。

## 障害診断の順序

推測する前に小さな証拠集合を作る。秘密値は出力しない。

### 1. 実行環境の識別

Bash：

```bash
printf 'shell=%s\n' "${BASH_VERSION:-not-bash}"
printf 'cwd=%s\n' "$PWD"
command -V git
git --version
uname -a
```

PowerShell：

```powershell
$PSVersionTable
Get-Location
Get-Command git -All | Select-Object CommandType, Name, Source, Version
git --version
```

### 2. 入力と境界を確認

- working directoryとconfig探索基準
- 実際のexecutable pathとversion
- argument数と引用
- environment variableは存在のみ確認し、値を出力しない
- fileの存在、サイズ、権限、line ending、encoding
- Windows processかWSL processか

### 3. 最小再現

wrapper、IDE task、CIを一度に直さず、同じexecutableとargumentを小さな一時directoryで実行する。最小再現が成功したらenvironmentとwrapperを一層ずつ戻す。

### 4. tracingは限定的に使う

Bash `set -x` とPowerShell `Set-PSDebug -Trace 1` は展開済みargumentを出力し、secretを露出し得る。保護されたlocal環境の最小区間だけで有効にし、credentialを含むcommand前には無効化する。CI debug loggingを運用secretと同時に有効化しない。

### 5. exit codeとstderrを保持する

pipeline末尾の `|| true`、PowerShellの広い `catch {}` で失敗を握り潰さない。許容できる特定エラーだけを分類し、その他は元のexit codeとcontextを保って上位呼出側へ渡す。

## 検証チェックリスト

- [ ] 対応OS、shell、shell versionを明示した。
- [ ] Bash strict modeとPowerShell terminating error policyを適用した。
- [ ] native commandのnon-zero exitがpipeline失敗として伝わる。
- [ ] pathと利用者入力を文字列commandで組み立てたり `eval` したりしない。
- [ ] stdout結果とstderr診断が分離されている。
- [ ] machine outputにschema version付きJSONを使う。
- [ ] `.gitattributes` でline endingを決め、Linux CIでexecutable bitを検証する。
- [ ] UTF-8 encodingと必要なlocale scopeを明示した。
- [ ] Windows/WSL path変換はadapter境界の一箇所で行う。
- [ ] scriptが再実行可能で、destructive targetを具体的に検証する。
- [ ] retryにエラー分類、backoff、jitter、deadlineがある。
- [ ] logとtraceにtoken、credential、個人情報がない。

最小test matrixは実際の対応契約に合わせる。たとえばLinux+Bash、Windows+PowerShell、必要時のみWSL integrationを追加する。全組合せを一jobへ入れ子にせず、障害境界を分ける。

## 失敗例と限界

### `set -e` だけですべてのBash失敗を検出できると考える

`if`、`while`、`&&`、command substitutionなどcontextにより挙動は直観と異なり得る。重要commandは条件とerror handlingを明示し、shell linterとtestを使う。

### PowerShellで文字列parsingへ依存する

cmdlet outputを画面用文字列にしてからregexで読み直すと、localeとformattingで壊れる。object propertyを維持し、外部受渡し境界でJSONへserializeする。

### WSLとWindows toolを同じ作業treeで無作為に混ぜる

Git設定、file watcher、permission、path case、lock fileが衝突し得る。リポジトリの主実行環境とGit所有者を決め、別環境は明示adapterでアクセスする。

### すべてのロジックをshellで実装する

短いorchestrationにはshellが優れるが、複雑なparsing、concurrency、domain validation、unit testが必要なら一般言語のCLIへ移す。shellはglue layerに保つ。

### クロスプラットフォームを「同一command」と定義する

重要なのは構文の同一性ではなく、結果契約の同一性である。OS別adapterが異なってもexit code、JSON schema、idempotency、security ruleが同じなら保守しやすい。

障害診断も同じ原理である。shell、executable、argument、filesystem、process resultを一層ずつ確認すれば、「環境問題」という曖昧な分類を再現可能な原因へ変えられる。
