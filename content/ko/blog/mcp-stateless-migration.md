---
title: "MCP 서버를 스테이트리스 스펙으로 어떻게 옮기면 될까요?"
date: 2026-08-18
draft: false
tags: ["mcp", "model-context-protocol", "stateless", "agentgateway", "aaif", "migration", "kubernetes"]
categories: ["Kubernetes"]
description: "MCP 2026-07-28 스테이트리스 개정으로 세션 기반 서버를 옮기는 과정을 쿠버네티스에서 처음부터 끝까지 따라갑니다. 실제 요청과 응답, 매니페스트, 그리고 레플리카를 늘리고 파드를 죽여 가며 잰 수치를 함께 싣습니다."
summary: "전송 계층을 v2 SDK로 옮기는 일은 대체로 버전만 올리면 됩니다. 진짜 마이그레이션은 세션이 들고 있던 상태를 핸들로 어디에 둘지 정하는 데 있고 파드 메모리에 두면 같은 실패가 HTTP 200 뒤에 숨어 되돌아옵니다."
ShowToc: true
TocOpen: true
---

MCP 2026-07-28 스테이트리스(stateless) 개정은 프로토콜 수준의 세션을 없앴습니다.
`Mcp-Session-Id` 헤더가 사라졌고 요청마다 처리에 필요한 정보를 함께 담아 보냅니다.
세션에 있던 상태는 이제 도구 인자에 실리는 핸들(handle)로 오갑니다.

이 변경이 쿠버네티스에서 도움이 된다는 이야기는 새롭지 않습니다. Hayden Sather가
레플리카 2개짜리 디플로이먼트에서 세션이 몇 개나 살아남는지 세어 보였고 Vikram
Vaswani가 신 스펙과 `sessionAffinity: None` 서비스를 짝지어 보여 줬습니다. AAIF
공식 마이그레이션 가이드에는 쿠버네티스 배포 방식과 파드 교체, 세션 유실 복구를
다루지 않는다고 적혀 있습니다. 이 글에서는 그 문서들이 다루지 않은 운영 쪽을
이어서 다뤄 보겠습니다. 마이그레이션이 처음부터 끝까지 어떻게 되는지를 페이로드와
매니페스트, 그리고 실제로 돌려서 나온 수치로 따라갑니다.

