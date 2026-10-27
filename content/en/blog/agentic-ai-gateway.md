---
title: "What does a gateway mean in the world of agentic AI?"
date: 2026-10-21T09:45:00+09:00
draft: false
tags: ["agentgateway", "agent-router", "mcp", "ai-gateway", "aaif", "cncf"]
categories: ["AI"]
description: "A look at the gateway placed where agents call tools: market moves, the Agentic AI Foundation's ecosystem, and what I found by installing the foundation's two gateways myself."
summary: "Why several companies are shipping products at the point where agents connect, what ecosystem the Agentic AI Foundation wants to grow, and, based on installing the foundation's two gateways myself, when a gateway is worth considering."
ShowToc: true
TocOpen: true
cover:
    image: "/images/og/agentic-ai-gateway.jpg"
    alt: "What does a gateway mean in the world of agentic AI?"
    hidden: true
---

In May 2025 the security company Invariant Labs showed that an issue filed in a public GitHub repository could make an AI agent leak content from the same user's private repositories. The agent had only called GitHub MCP (Model Context Protocol) server tools within its granted permissions, and the server code had no bug, so Invariant Labs concluded that GitHub could not stop the attack by fixing the server alone and that it had to be handled at the agent system level.

So what does a gateway, sitting where an agent calls tools, mean in the world of agentic AI? For readers who want to connect agents to real work, this post looks at the market and the Agentic AI Foundation (AAIF), then draws on my own installation of the foundation's two gateways to say when a gateway is worth considering.

