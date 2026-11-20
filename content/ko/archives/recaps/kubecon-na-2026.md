---
title: "KubeCon + CloudNativeCon North America 2026"
date: 2026-11-10
draft: false
event: "KubeCon + CloudNativeCon North America 2026"
city: "솔트레이크시티, 미국"
event_dates: "2026-11-09 ~ 11-12"
source_url: "https://www.linkedin.com/feed/update/urn:li:activity:7527587206685806592/"
summary: "오픈소스 LLM이 쿠버네티스 운영 시나리오 10개를 어디까지 해결하는지 측정한 결과를 발표하고 CNCF 앰버서더로 Project Pavilion 투어를 안내하고 Contribfest 2개를 도왔으며 Peer Group Mentoring 멘토로 참여했습니다."
ShowToc: false
cover:
    image: "/images/recaps/kubecon-na-2026/01-cover-pavilion-tour.jpg"
    alt: "Project Pavilion 투어에서 안내지를 나눠 드리는 모습"
    caption: "Project Pavilion 투어 안내 (사진: CNCF Flickr)"
    hidden: false
images:
    - /images/recaps/kubecon-na-2026/01-cover-pavilion-tour.jpg
---

11월 9일부터 12일까지 솔트레이크시티의 Salt Palace 컨벤션 센터에서 열린 KubeCon +
CloudNativeCon North America 2026에 다녀왔습니다. 이번에도 CNCF 트래블 펀딩 지원을 받아
참석했고 발표 외에도 CNCF 앰버서더(Ambassador)로서 행사 진행을 돕는 일을 여러 개 하게 되었습니다.

