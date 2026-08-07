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

## 테스트 환경

### 클러스터 구성

| 항목 | 내용 |
|------|------|
| Kubernetes 버전 | v1.34.2 |
| 아키텍처 | ARM64 (Apple Silicon) |
| OS | Ubuntu 22.04.5 LTS |
| 컨테이너 런타임 | containerd 1.7.24 |
| Gateway API 버전 | v1.2.0 |
| CNI | Cilium v1.18.4 (eBPF, kube-proxy replacement) |

### 노드 구성

| 노드 | 역할 | IP | CPU | 메모리 |
|------|------|----|-----|--------|
| cp-k8s | control-plane | 192.168.1.10 | 4 vCPU | 3.8 GB |
| w1-k8s | worker | 192.168.1.101 | 4 vCPU | 7.8 GB |
| w2-k8s | worker | 192.168.1.102 | 4 vCPU | 7.8 GB |
| w3-k8s | worker | 192.168.1.103 | 4 vCPU | 7.8 GB |

**총 클러스터 리소스**: 16 vCPU, 27.2 GB 메모리

### Gateway별 IP 할당

| 구현체 | GatewayClass | IP | 네임스페이스 |
|--------|-------------|-----|------------|
| NGINX Gateway Fabric | nginx | 192.168.1.11 | nginx-gateway |
| Envoy Gateway | eg | 192.168.1.12 | envoy-gateway-system |
| Istio Gateway | istio | 192.168.1.14 | istio-system |
| Cilium Gateway | cilium | 192.168.1.15 | kube-system |
| Kong Gateway | kong | 192.168.1.16 | kong |
| Traefik Gateway | traefik | 192.168.1.17 | traefik |
| kgateway | kgateway | N/A | ARM64 미지원, 테스트 제외 |

동일 클러스터에서 7개의 Gateway 구현체를 독립적으로 운영했습니다. CNI로 Cilium을 선택한 이유는 Cilium Gateway 테스트를 포함하기 위해서입니다. 다른 CNI를 사용할 경우 Cilium Gateway를 제외한 나머지 6개는 영향 없이 동일하게 동작합니다.

