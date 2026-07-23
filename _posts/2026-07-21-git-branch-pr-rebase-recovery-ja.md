---
title: "ブランチ、PR、merge、rebaseとGit安全復旧プレイブック"
date: 2026-07-21 09:10:00 +0900
categories: [Platform Engineering, Git]
tags: [git, branching, pull-request, rebase, recovery]
description: ブランチとコミットグラフを基準にPRの統合戦略を選び、ミスをデータ損失なく復旧する安全な手順を整理します。
lang: ja-JP
hidden: true
translation_key: git-branch-pr-rebase-recovery
---

{% include language-switcher.html %}

## 問題：Gitの事故は「コマンド」より「共有済みか」を見落とすと拡大する

同じミスでも、まだローカルにしかないのか、すでにリモートへ公開済みなのかによって、復旧方法はまったく異なる。ローカルコミットは比較的自由に書き換えられるが、他の人が基盤として使った公開コミットをrebaseや強制pushで変更すると、同僚の履歴とCIの基準点を同時に揺るがす。

安全に判断するには、次の三つの質問で十分である。

1. 失ってはならない変更は、作業ツリー、ステージング領域、コミットのどこにあるか？
2. 対象コミットを他の人がすでに取得しているか？
3. 望む結果は、新しい履歴で打ち消すことか、既存の履歴を書き換えることか？

復旧コマンドから実行せず、まず状態とグラフを記録する。

```bash
git status --short --branch
git log --graph --decorate --oneline --all -n 30
git reflog -n 20
```

## Mental model：ブランチはコミットを指す名前である

ブランチを「フォルダーのコピー」と考えると、mergeとrebaseを理解しにくい。ブランチはコミットIDを指す軽量な参照である。

```text
          F1---F2  feature
         /
M1---M2---M3      main
```

`feature`は`F2`、`main`は`M3`を指す。二つのブランチを統合する代表的な方法は三つある。

| 方法 | 結果 | 適する状況 | 注意点 |
|---|---|---|---|
| merge commit | 二つの親を持つ統合コミットを作成 | 分岐構造と個々のコミットを保存 | 履歴が複雑になりうる |
| squash merge | PRの変更を一つの新しいコミットとして統合 | 小さなfeature、整理されていない作業コミット | PR内のコミット境界が失われる |
| rebase + fast-forward | featureコミットを最新base上で再生 | 線形履歴と意味のあるコミットを両立 | コミットIDが変わるため、公開履歴の書き換えに注意 |

rebase前：

```text
          F1---F2  feature
         /
M1---M2---M3      main
```

`feature`を`main`上へrebaseした後：

```text
M1---M2---M3---F1'---F2'  feature
```

`F1'`、`F2'`は内容が似ていても、親とcommit IDが異なる新しいオブジェクトである。rebaseはコミットを「移動」するというより、パッチを新しい基盤上で**作り直す処理**である。

### PRはGitの機能を超えた変更統制の単位である

Pull requestはブランチ比較に次の要素を組み合わせる。

- 議論と設計根拠
- 自動テストと静的解析
- コード所有者の承認
- デプロイ環境の保護ルール
- 監査可能な統合判断

したがって、よいPRは単なる「コードをアップロードする場所」ではなく、変更のリスク、検証根拠、rollback方法をまとめるパッケージである。

## 実践パターン：短いブランチ、明示的な統合、復旧前のスナップショット

### 小さなfeature branchの基本フロー

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

ブランチの存続期間が短いほど、競合範囲は小さい。大きな機能でも、機能フラグ、インターフェースの先行変更、データmigrationのexpand/contractパターンに分割すれば、mainへ頻繁に統合できる。

PR本文には、少なくとも次を記す。

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

### feature branchを最新のmainへ合わせる二つの選択肢

チームがmergeベースなら：

```bash
git fetch origin
git switch feature/health-endpoint
git merge origin/main
```

チームがrebaseベースで、そのfeature branchを実質的に一人で使用しているなら：

```bash
git fetch origin
git switch feature/health-endpoint

# 복구 지점을 먼저 만든다.
git branch backup/health-endpoint-before-rebase

git rebase origin/main
```

競合でGitが停止したら、次の手順を繰り返す。

```bash
git status

# 파일에서 conflict marker를 해결하고 테스트한다.
git add <RESOLVED_FILE>
git rebase --continue
```

判断に確信が持てなければ、元の状態へ戻る。

```bash
git rebase --abort
```

rebase後、すでに存在する自分のリモートfeature branchを更新する必要がある場合、通常の`--force`ではなく次を使う。

```bash
git push --force-with-lease
```

`--force-with-lease`は、リモート参照が自分が最後に確認した値と同じ場合にだけ上書きを試みる。他の人の新しいpushを無条件に保護する絶対的な保証ではないため、共有ブランチの保護ルールとチームの合意が優先される。`main`のような保護ブランチでは、強制pushを許可しない。

### ミスの種類ごとの安全な復旧

#### 1. まだステージングしていない変更を取り消したい

まずdiffを読み、本当に破棄してよいか確認する。

```bash
git diff -- <FILE>
git restore -- <FILE>
```

`git restore`は作業ツリーの内容を変更するため、未コミットの変更を失う可能性がある。ファイル名を具体的に指定し、確信がなければ先にpatchファイルまたは一時ブランチのコミットとして保存する。

#### 2. addだけを取り消し、編集内容は維持したい

```bash
git diff --staged -- <FILE>
git restore --staged -- <FILE>
git diff -- <FILE>
```

これはステージングだけを解除し、通常は作業ツリーの変更を残す。

#### 3. 最後のローカルコミットのメッセージまたは不足ファイルを修正したい

まだ共有していないコミットか確認する。

