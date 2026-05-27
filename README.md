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

## 기본 사용법

1. `AGENTS.md`와 `docs/*.md`의 자리표시자를 실제 프로젝트 정보로 채운다.
2. `codex-harness-planner` skill을 사용해 phase 계획을 생성한다. 예: "Use $codex-harness-planner to create a phase plan for 0-mvp."

3. 생성된 `phases/0-mvp/*.md`를 검토한다.
4. step을 순차 실행한다.

```bash
python scripts/execute.py 0-mvp
```

5. `codex-harness-review` skill을 사용해 변경 사항을 리뷰한다. 예: "Use $codex-harness-review to review the uncommitted changes."

## 실행 엔진

`scripts/execute.py`는 다음을 자동 처리한다.

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
