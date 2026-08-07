---
title: "Port an MCP server to the stateless spec on Kubernetes: a step-by-step migration"
date: 2026-08-10
draft: true
tags: ["mcp", "model-context-protocol", "stateless", "agentgateway", "aaif", "migration", "kubernetes"]
categories: ["Kubernetes"]
description: "A walkthrough of migrating a session-based MCP server to the 2026-07-28 stateless spec on Kubernetes, with verbatim payloads, the manifests, and numbers from scale-out and pod-replacement runs."
summary: "Porting the transport to the v2 SDK is mostly a version bump. The real migration is deciding where handle state lives, and leaving it in pod memory brings the old failure back behind an HTTP 200 that transport retries never see."
ShowToc: true
TocOpen: true
---

The MCP 2026-07-28 revision removes protocol-level sessions. The `Mcp-Session-Id`
header is gone, every request carries what it needs, and anything that used to
live in a session now travels as an explicit handle in tool arguments.

That the change helps on Kubernetes is not a new claim. Hayden Sather showed
session survival counts across a two-replica Deployment, Vikram Vaswani paired
the new spec with a `sessionAffinity: None` Service, and the official AAIF
migration guide says outright that it does not cover Kubernetes deployment
patterns, pod replacement, or session-loss recovery. This walkthrough is the
operations companion to those: what the migration looks like end to end, with
the payloads, the manifests, and the numbers from running it.

Everything below is reproducible from the harness:
https://github.com/sysnet4admin/Research/tree/main/mcp-migration

## What you need

- A Kubernetes cluster with at least two worker nodes. Mine is 1.36.2 built
  with kubeadm, three nodes (one control plane, two workers with 2 CPU and 4GB
  each) on VirtualBox arm64, with Calico and MetalLB. kube-proxy is in its
  default iptables mode.
- Two servers to compare. The old-spec side is the official `server-everything`
  npm package pinned at `2026.7.4`, containerized locally. Note that its
  `initialize` response reports `serverInfo.version` as `2.0.0`; the v2 port is
  not merged upstream yet, so this is still the session-based server despite
  that string.
- The new-spec side is a port onto the Python SDK `mcp` 2.0.0.
- Python 3.11 or newer with `httpx` on your workstation, to drive load from
  outside the cluster.

```sh
./images/build_and_load.sh    # build both images, import into containerd
./k8s/deploy.sh               # namespace, code ConfigMap, Redis, both servers
kubectl --context <ctx> -n mcp-pilot get svc
```

`deploy.sh` supplies the new-spec server's code as a ConfigMap mounted at
`/app` rather than baking it into the image, so the image only carries
dependencies. If you follow the manifests by hand instead, that ConfigMap and
its volume mount are the step people miss. The images are side-loaded into
containerd rather than pushed to a registry, so `imagePullPolicy: Never`
applies and nothing can be pulled as a fallback. Load them **after** any cluster
reset; more on that at the end.

## Step 1: record what the old spec does before you change it

Run the capture against both servers. It performs one scripted sequence per
dialect and writes the request and response pairs verbatim:

```sh
python3 harness/capture.py http://<A_LB_IP>/mcp http://<B_LB_IP>/mcp payloads/
```

Both servers were at two replicas for this capture. The blocks below are the
recorded pairs with headers trimmed to the protocol-relevant ones; the full
pairs are in `payloads/payloads.md`.

The old spec opens with `initialize`, and the session ID comes back as a
response header:

```http
POST /mcp
Accept: application/json, text/event-stream
Content-Type: application/json

{"jsonrpc":"2.0","id":1,"method":"initialize",
 "params":{"protocolVersion":"2025-11-25","capabilities":{},
           "clientInfo":{"name":"capture","version":"0.1"}}}
```

```http
HTTP/1.1 200
content-type: text/event-stream
mcp-session-id: 1b9e50d6-06ad-4d6b-bab6-bfeba7ac836e
```

Then `notifications/initialized` (HTTP 202, empty body), and only then the
actual work, carrying the session header. Two round trips are spent before the
first tool call.

The interesting one comes when the same session ID travels over a new TCP
connection. The very first new connection already missed:

```http
HTTP/1.1 400

{"jsonrpc":"2.0","error":{"code":-32000,
 "message":"Bad Request: No valid session ID provided"}}
```

Nothing is broken. kube-proxy balances per connection, the session lives in one
pod's memory, and this connection reached a different pod. Every reconnect is a
fresh draw, and rollouts, autoscaling, and node drains all force reconnects.

