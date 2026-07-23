---
title: "Linux診断の基礎：Process、File、Signal、systemdを証拠として読む"
date: 2026-07-21 12:06:00 +0900
categories: [Linux, Operations]
tags: [linux, diagnostics, processes, signals, systemd]
description: Linux障害に対して再起動から始めず、process、descriptor、filesystem、signal、resource、systemd journalの証拠から原因を絞る手順を整理します。
lang: ja-JP
translation_key: linux-diagnostics-processes-files-signals-systemd
hidden: true
---
{% include language-switcher.html %}

## 問題：再起動は症状を消すが原因を説明しない

Linux serviceが遅い、または応答しないとき、直ちにrestartすれば一時的に復旧することがある。

しかしmemory、descriptor、socket、child process、filesystem、dependencyの証拠も同時に消える可能性がある。

次の誤解は診断を遅らせる。

- CPUが低いのでprocessは正常だと判断する。
- free memoryが少ないのでmemory不足だと断定する。
- fileが存在するので読めると考える。
- `kill` は強制終了そのものだと思う。
- service状態がactiveなので利用者機能も正常だと考える。
- log最後の一行だけを原因として解釈する。
- rootで実行してpermission問題を回避する。

運用診断は `観察 -> 仮説 -> 最小確認 -> 安全な緩和 -> 検証` の順に行う。

## Mental model：processはkernel resourceの集合である

processは単なる実行fileではない。

次を持つ。

- PIDとparent PID
- userとgroup identity
- virtual memory map
- open file descriptor table
- current working directory
- environment
- signal disposition
- namespaceとcgroup membership
- threadとscheduling state

実行fileを置換しても、実行中processのmemory mappingは自動で変わらない。

削除済みfileもdescriptorが開いていればdisk blockを占有し続ける。

### `/proc` は実行中kernelを観察する窓である

`/proc/<pid>/status` は状態とmemory概要を示す。

`/proc/<pid>/fd` はopen descriptorを示す。

`/proc/<pid>/maps` はmemory mappingを示す。

`/proc/<pid>/limits` はresource limitを示す。

読取りにも権限とnamespace境界が適用される。

### file descriptorはfileだけを指さない

regular file、directory、socket、pipe、device、event objectもdescriptorになり得る。

descriptor leakはfile open失敗だけでなく、新規connection失敗として現れることがある。

process limitとsystem-wide limitを同時に見る。

### signalは非同期notificationである

`SIGTERM` は正常終了を要求するcatch可能なsignalである。

`SIGKILL` はprocessが処理も無視もできない。

`SIGHUP` は歴史的にはterminal終了を意味し、daemonがreloadの意味で使うこともあるが、application契約を確認する。

signal伝達の成功とapplication cleanupの成功は異なる。

## Workflow：障害を絞る順序

### Step 1. 利用者症状を固定する

- いつ始まったか。
- 全要求か、特定endpointか。
- timeoutか、即時エラーか。
- 一hostか、fleet全体か。
- 最近deployment・設定・証明書・dependencyの変更があったか。

UTC timestampとcorrelation IDを確保する。

### Step 2. service managerの状態を確認する

```bash
systemctl status example.service --no-pager
systemctl show example.service -p ActiveState -p SubState -p Result -p MainPID
journalctl -u example.service --since "-30 min" --no-pager
```

`active (running)` はmain processが生存しているという意味に近い。

業務要求の成功は保証しない。

unitの `ExecStart`、`User`、`WorkingDirectory`、`EnvironmentFile`、restart policyも確認する。

### Step 3. process treeと状態を見る

```bash
ps -eo pid,ppid,user,stat,etimes,%cpu,%mem,cmd --forest
```

`STAT` の主な手掛かり：

- `R`：実行中またはrunnable
- `S`：interruptible sleep
- `D`：uninterruptible sleep、主にI/O待機
- `T`：stoppedまたはtraced
- `Z`：zombie

zombieは既に終了したがparentが終了状態を回収していないchildである。

zombie自体はmemoryをほぼ使わないが、継続的増加はparent bugの信号である。

### Step 4. CPUとschedulerを分けて見る

load averageはCPU使用率と同じではない。

runnable taskと一部uninterruptible taskが含まれ得る。

```bash
uptime
vmstat 1
pidstat -p <PID> 1
```

user CPU、system CPU、I/O wait、context switchを合わせて見る。

containerではcgroup quotaによりthrottlingされ得る。

host CPUが残っていてもworkloadは制限される場合がある。

### Step 5. memoryを構成要素として見る

Linuxは余剰memoryをpage cacheへ使う。

`free` のavailable推定値も見る。

```bash
free -h
cat /proc/<PID>/status
cat /proc/<PID>/smaps_rollup
```

RSS、virtual size、anonymous memory、file-backed mapping、shared memoryを区別する。

OOM killの有無はkernel journalとcgroup eventで確認する。

```bash
journalctl -k --since "-1 hour" --no-pager
```

### Step 6. descriptorとsocketを確認する

```bash
ls -l /proc/<PID>/fd
cat /proc/<PID>/limits
ss -lntp
ss -antp
```

descriptor数の推移とlimitを比較する。

connection stateが `SYN-SENT`、`CLOSE-WAIT`、`TIME-WAIT` のどこに集中するかを見る。

`CLOSE-WAIT` の蓄積は、peer終了後にapplicationがsocketを閉じていない手掛かりになり得る。