### 클러스터 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                  Kubernetes Cluster (v1.34.2)                    │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Control Plane (cp-k8s)                        │  │
│  │              192.168.1.10 | 4 CPU | 3.8GB                  │  │
│  │  ┌─────────┐ ┌──────┐ ┌───────────┐ ┌──────────┐          │  │
│  │  │kube-api │ │ etcd │ │ scheduler │ │ ctrl-mgr │          │  │
│  │  └─────────┘ └──────┘ └───────────┘ └──────────┘          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │ Worker: w1-k8s  │ │ Worker: w2-k8s  │ │ Worker: w3-k8s  │   │
│  │ 192.168.1.101   │ │ 192.168.1.102   │ │ 192.168.1.103   │   │
│  │ 4 CPU | 7.8GB   │ │ 4 CPU | 7.8GB   │ │ 4 CPU | 7.8GB   │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              CNI: Cilium v1.18.4 (eBPF)                    │  │
│  │  • kube-proxy replacement  • Gateway API 활성화  • VXLAN   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐       │
│  │   nginx   │ │   envoy   │ │   istio   │ │  cilium   │       │
│  │ .1.11     │ │ .1.12     │ │ .1.14     │ │ .1.15     │       │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘       │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐                      │
│  │   kong    │ │  traefik  │ │ kgateway  │                      │
│  │ .1.16     │ │ .1.17     │ │ (ARM64 ✗) │                      │
│  └───────────┘ └───────────┘ └───────────┘                      │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Backend Services                         │  │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────────────┐   │  │
│  │  │echo-v1 │  │echo-v2 │  │  grpc  │  │  backend-ns    │   │  │
│  │  │(stable)│  │(canary)│  │(HTTP/2)│  │(cross-namespace│   │  │
│  │  └────────┘  └────────┘  └────────┘  └────────────────┘   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 백엔드 서비스 구성

테스트에 사용된 백엔드 서비스는 4종류입니다.

| 서비스 | 역할 | 사용된 테스트 |
|--------|------|-------------|
| `echo-v1` | 안정 버전 (stable) | 카나리 배포 시 80% 트래픽 수신 |
| `echo-v2` | 카나리 버전 (canary) | 카나리 배포 시 20% 트래픽 수신 |
| `grpc` | gRPC 서버 (HTTP/2) | gRPC 라우팅 테스트 전용 |
| `backend-ns` | 별도 네임스페이스 서비스 | 크로스 네임스페이스 라우팅 테스트 |

`echo-v1`/`echo-v2`는 호스트 기반·경로 기반·헤더 기반 라우팅, 카나리, Rate Limiting 등 대부분의 테스트에서 공통으로 사용됩니다. `grpc`는 gRPC 프로토콜 전용, `backend-ns`는 `gateway-poc` 네임스페이스의 Gateway에서 `backend-ns` 네임스페이스로 트래픽을 넘기는 크로스 네임스페이스 시나리오에만 사용됩니다.

## 어떤 구현체를 테스트했나?

| 구현체 | 버전 | 특징 |
|--------|------|------|
| NGINX Gateway Fabric | v2.2.1 | F5 오픈소스, 검증된 안정성과 풍부한 문서 |
| Envoy Gateway | v1.6.0 | CNCF 졸업 프로젝트, xDS 기반, Rate Limiting 네이티브 지원 |
| Istio Gateway | v1.28.0 | 서비스 메시 통합, mTLS 자동화, CNCF 졸업(2024) |
| Cilium Gateway | v1.18.4 | eBPF 기반 고성능, 커널 레벨 처리, CNCF 졸업(2023) |
| Kong Gateway | v3.9 (KIC v3.5) | 엔터프라이즈 API 게이트웨이, 풍부한 플러그인 생태계 |
| Traefik Gateway | v3.6.2 | 클라우드 네이티브 리버스 프록시, Let's Encrypt 통합 |
| kgateway (Solo.io) | v2.1.1 | CNCF Sandbox(2025), ARM64 미지원으로 테스트 제외 |

### 구현체 선정 이유

**NGINX Gateway Fabric**: 웹 서버/리버스 프록시 시장에서 가장 오랜 운영 경험을 가진 NGINX의 공식 Gateway API 구현체. Ingress NGINX를 사용하던 팀이 가장 자연스럽게 전환할 수 있는 선택지.

**Envoy Gateway**: Envoy Proxy(CNCF 졸업, 2018)를 기반으로 한 Gateway API 구현체. xDS 프로토콜 기반 동적 설정과 풍부한 필터 체인이 특징. Rate Limiting을 선언적 CRD로 지원하는 유일한 구현체.

**Istio Gateway**: 서비스 메시의 사실상 표준인 Istio가 제공하는 Gateway API 지원. Envoy 기반이지만 Istio 컨트롤 플레인과 통합되어 mTLS 자동화, 트래픽 관리가 가능.

**Cilium Gateway**: eBPF를 활용해 커널 레벨에서 패킷을 처리하는 고성능 구현체. L3/L4/L7을 통합하며 네트워크 정책과 연동 가능. CNI로 Cilium을 사용하는 클러스터 전용.

**Kong Gateway**: 엔터프라이즈 API Gateway 시장의 선두 주자. 풍부한 플러그인 생태계와 엔터프라이즈 지원이 강점이나, Gateway API 지원은 발전 중.

**Traefik Gateway**: 클라우드 네이티브 환경에 특화된 리버스 프록시. 자동 서비스 디스커버리와 Let's Encrypt 통합이 장점이나, Gateway API 지원은 성숙 단계 진행 중.

## 무엇을 테스트했나?

17개 테스트 시나리오를 **100라운드** 반복 실행했습니다.

| 분류 | # | 테스트 항목 | 설명 |
|------|---|------------|------|
| **라우팅** | 1 | host-routing | `app.example.com`과 `api.example.com`을 다른 백엔드로 분기 |
| | 2 | path-routing | `/api/*`, `/web/*` 등 경로 패턴에 따른 백엔드 분기 |
| | 3 | header-routing | `X-Version: v2` 헤더 존재 시 특정 백엔드로 라우팅 |
| **TLS/보안** | 4 | tls-termination | Gateway에서 TLS 종료, 백엔드로 HTTP 전달 |
| | 5 | https-redirect | HTTP → HTTPS 자동 리다이렉션 (80 → 443) |
| | 6 | backend-tls | Gateway ↔ 백엔드 간 mTLS (사이드카 필요) |
| **트래픽 관리** | 7 | canary-traffic | 가중치 기반 트래픽 분배 (80% v1, 20% v2) |
| | 8 | rate-limiting | 초당/분당 최대 요청 수 제한 |
| | 9 | timeout-retry | 요청 타임아웃 및 실패 시 자동 재시도 |
| | 10 | session-affinity | 동일 클라이언트를 같은 백엔드로 유지 |
| **요청/응답 수정** | 11 | url-rewrite | `/old-api/*` → `/new-api/*` URL 경로 재작성 |
| | 12 | header-modifier | 요청/응답 헤더 추가·수정·삭제 |
| **고급 기능** | 13 | cross-namespace | `gateway-poc` → `backend-ns` 크로스 네임스페이스 라우팅 |
| | 14 | grpc-routing | HTTP/2 기반 gRPC 트래픽 처리 |
| | 15 | health-check | 백엔드 헬스체크 및 자동 장애 감지 |
| **성능/안정성** | 16 | load-test | 동시 20요청 부하 테스트 |
| | 17 | failover-recovery | Gateway Pod 재시작 후 복구 확인 |

## 100라운드 테스트 결과

### 전체 성공률

> 성공률 = `PASS / (PASS + FAIL)`, SKIP 제외

| 구현체 | 성공률 | PASS | FAIL | SKIP | 등급 |
|--------|--------|------|------|------|------|
| **NGINX Gateway Fabric** | **100%** | 15 | 0 | 2 | **A** |
| **Envoy Gateway** | **100%** | 15 | 0 | 2 | **A** |
| **Istio Gateway** | **100%** | 15 | 0 | 2 | **A** |
| **Cilium Gateway** | **100%** | 14 | 0 | 3 | **A** |
| Kong Gateway | 16.7% | 2 | 10 | 5 | F |
| Traefik Gateway | 8.3% | 1 | 11 | 5 | F |
| kgateway | N/A | N/A | N/A | 17 | N/A |

**4개 구현체(NGINX, Envoy, Istio, Cilium)가 100라운드에서 단 한 번도 실패하지 않았습니다.**

### 항목별 상세 결과

| # | 테스트 항목 | nginx | envoy | istio | cilium | kong | traefik |
|---|------------|:-----:|:-----:|:-----:|:------:|:----:|:-------:|
| 1 | host-routing | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| 2 | path-routing | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| 3 | header-routing | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| 4 | tls-termination | ✅ | ✅ | ✅ | ✅ | ⏭ | ⏭ |
| 5 | https-redirect | ✅ | ✅ | ✅ | ✅ | ⏭ | ⏭ |
| 6 | backend-tls | ⏭ | ⏭ | ⏭ | ⏭ | ⏭ | ⏭ |
| 7 | canary-traffic | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| 8 | rate-limiting | ✅ | ✅ | ✅ | ⏭ | ❌ | ❌ |
| 9 | timeout-retry | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| 10 | session-affinity | ⏭ | ⏭ | ⏭ | ⏭ | ⏭ | ⏭ |
| 11 | url-rewrite | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| 12 | header-modifier | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| 13 | cross-namespace | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| 14 | grpc-routing | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 15 | health-check | ✅ | ✅ | ✅ | ✅ | ⏭ | ⏭ |
| 16 | load-test | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| 17 | failover-recovery | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

✅ PASS · ❌ FAIL · ⏭ SKIP

### Skip 사유 정리

| 테스트 항목 | Skip 사유 | 해당 구현체 |
|------------|---------|------------|
| backend-tls | 사이드카 인젝션 미구성 (mTLS) | **전체** |
| session-affinity | 정책 미설정 | **전체** |
| tls-termination | Gateway Pod IP 미확보 | kong, traefik |
| https-redirect | 미구성 | kong, traefik |
| health-check | 미구성 | kong, traefik |
| rate-limiting | HTTP Rate Limiting 미지원 | cilium ([Feature Request #33500](https://github.com/cilium/cilium/issues/33500)) |
| kgateway 전체 | ARM64 아키텍처 미지원 | kgateway |

### Kong Gateway는 왜 실패했나?

```
Error: "no Route matched with those values"
```

HTTPRoute 리소스가 Kong 내부 설정으로 동기화되지 않는 문제입니다. "unmanaged gateway" 모드에서 Gateway API 호환성 이슈가 있으며, 기본 라우팅부터 실패하면서 연쇄적으로 대부분의 테스트가 실패했습니다.

추가로 KIC v3.5.3은 Kong Gateway v3.9와 설정 동기화 실패 문제가 있어 KIC v3.5를 유지해야 합니다.

### Traefik Gateway는 왜 실패했나?

```
Error: "404 page not found" / Warning: "Gateway not ready"
```

두 가지 근본 원인이 있습니다:

- **EntryPoints 포트 불일치**: 내부 포트(8000/8443)와 외부 포트(80/443) 매핑 문제
- **BackendTLSPolicy CRD 버전 불일치**: v1alpha3 vs v1

Gateway가 Ready 상태에 도달하지 못해 라우팅 자체가 불가능했습니다.

> Kong과 Traefik 모두 Ingress 구현체로서는 성숙한 제품이지만, **Gateway API 지원은 아직 발전 중**입니다.

## Rate Limiting은 어떻게 지원되나?

Rate Limiting은 **Gateway API 표준 스펙에 포함되어 있지 않습니다.** 각 구현체가 자체 방식으로 지원합니다.

| 구현체 | 지원 | 방식 | 특징 |
|--------|:----:|------|------|
| **Envoy Gateway** | **네이티브** | [`BackendTrafficPolicy`](https://gateway.envoyproxy.io/docs/tasks/traffic/backend-traffic-policy/rate-limit/) | Gateway API 스타일 선언적 설정, 가장 직관적 |
| NGINX Gateway Fabric | 제한적 | [`SnippetsFilter`](https://docs.nginx.com/nginx-gateway-fabric/traffic-management/snippets/) | 로우레벨 NGINX 설정 주입 방식 |
| Istio Gateway | 제한적 | [`EnvoyFilter`](https://istio.io/latest/docs/tasks/policy-enforcement/rate-limit/) | 로우레벨 Envoy 설정 주입 방식 |
| Cilium Gateway | **미지원** | N/A | [Issue #33500](https://github.com/cilium/cilium/issues/33500) 진행 중 |

**API 트래픽 제어가 중요하다면 Envoy Gateway의 `BackendTrafficPolicy`가 가장 Gateway API 친화적인 방식입니다.** NGINX와 Istio는 CRD를 통해 구성 가능하지만 전용 Rate Limiting API가 아닌 로우레벨 설정 주입 방식이라 복잡도가 높습니다.

## 상황별 어떤 구현체를 선택해야 할까?

| 상황 | 추천 구현체 | 이유 |
|------|------------|------|
| **안정성이 최우선** | NGINX Gateway Fabric | 검증된 운영 경험, 풍부한 문서, 대규모 커뮤니티 |
| **API Rate Limiting 필요** | Envoy Gateway | 선언적 CRD 기반 네이티브 Rate Limiting 지원 유일 |
| **서비스 메시 환경** | Istio Gateway | mTLS 자동화, Istio 컨트롤 플레인 통합 |
| **고성능/대용량 트래픽** | Cilium Gateway | eBPF 커널 레벨 처리, 네트워크 정책 통합 |
| **멀티 클라우드/하이브리드** | Envoy Gateway | xDS 프로토콜 기반 유연한 설정 |

## 마이그레이션 시 권장 사항

1. Ingress와 Gateway API를 **병행 운영**하며 점진적으로 전환
2. **스테이징 환경**에서 충분히 테스트 후 적용
3. 전환 기간 동안 **모니터링 강화**
4. 문제 발생 시 Ingress로 **롤백 계획** 준비

## 참고 사항

> 이 PoC는 **2025년 12월 5일**, ARM64(Apple Silicon) 기반 클러스터에서 진행되었습니다. 각 구현체의 버전이 이후 업데이트되면서 결과가 달라질 수 있으므로, 도입 검토 시에는 최신 버전으로 재검증하는 것을 권장합니다.

## 참고 자료

- [요즘IT 기사: 쿠버네티스 7개 주요 게이트웨이 기술 검증(PoC)하기](https://yozm.wishket.com/magazine/detail/3559/): 배경과 개념을 포함한 전체 내용
- [GitHub: gateway-PoC](https://github.com/sysnet4admin/Research/tree/main/gateway-PoC): 17개 테스트 자동화 스크립트 및 상세 결과