## Step 2: port the transport

Build the server on the v2 SDK and drop the session plumbing. This is the whole
transport surface for a stateless tool (the file in the repository adds the
handle designs below):

```python
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

mcp = MCPServer("pilot-b")

@mcp.tool(name="echo")
def echo(message: str) -> str:
    """Echoes back the input string"""
    return f"Echo: {message}"

# Reaching the server by LoadBalancer IP means the Host header is an IP that
# the SDK's DNS-rebinding guard rejects, and allowed_hosts has no wildcard for
# a floating IP. Turning the guard off is the only available route on a private
# lab network; do not do this on a routable one.
security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
app = mcp.streamable_http_app(transport_security=security)
```

On the wire the client now sends the dialect in headers plus `params._meta`,
with no handshake:

```http
POST /mcp
MCP-Protocol-Version: 2026-07-28
Mcp-Method: tools/call
Mcp-Name: echo

{"jsonrpc":"2.0","id":1,"method":"tools/call",
 "params":{"name":"echo","arguments":{"message":"ping"},
           "_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28",
                    "io.modelcontextprotocol/clientInfo":{"name":"capture","version":"0.1"},
                    "io.modelcontextprotocol/clientCapabilities":{}}}}
```

```http
HTTP/1.1 200

{"jsonrpc":"2.0","id":1,
 "result":{"content":[{"text":"Echo: ping","type":"text"}],
           "isError":false,"resultType":"complete",
           "structuredContent":{"result":"Echo: ping"},
           "_meta":{"io.modelcontextprotocol/serverInfo":{"name":"pilot-b","version":""}}}}
```

`resultType` and the `serverInfo` in `_meta` are new requirements in this
revision, and the SDK fills them in. I ported this server against a beta SDK in
July and it ran unmodified on stable 2.0.0, including the changes that looked
risky on paper: error codes renumbered, `resultType` required, `ttlMs` and
`cacheScope` added to list results. If your server is built on an SDK rather
than hand-rolled HTTP, this step is mostly a version bump.

Deploy it behind a Service. Nothing here is session-aware:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-b
  namespace: mcp-pilot
  labels: { app: mcp-b }
spec:
  replicas: 2
  selector:
    matchLabels: { app: mcp-b }
  template:
    metadata:
      labels: { app: mcp-b }
    spec:
      containers:
        - name: server
          image: docker.io/mcp-pilot/b-server:2.0.0
          imagePullPolicy: Never
          ports:
            - containerPort: 8000
          resources:
            requests: { cpu: 500m, memory: 256Mi }
            limits: { cpu: 500m, memory: 512Mi }
          readinessProbe:
            tcpSocket: { port: 8000 }
            initialDelaySeconds: 3
            periodSeconds: 2
          volumeMounts:
            - name: code
              mountPath: /app
      volumes:
        - name: code
          configMap:
            name: b-server-code
---
apiVersion: v1
kind: Service
metadata:
  name: mcp-b
  namespace: mcp-pilot
spec:
  type: LoadBalancer
  selector: { app: mcp-b }
  ports:
    - port: 80
      targetPort: 8000
```

## Step 3: decide where handle state lives

This is the actual migration, and the SDK cannot do it for you. The spec
deliberately leaves handle persistence to the application, so the obvious port
keeps the state exactly where the session used to keep it:

```python
_COUNTERS: dict[str, int] = {}
_POD = os.environ.get("HOSTNAME", "unknown")

@mcp.tool(name="counter_create")
def counter_create() -> str:
    h = uuid.uuid4().hex
    _COUNTERS[h] = 0
    return h

@mcp.tool(name="counter_incr")
def counter_incr(handle: str) -> str:
    if handle not in _COUNTERS:
        raise ValueError(f"unknown handle (pod={_POD})")
    _COUNTERS[handle] += 1
    return str(_COUNTERS[handle])
```

Create a handle and it comes back as an opaque token,
`25610556fd114780a5fe3d6797a92182`. Use it over a new connection, and the second
one landed on a pod that had never seen it:

```http
HTTP/1.1 200

{"jsonrpc":"2.0","id":11,
 "result":{"content":[{"text":"Error executing tool counter_incr: unknown handle (pod=mcp-b-6c7c764cc7-v22m6)","type":"text"}],
           "isError":true,"resultType":"complete"}}