### Step 7. filesystem容量とinodeを分ける

```bash
df -h
df -i
findmnt
```

byte容量が残っていてもinodeは枯渇し得る。

削除されたopen fileはdirectory一覧にないが容量を占有する。

```bash
lsof +L1
```

mount option、read-only remount、network filesystem latencyも確認する。

### Step 8. permissionをpath全体で見る

file modeだけでは不十分である。

各親directoryにtraverse権限が必要である。

```bash
namei -l /path/to/resource
id example-user
getfacl /path/to/resource
```

SELinuxまたはAppArmorを使用しているならMAC policy denialも確認する。

root実行は原因確認を難しくし、権限境界を壊す可能性がある。

### Step 9. I/Oとsyscallを最小範囲で観察する

```bash
iostat -xz 1
strace -f -p <PID> -tt -T
```

`strace` にはoverheadと機密データ露出の可能性がある。

短時間、必要なsyscallだけをfilterし、運用policyに従う。

`perf`、eBPF toolにも同じ安全原則を適用する。

### Step 10. 安全に終了する

まずservice manager経由で終了する。

```bash
systemctl stop example.service
```

必要ならSIGTERMを送り、grace period中に状態を観察する。

SIGKILLは最後の手段である。

強制終了前にstack、log、descriptor、core dump policyなど必要証拠を確保する。

## systemd unitを読む基準

### dependencyとorderingは異なる

`After=` は開始順を定義するが、dependencyの必要性を自動では追加しない。

`Requires=` と `Wants=` はdependency関係を表す。

networkが `online` でもapplication dependencyが実際にreadyとは限らない。

### restart policyは障害を隠し得る

`Restart=on-failure` は一時crashの復旧を助ける。

ただし高速crash loopがdependencyへ負荷を与える可能性がある。

start rate limitとbackoffを確認する。

反復restart数と最終exit reasonにalertを置く。

### 実行環境はinteractive shellと異なる

PATH、working directory、environment、umask、limitが異なり得る。

shell profileが自動読込みされると仮定しない。

unit fileへ必要pathを明記する。

secretをunit sourceやcommand lineへ露出しない。

## 実践例：serviceはactiveだがAPIがtimeoutする

1. 合成要求でendpointとtimestampを固定する。
2. `systemctl show` でMainPIDとrestart履歴を見る。
3. journalから同時刻のtimeoutとdependency errorを探す。
4. `ss` でoutbound connection stateを見る。
5. `/proc/<pid>/fd` 数とlimitを比較する。
6. thread別CPUとblocked状態を見る。
7. downstream endpointへbounded diagnostic requestを送る。
8. thread poolまたはconnection pool枯渇の仮説を検証する。
9. traffic drain後にrestartするか決める。
10. 復旧後に利用者SLIとresource metricを確認する。

再起動した場合、それを原因解決として記録しない。

`restartで症状を緩和、原因は未確定` と分ける。

## 検証Checklist

### 証拠保全

- [ ] 症状timestampと影響範囲を記録した。
- [ ] 最近の変更とartifact versionを確認した。
- [ ] 再起動前にjournalとprocess状態を収集した。
- [ ] core dumpと機密情報policyを確認した。
- [ ] command outputにsecretが含まれないようにした。

### processとresource

- [ ] process treeとownerを確認した。
- [ ] CPU、load、I/O waitを区別した。
- [ ] hostとcgroup limitを合わせて確認した。
- [ ] memory構成とOOM eventを確認した。
- [ ] descriptorとsocket stateを確認した。
- [ ] disk byteとinodeの両方を確認した。

### service運用

- [ ] unitの実行userとenvironmentが明確である。
- [ ] SIGTERM graceful shutdownをテストした。
- [ ] restart stormの制限がある。
- [ ] readinessとprocess生存を区別する。
- [ ] journal retentionとtime synchronizationを確認した。
- [ ] 復旧後に利用者機能を検証した。

## よくある失敗と限界

### `kill -9` から実行する

cleanupとdiagnostic hookをすべて飛ばす。

shared state破損の可能性も考慮する。

### host metricだけを見る

containerとsystemd serviceはcgroup limit内で枯渇し得る。

### logがなければeventもなかったと判断する

buffer flush前のcrash、sampling、rate limit、storage fullでlogは失われ得る。

metric、kernel event、traceを相互確認する。

### `D` state processをsignalですぐ消そうとする

uninterruptible kernel waitが解消するまでsignal処理は遅延し得る。

underlying I/Oとdevice状態を調べる必要がある。

### productionで無制限tracingを行う

診断tool自体がlatencyとdisk問題を作り得る。

scope、時間、filter、rollbackを決めて使う。

## 公式参考資料

- [Linux man-pages Project](https://www.kernel.org/doc/man-pages/)
- [proc(5)](https://man7.org/linux/man-pages/man5/proc.5.html)
- [signal(7)](https://man7.org/linux/man-pages/man7/signal.7.html)
- [systemd.service](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
- [systemd.exec](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html)
- [The Linux Kernel cgroup v2 Documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html)

## まとめ

Linux診断はcommand暗記ではなく、kernelが露出する証拠を適切な境界で読む作業である。

process、descriptor、memory、filesystem、signal、cgroup、service managerを結び、仮説を検証しよう。

再起動が必要でも先に証拠を残し、利用者機能で復旧を確認すれば、同じ障害を減らせる。
