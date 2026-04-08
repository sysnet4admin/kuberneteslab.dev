---
title: "[샘플 2] 그린 테마"
date: 2026-04-08T10:01:00
draft: false
tags: ["sample"]
categories: ["sample"]
summary: "차분한 그린 계열 색상 샘플"
---

## 이것은 h2 소제목입니다

일반 본문 텍스트입니다. Gateway API는 Ingress API를 대체하는 차세대 표준으로, 역할 분리와 확장성이 핵심입니다.

### 이것은 h3 소제목입니다

| 구현체 | 성공률 | 등급 |
|--------|--------|------|
| NGINX Gateway Fabric | 100% | A |
| Envoy Gateway | 100% | A |
| Kong Gateway | 16.7% | F |

> 이 PoC는 2025년 12월 5일에 진행되었습니다. 각 구현체의 버전이 이후 업데이트되면서 결과가 달라질 수 있습니다.

[요즘IT 기사 링크](https://yozm.wishket.com/magazine/detail/3559/)에서 더 자세한 내용을 확인할 수 있습니다.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: example-gateway
spec:
  gatewayClassName: nginx
```

- 안정성 우선 → **NGINX Gateway Fabric**
- API 트래픽 제어 → **Envoy Gateway**
- 서비스 메시 → **Istio Gateway**
