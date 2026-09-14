---
title: "What changes when you connect agents over A2A?"
date: 2026-09-14T00:00:00+09:00
draft: false
tags: ["a2a", "agent2agent", "mcp", "model-context-protocol", "aaif", "kubernetes", "agent"]
categories: ["Kubernetes"]
description: "Running the A2A protocol on the official Python SDK to check, item by item, whether the spec's promises hold, and building the same job over MCP and plain HTTP to compare what it costs the client."
summary: "What A2A gives you is a contract for progress and cancellation. What it costs is a larger response (seven times plain HTTP for the same job) and 1.2 to 2.1 ms more per call. The authentication the agent card declares is not enforced by the SDK's default setup, so read declaration and enforcement separately."
ShowToc: true
TocOpen: true
---

On 2026-08-17 a project called A2A (Agent2Agent) joined the Agentic AI
Foundation (AAIF). The name tells you it is a protocol for agents talking to
each other, but I wanted to know more than the published spec: what it is for
and when it is worth using. So I ran a server on the official SDK. Three
questions drove it. When is A2A the thing to use, what changes in my code if I
use it, and does the spec's promise actually hold.

Up front: what A2A gives you is a contract for progress and cancellation, and
in exchange the response grows and each call takes longer. For the same job the
response is seven times that of plain HTTP and latency is 1.2 to 2.1 ms higher.
That contract only earns its keep in certain situations, so there is nothing to
gain on short one-shot calls. And the authentication the agent card declares is
not enforced by the SDK's default setup, so you have to read declaration and
enforcement separately.

Some background on the project first. Google published A2A in April 2025 and
donated it to the Linux Foundation with AWS, Cisco, Microsoft, Salesforce, SAP
and ServiceNow among the founding organizations. It was proposed to AAIF in
June 2026, cleared the technical committee and the board, and became a hosted
project on 17 August at the Growth stage (Impact is the one above it). The spec
froze at v1.0.0 on 12 March 2026, and v1.0.1 from 28 May, the version this study
targets, is still the latest as I write. Because v1.0 renamed methods, part
types and task states all at once, field-level descriptions in posts from the
0.x era no longer match.

{{< note title="[Note] Terms used in this post" >}}
- A2A: the protocol that defines how agents hand work to each other. Where this
  post says A2A with no qualifier, it means the protocol.
- A2A SDK: the official library implementing A2A. There is one per language;
  this post uses the Python one, `a2a-python`. Sometimes shortened to the SDK.
- Agent: a service that hands work over or takes it on. The side handing work
  over is also called the client, the side taking it on the server.
- Agent Card: the JSON document an agent publishes to describe itself. It lives
  at `/.well-known/agent-card.json` and says what the agent can do, where and
  how to call it, and what authentication it requires.
- Security scheme: the name of a way to authenticate. API key, HTTP Bearer and
  OAuth2 are examples, and they are listed in the agent card's
  `securitySchemes`. Listing them is all the card does; actually checking is
  the server's job.
- Message: what agents send each other. Handing work over and asking a
  mid-flight question both happen as messages. A message can carry text, files
  and structured data, and each of those pieces is called a Part.
- Task: the unit of work A2A defines. Sending a message creates one, and it
  carries an identifier, a state, a history and artifacts. This is not the Task
  of Kubernetes Jobs or CI pipelines, so keep them apart while reading.
- Artifact: what a task produced. It stays attached to the task once the work
  finishes. Unlike the messages that pass back and forth, this is the final
  output.
{{< /note >}}

What A2A fixes is four of those, the agent card, the message, the task and the
artifact, plus the transport that carries them. It assumes you cannot see the
tools, the model or the internal plan the other agent uses, so it does not
define what happens inside the counterpart. Read the card, send a message and a
task appears; when the work ends an artifact remains. Those four travel over one
of three bindings: JSON-RPC, HTTP+JSON (the SDK calls it REST) and gRPC.

