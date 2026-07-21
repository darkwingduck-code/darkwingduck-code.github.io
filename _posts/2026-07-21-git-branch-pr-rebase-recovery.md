---
title: "브랜치, PR, merge, rebase와 Git 안전 복구 플레이북"
date: 2026-07-21 09:10:00 +0900
categories: [Platform Engineering, Git]
tags: [git, branching, pull-request, rebase, recovery]
description: 브랜치와 커밋 그래프를 기준으로 PR 통합 전략을 선택하고, 실수를 데이터 손실 없이 복구하는 안전한 절차를 정리합니다.
---

## 문제: Git 사고는 “명령”보다 “공유 여부”를 놓칠 때 커진다

같은 실수라도 아직 로컬에만 있는가, 이미 원격에 공개됐는가에 따라 복구 방식이 완전히 달라진다. 로컬 커밋은 비교적 자유롭게 재작성할 수 있지만, 다른 사람이 기반으로 삼은 공개 커밋을 rebase나 강제 push로 바꾸면 동료의 이력과 CI 기준점을 동시에 흔든다.

안전한 판단에는 세 질문이면 충분하다.

1. 잃으면 안 되는 변경이 작업 트리, 스테이징 영역, 커밋 중 어디에 있는가?
2. 대상 커밋을 다른 사람이 이미 가져갔는가?
3. 원하는 결과는 새 이력으로 상쇄하는 것인가, 기존 이력을 재작성하는 것인가?

복구 명령부터 실행하지 말고 먼저 상태와 그래프를 캡처한다.

```bash
git status --short --branch
git log --graph --decorate --oneline --all -n 30
git reflog -n 20
```

## Mental model: 브랜치는 커밋을 가리키는 이름이다

브랜치를 “폴더 복사본”으로 생각하면 merge와 rebase가 어렵다. 브랜치는 커밋 ID를 가리키는 가벼운 참조다.

```text
          F1---F2  feature
         /
M1---M2---M3      main
```

`feature`는 `F2`, `main`은 `M3`를 가리킨다. 두 브랜치를 통합하는 대표 방식은 세 가지다.

| 방식 | 결과 | 잘 맞는 상황 | 주의점 |
|---|---|---|---|
| merge commit | 두 부모를 가진 통합 커밋 생성 | 분기 구조와 개별 커밋을 보존 | 이력이 복잡해질 수 있음 |
| squash merge | PR 변경을 하나의 새 커밋으로 통합 | 작은 feature, 정리되지 않은 작업 커밋 | PR 내부 커밋 경계가 사라짐 |
| rebase + fast-forward | feature 커밋을 최신 base 위에 재생 | 선형 이력과 의미 있는 커밋을 함께 유지 | 커밋 ID가 바뀌므로 공개 이력 재작성 주의 |

rebase 전:

```text
          F1---F2  feature
         /
M1---M2---M3      main
```

`feature`를 `main` 위로 rebase한 뒤:

```text
M1---M2---M3---F1'---F2'  feature
```

`F1'`, `F2'`는 내용이 비슷해도 부모와 commit ID가 다른 새 객체다. rebase는 커밋을 “이동”하기보다 패치를 새 기반 위에서 **다시 만드는 작업**이다.

### PR은 Git 기능을 넘어선 변경 통제 단위다

Pull request는 브랜치 비교에 다음 요소를 결합한다.

- 토론과 설계 근거
- 자동 테스트와 정적 분석
- 코드 소유자 승인
- 배포 환경 보호 규칙
- 감사 가능한 통합 결정

따라서 좋은 PR은 단순히 “코드를 올리는 곳”이 아니라 변경의 위험, 검증 근거, 롤백 방법을 모으는 패키지다.

## 실전 패턴: 짧은 브랜치, 명시적 통합, 복구 전 스냅샷

### 작은 feature branch의 기본 흐름

```bash
git switch main
git fetch origin
git merge --ff-only origin/main

git switch -c feature/health-endpoint

# 편집과 테스트 후
git add --patch
git diff --staged
git commit -m "feat: add dependency-aware health endpoint"
git push --set-upstream origin feature/health-endpoint
```

브랜치가 짧게 생존할수록 충돌 범위가 작다. 큰 기능도 기능 플래그, 인터페이스 선행 변경, 데이터 migration의 expand/contract 패턴으로 쪼개면 main에 자주 통합할 수 있다.

PR 본문에는 최소한 다음을 남긴다.

```markdown
## 왜 필요한가
<문제와 사용자 영향>

## 무엇이 바뀌는가
<핵심 설계와 범위 밖 항목>

## 어떻게 검증했는가
<테스트 명령, 관찰 결과, 수동 확인>

## 위험과 복구
<호환성, migration, feature flag, rollback>
```

