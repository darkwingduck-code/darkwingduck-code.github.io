---
title: "Linux 진단 기본기: Process, File, Signal, systemd를 증거로 읽기"
date: 2026-07-21 12:06:00 +0900
categories: [Linux, Operations]
tags: [linux, diagnostics, processes, signals, systemd]
description: Linux 장애를 재시작부터 하지 않고 process, descriptor, filesystem, signal, resource, systemd journal의 증거로 좁혀가는 절차를 정리합니다.
lang: ko-KR
translation_key: linux-diagnostics-processes-files-signals-systemd
---
{% include language-switcher.html %}

## 문제: 재시작은 증상을 지우지만 원인을 설명하지 않는다

Linux service가 느리거나 응답하지 않을 때 즉시 restart하면 잠시 복구될 수 있다.

그러나 memory, descriptor, socket, child process, filesystem, dependency 증거도 함께 사라질 수 있다.

다음 오해가 진단을 늦춘다.

- CPU가 낮으니 process는 건강하다고 본다.
- free memory가 적으니 memory 부족이라고 단정한다.
- file이 존재하니 읽을 수 있다고 본다.
- `kill`이 곧 강제 종료라고 생각한다.
- service 상태가 active이므로 사용자 기능도 정상이라고 본다.
- log 마지막 한 줄만 원인으로 해석한다.
- root로 실행해 permission 문제를 우회한다.

운영 진단은 `관찰 -> 가설 -> 최소 확인 -> 안전한 완화 -> 검증` 순서로 한다.

## Mental model: process는 kernel 자원의 묶음이다

process는 단순한 실행 파일이 아니다.

다음을 가진다.

- PID와 parent PID
- user와 group identity
- virtual memory map
- open file descriptor table
- current working directory
- environment
- signal disposition
- namespace와 cgroup membership
- thread와 scheduling state

실행 file을 교체해도 이미 실행 중 process의 memory mapping은 자동 변경되지 않는다.

삭제된 file도 descriptor가 열려 있으면 disk block을 계속 점유할 수 있다.

### `/proc`는 실행 중 kernel 관찰 창이다

`/proc/<pid>/status`는 상태와 memory 개요를 보여준다.

`/proc/<pid>/fd`는 열린 descriptor를 보여준다.

`/proc/<pid>/maps`는 memory mapping을 보여준다.

`/proc/<pid>/limits`는 resource limit을 보여준다.

읽기에도 권한과 namespace 경계가 적용된다.

### file descriptor는 file만 가리키지 않는다

regular file, directory, socket, pipe, device, event object도 descriptor가 될 수 있다.

descriptor 누수는 file open 실패뿐 아니라 새 connection 실패로 나타날 수 있다.

process limit과 system-wide limit을 함께 본다.

### signal은 비동기 notification이다

`SIGTERM`은 정상 종료를 요청하는 catch 가능한 signal이다.

`SIGKILL`은 process가 처리하거나 무시할 수 없다.

`SIGHUP`은 역사적으로 terminal 종료이며 daemon이 reload 의미로 쓰기도 하지만 application 계약을 확인해야 한다.

signal 전달 성공과 application 정리 성공은 다르다.

## Workflow: 장애를 좁히는 순서

### Step 1. 사용자 증상을 고정한다

- 언제 시작했는가?
- 모든 요청인가 특정 endpoint인가?
- timeout인가 즉시 오류인가?
- 한 host인가 전체 fleet인가?
- 최근 배포·설정·인증서·dependency 변경이 있었는가?

UTC timestamp와 correlation ID를 확보한다.

### Step 2. service manager 상태를 확인한다

```bash
systemctl status example.service --no-pager
systemctl show example.service -p ActiveState -p SubState -p Result -p MainPID
journalctl -u example.service --since "-30 min" --no-pager
```

`active (running)`은 main process가 살아 있다는 뜻에 가깝다.

업무 요청 성공을 보장하지 않는다.

unit의 `ExecStart`, `User`, `WorkingDirectory`, `EnvironmentFile`, restart policy도 확인한다.

### Step 3. process tree와 상태를 본다

