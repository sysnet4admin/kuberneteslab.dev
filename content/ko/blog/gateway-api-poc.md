---
title: "Kubernetes Gateway API 7개 구현체 PoC 비교: 어떤 걸 선택해야 할까?"
date: 2026-04-08
draft: false
tags: ["kubernetes", "gateway-api", "ingress", "poc", "nginx", "envoy", "istio", "cilium"]
categories: ["Kubernetes"]
description: "Ingress NGINX 은퇴를 앞두고, NGINX Gateway Fabric, Envoy Gateway, Istio, Cilium 등 7개 Gateway API 구현체를 17개 테스트 시나리오로 100라운드 검증한 결과를 공유합니다."
summary: "7개 Kubernetes Gateway API 구현체를 17개 테스트로 100라운드 검증한 PoC 결과와 상황별 선택 가이드"
ShowToc: true
TocOpen: true
---

## Ingress NGINX가 은퇴합니다

2026년 3월, 가장 널리 사용되던 Ingress 구현체인 **Ingress NGINX의 지원이 종료**됩니다. Ingress API 자체는 유지되지만, 대표 구현체의 은퇴는 곧 **Gateway API로의 전환**을 의미합니다.

Gateway API는 Ingress API와 무엇이 다를까요? 가장 큰 차이는 **역할 분리**입니다. 인프라 관리자, 클러스터 운영자, 개발자가 각자의 영역에서 독립적으로 설정할 수 있어 더 높은 표현력과 확장성을 제공합니다.

