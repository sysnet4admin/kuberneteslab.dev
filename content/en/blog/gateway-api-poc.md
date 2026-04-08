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

## Which Implementations Were Tested?

| Implementation | Version | Key Feature |
|----------------|---------|-------------|
| NGINX Gateway Fabric | v2.2.1 | Official Gateway API impl by F5 Networks |
| Envoy Gateway | v1.6.0 | CNCF graduated project, xDS protocol based |
| Istio Gateway | v1.28.0 | Service mesh integration, automated mTLS |
| Cilium Gateway | v1.18.4 | eBPF-based high-performance networking |
| Kong Gateway | v3.9 (KIC v3.5) | Enterprise API gateway |
| Traefik Gateway | v3.6.2 | Cloud-native reverse proxy |
| kgateway (Solo.io) | v2.1.1 | Excluded — no ARM64 support |

## What Was Tested?

17 test scenarios were executed over **100 rounds**.

| Category | Test Items |
|----------|-----------|
| Routing (3) | Host-based, path-based, header-based routing |
| TLS/Security (3) | TLS termination, HTTPS redirect, backend TLS/mTLS |
| Traffic Management (4) | Canary deployment, rate limiting, timeout/retry, session affinity |
| Request/Response Modification (2) | URL rewrite, header modification |
| Advanced Features (3) | Cross-namespace, gRPC routing, health check |
| Performance/Stability (2) | Load test (20 concurrent), failover recovery |

## 100-Round Test Results

### Overall Success Rates

| Implementation | Success Rate | PASS | FAIL | SKIP | Grade |
|----------------|-------------|------|------|------|-------|
| **NGINX Gateway Fabric** | **100%** | 15 | 0 | 2 | **A** |
| **Envoy Gateway** | **100%** | 15 | 0 | 2 | **A** |
| **Istio Gateway** | **100%** | 15 | 0 | 2 | **A** |
| **Cilium Gateway** | **100%** | 15 | 0 | 2 | **A** |
| Kong Gateway | 16.7% | 2 | 10 | 5 | F |
| Traefik Gateway | 8.3% | 1 | 11 | 5 | F |
| kgateway | N/A | - | - | 17 SKIP | - |

**Four implementations (NGINX, Envoy, Istio, Cilium) achieved zero failures across 100 rounds.**

### Why Did Kong Gateway Fail?

```
Error: "no Route matched with those values"
```

HTTPRoute resources failed to sync with Kong's internal configuration. In "unmanaged gateway" mode, Gateway API compatibility issues caused basic routing to fail, triggering cascading failures across most tests.

### Why Did Traefik Gateway Fail?

```
Error: "404 page not found" / "Gateway not ready"
```

Two root causes were identified:
- **EntryPoints port mismatch**: Internal ports (8000/8443) vs external ports (80/443) mapping issue
- **BackendTLSPolicy CRD version mismatch**: v1alpha3 vs v1

The Gateway never reached Ready state, making routing impossible.

> Both Kong and Traefik are mature Ingress implementations, but their **Gateway API support is still evolving**.

## How Is Rate Limiting Supported?

Rate limiting is **not included in the Gateway API standard spec.** However, all Tier 1 implementations support it through their own CRDs.

| Implementation | Supported | CRD Used | Characteristics |
|----------------|-----------|----------|----------------|
| Envoy Gateway | Yes | BackendTrafficPolicy | Gateway API style, most intuitive |
| NGINX Gateway Fabric | Yes | NginxProxy | NGINX config based |
| Istio Gateway | Yes | Telemetry | Istio control plane integrated |
| Cilium Gateway | Yes | CiliumClusterwideNetworkPolicy | eBPF network policy integration |

**If API traffic control matters, Envoy Gateway's BackendTrafficPolicy is the most Gateway API-friendly approach.**

## Which Implementation Should You Choose?

| Scenario | Recommended | Reason |
|----------|------------|--------|
| **Stability first** | NGINX Gateway Fabric | Proven ops experience, rich docs, large community |
| **API rate limiting needed** | Envoy Gateway | Gateway API style native rate limiting |
| **Service mesh environment** | Istio Gateway | Automated mTLS, Istio control plane integration |
| **High performance / high traffic** | Cilium Gateway | eBPF kernel-level processing, network policy integration |
| **Multi-cloud / hybrid** | Envoy Gateway | Flexible xDS protocol-based configuration |

## Migration Recommendations

1. Run Ingress and Gateway API **in parallel** with gradual transition
2. Test thoroughly in a **staging environment** first
3. **Strengthen monitoring** during the transition period
4. Prepare a **rollback plan** to Ingress in case of issues

## Note

> This PoC was conducted on **December 5, 2025**. Results may differ as each implementation has been updated since then. We recommend re-validating with the latest versions before adoption.

## References

- [yozm.wishket.com article: PoC of 7 Kubernetes Gateway Implementations](https://yozm.wishket.com/magazine/detail/3559/) — Full context including background and concepts
- [GitHub: gateway-PoC](https://github.com/sysnet4admin/Research/tree/main/gateway-PoC) — 17-test automation script and detailed results
