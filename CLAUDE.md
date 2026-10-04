# kuberneteslab.dev: Claude 작업 컨텍스트

Hugo(PaperMod) 기반 블로그. ko/en 이중 언어, `content/{ko,en}/blog/`에 같은 슬러그로 쌍을 맞춘다.

## 이 저장소는 공개다 (2026-08-10 추가)

**비공개 저장소의 이름을 여기에 적지 않는다.** 파일 본문, README, 코드 주석뿐 아니라
**커밋 메시지 본문까지** 해당한다. 실제 사고가 두 번 다 커밋 메시지에서 났다.

- 초안 정본의 위치를 설명해야 하면 저장소 이름 없이 `<project>/_PUBLISHING/blog/`처럼
  상대 구조만 쓴다. "로컬 초안 저장소"까지가 허용 표현이다.
- 사용자명 `mz01-hj`와 로컬 절대 경로(`/Users/...`)도 같이 금지한다. 스크립트에는 `$HOME`을 쓴다.
- 커밋 전 확인: `git diff --cached`와 커밋 메시지 초안을 함께 훑는다.
- 푸시 후 검증. 0건이어야 한다. zsh는 `for p in $VAR`가 단어 분리를 하지 않으니
  여러 저장소를 돌 때는 배열(`PUBS=(...)`)로 써야 한다.

```bash
PRIV='<비공개 저장소 이름들>'
git grep -nIE "$PRIV" -- .                  # 현재 파일
git log --all -E --oneline -G"$PRIV"        # 커밋 내용 이력
git log --all -E --oneline --grep="$PRIV"   # 커밋 메시지
```

푸시된 뒤에는 파일 수정만으로 이력에서 안 사라진다. `git filter-repo` + 강제 푸시가 필요하다.
이 저장소의 이력은 2026-08-10에 한 번 재작성했다(비공개 저장소 이름 제거).

**사용자명 `mz01-hj`는 이 검증에서 제외한다 (2026-08-10 판정).** 이미 여러 공개 저장소의
이력과 포크 수백 개에 퍼져 있어 되돌릴 수 없다. 이력 재작성으로 얻는 것보다 그 포크와
클론을 깨뜨리는 비용이 크다고 판단했다. 앞으로 새로 넣지 않는 것으로만 관리하고,
검증의 0건 기준은 비공개 저장소 이름에만 적용한다.

## 한국어 문체 규칙 (2026-07-03 확정)

- **본문, 제목, front matter의 description과 summary 모두 합니다체**로 통일한다.
  한다체("확인했다", "갈렸다")를 섞지 않는다. description/summary는 블로그 목록에서
  여러 글의 카드가 나란히 보이는 자리라 혼용이 특히 눈에 띈다.
- 예외 하나: summary를 명사형으로 끝내는 것("...선택 가이드")은 허용한다(카드 요약 관례).
- em dash "—"는 쓰지 않는다. 한국어와 영문 본문 모두 해당한다(2026-08-07 확정).
  대체 방법은 표의 빈 칸이면 `N/A`, 목록 항목의 설명 구분이면 콜론, 본문 삽입구면
  콤마나 괄호로 바꾸거나 문장을 나눈다.
- 가운뎃점 "·"는 이 저장소에서 허용한다(2026-08-07 확정). 표 안 링크 구분자와
  소제목 나열에 이미 쓰이고 있어 그대로 둔다. 전역 규칙은 기본 금지이므로
  이 저장소만의 예외임에 유의한다.
- AI스러운 문장 4패턴(영어 직역체, 요약과 단언 반복, 평균 수렴 구조, 선언문 남용)을 피한다.
  상세 규칙은 전역 설정에서 불러온다.
- **블로그 글 본문과 About 소개 문단은 저자 명의 글이다.** 전역 규칙(어시스턴트
  레지스터)이 아니라 저자 문체 시트를 따른다. 쓰기 전에 `author-style` 스킬을 부른다.
  Archives의 표와 목록, README, 이 파일은 저자 명의 글이 아니므로 해당하지 않는다.

## 행사 참관 후기 (recaps, 2026-08-07 신설)

`content/{ko,en}/archives/recaps/`에 행사 단위로 쓴다. CNCF 트래블 펀딩 지원서에
인용할 수 있는 영구 URL을 만드는 것이 목적이라 LinkedIn 후기를 여기로 옮겨 적는다.

