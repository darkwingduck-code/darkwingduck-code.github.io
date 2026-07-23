---
title: "再現可能な研究ソフトウェア配布：Release・CITATION.cff・Zenodo DOI"
date: 2026-07-21 10:00:00 +0900
categories: [Research Engineering, Reproducibility]
tags: [research-software, reproducibility, release, git-tag, citation-cff, zenodo, software-doi, preprint]
description: "研究コードリポジトリを再現可能なreleaseにし、CITATION.cff、保存archive、software DOIを接続しながら、論文・preprintとは識別子を分離する手順を整理する。"
lang: ja-JP
translation_key: reproducible-research-software-release-doi
hidden: true
---

{% include language-switcher.html %}

研究コードが公開リポジトリにあるという事実だけで、再現可能または引用可能になるわけではない。default branchは変わり続け、dependencyは消え、どのcommitが結果を生成したのか読者が判断しにくいためである。

研究ソフトウェアを適切に公開するには、4つの対象を区別しなければならない。

1. 開発が続く**source repository**
2. 意味のある状態を固定した**versioned releaseとtag**
3. 長期保存と引用のための**archival software recordとDOI**
4. 研究課題・方法・結果を説明する**paperまたはpreprint**

本稿では、この4つのオブジェクトを混同せず、相互に追跡可能な形で接続する実践手順を整理する。

## 1. まず「何を識別するか」を分離する

| オブジェクト | 主な役割 | 変更可能性 | 代表的な識別子 |
|---|---|---|---|
| repository | 協働と継続開発 | branchは変化し続ける | repository URL |
| commit | source snapshot | content-addressedで事実上固定 | commit hash |
| tag | 人が読めるversion label | 方針上immutableを推奨 | tag name + target commit |
| release | 配布説明とartifactの集合 | release noteは修正可能な場合がある | version + release URL |
| software archive | 長期保存された研究オブジェクト | version record内のfileは固定 | software DOI |
| preprint/article | 研究上の主張と記述 | version方針はplatformごとに異なる | publication DOIまたはidentifier |
| dataset | 入出力データオブジェクト | versionごとに固定を推奨 | dataset DOI |

commit hashは正確なsourceを指すが、学術metadataや長期保存方針を提供しない。DOIは永続的な識別とmetadataの接続を提供するが、実行環境を自動的に復元しない。両方を併用する必要がある。

## 2. 再現性の水準を明示する

「再現可能」とだけ書かず、サポート範囲を定義する。

- **Source reproducibility**：同じsource treeを取得できる。
- **Build reproducibility**：指定環境で同じexecutableまたはpackageを作れる。
- **Computational reproducibility**：入力から許容誤差内で同じoutputを得る。
- **Result reproducibility**：論文のfigure・table・metricを再生成する。
- **Auditability**：結果からcode、configuration、data provenanceを逆追跡できる。

すべてのplatformでbitwise-identical outputを保証するのが難しい場合がある。その場合、サポートするOS・architecture、numeric tolerance、nondeterministic componentを明示する。

## 3. Releaseは「どのcommitを引用するか」を定める契約

### Tag、release、archiveの違い

- Git tagは特定のcommitに付けた名前である。
- hosting serviceのreleaseは、tagへrelease noteとbinary artifactを結び付けた配布オブジェクトである。
- archiveはsourceとmetadataを長期保存する別の研究recordである。

3つのオブジェクトのversionは一致しなければならない。

~~~text
package metadata version
  = documentation version
  = CITATION.cff version
  = release title
  = git tag
  = archived record version
~~~

### Versioning policy

Semantic Versioningを使えるが、研究softwareにおける「public API」が何かを先に決める必要がある。

- command-line optionとfile format
- Python/C++ API
- configuration schema
- numerical methodまたはdefaultの意味
- output schemaとunits
- trained weightsまたはparameter bundle

数値手法やdefaultを変え、同じ入力のscientific interpretationが変わるなら、単純なpatchとみなすか慎重に判断すべきである。version numberよりcompatibility contractが優先される。

### Tagを移動させない