### feature branch를 최신 main에 맞추는 두 선택

팀이 merge 기반이라면:

```bash
git fetch origin
git switch feature/health-endpoint
git merge origin/main
```

팀이 rebase 기반이고 해당 feature branch를 사실상 혼자 사용한다면:

```bash
git fetch origin
git switch feature/health-endpoint

# 복구 지점을 먼저 만든다.
git branch backup/health-endpoint-before-rebase

git rebase origin/main
```

충돌 시 Git이 멈추면 다음 순서를 반복한다.

```bash
git status

# 파일에서 conflict marker를 해결하고 테스트한다.
git add <RESOLVED_FILE>
git rebase --continue
```

판단이 불확실하면 원래 상태로 돌아간다.

```bash
git rebase --abort
```

rebase 후 이미 존재하는 자신의 원격 feature branch를 갱신해야 한다면 일반 `--force`보다 다음을 사용한다.

```bash
git push --force-with-lease
```

`--force-with-lease`는 원격 참조가 내가 마지막으로 본 값과 같을 때만 덮어쓰려 한다. 다른 사람의 새 push를 무조건 보존해 주는 절대적 보장은 아니므로, 공유 브랜치 보호 규칙과 팀 합의가 우선이다. `main` 같은 보호 브랜치에는 강제 push를 허용하지 않는다.

### 실수 유형별 안전 복구

#### 1. 아직 스테이징하지 않은 변경을 취소하고 싶다

먼저 diff를 읽고 정말 버려도 되는지 확인한다.

```bash
git diff -- <FILE>
git restore -- <FILE>
```

`git restore`는 작업 트리 내용을 바꾸므로 미커밋 변경을 잃을 수 있다. 파일명을 구체적으로 지정하고, 확신이 없으면 먼저 patch 파일이나 임시 브랜치 커밋으로 보존한다.

#### 2. add만 취소하고 편집 내용은 유지하고 싶다

```bash
git diff --staged -- <FILE>
git restore --staged -- <FILE>
git diff -- <FILE>
```

이는 스테이징만 해제하고 일반적으로 작업 트리 변경을 남긴다.

#### 3. 마지막 로컬 커밋 메시지 또는 누락 파일을 고치고 싶다

아직 공유하지 않은 커밋인지 확인한다.

```bash
git status --short --branch
git log --oneline origin/<BRANCH>..HEAD

# 필요한 변경을 stage한 뒤 마지막 커밋을 다시 만든다.
git add <FILE>
git commit --amend
```

amend도 새 commit ID를 만든다. 이미 공개한 커밋이면 보통 후속 커밋을 추가하는 편이 안전하다.

#### 4. 공개된 잘못된 커밋의 효과를 되돌리고 싶다

공개 이력을 지우지 않고 반대 변경을 새 커밋으로 기록한다.

```bash
git show <COMMIT_ID>
git revert <COMMIT_ID>
```

merge commit을 revert할 때는 mainline 부모 선택이 필요하고 향후 재병합에 영향을 줄 수 있다. 이 경우 그래프와 배포 상태를 검토한 뒤 팀 절차에 따라 처리한다.

#### 5. reset 또는 rebase 후 커밋을 잃어버린 것처럼 보인다

대부분 객체가 즉시 삭제된 것이 아니라 브랜치가 더 이상 가리키지 않을 뿐이다. reflog에서 이전 `HEAD`를 찾는다.

```bash
git reflog --date=local
git show <RECOVERABLE_COMMIT_ID>
git branch recovery/<SHORT_NAME> <RECOVERABLE_COMMIT_ID>
```

복구 브랜치를 만든 뒤 파일과 테스트를 확인하고 정상 브랜치로 cherry-pick 또는 merge한다. reflog는 로컬 저장소의 참조 이동 기록이며 영구 백업이 아니다. 정리 정책과 시간이 지나면 객체가 제거될 수 있다.

#### 6. 완전히 다른 브랜치에서 작업했다

변경을 버리지 말고 현재 위치에서 커밋 또는 stash로 보존한 뒤 이동한다. 가장 감사하기 쉬운 방법은 임시 브랜치 커밋이다.

```bash
git switch -c recovery/wrong-branch-work
git add --patch
git commit -m "wip: preserve work before branch correction"

git switch <TARGET_BRANCH>
git cherry-pick <PRESERVED_COMMIT_ID>
```

