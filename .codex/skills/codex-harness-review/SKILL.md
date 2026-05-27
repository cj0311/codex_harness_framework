---
name: codex-harness-review
description: Codex Harness 프로젝트의 변경 사항을 문서, 아키텍처, ADR, 테스트, CRITICAL 규칙, 빌드 가능성 기준으로 리뷰한다. 사용자가 diff, commit, PR, 미커밋 변경, harness step 결과를 리뷰하라고 요청하거나 기존 .claude/commands/review.md 워크플로우를 Codex skill로 사용하려 할 때 사용한다.
---

# Codex Harness Review

이 프로젝트의 변경 사항을 리뷰하라.

## 사전 확인

먼저 다음 문서들을 읽어라:

- `/AGENTS.md`
- `/docs/ARCHITECTURE.md`
- `/docs/ADR.md`
- 제품 동작이 관련되면 `/docs/PRD.md`
- UI 동작이나 표현이 관련되면 `/docs/UI_GUIDE.md`

그런 다음 리뷰 대상 변경을 확인한다.

- 미커밋 변경: `git diff --stat`, `git diff`
- staged 변경: `git diff --cached --stat`, `git diff --cached`
- 특정 커밋: `git show --stat <commit>`, `git show <commit>`
- base 대비 현재 브랜치: `git diff --stat <base>...HEAD`, `git diff <base>...HEAD`

## 체크리스트

아래 체크리스트로 검증하라.

1. 아키텍처 준수: `ARCHITECTURE.md`에 정의된 디렉토리 구조를 따르고 있는가?
2. 기술 스택 준수: `ADR.md`에 정의된 기술 선택을 벗어나지 않았는가?
3. 테스트 존재: 새로운 기능이나 동작 변경에 대한 테스트가 작성되어 있는가?
4. CRITICAL 규칙: `AGENTS.md`의 CRITICAL 규칙을 위반하지 않았는가?
5. 빌드 가능: 관련 빌드, lint, typecheck, test 명령어가 에러 없이 통과하는가?
6. Harness 메타데이터: phase/step status가 유효하며, 완료/실패/차단 상태에 필요한 `summary`, `error_message`, `blocked_reason`이 들어 있는가?
7. 범위 통제: 요청 범위를 벗어난 리팩터링, 생성물 노이즈, 광범위한 재작성은 없는가?

## 출력 형식

코드 리뷰 관점으로 작성한다. 발견한 문제를 먼저 심각도 순으로 제시하고, 가능한 경우 파일과 라인을 함께 적는다. 스타일 취향보다 버그, 회귀, 누락된 테스트, 설계 위반을 우선한다.

체크리스트 표가 필요하면 아래 형식을 사용한다.

| 항목 | 결과 | 비고 |
| --- | --- | --- |
| 아키텍처 준수 | 통과/실패 | {상세} |
| 기술 스택 준수 | 통과/실패 | {상세} |
| 테스트 존재 | 통과/실패 | {상세} |
| CRITICAL 규칙 | 통과/실패 | {상세} |
| 빌드 가능 | 통과/실패 | {상세} |

위반 사항이 있으면 가장 작은 수정 방안을 구체적으로 제시하라. 문제가 없으면 문제가 없다고 명확히 말하고, 실행하지 못한 검증 커맨드나 남은 리스크를 덧붙인다.
