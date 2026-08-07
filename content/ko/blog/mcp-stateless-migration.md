---
title: "MCP 서버를 스테이트리스 스펙으로 어떻게 옮기면 될까요?"
date: 2026-08-10
draft: true
tags: ["mcp", "model-context-protocol", "stateless", "agentgateway", "aaif", "migration", "kubernetes"]
categories: ["Kubernetes"]
description: "MCP 2026-07-28 스테이트리스 개정으로 세션 기반 서버를 옮기는 과정을 쿠버네티스에서 처음부터 끝까지 따라갑니다. 실제 요청과 응답, 매니페스트, 그리고 레플리카를 늘리고 파드를 죽여 가며 잰 수치를 함께 싣습니다."
summary: "전송 계층을 v2 SDK로 옮기는 일은 대체로 버전만 올리면 됩니다. 진짜 마이그레이션은 세션이 들고 있던 상태를 핸들로 어디에 둘지 정하는 데 있고, 파드 메모리에 두면 같은 실패가 HTTP 200 뒤에 숨어 되돌아옵니다."
ShowToc: true
TocOpen: true
---

MCP 2026-07-28 스테이트리스(stateless) 개정은 프로토콜 수준의 세션을
없앴습니다. `Mcp-Session-Id` 헤더가
사라졌고 요청마다 처리에 필요한 정보를 함께 담아 보내며 세션에 있던 상태는 이제
도구 인자에 실리는 핸들(handle)로 오갑니다.

이 변경이 쿠버네티스에서 도움이 된다는 이야기는 새롭지 않습니다. Hayden Sather가
레플리카 2개짜리 디플로이먼트에서 세션이 몇 개나 살아남는지 세어 보였고 Vikram Vaswani가 신
스펙과 `sessionAffinity: None` 서비스를 짝지어 보여 줬습니다. AAIF 공식 마이그레이션
가이드에는 쿠버네티스 배포 방식과 파드 교체, 세션 유실 복구를 다루지 않는다고
적혀 있습니다. 이 글에서는 그 문서들이 다루지 않은 운영 쪽을 이어서 다뤄 보겠습니다. 이관이 처음부터 끝까지
어떻게 되는지를 페이로드와 매니페스트, 그리고 실제로 돌려서 나온 수치로
따라갑니다.

