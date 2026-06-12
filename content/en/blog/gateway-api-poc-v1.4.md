---
title: "Passing Conformance Isn't Enough: Re-scoring 7 Gateway API Implementations from Scratch"
date: 2026-06-12
draft: false
tags: ["kubernetes", "gateway-api", "ingress", "conformance", "nginx", "envoy", "istio", "cilium", "kong", "traefik", "kgateway"]
categories: ["Kubernetes"]
description: "After Ingress NGINX retired, which Gateway API should you move to? We rebuilt last year's PoC around the official conformance model and re-measured 7 implementations from scratch. All 7 pass the required features, but their actual feature breadth splits from 6 to 13, and Kong and Traefik, which scored low last year, are now among those that pass."
summary: "We rebuilt last year's Gateway API PoC from the scoring model up and re-measured 7 implementations. All 7 pass official conformance, but the features you can actually use range from 6 to 13."
ShowToc: true
TocOpen: true
---

## Why Measure Again

In March 2026, Ingress NGINX reached end of support. With the most widely used Ingress implementation gone, the field is left with a single question: "So which Gateway API implementation should we move to?"

I took a first pass at that answer last year, running 7 implementations through 17 tests over 100 rounds and assigning A/F grades. But that scoring method had a structural flaw (an unsupported feature never cost any points). Implementation versions and the Gateway API standard have also moved on since. So this time, instead of simply running it again, I **rebuilt the scoring model around the official conformance framework** and started over on Gateway API v1.4. The conclusions changed quite a bit: the implementations that scored low last year are in a different position now.

