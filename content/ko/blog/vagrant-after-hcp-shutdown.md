---
title: "Vagrant Cloud가 종료되면 베이그런트는 어떻게 될까요?"
date: 2026-11-03
draft: true
tags: ["vagrant", "hcp-vagrant", "hashicorp", "virtualbox", "ruby", "macos", "license", "lima"]
categories: ["Tools"]
description: "HCP Vagrant(이전 이름 Vagrant Cloud)가 처음 공지한 일정보다 5개월 넘게 앞당겨진 2026년 12월 31일에 운영을 종료합니다. 베이그런트 CLI는 계속 사용할 수 있지만 2.4.9 이후 14개월 넘게 새 릴리스가 없고 macOS 26.7 이상에서 vagrant up이 실패하는 문제도 아직 해결되지 않았습니다. 11월 2일에 main 브랜치의 라이선스가 MIT로 돌아간 일까지 포함해 지금의 베이그런트 상태와 앞으로 지켜볼 부분을 정리했습니다."
summary: "Vagrant Cloud 종료 일정, 커뮤니티의 반응, 14개월 넘게 릴리스가 없는 베이그런트의 상태, macOS 포트 포워딩 문제, MIT 라이선스 복귀 그리고 베이그런트 대신 사용할 수 있는 도구를 정리했습니다."
ShowToc: true
TocOpen: true
cover:
    image: "/images/og/vagrant-after-hcp-shutdown.jpg"
    alt: "Vagrant Cloud가 종료되면 베이그런트는 어떻게 될까요?"
    hidden: true
---

**HCP Vagrant**가 2026년 12월 31일에 운영을 종료합니다. HCP Vagrant는 해시코프(HashiCorp)의 가상 머신(VM, Virtual Machine) 관리 도구인 베이그런트(Vagrant)가 **box**를 받아 오는 공개 서비스이고 box는 VM을 만들 때 사용하는 이미지 파일입니다. 2024년에 HCP(HashiCorp Cloud Platform)의 서비스가 되기 전까지는 Vagrant Cloud라는 이름으로 불렸기 때문에 지금도 이 이름이 더 익숙하신 분들이 많을 것 같습니다. Vagrantfile에 `config.vm.box = "sysnet4admin/Ubuntu-k8s"`처럼 이름만 적어도 box를 받을 수 있는 것은 베이그런트가 HCP Vagrant에서 그 이름을 찾아서 받아 오기 때문입니다.

저도 쿠버네티스와 앤서블(Ansible) 실습용 box 7개를 sysnet4admin 계정으로 배포하고 있어서 이번 종료에 맞춰 box를 옮기면서 관련 내용을 함께 조사했습니다. 그런데 조사하다 보니 HCP Vagrant가 없어지는 것과 함께 베이그런트 자체도 2025년 8월 이후로 새 릴리스가 없고 macOS 26.7 이상으로 올리면 `vagrant up`이 실패하는 문제도 있었는데, 국내에서는 이러한 내용을 정리한 글을 거의 찾을 수 없었습니다. 그래서 베이그런트를 사용해 오셨거나 앞으로도 계속 사용할지 고민하시는 분들께 도움이 될 것 같아 2편으로 나누어 정리했습니다.

결론부터 말씀드리면 베이그런트 CLI는 종료 뒤에도 그대로 남고 이미 내려받은 box도 계속 사용할 수 있기 때문에 베이그런트를 당장 사용할 수 없게 되는 것은 아닙니다. 다만 Vagrantfile에 box 이름만 적어 둔 경우에는 12월 31일 이후 그 box를 처음 받는 환경부터 실패하게 됩니다. 그리고 마지막 릴리스인 2.4.9 이후 새 릴리스가 나오지 않고 있어서 macOS 포트 포워딩 문제처럼 운영체제가 바뀌면서 발생한 문제가 언제 해결될지는 알 수 없는 상태입니다.

이 글에서는 베이그런트가 지금 어떤 상태이고 앞으로 어떻게 될지를 살펴보고 box를 어디로 옮기면 되는지는 다음 글에서 이야기하겠습니다. 글의 내용은 2026년 11월 3일을 기준으로 정리했습니다.

## 5개월 넘게 앞당겨진 종료 일정

