---
title: "재현 가능한 연구 소프트웨어 배포: Release·CITATION.cff·Zenodo DOI"
date: 2026-07-21 10:00:00 +0900
categories: [Research Engineering, Reproducibility]
tags: [research-software, reproducibility, release, git-tag, citation-cff, zenodo, software-doi, preprint]
description: "연구 코드 저장소를 재현 가능한 release로 만들고 CITATION.cff, 보존 archive, software DOI를 연결하되 논문·preprint와 식별자를 분리하는 절차를 정리한다."
lang: ko-KR
translation_key: reproducible-research-software-release-doi
---

{% include language-switcher.html %}

연구 코드가 공개 저장소에 있다는 사실만으로 재현 가능하거나 인용 가능한 것은 아니다. default branch는 계속 바뀌고, dependency는 사라지며, 어떤 commit이 결과를 만들었는지 독자가 알기 어렵기 때문이다.

연구 소프트웨어를 제대로 공개하려면 네 대상을 구분해야 한다.

1. 개발이 계속되는 **source repository**
2. 의미 있는 상태를 고정한 **versioned release와 tag**
3. 장기 보존과 인용을 위한 **archival software record와 DOI**
4. 연구 질문·방법·결과를 설명하는 **paper 또는 preprint**

이 글은 이 네 객체를 섞지 않고 서로 추적 가능하게 연결하는 실전 절차를 정리한다.

## 1. 먼저 “무엇을 식별하는가”를 분리한다

| 객체 | 주 역할 | 변경 가능성 | 대표 식별자 |
|---|---|---|---|
| repository | 협업과 지속 개발 | branch는 계속 변함 | repository URL |
| commit | source snapshot | content-addressed, 사실상 고정 | commit hash |
| tag | 사람이 읽는 version label | 정책상 immutable 권장 | tag name + target commit |
| release | 배포 설명과 artifact 묶음 | release note는 수정 가능할 수 있음 | version + release URL |
| software archive | 장기 보존된 연구 객체 | version record file은 고정 | software DOI |
| preprint/article | 연구 주장과 서술 | version 정책은 플랫폼별 상이 | publication DOI 또는 identifier |
| dataset | 입력·출력 데이터 객체 | version별 고정 권장 | dataset DOI |

commit hash는 정확한 source를 가리키지만 학술 metadata와 장기 보존 정책을 제공하지 않는다. DOI는 영구 식별과 metadata 연결을 제공하지만 실행 환경을 자동으로 복원하지 않는다. 둘을 함께 써야 한다.

## 2. 재현성 수준을 명시한다

“재현 가능”이라는 말만 쓰지 말고 지원 범위를 정의한다.

- **Source reproducibility**: 같은 source tree를 얻을 수 있다.
- **Build reproducibility**: 지정 환경에서 같은 executable 또는 package를 만들 수 있다.
- **Computational reproducibility**: 입력에서 허용 오차 내 같은 output을 얻는다.
- **Result reproducibility**: 논문의 figure·table·metric을 다시 생성한다.
- **Auditability**: 결과에서 code, configuration, data provenance를 역추적할 수 있다.

모든 플랫폼에서 bitwise-identical output을 보장하기 어려울 수 있다. 그 경우 지원 OS·architecture, numeric tolerance, nondeterministic component를 명시한다.

## 3. Release는 “어느 commit을 인용할지” 정하는 계약

### Tag, release, archive의 차이

- Git tag는 특정 commit에 붙인 이름이다.
- hosting service의 release는 tag에 release note와 binary artifact를 연결한 배포 객체다.
- archive는 source와 metadata를 장기 보존하는 별도 연구 record다.

세 객체의 version이 일치해야 한다.

~~~text
package metadata version
  = documentation version
  = CITATION.cff version
  = release title
  = git tag
  = archived record version
~~~

### Versioning policy

Semantic Versioning을 사용할 수 있지만 연구 software의 “public API”가 무엇인지 먼저 정해야 한다.

- command-line option과 file format
- Python/C++ API
- configuration schema
- numerical method 또는 default의 의미
- output schema와 units
- trained weights 또는 parameter bundle

수치 방법이나 default를 바꿔 같은 입력의 scientific interpretation이 달라진다면 단순 patch로 볼지 신중해야 한다. version number보다 compatibility contract가 우선이다.