The full numbers and reproduction steps live in the [GitHub repository](https://github.com/sysnet4admin/Research/tree/main/gateway-PoC). This post walks through **what I decided to measure and how, and which findings were interesting.**

## The Results at a Glance

Here is the summary of re-measuring 7 implementations (NGINX Gateway Fabric, hereafter NGF; Envoy Gateway; Istio; Cilium; Kong; Traefik; kgateway) on a live cluster.

First, a word on "conformant." In the Ingress era, behavior varied from one implementation to the next, so the same config often ran differently after a move. To curb that fragmentation, Gateway API runs an **official conformance test** that checks whether an implementation correctly implements the spec. Passing all of its required items makes an implementation **Core conformant**, which means that, at least for the required features, the same config behaves the same no matter which implementation you move to.

- **All 7 are Core conformant.** They pass all 7 required features, including Kong and Traefik, which scored low in last year's PoC.
- Where they diverge is **Extended feature breadth.** Of the 13 optional features, the number supported ranges from **6 to 13**. The conformance badge is the same, yet the features you can actually use differ by more than double.
- **Implementation-specific features** like rate limiting, external auth, and request body size limits sit outside conformance, so I left them out of the grade and compared them separately. This is where each implementation's character shows most.

The detailed tables are in the GitHub [rigor view](https://github.com/sysnet4admin/Research/blob/main/gateway-PoC/metrics/conformance-view/README_tables.md) and [starting-point view](https://github.com/sysnet4admin/Research/blob/main/gateway-PoC/metrics/migration-view/README_tables.md). From here, let's look at **why these results came out the way they did.**

## The Biggest Change from Last Year: From a Single Pass Rate to Conformance Tiers

Last year I weighted all 17 tests **equally**, computed a pass rate (PASS / (PASS + FAIL), excluding SKIP), and stamped each implementation A or F. That method had three structural unfairnesses.

- **Non-support barely registered in the score.** Because the pass rate counted only PASS and FAIL and dropped SKIP, not supporting a feature didn't cost points; it just fell out of the calculation. In the end, implementations with fewer features actually came out ahead.
- **Required and add-on features carried the same weight.** Host routing, which everyone must support, and rate limiting, which isn't even in the standard, counted as one item each, equally.
- **It couldn't tell 100% from 95%.** A binary A/F grade lumps "works except for one missing piece" together with "never worked from the start."

So this time, instead of inventing a new scoring system, I **mapped it directly onto the official Gateway API conformance model.** Rather than collapsing the 17 into one pass rate, I split each feature by where it sits in the spec.

- **Core (7):** required features every implementation must support. Miss even one and you are not conformant.
- **Extended (13):** standardized optional features. What isn't supported isn't penalized; it shows up as a difference in how many are supported (feature breadth).
- **Implementation-specific and non-functional:** outside the standard, so left out of the grade and compared only in a separate matrix.

The tiers aren't arbitrary; I fixed them from the Support markings in the kubernetes-sigs/gateway-api v1.4.0 source. As a result, scoring splits into **three axes** rather than one pass rate: whether it passes all of Core (conformance), how many Extended it supports (feature breadth), and which implementation-specific features it has (matrix). That shows far more than last year's single A/F letter.

I also revised the test set. I widened the graded Extended from an initial 5 to 13, and split the vaguely bundled SKIP into three: "unsupported / not instrumented / infrastructure issue."

## Why I Split One Measurement into Two Lenses

I split the same data along two questions, because a different question calls for different numbers.

- The **rigor view** asks "how faithfully does each implementation implement the spec?" It measures against the official Core/Extended model, adding quality indicators that conformance doesn't look at (weighted routing distribution convergence, success rate under load, failure recovery).
- The **starting-point view** asks "if I'm coming from Ingress NGINX, what carries over and what gets stuck?" It grades each annotation into four difficulty levels (standard / caution / vendor-locked / no equivalent) and records the actual output of running the ingress2gateway conversion tool.

An official conformance report only tells you "who is conformant," not "is it fine to move to the popular product I've been using?" That second question is exactly why I ran this measurement.

## Interesting Findings

### Why Kong and Traefik, Last Year's F Grades, Passed This Time

Kong and Traefik, which scored low in last year's PoC, both passed all 7 Core features this time, and kgateway, which I had to exclude back then, is now in the measurement. It wasn't one reason but three overlapping ones.

- **The ecosystem matured.** With BackendTLSPolicy promoted to the standard channel in Gateway API v1.4, the CRD version mismatch (v1alpha3 vs v1) that blocked Traefik's backend-tls cleared up. kgateway had no arm64 image last year and was excluded; now it supports arm64 and is included.
- **I measured the current recommended path.** I installed Kong via the KGO managed path instead of last year's KIC (unmanaged). That is the standard way to run Kong on Gateway API today.
- **I made the measurement more precise.** Kong pushes config as a single bundle, so a single unsupported feature in the mix got the whole thing rejected, taking even basic routing down with it. Once the harness isolated routes per feature, Core came back to life. For Traefik, the Gateway listener port and the internal entrypoint port were misaligned so it never reached Ready; aligning the ports fixed it.

In short, Kong's and Traefik's failures last year were not fundamental product limits. They were problems that disappeared as the standard matured, the install path settled, and the measurement got more precise.

### Conformance Doesn't Mean Equal Feature Breadth

The official Gateway API guidance is "pick a conformant implementation." Yet even among the 7 conformant ones, the Extended features actually supported range from 6 to 13. Envoy Gateway and Istio support all 13, while Kong stops at 6.

In other words, conformance is **a passing bar, not a guarantee that everything is the same.** Features used often in operations, like timeout, response header modification, and request mirroring, work on some implementations and not others. Choose by the badge alone and you'll hit "wait, why doesn't this work?" after the move.

### No One Enforces the Standard External-Auth Filter

This is the part anyone who used `auth-url` on Ingress NGINX for external auth will most want to know. Gateway API has a standard filter for external auth (GEP-1494) in experimental status, and yet **not a single implementation enforced it properly.**

Some rejected it or threw errors, and Cilium and kgateway don't implement the standard filter at all, so **traffic passed straight through with no authentication.** That's because GEP-1494 is still experimental and hasn't pinned down the failure behavior (reject or pass through). The conclusion is clear: external auth can't move to the standard filter yet, and you still have to rely on each implementation's CRD.

### The "Converts but Doesn't Work" Trap

ingress2gateway auto-converts more than 30 annotations. But **converting and actually working are two different things.** CORS annotations convert cleanly, yet in practice they passed on only 3 of the 7. Annotations that add headers, like `x-forwarded-prefix`, **vanished silently from the conversion output, without a single warning.**

That's why the starting-point view deliberately puts "converted" and "works" in separate columns. Even when the conversion tool passes something, you have to separately confirm it actually runs after the move.

### What's Hardest to Migrate

Some of what people used often on Ingress NGINX doesn't carry over to Gateway API as-is. The starting-point view sorts difficulty into four levels; here are the toughest.

- **Config snippets (`configuration-snippet`, `server-snippet`) have no replacement.** They inject raw nginx directives directly, and Gateway API deliberately offers no such injection path (the IngressNightmare CVE itself came from exactly this injection method). Common uses like header modification or timeouts are already absorbed into standard features, but if you leaned on arbitrary directive injection, you'll need to redesign.
- **mTLS client authentication (`auth-tls-*`) has no standard field in v1.4.** It was added in v1.5, so for now you either wait for v1.5 or rely on an implementation's CRD.
- **Session affinity (cookie sticky) is in the spec, but the cookie settings differ by implementation.** ingress2gateway also fails to convert this annotation and rejects it.

Checking whether these three are in your config before you move lets you head off "it converted, so why doesn't it work?" in advance.

### Once You've Chosen, How Fast Does It Recover?

I also measured operational metrics that conformance doesn't look at. **On a default install (one data-plane pod)**, I force-deleted the proxy pod taking traffic and, sending a request every 2 seconds, measured how long until traffic came back. This isn't a multi-replica HA failover; it measures how quickly a single pod recovers after it dies.

- **Istio and kgateway had zero downtime.** Not a single request failed.
- **NGF, Envoy Gateway, and Traefik recovered in about 13 seconds.**
- **Kong was the slowest, at about 34 seconds.**
- Cilium was excluded from this measurement because its shared eBPF data plane means an agent restart affects the whole cluster.

How can deleting a pod be zero-downtime? In Kubernetes, a pod doesn't shut off the instant it's told to delete. After receiving the termination signal it stays alive during the grace period, and meanwhile the Deployment spins up a new pod. If the old pod finishes serving the traffic it was handling (graceful drain) and that overlaps with the new pod coming up, there is no break as seen from outside. Istio and kgateway handed off cleanly; the ones that took 13 or 34 seconds had no such overlap, leaving a gap until the new pod was up. Repeating the same experiment three times gave nearly identical numbers (Kong was 34 seconds all three times).

In operations you normally run several replicas, and then for any implementation a single pod dying won't break traffic, because the rest absorb it. So this difference shows up where replicas can't hide it. In an environment where you can't easily add replicas, like a single-node edge cluster, this gap is exposed directly to users; and even with multiple replicas, Kong's 34 seconds shows up as the time for capacity to come back after a rolling update or node failure.

## So Which Implementation Should You Choose?

Since all 7 pass Core, the selection criteria move on to **feature breadth, data plane, and the ecosystem you already run.**

| Situation | Pick | Why |
|------|------|------|
| **You need the widest feature breadth** | Envoy Gateway, Istio | Support all standard Extended, and lead even on experimental-channel features |
| **The smoothest move from Ingress NGINX** | NGF | F5's official successor path, with deep operational experience and docs |
| **You already run the Cilium CNI** | Cilium | eBPF data plane, CNI and gateway in one |
| **You're going all the way to a service mesh** | Istio | Mesh and gateway integrated, automatic mTLS |
| **You already run Traefik or want simple operations** | Traefik | Automatic service discovery and a dashboard, easy setup |
| **You want Envoy's performance but a full mesh is too much** | kgateway | An Envoy-based gateway from the Gloo lineage, with a dedicated migration guide |
| **An edge-like environment where you can't add replicas** | Istio, kgateway | Only these two had no break while a pod died and came back (the rest had a 13 to 34 second gap) |
| **The API gateway ecosystem matters most** | Kong | A strong plugin ecosystem, though its standard Extended is the narrowest |

If you're evaluating adoption, remember one thing. This result is a **snapshot as of June 2026, on Gateway API v1.4.** Implementation versions move fast, and some non-support has already been resolved since the measurement (noted alongside the measured versions in the rigor view). When you use this as a reference, check once whether it still holds on the latest version available now.

One more thing. **The Gateway API version each implementation supports differs.** If you raise the CRDs ahead of what your controller supports, new resources can be ignored by the controller or end up unverified (when I reproduced it, an older controller skipped CRDs newer than the version it supports). As of mid-2026 most have caught up to v1.5, but how far each supports on a stable release varies. Before upgrading, always check the Gateway API version in each implementation's release notes. The reason I measured on v1.4 is that v1.4 was the version all 7 support on a stable release in common.

## Closing

The two lessons that came into sharpest focus in this re-measurement are these: one, that **conformance is only the starting line**, and two, that **the standard and the ecosystem evolve fast.** That the implementations which scored low last December all passed Core within half a year was a more valuable finding than any single line of a ranking table.

The measurement harness, scoring rubric, per-implementation install scripts, and ingress2gateway conversion evidence are all in the [GitHub repository](https://github.com/sysnet4admin/Research/tree/main/gateway-PoC). The edition at this point in time is preserved as-is on the [`gateway/v1.4` branch](https://github.com/sysnet4admin/Research/tree/gateway/v1.4).