> 이 글은 [요즘IT에 기고한 글](https://yozm.wishket.com/magazine/detail/3559/)의 연장선으로, 기사에서 다루지 못한 **상세 테스트 데이터와 선택 가이드**를 정리합니다.

## 어떤 구현체를 테스트했나?

| 구현체 | 버전 | 특징 |
|--------|------|------|
| NGINX Gateway Fabric | v2.2.1 | F5 Networks 공식 Gateway API 구현체 |
| Envoy Gateway | v1.6.0 | CNCF 졸업 프로젝트, xDS 프로토콜 기반 |
| Istio Gateway | v1.28.0 | 서비스 메시 통합, mTLS 자동화 |
| Cilium Gateway | v1.18.4 | eBPF 기반 고성능 네트워킹 |
| Kong Gateway | v3.9 (KIC v3.5) | 엔터프라이즈 API 게이트웨이 |
| Traefik Gateway | v3.6.2 | 클라우드 네이티브 리버스 프록시 |
| kgateway (Solo.io) | v2.1.1 | ARM64 미지원으로 테스트 제외 |

## 무엇을 테스트했나?

17개 테스트 시나리오를 **100라운드** 반복 실행했습니다.

| 분류 | 테스트 항목 |
|------|------------|
| 라우팅 (3개) | 호스트 기반, 경로 기반, 헤더 기반 라우팅 |
| TLS/보안 (3개) | TLS 종료, HTTPS 리다이렉트, 백엔드 TLS/mTLS |
| 트래픽 관리 (4개) | 카나리 배포, Rate Limiting, 타임아웃/재시도, 세션 어피니티 |
| 요청/응답 수정 (2개) | URL 재작성, 헤더 수정 |
| 고급 기능 (3개) | 크로스 네임스페이스, gRPC 라우팅, 헬스체크 |
| 성능/안정성 (2개) | 부하 테스트 (동시 20요청), 장애 복구 |

## 100라운드 테스트 결과

### 전체 성공률

| 구현체 | 성공률 | PASS | FAIL | SKIP | 등급 |
|--------|--------|------|------|------|------|
| **NGINX Gateway Fabric** | **100%** | 15 | 0 | 2 | **A** |
| **Envoy Gateway** | **100%** | 15 | 0 | 2 | **A** |
| **Istio Gateway** | **100%** | 15 | 0 | 2 | **A** |
| **Cilium Gateway** | **100%** | 15 | 0 | 2 | **A** |
| Kong Gateway | 16.7% | 2 | 10 | 5 | F |
| Traefik Gateway | 8.3% | 1 | 11 | 5 | F |
| kgateway | N/A | - | - | 17 SKIP | - |

**4개 구현체(NGINX, Envoy, Istio, Cilium)가 100라운드에서 단 한 번도 실패하지 않았습니다.**

### Kong Gateway는 왜 실패했나?

```
Error: "no Route matched with those values"
```

HTTPRoute 리소스가 Kong 내부 설정으로 동기화되지 않는 문제입니다. "unmanaged gateway" 모드에서 Gateway API 호환성 이슈가 있으며, 기본 라우팅부터 실패하면서 연쇄적으로 대부분의 테스트가 실패했습니다.

### Traefik Gateway는 왜 실패했나?

```
Error: "404 page not found" / "Gateway not ready"
```

두 가지 근본 원인이 있습니다:
- **EntryPoints 포트 불일치**: 내부 포트(8000/8443)와 외부 포트(80/443) 매핑 문제
- **BackendTLSPolicy CRD 버전 불일치**: v1alpha3 vs v1

Gateway가 Ready 상태에 도달하지 못해 라우팅 자체가 불가능했습니다.

> Kong과 Traefik 모두 Ingress 구현체로서는 성숙한 제품이지만, **Gateway API 지원은 아직 발전 중**입니다.

## Rate Limiting은 어떻게 지원되나?

Rate Limiting은 **Gateway API 표준 스펙에 포함되어 있지 않습니다.** 하지만 Tier 1 구현체 모두 자체 CRD를 통해 지원합니다.

| 구현체 | 지원 여부 | 사용 CRD | 특징 |
|--------|-----------|----------|------|
| Envoy Gateway | O | BackendTrafficPolicy | Gateway API 스타일, 가장 직관적 |
| NGINX Gateway Fabric | O | NginxProxy | NGINX 설정 기반 |
| Istio Gateway | O | Telemetry | Istio 컨트롤 플레인 통합 |
| Cilium Gateway | O | CiliumClusterwideNetworkPolicy | eBPF 기반 네트워크 정책 연동 |

**API 트래픽 제어가 중요하다면 Envoy Gateway의 BackendTrafficPolicy가 가장 Gateway API 친화적인 방식입니다.**

## 상황별 어떤 구현체를 선택해야 할까?

| 상황 | 추천 구현체 | 이유 |
|------|------------|------|
| **안정성이 최우선** | NGINX Gateway Fabric | 검증된 운영 경험, 풍부한 문서, 대규모 커뮤니티 |
| **API Rate Limiting 필요** | Envoy Gateway | Gateway API 스타일 네이티브 Rate Limiting |
| **서비스 메시 환경** | Istio Gateway | mTLS 자동화, Istio 컨트롤 플레인 통합 |
| **고성능/대용량 트래픽** | Cilium Gateway | eBPF 커널 레벨 처리, 네트워크 정책 통합 |
| **멀티 클라우드/하이브리드** | Envoy Gateway | xDS 프로토콜 기반 유연한 설정 |

## 마이그레이션 시 권장 사항

1. Ingress와 Gateway API를 **병행 운영**하며 점진적으로 전환
2. **스테이징 환경**에서 충분히 테스트 후 적용
3. 전환 기간 동안 **모니터링 강화**
4. 문제 발생 시 Ingress로 **롤백 계획** 준비

## 참고 사항

> 이 PoC는 **2025년 12월 5일**에 진행되었습니다. 각 구현체의 버전이 이후 업데이트되면서 결과가 달라질 수 있으므로, 도입 검토 시에는 최신 버전으로 재검증하는 것을 권장합니다.

## 참고 자료

- [요즘IT 기사: 쿠버네티스 7개 주요 게이트웨이 기술 검증(PoC)하기](https://yozm.wishket.com/magazine/detail/3559/) — 배경과 개념을 포함한 전체 내용
- [GitHub: gateway-PoC](https://github.com/sysnet4admin/Research/tree/main/gateway-PoC) — 17개 테스트 자동화 스크립트 및 상세 결과
