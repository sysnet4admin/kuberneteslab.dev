---
title: "cc-deck: Claude Code 세션 브라우저 & 태스크 관리 도구"
date: 2026-05-08
draft: false
tags: ["claude-code", "developer-tools", "productivity", "fzf", "zsh"]
categories: ["Tools"]
description: "여러 프로젝트를 오가며 Claude Code를 쓰다 보면 어떤 세션에서 뭘 하고 있었는지 파악하기 어렵습니다. cc-deck은 fzf TUI로 전체 세션을 탐색하고, 마지막 입력 내용을 미리보기로 보여주며, Claude 메모리의 TODO를 자동으로 상단에 고정합니다."
summary: "fzf TUI로 Claude Code 세션을 탐색하고, 메모리 TODO를 자동 고정하며, 원래 디렉토리로 이동해 세션을 재개하는 zsh 함수"
ShowToc: true
TocOpen: true
---

## 문제

Claude Code는 `/quit`으로 종료할 때 resume 링크를 알려줍니다. 하지만 터미널이 갑자기 닫히거나, 어제 작업하던 세션으로 돌아가고 싶을 때 `claude --resume`이 보여주는 목록은 요약이 압축되어 있어 어느 세션인지 구분하기 어렵습니다. 결국 세션을 찾는 데 더 많은 시간을 씁니다.

또 다른 문제가 있습니다. Claude에게 *"며칠 지켜봐줘"*, *"다음 주에 다시 확인해줘"* 같은 요청을 하면 메모리에 기록되지만, 다음 번에 세션을 열 때 그 내용을 다시 찾아보기가 번거롭습니다.

## cc-deck이 하는 것

`cc-deck`은 fzf picker로 최근 Claude Code 세션을 탐색하는 zsh 함수입니다. 각 항목에는 압축된 요약이 아니라 **그 세션에서 마지막으로 입력한 내용**이 표시됩니다.

```
[TODO] /tmp/projects/infra/k8s: 3Gi 적용 후 2주간 OOMKill 재발 여부 모니터링
[PIN]  /tmp/projects/api-server: 롤백 없이 어떻게 수정해?
────────────────────────────────────────────────────────────────────────
* 2026-05-08 09:14  /tmp/projects/api-server:    롤백 없이 어떻게 수정해?
  2026-05-08 08:59  /tmp/projects/infra/k8s:    적용했어 — OOMKill 다시 나면 알려줘
  2026-05-08 08:38  /tmp/projects/frontend:     수정 방법이 뭐야?
  2026-05-08 08:17  /tmp/projects/auth-service: 토큰 폐기는 어떻게 해?
  2026-05-08 07:59  /tmp/projects/monitoring:   에러율 알림도 추가해줘
```

Claude 메모리의 TODO는 상단에 자동으로 고정됩니다. 세션을 선택하면 원래 디렉토리로 자동 이동 후 재개합니다.

![데모](https://raw.githubusercontent.com/sysnet4admin/cc-deck/main/demo/demo_ko.gif)

## 주요 기능

**마지막 입력 내용 미리보기**  
UUID나 압축 요약 대신, 그 세션에서 실제로 무엇을 묻고 있었는지를 보여줍니다. JSONL 파일에서 마지막 user 입력을 직접 추출합니다.

**TODO 자동 고정**  
*"메모리에 TODO로 기록해줘"*, *"다음 주에 다시 확인해줘"* 같은 요청을 하면 Claude가 `type: project`, `name: TODO...` 형식의 메모리 파일을 작성합니다. cc-deck이 이를 자동 감지해서 상단에 고정하고, `originSessionId`를 통해 해당 작업 세션으로 바로 이동합니다.

**Ctrl-K 수동 고정**  
어떤 세션이든 `Ctrl-K`로 핀/언핀 토글을 할 수 있습니다. 수동으로 고정한 세션은 해제하기 전까지 상단에 유지됩니다.

**스마트 재개**  
세션 선택 시 원래 디렉토리로 자동으로 `cd`한 후 `claude --resume`을 실행합니다. 수동으로 이동할 필요가 없습니다.

**4가지 실행 모드**  
`Ctrl-O/A/D/X`로 `claude`, `claude-api`, `--dangerously-skip-permissions` 및 조합을 선택할 수 있고, 마지막 선택한 모드가 다음 실행에도 유지됩니다.

**빠른 속도**  
mtime 기반 캐시로 100개 세션 기준 재실행 시 ~0.04초.

## 설치

```zsh
git clone https://github.com/sysnet4admin/cc-deck.git ~/cc-deck
cd ~/cc-deck
./install.sh
source ~/.zshrc
```

[fzf](https://github.com/junegunn/fzf) 필요: `brew install fzf`

## TODO가 고정되는 원리

Claude에게 추적을 요청하면:

```
메모리에 TODO로 기록해줘
다음 주에 다시 확인해줘
며칠 지켜보자
```

Claude가 다음과 같은 메모리 파일을 작성합니다:

```yaml
---
name: TODO - EKS 클러스터 3Gi 메모리 제한 적용 후 모니터링
description: 2주간 OOMKill 재발 여부 확인
type: project
originSessionId: a40fabf4-3d29-4014-a710-dcd444580c9d
---
```

cc-deck은 `~/.claude/projects/*/memory/*.md`에서 `type: project`이고 이름이 `TODO`로 시작하는 항목을 스캔해서 `originSessionId`로 원본 세션과 연결합니다. 별도 설정 없이 동작합니다.

## 키 바인딩

| 키 | 동작 |
|----|------|
| `Enter` | 마지막 저장된 모드로 재개 |
| `Ctrl-K` | 현재 세션 고정 / 해제 |
| `Ctrl-O` | `claude`로 재개 |
| `Ctrl-A` | `claude-api`로 재개 |
| `Ctrl-D` | `claude --dangerously-skip-permissions`로 재개 |
| `Ctrl-X` | `claude-api --dangerously-skip-permissions`로 재개 |

## 소스

[github.com/sysnet4admin/cc-deck](https://github.com/sysnet4admin/cc-deck)