화요일 낮에는 Tsomorlig Khishigbold 님의 안내로
[Women's Community Gathering](https://kubecon-cloudnativecon-north-america-2026.sessionize.com/session/1336486)에
참석했습니다. 참석한 분들이 한 분씩 돌아가며 자기 이야기를 나누는 모임이었는데, 거기서 Niki
Manoledaki 님을 직접 만나 그동안 해 오신 일에 대한 이야기를 들을 수 있어서 매우 좋았습니다.

![Women's Community Gathering](/images/recaps/kubecon-na-2026/02-womens-gathering.jpg "Women's Community Gathering (사진: CNCF Flickr)")

발표 전에는
[SIG ContribEx(Special Interest Group Contributor Experience) 세션](https://kubecon-cloudnativecon-north-america-2026.sessionize.com/session/1289639)에
들렀습니다. 이 세션에서는 Kaslin Fields, Natalie Fisher, Priyanka Saggu 그리고 Nabarun Pal 님이
하위 프로젝트와 거버넌스가 어떻게 바뀌고 있는지를 정리해 주셔서 쿠버네티스 기여자 커뮤니티가
앞으로 어떤 방향으로 운영되는지 알 수 있었습니다.

![SIG ContribEx 세션](/images/recaps/kubecon-na-2026/03-contribex.jpg "SIG ContribEx 세션")

그리고 화요일 마지막 순서로 Operations + Performance 트랙에서 "How Far Are Open-Source LLMs
from Running Real Kubernetes Operations? A 10-Scenario Benchmark"를 발표했습니다. 이 발표에서는
오픈소스 LLM에 쿠버네티스 운영 시나리오 10개를 맡겨 보고 어디까지 해결하는지를 상용 모델과 비교해
측정한 결과를 다뤘고 [슬라이드](https://github.com/sysnet4admin/talks/tree/main/KubeCon/2026-NA)는
저장소에 올려뒀습니다. 발표가 끝나고 상용 모델로 앤트로픽(Anthropic)의 Claude는 왜 넣지 않았느냐는
질문을 받았는데, 솔직히 말씀드리면 측정할 당시 API 크레딧을 지원받을 수 있었던 것이 OpenAI의
Codex뿐이었고 다른 특별한 이유는 없었습니다(정말입니다...).

![발표 중](/images/recaps/kubecon-na-2026/04-my-talk.jpg "Operations + Performance 트랙 발표")

수요일 오전에는 Emily Chen 님과 Project Pavilion의
[TCG(Technical Community Group) Students 키오스크](https://kubecon-cloudnativecon-north-america-2026.sessionize.com/session/1373666)를
지키면서 대부분의 시간을 학생들과 이야기하며 보냈는데, 이번 행사에서 가장 즐거웠던 시간이었습니다.

![TCG Students 키오스크](/images/recaps/kubecon-na-2026/05-tcg-kiosk.jpg "Emily Chen 님과 있던 TCG Students 키오스크")

키오스크에 있는 동안 10시 40분부터 20분은 따로 빠져서
[Project Pavilion 투어](https://kubecon-cloudnativecon-north-america-2026.sessionize.com/session/1341037)를
안내했습니다. 투어 팻말을 들고 참가자들과 프로젝트 키오스크를 차례로 돌았는데, 같이 배정된 Rafael
Brito 님이 미리 다음 키오스크에 가서 투어를 받을 수 있는지 확인해 주셨습니다. Rafael 님이 없었다면
투어를 제대로 진행하지 못했을 것 같습니다.

![Project Pavilion 투어](/images/recaps/kubecon-na-2026/06-pavilion-tour.jpg "Project Pavilion 투어 안내")

같은 날 Pavilion에 들러 주신 YoungJoon Jeong 님과 Seol Heo 님께도 감사드리는데, 시차와 다른 일정
때문에 그분들의 발표를 듣지 못한 점은 다소 아쉬웠습니다.

오후에는 Contribfest 2개에 CNCF 앰버서더 도우미로 참여했습니다. Contribfest는 메인테이너와
참가자가 한 방에서 실제로 기여해 보는 세션인데, 도우미는 진행자가 아니라 메인테이너가 필요한 일을
돕고 참가자가 어려워하는 부분을 같이 해결하는 역할을 합니다. 먼저
[Kyverno Contribfest](https://kubecon-cloudnativecon-north-america-2026.sessionize.com/session/1294761)는
Jim Bugwadia, Cortney Nickerson 그리고 Saurabh Garg 님이 진행했고 약 40명이 참석했습니다.

![Kyverno Contribfest](/images/recaps/kubecon-na-2026/07-contribfest-kyverno.jpg "Kyverno Contribfest에서 참가자를 돕는 장면")

이어서 같은 방에서 열린
[Inspektor Gadget Contribfest](https://kubecon-cloudnativecon-north-america-2026.sessionize.com/session/1294763)를
도왔습니다. Qasim Sarfraz 님과 Michael Friese 님이 진행한 이 세션은 첫 가젯(gadget)을 공개하는 것이
목표였고 참가자 약 20명이 GitHub 템플릿으로 저장소를 만든 뒤 GitHub Actions로 top_syscall 가젯을
빌드하는 과정을 옆에서 도왔습니다.

![Inspektor Gadget Contribfest](/images/recaps/kubecon-na-2026/08-contribfest-gadget.jpg "Inspektor Gadget Contribfest")

Contribfest가 끝난 수요일 저녁에는 Samudra Weerasinghe 님과 Savi Saluwadana 님 덕분에 WSO2가
마련한 OpenChoreo 저녁 모임에 참석했습니다.

목요일 오후에는 KubeCon Japan 2026에 이어
[Peer Group Mentoring](https://kubecon-cloudnativecon-north-america-2026.sessionize.com/session/1339180)에
멘토로 참여했습니다. 제가 멘토로 앉은 테이블은 기술 트랙이었고 AI 에이전트 시대에 엔지니어에게 필요한
역할, 관심사가 서로 다른 SRE(Site Reliability Engineering) 팀과 일하는 방법 그리고 인프라의 모범
사례가 주제로 나왔습니다. 하지만 가장 많이 이야기한 주제는 커리어를 스스로 이끌면서 계속 성장하는
방법이었고 저에게도 매우 의미 있는 한 시간이었습니다.

![Peer Group Mentoring](/images/recaps/kubecon-na-2026/09-peer-mentoring.jpg "Peer Group Mentoring (사진: CNCF Flickr)")

선물도 여러 개 받아서 왔습니다. Mars Toktonaliev 님께 받은 텍사스 스티커와 쿠버네티스 모양 귀걸이,
Emily 님께 받은 샴푸 바와 판다 책갈피, LF Education의 턱스(Tux)와 쿠버네티스 핀, Priyanka 님께 받은
인도 수제 초콜릿 그리고 Women's Community Gathering에서 받은 양초까지 받았습니다.

![받은 선물들](/images/recaps/kubecon-na-2026/10-gifts.jpg "이번 행사에서 받은 선물들")

마지막으로 행사를 준비해 주신 Audra Montenegro 님과 CNCF 팀 그리고 같이 일한 앰버서더분들께
감사드립니다. 화요일 아침에는 앰버서더와 쿠버스트로넛(Kubestronaut)이 모여 아침 식사를 하는 Ambassador + Kubestronaut Breakfast가
있었는데, 이렇게 여러 나라에서 온 분들이 한자리에 모일 수 있는 것도 KubeCon이기 때문에 가능한
일입니다.

![CNCF 앰버서더와 쿠버스트로넛 단체 사진](/images/recaps/kubecon-na-2026/11-ambassadors-group.jpg "Ambassador + Kubestronaut Breakfast 단체 사진")

멘토링을 마친 목요일 오후에는 템플 스퀘어에 들렀고 다음 날 새벽 첫 트램을 타고 공항으로 가면서 이번
KubeCon도 끝이 났습니다.

![템플 스퀘어](/images/recaps/kubecon-na-2026/12-temple-square.jpg "솔트레이크시티 템플 스퀘어")