아래 내용은 모두 [GitHub 저장소](https://github.com/sysnet4admin/Research/tree/main/mcp-migration)의
하네스로 재현할 수 있습니다.

## 준비물

- 워커 노드가 2대 이상인 쿠버네티스 클러스터. 여기서는 kubeadm으로 만든 1.36.2에
  노드 3대(컨트롤플레인 1, 워커 2. 워커는 2 CPU와 4GB)를 VirtualBox arm64에
  올렸고 Calico와 MetalLB를 씁니다. kube-proxy는 기본값인 iptables 모드입니다.
- 비교할 서버 두 대. 구 스펙 쪽은 공식 `server-everything` npm 패키지의
  `2026.7.4`를 로컬에서 컨테이너로 만든 것입니다. 이 서버의 `initialize` 응답이
  `serverInfo.version`을 `2.0.0`으로 보고하는데, v2 포팅이 아직 업스트림에
  병합되지 않아서 그 문자열과 달리 여전히 세션 기반 서버입니다.
- 신 스펙 쪽은 Python SDK `mcp` 2.0.0으로 포팅한 서버입니다.
- 부하를 클러스터 밖에서 주기 위해 작업용 컴퓨터에 Python 3.11 이상과 `httpx`가
  필요합니다.

```sh
./images/build_and_load.sh    # 두 이미지를 빌드해 containerd에 적재
./k8s/deploy.sh               # 네임스페이스, 코드 컨피그맵, Redis, 두 서버
kubectl --context <ctx> -n mcp-pilot get svc
```

`deploy.sh`는 신 스펙 서버의 코드를 이미지에 굽지 않고 컨피그맵(ConfigMap)으로
만들어 `/app`에 마운트합니다. 이미지에는 의존성만 들어 있습니다. 매니페스트를 손으로
따라 적용한다면 이 컨피그맵과 볼륨 마운트가 빠뜨리기 쉬운 부분입니다. 이미지는
레지스트리에 올리지 않고 containerd에 직접 적재하므로 `imagePullPolicy: Never`가
걸려 있고 받아 올 곳이 없습니다. 클러스터를 초기화했다면 그 **뒤에** 적재해야
합니다. 이유는 글 끝에서 다룹니다.

## 1단계: 바꾸기 전에 구 스펙이 무엇을 하는지 기록합니다

두 서버에 캡처를 돌립니다. 구 스펙과 신 스펙 각각 정해진 순서로 한 번씩 호출하고
요청과 응답을 원문 그대로 남깁니다.

```sh
python3 harness/capture.py http://<A_LB_IP>/mcp http://<B_LB_IP>/mcp payloads/
```

이 캡처를 뜰 때 두 서버 모두 레플리카가 2개였습니다. 아래 블록은 기록된 쌍에서
프로토콜과 관련된 헤더만 남긴 것이고 전체는 `payloads/payloads.md`에 있습니다.

구 스펙은 `initialize`로 시작하고 세션 ID가 응답 헤더로 옵니다.

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

그다음 `notifications/initialized`(HTTP 202, 빈 본문)를 보내고 그러고 나서야
세션 헤더를 달고 실제 일을 시작합니다. 첫 도구 호출 전에 왕복 2회를 씁니다.

여기서 볼 것은 같은 세션 ID를 새 TCP 연결로 보냈을 때입니다. 첫 새 연결에서 바로
어긋났습니다.

```http
HTTP/1.1 400

{"jsonrpc":"2.0","error":{"code":-32000,
 "message":"Bad Request: No valid session ID provided"}}
```

그렇다면 왜 이런 응답이 왔을까요? 고장이 난 것이 아닙니다. kube-proxy는 연결
단위로 분배하고 세션은 파드 하나의
메모리에 있는데, 이 연결이 다른 파드로 전달된 것입니다. 재연결은 매번 새로
뽑는 것과 같고 롤아웃과 오토스케일링, 노드 드레인이 모두 재연결을 일으킵니다.

## 2단계: 전송 계층을 옮깁니다

v2 SDK로 서버를 만들고 세션을 다루던 부분을 걷어냅니다. 스테이트리스 도구
하나에 필요한 전송 계층은 이게 전부입니다. 저장소의 파일에는 아래에서 다룰 핸들
구현이 더 붙어 있습니다.

```python
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

mcp = MCPServer("pilot-b")

@mcp.tool(name="echo")
def echo(message: str) -> str:
    """Echoes back the input string"""
    return f"Echo: {message}"

# LoadBalancer IP로 접근하면 Host 헤더가 IP라서 SDK의 DNS 리바인딩 보호가
# 거절하는데, allowed_hosts는 유동 IP를 위한 와일드카드를 지원하지 않는다.
# 사설망에서는 보호를 끄는 것이 유일한 방법이다. 공인망에서는 이렇게 하면 안 된다.
security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
app = mcp.streamable_http_app(transport_security=security)
```

이제 클라이언트는 신 스펙임을 헤더와 `params._meta`에 실어 보내고 핸드셰이크는
없습니다.

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

`resultType`과 `_meta`의 `serverInfo`는 이번 개정에서 새로 필수가 된 항목인데
SDK가 채워 줍니다. 저는 7월에 베타 SDK로 이 서버를 포팅했고 안정 버전 2.0.0에서
수정 없이 그대로 돌았습니다. 문서로만 보면 위험해 보이던 변경들, 그러니까 오류
코드 번호가 다시 매겨진 것과 `resultType`이 필수가 된 것, 목록 응답에 `ttlMs`와
`cacheScope`가 추가된 것도 마찬가지였습니다. 서버를 raw HTTP가 아니라 SDK 위에
만들었다면 이 단계는 대체로 버전만 올리면 되는 수준입니다.

서비스 뒤에 배포합니다. 여기에 세션을 아는 설정은 하나도 없습니다.

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

## 3단계: 핸들 상태를 어디에 둘지 정해야 합니다

여기서부터가 실제 마이그레이션이고 SDK가 대신해 줄 수 없는 부분입니다. 스펙은
핸들을 어디에 얼마나 보관할지를 일부러 정하지 않고 애플리케이션이 정하도록
남겨 두었습니다. 그래서 가장 손이 덜 가는 포팅은 세션이 있던 자리에 상태를
그대로 두는 것입니다.

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

핸들을 만들면 `25610556fd114780a5fe3d6797a92182`처럼 뜻을 알 수 없는 토큰이
돌아옵니다.
이걸 새 연결로 다시 쓰자 두 번째 연결은 그 핸들을 가지고 있지 않은 파드로
전달됐습니다.

```http
HTTP/1.1 200

{"jsonrpc":"2.0","id":11,
 "result":{"content":[{"text":"Error executing tool counter_incr: unknown handle (pod=mcp-b-6c7c764cc7-v22m6)","type":"text"}],
           "isError":true,"resultType":"complete"}}
```

이렇게 구 스펙과 같은 실패가 한 층 위에서 일어났고 알아채기는 오히려 더
어렵습니다. 상태 코드는 200이고 실패는 도구 수준 오류라서 전송 계층의 재시도가
이걸 보지 못하기 때문입니다. 따라서 부하를 주면 수치가 이렇게 나옵니다.
레플리카 2개에 호출마다 새 연결, 목표 100rps로 30초씩 3회 측정해서 실제
처리량은 51.2rps(중앙값)이고 핸들 유실은 4,461건(합)입니다.

전송 계층이 스테이트리스가 됐다고 해서 애플리케이션까지 스테이트리스가 되는
것은 아닙니다. 세션이 들고 있던 상태가 핸들로 이름만 바뀌었을 뿐, 그 값을
어디에 둘지는 여전히 만드는 사람이 정해야 하기 때문입니다.

## 4단계: 핸들 상태를 보관할 곳을 정합니다

설계는 두 가지로 나누어 볼 수 있습니다. 첫째는 값을
HMAC(Hash-based Message Authentication Code, 해시 기반 메시지 인증 코드)으로
서명해 핸들에 담아서 서버가 아무것도 보관하지 않는 방식입니다.

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

**모든 레플리카가 같은 키를 가져야 합니다.** 파드마다 값이 다르면 이 설계가
없애려던 실패가 그대로 재현되고 똑같이 눈에 안 띄는 방식으로 실패합니다. 측정할
때는 이미지에 담긴 공유 기본값을 그대로 썼는데, 테스트 환경에서는 문제가 없지만 실제 서비스에서는
이렇게 하시면 안 됩니다. 실제로 배포한다면 시크릿(Secret) 하나에서 주입합니다.

```yaml
          env:
            - name: HANDLE_KEY
              valueFrom:
                secretKeyRef: { name: mcp-handle-key, key: key }
```

이제 핸들은 읽을 수 있는 상태에 서명이 붙은 형태입니다. 만들면
`v0:d6d16df58e19b715`이고 한 번 올리면 `v1:a153e7227d1f3756`이 됩니다. 새 연결로
10회 왕복하는 동안 어느 파드가 받았든 전부 처리됐습니다. 값을 그냥 직렬화하지
말고 서명해야 합니다. 안 그러면 클라이언트가 아무 값이나 만들어 보낼 수 있습니다.

둘째는 상태를 Redis에 두고 핸들은 불투명한 키로 두는 방식입니다.

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

서비스 이름을 `redis`로 지었다면 함정이 하나 있습니다. kubelet이 같은
네임스페이스의 모든 파드에 `REDIS_PORT=tcp://<ip>:6379` 형태의 링크 스타일
변수를 넣어 주는데, 이 이름이 Redis 클라이언트 라이브러리가 사용하는 변수
이름과 겹칩니다. 직접 쓰는 변수는 다른 이름으로 짓습니다.

```python
_REDIS = redis.Redis(
    host=os.environ.get("HANDLE_REDIS_HOST", "redis"),
    port=int(os.environ.get("HANDLE_REDIS_PORT", "6379")),
    socket_timeout=2,
)
```

두 설계의 측정값은 같았습니다. 목표 100rps를 전부 달성했고 유실 0에 p50은 7.5ms
대 7.9ms입니다. 그래서 어느 쪽을 고를지는 보관할 상태의
성격에 따라 정하면 됩니다. 서명 핸들은 클라이언트에게 넘겨도 되는 작은 값에
적합하고 Redis는 값이 크거나 비밀이거나 여러 곳에서 공유해야 하는 경우에
씁니다.

## 5단계: 레플리카 1개가 아니라 스케일아웃에서 확인해 보겠습니다

레플리카가 1개면 잘못된 설계까지 포함해 전부 멀쩡해 보입니다. 스케일아웃
(scale-out)을 한 다음 호출마다
새 연결을 여는 방식으로 부하를 줍니다. 여기서 연결을 어떻게 여는지에 따라 문제가 보이기도 하고 보이지 않기도 합니다.
keep-alive를 쓰면 연결이 파드 하나에 고정되기 때문에 문제가 겉으로 나타나지
않습니다.

```sh
kubectl --context <ctx> -n mcp-pilot scale deploy/mcp-b --replicas=4
kubectl --context <ctx> -n mcp-pilot rollout status deploy/mcp-b --timeout=240s

python3 harness/loadgen.py --url http://<LB_IP>/mcp \
  --dialect b --tool echo \
  --concurrency 16 --duration 30 --conn-mode close --rps 200 \
  --out cell.json
```

같은 워크로드를 같은 클러스터에서 목표 200rps로 30초씩, 셀마다 3회 돌렸습니다.
아래 처리량은 3회 중앙값이고 유실 건수는 3회 합입니다.

| 구성 | 레플리카 1 | 레플리카 2 | 레플리카 4 |
|---|---|---|---|
| 구 스펙, 호출마다 새 연결 | 200.0rps | 98.9rps | 38.3rps |
| 구 스펙, 연결 재사용 | 200.0rps | 181.4rps | 119.2rps |
| 신 스펙 | 200.0rps | 200.0rps | 200.0rps |

구 스펙은 레플리카를 늘릴수록 처리량이 줄어서 4개에서 38.3rps가 되고 요청
18,000건 중 세션 유실이 8,695건입니다. 연결을 재사용하면 정도는 덜하지만
없어지지는 않습니다. 그 행은 레플리카 4에서 회차 편차도 큽니다(154, 107,
119rps). 정확한 값보다 방향을 보는 편이 맞습니다. 신 스펙은 모든 레플리카
수에서 그대로이고 유실 0에 p50도 6.2ms로 일정합니다.

다만 이 표를 보실 때 함께 봐 주셔야 할 부분이 있습니다. 노드 3대짜리
VirtualBox 클러스터에서 나온 값이라 절대 수치는 다른 환경으로 옮겨 해석하면 안 됩니다. 그리고 200rps는 일부러
포화 아래로 잡은 값으로, 하네스를 시험하며 관측한 상한의 절반 정도입니다. 다른 클러스터에서도 같게 나타날 것은 절대
수치보다 경향 쪽이라고 보시면 됩니다.

그다음으로 실행 중에 파드를 강제로 종료해 봅니다. 롤아웃을 하면 어차피
일어나는 일입니다.

```sh
kubectl --context <ctx> -n mcp-pilot delete pod \
  $(kubectl --context <ctx> -n mcp-pilot get pod -l app=mcp-a \
    -o jsonpath='{.items[0].metadata.name}')
```

100rps로 60초씩 3회 돌리며 20초 시점에 파드를 종료했더니 구 스펙은 세션을 모두
667개 잃었고(회차별로 421, 155, 91), 신 스펙은 세 번 다 하나도 잃지 않았습니다.
두 셀의 설정은 같지 않습니다. 구 스펙 셀은 연결을 재사용하며 echo를 부르는데 이게
구 스펙에 가장 유리한 조건이고 신 스펙 셀은 호출마다 새 연결로 HMAC 카운터를
씁니다. 여섯 번의 종료가 모두 실제로 이뤄진 것은 확인했습니다.

## 아직 옮길 수 없다면

세션을 종단하고 일관되게 라우팅하는 게이트웨이를 두면 그동안 구 스펙 서버를
지탱할 수 있습니다. agentgateway v1.4.1에서는 백엔드가 라우팅 방식을 선언합니다.

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
    sessionRouting: Stateful     # 신 스펙 백엔드는 Stateless
```

`selector`는 Stateful 라우팅에 필수입니다. 타깃 이름만으로는 게이트웨이가 뒤에
있는 서비스를 찾지 못합니다.

게이트웨이를 거치자 같은 구 스펙 서버가 레플리카 4에서 요청을 하나도 놓치지 않고
세션 유실 0이었습니다. 직접 경로에서는 8,695건이 났던 조건입니다. 두 경로의 절대
처리량은 비교하면 안 됩니다. 게이트웨이 컨트롤 플레인과 프록시가 워커 CPU를 쓰기
때문에 그 셀들은 한 번에 한 서버만 레플리카 4로 올려서 쟀습니다. 이 비교로 확인하려던 것은 세션
라우팅이 유실을 없애 주는가였고 실제로 없앴습니다.

물론 무엇을 얻는 것인지는 분명히 해 둘 필요가 있습니다. 세션 상태가 사라진 것이
아니라 게이트웨이로 옮겨 갔고 이제 스케일과 교체를 걱정해야 할 대상이
게이트웨이가 됩니다. 신 스펙은 그런 장치 없이 같은 수치를 냅니다.

일찍 시도해 본 분을 위해 버전을 하나 밝힙니다. agentgateway v1.4.0-alpha.1은
`params._meta`를 훼손해서 신 스펙 트래픽이 게이트웨이를 통과하지 못했습니다.
7월에 제가 막혔던 지점입니다. 스펙 다음 날 나온 v1.4.1은 온전히 통과시킵니다.

## 측정하며 겪은 함정

**코드에 문제가 생기기 전에 측정값이 먼저 틀릴 수 있습니다.** 첫 전체 측정에서 신 스펙이
셀을 거치며 200rps에서 158rps로 내려갔습니다. 서버는 멀쩡했습니다. 초당 200개의
새 연결을 셀마다 연이어 만들면 경로에 conntrack TIME_WAIT 항목이 쌓이는데 이게
120초 동안 남아서 뒤 셀이 TCP SYN 재전송 비용을 물게 됩니다. 증상은 p50은 거의
그대로인데 p99가 16ms에서 1,008ms로 뛰는 것이었습니다. 같은 측정에는 순서 편향도
겹쳐 있었습니다. 러너가 레플리카 블록마다 구 스펙 셀을 먼저 다 돌리고 신 스펙을
나중에 돌려서 구 스펙만 깨끗한 conntrack 테이블에서 측정된 것입니다. 부하
생성기가 요청마다 연결을 연다면 셀 사이에 쿨다운을 넣어 앞 셀이 남긴 것이 넘어가지
않게 하고 한쪽만 매번 깨끗한 상태를 받지 않도록 순서를 번갈아 두는 것도 좋습니다.
하네스는 이제 `COOLDOWN` 초(기본 180)를 쉽니다. 저는 셀 순서는 그대로 두고
쿨다운으로 넘어감을 없앤 뒤 전체를 다시 쟀습니다.

**스냅샷을 복원하면 방금 적재한 이미지가 지워집니다.** 제 실행 순서 문서에는
이미지를 빌드한 다음 클러스터를 기준 상태로 초기화한다고 적혀 있었습니다.
초기화는 이미지보다 앞선 시점의 VM 스냅샷을 복원하는 것이라, 그 순서로 하면
적재한 이미지가 지워집니다. 이때 별도의 오류가 나지 않아서 배포 단계에
가서야 알게 됩니다. `imagePullPolicy: Never`에 레지스트리도
없으니 받아 올 곳이 없습니다. 맞는 순서는 클러스터를 올린 다음 스냅샷을 복원하고
그다음 이미지를 빌드해 적재한 뒤 마지막에 배포하는 것입니다.

## 점검 목록

1. 바꾸기 전에 구 스펙의 동작을 먼저 기록합니다. 새 연결에서 실패한 요청 하나를
   함께 남기면 전후 대조가 가장 분명해집니다.
2. v2 SDK로 옮겨 전송 계층을 포팅합니다. 이 단계에서 손볼 곳은 많지 않을
   것입니다.
3. 세션이 들고 있던 상태를 하나도 빠짐없이 찾습니다. 여기서부터가 실제로 손이
   많이 가는 부분입니다.
4. 상태마다 정합니다. 모든 레플리카가 공유하는 키로 서명해 핸들에 담거나, 공유
   저장소에 둡니다. 파드 메모리에는 두지 않습니다.
5. 레플리카 2개 이상에서 호출마다 새 연결로 확인합니다. 레플리카가 1개면
   잘못된 설계도 정상으로 보이기 때문에 아무것도 확인할 수 없습니다.
6. 실행 중에 파드를 죽여 보고 무엇을 잃는지 셉니다.
7. 당장 옮길 수 없는 상황이라면 게이트웨이 세션 라우팅을 임시로 쓰되 무엇을
   옮기는 것인지 알고 써야 하며 그 게이트웨이의 이중화도 함께 계획합니다.

하네스와 핸들 설계 3종이 든 포팅 서버, 캡처한 페이로드, 측정 표 전체를 저장소에
공개해 두었으니 참고하시기 바랍니다. 부하 생성기가 구 스펙과 신 스펙을 모두 지원하는 덕분에 전후 비교가
가능했습니다.
시작할 때는 MCP 전용 부하 도구가 없었습니다. 다른 환경에서 재현해 보신 결과가
있다면 알려주시기 바랍니다.
