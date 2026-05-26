---
title: "Comparing 7 Kubernetes Gateway API Implementations: Which One Should You Choose?"
date: 2026-04-08
draft: false
tags: ["kubernetes", "gateway-api", "ingress", "poc", "nginx", "envoy", "istio", "cilium"]
categories: ["Kubernetes"]
description: "We tested 7 Gateway API implementations — NGINX Gateway Fabric, Envoy Gateway, Istio, Cilium, and more — across 17 test scenarios over 100 rounds ahead of Ingress NGINX retirement."
summary: "100-round PoC results and selection guide for 7 Kubernetes Gateway API implementations across 17 test scenarios"
ShowToc: true
TocOpen: true
---

## Ingress NGINX Is Retiring

In March 2026, **Ingress NGINX — the most widely used Ingress implementation — reaches end of support.** While the Ingress API itself remains, the retirement of its flagship implementation signals a shift to the **Gateway API**.

What makes Gateway API different from Ingress? The key difference is **role separation**. Infrastructure admins, cluster operators, and developers can configure their respective domains independently, offering greater expressiveness and extensibility.

> This post extends the [article published on yozm.wishket.com](https://yozm.wishket.com/magazine/detail/3559/) with **detailed test data and a selection guide** not covered in the original piece.

## Test Environment

### Cluster Overview

| Item | Details |
|------|---------|
| Kubernetes Version | v1.34.2 |
| Architecture | ARM64 (Apple Silicon) |
| OS | Ubuntu 22.04.5 LTS |
| Container Runtime | containerd 1.7.24 |
| Gateway API Version | v1.2.0 |
| CNI | Cilium v1.18.4 (eBPF, kube-proxy replacement) |

### Node Configuration

| Node | Role | IP | CPU | Memory |
|------|------|----|-----|--------|
| cp-k8s | control-plane | 192.168.1.10 | 4 vCPU | 3.8 GB |
| w1-k8s | worker | 192.168.1.101 | 4 vCPU | 7.8 GB |
| w2-k8s | worker | 192.168.1.102 | 4 vCPU | 7.8 GB |
| w3-k8s | worker | 192.168.1.103 | 4 vCPU | 7.8 GB |

**Total cluster resources**: 16 vCPU, 27.2 GB memory

### Gateway IP Assignments

| Implementation | GatewayClass | IP | Namespace |
|----------------|-------------|-----|-----------|
| NGINX Gateway Fabric | nginx | 192.168.1.11 | nginx-gateway |
| Envoy Gateway | eg | 192.168.1.12 | envoy-gateway-system |
| Istio Gateway | istio | 192.168.1.14 | istio-system |
| Cilium Gateway | cilium | 192.168.1.15 | kube-system |
| Kong Gateway | kong | 192.168.1.16 | kong |
| Traefik Gateway | traefik | 192.168.1.17 | traefik |
| kgateway | kgateway | — | ARM64 not supported, excluded |

All 7 Gateway implementations ran independently in the same cluster. Cilium was chosen as the CNI to include Cilium Gateway in the tests. With a different CNI, the remaining 6 implementations are unaffected.

### Cluster Architecture

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
│  │  • kube-proxy replacement  • Gateway API enabled  • VXLAN  │  │
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

### Backend Services

Four backend services were used across the test scenarios.

| Service | Role | Used In |
|---------|------|---------|
| `echo-v1` | Stable version | Canary: receives 80% of traffic |
| `echo-v2` | Canary version | Canary: receives 20% of traffic |
| `grpc` | gRPC server (HTTP/2) | gRPC routing test only |
| `backend-ns` | Separate namespace service | Cross-namespace routing test |

`echo-v1` and `echo-v2` are used across most tests including host/path/header routing, canary, and rate limiting. `grpc` is dedicated to the gRPC protocol test, and `backend-ns` is used exclusively for the cross-namespace scenario — routing traffic from the `gateway-poc` namespace Gateway into the `backend-ns` namespace.

## Which Implementations Were Tested?

| Implementation | Version | Key Feature |
|----------------|---------|-------------|
| NGINX Gateway Fabric | v2.2.1 | F5 open source, proven stability and rich documentation |
| Envoy Gateway | v1.6.0 | CNCF graduated, xDS-based, native rate limiting support |
| Istio Gateway | v1.28.0 | Service mesh integration, automated mTLS, CNCF graduated (2024) |
| Cilium Gateway | v1.18.4 | eBPF-based high performance, kernel-level processing, CNCF graduated (2023) |
| Kong Gateway | v3.9 (KIC v3.5) | Enterprise API gateway, rich plugin ecosystem |
| Traefik Gateway | v3.6.2 | Cloud-native reverse proxy, Let's Encrypt integration |
| kgateway (Solo.io) | v2.1.1 | CNCF Sandbox (2025), excluded — no ARM64 support |

### Why Each Implementation Was Selected

**NGINX Gateway Fabric**: The official Gateway API implementation from NGINX, which has the longest production track record in the web server and reverse proxy space. The most natural migration path for teams running Ingress NGINX.

**Envoy Gateway**: Built on Envoy Proxy (CNCF graduated 2018), featuring xDS protocol-based dynamic configuration and a rich filter chain. The only implementation with native declarative Rate Limiting via CRD.

**Istio Gateway**: Gateway API support from Istio, the de facto standard for service meshes. Envoy-based but integrated with the Istio control plane, enabling automated mTLS and traffic management.

**Cilium Gateway**: A high-performance implementation using eBPF for kernel-level packet processing. Integrates L3/L4/L7 with network policy. Requires Cilium CNI.

**Kong Gateway**: The enterprise API gateway market leader with a rich plugin ecosystem. Strong for API management but Gateway API support is still maturing.

**Traefik Gateway**: A cloud-native reverse proxy with automatic service discovery and Let's Encrypt integration. Gateway API support is progressing toward maturity.

## What Was Tested?

17 test scenarios were executed over **100 rounds**.

| Category | # | Test Item | Description |
|----------|---|-----------|-------------|
| **Routing** | 1 | host-routing | Route `app.example.com` and `api.example.com` to different backends |
| | 2 | path-routing | Route by URL path patterns like `/api/*`, `/web/*` |
| | 3 | header-routing | Route to specific backend when `X-Version: v2` header is present |
| **TLS/Security** | 4 | tls-termination | TLS termination at Gateway, forward HTTP to backend |
| | 5 | https-redirect | Automatic HTTP → HTTPS redirection (80 → 443) |
| | 6 | backend-tls | mTLS between Gateway and backend (requires sidecar) |
| **Traffic Management** | 7 | canary-traffic | Weight-based traffic split (80% v1, 20% v2) |
| | 8 | rate-limiting | Limit max requests per second/minute |
| | 9 | timeout-retry | Request timeout and automatic retry on failure |
| | 10 | session-affinity | Sticky routing — same client to same backend |
| **Request/Response** | 11 | url-rewrite | Rewrite URL paths: `/old-api/*` → `/new-api/*` |
| | 12 | header-modifier | Add, modify, or delete request/response headers |
| **Advanced** | 13 | cross-namespace | Route from `gateway-poc` to `backend-ns` namespace |
| | 14 | grpc-routing | HTTP/2-based gRPC traffic handling |
| | 15 | health-check | Backend health check and automatic failure detection |
| **Performance** | 16 | load-test | Load test with 20 concurrent requests |
| | 17 | failover-recovery | Verify recovery after Gateway Pod restart |

## 100-Round Test Results

### Overall Success Rates

> Success rate = `PASS / (PASS + FAIL)`, excluding SKIP

| Implementation | Success Rate | PASS | FAIL | SKIP | Grade |
|----------------|-------------|------|------|------|-------|
| **NGINX Gateway Fabric** | **100%** | 15 | 0 | 2 | **A** |
| **Envoy Gateway** | **100%** | 15 | 0 | 2 | **A** |
| **Istio Gateway** | **100%** | 15 | 0 | 2 | **A** |
| **Cilium Gateway** | **100%** | 14 | 0 | 3 | **A** |
| Kong Gateway | 16.7% | 2 | 10 | 5 | F |
| Traefik Gateway | 8.3% | 1 | 11 | 5 | F |
| kgateway | N/A | — | — | 17 | — |

**Four implementations (NGINX, Envoy, Istio, Cilium) achieved zero failures across all 100 rounds.**

### Detailed Results by Test Item

| # | Test Item | nginx | envoy | istio | cilium | kong | traefik |
|---|-----------|:-----:|:-----:|:-----:|:------:|:----:|:-------:|
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

### Skip Reasons

| Test Item | Reason | Affected |
|-----------|--------|----------|
| backend-tls | Sidecar injection not configured (mTLS) | **All** |
| session-affinity | Policy not configured | **All** |
| tls-termination | Gateway Pod IP not obtained | kong, traefik |
| https-redirect | Not configured | kong, traefik |
| health-check | Not configured | kong, traefik |
| rate-limiting | HTTP Rate Limiting not supported | cilium ([Issue #33500](https://github.com/cilium/cilium/issues/33500)) |
| kgateway all | ARM64 architecture not supported | kgateway |

### Why Did Kong Gateway Fail?

```
Error: "no Route matched with those values"
```

HTTPRoute resources failed to sync with Kong's internal configuration. In "unmanaged gateway" mode, Gateway API compatibility issues caused basic routing to fail, triggering cascading failures across most tests.

Additionally, KIC v3.5.3 has configuration sync failures with Kong Gateway v3.9 — staying on KIC v3.5 is recommended.

### Why Did Traefik Gateway Fail?

```
Error: "404 page not found" / Warning: "Gateway not ready"
```

Two root causes were identified:

- **EntryPoints port mismatch**: Internal ports (8000/8443) vs external ports (80/443)
- **BackendTLSPolicy CRD version mismatch**: v1alpha3 vs v1

The Gateway never reached Ready state, making routing impossible.

> Both Kong and Traefik are mature Ingress implementations, but their **Gateway API support is still evolving**.

## How Is Rate Limiting Supported?

Rate limiting is **not included in the Gateway API standard spec.** Each implementation handles it differently.

| Implementation | Support | Method | Notes |
|----------------|:-------:|--------|-------|
| **Envoy Gateway** | **Native** | [`BackendTrafficPolicy`](https://gateway.envoyproxy.io/docs/tasks/traffic/backend-traffic-policy/rate-limit/) | Declarative Gateway API-style config, most intuitive |
| NGINX Gateway Fabric | Limited | [`SnippetsFilter`](https://docs.nginx.com/nginx-gateway-fabric/traffic-management/snippets/) | Low-level NGINX config injection |
| Istio Gateway | Limited | [`EnvoyFilter`](https://istio.io/latest/docs/tasks/policy-enforcement/rate-limit/) | Low-level Envoy config injection |
| Cilium Gateway | **Not supported** | — | [Issue #33500](https://github.com/cilium/cilium/issues/33500) in progress |

**Envoy Gateway is the only implementation with native declarative Rate Limiting via `BackendTrafficPolicy`.** NGINX and Istio can achieve it through low-level config injection, but this is not a dedicated Rate Limiting API and adds complexity. Cilium currently does not support HTTP Rate Limiting.

## Which Implementation Should You Choose?

| Scenario | Recommended | Reason |
|----------|------------|--------|
| **Stability first** | NGINX Gateway Fabric | Proven ops experience, rich docs, large community |
| **API rate limiting needed** | Envoy Gateway | Only implementation with native declarative Rate Limiting CRD |
| **Service mesh environment** | Istio Gateway | Automated mTLS, Istio control plane integration |
| **High performance / high traffic** | Cilium Gateway | eBPF kernel-level processing, network policy integration |
| **Multi-cloud / hybrid** | Envoy Gateway | Flexible xDS protocol-based configuration |

## Migration Recommendations

1. Run Ingress and Gateway API **in parallel** with gradual transition
2. Test thoroughly in a **staging environment** first
3. **Strengthen monitoring** during the transition period
4. Prepare a **rollback plan** to Ingress in case of issues

## Note

> This PoC was conducted on **December 5, 2025**, on an ARM64 (Apple Silicon) cluster. Results may differ as each implementation has been updated since then. We recommend re-validating with the latest versions before adoption.

## References

- [yozm.wishket.com: PoC of 7 Kubernetes Gateway Implementations](https://yozm.wishket.com/magazine/detail/3559/) — Full context including background and concepts
- [GitHub: gateway-PoC](https://github.com/sysnet4admin/Research/tree/main/gateway-PoC) — 17-test automation scripts and detailed results