{{< note title="[Note] Where is the full article?" >}}
This post is a condensed English version of an article I wrote in Korean for [Yozm IT](https://yozm.wishket.com/magazine/detail/3999/). The full article there includes the cases trimmed here and a table comparing the two gateways.
{{< /note >}}

## Why products keep appearing where agents connect

Over the past year or so, products for the point where an agent calls models, tools, and other agents have kept arriving. For example, Kong AI Gateway 2.0 from Kong, Amazon Bedrock AgentCore Gateway from AWS, and Agent Gateway from Google are generally available. In Korea, KT DS added AI gateway features to its API gateway BEAST, and Samsung SDS said FabriX 2.0, the AI platform it has announced for an October 2026 launch, will get the same. The timeline below adds acquisitions and the foundation's main events.

![Timeline of the agent gateway market and Agentic AI Foundation milestones](/images/agentic-ai-gateway-timeline-en.svg "Agent gateway market and Agentic AI Foundation milestones")

Several companies are interested in the same point because calls through it have grown fast while ways to manage them are not yet in place. According to the foundation, ChatGPT users made 98 times as many MCP tool calls in August 2026 as in January. In Deloitte's survey of 24 countries, by contrast, 21% of organizations said they had a mature system for managing autonomous agents. Some build their own: in October, Uber published how it put more than 800 MCP servers behind an internal MCP gateway.

A gateway's job is to decide who may call which tool, and to record those calls, without modifying the MCP servers. When every team has its own MCP server, client settings and permissions must be handled per server, but with one gateway you manage control, and the records it produces, in one place.

![Agent connecting to each MCP server separately without a gateway, and to one gateway with it](/images/agentic-ai-gateway-structure-en.svg "MCP server connections without and with a gateway")

## Compared with the microservices era

Microservices also put a shared layer in the call path: authentication and observability moved out of each service into an API gateway and a service mesh. But Ram Vennam of Solo.io, which built agentgateway, explained that predictability differs: an agent can call different tools in a different order for the same request every time. So checking and recording each call as it happens matters more than allowing only calls defined in advance.

Standards for this point are only starting to form, but the protocol is changing first. The MCP spec revised in July 2026 puts the method and tool name in request headers, and the spec document says the goal is to let an intermediary such as a gateway check a request without parsing the body.

## The ecosystem the Agentic AI Foundation wants to grow

CNCF (the Cloud Native Computing Foundation) was created in July 2015 when Google donated Kubernetes. Projects have been added around Kubernetes since, and as of October 2026 it has 230 hosted projects (projects whose trademarks and repositories the foundation takes over and manages neutrally) and 723 member companies.

The Agentic AI Foundation launched the same way in December 2025 with Anthropic's MCP, Block's goose, and OpenAI's AGENTS.md as founding projects; in August 2026 A2A (Agent2Agent), started by Google, became a hosted project too. It has 270 member companies as of October 2026.

![Table comparing CNCF and the Agentic AI Foundation by founding, core projects, traffic layer, other major projects, and size today](/images/agentic-ai-gateway-ecosystems-en.svg "Ecosystems of CNCF and the Agentic AI Foundation")

The traffic layer row holds the foundation's two gateways. Solo.io's agentgateway became a hosted project in June 2026, and Envoy AI Gateway, which Bloomberg and Tetrate started as a subproject of the Envoy proxy, won approval from the foundation's board in August 2026 and was renamed Agent Router in September. Solo.io and Tetrate both sell separate commercial products yet donated the open-source projects to a neutral foundation, which tells me competition over this point is very intense. From the foundation's side, it looks like an effort to grow the traffic layer alongside MCP and A2A, the way Envoy became the common base for several gateways in CNCF.

## What I found by installing agentgateway and Agent Router

I installed each on a Kubernetes cluster, attached policies, and made calls. In the versions I checked (agentgateway v1.5.0, Agent Router v1.1.0), the scope of control differed. Blocking by tool name worked as configured on both. With an authorization policy alone, Agent Router could enforce a condition on the values passed in a call; agentgateway v1.5.0 needed a separate external checking server. The configuration docs that users mostly read give no warning, but adding such a policy sometimes left the agent with an empty tool list. agentgateway v1.6.0, released on October 2, 2026, can apply a condition on passed values through a route-level authorization policy, and when I retested it, only the intended calls were blocked, with no external checking server.

The latency the gateway added (median, compared with calling the server directly) was under 1 ms per tool call for agentgateway and about 20 ms for Agent Router at default settings. Most of that 20 ms came from the default iteration count for session encryption; lowering it brought the figure to about 0.5 ms. I measured each gateway separately, so this is not a comparison under identical conditions. Conditions and per-item results are in the [agentgateway post](/en/blog/agentgateway-mcp-enforcement/) and the [Agent Router post](/en/blog/agent-router-mcp-gateway/).

## When a gateway is worth considering

Consider one when you have several MCP servers and managing who may call what has become hard to do per server. If you have only one MCP server, or blocking by tool name is enough, you do not need one: the gateways I checked did not make calls faster and only added latency.

If you adopt one, after adding a policy, check for yourself that the tool list the agent receives is not empty, that the calls you meant to block are blocked, and that the settings you left at their defaults suit production. For security-related defaults like the session encryption iteration count, first find out why the value was chosen instead of simply lowering it.

## Wrapping up

To answer the opening question from what I checked: in agentic AI, a gateway is a layer where calls, which grow with the number of agents, are controlled and recorded in one place without modifying each server. I think that is why several companies have shipped products and why the AAIF accepted not one but two gateway projects. But standards are not yet settled, and even the two gateways in the same foundation differed in scope of control and in defaults, so it is worth watching how the foundation, like CNCF before it, grows this layer around MCP and A2A.

Finally, I am an AAIF ambassador, and agentgateway and Agent Router are its projects. So along with the good parts, I tested and included what does not work as documented. I hope it is of some use to readers connecting agents to real work.

## References

- [Yozm IT (Korean): 에이전틱 AI 세계에서 게이트웨이는 어떤 의미를 가질까요?](https://yozm.wishket.com/magazine/detail/3999/): the full article, including the cases trimmed here and a table comparing the two gateways
- [Invariant Labs: GitHub MCP Exploited: Accessing private repositories via MCP](https://invariantlabs.ai/blog/mcp-github-vulnerability): the GitHub case in the opening (May 26, 2025)
- [What changes when you put a gateway in front of MCP?](/en/blog/agentgateway-mcp-enforcement/): agentgateway measurements
- [What changes when you put Agent Router in front of your MCP servers?](/en/blog/agent-router-mcp-gateway/): Agent Router measurements