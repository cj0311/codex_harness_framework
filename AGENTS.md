# 프로젝트: {프로젝트명}

이 파일은 Codex가 이 저장소에서 작업할 때 가장 먼저 읽는 프로젝트 규칙이다.
프로젝트별 확정 사항을 중괄호 자리표시자에 채워 넣고, 불확실한 내용은 추정하지 말고 사용자에게 확인한다.

## 기술 스택
- {프레임워크 (예: Next.js 15)}
- {언어 (예: TypeScript strict mode)}
- {스타일링 (예: Tailwind CSS)}

## 아키텍처 규칙
- CRITICAL: {절대 지켜야 할 규칙 1 (예: 모든 API 로직은 app/api/ 라우트 핸들러에서만 처리)}
- CRITICAL: {절대 지켜야 할 규칙 2 (예: 클라이언트 컴포넌트에서 직접 외부 API를 호출하지 말 것)}
- {일반 규칙 (예: 컴포넌트는 components/ 폴더에, 타입은 types/ 폴더에 분리)}

## 개발 프로세스
- CRITICAL: 새 기능 구현 시 반드시 테스트를 먼저 작성하고, 테스트가 통과하는 구현을 작성할 것 (TDD).
- 작업 범위는 현재 phase/step에 명시된 내용으로 제한한다.
- 관련 문서(`docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/ADR.md`, `docs/UI_GUIDE.md`)를 먼저 읽고 구현한다.
- 커밋 메시지는 conventional commits 형식을 따른다 (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).

## 명령어
```bash
npm run dev      # 개발 서버
npm run build    # 프로덕션 빌드
npm run lint     # ESLint
npm run test     # 테스트
```

프로젝트에 해당 명령이 없으면 `package.json` 또는 프로젝트 문서에 정의된 실제 검증 명령을 사용한다.