### Tag는 이동시키지 않는다

이미 공개한 tag를 다른 commit으로 force-update하면 같은 version 이름이 서로 다른 source를 뜻하게 된다. 수정이 필요하면 새 patch release를 만들고 이전 version의 known issue를 기록한다.

## 4. Release에 포함할 재현성 묶음

최소 release에는 다음이 필요하다.

### 이해와 실행

- README: 목적, 범위, quick start
- LICENSE: source와 bundled asset의 사용 조건
- environment/lock file
- configuration example과 schema
- input/output data dictionary
- 최소 end-to-end example
- known limitations

### 품질 근거

- automated test 결과
- analytic 또는 benchmark verification
- numerical tolerance
- deterministic/nondeterministic contract
- supported platform matrix
- changelog와 migration note

### 계보

- source revision
- release date와 version
- dependency lock digest
- container image digest가 있다면 tag와 함께 기록
- input data version 또는 checksum
- figure/table 생성 command

source archive에 large generated output과 secret을 무조건 넣지 않는다. 재생성 가능한 output은 recipe와 checksum을 제공하고, 필요한 data는 license와 privacy를 확인해 별도 archival object로 연결한다.

## 5. CITATION.cff의 역할

`CITATION.cff`는 사람이 읽고 도구도 해석할 수 있는 YAML 기반 citation metadata 파일이다. 저장소 root에 두면 지원되는 hosting UI가 인용 정보를 표시할 수 있다. 현재 공식 CFF 안내와 GitHub 문서는 `cff-version: 1.2.0` 형식을 예시로 제공한다.

다음은 구조를 보여 주는 일반 template이다.

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

placeholder는 실제 공개 metadata로 교체하고 CFF validator로 검증한다. 개인 email은 citation에 필수적이지 않으며 공개 필요성이 없으면 넣지 않는다.

### 최소한 일치시킬 필드

- software title
- creators와 순서
- version
- release date
- repository URL
- license
- version-specific software DOI

기여자 순서는 commit count로 자동 결정하지 않는다. 저자 자격과 contributor role 정책을 사전에 정하고, 필요하면 contributor metadata를 별도로 제공한다.

### Software 자체와 paper를 어떻게 연결할까

`preferred-citation`으로 관련 paper를 제시할 수 있지만, repository의 citation UI가 software 대신 paper 인용을 우선하도록 만들 수 있다. software 자체의 credit와 정확한 version 재현이 중요하면 root citation을 software record로 유지하고 paper는 references/related identifiers에서 연결하는 방식이 명확하다.

## 6. DOI를 붙이기 전 archive를 이해한다

DOI는 source code 안의 숫자 장식이 아니라 특정 research object를 식별하는 persistent identifier다. Zenodo의 현재 안내에 따르면 record를 publish하면 DOI가 등록되고, file이 바뀐 새 version은 별도 record와 persistent identifier로 관리된다.

### Version DOI와 Concept DOI

Zenodo의 DOI versioning은 첫 publish에서 두 범주의 DOI를 제공한다.

- **Version DOI**: 특정 release 파일을 식별
- **Concept DOI**: 모든 version의 묶음을 식별하며 최신 version landing page로 연결

재현을 위해 “이 결과에 사용한 정확한 코드”를 인용할 때는 version DOI가 기본이다. 계속 발전하는 software project 전체를 언급할 때는 concept DOI가 적절할 수 있다.

DOI 문자열에 임의로 `.v2` 같은 suffix를 붙여 version을 만들면 안 된다. version 관계는 archive metadata로 연결한다.

## 7. Zenodo와 release를 연결하는 안전한 절차

Git hosting 연동을 사용하는 일반 흐름은 다음과 같다.

1. 공개 가능한 repository인지 확인한다.
2. secret scan, history audit, license audit를 수행한다.
3. archive integration에서 repository를 활성화한다.
4. release candidate commit을 고정한다.
5. tests, documentation build, example reproduction을 실행한다.
6. version metadata와 `CITATION.cff`를 맞춘다.
7. immutable tag와 release를 만든다.
8. archive record의 title, creators, resource type, version, license를 검토한다.
9. publish 후 version DOI와 concept DOI를 구분해 기록한다.
10. release page, README, CFF, paper metadata에 올바른 관계를 추가한다.

