---
title: "CLAUDE.md를 AGENTS.md로 바꾸면 느려질까요?"
date: 2026-07-03
draft: false
tags: ["claude-code", "agents-md", "aaif", "context-file", "llm-agent", "benchmark", "kubernetes"]
categories: ["AI"]
description: "프로젝트 컨텍스트 파일을 CLAUDE.md에서 AGENTS.md로 옮길 때 import와 심볼릭 링크 두 우회 방법이 속도나 토큰 비용을 늘리는지, 모델 4종과 174회 실행으로 검증했습니다. 어느 티어에서도 페널티가 없었습니다."
summary: "AGENTS.md 마이그레이션의 두 우회 방법(import, 심볼릭 링크)을 쿠버네티스 장애 대응 과제에서 검증했더니, 속도와 컨텍스트 로드 토큰 어느 쪽에도 페널티가 없었고 import는 오히려 3~4% 가벼웠습니다."
ShowToc: true
TocOpen: true
---

## 컨텍스트 파일이 하나씩 늘어나는 문제

AI 코딩 에이전트를 쓰는 팀이라면 저장소 루트에 이런 파일들이 쌓여 있을 겁니다. Claude Code용 `CLAUDE.md`, Cursor용 규칙 파일, Copilot용 instructions. 내용은 거의 같습니다. 빌드 명령, 테스트 방법, 건드리면 안 되는 영역. 도구가 하나 늘 때마다 같은 내용을 파일명만 바꿔 복제하고, 하나를 고치고 나면 나머지 고치는 걸 잊어버릴 수도 있습니다.