참고로 전환이 강제되는 시점은 없고 SDK가 기본으로 양쪽을 지원하므로 구 스펙에
그대로 있어도 됩니다. 여기서는 옮기기로 정한 뒤의 절차를 다룹니다.

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
docker info > /dev/null       # 무엇보다 데몬이 떠 있어야 한다
./images/build_and_load.sh    # 두 이미지를 빌드해 containerd에 적재
./k8s/deploy.sh               # 네임스페이스, 코드 컨피그맵, Redis, 두 서버
kubectl --context <ctx> -n mcp-pilot get svc
```

첫 줄은 형식이 아닙니다. Docker 데몬을 손으로 켜야 하는 환경이라면(저는 colima를
씁니다) 스냅샷을 복원하고 빌드가 실패했는데도 배포까지 진행되기 쉽습니다. 그러면
받아 올 레지스트리가 없어서 파드가 `ErrImageNeverPull`에 걸립니다. 무인 실행 한
회차를 이것 때문에 전부 잃었습니다.

`deploy.sh`는 신 스펙 서버의 코드를 이미지에 굽지 않고 컨피그맵(ConfigMap)으로
만들어 `/app`에 마운트합니다. 이미지에는 의존성만 들어 있습니다. 매니페스트를 손으로
따라 적용한다면 이 컨피그맵과 볼륨 마운트가 빠뜨리기 쉬운 부분입니다. 이미지는
레지스트리에 올리지 않고 containerd에 직접 적재하므로 `imagePullPolicy: Never`가
걸려 있고 받아 올 곳이 없습니다. 클러스터를 초기화(스냅샷 복원)했다면 그 **뒤에** 적재해야
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
뽑는 것과 같고 롤아웃과 노드 드레인, 오토스케일링의 축소가 모두 재연결을 일으킵니다.

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
# IP를 고정해 allowed_hosts에 등록하면 보호를 켠 채 통과할 수 있지만 사설
# 측정망에서는 끄는 것이 가장 간단하다. 공인망에서는 이렇게 하면 안 된다.
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
SDK가 채워 줍니다. 목록 응답의 `ttlMs`와 `cacheScope`도 마찬가지입니다. 오류 코드
번호도 다시 매겨졌는데, 이건 번호를 읽는 쪽에만 해당합니다. 이 하네스는 도구를
호출할 뿐 코드를 들여다보지 않아서 영향이 없었습니다. 저는 7월에 베타 SDK로 이
서버를 포팅했고 안정 버전 2.0.0에서 수정 없이 그대로 돌았습니다. 서버를 raw
HTTP가 아니라 SDK 위에 만들었다면 이 단계는 대체로 버전만 올리면 되는
수준입니다.

매니페스트로 넘어가기 전에 이 글의 범위를 밝혀 둡니다. 여기서 다루는 것은 세션
상태이고 세션 기반 서버라면 누구나 마주치는 부분입니다. 마이그레이션에는 두
가지가 더 있는데 이 글에서는 다루지 않습니다. 엘리시테이션을 쓰던 서버는 MRTR
패턴으로 다시 써야 하고 오래 걸리는 작업은 Tasks 확장으로 옮겨야 하는데 Python
SDK 2.0.0에는 Tasks가 아직 구현되어 있지 않습니다.

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

같은 워크로드를 같은 클러스터에서 목표 200rps로 30초씩, 셀마다 10회에서
22회 돌렸습니다. 아래 처리량은 중앙값이고 괄호 안은
관측 범위, 유실 건수는 반복의 합입니다.

| 구성 | 레플리카 1 | 레플리카 2 | 레플리카 4 |
|---|---|---|---|
| 구 스펙, 호출마다 새 연결 | 199.9 | 116.5 (92~155) | 33.2 (22~57) |
| 구 스펙, 연결 재사용 | 200.0 | 168.9 (136~193) | 130.8 (96~191) |
| 신 스펙, 두 방식 모두 | 200.0 | 200.0 | 200.0 |

두 가지가 눈에 띕니다. 우선 구 스펙은 레플리카를 늘릴수록 처리량이 줄어서 4개에서
중앙값 33.2rps가 되고 요청 78,000건 중 세션 유실이 37,844건입니다. 연결을
재사용하면 정도는 덜하지만 없어지지는 않습니다. 반복해서 재 보기 전에는 잘 안
보이는 것이 하나 더 있습니다. 레플리카가 2개 이상인 구 스펙 셀은 전부 회차마다
값이 달라집니다. 레플리카 4에서는 22에서 57rps, 그리고 96에서 191rps까지
나왔습니다. 어느 파드가 세션을 들고 있고 내 연결이 어느 파드로 가느냐에 따라
결과가 갈리기 때문입니다. 레플리카 1은 196.8에서 200.0으로 안정적이니 측정
잡음이 아니라 구 스펙의 성질입니다.

그에 반해 신 스펙은 69회 관측의 중앙값이 200.0rps이고 가장 낮은 회차도
199.7rps였습니다. 레플리카 수도 연결 방식도 가리지 않았고 유실은 전부 0,
p50도 6.2ms로 일정했습니다. 이번 개정이 실제로
노린 것이 이것입니다. 놓칠 세션이 없으니 쿠버네티스 서비스 뒤에 평범한
라운드로빈으로 레플리카를 늘리는 구성이 성립하고 스티키 세션이 더는 필요 조건이
아니게 됩니다. 무엇보다 그날의 운에 따라 처리량이 달라지지 않습니다.

다만 이 표를 보실 때 함께 봐 주셔야 할 부분이 있습니다. 노드 3대짜리
VirtualBox 클러스터에서 나온 값이라 절대 수치는 다른 환경으로 옮겨 해석하면 안 됩니다. 그리고 200rps는 일부러
포화 아래로 잡은 값입니다. 신 스펙에 목표를 더 올려 보니 300rps까지는 정확히
따라오고 400rps부터 못 따라갔는데(달성 324.6rps), 그때도 유실은 0이었습니다.
그러니까 이 글의 200rps는 이 클러스터가 감당하는 양의 3분의 2쯤입니다. 다른
클러스터에서도 같게 나타날 것은 절대 수치보다 경향 쪽이라고 보시면 됩니다.

그다음으로 실행 중에 파드를 강제로 종료해 봅니다. 롤아웃을 하면 어차피
일어나는 일입니다.

```sh
kubectl --context <ctx> -n mcp-pilot delete pod \
  $(kubectl --context <ctx> -n mcp-pilot get pod -l app=mcp-a \
    -o jsonpath='{.items[0].metadata.name}')
```

100rps로 60초씩 구 스펙에 6회, 신 스펙에 3회 돌리며 20초 시점에 파드를
종료했습니다. 구 스펙은 요청 1,922건을 세션 유실로 잃었고 회차별로는
59건에서 1,072건까지 갈렸는데, 죽은 파드가 세션을 몇 개나 들고 있었는지에
따라 달라지기 때문입니다. 신 스펙은 3회 모두 하나도 잃지 않았습니다. 두 셀의 설정은 같지 않습니다. 구 스펙 셀은
연결을 재사용하며 echo를 부르는데 이게 구 스펙에 가장 유리한 조건이고 신 스펙
셀은 호출마다 새 연결로 HMAC 카운터를 씁니다. 종료는 매회 실제로 이뤄진 것을
확인했습니다.

핸들 설계에도 같은 시험을 했습니다. 파드 메모리 구현은 파드가 죽으면 들고 있던
상태가 함께 사라지므로 5회에 핸들 유실이 13,942건 나왔고 HMAC과 Redis는
0건이었습니다. 덧붙여 Redis 자체를 실행 중에 종료해 봤는데 91.7rps에 유실
24건으로 끝났습니다. 파드 재기동이 빨라 손실은 작았지만 외부 저장을 고르는
것은 지켜야 할 의존성을 하나 들이는 선택이라는 점은 수치로도 남습니다.

## 아직 옮길 수 없다면

구 스펙 서버 자체는 그대로 동작합니다. 클라이언트와 SDK가 양쪽을 다 지원하기
때문입니다. 문제가 되는 것은 레플리카를 여러 개로 늘렸을 때입니다. 옮기기
전까지 버티게 해 주는 다리가 두 가지 있는데 둘 다 실제로 유실을 없앴습니다.
다만 치르는 값이 서로 다릅니다.

값이 싼 쪽은 쿠버네티스 서비스의 스티키 세션입니다.

```sh
kubectl --context <ctx> -n mcp-pilot patch svc mcp-a -p \
  '{"spec":{"sessionAffinity":"ClientIP"}}'