- `archives`는 branch bundle(`_index.md`)이고 recaps가 그 하위 섹션이다.
  상단 메뉴에는 넣지 않는다. 진입은 Archives 발표 이력 표의 `[후기]` 링크로 한다.
- `_index.md`에 `type: "recaps"`를 두면 `layouts/recaps/list.html`이 잡힌다.
  목록은 행사명과 일정만 최신순으로 보여준다.
- front matter는 `archetypes/recaps.md` 참조. `event`, `city`, `event_dates`,
  `source_url`(원문 링크)을 채운다. `date`는 행사 날짜로 두면 정렬이 곧 행사 최신순이다.
- tags와 categories는 넣지 않는다. 넣으면 `/tags/`에서 블로그 글과 섞인다.
- 사진은 `static/images/recaps/<슬러그>/`에 두고 ko/en이 공유한다. 대표 사진은
  `cover`로 걸고 `cover.caption`까지 채운다(공유 시 미리보기 카드에 쓰인다).

### 그림 캡션

`layouts/_default/_markup/render-image.html`이 마크다운 title 자리를 캡션으로 만들고
`[그림 N]` 번호를 자동으로 붙인다. 번호는 Hugo의 이미지 순번이라 사진을 넣고 빼도
손댈 필요가 없다. 라벨 문구는 `i18n/{ko,en}.yaml`의 `figure_label`에 있다.

```markdown
![대체 텍스트](/images/... "화면에 보이는 캡션")
```

title이 없으면 캡션도 번호도 안 붙고 그냥 `<img>`로 나간다. 그래서 기존 블로그 글은
영향을 받지 않는다. **설명 문단이 먼저 오고 그림이 뒤에 온다.** 예외를 두지 않는다.

## 발행 흐름

- 연구 글은 로컬 초안 저장소의 `<project>/_PUBLISHING/blog/`가 정본이고,
  이 저장소의 content 파일은 렌더링 사본이다. 수정은 정본에서 먼저 한다.
- 새 글은 `draft: true`로 넣고 로컬 확인(`hugo server -D`) 후 발행 시점에 false로 바꾼다.
- 발행 후 해당 연구 프로젝트의 README(EN/KO)와 Public Research 루트 README에 링크를 추가하고
  `/digest`로 반영한다.

## 노트 상자 (2026-09-07)

본문 안 용어 설명이나 [노트] 블록은 인용문(>)이 아니라 `note` 쇼트코드로 감싼다.
사방 테두리와 옅은 배경이 붙어 본문과 구분된다(`layouts/shortcodes/note.html`,
스타일은 `assets/css/extended/custom.css`의 `.note-box`).

```
{{</* note title="[노트] 이 글에서 쓰는 용어" */>}}
- 항목: 설명
{{</* /note */>}}
```

안에는 마크다운(목록, 코드체)을 그대로 쓸 수 있다. 인용문(>)은 인용에만 쓴다.

## promo 하위 사이트 (promo.kuberneteslab.dev, 2026-10-03)

리눅스 재단 자격증 할인 안내 사이트다. 도메인 때문에 저장소는 따로 두지만
(이 저장소와 같은 상위 폴더의 `../promo.kuberneteslab.dev`, 공개) 블로그의 하위 채널로 보고
**이 저장소에서 연 세션에서 함께 관리한다.** promo 폴더에서 세션을 따로 열지 않는다.

### 저장소와 배포
- 커밋, 검증, 푸시는 promo 저장소 안에서 한다. 블로그 커밋에 섞지 않는다.
- 위 "이 저장소는 공개다" 규칙이 그대로 적용된다. 검증 명령은 promo 저장소에서 돌리고
  결과를 본 뒤에 푸시한다. 검증과 푸시를 한 명령에 엮지 않는다.
- Cloudflare Pages 프로젝트 `promo-kuberneteslab-dev`. push 때와 매일 cron으로 다시
  배포하고, 끝난 프로모션은 재배포 때 내려간다.
- 배포 확인은 커밋 SHA로 실행을 찾아서 한다. 푸시 직후 목록 맨 위는 이전 실행일 수 있다.