[AGENTS.md](https://agents.md/)는 이 문제를 해결하려고 나온 개방형 형식입니다. Linux Foundation 산하 AAIF(Agentic AI Foundation)가 관리하고, 30개가 넘는 에이전트가 이 파일을 읽습니다. 파일 하나로 모든 도구에 대응하자는 것이죠.

그런데 Claude Code는 아직 AGENTS.md를 바로 읽지 못합니다([issue #34235](https://github.com/anthropics/claude-code/issues/34235)). 옮기려면 우회 방법이 필요합니다. `CLAUDE.md`에 `@AGENTS.md` import 한 줄만 남기거나, `CLAUDE.md`를 `AGENTS.md`를 가리키는 심볼릭 링크로 바꾸는 것입니다.

여기서 걱정이 생깁니다. 컨텍스트 파일은 에이전트 세션마다 로드됩니다. 우회하는 과정에서 비용이 조금이라도 늘어난다면, 그 비용은 세션을 돌릴 때마다 쌓입니다. Princeton의 [측정 연구](https://arxiv.org/abs/2601.20404)는 AGENTS.md를 네이티브로 읽는 Codex만 다뤘고, import나 심볼릭 링크 경로를 측정한 데이터는 없었습니다. 그래서 직접 측정해 봤습니다. 결과 수치와 재현 방법은 [GitHub 저장소](https://github.com/sysnet4admin/Research/tree/main/agents-md-migration)에 있습니다.

## 무엇을 어떻게 측정했나

같은 내용을 세 가지 방식으로 전달했습니다.

- **A (native)**: 지금처럼 `CLAUDE.md`에 본문을 둡니다.
- **B (import)**: `CLAUDE.md`에는 `@AGENTS.md` 한 줄, 본문은 `AGENTS.md`로 옮깁니다.
- **C (symlink)**: 본문은 `AGENTS.md`에 두고, `CLAUDE.md`는 이를 가리키는 심볼릭 링크입니다.

세 조건의 본문은 체크섬까지 같은 문서입니다. 실험용으로 지어낸 문서가 아니라 실제 벤치마크 운영에 쓰는 컨텍스트 파일(클러스터 규칙, 점수 공식, 알려진 함정)을 그대로 썼습니다.

과제는 쿠버네티스 장애 대응입니다. CrashLoopBackOff에 빠진 파드, 잘못된 Service selector, OOM 같은 장애를 심어 둔 전용 클러스터에서 에이전트가 원인을 찾아 고치게 했습니다. 속도를 측정하기 전에 본문에 카나리 한 줄("PING에 PONG으로 답하라")을 심어 세 방식이 실제로 읽히는지부터 확인했습니다. 셋 다 읽혔고, 컨텍스트가 없는 대조군만 카나리에 응답하지 않았으니 확인 방법 자체도 제대로 작동한 셈입니다.

측정은 두 단계로 했습니다. 먼저 10개 시나리오 전체를 한 번씩 돌리고(30회), 편차가 작은 4개 시나리오는 모델 4종(Haiku 4.5, Sonnet 4.6, Opus 4.8, Fable 5)으로 3회씩 반복했습니다(144회). 174회 전부 정상적으로 끝났습니다.

## 결과: 걱정할 필요가 없었습니다

비용을 가장 정확하게 보여주는 지표는 세션 시작 때 한 번 발생하는 컨텍스트 로드 토큰(cache write)입니다. 우회 방법이 로드되는 내용을 부풀렸다면 여기서 B나 C가 A보다 커야 합니다. 결과는 반대였습니다.

| 모델 | A (native) | B (import) vs A | C (symlink) vs A |
|---|---|---|---|
| Haiku 4.5 | 22,049 | -3% | +1% |
| Sonnet 4.6 | 14,357 | -3% | -1% |
| Opus 4.8 | 15,542 | -4% | -1% |
| Fable 5 | 16,357 | -3% | -1% |

import(B)는 오히려 3~4% 낮습니다. 네 모델 모두에서 같은 방향이므로 우연이 아닙니다. 심볼릭 링크(C)는 native와 ±1% 안, 사실상 같습니다.

wall time은 차이가 커 보이지만 일관된 경향이 없습니다. 어떤 모델에서는 B가 빠르고 어떤 모델에서는 느리며, 시간 차이가 가장 큰 경우에도 토큰 차이는 거의 없습니다. 전달 방식에서 온 오버헤드라면 결과가 한쪽으로 치우쳐야 합니다. 그렇지 않다는 것은, 이 변동이 에이전트가 매번 조금씩 다르게 문제를 풀어서 생겼다는 뜻입니다. 모델별 수치는 [README 결과 섹션](https://github.com/sysnet4admin/Research/tree/main/agents-md-migration)에 있습니다.

## 왜 이런 결과가 나올까

심볼릭 링크에 비용이 들지 않는 이유는 단순합니다. Claude Code가 `CLAUDE.md`라는 경로를 여는 순간 OS가 링크를 해석해 `AGENTS.md`의 내용을 돌려줍니다. Claude Code 입장에서는 native 파일을 읽을 때와 완전히 같고, 링크 처리는 파일시스템의 몫입니다. C가 A와 ±1%였던 측정 결과와 정확히 맞아떨어집니다.

import의 -3%는 예상 밖이었습니다. 같은 본문인데 로드 토큰이 줄었다는 것은, Claude Code가 import된 파일을 본문을 직접 둘 때와 조금 다르게 처리한다는 뜻으로 보입니다. 어느 쪽이든 손해가 아니라는 점이 중요합니다.

## 그래서 어떻게 하면 될까

AGENTS.md를 정본으로 두고 `CLAUDE.md`는 `@AGENTS.md` 한 줄로 줄여도 됩니다. 속도도 토큰도 잃지 않습니다. 도구가 늘어나도 관리하는 파일은 하나입니다.

다만 두 가지는 짚어두겠습니다. 첫째, 이번에 측정한 것은 속도와 토큰 비용까지입니다. 답변 정확성과 안전(파괴적 kubectl 명령이 줄거나 느는지)은 별도 채점이 필요해서 이번에는 다루지 않았습니다. 둘째, 무엇을 담느냐가 어떻게 전달하느냐보다 중요합니다. [ETH Zurich 연구](https://arxiv.org/abs/2602.11988)는 LLM이 생성한 컨텍스트 파일이 오히려 성공률을 낮추고 비용을 20% 넘게 올린다고 보고했습니다. 파일은 사람이 다듬고, 전달 방식은 편한 쪽을 고르면 됩니다.

## 마치며

마이그레이션을 미루게 되는 이유는 대부분 "느려지면 어떡하지" 같은 막연한 걱정입니다. 이런 걱정은 직접 확인해 보기 전에는 사라지지 않습니다. 그래서 확인해 봤고, Haiku부터 Fable까지 어느 티어에서도 페널티가 없었습니다. import는 오히려 조금 가벼웠습니다. 측정 하네스와 클러스터 구성, 집계 스크립트는 모두 [GitHub 저장소](https://github.com/sysnet4admin/Research/tree/main/agents-md-migration)에 있으니, 자기 프로젝트의 컨텍스트 파일로 같은 비교를 돌려볼 수 있습니다.