```

Same failure as the old spec, one layer up, and harder to notice: the status
code is 200 and the failure is a tool-level error, so transport-level retries
will not see it. Under load, at two replicas with a new connection per call,
100 rps offered for 30 seconds, three runs: 51.2 rps achieved (median) and
4,461 handle losses (summed).

A stateless transport does not make a stateless application.

## Step 4: give the handle somewhere to live

Two designs work. The first signs the value into the handle, so the server
stores nothing:

```python
_KEY = os.environ.get("HANDLE_KEY", "...").encode()

def _sign(value: int) -> str:
    sig = hmac.new(_KEY, str(value).encode(), hashlib.sha256).hexdigest()[:16]
    return f"v{value}:{sig}"

def _verify(handle: str) -> int:
    payload, sig = handle.rsplit(":", 1)
    value = int(payload[1:])
    if not hmac.compare_digest(
        sig, hmac.new(_KEY, str(value).encode(), hashlib.sha256).hexdigest()[:16]
    ):
        raise ValueError("bad handle signature")
    return value

@mcp.tool(name="hcounter_incr")
def hcounter_incr(handle: str) -> str:
    return _sign(_verify(handle) + 1)
```

**Every replica must hold the same key.** A per-pod value reproduces exactly the
failure this design is meant to remove, and it fails in the same invisible way.
The measurement runs relied on the shared default compiled into the image, which
is fine for a lab and wrong for anything else. In a real deployment, inject it
from one Secret:

```yaml
          env:
            - name: HANDLE_KEY
              valueFrom:
                secretKeyRef: { name: mcp-handle-key, key: key }
```

The handle is now readable state plus a signature: `v0:d6d16df58e19b715` on
create, `v1:a153e7227d1f3756` after one increment. Ten round trips on ten new
connections all succeeded, whichever pod answered. Sign the value rather than
just serializing it, or clients can hand you back whatever they like.

The second design puts the state in Redis and keeps the handle opaque:

```python
@mcp.tool(name="rcounter_create")
def rcounter_create() -> str:
    h = uuid.uuid4().hex
    _redis().set(f"ctr:{h}", 0, ex=3600)
    return h

@mcp.tool(name="rcounter_incr")
def rcounter_incr(handle: str) -> str:
    key = f"ctr:{handle}"
    if not _redis().exists(key):
        raise ValueError(f"unknown handle (pod={_POD})")
    return str(_redis().incr(key))
```

One trap if your Service is named `redis`: kubelet injects link-style
`REDIS_PORT=tcp://<ip>:6379` into every pod in the namespace, which collides
with the variable name a Redis client library expects. Name your own variables
something else.

```python
_REDIS = redis.Redis(
    host=os.environ.get("HANDLE_REDIS_HOST", "redis"),
    port=int(os.environ.get("HANDLE_REDIS_PORT", "6379")),
    socket_timeout=2,
)
```

Both designs measured the same: the full 100 rps offered, zero losses, 7.5ms
versus 7.9ms at p50. Pick by what the state actually is. Signed handles suit
small values you are willing to hand to the client. Redis suits anything large,
secret, or shared.

## Step 5: verify under scale-out, not at one replica

At one replica every design looks fine, including the broken one. Scale up and
drive load with a new connection per call. Connection mode is the setting that
decides whether you see anything: with keep-alive you stay pinned to a pod and
the problem hides.

```sh
kubectl --context <ctx> -n mcp-pilot scale deploy/mcp-b --replicas=4
kubectl --context <ctx> -n mcp-pilot rollout status deploy/mcp-b --timeout=240s

python3 harness/loadgen.py --url http://<LB_IP>/mcp \
  --dialect b --tool echo \
  --concurrency 16 --duration 30 --conn-mode close --rps 200 \
  --out cell.json
```

Same workload, same cluster, 200 rps offered for 30 seconds, three runs per
cell. Throughput below is the median of the three; loss counts are summed over
them:

| Setup | 1 replica | 2 replicas | 4 replicas |
|---|---|---|---|
| Old spec, new connection per call | 200.0 rps | 98.9 rps | 38.3 rps |
| Old spec, connection reuse | 200.0 rps | 181.4 rps | 119.2 rps |
| New spec | 200.0 rps | 200.0 rps | 200.0 rps |

The old spec loses throughput as replicas are added, down to 38.3 rps with
8,695 session losses out of 18,000 requests. Connection reuse softens it and
does not remove it; that row also varies run to run at four replicas
(154, 107, 119 rps), so read its direction rather than its exact value. The new
spec is unchanged at every replica count, zero losses, p50 steady at 6.2ms.