すでに公開したtagを別commitへforce-updateすると、同じversion名が異なるsourceを意味してしまう。修正が必要なら新しいpatch releaseを作り、旧versionのknown issueを記録する。

## 4. Releaseに含める再現性bundle

最低限、releaseには次が必要である。

### 理解と実行

- README：目的、範囲、quick start
- LICENSE：sourceとbundled assetの利用条件
- environment/lock file
- configuration exampleとschema
- input/output data dictionary
- 最小end-to-end example
- known limitations

### 品質の根拠

- automated test結果
- analyticまたはbenchmark verification
- numerical tolerance
- deterministic/nondeterministic contract
- supported platform matrix
- changelogとmigration note

### 来歴

- source revision
- release dateとversion
- dependency lock digest
- container image digestがあるならtagと併記
- input data versionまたはchecksum
- figure/table生成command

source archiveへlarge generated outputとsecretを無条件に入れない。再生成可能なoutputにはrecipeとchecksumを提供し、必要なdataはlicenseとprivacyを確認して別のarchival objectへ接続する。

## 5. CITATION.cffの役割

`CITATION.cff`は、人が読めてツールも解釈できるYAMLベースのcitation metadataファイルである。リポジトリrootへ置くと、対応するhosting UIが引用情報を表示できる。現在の公式CFF案内とGitHub文書は`cff-version: 1.2.0`形式を例示している。

次は構造を示す一般的なtemplateである。

~~~yaml
cff-version: 1.2.0
message: "If you use this software, please cite this version."
title: "Example Scientific Software"
type: software
version: 1.0.0
date-released: 2026-07-21
license: MIT
repository-code: "https://example.org/example-software"
authors:
  - family-names: "Replace-With-Family-Name"
    given-names: "Replace-With-Given-Name"
~~~

placeholderは実際の公開metadataに置き換え、CFF validatorで検証する。個人emailはcitationに必須ではなく、公開の必要がなければ記載しない。

### 最低限一致させるフィールド

- software title
- creatorsと順序
- version
- release date
- repository URL
- license
- version-specific software DOI

貢献者の順序をcommit数から自動決定しない。著者資格とcontributor roleの方針を事前に定め、必要ならcontributor metadataを別途提供する。

### Software自体とpaperをどう接続するか

`preferred-citation`で関連paperを提示できるが、repositoryのcitation UIがsoftwareよりpaperの引用を優先する可能性がある。software自体へのcreditと正確なversionの再現が重要なら、root citationをsoftware recordとして維持し、paperはreferences/related identifiersで接続する方が明確である。

## 6. DOIを付ける前にarchiveを理解する

DOIはsource code内の数字の装飾ではなく、特定のresearch objectを識別するpersistent identifierである。Zenodoの現行案内によれば、recordをpublishするとDOIが登録され、fileを変更した新versionは別recordとpersistent identifierで管理される。

### Version DOIとConcept DOI

ZenodoのDOI versioningでは、最初のpublish時に2種類のDOIが提供される。

- **Version DOI**：特定releaseのfileを識別
- **Concept DOI**：すべてのversionを束ね、最新versionのlanding pageへ接続

再現のために「この結果で使った正確なコード」を引用するときはversion DOIが基本である。継続的に発展するsoftware project全体へ言及するときはconcept DOIが適切な場合がある。

DOI文字列へ恣意的に`.v2`のようなsuffixを付けてversionを作ってはならない。version関係はarchive metadataで接続する。

## 7. Zenodoとreleaseを安全に接続する手順

Git hosting連携を使う一般的なフローは次のとおりである。

1. 公開可能なrepositoryか確認する。
2. secret scan、history audit、license auditを実施する。
3. archive integrationでrepositoryを有効化する。
4. release candidate commitを固定する。
5. tests、documentation build、example reproductionを実行する。
6. version metadataと`CITATION.cff`を一致させる。
7. immutable tagとreleaseを作る。
8. archive recordのtitle、creators、resource type、version、licenseをレビューする。
9. publish後、version DOIとconcept DOIを区別して記録する。
10. release page、README、CFF、paper metadataへ正しい関係を追加する。