최종 이력에 WIP 커밋을 남기고 싶지 않다면 PR 통합 시 squash하거나, 공개 전 interactive rebase로 정리할 수 있다.

### `reset`은 세 공간을 얼마나 이동시키는지가 다르다

| 모드 | 브랜치/HEAD | 스테이징 | 작업 트리 | 대표 위험 |
|---|---:|---:|---:|---|
| `--soft` | 이동 | 유지 | 유지 | 이력 위치를 잘못 선택 |
| 기본 `--mixed` | 이동 | 대상 커밋으로 변경 | 유지 | stage 상태가 풀림 |
| `--hard` | 이동 | 대상 커밋으로 변경 | 대상 커밋으로 변경 | 미커밋 작업 손실 |

`git reset --hard`는 복구의 첫 단계가 아니다. 필요하다면 현재 commit ID와 작업 트리 변경을 별도 안전 지점에 보존하고, 대상 커밋을 `git show`로 검증한 뒤 제한적으로 사용해야 한다. 공유 이력을 되돌리는 목적에는 `revert`가 기본이다.

### 안전장치를 저장소 정책으로 만든다

사람의 주의력만으로 main을 보호할 수 없다. 저장소 설정에서 다음을 강제한다.

- PR을 통한 변경만 허용
- 필수 상태 검사 통과
- 최소 승인 수와 stale approval 무효화
- CODEOWNERS가 필요한 경로의 소유자 검토
- 대화가 해결되지 않으면 통합 차단
- force push와 branch deletion 제한
- 관리자 우회 사용을 예외 절차로 기록

## 검증 체크리스트

PR을 통합하기 전:

- [ ] 변경 범위가 한 가지 목적에 집중돼 있다.
- [ ] base branch가 맞고 불필요한 커밋이나 파일이 없다.
- [ ] 자동 테스트뿐 아니라 실패 경로와 롤백도 검토했다.
- [ ] 데이터·API·설정 변경의 하위 호환성을 확인했다.
- [ ] merge, squash, rebase 중 저장소 정책에 맞는 방식을 선택했다.
- [ ] 배포 전후 관찰 지표와 책임자가 명확하다.

복구 명령을 실행하기 전:

- [ ] `status`, `log --graph --all`, `reflog`를 캡처했다.
- [ ] 변경이 로컬 전용인지 이미 공유됐는지 확인했다.
- [ ] 보존용 branch 또는 커밋을 만들었다.
- [ ] 파일·브랜치·commit ID를 구체적으로 지정했다.
- [ ] 비밀 노출이라면 Git 조작보다 자격 증명 폐기·재발급을 먼저 했다.
- [ ] 복구 후 diff, 테스트, 원격 그래프를 다시 확인했다.

## 실패 사례와 한계

### 긴 브랜치에서 한 번에 통합하기

충돌은 줄 수가 아니라 의미가 문제다. 오래 분리된 브랜치는 양쪽 설계 의도가 동시에 변해 텍스트 충돌이 없어도 동작 충돌이 생긴다. 작은 PR과 지속적인 통합이 복구 비용을 줄인다.

### 공개 브랜치를 무심코 rebase하기

rebase 자체가 위험한 것이 아니라 공유된 기반을 합의 없이 교체하는 것이 위험하다. 개인 feature branch 정리와 공용 branch 이력 변경을 구분한다.

### 충돌 marker만 없애고 해결됐다고 판단하기

`<<<<<<<`, `=======`, `>>>>>>>`를 제거해도 양쪽 의도가 보존됐다는 뜻은 아니다. 충돌 해결 후 관련 테스트, 타입 검사, 데이터 migration 검증을 다시 수행해야 한다.

### 비밀을 커밋 이력에서 지우면 사고가 끝난다고 생각하기

토큰이나 키가 한 번 push됐다면 이미 복제, CI log, cache, fork에 남았을 수 있다. 먼저 비밀을 폐기하고 교체한다. 이력 정리가 필요하면 저장소 관리자와 사용자 전체가 동기화하는 별도 사고 대응으로 수행한다. 단독 force push는 노출을 되돌리지 못하면서 협업 이력만 깨뜨릴 수 있다.

### reflog를 백업으로 생각하기

reflog는 매우 유용하지만 로컬·임시 복구 수단이다. 원격 push, 보호 브랜치, 태그, 아티팩트 보존, 저장소 백업 정책을 대체하지 않는다.

좋은 Git 전략의 목적은 “예쁜 그래프”가 아니다. 변경을 작게 만들고, 검토 근거를 남기며, 실패했을 때 어느 커밋으로 돌아갈지 누구나 판단할 수 있게 하는 것이 목적이다.