```bash
ps -eo pid,ppid,user,stat,etimes,%cpu,%mem,cmd --forest
```

`STAT`의 주요 단서는 다음과 같다.

- `R`: 실행 중 또는 runnable
- `S`: interruptible sleep
- `D`: uninterruptible sleep, 주로 I/O 대기
- `T`: stopped 또는 traced
- `Z`: zombie

zombie는 이미 종료됐지만 parent가 종료 상태를 회수하지 않은 child다.

zombie 자체는 memory를 거의 쓰지 않지만 지속 증가는 parent bug 신호다.

### Step 4. CPU와 scheduler를 분리해 본다

load average는 CPU 사용률과 동일하지 않다.

runnable task와 일부 uninterruptible task가 포함될 수 있다.

```bash
uptime
vmstat 1
pidstat -p <PID> 1
```

user CPU, system CPU, I/O wait, context switch를 함께 본다.

container에서는 cgroup quota로 throttling될 수 있다.

host CPU가 남아도 workload는 제한될 수 있다.

### Step 5. memory를 구성 요소로 본다

Linux는 남는 memory를 page cache로 활용한다.

`free`의 available 추정치를 함께 본다.

```bash
free -h
cat /proc/<PID>/status
cat /proc/<PID>/smaps_rollup
```

RSS, virtual size, anonymous memory, file-backed mapping, shared memory를 구분한다.

OOM kill 여부는 kernel journal과 cgroup event에서 확인한다.

```bash
journalctl -k --since "-1 hour" --no-pager
```

### Step 6. descriptor와 socket을 확인한다

```bash
ls -l /proc/<PID>/fd
cat /proc/<PID>/limits
ss -lntp
ss -antp
```

descriptor 수 추세와 limit을 비교한다.

connection state가 `SYN-SENT`, `CLOSE-WAIT`, `TIME-WAIT` 어디에 몰리는지 본다.

`CLOSE-WAIT` 누적은 peer 종료 뒤 application이 socket을 닫지 않는 단서일 수 있다.

### Step 7. filesystem 용량과 inode를 분리한다

```bash
df -h
df -i
findmnt
```

byte 공간이 남아도 inode가 고갈될 수 있다.

삭제된 열린 file은 directory 목록에 없지만 공간을 차지한다.

```bash
lsof +L1
```

mount option, read-only remount, network filesystem latency도 확인한다.

### Step 8. permission을 경로 전체에서 본다

file mode만 보면 부족하다.

상위 directory마다 traverse 권한이 필요하다.

```bash
namei -l /path/to/resource
id example-user
getfacl /path/to/resource
```

SELinux 또는 AppArmor가 사용 중이면 MAC policy denial도 확인한다.

root 실행은 원인 확인을 어렵게 하고 권한 경계를 깨뜨릴 수 있다.

### Step 9. I/O와 syscall을 최소 범위로 관찰한다

```bash
iostat -xz 1
strace -f -p <PID> -tt -T
```

`strace`는 overhead와 민감 데이터 노출 가능성이 있다.

짧은 시간, 필요한 syscall만 filter하고 운영 정책을 따른다.

`perf`, eBPF 도구도 같은 안전 원칙을 적용한다.

### Step 10. 안전하게 종료한다

먼저 service manager를 통해 종료한다.

```bash
systemctl stop example.service
```

필요하면 SIGTERM을 보내고 grace period 동안 상태를 관찰한다.

SIGKILL은 마지막 수단이다.

강제 종료 전 stack, log, descriptor, core dump 정책 등 필요한 증거를 확보한다.

## systemd unit을 읽는 기준

### dependency와 ordering은 다르다

`After=`는 시작 순서를 정의하지만 dependency 필요성을 자동 추가하지 않는다.

`Requires=`와 `Wants=`는 dependency 관계를 표현한다.

network가 `online`이라고 application dependency가 실제 준비됐다는 뜻은 아니다.

### restart policy는 장애를 숨길 수 있다

`Restart=on-failure`는 일시적 crash 복구에 도움을 준다.

그러나 빠른 crash loop가 dependency를 압박할 수 있다.

