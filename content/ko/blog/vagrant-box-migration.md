---
title: "Vagrant Cloud가 종료되면 box는 어디로 옮겨야 할까요?"
date: 2026-11-05T08:25:00+09:00
draft: false
tags: ["vagrant", "hcp-vagrant", "box", "cloudflare-r2", "github-releases", "github-pages", "virtualbox"]
categories: ["Tools"]
description: "HCP Vagrant(이전 이름 Vagrant Cloud)가 2026년 12월 31일에 종료되면 box 이름만 적은 Vagrantfile은 box를 처음 받는 환경부터 실패합니다. 다른 프로젝트들의 대응 방식과 box를 올릴 수 있는 호스팅을 살펴보고 sysnet4admin box를 Cloudflare R2와 GitHub(릴리스, Pages)로 옮기면서 측정하고 비교한 장단점, 12월 31일 전에 확인할 것 그리고 옮긴 뒤에 관리할 것을 정리했습니다."
summary: "Vagrant Cloud 종료 뒤 Vagrantfile의 동작, 다른 프로젝트의 대응, box 호스팅 선택지, Cloudflare R2와 GitHub의 장단점 그리고 sysnet4admin box를 옮긴 구성과 옮긴 뒤의 점검 목록을 정리했습니다."
ShowToc: true
TocOpen: true
cover:
    image: "/images/og/vagrant-box-migration.jpg"
    alt: "Vagrant Cloud가 종료되면 box는 어디로 옮겨야 할까요?"
    hidden: true
---

