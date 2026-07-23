# Technical Notes 공개·편집 정책

이 저장소는 재사용 가능한 기술 지식과 검증 가능한 방법론을 공개하기 위한 곳이다. 원시 대화 기록이나 개인 작업 일지를 그대로 보관하지 않는다.

## 공개하는 내용

- 개념의 정확한 정의와 mental model
- 독립적으로 실행 가능한 최소 예제
- 설계 대안과 trade-off
- 실패 모드, 검증 절차, 운영 checklist
- 공개 표준·공식 문서에 근거한 일반 방법론
- 식별할 수 없는 synthetic example

## 공개하지 않는 내용

- 개인·가족·연락처·주소·계정 복구 정보
- 현재·과거 회사, 고객, 협력사, 내부 시스템을 식별할 수 있는 정보
- token, password, key, cookie, secret, 실제 endpoint와 내부 경로
- 원시 ChatGPT 대화, 대화 URL, prompt history
- 비공개 코드·문서·데이터의 원문 또는 실질적으로 복원 가능한 요약
- 미공개 연구 질문, 특정 데이터, 실험 조건·수치·결과, 투고 전략
- 개인의 건강·재무·채용·가족·일정 정보

연구 관련 글은 특정 연구 대상이 아니라 문제 정의, verification·validation 구분, 실험설계, 불확실성, 재현성, 소프트웨어 릴리스 같은 **일반 방법론**만 다룬다.

## 예제 작성 규칙

- 이름은 `example`, `sample`, `resource-id`처럼 명백한 가상 값만 사용한다.
- URL은 `example.com` 또는 표준 문서 URL을 사용한다.
- 비밀값은 `SECRET_FROM_MANAGER`처럼 저장 위치를 설명하는 placeholder로 쓴다.
- 절대 사용자 경로 대신 저장소 기준 상대 경로를 사용한다.
- 성능 수치가 필요하면 설명용 가상 값임을 밝히거나 수치 없이 관계를 설명한다.
- 특정 제품 버전이 필요할 때만 명시하고, 확인 날짜 또는 공식 문서를 연결한다.

## 포스트 구조

각 글은 가능한 범위에서 다음 순서를 따른다.

1. 문제와 적용 범위
2. 핵심 mental model 또는 정의
3. 실전 workflow와 최소 예제
4. 검증 checklist
5. 흔한 실패와 한계
6. 공식 참고 자료

Front matter에는 `title`, `date`, 2단 `categories`, 소문자 `tags`, 한 문장 `description`, `lang`, `translation_key`를 둔다.

## 다국어 편집 규칙

- 기술 포스트는 `ko-KR`, `ja-JP`, `en`, `fr-FR`, `de-DE` 다섯 판을 하나의 `translation_key`로 묶는다.
- 제목, 설명, 본문, 표, checklist는 해당 언어의 자연스러운 기술 문장으로 번역한다.
- 명령, 코드, 식별자, 공식 문서 URL, 수식의 의미는 원문과 동일하게 유지한다.
- 번역판에는 `hidden: true`를 두고 언어별 색인과 글 상단 전환 메뉴에서 접근한다.
- 번역하면서 새로운 사례·수치·프로젝트 맥락을 추가하지 않는다.

## 공개 전 점검

1. `python3 tools/content_audit.py`와 `python3 tools/translation_audit.py`를 실행한다.
2. 이름, 연락처, 회사·프로젝트 식별자, 실제 수치가 없는지 사람이 다시 읽는다.
3. 연구 글은 구체 대상이 없어도 방법론이 독립적으로 유용한지 확인한다.
4. 코드와 명령이 파괴적이지 않고 placeholder가 명백한지 확인한다.
5. Jekyll build와 내부 link 검사를 통과시킨다.
6. PR diff에서 삭제된 민감정보가 Git history에 남지 않는지 확인한다.

자동 검사는 높은 확률의 누출을 막는 보조 수단이다. 최종 공개 판단은 항상 사람이 diff 전체를 검토해 내린다.
