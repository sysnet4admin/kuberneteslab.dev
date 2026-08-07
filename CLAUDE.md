# kuberneteslab.dev: Claude 작업 컨텍스트

Hugo(PaperMod) 기반 블로그. ko/en 이중 언어, `content/{ko,en}/blog/`에 같은 슬러그로 쌍을 맞춘다.

## 한국어 문체 규칙 (2026-07-03 확정)

- **본문, 제목, front matter의 description과 summary 모두 합니다체**로 통일한다.
  한다체("확인했다", "갈렸다")를 섞지 않는다. description/summary는 블로그 목록에서
  여러 글의 카드가 나란히 보이는 자리라 혼용이 특히 눈에 띈다.
- 예외 하나: summary를 명사형으로 끝내는 것("...선택 가이드")은 허용한다(카드 요약 관례).
- em dash "—"는 쓰지 않는다. 한국어와 영문 본문 모두 해당한다(2026-08-07 확정).
  대체 방법은 표의 빈 칸이면 `N/A`, 목록 항목의 설명 구분이면 콜론, 본문 삽입구면
  콤마나 괄호로 바꾸거나 문장을 나눈다.
- 가운뎃점 "·"는 이 저장소에서 허용한다(2026-08-07 확정). 표 안 링크 구분자와
  소제목 나열에 이미 쓰이고 있어 그대로 둔다. 전역 규칙(`ko-writing-style.md`)은
  금지로 되어 있으니 이 저장소만의 예외임에 유의한다.
- AI스러운 문장 4패턴(영어 직역체, 요약과 단언 반복, 평균 수렴 구조, 선언문 남용)을 피한다.
  상세는 <research-workspace> 루트 CLAUDE.md의 "글쓰기 금지" 섹션 참조.

## 발행 흐름

- 연구 글은 <research-workspace>의 `<project>/_PUBLISHING/blog/`가 초안 정본이고,
  이 리포의 content 파일은 렌더링 사본이다. 수정은 정본에서 먼저.
- 새 글은 `draft: true`로 넣고 로컬 확인(`hugo server -D`) 후 발행 시점에 false로 바꾼다.
- 발행 후 해당 연구 프로젝트의 README(EN/KO)와 Public Research 루트 README에 링크를 추가하고
  `/digest`로 반영한다.