GitHubの公式案内は、Zenodo連携によりrepository archiveへDOIを発行でき、連携対象repositoryがpublicでなければならないと説明する。組織repositoryではintegrationへのアクセス承認が別途必要な場合がある。

### DOIをrelease前にファイルへ入れたい場合

2つの方法がある。

- archiveでDOIを事前予約し、release metadataへ入れる。
- 最初のreleaseをarchiveした後でDOIをdefault branchへ反映し、次回releaseからversion metadataを完全同期する。

事前予約したdraftを削除すると予約DOIを失う可能性があるため、archiveの現行方針を確認する。また、すでに同じオブジェクトにDOIがあるなら、新しいDOIを重複発行せず、既存DOIをmetadataへ入力する。

## 8. Software DOIとpreprint DOIは決して同じオブジェクトではない

softwareとpreprintは異なる研究成果物である。

| 区分 | Software record | Preprint record |
|---|---|---|
| 内容 | source、package、executable、documentation | 研究課題、方法、結果、解釈 |
| resource type | software | preprint/publication |
| versionの意味 | code release | manuscript revision |
| 主な引用対象 | 実行した正確なsoftware version | 読み、議論した文書version |
| identifier | software DOI | preprint DOI/identifier |

したがって、次を避ける。

- preprint DOIを`CITATION.cff`のsoftware DOI欄へ入れる
- software archiveへpreprint fileを混在させ、resource typeを一つにまとめる
- journal article DOIをsupplemental code uploadのDOIとして再利用する
- code release versionとmanuscript revisionへ同じ番号体系を強制する

代わりにarchive metadataで関係を接続する。

- software **IsSupplementTo** paper
- software **IsDocumentedBy** paperまたは別documentation record
- paper **References** software
- software **Requires** input dataset、dataset **IsRequiredBy** software

実際のrelation type名は利用するarchiveのmetadata vocabularyで確認し、方向を再確認する。prose descriptionだけでなく、machine-readableなrelated identifierを提供することが望ましい。

## 9. Source、environment、dataを一緒に固定する

software DOIがあってもdependencyとinputがなければ結果を再現できない。

### Source

- exact tagとcommit
- submodule revision
- generated sourceのgenerator version
- build script

### Environment

- dependency lock file
- compiler/interpreter version
- OSとarchitecture
- numeric libraryとaccelerator runtime
- container digestまたはenvironment export

container tagとして`latest`だけを記録すると、時間経過により異なるimageを指し得る。immutable digestを併記する。

### Dataとconfiguration

- input dataset version/DOI
- file checksum
- preprocessing codeとorder
- configuration file
- random seedとsplit manifest
- schemaとunits

raw dataを公開できない場合、synthetic/minimal example、schema、generator、アクセス条件を提供し、何が非公開で完全再現が制限されるかを明示する。

## 10. 自動化できるrelease gate

CI release workflowは最低限、次を検査できる。

~~~text
[quality]
unit + integration + numerical tests pass
example workflow reproduces expected metrics
documentation builds without broken internal links

[metadata]
package version == tag version
CITATION.cff parses and validates
release date and changelog entry exist
license and notices are present

[security]
secret scan passes
private paths and hostnames are absent
large or restricted data are not bundled

[archive readiness]
source archive is self-contained
dependency lock exists
input/output schema is documented
~~~

DOI発行自体はpublishという外部状態変更なので、dry runとhuman reviewを設ける方が安全である。一度公開されたarchival recordを単なるbranchのように扱ってはならない。

## 11. Release runbook

### 準備

- scopeとcompatibility changeを分類する。
- versionを決める。
- changelogとmigration noteを作成する。
- 古いdependencyとlicenseを点検する。
- citation author/contributor metadataをreviewする。

### 検証

- clean environmentでbuildする。
- 最小exampleを最初から再実行する。
- 主要figure/table生成commandを確認する。
- numerical toleranceとplatform差を確認する。
- archiveへ含めるsource bundleを実際に展開して実行する。

### 発行