### 데이터 흐름
- `data/promo/history.yaml`이 단일 출처다. 현재 배너, 비교 문장, 차트, 이력 표,
  `cta.json`이 모두 이 파일을 읽는다. 새 프로모션은 여기에만 추가한다.
  종료 시각은 미국 동부 23:59를 UTC로 적는다(예: `2026-09-23T03:59:00Z`).
- `/ko/cta.json`은 이 저장소의 글 끝 배너(`layouts/partials/promo_cta.html`)가 읽는다.
  형식을 바꾸면 배너도 같이 고친다. CORS는 `https://kuberneteslab.dev`만 허용하므로
  로컬에서는 기본값(상시 30%)이 보이는 게 정상이다.
- FAQ는 `data/faq.yaml` 한 곳에서 화면과 FAQPage 스키마를 같이 만든다.
- 제휴 링크는 `static/_redirects`의 `/go/*`.

### 배포에서 조심할 것
- 언어 하위 경로라 Hugo가 루트 404를 만들지 않는다. 워크플로가 `public/ko/404.html`을
  루트로 복사한다.
- "마지막 업데이트"는 배포 때 `content/`와 `data/`의 마지막 커밋 시각을
  `HUGO_PARAMS_LASTUPDATED`로 넘겨 채운다. 그래서 checkout에 `fetch-depth: 0`이 필요하다.
  날짜를 손으로 적지 않는다.
- front matter의 `date`, `lastmod`에는 시간대(`+09:00`)를 붙인다. 빠뜨리면 UTC로
  읽혀 미래 날짜가 되고 페이지가 경고 없이 빌드에서 빠진다.

### 피드와 메일
- 피드 `/ko/feed.xml`, `/en/feed.xml`은 `history.yaml`에서 시작 시각이 지난 항목만 담는다.
  끝난 항목은 다음 배포 때 제목 앞에 `[종료]`가 붙는다.
- 새 프로모션 확인은 Awin 메일과 리눅스 재단 공식 페이지로 한다. 메일은 Awin 메일만 조회한다.
- promo 감사 페이지(`content/*/thanks/`)는 "마지막 업데이트" 계산에서 빠진다.
  promo `content/`에 독자용이 아닌 페이지를 더하면 같은 제외를 넣는다.

### 내용 원칙
- 페이지 본문과 FAQ 답변은 저자 명의 글이다. `author-style` 절차를 탄다.
- 자격증 정책, 할인율, 통계는 공식 문서 원문과 대조한다. FAQ처럼 오래 걸어 두는
  정보는 서로 다른 모델 둘로 독립 검증을 돌린다(2026-09-28 CARE FAQ 선례).
- 수수료 구조는 "링크와 수수료에 대해서" 문단 이상으로 자세히 쓰지 않는다.
- 다른 할인 경로나 제휴 조건과 비교하는 문장을 넣지 않는다.
- 공식 페이지에 공개되지 않은 일정이나 할인 정보는 싣지 않는다.

## 뉴스레터 구독 (Kit, 2026-10-04)

- 고정 주소는 `kuberneteslab.dev/newsletter`(302로 `/ko/newsletter/`)다. QR
  (`static/images/qr/newsletter.svg`, `.png`)과 인쇄물에는 이 주소만 쓴다.
- 폼은 Kit 스크립트 없이 이메일만 Kit 폼 주소로 보내는 HTML 폼이다(`layouts/partials/newsletter.html`,
  promo에도 같은 이름의 파일). Kit 폼 번호는 두 저장소 `hugo.toml`의 `[params.newsletter]`에만 둔다.
- 폼 아래 동의 문구 두 줄은 Kit 폼에 적힌 문구와 같게 두고 숨기지 않는다. 바꿀 때는 Kit 폼과 두 사이트를 함께 고친다.
- 블로그 글에서는 작성자 띠 안에 넣는다(`layouts/partials/post_author.html`).
- Kit 폼의 가입 후 동작은 외부 주소 이동이고, 이동 주소는 `/ko/newsletter/thanks/`, `/en/newsletter/thanks/`다.
  감사 페이지 주소를 바꾸면 Kit 설정도 함께 바꾼다.
- 감사 페이지는 `nl_return` 쿠키(구독 버튼을 누른 페이지 주소, 30분)로 돌아가기 링크를 만들고,
  promo에서 왔으면 promo 감사 페이지로 넘긴다.
- Kit 계정, API 키, 발송 설정은 이 저장소 세션에서 다루지 않는다.
