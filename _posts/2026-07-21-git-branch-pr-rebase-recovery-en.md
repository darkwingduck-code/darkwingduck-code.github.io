---
title: "Branches, PRs, Merge, Rebase, and a Safe Git Recovery Playbook"
date: 2026-07-21 09:10:00 +0900
categories: [Platform Engineering, Git]
tags: [git, branching, pull-request, rebase, recovery]
description: Learn to choose a PR integration strategy from the branch and commit graph and recover from mistakes safely without losing data.
lang: en
translation_key: git-branch-pr-rebase-recovery
hidden: true
---

{% include language-switcher.html %}

## The problem: Git incidents grow when you overlook whether history is shared, not because of a command

Recovery is completely different depending on whether the same mistake still exists only locally or has already been published to a remote. You can rewrite local commits relatively freely, but changing public commits on which others have based work through rebase or force push disrupts both your colleagues' history and CI reference points.

Three questions are enough to make a safe decision.

1. Is the change that must not be lost in the working tree, staging area, or a commit?
2. Has anyone else already fetched the target commit?
3. Is the desired result to counteract it with new history, or to rewrite existing history?

Do not begin with a recovery command. Capture the status and graph first.

```bash
git status --short --branch
git log --graph --decorate --oneline --all -n 30
git reflog -n 20
```

## Mental model: A branch is a name that points to a commit

Thinking of a branch as a “copy of a folder” makes merge and rebase difficult to understand. A branch is a lightweight reference pointing to a commit ID.

```text
          F1---F2  feature
         /
M1---M2---M3      main
```

`feature` points to `F2`, while `main` points to `M3`. There are three representative ways to integrate the two branches.

| Method | Result | Best suited to | Caution |
|---|---|---|---|
| merge commit | Creates an integration commit with two parents | Preserving branch structure and individual commits | History can become complex |
| squash merge | Integrates PR changes as one new commit | Small features and unpolished work commits | Commit boundaries within the PR disappear |
| rebase + fast-forward | Replays feature commits on the latest base | Keeping linear history and meaningful commits | Commit IDs change, so take care when rewriting public history |

Before rebase:

```text
          F1---F2  feature
         /
M1---M2---M3      main
```

After rebasing `feature` onto `main`:

```text
M1---M2---M3---F1'---F2'  feature
```

Even if `F1'` and `F2'` have similar content, they are new objects with different parents and commit IDs. Rather than “moving” commits, rebase **recreates patches** on a new base.

### A PR is a change-control unit beyond Git itself

A pull request combines a branch comparison with the following elements.

- Discussion and design rationale
- Automated tests and static analysis
- Code-owner approval
- Deployment-environment protection rules
- An auditable integration decision

A good PR is therefore not merely “a place to upload code,” but a package that brings together change risks, validation evidence, and rollback methods.

## Practical pattern: Short branches, explicit integration, and a snapshot before recovery

### Basic flow for a small feature branch

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

The shorter a branch lives, the smaller its conflict surface. Even a large feature can be integrated into main frequently by splitting it with feature flags, advance interface changes, and the expand/contract pattern for data migrations.

At minimum, include the following in the PR description.

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

### Two ways to bring a feature branch up to date with main

If the team uses a merge-based workflow:

```bash
git fetch origin
git switch feature/health-endpoint
git merge origin/main
```

If the team uses a rebase-based workflow and you are effectively the only person using the feature branch:

```bash
git fetch origin
git switch feature/health-endpoint

# 복구 지점을 먼저 만든다.
git branch backup/health-endpoint-before-rebase

git rebase origin/main
```

When Git stops on a conflict, repeat the following sequence.

```bash
git status

# 파일에서 conflict marker를 해결하고 테스트한다.
git add <RESOLVED_FILE>
git rebase --continue
```

If you are uncertain about the resolution, return to the original state.

```bash
git rebase --abort
```

If you must update your existing remote feature branch after the rebase, use the following instead of ordinary `--force`.

```bash
git push --force-with-lease
```

`--force-with-lease` attempts to overwrite the remote reference only when it still has the value you last observed. It is not an absolute guarantee that every new push by someone else will be preserved, so shared-branch protection rules and team agreement take precedence. Do not allow force pushes to protected branches such as `main`.

### Safe recovery by mistake type

#### 1. You want to discard a change that has not been staged

Read the diff first and confirm that it is truly safe to discard.

```bash
git diff -- <FILE>
git restore -- <FILE>
```

Because `git restore` changes working-tree contents, it can lose uncommitted changes. Specify the filename precisely; if you are uncertain, preserve the change first in a patch file or a commit on a temporary branch.

#### 2. You want to undo only `add` and preserve the edited content

```bash
git diff --staged -- <FILE>
git restore --staged -- <FILE>
git diff -- <FILE>
```

This only unstages the change and generally leaves the working-tree change intact.

#### 3. You want to fix the last local commit message or add a missing file

Confirm that the commit has not been shared yet.