GitHub의 공식 안내는 Zenodo 연동으로 repository archive에 DOI를 발급할 수 있으며, 연동 대상 repository가 public이어야 한다고 설명한다. 조직 repository라면 integration 접근 승인이 별도로 필요할 수 있다.

### DOI를 release 전에 파일에 넣고 싶다면

두 방법이 있다.

- archive에서 DOI를 사전 예약한 뒤 release metadata에 넣는다.
- 첫 release를 archive한 후 DOI를 default branch에 반영하고 다음 release부터 version metadata를 완전 동기화한다.

사전 예약한 draft를 삭제하면 예약 DOI를 잃을 수 있으므로 archive의 현재 정책을 확인한다. 또한 이미 같은 객체에 DOI가 있다면 새 DOI를 중복 발급하지 말고 기존 DOI를 metadata에 입력한다.

## 8. Software DOI와 preprint DOI는 절대 같은 객체가 아니다

software와 preprint는 서로 다른 연구 산출물이다.

| 구분 | Software record | Preprint record |
|---|---|---|
| 내용 | source, package, executable, documentation | 연구 질문, 방법, 결과, 해석 |
| resource type | software | preprint/publication |
| version 의미 | code release | manuscript revision |
| 주 인용 대상 | 실행한 정확한 software version | 읽고 논의한 문서 version |
| identifier | software DOI | preprint DOI/identifier |

따라서 다음을 피한다.

- preprint DOI를 `CITATION.cff`의 software DOI 자리에 넣기
- software archive에 preprint 파일을 섞고 resource type을 하나로 퉁치기
- journal article DOI를 supplemental code upload의 DOI로 재사용하기
- code release version과 manuscript revision을 같은 번호 체계로 강제하기

대신 archive metadata에서 관계를 연결한다.

- software **IsSupplementTo** paper
- software **IsDocumentedBy** paper 또는 별도 documentation record
- paper **References** software
- software **Requires** input dataset, dataset **IsRequiredBy** software

실제 relation type 이름은 사용하는 archive의 metadata vocabulary에서 확인하고 방향을 검산한다. prose description만 쓰지 말고 machine-readable related identifier를 제공하는 것이 좋다.

## 9. Source, environment, data를 함께 고정하기

software DOI가 있어도 dependency와 input이 없으면 결과를 재현하지 못한다.

### Source

- exact tag와 commit
- submodule revision
- generated source의 generator version
- build script

### Environment

- dependency lock file
- compiler/interpreter version
- OS와 architecture
- numeric library와 accelerator runtime
- container digest 또는 environment export

container tag `latest`만 기록하면 시간이 지나며 다른 image를 가리킬 수 있다. immutable digest를 병기한다.

### Data와 configuration

- input dataset version/DOI
- file checksum
- preprocessing code와 order
- configuration file
- random seed와 split manifest
- schema와 units

raw data를 공개할 수 없다면 synthetic/minimal example, schema, generator, 접근 조건을 제공하고 무엇이 비공개라 완전 재현이 제한되는지 명시한다.

## 10. 자동화 가능한 release gate

CI release workflow는 최소한 다음을 검사할 수 있다.

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

DOI 발급 자체는 publish라는 외부 상태 변경이므로 dry run과 human review를 두는 편이 안전하다. 한번 공개된 archival record는 단순 branch처럼 취급해서는 안 된다.

## 11. Release runbook

### 준비

- scope와 compatibility change를 분류한다.
- version을 결정한다.
- changelog와 migration note를 작성한다.
- 오래된 dependency와 license를 점검한다.
- citation author/contributor metadata를 review한다.

### 검증

- clean environment에서 build한다.
- 최소 example을 처음부터 재실행한다.
- 핵심 figure/table 생성 command를 확인한다.
- numerical tolerance와 platform 차이를 확인한다.
- archive에 포함될 source bundle을 직접 풀어 실행한다.

### 발행

- release commit을 merge한다.
- annotated/signed tag 정책이 있으면 적용한다.
- release note와 artifact checksum을 게시한다.
- archival record metadata를 최종 검토한 뒤 publish한다.
- version DOI를 release와 CFF에 연결한다.

