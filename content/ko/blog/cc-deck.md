---
title: "cc-deck: Claude Code 세션을 한눈에"
date: 2026-05-08
draft: false
tags: ["claude-code", "developer-tools", "productivity", "fzf", "zsh", "bash"]
categories: ["Tools"]
description: "여러 프로젝트의 Claude Code 세션이 쌓입니다. cc-deck은 이를 검색 가능한 허브로 만드는 TUI 도구입니다. macOS(zsh), Linux(bash), Windows(PowerShell) 지원. 퍼지 검색, TODO 자동 고정, 수동 북마크, 자동 업데이트."
summary: "Claude Code 세션을 검색하고 관리할 수 있는 다중 플랫폼 TUI 도구 — 퍼지 검색, TODO 자동 고정, 수동 북마크, 스마트 재개."
ShowToc: true
TocOpen: true
---

## 문제

여러 프로젝트에서 Claude Code 세션이 쌓입니다. 어제 디버깅하던 세션, Claude가 나중에 확인하라고 기록한 TODO, 북마크해두고 싶은 세션으로 돌아가려면 번거롭습니다.

`claude --resume`으로 목록을 봐도 요약이 압축되어 있어서 어느 세션인지 구분하기 어렵습니다.

## cc-deck이란?

`cc-deck`은 전체 Claude Code 세션에 대한 fzf TUI를 엽니다. 각 항목은 압축 요약이 아닌 **마지막으로 입력한 내용**을 보여줍니다. 텍스트를 입력하면 실시간으로 필터링됩니다. TODO와 수동 핀 항목은 항상 상단에 고정됩니다.

macOS(zsh), Linux(bash), Windows(PowerShell)을 모두 지원합니다.

![데모](https://raw.githubusercontent.com/sysnet4admin/cc-deck/main/demo/demo_social_ko.gif)

## 기능

### 1. 퍼지 검색

프롬프트에 텍스트를 입력하면 마지막 입력 내용을 기준으로 세션이 실시간 필터링됩니다. 언제 어디서 했는지 기억하지 않아도 됩니다.

```
cc-deck> OOM
  2/100
  2026-05-08 08:59  /tmp/projects/infra/k8s: 스케일 업 후 pod OOMKill 계속 남
```

항목을 선택하면 cc-deck이 원래 디렉토리로 이동하고 해당 세션을 자동으로 재개합니다.

---

### 2. TODO 자동 고정

Claude에게 나중에 확인할 항목을 기록해달라고 하면:

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

cc-deck이 `~/.claude/projects/*/memory/*.md`에서 `type: project`이고 이름에 `TODO`가 포함된 항목을 감지해서 상단에 고정합니다. `originSessionId`로 원본 세션과 연결되어 있어서, 선택하면 해당 작업이 이루어진 프로젝트 디렉토리로 바로 이동합니다.

```
[TODO] /tmp/projects/infra/k8s: 2주간 OOMKill 재발 여부 확인
```

TODO가 해결되면 `Ctrl-R`을 누릅니다. cc-deck이 메모리 파일 이름을 `TODO - EKS 클러스터 ...` → `EKS 클러스터 ... (completed)`으로 변경하고 목록에서 제거합니다. 메모리 파일은 그대로 남아서 Claude도 내용을 기억합니다.

---

### 3. 수동 PIN

자주 돌아올 세션을 북마크합니다. 세션으로 이동 후 `Ctrl-K`를 누르면 마지막 입력 내용이 레이블로 저장되어 상단에 고정됩니다.

```
[PIN]  /tmp/projects/api-server: 배포 이후 메모리 사용량 계속 증가 — 원인 찾아줘
```

선택하면 cc-deck이 `/tmp/projects/api-server`로 이동하고 정확히 그 세션을 재개합니다. 핀된 항목에서 `Ctrl-K`를 다시 누르면 해제됩니다. `Ctrl-R`로도 제거할 수 있습니다.

---

## 기본 포함 기능

**키 바인딩**

| 키 | 동작 |
|----|------|
| `Enter` | 마지막 저장된 모드로 재개 |
| `Tab` | 실행 모드 순환 (default → api → skip → api+skip) |
| `Ctrl-O` | `claude`로 재개 |
| `Ctrl-A` | `claude-api`로 재개 |
| `Ctrl-S` | `claude --dangerously-skip-permissions`로 재개 |
| `Ctrl-X` | `claude-api --dangerously-skip-permissions`로 재개 |
| `Ctrl-K` | 현재 세션 핀 / 언핀 |
| `Ctrl-R` | TODO 완료 처리 / PIN 제거 |
| `F1` | 도움말 표시 |
| `ESC` | 종료 |

모드를 선택하면 다음에도 그대로 유지됩니다. 기본값 변경: `export CLAUDE_DECK_CMD="claude-api"`

**디렉토리 자동 이동**  
TODO, PIN, 일반 세션 어떤 항목을 선택하든 `claude --resume` 전에 원래 작업 디렉토리로 자동으로 `cd`합니다. 설정 없이도 항상 맞는 디렉토리에서 시작합니다.

**자동 업데이트**  
cc-deck 실행 시 백그라운드에서 24시간마다 업데이트를 자동으로 확인합니다. 업데이트가 있으면 다음 실행 시 알림이 표시됩니다.

```
[cc-deck] Updated (v0.2.0 → v1.0.0). Reload with: source ~/.zshrc
```

수동으로 즉시 업데이트하려면:

```bash
cc-deck update
```

비활성화하려면 `CC_DECK_DISABLE_AUTOUPDATER=1`을 설정합니다.

**캐시**  
mtime 기반 세션 캐시로 재실행 시 ~0.04초.

---

## 설치

**macOS (zsh)**

```zsh
git clone https://github.com/sysnet4admin/cc-deck.git ~/cc-deck
cd ~/cc-deck
./install.sh
source ~/.zshrc
```

**Linux (bash)**

```bash
git clone https://github.com/sysnet4admin/cc-deck.git ~/cc-deck
cd ~/cc-deck
./install.sh --bash
source ~/.bashrc
```

**Windows (PowerShell)**

```powershell
git clone https://github.com/sysnet4admin/cc-deck.git "$HOME\cc-deck"
. "$HOME\cc-deck\install.ps1"
```

사전 요구사항:
- git (모든 플랫폼 필수 — Windows: `winget install Git.Git`)
- python3 (모든 플랫폼 필수)
- macOS: `brew install fzf`
- Linux: `sudo apt install fzf` 또는 `sudo dnf install fzf`
- Windows: `winget install junegunn.fzf`

## 소스

[github.com/sysnet4admin/cc-deck](https://github.com/sysnet4admin/cc-deck)
