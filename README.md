# Codex Harness Framework

Codex용 phase 기반 작업 하네스 템플릿이다. 프로젝트 문서로 맥락을 고정하고, 구현 작업을 작은 step으로 쪼갠 뒤, 각 step을 별도의 `codex exec` 세션에서 실행한다.

## Claude 버전에서 바뀐 대응 관계

| Claude Harness | Codex Harness |
| --- | --- |
| `CLAUDE.md` | `AGENTS.md` |
| `.claude/commands/harness.md` | `.codex/skills/codex-harness-planner/SKILL.md` |
| `.claude/commands/review.md` | `.codex/skills/codex-harness-review/SKILL.md` |
| `.claude/settings.json` | `.codex/hooks.json` |
| `claude -p` | `codex exec` |
| `CLAUDE_TOOL_INPUT` hook input | Codex hook JSON stdin (`tool_name`, `tool_input`) |

## 기본 프로세스

Harness는 구현을 바로 시작하는 도구가 아니라, 프로젝트 맥락을 문서로 먼저 고정한 뒤 작업을 작은 step으로 나누어 실행하는 흐름이다. Codex 버전에서도 기존 Claude 버전과 동일하게 문서 작성이 먼저다.

1. 프로젝트를 충분히 기획한다.
   - 해결하려는 문제, 사용자, MVP 범위, 제외할 범위, 디자인 방향을 정한다.
   - 기술 스택, 아키텍처 원칙, 데이터 흐름, 상태 관리, 검증 명령을 정한다.
   - 불확실한 내용은 추정하지 말고 사용자와 논의해 확정한다.
2. `AGENTS.md`와 `docs/*.md`를 실제 프로젝트 정보로 채운다.
   - `AGENTS.md`: 기술 스택, CRITICAL 규칙, 개발 프로세스, 명령어
   - `docs/PRD.md`: 목표, 사용자, 핵심 기능, MVP 제외 사항, 디자인
   - `docs/ARCHITECTURE.md`: 디렉토리 구조, 패턴, 데이터 흐름, 상태 관리
   - `docs/ADR.md`: 주요 기술 결정, 이유, 트레이드오프
   - `docs/UI_GUIDE.md`: UI 방향이 필요한 경우 함께 작성
3. 문서가 충분히 채워진 뒤 `codex-harness-planner` skill을 실행한다.
   - 예: "Use $codex-harness-planner to create a phase plan for 0-mvp."
   - 사용자 입장에서 준비 후 마지막으로 취하는 주요 액션은 이 skill 실행이다.
   - 이후 skill이 문서를 읽고, 필요한 논의를 진행하고, phase/step 초안을 작성해 피드백을 요청한다.
   - 사용자가 승인하면 `phases/index.json`, `phases/{phase}/index.json`, `phases/{phase}/stepN.md` 같은 계획 파일을 생성한다.
   - 생성된 phase를 실행해야 할 때는 아래 실행 엔진을 사용한다.

## 실행 엔진

`scripts/execute.py`는 `codex-harness-planner`가 만든 phase를 실행하는 엔진이다.

```bash
python scripts/execute.py 0-mvp
python scripts/execute.py 0-mvp --push
```

실행 엔진은 다음을 자동 처리한다.

- `codex/{phase}` 브랜치 생성 또는 checkout
- `AGENTS.md`와 `docs/*.md`를 매 step 프롬프트에 포함
- 완료된 step의 `summary`를 다음 step 컨텍스트로 전달
- 실패 시 최대 3회 재시도
- 같은 에러가 3회 반복되면 circuit breaker로 중단
- step 결과를 `phases/{phase}/stepN-output.json`에 저장
- 코드 변경과 phase 메타데이터를 분리 커밋

## Codex hooks

`.codex/hooks.json`은 다음 안전망을 켠다.

- 위험 명령어 차단: `rm -rf`, `git reset --hard`, forced push, destructive SQL 등
- TDD 가드: `src/`, `app/`, `components/`, `lib/`, `services/` 등의 production code 변경에 테스트 파일이 같은 patch에 없으면 차단
- Stop 검증: `package.json`에 존재하는 `lint`, `build`, `test` script를 순서대로 실행

Codex는 hook 기능을 기본으로 켜며, 프로젝트가 trusted 상태이면 `<repo>/.codex/hooks.json`을 직접 로드한다. 별도의 project-local `.codex/config.toml`은 필요하지 않다.

## Codex skills

Claude custom command는 자연어 워크플로우 문서였기 때문에 Python 래퍼가 아니라 Codex skill로 유지한다.

- `.codex/skills/codex-harness-planner/SKILL.md`: phase/index/step 계획 파일 생성 절차
- `.codex/skills/codex-harness-review/SKILL.md`: 아키텍처, 기술 스택, 테스트, CRITICAL 규칙, 빌드 가능성 리뷰 절차

이 저장소를 템플릿으로 복사한 뒤, `.codex/skills/*`를 `$CODEX_HOME/skills` 또는 `~/.codex/skills`로 복사하면 Codex가 skill로 발견할 수 있다. 이후 `$codex-harness-planner` 또는 `$codex-harness-review`로 호출한다.