```bash
git status --short --branch
git log --oneline origin/<BRANCH>..HEAD

# 필요한 변경을 stage한 뒤 마지막 커밋을 다시 만든다.
git add <FILE>
git commit --amend
```

amendも新しいcommit IDを作る。すでに公開したコミットなら、通常は後続コミットを追加するほうが安全である。

#### 4. 公開済みの誤ったコミットの効果を元に戻したい

公開履歴を消さず、反対の変更を新しいコミットとして記録する。

```bash
git show <COMMIT_ID>
git revert <COMMIT_ID>
```

merge commitをrevertするときはmainlineの親を選択する必要があり、今後の再mergeに影響しうる。この場合はグラフとデプロイ状態をレビューしたうえで、チームの手順に従って処理する。

#### 5. resetまたはrebase後にコミットを失ったように見える

ほとんどの場合、オブジェクトがすぐに削除されたのではなく、ブランチが指さなくなっただけである。reflogで以前の`HEAD`を探す。

```bash
git reflog --date=local
git show <RECOVERABLE_COMMIT_ID>
git branch recovery/<SHORT_NAME> <RECOVERABLE_COMMIT_ID>
```

復旧ブランチを作った後、ファイルとテストを確認し、通常のブランチへcherry-pickまたはmergeする。reflogはローカルリポジトリにおける参照移動の記録であり、恒久的なバックアップではない。整理ポリシーと時間の経過により、オブジェクトが削除されることがある。

#### 6. まったく別のブランチで作業していた

変更を破棄せず、現在の位置でコミットまたはstashとして保存してから移動する。最も監査しやすい方法は、一時ブランチへのコミットである。

```bash
git switch -c recovery/wrong-branch-work
git add --patch
git commit -m "wip: preserve work before branch correction"

git switch <TARGET_BRANCH>
git cherry-pick <PRESERVED_COMMIT_ID>
```

最終履歴にWIPコミットを残したくなければ、PRの統合時にsquashするか、公開前にinteractive rebaseで整理できる。

### `reset`は三つの領域をどれだけ移動させるかが異なる

| モード | ブランチ/HEAD | ステージング | 作業ツリー | 主なリスク |
|---|---:|---:|---:|---|
| `--soft` | 移動 | 維持 | 維持 | 履歴上の位置を誤って選択 |
| デフォルトの`--mixed` | 移動 | 対象コミットに変更 | 維持 | stage状態が解除される |
| `--hard` | 移動 | 対象コミットに変更 | 対象コミットに変更 | 未コミット作業の損失 |

`git reset --hard`は復旧の第一歩ではない。必要なら現在のcommit IDと作業ツリーの変更を別の安全な地点へ保存し、対象コミットを`git show`で検証してから限定的に使用すべきである。共有履歴を元に戻す目的には`revert`が基本である。

### 安全策をリポジトリポリシーにする

人の注意力だけでmainを保護することはできない。リポジトリ設定で次を強制する。

- PRを通した変更のみ許可
- 必須ステータスチェックの通過
- 最小承認数とstale approvalの無効化
- CODEOWNERSが必要なパスの所有者レビュー
- 会話が未解決なら統合をブロック
- force pushとbranch deletionを制限
- 管理者による回避の使用を例外手順として記録

## 検証チェックリスト

PRを統合する前：

- [ ] 変更範囲が一つの目的に集中している。
- [ ] base branchが正しく、不要なコミットやファイルがない。
- [ ] 自動テストだけでなく、失敗経路とrollbackもレビューした。
- [ ] データ・API・設定変更の下位互換性を確認した。
- [ ] merge、squash、rebaseからリポジトリポリシーに合う方法を選択した。
- [ ] デプロイ前後の観測指標と担当者が明確である。

復旧コマンドを実行する前：

- [ ] `status`、`log --graph --all`、`reflog`を記録した。
- [ ] 変更がローカル専用か、すでに共有済みか確認した。
- [ ] 保存用branchまたはコミットを作成した。
- [ ] ファイル・ブランチ・commit IDを具体的に指定した。
- [ ] secretの露出なら、Git操作よりcredentialの失効・再発行を先に行った。
- [ ] 復旧後、diff、テスト、リモートグラフを再確認した。

## 失敗例と限界

### 長いブランチを一度に統合する

競合は行数ではなく意味が問題である。長期間分離されたブランチでは双方の設計意図が同時に変わり、テキスト上の競合がなくても動作上の競合が生じる。小さなPRと継続的な統合が復旧コストを下げる。

### 公開ブランチを不用意にrebaseする

rebase自体が危険なのではなく、共有された基盤を合意なく入れ替えることが危険である。個人のfeature branchの整理と、共有branchの履歴変更を区別する。

### 競合markerだけを消して解決したと判断する

`<<<<<<<`、`=======`、`>>>>>>>`を削除しても、双方の意図が保たれたことにはならない。競合解決後、関連テスト、型検査、データmigrationの検証を再実行しなければならない。

### secretをコミット履歴から消せば事故が終わると考える

tokenやkeyが一度でもpushされたなら、すでにclone、CI log、cache、forkに残っている可能性がある。まずsecretを失効させて交換する。履歴の整理が必要なら、リポジトリ管理者と全利用者が同期して行う別個のインシデント対応とする。単独のforce pushは露出を取り消せないうえ、共同作業の履歴だけを壊しかねない。

### reflogをバックアップだと考える

reflogは非常に有用だが、ローカルで一時的な復旧手段である。リモートpush、保護ブランチ、tag、artifactの保存、リポジトリのバックアップポリシーを代替するものではない。

よいGit戦略の目的は「美しいグラフ」ではない。変更を小さくし、レビューの根拠を残し、失敗したときにどのコミットへ戻るべきかを誰でも判断できるようにすることが目的である。