우선 종료 일정부터 살펴보겠습니다. 해시코프는 2026년 8월 3일에 GitHub의 베이그런트 저장소 이슈(#13836)와 공식 포럼인 HashiCorp Discuss에 종료를 공지했는데, 그보다 며칠 앞선 7월 29일에 처음 작성된 종료 안내 문서에는 운영 종료가 2027년 6월 7일로 적혀 있었습니다. 그런데 8월 31일에 해시코프의 문서 저장소에 반영된 PR 2개(web-unified-docs#3256, #3257)로 일정이 단계마다 모두 앞당겨졌고 이를 표로 정리하면 다음과 같습니다.

| 단계 | 처음 공지한 일정 | 지금 일정 |
|---|---|---|
| 새 box 생성 중단 | 2026-12-14 | 2026-10-01 |
| 지원과 유지보수 종료 | 2027-03-15 | 2026-11-02 |
| 운영 종료, 모든 배포 정리 | 2027-06-07 | 2026-12-31 |

그 결과 운영 종료는 5개월 넘게 빨라졌고 이미 10월 1일부터는 새 box를 만드는 것뿐 아니라 기존 box에 신규 버전을 올리는 것도 거부되고 있습니다. 올리려고 하면 `resource creation is currently disabled` 오류가 나오는데 AlmaLinux를 비롯한 배포자들이 같은 오류를 보고했습니다.

일정과 함께 무엇이 남는지도 확인해 봐야 하는데, 종료 뒤에도 남는 것은 베이그런트 CLI와 GitHub의 소스 저장소입니다. 반면 HCP Vagrant에 올라가 있는 box 목록, box 파일 그리고 공개 box 검색은 없어지고 해시코프가 이를 대체할 공개 서비스를 발표하지 않았기 때문에 배포자가 다른 곳에 box를 올리고 그 호스팅 비용도 부담해야만 합니다. 대신 해시코프는 9월 11일에 Amazon S3, Azure Blob Storage 그리고 IBM Cloud Object Storage로 옮기는 안내 문서를 추가했습니다. 그리고 10월 28일에는 계정의 box를 모두 로컬 폴더로 내려받고 베이그런트가 읽는 `metadata.json`까지 만드는 내보내기 도구인 vagrant-registry-export를 공개했다고 알렸습니다. 다만 이 도구는 box를 내려받기만 하고 이때 만들어지는 `metadata.json`도 내려받은 머신의 로컬 경로를 가리키기 때문에 새 위치에 맞게 다시 만들어서 올리는 일은 배포자가 직접 해야 합니다.

해시코프는 전환 기간에 기존 주소를 넘겨 주는 정적 아카이브도 제공하겠다고 했지만 해시코프가 9월 17일에 올린 블로그 글과 종료 안내 문서에는 아직 예정으로 적혀 있고 11월 3일까지 공개되지 않았습니다. 종료 안내 문서 자체도 8월 31일 이후로 수정된 내용이 없습니다.

## 커뮤니티의 반응과 베이그런트 지원을 끝낸 프로젝트

일정이 이렇게 당겨졌으니 커뮤니티에서 반발이 컸을 것 같지만 실제로 찾아보니 반응 자체는 많지 않았습니다. HashiCorp Discuss의 공지에 달린 답글은 1개였고 GitHub 공지 이슈(#13836)의 댓글은 "F"(애도를 표하는 인터넷 밈)처럼 짧게 아쉬움을 남긴 것이 대부분이었습니다. Hacker News에도 관련 스레드가 3개 올라왔는데 가장 큰 것도 19점에 댓글 8개였습니다(Reddit은 r/vagrant 게시판만 확인했고 lobste.rs는 확인하지 못했습니다).

글 내용을 보면 Discuss의 유일한 답글은 box 파일을 각자 호스팅하고 목록만 함께 사용하는 공유 카탈로그를 만들어 달라는 요청이었는데 해시코프는 답하지 않았습니다. Hacker News에서는 공개 레지스트리가 없는 Docker와 같아서 이제 아무도 사용하지 않을 것이라는 댓글과 VM을 실행하는 오픈소스 도구인 Lima로 옮겼다는 댓글이 올라왔고 반대로 Vagrantfile만큼 같은 환경을 그대로 다시 만들 수 있는 대안은 없다는 의견도 있었습니다. Mastodon에서도 Lima로는 고정 IP 같은 기본적인 네트워크 설정을 할 수 없다거나 오픈소스 라이선스로 그대로 대체할 도구가 없다는 글이 보였습니다.

반응이 적었던 이유는 따로 확인하지 못했지만 2023년에 베이그런트의 라이선스가 **BSL**(Business Source License, 경쟁 제품으로 제공하는 것을 제한하는 소스 공개 라이선스)로 바뀐 뒤로 이미 베이그런트 지원을 줄이거나 끝낸 곳이 적지 않았던 것과도 관련이 있어 보입니다. 실제로 2024년부터 이렇게 한 프로젝트를 정리하면 다음과 같습니다.

| 프로젝트 | 시점 | 한 일 |
|---|---|---|
| Ubuntu | 2024-02 | 24.04에서 베이그런트 패키지를 빼고 24.04부터 베이그런트 box를 내지 않음 |
| Arch Linux | 2025-04 | 베이그런트 box 배포 중단 |
| Trellis(Roots) | 2025-10 | 베이그런트 지원을 끝내고 Lima로 전환 |
| Debian | 2025-11(testing에서 제외) | Debian 13에는 BSL 직전 커밋인 2.3.7만 두고 BSL 버전은 패키징하지 않음 |
| netlab | 2026-09 | vagrant-libvirt 프로바이더의 일몰을 발표하고 containerlab 중심으로 전환하는 중 |

곳마다 사정은 다른데 Ubuntu, Debian 그리고 netlab은 라이선스 변경을 그 배경 중 하나로 들었습니다. 이 중 netlab은 네트워크 실습 환경을 만드는 오픈소스 도구로, 만든 사람인 이반 페펠냐크(Ivan Pepelnjak)는 9월 14일 netlab 저장소(#3879)에서 vagrant-libvirt가 2023년 6월 이후 릴리스가 없어 사실상 버려진 상태(abandonware)라는 점 그리고 라이선스 변경과 HCP Vagrant 종료를 근거로 해시코프가 베이그런트에 관심을 두지 않는 것 같다는 점을 이유로 들었습니다. 그래서 컨테이너 기반으로 네트워크 장비를 실행하는 containerlab 중심으로 전환하고 있고 libvirt 프로바이더는 바로 지우지 않고 버그만 수정한다고 했습니다.

라이선스가 바뀐 뒤로 베이그런트를 오픈소스로 보지 않는 시각도 있는데, Lima를 만든 스다 아키히로(Akihiro Suda)는 2026년 1월 FOSDEM 발표에서 Lima를 소개하면서 슬라이드에 베이그런트를 "Proprietary"(독점 소프트웨어)로 적었습니다.

반면 box를 배포하던 쪽은 대부분 아직 아무 발표도 하지 않았습니다. 예를 들어 『Ansible for DevOps』의 저자인 제프 걸링(Jeff Geerling)의 geerlingguy 계정은 `geerlingguy/centos7` 1개만 해도 다운로드가 55만 9천 회입니다. 그런데 box 파일이 모두 HCP Vagrant에 있어서 이대로라면 12월 31일에 파일까지 함께 지워지게 됩니다. 다른 배포자들이 어떻게 대응하고 있는지는 다음 글에서 자세히 다루겠습니다.

## 14개월 넘게 릴리스가 없는 베이그런트

그렇다면 HCP Vagrant가 아닌 베이그런트 자체는 지금 어떤 상태일까요? 종료 안내 문서에 "The community edition in GitHub including the CLI will remain available"이라고 적혀 있는 것처럼 CLI는 종료 뒤에도 남습니다. 다만 여기서 "community edition"은 GitHub에 있는 CLI를 HCP Vagrant와 구분해 부르는 이름이고 관리를 커뮤니티에 넘긴다는 문장은 없습니다. 따로 공개된 로드맵도 없고 IBM이 해시코프 인수를 마치면서 낸 발표(2025년 2월 27일)에도 베이그런트는 나오지 않았습니다.

릴리스 기록을 보면 2025년 5월부터 8월까지 3개월 동안 2.4.6, 2.4.7, 2.4.8 그리고 2.4.9가 연달아 나왔지만 8월 21일에 나온 2.4.9를 마지막으로 14개월 넘게 새 릴리스가 없습니다. 그 뒤로는 나이틀리 빌드(nightly build, `2.4.10.dev+...`)만 있었고 이마저도 2026년 6월 1일이 마지막입니다.

이렇게 릴리스가 나오지 않는 동안 개발 활동도 크게 줄었습니다. 봇을 제외하고 사람이 직접 한 커밋은 2025년 3~5월에 월 44, 44, 31건으로 가장 많았다가 그 뒤로 계속 줄어들었고 2026년의 커밋은 24건인데 그중 코드를 수정한 커밋은 1건입니다. 그사이 2026년에 새로 열린 이슈는 25건인데 닫힌 이슈는 3건이고 지금 열려 있는 이슈는 676건, PR은 83건입니다. 2025년 9월 이후 병합된 PR 35건 중 30건은 해시코프 소속 1명이 처리했고 같은 기간에 main 브랜치에 반영된 코드 수정 중 봇이 아닌 사람이 한 것은 외부 기여 3건(Hyper-V 디스크, VirtualBox 스토리지 컨트롤러, Ubuntu 24.04 종료 시 멈춤)인데 모두 아직 릴리스되지 않았습니다. 릴리스할 때 OS별 설치 파일을 만드는 `hashicorp/vagrant-installers` 저장소도 사람이 한 마지막 커밋이 2025년 8월 4일입니다.

개발이 줄어든 것과 별도로 베이그런트를 설치할 수 있는 방법도 예전보다 적어졌습니다. Linux 배포판들이 BSL로 바뀐 2.4 버전을 패키징하지 않았기 때문인데, 설치 방식별로 받을 수 있는 버전을 2026년 11월 기준으로 정리하면 다음과 같습니다.

| 설치 방식 | 버전 | 상태 |
|---|---|---|
| Ubuntu 패키지 | 없음 | 24.04에서 빠짐(라이선스 변경과 유지보수 어려움) |
| Debian 패키지 | Debian 13에 2.3.7(BSL 직전 커밋) | BSL 버전은 패키징하지 않음 |
| Fedora 패키지 | 2.3.4 | 2.4.0 이상은 패키징하지 않음 |
| Arch Linux | AUR(Arch User Repository)에 2.4.9 | 공식 패키지 저장소에는 없음 |
| Homebrew, Chocolatey, winget, Scoop, Nix | 2.4.9 | 최신 릴리스 제공 |

배포판에 남아 있는 2.3 버전에는 box 아키텍처 지원(2.4.0), VirtualBox 7.1 지원(2.4.2) 그리고 7.2 지원(2.4.9)이 없기 때문에 지금의 VirtualBox와 함께 사용하려면 해시코프가 직접 내는 설치 파일이나 Homebrew, Chocolatey 같은 패키지 관리자로 2.4.9를 설치해야 합니다. 예외로 Debian의 개발 버전인 sid는 2.3 버전에 VirtualBox 7.1, 7.2 지원 부분만 따로 덧붙였습니다. 그리고 이 2.4.9 설치 파일도 macOS arm64용은 있지만 Linux와 Windows의 arm64용은 없습니다.

VirtualBox 지원도 새 베이그런트 릴리스가 나와야 추가됩니다. 앞에서 본 것처럼 VirtualBox 7.1은 베이그런트 2.4.2에서, 7.2는 2.4.9에서 지원되었기 때문에 VirtualBox의 다음 마이너나 메이저 버전도 그 버전을 지원하는 새 베이그런트 릴리스가 있어야 사용할 수 있습니다. 다른 하이퍼바이저용 플러그인은 상황이 제각각인데, netlab이 지원을 줄이기로 한 vagrant-libvirt는 2023년 6월 이후 릴리스가 없습니다. VMware Workstation Pro와 Fusion Pro는 2024년 11월부터 누구나 무료로 사용할 수 있게 되었지만 베이그런트용 VMware 플러그인은 2025년 4월이 마지막 릴리스이고 최신 Workstation을 인식하지 못한다는 이슈가 아직 열려 있습니다. 반면 vagrant-qemu(0.7.0, 10월 15일), vagrant_utm(0.2.0, 10월 14일) 그리고 vagrant-parallels(2.4.10, 10월 28일)처럼 지금도 릴리스가 이어지는 플러그인도 있습니다.

앤서블 프로비저너(provisioner, VM을 만든 뒤 설정을 자동으로 적용하는 기능)도 비슷한 상황입니다(이슈 #13733). 2.4.9는 앤서블을 실행할 때 `--inventory-file` 옵션을 넘기는데 ansible-core 2.19부터는 이 옵션이 2.23에서 없어진다는 경고가 나옵니다. 수정(#13740)은 이미 main 브랜치에 있지만 이것도 새 릴리스에 포함되어야 받을 수 있습니다.

그렇다고 해시코프 대신 베이그런트를 이어서 관리하는 오픈소스 포크를 찾을 수 있었던 것도 아닙니다. GitHub에서 찾아본 포크 4,526개 중 스타가 가장 많은 것도 14개였고 2023년 BSL 전환 직후 Hacker News에 소개되었던 Vagrunt는 지금 저장소 주소가 404를 반환합니다.

## macOS 26.7 이상에서 vagrant up이 실패하는 문제

macOS를 사용한다면 지금 바로 영향을 받을 수 있는 문제도 있습니다. 9월 17일에 열린 이슈 #13845에 따르면 macOS 26.7 이상에서는 베이그런트가 호스트의 모든 포트를 이미 사용 중인 것으로 인식해서 `vagrant up`이 "Vagrant cannot forward the specified ports on this VM" 오류를 내고 실패한다고 합니다. 포트 포워딩을 따로 설정하지 않은 Vagrantfile이라도 VirtualBox를 사용할 때는 SSH 접속에 사용할 포트 1개를 기본으로 포워딩하기 때문에 이 문제가 생기는 Mac에서는 VirtualBox를 사용하는 대부분의 Vagrantfile에서 `vagrant up`이 같은 단계에서 실패할 수 있습니다. 다만 이 부분은 문제가 생기는 Mac에서 직접 재현해 보지는 못했습니다.

이슈 댓글을 보면 영향 범위는 처음 보고보다 넓을 수도 있는데, Intel Mac에서 VirtualBox 7.2.20(macOS 26.7.1)을 사용할 때도 같은 문제가 생겼다는 보고가 있고 macOS 15.8.1(Sequoia)로 올린 뒤 겪었다는 댓글도 1건 있습니다.

이 문제는 macOS의 동작이 바뀐 것과 Ruby가 연결 결과를 확인하는 방식이 겹쳐서 발생한 것으로 보입니다. 베이그런트는 Ruby로 만들어졌고 포트가 비어 있는지 확인할 때 Ruby의 `Socket.tcp`로 그 포트에 연결을 시도해서 연결이 거부되면 비어 있는 포트로 판단합니다. 그런데 Ruby는 시간 제한을 둔 연결을 할 때 연결을 시작해 두고 끝나기를 기다린 뒤 `connect`를 한 번 더 호출해서 결과를 확인하는데, 이때 "이미 연결됨(EISCONN)"이 돌아오면 성공으로 간주합니다. macOS 27 베타부터 커널이 거부된 연결에도 EISCONN을 돌려주기 시작했고 같은 동작이 26.7에도 적용된 것 같은데, 그러면 실제로는 연결이 거부되었는데도 Ruby는 연결에 성공한 것으로 처리하게 됩니다. 즉 실제 결과인 연결 거부는 소켓의 `SO_ERROR`에 기록되어 있었지만 Ruby는 그 값을 읽지 않았습니다. 같은 macOS 변화 때문에 로봇 시뮬레이터인 Webots도 macOS 27 베타에서 모든 TCP 포트를 사용 중으로 잘못 판정한 사례가 있으니 베이그런트에만 생기는 문제는 아니라고 볼 수 있습니다.

그러면 Ruby 쪽에서 수정해 주기를 기다리면 될까요? Ruby는 이미 이 문제를 해결했습니다. 7월 31일에 macOS 27 베타에서 보고된 문제(Bug #22223)에 대한 변경을 8월 6일에 반영했는데, 연결이 끝나기를 기다린 뒤 `SO_ERROR`를 먼저 읽어서 오류가 있으면 그 오류를 내도록 7줄을 바꾸었고(ruby/ruby#18203) 이 변경은 3.4.11(9월 23일), 3.4.12(10월 23일) 그리고 4.0에 포함되었습니다. 하지만 베이그런트 2.4.9에 포함된 Ruby는 3.3.8입니다. Ruby 3.3은 2026년 4월 1일부터 보안 수정만 받는 단계이고 이 변경의 **백포트**(backport, 최신 버전의 변경 사항을 이전 버전에도 적용하는 작업) 항목은 "3.3: DONTNEED"(필요 없음)로 처리되었습니다. 3.3 자체도 2027년 3월 31일에 지원이 끝납니다.

따라서 Ruby 3.3에 이 변경이 적용되기를 기대하기는 어렵고 베이그런트가 Ruby 3.4.11 이상으로 새로 빌드한 릴리스를 내거나 같은 `SO_ERROR` 확인을 베이그런트 코드에 직접 넣은 PR #13842를 병합해서 새로 릴리스해야 해결됩니다. 정작 11월 3일 기준으로 #13845에는 7주째 분류 대기(`waiting-intake`) 라벨만 붙어 있고 메인테이너의 댓글도 없습니다. 외부 기여자가 낸 #13842에도 아직 리뷰가 없고 main 브랜치의 `is_port_open.rb`도 11월 2일에 라이선스 헤더만 바뀌었을 뿐 그대로입니다.

지금 사용하는 Mac이 영향을 받는지는 베이그런트에 포함된 Ruby로 닫힌 포트에 연결해 보면 알 수 있습니다.

```bash
/opt/vagrant/embedded/bin/ruby -e 'require "socket"; s=TCPServer.new("127.0.0.1",0); p=s.addr[1]; s.close; begin; Socket.tcp("127.0.0.1",p,connect_timeout:0.1); puts "AFFECTED"; rescue => e; puts "OK: #{e.class}"; end'
```

제 Mac(macOS 26.0.1)에서는 `OK: Errno::ECONNREFUSED`가 출력되어 영향이 없었습니다. 문제가 생기는 환경이라면 연결 거부가 오류로 나오지 않으므로 `AFFECTED`가 출력될 것으로 보이지만 그런 환경에서는 실행해 보지 못했습니다. 이 경우에는 `~/.vagrant.d/Vagrantfile`에 `is_port_open?`을 재정의하는 코드를 넣는 임시 방법이 이슈 댓글에 올라와 있고 여러 사람이 이 방법으로 해결했다고 합니다. 공식 수정이 아니므로 적용하기 전에 이슈의 댓글을 먼저 확인해 보시는 게 좋을 것 같습니다.

## MIT 라이선스로 돌아간 main 브랜치

이처럼 릴리스가 나오지 않는 가운데 이 글을 작성하던 중에 베이그런트 저장소에 변화가 하나 생겼습니다. UTC 기준 11월 2일 23시 4분(한국 시간 11월 3일 오전 8시 4분)에 "Revert license update"라는 PR #13858이 병합되면서 1,555개 파일의 라이선스 헤더가 BSL 1.1(BUSL-1.1)에서 MIT로 바뀌었고 이어서 병합된 #13859에서 저작권 표기가 "Copyright IBM Corp. 2026"으로 수정되었습니다. 직접 확인해 보니 main 브랜치의 `LICENSE` 파일도 지금은 MIT입니다. 베이그런트의 라이선스가 그동안 어떻게 바뀌었는지 표로 정리하면 다음과 같습니다.

| 시점 | 내용 |
|---|---|
| 2010년 ~ 2.3.7(2023-06-15) | MIT |
| 2023-08-10 | 해시코프가 BSL 1.1 도입을 발표 |
| 2.4.0(2023-10-16)부터 | BSL 1.1. 버전마다 공개 4년 뒤 MPL 2.0(Mozilla Public License 2.0)으로 바뀌도록 정해져 있어 2.4.0은 2027-10-16, 2.4.9는 2029-08-21 |
| 2026-03-11 | 라이선스를 부여하는 주체가 IBM으로 바뀜(#13791) |
| 2026-11-02 | main 브랜치를 MIT로 되돌림. 릴리스는 아직 없음 |

그렇다면 왜 지금 MIT로 되돌렸을까요? 그 이유를 알 수 있는 자료는 찾지 못했습니다. PR 본문에는 "Reverts the license update returning to the MIT license."라는 한 줄만 있고 hashicorp.com, HashiCorp Discuss 그리고 Hacker News에서도 관련 발표가 있는지 확인했지만 따로 나온 것은 없었습니다. 같은 해시코프 제품인 Terraform, Packer, Vault는 여전히 BSL이라 해시코프 전체의 라이선스 정책이 바뀐 것으로 보기도 어렵습니다.

이유가 무엇이든 이 변경으로 달라지는 부분도 있는데, 우선 main 브랜치가 MIT가 되면서 2.4 이후의 코드까지 MIT 라이선스로 포크할 수 있게 되었습니다. 또 Debian과 Fedora처럼 BSL 버전을 패키징하지 않겠다고 한 배포판도 다시 최신 코드를 패키징할 수 있게 될 것으로 보입니다. 하지만 바뀐 것은 main 브랜치뿐이라 2.4.9까지의 릴리스는 BSL로 배포된 그대로이고 MIT 라이선스로 배포되는 릴리스(이하 **MIT 릴리스**)가 언제 나올지도 해시코프는 따로 밝히지 않았습니다.

## 앞으로 지켜볼 4가지

그럼 베이그런트도 이대로 지원이 종료되는 걸까요? 비교해 볼 만한 사례로 쿠버네티스의 ingress-nginx가 있습니다. ingress-nginx의 경우 쿠버네티스 SIG(Special Interest Group) Network와 보안 대응 위원회(Security Response Committee)가 2025년 11월 11일에 지원 종료(retirement)를 발표했고 2026년 3월에 관리를 멈춘 뒤로는 릴리스, 버그 수정 그리고 보안 수정이 없을 것이라고 밝혔습니다. 실제로 저장소는 아카이브(archive) 처리되었고 마지막 릴리스는 2026년 3월 19일에 나온 Helm 차트입니다.

하지만 베이그런트는 지원 종료 발표도 저장소 아카이브 처리도 없었고 라이선스는 오히려 MIT로 되돌렸으므로 공식적으로 지원 종료가 정해진 것은 아닙니다. 다만 2.4.9 이후 새 릴리스가 없고 macOS 포트 포워딩 문제 같은 이슈가 분류조차 되지 않고 있어서 운영체제가 바뀌면서 생긴 문제의 수정이 제때 릴리스되지 않는 상태라고 볼 수 있습니다. 앞으로 베이그런트가 어떻게 될지는 다음 4가지를 지켜보면서 판단할 수 있을 것 같아 표로 정리해 보았습니다.

| 지켜볼 것 | 중요한 이유 |
|---|---|
| MIT 릴리스 | 2.4.9 이후 main 브랜치에만 있는 수정(앤서블 옵션, Hyper-V 디스크 등)도 함께 받을 수 있음 |
| #13845와 #13842의 처리 | Ruby 3.4.11 이상으로 빌드한 릴리스나 #13842를 포함한 릴리스가 나와야 macOS 포트 포워딩 문제가 공식적으로 해결됨 |
| 다음 VirtualBox 버전 지원 | 다음 마이너나 메이저 버전도 새 베이그런트 릴리스가 있어야 사용할 수 있음 |
| Ruby 3.3의 지원 종료(2027-03-31) | 그 뒤에는 Ruby 3.3 자체에 보안 수정이 나오지 않으므로 Ruby를 올린 베이그런트 릴리스가 필요함 |

해시코프가 관리를 중단하더라도 커뮤니티에서 포크해 이어 갈 수는 있지만 실제로는 쉽지 않을 것 같습니다. 베이그런트는 OS마다 Ruby를 포함한 설치 파일을 만들어 배포하기 때문에 포크하더라도 코드뿐 아니라 그 설치 파일 빌드까지 해야 합니다. 게다가 BSL 기간에도 꾸준히 관리된 포크는 찾지 못했습니다.

그럼 이제부터 베이그런트 대신 사용할 수 있는 도구에는 어떤 것들이 있고 각각 무엇이 부족한지 살펴보겠습니다.

## 베이그런트 대신 사용할 수 있는 도구

물론 이런 상황에서 다른 도구로 전환하는 쪽을 선택할 수도 있습니다. 어떤 도구로 옮길 수 있는지 판단하려면 먼저 베이그런트로 하던 일을 구분해 봐야 하는데, 크게 다음 5가지로 나누어 볼 수 있습니다.

- Windows, macOS 그리고 Linux에서 같은 Vagrantfile로 실습 환경을 만드는 것
- Vagrantfile 하나로 여러 대의 VM을 한 번에 만드는 것
- 호스트 전용 네트워크에서 VM에 고정 IP를 지정하는 것
- 미리 만든 이미지(box)를 다른 사람에게 배포하는 것
- Windows나 네트워크 장비 같은 다양한 게스트를 실행하는 것

범용 VM 도구로는 캐노니컬(Canonical)이 만든 Multipass, 앞에서 본 Lima, Linux에서 컨테이너와 VM을 관리하는 Incus, macOS용 가상화 앱인 UTM 그리고 macOS에서 Linux 환경을 실행하는 OrbStack(개인은 무료, 회사에서 사용하면 사용자당 월 8달러)이 있는데, 이 5개를 위의 기준으로 비교해 표로 정리하면 다음과 같습니다.

| 도구 | 호스트 OS | 한 파일로 여러 VM | 고정 IP | 이미지 배포 | Windows, 네트워크 장비 게스트 |
|---|---|---|---|---|---|
| 베이그런트 + VirtualBox | 모두 가능(Apple Silicon은 Arm 게스트만) | 가능 | 가능 | 가능(box) | 가능(x86 호스트) |
| Multipass | 모두 가능 | 안 됨 | 기본으로는 안 됨(Linux만 별도 안내) | 가능(URL로 지정, 1.16부터) | 안 됨 |
| Lima | Windows는 실험 단계 | 안 됨(VM마다 YAML 1개) | 안 됨(옵션 없음) | 가능(이미지 주소와 sha256) | Windows는 실험 단계 |
| Incus | 서버는 Linux만 | 별도 도구(OpenTofu, Incant)로 가능 | 가능 | 가능 | 가능 |
| UTM | macOS만 | 안 됨 | 직접 지정 | `.utm` 파일 | 가능(Apple Silicon의 x86은 에뮬레이션) |
| OrbStack | macOS 14 이상만 | 안 됨 | 안 됨(동적 IP) | 안 됨 | Linux만 |

이번에 비교한 도구 중에서 5가지를 모두 할 수 있는 조합은 베이그런트와 VirtualBox뿐이었습니다. 다만 이건 x86 호스트 기준이고 Apple Silicon Mac에서는 어느 도구를 사용하더라도 x86 게스트를 실행하기 어렵다는 제약이 있습니다. Apple Silicon에서는 VirtualBox도 Arm 게스트만 지원하고 x86용 Windows Server, NX-OSv, Cumulus VX처럼 x86용으로 만든 게스트는 다른 도구에서도 에뮬레이션을 거쳐야만 실행할 수 있습니다.

실제로 베이그런트 지원을 끝낸 프로젝트들도 한 도구로 모두 옮기기보다 용도에 맞는 도구를 선택했습니다. 앞에서 본 Trellis는 Lima로 전환했고 netlab은 containerlab 중심으로 옮기는 중입니다. 게다가 대안 도구들은 기능과 라이선스가 바뀌는 속도도 빠른 편입니다. 캐노니컬은 10월에 낸 Multipass 1.17에서 Windows 드라이버를 바꾸고 Blueprints 기능을 없앴으며 문서에는 1.18부터 VirtualBox 드라이버를 사용할 수 없다고 적혀 있습니다. Apple Silicon 전용 가상화 도구인 Tart는 저장소가 `openai/tart`로 옮겨졌는데 개발사는 4월 7일에 오픈AI(OpenAI) 소속이 되었다고 발표했고 6월부터 라이선스도 FSL(Functional Source License, 경쟁 제품만 막고 2년 뒤 Apache 2.0이 되는 라이선스) 계열인 FSL-1.1-ALv2로 바뀌었습니다.

용도별로 보면 쿠버네티스 실습은 kind나 minikube로 여러 노드로 된 클러스터를 쉽게 만들 수 있는데, kind를 Docker Desktop과 함께 사용하는 경우 일정 규모 이상의 회사(직원 250명 또는 매출 1천만 달러 기준)에서는 Docker Desktop이 유료입니다. 또 둘 다 kubeadm으로 노드를 클러스터에 추가하는 과정을 자동으로 처리하기 때문에 컨테이너 런타임을 설치하고 `kubeadm join`으로 노드를 조인하는 과정 자체를 익히기에는 맞지 않습니다. 그 과정을 다루지 않는다면 kind로 충분할 수 있고 실제로 매닝(Manning) 출판사의 『Kubernetes in Action』 2판은 kind를 사용합니다.

kubeadm 과정까지 다뤄야 한다면 Multipass나 Lima로 VM을 여러 대 만들고 직접 클러스터에 추가하는 방법이 있습니다. 예를 들어 코드클라우드(KodeKloud)는 CKA(Certified Kubernetes Administrator) 강의 저장소에서 Windows와 Intel Mac용으로 베이그런트와 VirtualBox를, Apple Silicon용으로 Multipass를 따로 안내하고 있습니다. 그런데 Multipass용 구성은 고정 IP를 지정할 수 없어서 DHCP로 받은 IP를 `/etc/hosts`에 적는 방식으로 처리합니다. 참고로 이 안내는 VirtualBox 7.1이 Apple Silicon을 지원하기 전인 2024년 3~4월에 만들어졌고 베이그런트용 구성은 amd64 box인 `ubuntu/jammy64`를 사용하기 때문에 지금도 Apple Silicon에서는 실행되지 않습니다.

네트워크 실습 환경은 netlab처럼 containerlab으로 전환하는 경우가 있습니다. 하지만 containerlab은 Linux와 Docker가 필요해서 Windows에서는 WSL2에서, macOS에서는 VM 안에서 실행해야 합니다. 또 NX-OSv, VyOS, Cumulus VX 같은 장비 이미지는 VM 기반이라 **중첩 가상화**(nested virtualization)가 필요한데, Mac에서는 M3 이상 칩과 macOS 15 이상에서만 지원하고 어떤 이미지가 동작하는지는 아직 정리되어 있지 않아 containerlab 문서에는 확인한 결과를 알려 달라고 적혀 있습니다.

설치 없이 브라우저에서 실습하는 방법도 있는데, Killercoda에서는 무료로 1시간짜리 세션을 사용할 수 있고 kubeadm으로 만든 2노드 환경도 제공합니다. 반면 비슷한 서비스였던 Play with Kubernetes는 2026년 3월 1일에 서비스를 종료했습니다.

이렇게 보면 용도마다 도구를 나누어 선택하면 옮길 수는 있지만 그만큼 실습 환경을 설명하는 문서와 스크립트도 도구마다 따로 관리해야 할 것으로 보입니다.

## 마치며

지금까지 HCP Vagrant 종료와 베이그런트의 상태를 살펴봤습니다. 정리하자면 HCP Vagrant는 12월 31일에 없어지지만 베이그런트 CLI는 남고 이미 받은 box도 계속 사용할 수 있습니다. 다만 베이그런트는 Ruby를 포함해 배포되기 때문에 macOS 포트 포워딩 문제처럼 새로 생기는 문제는 Ruby 쪽 수정만으로는 부족하고 베이그런트의 새 릴리스가 나와야 해결되는데, 2.4.9 이후 아직 새 릴리스가 없습니다. 11월 2일에 main 브랜치의 라이선스가 MIT로 돌아갔지만 그 이유를 밝힌 발표는 찾지 못했고 MIT 릴리스도 아직 없습니다. 저는 베이그런트로 하던 일을 그대로 대신할 도구를 찾을 때까지 당분간 베이그런트를 계속 사용하려고 합니다. 그동안 MIT 릴리스가 나오는지, macOS 포트 포워딩 문제가 해결되는지, VirtualBox의 다음 버전을 지원하는지 그리고 Ruby 3.3의 지원이 끝나는 2027년 3월 전에 Ruby를 올린 릴리스가 나오는지를 지켜보겠습니다.

저처럼 box를 배포하고 계시다면 베이그런트가 앞으로 어떻게 되든 12월 31일 전에 box를 옮겨야 하는데, 어디로 옮기면 되는지 그리고 다른 배포자들이 어떻게 대응하고 있는지는 다음 글에서 정리해 보겠습니다. 이 글이 베이그런트를 계속 사용할지 고민하시는 분들께 조금이나마 도움이 되었으면 좋겠습니다.

## 참고 자료

- HCP Vagrant 종료 안내: https://developer.hashicorp.com/hcp/docs/vagrant/hcp-vagrant-eol
- 해시코프 블로그, HCP Vagrant deprecation: https://www.hashicorp.com/en/blog/hcp-vagrant-deprecation-important-dates-and-migration-guidance
- 종료 공지 이슈 hashicorp/vagrant#13836: https://github.com/hashicorp/vagrant/issues/13836
- HashiCorp Discuss 공지: https://discuss.hashicorp.com/t/deprecation-of-hcp-vagrant/77619
- 일정을 앞당긴 PR web-unified-docs#3256: https://github.com/hashicorp/web-unified-docs/pull/3256
- 내보내기 도구 vagrant-registry-export: https://github.com/hashicorp/vagrant-registry-export
- MIT로 되돌린 PR hashicorp/vagrant#13858: https://github.com/hashicorp/vagrant/pull/13858
- macOS 포트 포워딩 이슈 hashicorp/vagrant#13845: https://github.com/hashicorp/vagrant/issues/13845
- 베이그런트 쪽 수정 PR hashicorp/vagrant#13842: https://github.com/hashicorp/vagrant/pull/13842
- Ruby Bug #22223: https://bugs.ruby-lang.org/issues/22223
- Ruby 수정 ruby/ruby#18203: https://github.com/ruby/ruby/pull/18203
- Ruby 브랜치별 지원 상태: https://www.ruby-lang.org/en/downloads/branches/
- ingress-nginx 지원 종료 발표: https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/
- netlab의 vagrant-libvirt 일몰 ipspace/netlab#3879: https://github.com/ipspace/netlab/issues/3879
- ipSpace, Sunsetting vagrant-libvirt: https://blog.ipspace.net/2026/09/sunsetting-vagrant-libvirt/
- Roots의 Trellis 베이그런트 지원 종료 글: https://roots.io/trellis-drops-vagrant-support-in-favor-of-lima/
- Ubuntu 문서의 베이그런트 안내: https://ubuntu.com/docs/public-images/public-images-explanation/vagrant/
- KodeKloud CKA 과정 kubeadm-clusters: https://github.com/kodekloudhub/certified-kubernetes-administrator-course/tree/master/kubeadm-clusters
- containerlab macOS: https://containerlab.dev/macos/
- Docker Desktop 라이선스: https://docs.docker.com/subscription/desktop-license/
- 이기하, HCP Vagrant 종료 관련 LinkedIn 글(2026-11-02): https://lnkd.in/p/gd_jB9Dd
