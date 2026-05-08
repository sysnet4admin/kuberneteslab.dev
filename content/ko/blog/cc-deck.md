---
title: "cc-deck: Claude Code 세션 허브"
date: 2026-05-08
draft: false
tags: ["claude-code", "developer-tools", "productivity", "fzf", "zsh"]
categories: ["Tools"]
description: "여러 프로젝트의 Claude Code 세션이 쌓입니다. cc-deck은 이를 검색 가능한 허브로 만드는 zsh 함수입니다. 마지막 입력 내용으로 퍼지 검색, Claude 메모리 TODO 자동 고정, Ctrl-K 북마크, 원래 디렉토리로 자동 이동 후 재개."
summary: "Claude Code 세션을 검색하고 관리할 수 있는 zsh 함수 — 퍼지 검색, TODO 자동 고정, 수동 북마크, 스마트 재개."
ShowToc: true
TocOpen: true
---

## 문제

여러 프로젝트에서 Claude Code 세션이 쌓입니다. 어제 디버깅하던 세션, Claude가 나중에 확인하라고 기록한 TODO, 북마크해두고 싶은 세션으로 돌아가려면 번거롭습니다.

`claude --resume`으로 목록을 봐도 요약이 압축되어 있어서 어느 세션인지 구분하기 어렵습니다. UUID를 보며 스크롤하는 대신 바로 작업으로 돌아가고 싶습니다.

## cc-deck이 하는 것

`cc-deck`은 전체 Claude Code 세션에 대한 fzf TUI를 엽니다. 각 항목은 압축 요약이 아닌 **마지막으로 입력한 내용**을 보여줍니다. 텍스트를 입력하면 실시간으로 필터링됩니다. Claude 메모리의 TODO는 자동으로 상단에 고정됩니다.

![데모](https://raw.githubusercontent.com/sysnet4admin/cc-deck/main/demo/demo_social_ko.gif)

## 주요 기능

**퍼지 검색**  
마지막 입력 내용을 기준으로 세션을 필터링합니다. 언제 어디서 했는지 기억하지 않아도 원하는 세션을 바로 찾을 수 있습니다.

**TODO 자동 고정**  
*"메모리에 TODO로 기록해줘"*, *"다음 주에 다시 확인해줘"* 라고 하면 Claude가 `name: TODO ...` 형식의 메모리 항목을 작성합니다. cc-deck이 이를 자동 감지해서 상단에 고정하고, `originSessionId`로 원본 세션과 연결합니다.

**Ctrl-D로 TODO 완료 처리**  
TODO가 해결되면 `Ctrl-D`를 누릅니다. cc-deck은 메모리 항목 이름에서 `TODO`를 제거하고 `(completed)`를 추가합니다. 메모리 파일은 보존되므로 Claude의 컨텍스트는 그대로 유지됩니다.

**Ctrl-K로 북마크**  
`Ctrl-K`로 세션을 고정합니다. 마지막 입력 내용이 레이블로 저장됩니다. 다시 누르면 해제됩니다.

**스마트 재개**  
세션 선택 시 원래 디렉토리로 자동 이동 후 `claude --resume`을 실행합니다. 수동 이동이 필요 없습니다.

**4가지 실행 모드**  
`Ctrl-O/A/S/X`로 `claude`, `claude-api`, `--dangerously-skip-permissions` 및 조합을 선택할 수 있고, 마지막 선택한 모드가 유지됩니다.

**빠른 속도**  
mtime 기반 캐시로 재실행 시 ~0.04초.

## 설치

```zsh
git clone https://github.com/sysnet4admin/cc-deck.git ~/cc-deck
cd ~/cc-deck
./install.sh
source ~/.zshrc
```

[fzf](https://github.com/junegunn/fzf) 필요: `brew install fzf`

## TODO 동작 방식

Claude에게 추적을 요청합니다:

```
메모리에 TODO로 기록해줘
다음 주에 다시 확인해줘
```

Claude가 메모리 파일을 작성합니다:

```yaml
---
name: TODO - EKS 클러스터 3Gi 메모리 제한 적용 후 모니터링
description: 2주간 OOMKill 재발 여부 확인
type: project
originSessionId: a40fabf4-3d29-4014-a710-dcd444580c9d
---
```

cc-deck은 `~/.claude/projects/*/memory/*.md`에서 `type: project`이고 이름에 `TODO`가 포함된 항목을 감지해서 원본 세션과 연결합니다. `Ctrl-D`를 누르면 이름이 `EKS 클러스터 3Gi 메모리 제한 적용 후 모니터링 (completed)`으로 변경되어 목록에서 사라지지만, 메모리는 그대로 보존됩니다.

## 키 바인딩

| 키 | 동작 |
|----|------|
| `Enter` | 마지막 저장된 모드로 재개 |
| `Ctrl-K` | 현재 세션 고정 / 해제 |
| `Ctrl-D` | TODO 완료 처리 / PIN 제거 |
| `Ctrl-O` | `claude`로 재개 |
| `Ctrl-A` | `claude-api`로 재개 |
| `Ctrl-S` | `claude --dangerously-skip-permissions`로 재개 |
| `Ctrl-X` | `claude-api --dangerously-skip-permissions`로 재개 |

## 소스

[github.com/sysnet4admin/cc-deck](https://github.com/sysnet4admin/cc-deck)