start rate limit과 backoff를 확인한다.

반복 restart 횟수와 마지막 exit reason에 경보를 둔다.

### 실행 환경은 interactive shell과 다르다

PATH, working directory, environment, umask, limit이 다를 수 있다.

shell profile이 자동 로드된다고 가정하지 않는다.

unit file에 필요한 경로를 명시한다.

secret을 unit source나 command line에 노출하지 않는다.

## 실전 예제: service는 active지만 API가 timeout

1. 합성 요청으로 endpoint와 timestamp를 고정한다.
2. `systemctl show`에서 MainPID와 restart 이력을 본다.
3. journal에서 같은 시간의 timeout과 dependency 오류를 찾는다.
4. `ss`에서 outbound connection state를 본다.
5. `/proc/<pid>/fd` 수와 limit을 비교한다.
6. thread별 CPU와 blocked 상태를 본다.
7. downstream endpoint에 bounded diagnostic request를 보낸다.
8. thread pool 또는 connection pool 고갈 가설을 검증한다.
9. traffic drain 뒤 restart할지 결정한다.
10. 복구 뒤 사용자 SLI와 resource metric을 확인한다.

재시작했다면 원인 해결로 기록하지 않는다.

`restart로 증상 완화, 원인은 미확정`으로 분리한다.

## 검증 Checklist

### 증거 보존

- [ ] 증상 timestamp와 영향 범위를 기록했다.
- [ ] 최근 변경과 artifact version을 확인했다.
- [ ] 재시작 전 journal과 process 상태를 수집했다.
- [ ] core dump와 민감정보 정책을 확인했다.
- [ ] 명령 출력에 secret이 포함되지 않게 했다.

### process와 resource

- [ ] process tree와 owner를 확인했다.
- [ ] CPU, load, I/O wait를 구분했다.
- [ ] host와 cgroup limit을 함께 확인했다.
- [ ] memory 구성과 OOM event를 확인했다.
- [ ] descriptor와 socket state를 확인했다.
- [ ] disk byte와 inode를 모두 확인했다.

### service 운영

- [ ] unit의 실행 user와 environment가 명확하다.
- [ ] SIGTERM graceful shutdown을 시험했다.
- [ ] restart storm 제한이 있다.
- [ ] readiness와 process 생존을 구분한다.
- [ ] journal retention과 time synchronization을 확인했다.
- [ ] 복구 뒤 사용자 기능을 검증했다.

## 자주 겪는 실패와 한계

### `kill -9`부터 실행한다

cleanup과 diagnostic hook을 모두 건너뛴다.

shared state 손상 가능성도 고려해야 한다.

### host metric만 본다

container와 systemd service는 cgroup limit 안에서 고갈될 수 있다.

### log가 없으면 event가 없었다고 판단한다

buffer flush 전 crash, sampling, rate limit, storage full로 log가 유실될 수 있다.

metric, kernel event, trace를 교차 확인한다.

### `D` state process를 signal로 즉시 없애려 한다

uninterruptible kernel wait가 풀릴 때까지 signal 처리가 지연될 수 있다.

underlying I/O와 device 상태를 조사해야 한다.

### production에서 무제한 tracing을 한다

진단 도구 자체가 latency와 disk 문제를 만들 수 있다.

범위, 시간, filter, rollback을 정하고 사용한다.

## 공식 참고자료

- [Linux man-pages Project](https://www.kernel.org/doc/man-pages/)
- [proc(5)](https://man7.org/linux/man-pages/man5/proc.5.html)
- [signal(7)](https://man7.org/linux/man-pages/man7/signal.7.html)
- [systemd.service](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
- [systemd.exec](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html)
- [The Linux Kernel cgroup v2 Documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html)

## 마무리

Linux 진단은 명령어 암기가 아니라 kernel이 노출한 증거를 올바른 경계에서 읽는 일이다.

process, descriptor, memory, filesystem, signal, cgroup, service manager를 연결해 가설을 검증하자.

재시작이 필요하더라도 먼저 증거를 남기고 사용자 기능으로 복구를 확인해야 같은 장애를 줄일 수 있다.