### 발행 후

- DOI가 올바른 landing page로 resolve되는지 확인한다.
- archive의 file 목록과 checksum을 확인한다.
- concept/version DOI가 의도대로 표시되는지 확인한다.
- repository, documentation, preprint의 related identifier를 갱신한다.
- 다음 release를 위한 runbook issue를 남긴다.

## 12. 검증 체크리스트

- [ ] repository, commit, tag, release, archive의 역할을 구분했는가?
- [ ] tag·package·문서·CFF·archive version이 일치하는가?
- [ ] 공개된 tag를 이동시키지 않는 정책이 있는가?
- [ ] clean environment에서 end-to-end example이 실행되는가?
- [ ] dependency와 input data version이 고정되어 있는가?
- [ ] `CITATION.cff`가 root에 있고 validator를 통과하는가?
- [ ] software title, creator 순서, version, license가 archive metadata와 같은가?
- [ ] version DOI와 concept DOI의 용도를 구분했는가?
- [ ] software DOI와 preprint/article DOI를 별도 객체로 관리하는가?
- [ ] 관련 DOI를 machine-readable relation으로 연결했는가?
- [ ] source와 archive에 secret·개인 경로·비공개 data가 없는가?
- [ ] container tag뿐 아니라 immutable digest를 기록했는가?
- [ ] DOI publish 전에 사람이 metadata와 file bundle을 review하는가?

## 13. 흔한 함정과 한계

### “Git에 있으니 영구 보존된다”

hosting URL과 account는 보존 식별자가 아니다. archive와 DOI는 장기 접근 가능성을 높이지만, license·metadata·실행 recipe가 없으면 활용성이 낮다.

### “DOI가 있으니 재현 가능하다”

DOI는 객체를 식별한다. dependency, data, configuration, numerical tolerance를 자동으로 제공하지 않는다.

### 최신 Concept DOI만 인용

독자가 나중의 incompatible version을 받을 수 있다. 특정 연구 결과 재현에는 version DOI와 release version이 필요하다.

### DOI를 README에 수동 복사하다 불일치

CFF, package metadata, release note, archive metadata를 가능한 한 하나의 source에서 생성하거나 CI로 교차 검증한다.

### 공개 저장소에서 기록을 지우면 secret도 사라진다는 오해

secret은 history, fork, CI log, release artifact, archive에 남을 수 있다. 노출 시 삭제만 하지 말고 즉시 revoke·rotate하고 각 보존 위치를 점검한다.

### Source만 있고 실행 계약이 없음

지원 platform, tolerance, nondeterministic component, expected runtime 범위를 문서화하지 않으면 재현 실패가 bug인지 환경 차이인지 판단하기 어렵다.

## 14. 공식 참고 자료

- [Citation File Format 공식 안내](https://citation-file-format.github.io/)
- [GitHub의 CITATION 파일 안내](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files)
- [GitHub repository를 DOI로 보존하는 공식 안내](https://docs.github.com/repositories/archiving-a-github-repository/referencing-and-citing-content)
- [Zenodo record와 version의 생명주기](https://help.zenodo.org/docs/deposit/about-records/)
- [Zenodo DOI versioning 안내](https://support.zenodo.org/help/en-gb/1-upload-deposit/97-what-is-doi-versioning)
- [Zenodo DOI 예약 안내](https://help.zenodo.org/docs/deposit/describe-records/reserve-doi/)
- [DataCite related identifier 관계형 정의](https://datacite-metadata-schema.readthedocs.io/en/4.6/appendices/appendix-1/relationType/)

## 마무리

재현 가능한 연구 software의 핵심 연결은 다음과 같다.

~~~text
result
  -> input/data version
  -> configuration
  -> software version DOI
  -> release tag
  -> exact commit
  -> locked environment
~~~

그리고 paper/preprint는 이 연결을 설명하고 주장하는 별도 객체다. software와 문서의 DOI를 분리한 뒤 related identifier로 연결해야 credit과 재현성을 동시에 지킬 수 있다.

좋은 release는 “코드를 공개한 날”이 아니라, 제3자가 어떤 version을 받아 어떤 환경에서 무엇을 실행해야 하는지 더 이상 추측하지 않아도 되는 상태다.