```

이 필드 하나로 레플리카 4 셀이 중앙값 26.4rps에 유실 13,760건에서 200.0rps에
유실 0으로 바뀌었고 파드 교체의 유실도 2,148건에서 88건으로 줄었습니다. 그대로
복사하시기 전에 어떻게 이긴 것인지를 봐 주시기 바랍니다. 제 부하 생성기는
호스트 한 대라 클라이언트 IP가 하나이고 ClientIP 친화도는 IP 단위로
고정하므로 트래픽 전부가 파드 하나로 갔습니다. 세션이 전부 살아남은 대신 부하
분산을 전부 포기한 것입니다. 실제 환경은 클라이언트 IP가 여러 개라 효과가
부분적일 것이고 요청이 많은 클라이언트 하나가 파드 하나를 계속 누르게 됩니다.

값이 비싼 쪽은 세션을 종단하는 게이트웨이입니다. agentgateway v1.4.1에서는
백엔드가 라우팅 방식을 선언합니다.

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

게이트웨이를 거치자 구 스펙 서버가 레플리카 4의 스케일아웃에서 유실 0이 됐고
파드 교체에서도 5회에 실패 20건, 회차당 4건으로 끝났습니다. 같은 날 같은
조건으로 잰 직접 경로 대조는 3회에 1,255건, 회차당 418건이었습니다. 게이트웨이가 세션을 종단하고 살아 있는
파드로 다시 연결해 주기 때문에 클라이언트가 죽은 파드를 만나지 않는 것입니다.
참고로 두 경로의 절대 처리량은 비교하면 안 됩니다. 게이트웨이가 워커 CPU를 쓰기
때문에 스케일아웃 셀은 한 번에 한 서버만 올려서 쟀고 파드 교체 비교만 같은
조건으로 잇달아 쟀습니다.

솔직하게 밝혀 둘 것이 두 가지 있습니다. 하나는 이 수치가 5xx를 받으면 다시
초기화하는 클라이언트로 잰 것이라는 점입니다. 게이트웨이 뒤에서는 세션을 잃은
요청이 직접 경로의 400이 아니라 5xx로 오는데, 제 하네스가 처음에는 5xx에서
복구하지 않아서 게이트웨이가 실제보다 훨씬 나쁘게 측정됐고 그 회차는 폐기한 뒤
고쳐서 다시 쟀습니다. 게이트웨이 벤치마크를 보실 때는 이 글을 포함해서
클라이언트가 5xx를 어떻게 다루는지부터 확인하시기 바랍니다. 다른 하나는 세션
상태를 지키는 부담이 사라진 것이 아니라 게이트웨이로 옮겨 갔다는 점입니다. 이제
장애와 교체를 걱정해야 할 대상이 게이트웨이 자신이 되는데, 이번 측정에서
게이트웨이를 죽여 보지는 않았습니다. 신 스펙은 이 두 장치 없이 같은 수치를
냅니다.

일찍 시도해 본 분을 위해 버전을 하나 밝힙니다. 1.4.0 정식판이 나오기 전의
프리릴리스인 에이전트게이트웨이(agentgateway) v1.4.0-alpha.1은 `params._meta`를
훼손해서 신 스펙 트래픽이 게이트웨이를 통과하지 못했습니다. 7월에 제가 막혔던
지점입니다. 위 측정은 모두 스펙 확정 직후에 나온 v1.4.1에서 했고 이 버전은 온전히
통과시킵니다.

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
7. 당장 옮길 수 없는 상황이라면 스티키 세션과 게이트웨이 세션 라우팅이 둘 다
   통합니다. 다만 값을 알고 씁니다. 스티키 세션은 부하 분산을 포기하는 것이고
   게이트웨이는 세션을 지키는 부담을 넘겨받는 것이라 그쪽 이중화도 함께
   계획합니다.

하네스와 핸들 설계 3종이 든 포팅 서버, 캡처한 페이로드, 측정 표 전체를 저장소에
공개해 두었으니 참고하시기 바랍니다. 부하 생성기가 구 스펙과 신 스펙을 모두 지원하는 덕분에 전후 비교가
가능했습니다.
시작할 때는 MCP 전용 부하 도구가 없었습니다. 다른 환경에서 재현해 보신 결과가
있다면 알려주시기 바랍니다.