- release commitをmergeする。
- annotated/signed tag方針があれば適用する。
- release noteとartifact checksumを公開する。
- archival record metadataを最終レビューしてからpublishする。
- version DOIをreleaseとCFFへ接続する。

### 発行後

- DOIが正しいlanding pageへresolveするか確認する。
- archiveのfile一覧とchecksumを確認する。
- concept/version DOIが意図どおり表示されるか確認する。
- repository、documentation、preprintのrelated identifierを更新する。
- 次回release用のrunbook issueを残す。

## 12. 検証チェックリスト

- [ ] repository、commit、tag、release、archiveの役割を区別したか。
- [ ] tag・package・文書・CFF・archiveのversionが一致するか。
- [ ] 公開済みtagを移動しない方針があるか。
- [ ] clean environmentでend-to-end exampleを実行できるか。
- [ ] dependencyとinput data versionが固定されているか。
- [ ] `CITATION.cff`がrootにあり、validatorを通過するか。
- [ ] software title、creator順、version、licenseがarchive metadataと同じか。
- [ ] version DOIとconcept DOIの用途を区別したか。
- [ ] software DOIとpreprint/article DOIを別オブジェクトとして管理するか。
- [ ] 関連DOIをmachine-readable relationで接続したか。
- [ ] sourceとarchiveにsecret・個人パス・非公開dataがないか。
- [ ] container tagだけでなくimmutable digestも記録したか。
- [ ] DOI publish前に人がmetadataとfile bundleをreviewするか。

## 13. よくある落とし穴と限界

### 「Gitにあるから永久保存される」

hosting URLとaccountは保存識別子ではない。archiveとDOIは長期アクセス可能性を高めるが、license・metadata・実行recipeがなければ活用しにくい。

### 「DOIがあるから再現可能である」

DOIはオブジェクトを識別する。dependency、data、configuration、numerical toleranceを自動提供しない。

### 最新Concept DOIだけを引用する

読者が後からincompatible versionを受け取る可能性がある。特定の研究結果を再現するにはversion DOIとrelease versionが必要である。

### DOIをREADMEへ手作業でコピーし不一致になる

CFF、package metadata、release note、archive metadataを可能な限り単一sourceから生成するか、CIで相互検証する。

### 公開リポジトリから履歴を消せばsecretも消えるという誤解

secretはhistory、fork、CI log、release artifact、archiveに残り得る。露出時は削除だけでなく直ちにrevoke・rotateし、各保存場所を点検する。

### Sourceだけで実行契約がない

サポートplatform、tolerance、nondeterministic component、expected runtime範囲を文書化しなければ、再現失敗がbugか環境差か判断しにくい。

## 14. 公式参考資料

- [Citation File Format公式案内](https://citation-file-format.github.io/)
- [GitHubのCITATIONファイル案内](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files)
- [GitHub repositoryをDOIで保存する公式案内](https://docs.github.com/repositories/archiving-a-github-repository/referencing-and-citing-content)
- [Zenodo recordとversionのライフサイクル](https://help.zenodo.org/docs/deposit/about-records/)
- [Zenodo DOI versioning案内](https://support.zenodo.org/help/en-gb/1-upload-deposit/97-what-is-doi-versioning)
- [Zenodo DOI予約案内](https://help.zenodo.org/docs/deposit/describe-records/reserve-doi/)
- [DataCite related identifier関係型の定義](https://datacite-metadata-schema.readthedocs.io/en/4.6/appendices/appendix-1/relationType/)

## まとめ

再現可能な研究softwareの中心的な接続は次のとおりである。

~~~text
result
  -> input/data version
  -> configuration
  -> software version DOI
  -> release tag
  -> exact commit
  -> locked environment
~~~

そしてpaper/preprintは、この接続を説明し主張する別のオブジェクトである。softwareと文書のDOIを分離し、related identifierで接続してこそ、creditと再現性を同時に守れる。

良いreleaseとは「コードを公開した日」ではなく、第三者がどのversionを取得し、どの環境で何を実行すべきかを、もはや推測しなくてよい状態である。