```bash
git status --short --branch
git log --oneline origin/<BRANCH>..HEAD

# 필요한 변경을 stage한 뒤 마지막 커밋을 다시 만든다.
git add <FILE>
git commit --amend
```

Amending also creates a new commit ID. If the commit has already been published, adding a follow-up commit is usually safer.

#### 4. You want to undo the effect of an incorrect public commit

Record the opposite change in a new commit without deleting public history.

```bash
git show <COMMIT_ID>
git revert <COMMIT_ID>
```

Reverting a merge commit requires choosing the mainline parent and can affect future remerges. In this case, review the graph and deployment state, then follow the team's procedure.

#### 5. A commit appears to have been lost after reset or rebase

In most cases, the object was not deleted immediately; the branch simply no longer points to it. Find the previous `HEAD` in the reflog.

```bash
git reflog --date=local
git show <RECOVERABLE_COMMIT_ID>
git branch recovery/<SHORT_NAME> <RECOVERABLE_COMMIT_ID>
```

After creating a recovery branch, verify the files and tests, then cherry-pick or merge into the normal branch. The reflog records reference movements in a local repository; it is not a permanent backup. Cleanup policies and the passage of time can remove objects.

#### 6. You worked on a completely different branch

Do not discard the changes. Preserve them in a commit or stash at the current location, then move. A temporary branch commit is the most auditable method.

```bash
git switch -c recovery/wrong-branch-work
git add --patch
git commit -m "wip: preserve work before branch correction"

git switch <TARGET_BRANCH>
git cherry-pick <PRESERVED_COMMIT_ID>
```

If you do not want a WIP commit in the final history, squash it during PR integration or clean it up with interactive rebase before publication.

### `reset` modes differ in how far they move the three areas

| Mode | Branch/HEAD | Staging area | Working tree | Representative risk |
|---|---:|---:|---:|---|
| `--soft` | Moves | Preserved | Preserved | Choosing the wrong point in history |
| default `--mixed` | Moves | Changed to target commit | Preserved | Staged state is removed |
| `--hard` | Moves | Changed to target commit | Changed to target commit | Loss of uncommitted work |

`git reset --hard` is not the first step in recovery. If it is necessary, preserve the current commit ID and working-tree changes at a separate safe point, verify the target commit with `git show`, and then use it in a limited scope. `revert` is the default for undoing shared history.

### Make safeguards part of repository policy

Human attention alone cannot protect main. Enforce the following in repository settings.

- Allow changes only through PRs
- Require status checks to pass
- Require a minimum number of approvals and dismiss stale approvals
- Require owner review through CODEOWNERS for applicable paths
- Block integration while conversations remain unresolved
- Restrict force pushes and branch deletion
- Record administrator bypasses as an exception procedure

## Validation checklist

Before integrating a PR:

- [ ] The scope of the change focuses on one purpose.
- [ ] The base branch is correct, with no unnecessary commits or files.
- [ ] Failure paths and rollback were reviewed in addition to automated tests.
- [ ] Backward compatibility of data, API, and configuration changes was verified.
- [ ] The integration method—merge, squash, or rebase—matches repository policy.
- [ ] Pre- and post-deployment metrics and their owners are clear.

Before running a recovery command:

- [ ] `status`, `log --graph --all`, and `reflog` were captured.
- [ ] You determined whether the changes are local only or already shared.
- [ ] A preservation branch or commit was created.
- [ ] File, branch, and commit IDs were specified precisely.
- [ ] If a secret was exposed, credential revocation and reissuance happened before Git manipulation.
- [ ] The diff, tests, and remote graph were checked again after recovery.

## Failure cases and limitations

### Integrating a long-lived branch all at once

The problem with conflicts is their meaning, not their line count. On a branch separated for a long time, the design intent on both sides changes; behavioral conflicts can arise even without text conflicts. Small PRs and continuous integration reduce recovery cost.

### Carelessly rebasing a public branch

Rebase itself is not dangerous; replacing a shared foundation without agreement is. Distinguish cleaning up a personal feature branch from changing the history of a shared branch.

### Deciding a conflict is resolved after merely removing its markers

Removing `<<<<<<<`, `=======`, and `>>>>>>>` does not mean that both sides' intent was preserved. After resolving a conflict, rerun relevant tests, type checks, and data-migration validation.

### Thinking that removing a secret from commit history ends the incident

Once a token or key has been pushed, it may already remain in clones, CI logs, caches, and forks. Revoke and replace the secret first. If history cleanup is necessary, treat it as a separate incident response coordinated by repository administrators and all users. A unilateral force push may break collaborative history without undoing the exposure.

### Treating the reflog as a backup

The reflog is extremely useful, but it is a local and temporary recovery mechanism. It does not replace remote pushes, protected branches, tags, artifact retention, or repository backup policy.

The purpose of a good Git strategy is not a “pretty graph.” It is to keep changes small, preserve review evidence, and enable anyone to determine which commit to return to after a failure.
