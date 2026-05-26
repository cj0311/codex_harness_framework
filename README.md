# Codex Harness Framework

Codex용 phase 기반 작업 하네스 템플릿이다. 프로젝트 문서로 맥락을 고정하고, 구현 작업을 작은 step으로 쪼갠 뒤, 각 step을 별도의 `codex exec` 세션에서 실행한다.

## Claude 버전에서 바뀐 대응 관계

| Claude Harness | Codex Harness |
| --- | --- |
| `CLAUDE.md` | `AGENTS.md` |
| `.claude/commands/harness.md` | `scripts/harness.py` |
| `.claude/commands/review.md` | `scripts/review.py` |
| `.claude/settings.json` | `.codex/config.toml` + `.codex/hooks.json` |
| `claude -p` | `codex exec` |
| `CLAUDE_TOOL_INPUT` hook input | Codex hook JSON stdin (`tool_name`, `tool_input`) |

## 기본 사용법

1. `AGENTS.md`와 `docs/*.md`의 자리표시자를 실제 프로젝트 정보로 채운다.
2. phase 계획을 생성한다.

```bash
python scripts/harness.py 0-mvp --project "프로젝트명"
```

3. 생성된 `phases/0-mvp/*.md`를 검토한다.
4. step을 순차 실행한다.

```bash
python scripts/execute.py 0-mvp
```

5. 변경 사항을 리뷰한다.

```bash
python scripts/review.py --uncommitted
```

## 실행 엔진

`scripts/execute.py`는 다음을 자동 처리한다.

- `codex/{phase}` 브랜치 생성 또는 checkout
- `AGENTS.md`와 `docs/*.md`를 매 step 프롬프트에 포함
- 완료된 step의 `summary`를 다음 step 컨텍스트로 전달
- 실패 시 최대 5회 재시도
- 같은 에러가 5회 반복되면 circuit breaker로 중단
- step 결과를 `phases/{phase}/stepN-output.json`에 저장
- 코드 변경과 phase 메타데이터를 분리 커밋

## Codex hooks

`.codex/hooks.json`은 다음 안전망을 켠다.

- 위험 명령어 차단: `rm -rf`, `git reset --hard`, forced push, destructive SQL 등
- TDD 가드: `src/`, `app/`, `components/`, `lib/`, `services/` 등의 production code 변경에 테스트 파일이 같은 patch에 없으면 차단
- Stop 검증: `package.json`에 존재하는 `lint`, `build`, `test` script를 순서대로 실행

Codex hooks는 프로젝트가 trusted 상태일 때 로드된다.
