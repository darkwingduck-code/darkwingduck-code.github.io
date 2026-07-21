# Gyeongtae Im — Technical Notes

재현 가능한 소프트웨어·데이터·시뮬레이션·AI 시스템을 만들기 위한 기술 기록입니다.

[Technical Notes 바로가기](https://darkwingduck-code.github.io)

[![Build and Deploy](https://github.com/darkwingduck-code/darkwingduck-code.github.io/actions/workflows/pages-deploy.yml/badge.svg)](https://github.com/darkwingduck-code/darkwingduck-code.github.io/actions/workflows/pages-deploy.yml)
[![GitHub license](https://img.shields.io/github/license/darkwingduck-code/darkwingduck-code.github.io.svg)](LICENSE)

## 다루는 기술 축

- Git, GitHub, CI/CD와 안전한 변경 관리
- Python, shell, container와 재현 가능한 실행 환경
- Terraform, cloud infrastructure와 운영 신뢰성
- 데이터베이스, API, 네트워크, 테스트와 애플리케이션 보안
- ML 평가, 시계열, MLOps, surrogate model과 AI agent
- 선형대수, 수치해석, 실험설계와 불확실성
- 시뮬레이션 verification/validation과 결정적 테스트
- 위험성평가와 연구 소프트웨어 재현성

각 글은 개념 요약에 그치지 않고 문제, mental model, 실행 가능한 패턴, 검증 checklist, 흔한 실패와 한계를 함께 기록합니다.

## 편집 원칙

- 원시 대화나 개인 작업 기록을 그대로 게시하지 않습니다.
- 특정 회사·고객·내부 프로젝트를 식별할 수 있는 정보는 제외합니다.
- 연구는 구체 주제·데이터·결과가 아닌 일반 방법론만 다룹니다.
- 예제는 공개 표준과 명백한 가상 값으로 독립적으로 재작성합니다.
- 재현 조건, 실패 모드, 적용 범위와 한계를 함께 밝힙니다.

자세한 기준은 [Technical Notes 공개·편집 정책](docs/CONTENT_POLICY.md)에 있습니다.

## 저장소 구조

```text
.
├── _posts/                  # 공개 기술 포스트
├── _tabs/                   # About, Archives, Categories, Tags
├── docs/                    # 편집 정책과 유지관리 문서
├── tools/
│   ├── content_audit.py     # 민감정보·front matter 사전 검사
│   ├── run.sh               # 로컬 미리보기
│   └── test.sh              # Jekyll build + 내부 링크 검사
├── .github/workflows/       # audit, build, GitHub Pages 배포
└── _config.yml              # Chirpy/Jekyll 사이트 설정
```

## 로컬 검증

Ruby와 Bundler가 준비된 환경에서 실행합니다.

```bash
bundle install
python3 tools/content_audit.py
bash tools/test.sh
```

로컬 미리보기:

```bash
bash tools/run.sh
```

Pull Request에서는 공개 범위와 diff를 검토하고, `main` 반영 후 GitHub Pages workflow가 production build와 배포를 수행합니다.

## License

별도 표시가 없는 저장소 콘텐츠와 코드는 [MIT License](LICENSE)를 따릅니다. 외부 표준과 공식 문서의 권리는 각 원저작자에게 있습니다.

사이트는 [Jekyll Theme Chirpy](https://github.com/cotes2020/jekyll-theme-chirpy)를 사용합니다.
