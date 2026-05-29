---
title: "cc-deck: Claude Code 세션을 한눈에"
date: 2026-05-08
draft: false
tags: ["claude-code", "developer-tools", "productivity", "fzf", "zsh", "bash"]
categories: ["Tools"]
description: "여러 프로젝트의 Claude Code 세션이 쌓입니다. cc-deck은 이를 검색 가능한 허브로 만드는 TUI 도구입니다. macOS(zsh), Linux(bash), Windows(PowerShell) 지원. 퍼지 검색, TODO 자동 고정, 수동 북마크, 기록 없는 빠른 질문, 세션 크기 관리, 스마트 재개."
summary: "Claude Code 세션을 검색하고 관리할 수 있는 다중 플랫폼 TUI 도구 — 퍼지 검색, TODO 자동 고정, 수동 북마크, 빠른 질문, 비대 세션 크기 관리, 스마트 재개."
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

### 4. 빠른 질문 (Quick Query)

기록이 필요 없는 짧은 질문:

```zsh
# 일회성: 답변 출력 후 세션 저장 없음
cc-deck -q "SIGTERM이 뭐야?"

# 대화형: 계속 질문 가능, 7일 후 자동 삭제
cc-deck -q
```

2회 이상 대화한 세션은 보존되어 TUI에 `[Quick]`으로 표시됩니다. TUI 안에서 `Ctrl-Q`를 누르면 브라우저를 나가지 않고 빠른 질문을 할 수 있습니다.

```
[TODO]  /tmp/projects/infra/k8s: 3Gi 적용 후 OOMKill 모니터링
[PIN]   /tmp/projects/api-server: 메모리 사용량 계속 증가
[Quick] ▶ 1 session
────────────────────────────────────────────────────────────
* 2026-05-08 09:14  /tmp/projects/api-server: ...
```

---

### 5. 세션 크기 관리

오래 이어간 세션의 `.jsonl`은 수백 MB까지 커집니다. `claude --resume`이 파일 전체를 메모리에 로드하기 때문에, 큰 세션은 시작이 느려집니다 — 수 초간 멈춤, RAM 폭증. 그런데 비대한 세션은 보통 오래된 것이라 최근 목록 밖으로 밀려 잘 보이지도 않습니다.

cc-deck은 이런 비대 세션을 최근 사용 여부와 무관하게 `[Quick]` 아래 **"sessions to manage"** 그룹에 노출합니다:

```
[Quick] ▶ 1 session
──────────────── sessions to manage (large) ────────────────
[122M] /tmp/projects/books: 챕터 초안 검토
 [77M] /tmp/projects/research: keep-alive 튜닝 결과
```

정리 방법은 두 가지이며, 둘 다 세션 ID를 유지해 resume이 그대로 됩니다:

**`Ctrl-G` — 스냅샷 정리 (무손실).** 비대의 주범은 대개 `file-history-snapshot`(매 턴 기록되는 rewind 체크포인트)입니다. 누적식이라 매번 *전체* 추적-파일 장부를 다시 적기 때문에 제곱으로 커지고, 한 파일의 60%를 차지하면서도 대화엔 전혀 기여하지 않습니다. 마지막 몇 개만 남기고 제거하며 대화는 그대로입니다. 100MB↑ 세션은 실행 시 자동으로도 정리되고, 원본 수정 시각을 보존해 정리된 세션이 목록 위로 튀지 않습니다.

**`Ctrl-E` — 최근 턴만 남기기 (손실).** 대화 자체로 큰 세션일 때, 최근 ~10턴만 남기고 **전체 세션을 `~/.claude/_archive/`에 gzip으로 먼저 보관**합니다. 최근 흐름은 유지되고 전체 기록은 안전하게 저장됩니다. 정리된 세션은 정상적으로 resume되어 하던 곳에서 바로 이어집니다.

실제로 305MB 세션이 무손실로 122MB가 되고, 대화-주범 77MB 세션이 최근 10턴을 유지하며 0.8MB로 줄었습니다.

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
| `Ctrl-R` | TODO 완료 처리 / PIN 또는 Quick 세션 제거 |
| `Ctrl-Q` | 빠른 질문 (세션 저장 없음) |
| `Ctrl-G` | 옛 스냅샷 정리 (무손실, 크기 축소) |
| `Ctrl-E` | 최근 턴만 남기고 정리 (손실, 전체 먼저 아카이브) |
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