[앞선 글](https://kuberneteslab.dev/ko/blog/vagrant-after-hcp-shutdown/)에서 **HCP Vagrant**가 2026년 12월 31일에 운영을 종료하고 베이그런트 자체도 2.4.9 이후 새 릴리스가 없는 상태라는 것을 살펴봤습니다. HCP Vagrant는 해시코프(HashiCorp)의 가상 머신(VM, Virtual Machine) 관리 도구인 베이그런트(Vagrant)가 **box**(VM을 만들 때 사용하는 이미지 파일)를 받아 오는 공개 서비스이고 2024년에 HCP(HashiCorp Cloud Platform)의 서비스가 되기 전까지는 Vagrant Cloud라는 이름으로 불렸습니다. 이 글에서는 종료에 맞춰 box를 어디로 옮기면 되는지를 다루겠습니다.

저도 쿠버네티스와 앤서블(Ansible) 실습용 box 7개를 sysnet4admin 계정으로 배포하고 있고 그중 `CentOS-k8s` 1개만 해도 누적 다운로드가 19,650회(11월 2일 기준)입니다. 제가 집필한 책과 강의의 실습 Vagrantfile도 이 box 이름을 사용하고 있어서 box를 옮기면서 다른 프로젝트들의 대응도 살펴봤는데, 국내에서는 개인 저장소 2곳이 GitHub 릴리스로 옮긴 것 말고는 공개된 대응을 찾지 못했습니다. 따라서 box를 배포하거나 사용하는 분들이 참고할 수 있도록 이번에 조사하고 측정한 내용을 정리했습니다.

결론부터 말씀드리면 box 파일과 **카탈로그**(`metadata.json`, box의 버전과 파일 주소를 적은 JSON)를 정적 호스팅에 올리고 Vagrantfile의 `config.vm.box_url`에 카탈로그 주소를 적는 방식이 가장 흔했고 저 역시 이 방식을 기본으로 정했습니다. 호스팅은 클라우드플레어(Cloudflare)의 객체 저장소 서비스인 Cloudflare R2를 주 저장소로 사용하고 GitHub 저장소의 릴리스에 파일을 올려 배포하는 GitHub 릴리스와 GitHub의 정적 웹사이트 호스팅인 GitHub Pages를 예비로 준비했습니다. R2와 GitHub 모두 지금 규모에서는 비용이 들지 않지만 각각 약점이 있어서 한 곳만으로는 부족하다고 판단했기 때문입니다. 글의 내용은 2026년 11월 3일을 기준으로 정리했습니다.

## 12월 31일 이후 Vagrantfile의 동작

우선 종료 뒤에 지금의 Vagrantfile이 어떻게 동작하는지부터 확인해 보겠습니다. 베이그런트 소스를 읽고 로컬 HTTP 서버에 카탈로그를 올린 뒤 기본 서버 주소(`https://vagrantcloud.com`)를 닫힌 포트로 바꿔 종료 뒤의 상황을 만들어 시험해 봤는데, Vagrantfile과 환경 변수를 어떻게 설정했는지 그리고 box를 이미 받았는지에 따라 결과가 나누어졌습니다. 이를 표로 정리하면 다음과 같습니다.

| 경우 | 12월 31일 이후 |
|---|---|
| Vagrantfile에 box 이름만 적었고 아직 받은 적이 없음 | 실패(`BoxAddShortNotFound`) |
| `box_url`에 새 카탈로그 주소를 지정 | 새 카탈로그에서 받고 SHA-256 확인과 `vagrant box outdated`도 동작 |
| Vagrantfile은 그대로 두고 `VAGRANT_SERVER_URL`에 새 주소를 지정 | 정적 호스팅만으로 동작(그 주소의 `/<계정>/<box>` 경로가 `application/json`으로 카탈로그를 응답할 때) |
| 이미 받은 box | 계속 사용할 수 있고 업데이트 확인이 실패해도 경고만 나옴 |

![box를 이미 받았는지, box_url이 있는지, VAGRANT_SERVER_URL을 설정했는지를 차례로 물어 12월 31일 이후의 결과를 찾는 흐름 그림](/images/vagrant-box-after-shutdown-ko.svg "12월 31일 이후 Vagrantfile의 동작을 확인하는 순서")

첫 번째 경우가 가장 크게 영향을 받는 이유는 베이그런트가 box 이름만 있으면 `{서버}/api/v2/vagrant/<이름>`과 `{서버}/<이름>`을 차례로 찾고 둘 다 실패하면 오류를 내기 때문입니다. 그래서 새 CI 러너, 새 노트북 그리고 다시 설치한 머신처럼 box를 처음 받는 환경부터 실패하게 됩니다. 반면 이미 box를 받아 둔 머신은 당장 문제가 없지만 `vagrant box update`는 처음 받을 때 저장한 주소(`~/.vagrant.d/boxes/<이름>/metadata_url`)를 계속 찾으므로 새 카탈로그에서 `vagrant box add`를 한 번 해야 그 주소가 바뀝니다.

`box_url`을 사용할 때 알아 두면 좋은 동작도 있습니다. 베이그런트는 그 주소에 HEAD 요청을 보내 응답의 Content-Type이 `application/json`이면 카탈로그로, 아니면 box 파일 하나로 판단하는데 리다이렉트를 따라간 마지막 응답이 기준입니다. 그리고 카탈로그의 `name`은 `config.vm.box`와 대소문자까지 같아야 하고 다르면 `BoxAddNameMismatch` 오류가 납니다. 또 `box_url`을 배열로 지정하면 앞의 주소가 실패할 때 다음 주소로 넘어가지만 이건 box 파일 주소일 때만 해당하고 카탈로그 주소를 2개 이상 지정하면 `BoxAddMetadataMultiURL` 오류가 발생합니다.

앞의 시험은 기본 서버 주소를 닫힌 포트로 바꿔 만든 상황이라 12월 31일 뒤에 실제 vagrantcloud.com에 연결이 실패할지, 404가 나올지 아니면 다른 페이지가 나올지는 확인하지 못했습니다. 다만 해시코프가 전환 기간에 기존 주소를 넘겨 주는 정적 아카이브를 제공하겠다고 했던 것도 11월 3일까지 공개되지 않았으므로 지금으로서는 box 이름만 적은 경우 처음 받는 환경에서 실패한다고 보는 것이 맞을 것 같습니다.

## 다른 프로젝트들의 대응

그렇다면 다른 프로젝트들은 어떻게 대응하고 있을까요? 해시코프가 대체할 레지스트리(HCP Vagrant처럼 box 이름으로 찾아서 받을 수 있게 해 주는 서비스)를 내지 않았기 때문에 각자 직접 호스팅하는 수밖에 없는데, box를 배포하던 곳들의 방식은 다음 4가지로 나누어 볼 수 있습니다.

| 방식 | 내용 | 사례 |
|---|---|---|
| 정적 호스팅과 `box_url` | box 파일과 카탈로그를 정적 호스팅에 올리고 Vagrantfile에 카탈로그 주소를 적음. 가장 흔한 방식 | Oracle Linux(처음부터 이 방식), 국내 개인 box 저장소 1곳 |
| `VAGRANT_SERVER_URL` 지정 | 사용자가 환경 변수로 주소를 지정하고 Vagrantfile에는 box 이름만 적음 | AlmaLinux |
| 직접 빌드 | 재배포할 수 없는 이미지는 빌드 스크립트만 제공하고 사용자가 직접 빌드 | 라이선스 제약이 있는 일부 장비 이미지, Windows 평가판 |
| box 배포 중단 | box를 더 이상 내지 않거나 베이그런트를 빼고 다른 방법으로 전환(일부는 종료 공지 전부터) | Arch Linux, Ubuntu(24.04부터), CI에서만 사용하던 프로젝트 |

사례 가운데 공식 배포판은 box 파일을 어디에 올렸는지에 따라 결과가 다릅니다. 배포판 서버에 파일을 두고 HCP Vagrant에는 주소만 등록한 곳은 12월 31일 뒤에도 파일이 남고 이름으로 찾을 수만 없게 되지만 HCP Vagrant에 파일을 올린 곳은 파일까지 지워집니다. 배포판별로 살펴보면 다음과 같습니다.

| 배포판 | box 파일 또는 카탈로그 위치 | 상태 |
|---|---|---|
| AlmaLinux | 자체 저장소(`vagrant.almalinux.org`) | 11월 2일에 카탈로그를 공지했고 `VAGRANT_SERVER_URL`과 `box_url` 모두 지원 |
| Oracle Linux | `oracle.github.io`의 JSON 카탈로그 | 처음부터 `box_url` 방식이라 그대로 사용 가능 |
| Ubuntu | `cloud-images.ubuntu.com` | 예전 box 파일은 남음. 24.04부터 box를 내지 않음 |
| CentOS | `cloud.centos.org` | 파일은 남음. 발표 없음 |
| Rocky Linux | `dl.rockylinux.org` | `rockylinux/9`의 VirtualBox amd64 항목은 없어진 9.6 경로를 가리켜 이미 404 |
| Fedora | 배포판 서버 | HCP Vagrant 등록은 41에서 멈춤. 44 box는 서버에 있지만 카탈로그는 없음 |
| Debian | HCP Vagrant | 최신 box(2026-05-19)는 libvirt용만 있고 메인테이너는 trixie64의 libvirt용 box를 관리할 계획이라고 밝힘 |
| Kali, FreeBSD | HCP Vagrant | 발표 없음. Kali 2026.3은 box가 없고 FreeBSD는 2024년의 13.4에서 멈춤 |

배포판이 아닌 곳에서 관리하는 box는 상황이 더 다양합니다. box 51개를 배포하는 gusztavvargadr는 box 파일을 이미 Cloudflare R2에 올렸고 정적 카탈로그를 `box_url`로 알리는 방식과 레지스트리 서버를 `VAGRANT_SERVER_URL`로 알리는 방식 중에서 선택하는 중인데 11월 초에 정하고 12월에 전환한다고 했습니다(#614). 반면 chef/bento는 GitLab 패키지 레지스트리와 GitLab Pages로 옮기자는 제안(#1699)에 메인테이너의 답이 없고 마지막 활동은 10월 6일입니다. 그리고 generic/* box를 내던 lavabit/robox에는 메인테이너가 오래 자리를 비워 상태를 알 수 없다는 댓글만 올라와 있습니다(#311). 앞선 글에서 이야기한 『Ansible for DevOps』의 저자 제프 걸링(Jeff Geerling)도 box를 어떻게 할지 아직 발표하지 않았고 box 파일은 모두 HCP Vagrant에 있는 상태입니다.

대응하면서 주의할 점으로 보고된 것도 있습니다. 버전을 낮춰 다시 내면(1.1.0 다음에 0.3.0) 이미 1.1.0을 받은 사용자는 계속 1.1.0을 사용하게 된다는 사례가 있었습니다. 그리고 9~10월에는 HCP Vagrant가 502 오류를 자주 냈다는 이슈(theforeman/foremanctl#886)도 올라와 있으니 종료 전이라도 box 받기가 실패할 수 있습니다. 또 `box_url`을 지정해도 레지스트리를 찾는다는 이슈(theforeman/foremanctl#903)도 있었는데, 그쪽 `box_url`은 카탈로그가 아니라 box 파일 주소였습니다. 반대로 카탈로그 주소를 지정하면 레지스트리를 찾지 않는다는 것은 소스와 시험으로 확인했습니다.

## 조사해 본 호스팅 선택지

그럼 box를 어디에 올릴 수 있을까요? 베이그런트가 별도 설정 없이 바로 받을 수 있는지를 기준으로 호스팅 서비스를 비교해서 표로 정리하면 다음과 같습니다.

| 호스팅 | 파일 1개 크기 | 비용 | 베이그런트가 바로 받는가 |
|---|---|---|---|
| GitHub 릴리스 | 2 GiB 미만, 릴리스당 자산(asset) 1,000개 | 무료, 대역폭 제한 없음 | box는 됨. 카탈로그는 안 됨(`application/octet-stream`) |
| GitHub Pages | 사이트 1 GB, 월 100 GB 권고 | 무료 | 카탈로그는 됨(`.json` 주소) |
| GitLab 일반 패키지 레지스트리 | 5 GB | 공개 프로젝트 무료 | chef/bento#1699의 정리이고 직접 확인하지 않음 |
| Cloudflare R2 | 한 번에 올리면 약 4.995 GiB | GB당 월 0.015달러, 10 GB 무료, 내려받기 무료 | 됨. 자체 도메인을 연결해서 사용 |
| Amazon S3 | N/A | 저장과 내려받기 요금 | 됨. 해시코프 가이드에는 box 파일을 바로 가리키는 예만 있음 |
| Internet Archive | 권장 최대 약 500 GB | 무료 | 됨. 영구 보존은 보장하지 않음 |
| Zenodo | 레코드당 50 GB, 파일 100개 | 무료 | box는 될 것으로 보이고 카탈로그는 시험하지 않음 |
| Hugging Face | 500 GB | 무료(best-effort) | 카탈로그는 안 됨(`text/plain`). 머신러닝 자료가 아니라 정책에도 맞지 않음 |
| ghcr.io, Docker Hub(OCI, Open Container Initiative) | ghcr.io는 레이어당 10 GB | 공개 무료 | 안 됨. 로그인 없는 요청에도 토큰 교환이 필요한데 베이그런트는 이를 하지 않음 |
| JFrog Artifactory | N/A | 유료 | 됨. 베이그런트 저장소 형식이 있음 |

이 표에서 베이그런트가 바로 받을 수 있는지는 대부분 카탈로그의 Content-Type에 따라 결정되었습니다. 앞에서 본 것처럼 베이그런트는 응답이 `application/json`일 때만 카탈로그로 읽는데, 실측해 보니 GitHub 릴리스는 자산을 `application/octet-stream`으로 응답해서 box 파일만 올릴 수 있었습니다. 그리고 GitHub Pages는 확장자 없는 파일을 `application/octet-stream`으로 응답해서 주소 끝에 `.json`이 붙어야 카탈로그로 읽혔습니다. 반면 Cloudflare R2나 Amazon S3 같은 객체 저장소는 올릴 때 객체마다 Content-Type을 지정하므로 `/sysnet4admin/Ubuntu-k8s`처럼 확장자 없는 주소에도 카탈로그를 둘 수 있고 이 덕분에 `VAGRANT_SERVER_URL` 방식도 정적 호스팅만으로 지원됩니다.

따라서 HCP Vagrant처럼 API를 제공하는 레지스트리 서버를 따로 운영할 필요는 없습니다. 같은 API를 제공하는 오픈소스 서버들도 있긴 하지만 대부분 규모가 작고 2015~2023년에 개발이 멈췄으며 최근에 나온 것도 참고용 수준입니다.

## Cloudflare R2와 GitHub의 장단점

이 중에서 저는 Cloudflare R2와 GitHub(릴리스와 Pages)를 선택했습니다. R2는 S3와 달리 내려받는 양에 요금을 받지 않아서 다운로드가 늘어도 전송 비용이 생기지 않고 GitHub는 무료이기 때문입니다. 그런데 실제로 2곳에 같은 box를 올리고 측정해 보니 항목마다 더 나은 쪽이 달랐습니다. 측정은 서울의 회사망(LG U+)과 미국의 GitHub Actions 러너 2대에서 했고 회사망은 약 120~140 Mbps가 상한이라 한국에서는 속도 차이를 구분할 수 없었습니다. 측정한 항목을 문서로 확인한 항목과 함께 표로 정리하면 다음과 같습니다.

| 항목 | Cloudflare R2 | GitHub 릴리스와 Pages | 더 나은 쪽 |
|---|---|---|---|
| 파일 1개 크기 | 한 번에 약 4.995 GiB, 나눠 올리면 약 4.995 TiB | 2 GiB 미만 | R2 |
| 비용 | 10 GB까지 무료, 넘으면 GB당 월 0.015달러, 내려받기 무료 | 무료 | 작은 규모에서는 같음 |
| 결제 수단 | R2 구독에는 결제 수단이 있어야 하고 결제가 실패하면 요청이 오류를 냄 | 필요 없음 | GitHub |
| 카탈로그 주소 | 확장자 없는 주소에 JSON을 지정할 수 있어 `VAGRANT_SERVER_URL`도 지원 | Pages 주소에 `.json`이 붙어야 하고 `VAGRANT_SERVER_URL`은 지원하지 않음 | R2 |
| 한국에서 응답한 거점(PoP, 실측) | 클라우드플레어 홍콩 거점. 캐시되지 않음 | GitHub가 사용하는 CDN인 Fastly의 서울 거점 캐시 | GitHub |
| 속도(실측) | 한국 회사망에서는 2곳이 같았음(약 14~15 MB/s). 미국에서 전체 파일 23~45 MB/s | 미국에서 52~82 MB/s | GitHub |
| 로그인 없는 요청 | 자체 도메인 요청에 알려진 제한 없음 | 2025년 5월부터 제한을 강화했고 로그인 없는 요청만 실패한 장애가 3번 있었음 | R2 |
| 다운로드 수 | GraphQL Analytics API로 객체별로 셀 수 있음(토큰 필요) | 자산마다 `download_count`를 API로 누구나 확인(세는 기준은 문서에 없음) | GitHub |
| 파일 고정 | 따로 확인하지 않음. 카탈로그의 SHA-256으로 확인 | 불변 릴리스(immutable releases)를 활성화하면 자산을 바꿀 수 없고 SHA-256을 API로 제공 | GitHub |
| 약관상 위험 | 큰 파일을 제한하는 조항의 예외에 R2가 이름으로 적혀 있지 않아 해석이 필요하고 신고가 오면 콘텐츠를 차단함 | 대역폭 과다 사용 조항, DMCA(Digital Millennium Copyright Act, 미국 디지털 밀레니엄 저작권법) 신고 시 저장소 전체를 비활성화할 수 있음 | 둘 다 있음 |
| SLA(Service Level Agreement, 서비스 수준 협약) | 월 99.9%지만 보상이 낸 요금 기준이라 무료 한도 안에서는 받을 것이 없음(무료 사용에도 적용되는지는 확인하지 못함) | 무료 플랜에는 SLA 없음 | 같음 |

표를 보면 의외로 미국에서는 GitHub 쪽이 빨랐습니다. 그 이유를 살펴보면 우선 클라우드플레어는 무료 플랜 트래픽을 여유가 있는 거점에서("wherever there is spare room") 처리한다고 밝히고 있는데, 저도 블로그 도메인에 무료 플랜을 사용하고 있어서 한국 요청이 홍콩 거점으로 간 것으로 보입니다. 게다가 클라우드플레어는 기본 설정에서 확장자를 보고 캐시할 파일을 정하는데 `.box`, `.json` 그리고 확장자 없는 파일은 기본 대상 목록에 없어서 캐시되지 않습니다. 캐시 규칙을 더해도 무료 플랜은 512 MB가 넘는 파일을 캐시하지 않기 때문에 box(0.7~1 GB)는 여전히 캐시 대상이 아닙니다. 그래서 요청마다 아시아·태평양 지역에 있는 버킷까지 가는 것으로 보이고 버킷에서 먼 미국에서는 GitHub보다 느렸습니다. 다만 미국 측정에 사용한 러너는 마이크로소프트(Microsoft) 망에 있고 GitHub 릴리스 자산은 Azure Blob Storage에 있어서 GitHub에 유리한 위치였을 수 있습니다. 그리고 한국에서는 LG U+ 회사망에서만 측정했고 KT나 SK브로드밴드 같은 다른 통신사망은 측정 범위에 넣지 못했습니다.

![서울, 피닉스, 보이드턴에서 Cloudflare R2와 GitHub로 box를 받을 때 거친 거점과 버킷 그리고 받은 속도를 한 줄씩 함께 놓고 비교한 그림](/images/vagrant-box-path-speed-ko.svg "측정 지점별로 box 요청이 지나간 길과 받은 속도")

속도가 R2의 약점이었다면 GitHub는 로그인 없는 요청을 처리하는 방식에 약점이 있었습니다. 베이그런트는 항상 로그인 없이 box를 받는데, GitHub는 2025년 5월 8일에 로그인 없는 요청의 제한을 강화하면서 제한 수치를 밝히지 않았고 릴리스나 Pages가 포함되는지도 적지 않았습니다. 이와 별개로 UTC 기준 2025년 12월 22일(31분, GitHub Actions 안의 요청), 2026년 6월 8일(약 2시간) 그리고 8월 12~13일(합쳐 약 7.7시간)에는 로그인 없는 요청만 실패한 장애가 있었고 뒤의 2번에 대해서는 GitHub가 로그인한 사용자는 영향을 받지 않았다고 밝혔습니다. 강화된 제한이 강의실처럼 수강생 수십 명이 공인 IP 1개를 함께 사용하면서 같은 box를 동시에 받는 환경에 어떻게 적용되는지는 확인하지 못했습니다. 하지만 한 IP에서 HEAD 요청 100개를 10개씩 동시에 보낸 시험에서는 릴리스, Pages, R2 카탈로그 그리고 R2 box 주소 4개 모두 차단되지 않았습니다.

이 밖에 GitHub 릴리스에서 box를 받으면 서명된 URL(signed URL)로 리다이렉트되는데, 이번 box 파일들은 그 URL이 1시간 동안 유효했습니다. 베이그런트는 전송이 끊긴 뒤 다시 실행하면 원래 주소로 다시 요청해서 이어 받으므로(소스 기준) 새 URL을 받아 이어 받을 수 있습니다. 다만 한 번의 전송이 60분을 넘으면 끊기는지는 시험하지 않았습니다. 회선 1개를 여러 명이 공유하는 곳에서는 이 경우가 생길 수 있는데, 1 GB를 60분 안에 받으려면 약 2.2 Mbps가 필요하고 100 Mbps 회선을 45명이 함께 사용하면 1명당 속도가 그 정도가 됩니다. 또 2025년 4월 말쯤부터 서명된 URL의 호스트가 `release-assets.githubusercontent.com`으로 바뀌었다는 보고가 있고 허용 목록에 있는 주소로만 접속할 수 있는 회사망에서 다운로드가 실패한 사례도 있었습니다. 그래서 학교나 회사망에서 box를 받지 못한다면 이 호스트 변경이 원인일 수도 있습니다.

이렇게 보면 어느 한쪽이 모든 면에서 낫지는 않아서 상황별로 선택하는 편이 좋을 것 같습니다.

- 결제 수단 없이 작게 시작한다면 GitHub 릴리스(box 파일)와 GitHub Pages(카탈로그)
- 2 GiB가 넘는 box가 있다면 R2나 S3 같은 객체 저장소
- 인쇄된 책처럼 Vagrantfile을 수정할 수 없어서 `VAGRANT_SERVER_URL`을 안내해야 하거나 짧은 주소가 필요하다면 자체 도메인을 연결한 R2
- 강의실처럼 한 공인 IP에서 많은 사람이 받는다면 로그인 없는 요청의 제한 수치가 공개되지 않은 GitHub보다는 R2

## sysnet4admin box를 옮긴 구성

그래서 sysnet4admin box는 R2와 GitHub 2곳에 함께 올리고 평소에는 R2에서, R2에 문제가 생기면 GitHub에서 받도록 구성했습니다. 사용자가 접속하는 주소는 `box.kuberneteslab.dev` 하나이고 장애가 나면 미리 만들어 비활성화해 둔 클라우드플레어의 전환용 리다이렉트 규칙을 활성화해서 요청을 GitHub로 넘깁니다. 이 구성을 그림으로 나타내면 다음과 같습니다.

![사용자의 요청이 box.kuberneteslab.dev를 거쳐 평소에는 Cloudflare R2로, 전환했을 때는 GitHub Pages와 릴리스로 가고 클라우드플레어 장애 시에는 Pages 주소로 직접 가는 구성 그림](/images/vagrant-box-topology-ko.svg "box.kuberneteslab.dev를 거쳐 백엔드로 나누어지는 구성")

따라서 Vagrantfile에는 다음과 같이 한 줄을 더하면 되고 인쇄된 책처럼 Vagrantfile을 수정할 수 없는 경우에는 `VAGRANT_SERVER_URL=https://box.kuberneteslab.dev`를 설정하면 됩니다.

```ruby
config.vm.box     = "sysnet4admin/Ubuntu-k8s"
config.vm.box_url = "https://box.kuberneteslab.dev/sysnet4admin/Ubuntu-k8s"
```

처음에는 책에 넣을 주소가 도메인 갱신이나 클라우드플레어 계정에 영향을 받지 않도록 카탈로그를 GitHub Pages에 올리고 그 주소를 책에 넣는 방법을 생각했습니다. 하지만 자체 도메인을 접속 주소로 사용하면 확장자 없는 주소에 카탈로그를 둘 수 있어서 `VAGRANT_SERVER_URL`도 지원할 수 있습니다. 또 베이그런트는 리다이렉트된 최종 주소가 아니라 처음 주소를 저장하므로 나중에 리다이렉트 대상을 바꿔도 이미 box를 받은 사용자의 업데이트 확인은 바뀐 대상으로 연결됩니다. 대신 `kuberneteslab.dev` 도메인을 책이 판매되는 동안 계속 갱신하고 클라우드플레어에서 관리해야 하는데, 저는 이 부담보다 이 2가지 장점이 더 크다고 판단했습니다.

R2에서 GitHub로 넘기는 작업은 클라우드플레어의 서버리스 실행 환경인 Cloudflare Workers로 자동화할 수도 있지만 관리할 코드가 생기기 때문에 규칙을 직접 활성화하는 방식을 선택했습니다. 시험해 보니 규칙을 활성화하고 20초 안에 전환이 반영되었습니다.

box는 사용하는 곳과 빈도에 따라 3개 그룹으로 나누어 옮겼고 이를 표로 정리하면 다음과 같습니다.

| 그룹 | box | R2 | GitHub |
|---|---|---|---|
| 그룹 1(자주 사용) | `Ubuntu-k8s` 1.0.0(amd64, arm64) | 올림 | 사본을 올림 |
| 그룹 2(가끔 사용) | `CentOS-k8s` 0.8.0 | 카탈로그만 | 올림 |
| 그룹 3(사용처가 적음) | 네트워크 장비 box(`nxosv_v7`, `nxosv_v9`, `VyOS`) | 카탈로그만 | 올림 |

`CentOS-k8s`는 다운로드가 가장 많은 box지만 강의에서 사용하는 box를 Ubuntu로 바꾸어서 그룹 2로 분류했고 네트워크 장비 box는 주로 오래된 앤서블 책과 강의에서 사용하기 때문에 그룹 3에 넣었습니다. 이에 따라 R2에는 그룹 1의 파일만 두고 그룹 2와 3의 파일은 GitHub에만 올렸습니다. 반면 `Rocky8`은 제 책과 강의에서 사용하는 곳이 없어서 옮기지 않았습니다. 기존 Windows box인 `Windows2016`은 Windows Server 2019 평가판으로 새로 만든 `Windows2019` box로 대체했는데, 새 box는 GitHub 릴리스로 배포했고 앤서블 강의와 책의 실습도 이 box에 맞췄습니다. 또 box마다 최신 버전 1개만 옮기고 수정할 일이 생기면 기존 버전을 덮어쓰지 않고 1.0.0 다음에 1.0.1처럼 신규 버전으로 내기로 했습니다. 다만 `nxosv_v9`은 최신 버전인 9.3.5가 3.51 GiB로 GitHub 릴리스의 파일 크기 제한(2 GiB 미만)을 넘기 때문에 그 대신 9.2.3을 올렸습니다.

GitHub 쪽은 `vg-box` 조직 아래에 저장소 2개를 만들었습니다. `vg-box/k8s`에는 그룹 1 box의 사본, 그룹 2 box 그리고 전환용 카탈로그(Pages)를 올리고 `vg-box/ansible`에는 그룹 3 box와 `Windows2019`를 올렸는데, `vg-box/ansible`에 문제가 생겨도 `vg-box/k8s`와 R2는 영향을 받지 않도록 나눈 것입니다. 릴리스는 box 버전마다 1개를 만들고 태그는 `<box>-<version>`으로 정했으며 같은 릴리스에 `SHA256SUMS`를 함께 올렸습니다. R2 쪽은 지금 올린 box 파일이 그룹 1의 2개뿐이고 합쳐서 1.92 GB라 무료 한도 안에 있어서 비용이 들지 않고 있습니다.

그래도 문제가 생겼을 때 대체할 곳이 없어서 box를 받을 수 없는 경우가 2가지 있습니다.

**첫 번째는 클라우드플레어 프록시가 멈추는 경우**입니다. 접속 주소의 도메인은 클라우드플레어 1곳에만 의존하고 리다이렉트 규칙도 같은 프록시에서 동작하므로 이때는 GitHub로 넘길 수 없을 것으로 봅니다. 이 경우에 대비해 GitHub Pages 주소(`vg-box.github.io/k8s/...json`)로도 직접 받을 수 있게 해 두었습니다.

**두 번째는 GitHub에 문제가 생기는 경우**입니다. 그룹 2와 3의 box 그리고 `Windows2019`는 파일이 GitHub에만 있어서 이때는 받을 수 없습니다.

## 12월 31일 전에 확인할 것

지금까지 이야기한 내용을 box를 배포하는 쪽과 사용하는 쪽으로 나누어 정리해 보겠습니다.

### box를 배포하는 경우

- 카탈로그를 만들고 `box_url`에는 box 파일이 아니라 카탈로그 주소를 적는 게 좋겠습니다. box 파일 주소를 바로 적으면 버전 관리와 `vagrant box update`를 사용할 수 없기 때문입니다.
- 카탈로그에는 SHA-256 체크섬을 적습니다. 체크섬이 있으면 받은 파일이 원본과 다를 때 받기가 실패하므로 파일이 바뀐 것을 알 수 있는데, 사실 제가 HCP Vagrant에 올렸던 box 7개의 파일 42개에도 체크섬은 하나도 등록되어 있지 않았습니다.
- box 이름은 기존 `<계정>/<box>` 그대로 두고 카탈로그의 `name`도 대소문자까지 맞춥니다. 그래야 이미 box를 받은 사용자도 같은 이름으로 이어서 사용할 수 있습니다.
- 카탈로그는 `application/json`으로 응답하게 합니다. `VAGRANT_SERVER_URL`도 지원하려면 카탈로그를 확장자 없는 `/<계정>/<box>` 경로에 올립니다.
- 수정한 box는 버전을 낮추지 말고 1.0.1처럼 신규 버전으로 냅니다.
- 해시코프가 공개한 내보내기 도구인 vagrant-registry-export가 만든 `metadata.json`은 내려받은 머신의 로컬 경로를 가리키므로 새 주소에 맞게 다시 만들어야 합니다.
- R2의 기본 주소(`r2.dev`)는 속도 제한이 있는 개발용이라 자체 도메인을 연결해서 사용합니다.
- box는 Git 저장소나 Git LFS(Large File Storage)에 올리지 않습니다. GitHub는 100 MiB가 넘는 파일을 저장소에 올릴 수 없게 하고 GitHub의 LFS 무료 플랜은 대역폭이 월 10 GiB라 box를 몇 번만 내려받아도 한도를 넘습니다.
- R2에 큰 파일을 올릴 때는 AWS CLI를 사용하시면 됩니다. 클라우드플레어의 명령줄 도구인 wrangler는 파일 1개를 300 MiB까지만 지원합니다.
- 종료 전이라도 HCP Vagrant가 502를 낼 수 있으니 기존 box는 가능한 한 빨리 내려받아 두시기 바랍니다.
- 다 옮기고 나면 기본 서버 주소가 응답하지 않는 상태에서 `vagrant box add`를 시험해 보는 게 좋을 것 같습니다. 저는 기본 서버 주소를 닫힌 포트로 바꿔서 종료 뒤의 상황을 확인했습니다.

### box를 사용하는 경우

- 사용하는 box의 버전을 `config.vm.box_version`으로 고정하고 지금 받아 둡니다.
- 받은 파일은 `metadata.json`을 만들어 `box_url`로 지정하거나 `vagrant box add ./metadata.json`으로 추가할 수 있고 `box_url`을 사용할 때는 그 카탈로그에 체크섬도 함께 적습니다.
- 배포자가 새 카탈로그를 안내했다면 새 카탈로그에서 `vagrant box add`를 한 번 해서 업데이트 확인 주소를 바꿉니다.
- 재배포할 수 없는 이미지는 배포자가 제공하는 빌드 스크립트와 해시코프의 이미지 빌드 도구인 Packer로 직접 빌드해야 합니다.

## 옮기고 나서 관리할 것

box를 옮긴 뒤에도 배포자가 계속 챙겨야 하는 일이 있습니다. 대부분 HCP Vagrant를 사용할 때는 해시코프가 대신 해 주던 일이지만 이제는 배포자가 모두 직접 해야만 합니다.

- 도메인 갱신: 접속 주소가 `kuberneteslab.dev` 아래에 있으므로 앞으로 책에 넣을 주소로 계속 box를 받을 수 있게 하려면 도메인을 만료 전에 계속 갱신해야 합니다.
- 결제 수단: R2는 결제가 실패하면 버킷에 접근할 수 없고 요청이 오류를 내며 30일 안에 결제 수단을 바꾸지 않으면 데이터가 지워질 수 있습니다. 그래서 등록한 카드의 유효기간이 지나면 사용자가 box를 받지 못할 수 있고 도메인 갱신 결제도 함께 확인해야 합니다.
- 전환 수단: 리다이렉트 규칙을 활성화하려면 클라우드플레어 대시보드나 API가 필요한데 2025년 9월 12일 장애 때는 대시보드와 API가 모두 멈췄고 11월 18일 장애 때는 대시보드도 영향을 받았습니다. 그래서 클라우드플레어 자체에 문제가 생기면 규칙 대신 GitHub Pages 주소로 직접 받는 방법을 안내해야 합니다.
- 보안 설정: 베이그런트는 curl로 받기 때문에 브라우저 확인 화면을 통과하지 못합니다. 그래서 클라우드플레어의 봇 차단 기능인 Bot Fight Mode나 I'm Under Attack 모드를 활성화하면 `vagrant box add`가 실패할 수 있으므로 보안 설정을 바꾼 뒤에는 box를 다시 받아 보는 게 좋겠습니다.
- 다운로드 수: GitHub에서는 `download_count`로 바로 확인할 수 있지만 시험해 보니 GET 요청도 모두 세지는 않았고 세는 기준도 문서에 없어서 대략적인 값으로만 참고합니다. 그런데 평소에는 R2가 box를 응답하기 때문에 R2 쪽 수치는 GraphQL Analytics API로 따로 집계합니다.

이와 별개로 베이그런트 자체의 변화도 계속 확인합니다. [앞선 글](https://kuberneteslab.dev/ko/blog/vagrant-after-hcp-shutdown/)에서 정리한 MIT 라이선스로 배포되는 릴리스, macOS 26.7 이상에서 `vagrant up`이 실패하는 문제의 처리, VirtualBox 다음 버전 지원 그리고 Ruby 3.3의 지원 종료 전에 Ruby를 올린 릴리스가 나오는지가 여기에 해당합니다.

## 마치며

지금까지 HCP Vagrant 종료에 맞춰 box를 어디로 옮기면 되는지 살펴봤습니다. 정리하자면 box 이름만 적은 Vagrantfile은 12월 31일 이후 box를 처음 받는 환경부터 실패하므로 box 파일과 카탈로그를 직접 호스팅하고 `box_url`이나 `VAGRANT_SERVER_URL`로 그 주소를 알려야 합니다. 호스팅은 Cloudflare R2와 GitHub 모두 지금 규모에서는 비용 없이 운영할 수 있지만 R2는 결제 수단을 관리해야 하고 캐시되지 않아 버킷에서 먼 곳에서는 느리다는 점이, GitHub는 파일 크기 제한과 로그인 없는 요청의 장애가 약점이라 저는 둘을 함께 사용하는 쪽을 선택했습니다.

해시코프가 약속한 정적 아카이브는 11월 3일까지 공개되지 않았으므로 그것을 기다리지 않고 옮기시는 편이 좋을 것 같습니다. 이 글이 box를 배포하거나 사용하시는 분들께 조금이나마 도움이 되었으면 좋겠습니다.

## 참고 자료

- HCP Vagrant 종료와 베이그런트의 상태를 다룬 앞선 글: https://kuberneteslab.dev/ko/blog/vagrant-after-hcp-shutdown/
- HCP Vagrant 종료 안내: https://developer.hashicorp.com/hcp/docs/vagrant/hcp-vagrant-eol
- 해시코프 저장소 이전 가이드(Amazon S3): https://developer.hashicorp.com/vagrant/vagrant-cloud/hcp-vagrant/storage-providers/aws
- 내보내기 도구 vagrant-registry-export: https://github.com/hashicorp/vagrant-registry-export
- AlmaLinux 베이그런트 카탈로그 안내: https://almalinux.org/blog/2026-11-02-vagrant-catalog/
- gusztavvargadr/packer#614: https://github.com/gusztavvargadr/packer/issues/614
- chef/bento#1699: https://github.com/chef/bento/issues/1699
- lavabit/robox#311: https://github.com/lavabit/robox/issues/311
- theforeman/foremanctl#886: https://github.com/theforeman/foremanctl/issues/886
- theforeman/foremanctl#903: https://github.com/theforeman/foremanctl/issues/903
- GitHub 릴리스 안내: https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
- GitHub Pages 제한: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- GitHub 로그인 없는 요청 제한 변경(2025-05-08): https://github.blog/changelog/2025-05-08-updated-rate-limits-for-unauthenticated-requests/
- GitHub 불변 릴리스: https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/immutable-releases
- Cloudflare R2 제한: https://developers.cloudflare.com/r2/platform/limits/
- Cloudflare R2 요금: https://developers.cloudflare.com/r2/pricing/
- Cloudflare R2 공개 버킷: https://developers.cloudflare.com/r2/buckets/public-buckets/
- Cloudflare 기본 캐시 동작: https://developers.cloudflare.com/cache/concepts/default-cache-behavior/
- Cloudflare's commitment to free: https://blog.cloudflare.com/cloudflares-commitment-to-free/