![The counterpart is opaque; only four things are visible](/images/a2a-surface-en.svg)

By this point you may wonder how it differs from MCP (Model Context Protocol),
since both call something over JSON-RPC and get a result back, which makes them
look alike from the outside. They differ in what sits on the other end. To quote
the spec appendix, MCP standardizes how an agent uses tools and resources, while
A2A standardizes how an agent delegates work to another agent. A tool is
something you call and a result comes back; an agent takes work, spends time on
it, and may ask a question or refuse along the way. So MCP has tool listing and
tool calls, and A2A has cards, tasks and state changes. One thing is easy to get
wrong about the relationship: they are not a sequence, they are a choice. Using
a tool yourself needs only MCP, and A2A is for handing work to someone else.

![MCP and A2A differ in what sits on the other end](/images/a2a-compare-en.svg)

I measured three things. Whether what the spec promises actually works in the
SDK's default setup, checked as twelve items. What the client goes through when
the same job is built three ways, over A2A, MCP and plain HTTP. And how much
latency and how many bytes the protocol itself adds under load. The versions are
spec v1.0.1 and `a2a-python` 1.1.2; the MCP arm runs `mcp` 2.0.0 and the HTTP arm
is a minimal JSON-RPC server from the standard library. The environment is a
three-node Kubernetes 1.37.0 on VirtualBox, so read the numbers as relative
comparisons between implementations rather than absolute values. The exact
conditions and the per-item verdicts are in the
[public repository](https://github.com/sysnet4admin/Research/tree/main/a2a-study).

## What you get: a contract for progress and cancellation

Start with what A2A buys you. Wrapping the same work function three ways and
handing over a 15-second job, all three take 15.1 to 15.2 seconds to return a
result. What differs is what the client can do during those 15 seconds.

There are three ways to learn how far the work has progressed, and A2A has all
three in the spec.

- Polling: the client asks for the state periodically. It is the easiest to
  build and it costs one round trip per question.
- Streaming: the server holds one connection open and sends an event whenever
  the state changes. The client never has to go and ask.
- Push: the server calls a URL you registered in advance. Nothing has to hold a
  connection open, which suits long work. In the SDK's default setup the
  configuration request itself is rejected, so using push takes wiring; more on
  that later.

![What you can do while a 15-second job runs](/images/a2a-waiting-en.svg)

You can build the same thing over plain HTTP and MCP. The difference is that
nothing is given to you as a contract, so you write all of it, and since you
choose the names and the response shapes yourself, you redo them when the
counterpart changes. This study built only a status-lookup call on both and
polled it once a second; nothing equivalent to streaming or push, because that
would mean adding an SSE (Server-Sent Events) endpoint and a webhook sender.

MCP has one more option: a blocking call that waits out the 15 seconds. Send one
`tools/call` and hold it until the result arrives, and the status round trips
are zero. In exchange you cannot see how far along the work is, and a timeout
loses the result. Since `mcp` 2.0.0 has no task lifecycle in its core, the only
other option is a separate tool that reports status.

Cancellation is the same story. A2A has it in the spec, and the SDK wires it to
the cancellation hook of the AgentExecutor, the class where the application puts
its work logic. Tasks in flight and tasks waiting on an answer were both
cancelled. One thing to note: cancelling a finished task is rejected, and the
error code that comes back is an internal error (-32603) rather than the
`TaskNotCancelableError` (-32002) the spec defines. If you plan to branch on that
code, account for it. Plain HTTP and MCP have no cancellation contract at all,
so this study left them with a minimal implementation that only flips a flag,
and the worker thread kept running. Building real cancellation is of course
possible, and that work is what a missing contract costs you.

One more case: the counterpart asking a question mid-flight. Something like
which environment to deploy to, asked while the work is under way. A2A has a
state for it (input-required), and sending the answer on the same task resumes
the work. MCP's core has no such state, so unless the application builds one the
call starts over from the beginning.

## Five things you stop rebuilding as counterparts multiply

Here is what you get as a single number. To build progress tracking and
cancellation you need to know five things about the counterpart agent. The names
in parentheses are what A2A fixes in the spec.

- the name of the call that starts the work (`message/send`)
- the field name that identifies it (`taskId`)
- the name of the call that asks for status (`tasks/get`)
- the set of state values that come back (8 of them: `submitted`, `working`,
  `completed` and so on)
- how to cancel (`tasks/cancel`)

Those are the v0.3 JSON-RPC names. In v1.0 they became `SendMessage`, `GetTask`
and `CancelTask`, and the state values took an uppercase prefix, as in
`TASK_STATE_COMPLETED`. The names changed; that the spec fixes them did not.

Over plain HTTP and MCP each agent decides these five for itself. Every time one
more counterpart agent shows up you check its rules and write new client code.
In A2A all five come from the spec, so the client code you already have keeps
working when the counterpart changes.

Of course, if you only ever call one in-house agent the number means nothing.
With a single counterpart you match it once and there is no reason to pay for
following a contract. But if there are five of them, or they belong to another
company, you rebuild the client each time, and the amount is five things per
counterpart agent. Where the contract earns its keep depends on how many
counterparts you have.

## What A2A adds: response bytes and latency

If there is something to gain there is something to lose. Using A2A means larger
responses and slightly higher latency per call than building it over plain HTTP.
On short jobs the three implementations returned result strings identical down
to the character, and the only differences were the round trips, the latency and
the response size, so a table covers it.

| Implementation | First-call round trips | Median latency | Response bytes |
|---|---|---|---|
| HTTP | 1 | 3.2 ms | 80 |
| MCP | 1 | 5.9 ms | 286 |
| A2A | 2 | 6.1 ms | 581 |

A2A's first round trip fetches the agent card and costs 858 bytes. The response
is large because the task object rides along every time. That object carries the
identifier, the state and the history, and it is sent ahead so you can check
progress or cancel later. On a call that finishes in under a second that later
never comes: there is no progress to check and nothing to cancel, so the extra
bytes go unused.

Polling repeats that weight. Every status check carries the whole task object,
so on A2A the final response that confirms completion is 571 bytes (423 while
the work is still running), against 92 bytes for the status lookup built by hand
over plain HTTP, more than six times. MCP sits in between at 286.

That said, this is what polling costs. Asking once a second about a 15-second
job means checking 16 times and receiving 6,916 bytes along the way. The same
work received over streaming is 1,287 bytes across four events, and over push it
is 465 bytes across the two requests the server sends. A single response is
heavy, but for long work dropping polling ends up far lighter overall.

Latency grows too, which I checked by putting the same load on all three
implementations. Two request rates and two connection modes give four
conditions, and running one implementation under one condition for 30 seconds
counts as one cell. I ran ten rounds; the table below is the median of those ten.
Not a single cell produced an error or a shed request.

| Condition | HTTP | MCP | A2A | A2A - HTTP |
|---|---|---|---|---|
| 50 rps, new connection per call | 4.4 | 5.5 | 5.8 | +1.4 |
| 50 rps, connection reuse | 3.4 | 5.5 | 5.5 | +2.1 |
| 100 rps, new connection per call | 3.6 | 4.4 | 4.8 | +1.2 |
| 100 rps, connection reuse | 3.0 | 4.2 | 4.5 | +1.5 |

The values are p50 latency per call (the time half the requests finish within)
in milliseconds. The generator ran 50 and 100 rps at concurrency 8 and 16
respectively, so compare implementations within a row rather than across rows.

Put the A2A-to-HTTP gap (1.2 to 2.1 ms) next to the A2A-to-MCP gap (0 to 0.4 ms)
and it is clear that most of the cost is not there because it is A2A but because
it is a structured protocol. So if you already run MCP and are used to that much
latency, adding A2A will not move it much; coming from plain HTTP you take on
the full 1.2 to 2.1 ms.

![What you get and what you pay](/images/a2a-result-en.svg)

## An agent card that declares authentication the server never checks

So far this has been what you get and what you give up. From here it is what you
should not trust. Of the twelve items the spec promises, the SDK's default setup
matched the spec on five, met it with conditions on four, and behaved differently
on three. Two of those three share a cause.

Authentication first. Spec section 7.4 says the server must authenticate every
request according to what the card declares, so I put all three security schemes,
API key, HTTP Bearer and OAuth2, in the card at once. I wanted to see which one
blocks the call and what error a wrong key produces.

Calling with no credentials at all returned 200, and a request carrying a wrong
key did the same. The server was built to compare how it blocks, and it was not
blocking at all. My first thought was that I had misconfigured the server, so I
went back to the card. The three schemes were there, declared as written.

And the problem does not end with authentication. The extended agent card, the
one meant to go only to authenticated requests, behaved the same way. The spec
says it goes only to authenticated callers, yet unauthenticated requests got back
skills that are not in the public card.

Both have the same cause: the SDK's default handler has no place that checks who
the caller is. The card's `securitySchemes` is only a declaration telling clients
how to authenticate, and the code that checks against that declaration is left to
the application. The spec puts it on the server, the default setup does not do
it, and the gap is the result. When I
[put a gateway in front of MCP](/en/blog/agentgateway-mcp-enforcement/) earlier,
an accepted policy and an enforced one also turned out to be different things;
this time the same gap shows up inside the protocol.

So do not assume that reading the card and adding authentication means the server
will block anything. Enforce it in the application or let a gateway in front do
it. Putting private information in the extended card is risky for the same
reason: identity is never checked, so a skill kept out of the public card goes to
anyone who asks.

## The `A2A-Version` header that splits two versions

The remaining difference is that the addresses the agent card advertises and the
addresses the server actually serves do not match. Reading that requires knowing
how the server splits the two generations first (this post calls v0.3 and v1.0
generations). Generation selection is written plainly in the spec and was still
the hardest thing to notice.

When v1.0.0 froze in March 2026 the method names, part types and task state names
all changed at once. You cannot cut off existing v0.3 clients just because the
names changed, so a server with v0.3 compatibility on serves both, and which one
handles a request comes down to a single `A2A-Version` header value. Spec section
3.6.1 tells clients they must send the header and, in the same sentence, says an
absent header means v0.3.

The trouble starts when a v1.0 client forgets the header: instead of an error the
request is handled as v0.3. I first concluded that "JSON-RPC only takes the v0.3
shape", and only after adding the header and calling again did I learn that the
same address takes v1.0 method names and message shapes perfectly well. A result
served by the other generation comes back as a normal response, which makes it
hard to spot.

How the split happens also differed between the two bindings I checked (gRPC
speaks the v1.0 schema from the start, so it does not split by generation).
JSON-RPC splits on the header alone at a single address, while REST splits by
path as well, and there `/a2a/rest/` is v1.0 and `/a2a/rest/v1/` is v0.3, so the
names read backwards from what they are (pick v1.0 by path and you land on v0.3).

![One header splits the same address into two generations](/images/a2a-version-en.svg)

Now for the remaining item mentioned earlier. A server with v0.3 compatibility
turned off still lists v0.3 interfaces in its card, and calling those addresses
gets you rejected. The list the card advertises and the addresses the server
actually accepts are maintained separately. Put next to the authentication
section, it shows that how far to trust the card is a question this protocol
keeps raising. A client that reads the card and connects gets blocked at an
address the card says exists.

## So when is it worth using?

That is what I checked. Now for when adopting it makes sense.

Start with when you do not need it. Calling the tools of a single in-house
service is one: MCP is enough there and adding A2A gains you nothing. Handing a
sub-second job to an agent on your own team is another. The contract has nothing
to do, and with a single counterpart matching it over plain HTTP is more
effective.

There are two places where it does matter. One is handing over long work and
watching its progress or cancelling it mid-flight. Get, streaming, push and
cancel are all in the spec, so the client you already have keeps working when the
counterpart agent changes. The other is calling several agents from other teams
or other organizations. You find them by card and handle them under one contract,
and the five things you used to rebuild per counterpart go away.

Prototypes need a separate look. If you plan to build one quickly and decide from
there, the SDK's default setup is not enough on its own. Enforcing authentication
means putting the caller check in the application or a gateway in front, push
notifications mean building somewhere to keep the configuration and something to
send them, and surviving a restart means swapping the task store. Wiring those
three can outgrow what the prototype was meant to answer.

## A checklist for adopting it

Finally, the things worth checking when you actually adopt it.

1. The security schemes the agent card declares are not checked by the server.
   Enforce authentication in the application or in front of it.
2. Do not put private information in the extended agent card. The SDK's default
   setup does not check identity, so unauthenticated requests get it as is.
3. Always send the `A2A-Version` header. Omit it and you get v0.3 rather than an
   error.
4. Do not trust the card's interface list; call the addresses and see. Turning
   v0.3 compatibility off leaves them in the card.
5. If you branch on cancellation failure by error code, do not look only for
   `TaskNotCancelableError` (-32002). A finished task returned an internal error
   (-32603).
6. To use push notifications you have to build somewhere to keep the
   configuration and something that sends them, and wire both. Without that the
   configuration request itself is rejected. And even once wired, a failed
   delivery still leaves the task completed, so the client has no way to learn
   about it and only the server log shows it.
7. Polling alone means receiving up to 571 bytes per status check, so consider
   streaming or push alongside it.
8. The SDK default keeps tasks in pod memory with `InMemoryTaskStore`, so
   restarting the backend loses the state. Swap in a store that survives a
   restart.

## Limits

This was measured with one SDK (Python 1.1.2) and a server built on the sample
AgentExecutor, so other language SDKs and production executors may differ. And
the status lookups I wrote by hand on the plain HTTP and MCP sides are minimal
implementations for comparison; a real service would add a store, cancellation
propagation and notifications, and the code would grow accordingly. Read the
amount of code here as the floor of that work.

One more thing to disclose. A2A renamed its fields when v1.0 arrived in March
2026, and measuring both generations side by side showed latency within 0 to
0.2 ms of each other while the response was 34 bytes smaller on v1.0. The state
names got longer, but the discriminator fields on parts and messages went away,
so the total shrank. The numbers above are on the v0.3 shape; switching to v1.0
brings the bytes down by that much.

## Closing

I started with three questions. Here they are one at a time.

**First, when is A2A the thing to use?**

It depends on whether what you send the request to is a tool or an agent. If it
is a tool that returns a result when called, MCP is enough. If it is an agent
that spends time on the work and may ask a question or refuse along the way, you
need a way to ask how far it has got and to stop it if necessary. A2A is where
that way is defined.

**Second, what changes in my code if I use A2A?**

What changes is progress tracking and cancellation: you no longer build those two
yourself. The spec fixes five things, from the name of the starting call to the
cancellation contract, so one more counterpart agent does not mean new client
code. In exchange the response grows and each call takes 1.2 to 2.1 ms longer,
which is a cost with no reason to pay it when you have a single counterpart and
short calls.

**Third, does what the spec promises actually hold?**

Only five of the twelve items matched the spec. Four came with conditions and
three behaved differently. In particular, an agent card declaring authentication
did not make the SDK's default setup check it. Read what the card says and what
the server does as two separate things.

The scripts, the manifests and the per-item verdict table are in the
[public repository](https://github.com/sysnet4admin/Research/tree/main/a2a-study),
so have a look if you want to run it yourself. If you reproduce any of it in a
different environment I would like to hear about it.

This time I called the same server in both generation shapes. What happens when a
v0.3 client and a v1.0 server actually mix, and how a gateway in front decides
the generation and rewrites the agent card, are outside this round.