Two things about this table. It comes from a three-node VirtualBox cluster, so
the absolute numbers do not extrapolate. And 200 rps is deliberately below
saturation, roughly half the ceiling observed while piloting the harness. What
transfers to your cluster is the shape, not the values.

Then kill a pod during a run, which is what a rollout does anyway:

```sh
kubectl --context <ctx> -n mcp-pilot delete pod \
  $(kubectl --context <ctx> -n mcp-pilot get pod -l app=mcp-a \
    -o jsonpath='{.items[0].metadata.name}')
```

Across three 60-second runs at 100 rps with a pod killed at t=20s, the old spec
lost 667 sessions in total (421, 155, and 91 in the three runs) and the new spec
lost nothing in any of them. The two cells are not identically configured: the
old-spec cell echoes over reused connections, which is its most favourable mode,
while the new-spec cell exercises the HMAC counter with a new connection per
call. All six kills were verified to have actually landed.

## If you cannot migrate yet

A gateway that terminates sessions and routes them consistently keeps an
old-spec server working while you wait. With agentgateway v1.4.1, the backend
declares the routing mode:

```yaml
apiVersion: agentgateway.dev/v1alpha1
kind: AgentgatewayBackend
metadata:
  name: mcp-a-stateful
  namespace: mcp-pilot
spec:
  mcp:
    targets:
      - name: mcp-a
        selector:
          services:
            matchLabels:
              app: mcp-a
    sessionRouting: Stateful     # Stateless for a new-spec backend
```

The `selector` is required for stateful routing; a bare target name is not
enough for the gateway to find the backing Service.

Through the gateway, the same old-spec server at four replicas kept every
request served, with zero session losses, against 8,695 losses on the direct
path.
The absolute throughput of the two paths is not comparable, because the gateway
control plane and proxy consume worker CPU and those cells run only one server
at four replicas at a time. What the comparison answers is whether session
routing removes the losses, and it does.

Be clear about what this buys. The session state did not disappear, it moved
into the gateway, which becomes the component whose scaling and replacement you
now think about. The new spec posts the same numbers with none of that
machinery.

One version note if you tried this early: agentgateway v1.4.0-alpha.1 mangled
`params._meta`, so new-spec traffic could not pass through it end to end. That
was my blocker in July. v1.4.1, released the day after the spec, passes it
intact.

## Two traps worth writing down

**The measurement can lie before the code does.** My first full run showed the
new spec degrading across cells, 200 rps falling to 158. The server was fine.
Firing 200 new connections per second in back-to-back cells piles up conntrack
TIME_WAIT entries on the path, which have a 120-second timeout, and later cells
start paying SYN retransmits. The symptom was p99 climbing from 16ms to 1,008ms
while p50 barely moved. The same run also had an ordering bias: the runner
measured all the old-spec cells before the new-spec ones inside each replica
block, so the old spec got the clean conntrack table and the new spec inherited
the debris. If your load generator opens a connection per request, put a
cooldown between cells so nothing carries over, and consider alternating the
order so no arm gets the clean table every time. The harness now sleeps
`COOLDOWN` seconds, default 180; I kept the cell order and let the cooldown
remove the carry-over, then reran everything.

**Restoring a snapshot wipes the images you just loaded.** My runbook said build
images, then reset the cluster to baseline. The reset restores a VM snapshot
that predates the images, so doing it in that order silently removed every image
I had side-loaded, and with `imagePullPolicy: Never` and no registry there is
nothing to fall back to. The working order is: start the cluster, restore the
snapshot, then build and load images, then deploy.

## Checklist

1. Capture the old behavior first, including one failed request on a new
   connection. It is the clearest before/after evidence you will get.
2. Port the transport by moving to the v2 SDK. Expect this to be small.
3. Find every piece of state the session used to hold. This is the real work.
4. Choose per state: sign it into the handle with a key shared by every
   replica, or put it in shared storage. Never leave it in pod memory.
5. Verify at two or more replicas with a new connection per call. One replica
   proves nothing.
6. Kill a pod during a run and count what you lose.
7. If you need a bridge, use gateway session routing knowingly, and plan for
   the gateway's own redundancy.

The harness, the ported server with all three handle designs, the captured
payloads, and the full measurement tables are in the repository. The load
generator speaks both dialects, which is what made the before/after comparison
possible; there was no MCP-specific load tool when I started.
