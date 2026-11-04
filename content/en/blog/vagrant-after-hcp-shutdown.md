---
title: "What happens to Vagrant when Vagrant Cloud shuts down?"
date: 2026-11-05T08:20:00+09:00
draft: false
tags: ["vagrant", "hcp-vagrant", "hashicorp", "virtualbox", "ruby", "macos", "license", "lima"]
categories: ["Tools"]
description: "HCP Vagrant (formerly Vagrant Cloud) shuts down on December 31, 2026, more than five months earlier than first announced. The Vagrant CLI stays, but there has been no release for over 14 months since 2.4.9, and the bug that makes vagrant up fail on macOS 26.7 and later is still open. This post covers the current state of Vagrant, including the switch of the main branch back to MIT on November 2, and what to watch next."
summary: "The Vagrant Cloud shutdown schedule, how the community reacted, the state of Vagrant after more than 14 months without a release, the macOS port forwarding bug, the return to the MIT license, and the tools you can use instead of Vagrant."
ShowToc: true
TocOpen: true
cover:
    image: "/images/og/vagrant-after-hcp-shutdown.jpg"
    alt: "What happens to Vagrant when Vagrant Cloud shuts down?"
    hidden: true
---

**HCP Vagrant** shuts down on December 31, 2026. HCP Vagrant is the public service that Vagrant, HashiCorp's virtual machine (VM) management tool, downloads **boxes** from, and a box is the image file Vagrant uses to create a VM. It was called Vagrant Cloud until it became part of HCP (HashiCorp Cloud Platform) in 2024, so many people probably still know it by that name. When you write only a name in a Vagrantfile, such as `config.vm.box = "sysnet4admin/Ubuntu-k8s"`, Vagrant can fetch the box because it looks that name up on HCP Vagrant.

I publish seven boxes for Kubernetes and Ansible labs under the sysnet4admin account, so I looked into the shutdown while moving those boxes. Along the way it turned out that HCP Vagrant was not the only problem: Vagrant itself has had no new release since August 2025, and upgrading to macOS 26.7 or later makes `vagrant up` fail. I could hardly find anything in Korean that put this together, so I wrote it up in two posts for anyone who has been using Vagrant or is deciding whether to keep using it.

The short answer is that the Vagrant CLI stays after the shutdown and boxes you have already downloaded keep working, so you do not lose Vagrant right away. However, if a Vagrantfile only names a box, any environment that downloads that box for the first time after December 31 will fail. And because there has been no release since 2.4.9, it is unclear when problems caused by operating system changes, like the macOS port forwarding bug, will be fixed.

This post looks at where Vagrant stands today and where it may go, and the next post covers where to move boxes. Everything here is as of November 3, 2026, and I checked the MIT release and the status of #13845 again on November 5, before publishing.

## A shutdown schedule moved up by more than five months

Let's start with the schedule. HashiCorp announced the shutdown on August 3, 2026, in an issue on the Vagrant GitHub repository (#13836) and on its official forum, HashiCorp Discuss. A few days earlier, on July 29, the first version of the end-of-life page set the final shutdown for June 7, 2027. Then two PRs merged into HashiCorp's documentation repository on August 31 (web-unified-docs#3256 and #3257) moved every stage forward, as the figure below shows.

![Two timelines showing that all three stages of the first announced schedule moved earlier, with the shutdown moving from June 7, 2027 to December 31, 2026](/images/vagrant-shutdown-schedule-en.svg "First announced schedule vs. current schedule")

As a result the shutdown came more than five months earlier, and since October 1 HCP Vagrant has rejected not only new boxes but also new versions of existing boxes. Uploads fail with `resource creation is currently disabled`, and AlmaLinux and other publishers reported the same error.

What remains after the shutdown is the Vagrant CLI and the source repository on GitHub. The box listings, the box files hosted on HCP Vagrant, and public box search all go away, and HashiCorp has not announced a public replacement, so publishers have to host their boxes elsewhere and pay for that hosting. HashiCorp did add a migration guide for Amazon S3, Azure Blob Storage, and IBM Cloud Object Storage on September 11. On October 28 it also announced vagrant-registry-export, an export tool that downloads every box in an account to a local folder and writes the `metadata.json` that Vagrant reads. The tool only downloads, though, and the `metadata.json` it writes points at local paths on the machine that ran it, so publishers still have to rebuild that file for the new location and upload everything themselves.

HashiCorp also said it would provide a static archive that redirects existing addresses during the transition, but its September 17 blog post and the end-of-life page still describe it as planned, and it had not appeared as of November 3. The end-of-life page itself has not changed since August 31.

## How the community reacted, and projects that dropped Vagrant

With the schedule pulled in like this, I expected a strong backlash, but when I looked there was little reaction. The announcement on HashiCorp Discuss got one reply, and most comments on the GitHub announcement issue (#13836) were short notes of regret like "F" (an internet meme for paying respects). Hacker News had three threads, and the largest had 19 points and 8 comments. (On Reddit I only checked r/vagrant, and I could not check lobste.rs.)

The one reply on Discuss asked for a shared catalog where each publisher hosts its own files and only the list is shared, and HashiCorp did not respond. On Hacker News, some said Vagrant was now Docker without a public registry and nobody would use it, and some said they had moved to Lima, an open source tool for running VMs. Others said nothing else recreates an environment as reliably as a Vagrantfile. On Mastodon there were posts saying Lima cannot do basic network setup such as static IPs, and that no tool under an open source license replaces Vagrant one for one.

I did not find out why the reaction was so small, but it may be related to the fact that many projects had already scaled back or ended Vagrant support after Vagrant's license changed to the **BSL** (Business Source License, a source-available license that restricts offering the software as a competing product) in 2023. The projects that did so from 2024 onward are listed below.

| Project | When | What they did |
|---|---|---|
| Ubuntu | 2024-02 | Removed the Vagrant package in 24.04 and stopped publishing Vagrant boxes from 24.04 |
| Arch Linux | 2025-04 | Stopped publishing Vagrant boxes |
| Trellis (Roots) | 2025-10 | Ended Vagrant support and moved to Lima |
| Debian | 2025-11 (removed from testing) | Kept only 2.3.7, the last commit before the BSL, in Debian 13 and does not package BSL versions |
| netlab | 2026-09 | Announced the sunset of the vagrant-libvirt provider and is moving to containerlab |

Each had its own reasons, but Ubuntu, Debian, and netlab named the license change as one of them. netlab is an open source tool for building network labs, and its author, Ivan Pepelnjak, gave two reasons in the netlab repository on September 14 (#3879): vagrant-libvirt had been effectively abandoned (abandonware) with no release since June 2023, and the license change and the HCP Vagrant shutdown suggested that HashiCorp no longer cares about Vagrant. netlab is therefore moving to containerlab, which runs network devices in containers, and will keep the libvirt provider for now with bug fixes only.

Some no longer see Vagrant as open source since the license change. In his January 2026 FOSDEM talk introducing Lima, Lima's creator Akihiro Suda listed Vagrant as "Proprietary" on his slides.

Most box publishers, on the other hand, have not announced anything. For example, the geerlingguy account of Jeff Geerling, author of "Ansible for DevOps", has 559,000 downloads for `geerlingguy/centos7` alone. Its box files are all on HCP Vagrant, so unless something changes they will be deleted on December 31. The next post covers how other publishers are responding.

## Vagrant after more than 14 months without a release

So where does Vagrant itself stand, apart from HCP Vagrant? As the end-of-life page says, "The community edition in GitHub including the CLI will remain available", so the CLI stays after the shutdown. But "community edition" here is just the name used to tell the CLI on GitHub apart from HCP Vagrant, and nothing says maintenance is being handed to the community. There is no public roadmap, and Vagrant was not mentioned in IBM's announcement that it had completed the HashiCorp acquisition (February 27, 2025).

The release history shows 2.4.6, 2.4.7, 2.4.8, and 2.4.9 within three months from May to August 2025, and then nothing for more than 14 months after 2.4.9 on August 21. Since then there have only been nightly builds (`2.4.10.dev+...`), and the last one is from June 1, 2026.

![A timeline showing four releases from 2.4.6 to 2.4.9 within three months, followed by more than 14 months with no release, with the Ruby fix, the issue report, and the switch back to MIT marked in between](/images/vagrant-release-gap-en.svg "What happened while no release followed 2.4.9")

Development has slowed down a lot while no releases came out. Commits by people, excluding bots, peaked at 44, 44, and 31 per month in March to May 2025 and kept falling after that. In 2026 there have been 24 commits, only one of which changed code. Meanwhile 25 issues were opened in 2026 and 3 were closed, and there are 676 open issues and 83 open PRs. Of the 35 PRs merged since September 2025, 30 were merged by one person at HashiCorp, and the code changes merged to main in that period include three external contributions (a Hyper-V disk fix, a VirtualBox storage controller fix, and a fix for Ubuntu 24.04 hanging on shutdown) and an Ansible provisioner fix (#13740), none of them released yet. The `hashicorp/vagrant-installers` repository, which builds the per-OS installers for each release, last had a commit by a person on August 4, 2025.

Separately from the slowdown, there are also fewer ways to install Vagrant. Linux distributions did not package 2.4, which moved to the BSL, and the versions available by installation method as of November 2026 are as follows.

| Installation method | Version | Status |
|---|---|---|
| Ubuntu package | None | Removed in 24.04 (license change and maintenance burden) |
| Debian package | 2.3.7 in Debian 13 (last commit before the BSL) | Does not package BSL versions |
| Fedora package | 2.3.4 | Does not package 2.4.0 or later |
| Arch Linux | 2.4.9 in the AUR (Arch User Repository) | Not in the official repositories |
| Homebrew, Chocolatey, winget, Scoop, Nix | 2.4.9 | Latest release |

The 2.3 versions left in distributions lack box architecture support (2.4.0), VirtualBox 7.1 support (2.4.2), and VirtualBox 7.2 support (2.4.9), so to use Vagrant with current VirtualBox you need to install 2.4.9 from HashiCorp's own installers or a package manager such as Homebrew or Chocolatey. The exception is Debian's development branch, sid, which backported only the VirtualBox 7.1 and 7.2 support into 2.3. The 2.4.9 installers also include macOS arm64 but not arm64 for Linux or Windows.

VirtualBox support likewise only arrives with a new Vagrant release. VirtualBox 7.1 was supported from Vagrant 2.4.2 and 7.2 from 2.4.9, so the next minor or major VirtualBox version will also need a new Vagrant release before you can use it. Plugins for other hypervisors are in mixed shape. vagrant-libvirt, which netlab is moving away from, has had no release since June 2023. VMware Workstation Pro and Fusion Pro have been free for everyone since November 2024, but the Vagrant VMware plugin's last release was in April 2025, and an issue about it not recognizing the latest Workstation is still open. On the other hand, some plugins are still releasing, such as vagrant-qemu (0.7.0, October 15), vagrant_utm (0.2.0, October 14), and vagrant-parallels (2.4.10, October 28).

The Ansible provisioner (the feature that applies configuration automatically after a VM is created) is in a similar position. 2.4.9 passes the `--inventory-file` option when it runs Ansible, and from ansible-core 2.19 you get a warning that the option will be removed in 2.23. A fix (#13740) based on an outside contributor's PR (#13733) was merged to main on November 19, 2025, but you only get it once it ships in a new release.

Nor could I find an open source fork that carries Vagrant on in HashiCorp's place. Of the 4,526 forks on GitHub that I checked, the most starred has 14 stars, and Vagrunt, which was announced on Hacker News right after the BSL change in 2023, now returns 404.

## vagrant up fails on macOS 26.7 and later

If you use macOS, there is also a problem that can affect you right now. According to issue #13845, opened on September 17, on macOS 26.7 and later Vagrant treats every host port as already in use, so `vagrant up` fails with "Vagrant cannot forward the specified ports on this VM". Even a Vagrantfile with no port forwarding of its own gets one port forwarded for SSH by default when it uses VirtualBox, so on an affected Mac most Vagrantfiles that use VirtualBox can fail at the same step. I have not reproduced this on an affected Mac myself.

The comments on the issue suggest the scope may be wider than first reported. One reports the same failure on an Intel Mac with VirtualBox 7.2.20 (macOS 26.7.1), and one comment says it started after upgrading to macOS 15.8.1 (Sequoia).

The cause appears to be a change in macOS behavior combined with how Ruby checks the result of a connection. Vagrant is written in Ruby, and to check whether a port is free it tries to connect to that port with Ruby's `Socket.tcp`, treating the port as free if the connection is refused. When Ruby makes a connection with a timeout, it starts the connection, waits for it to finish, and then calls `connect` once more to check the result, and if that returns "already connected" (EISCONN) it treats the connection as successful. Starting with the macOS 27 beta, the kernel returns EISCONN even for refused connections, and the same behavior seems to have reached 26.7, so Ruby treats a refused connection as a successful one. In other words, the actual result, the refusal, was recorded in the socket's `SO_ERROR`, but Ruby never read it. The same macOS change made Webots, a robot simulator, wrongly report every TCP port as in use on the macOS 27 beta, so this is not specific to Vagrant.

![A side-by-side sequence diagram: on earlier macOS the kernel returns a refusal and the port is treated as free, while on macOS 26.7 and later it returns EISCONN and the port is treated as in use](/images/vagrant-macos-port-en.svg "How Vagrant checks whether a port is free")

Can you simply wait for Ruby to fix it? Ruby already has. The problem was reported on the macOS 27 beta on July 31 (Bug #22223), and a change merged on August 6 (ruby/ruby#18203) touched seven lines so that Ruby reads `SO_ERROR` first after waiting and raises the error if there is one. That change is in 3.4.11 (September 23), 3.4.12 (October 23), and 4.0. But the Ruby bundled with Vagrant 2.4.9 is 3.3.8. Ruby 3.3 has been in its security-only phase since April 1, 2026, the backport entry for this change was marked "3.3: DONTNEED", and 3.3 itself reaches end of life on March 31, 2027.

So the fix is unlikely to reach Ruby 3.3, and the problem will only be solved when Vagrant ships a release built with Ruby 3.4.11 or later, or merges PR #13842, which adds the same `SO_ERROR` check to Vagrant's own code, and ships that. As of November 3, though, #13845 has only had the triage label (`waiting-intake`) for seven weeks with no maintainer comment. #13842, from an outside contributor, has no review either, and `is_port_open.rb` on main is unchanged apart from its license header on November 2.

You can check whether your Mac is affected by having the Ruby bundled with Vagrant connect to a closed port.

```bash
/opt/vagrant/embedded/bin/ruby -e 'require "socket"; s=TCPServer.new("127.0.0.1",0); p=s.addr[1]; s.close; begin; Socket.tcp("127.0.0.1",p,connect_timeout:0.1); puts "AFFECTED"; rescue => e; puts "OK: #{e.class}"; end'
```

On my Mac (macOS 26.0.1) it printed `OK: Errno::ECONNREFUSED`, so it is not affected. On an affected system the refusal does not come back as an error, so I would expect `AFFECTED`, but I have not run it on one. If you are affected, a comment on the issue shows a workaround that overrides `is_port_open?` in `~/.vagrant.d/Vagrantfile`, and several people said it worked for them. It is not an official fix, so I suggest reading the issue comments before you apply it.

## The main branch back on the MIT license

With no release in sight, something changed in the Vagrant repository while I was writing this post. At 23:04 UTC on November 2 (8:04 a.m. on November 3 in Korea), PR #13858, "Revert license update", was merged and changed the license headers of 1,555 files from BSL 1.1 (BUSL-1.1) to MIT, and #13859, merged right after, changed the copyright line to "Copyright IBM Corp. 2026". I checked, and the `LICENSE` file on main is now MIT as well. Here is how Vagrant's license has changed over time.

| When | What |
|---|---|
| 2010 to 2.3.7 (2023-06-15) | MIT |
| 2023-08-10 | HashiCorp announced the move to BSL 1.1 |
| From 2.4.0 (2023-10-16) | BSL 1.1. Each version converts to MPL 2.0 (Mozilla Public License 2.0) four years after release: 2.4.0 on 2027-10-16 and 2.4.9 on 2029-08-21 |
| 2026-03-11 | The licensor changed to IBM (#13791) |
| 2026-11-02 | main switched back to MIT. No release yet |

Why switch back to MIT now? I could not find anything that explains it. The PR description has a single line, "Reverts the license update returning to the MIT license.", and I found no announcement on hashicorp.com, HashiCorp Discuss, or Hacker News. Terraform, Packer, and Vault, also HashiCorp products, are still under the BSL, so it is hard to read this as a change in HashiCorp's overall license policy.

Whatever the reason, the change does matter in a few ways. First, with main now under MIT, the code from 2.4 onward can be forked under the MIT license. Distributions such as Debian and Fedora, which said they would not package BSL versions, may also be able to package current code again. But only main has changed, so releases up to 2.4.9 remain under the BSL as published, and HashiCorp has not said when a release under the MIT license (an **MIT release** below) will come out.

## Four things to watch

Is Vagrant on its way to being retired as well? A useful comparison is ingress-nginx in Kubernetes. For ingress-nginx, Kubernetes SIG (Special Interest Group) Network and the Security Response Committee announced its retirement on November 11, 2025, and said that after maintenance stopped in March 2026 there would be no more releases, bug fixes, or security fixes. The repository was archived, and its last release was a Helm chart on March 19, 2026.

Vagrant has had no retirement announcement and no archiving, and its license actually went back to MIT, so it has not been officially retired. Still, there has been no release since 2.4.9 and issues like the macOS port forwarding bug have not even been triaged, so fixes for problems caused by operating system changes are not getting released in time. I think the four things below are the ones to watch to judge where Vagrant is heading.

| What to watch | Why it matters |
|---|---|
| An MIT release | Fixes that are only on main since 2.4.9 (the Ansible option, the Hyper-V disk fix, and others) would ship with it |
| What happens to #13845 and #13842 | The macOS port forwarding bug is only officially fixed by a release built with Ruby 3.4.11 or later, or a release that includes #13842 |
| Support for the next VirtualBox version | The next minor or major version also needs a new Vagrant release before you can use it |
| Ruby 3.3 end of life (2027-03-31) | Ruby 3.3 itself gets no security fixes after that, so a Vagrant release with a newer Ruby is needed |

Even if HashiCorp stops maintaining Vagrant, the community could fork it and carry it on, but I think that would be hard in practice. Vagrant ships per-OS installers that bundle Ruby, so a fork would have to build those installers as well as maintain the code. On top of that, I could not find a fork that was actively maintained during the BSL period.

Next, let's look at the tools you can use instead of Vagrant and what each one lacks.

## Tools you can use instead of Vagrant

You might of course decide to move to another tool. To judge which one, it helps to first break down what Vagrant does for you, which comes down to these five things.

- Building the same lab environment on Windows, macOS, and Linux from one Vagrantfile
- Creating several VMs at once from a single Vagrantfile
- Assigning static IPs to VMs on a host-only network
- Distributing a prebuilt image (a box) to other people
- Running a range of guests, including Windows and network devices

The general-purpose VM tools are Multipass from Canonical, Lima from earlier, Incus for managing containers and VMs on Linux, UTM, a virtualization app for macOS, and OrbStack, which runs Linux environments on macOS (free for personal use, $8 per user per month for business use). Comparing these five against the criteria above gives the following.

| Tool | Host OS | Several VMs from one file | Static IP | Image distribution | Windows and network device guests |
|---|---|---|---|---|---|
| Vagrant + VirtualBox | All (Apple Silicon runs Arm guests only) | Yes | Yes | Yes (boxes) | Yes (x86 hosts) |
| Multipass | All | No | Not by default (separate guide for Linux only) | Yes (by URL, from 1.16) | No |
| Lima | Windows is experimental | No (one YAML per VM) | No (no option) | Yes (image URL and sha256) | Windows is experimental |
| Incus | Server runs on Linux only | With separate tools (OpenTofu, Incant) | Yes | Yes | Yes |
| UTM | macOS only | No | Set by hand | `.utm` files | Yes (x86 is emulated on Apple Silicon) |
| OrbStack | macOS 14 or later only | No | No (dynamic IPs) | No | Linux only |

Among the tools compared here, only Vagrant with VirtualBox covered all five. That holds for x86 hosts, though: on Apple Silicon Macs, every tool has trouble running x86 guests. On Apple Silicon, VirtualBox also supports Arm guests only, and guests built for x86, such as x86 Windows Server, NX-OSv, and Cumulus VX, can only run under emulation in other tools too.

In practice, projects that ended Vagrant support picked a tool for each use rather than moving everything to one tool. Trellis, mentioned earlier, moved to Lima, and netlab is moving to containerlab. The alternatives also change quickly, in features and in licenses. Canonical changed the Windows driver and removed the Blueprints feature in Multipass 1.17 in October, and the documentation says the VirtualBox driver will not be available from 1.18. Tart, a virtualization tool for Apple Silicon only, moved its repository to `openai/tart` after its developer announced on April 7 that it had joined OpenAI, and in June its license changed to FSL-1.1-ALv2, from the FSL (Functional Source License) family, which blocks only competing products and turns into Apache 2.0 after two years.

By use case, for Kubernetes labs kind or minikube can create multi-node clusters easily, but if you use kind with Docker Desktop, Docker Desktop requires a paid subscription at companies above a certain size (based on 250 employees or $10 million in revenue). Both also automate the kubeadm step that adds nodes to the cluster, so they are not a good fit for learning the process itself: installing a container runtime and joining nodes with `kubeadm join`. If you do not need to cover that process, kind may be enough, and Manning's "Kubernetes in Action, Second Edition" uses kind.

If you do need to cover kubeadm, you can create several VMs with Multipass or Lima and add them to the cluster yourself. For example, KodeKloud's CKA (Certified Kubernetes Administrator) course repository gives separate setups: Vagrant with VirtualBox for Windows and Intel Macs, and Multipass for Apple Silicon. The Multipass setup cannot assign static IPs, so it writes the DHCP-assigned IPs into `/etc/hosts`. Note that this guide was written in March and April 2024, before VirtualBox 7.1 supported Apple Silicon, and its Vagrant setup uses `ubuntu/jammy64`, an amd64 box, so it still does not run on Apple Silicon.

For network labs, some projects are moving to containerlab, as netlab is. containerlab needs Linux and Docker, though, so it has to run in WSL2 on Windows and inside a VM on macOS. Network device images such as NX-OSv, VyOS, and Cumulus VX are VM based and need **nested virtualization**, which on a Mac is only supported on M3 or later chips with macOS 15 or later, and the containerlab documentation asks users to report which images work because that is not yet settled.

You can also run labs in a browser with nothing to install. Killercoda offers free one-hour sessions and includes a two-node environment built with kubeadm. Play with Kubernetes, a similar service, shut down on March 1, 2026.

So you can move by choosing a tool for each use, but you will likely end up maintaining separate documentation and scripts for each tool.

## Wrapping up

That covers the HCP Vagrant shutdown and the state of Vagrant. To sum up, HCP Vagrant goes away on December 31, but the Vagrant CLI stays and boxes you have already downloaded keep working. Because Vagrant ships with its own Ruby, though, new problems like the macOS port forwarding bug cannot be solved by a Ruby fix alone and need a new Vagrant release, and there has been none since 2.4.9. The main branch went back to MIT on November 2, but I could not find any announcement explaining why, and there is no MIT release yet. I plan to keep using Vagrant until I find a tool that can do everything it does for me. In the meantime I will watch whether an MIT release comes out, whether the macOS port forwarding bug gets fixed, whether the next VirtualBox version is supported, and whether a release with a newer Ruby ships before Ruby 3.3 reaches end of life in March 2027.

If you publish boxes like I do, you need to move them before December 31 regardless of what happens to Vagrant. The next post covers where to move them and how other publishers are responding. I hope this post helps if you are deciding whether to keep using Vagrant.

## References

- HCP Vagrant end-of-life page: https://developer.hashicorp.com/hcp/docs/vagrant/hcp-vagrant-eol
- HashiCorp blog, HCP Vagrant deprecation: https://www.hashicorp.com/en/blog/hcp-vagrant-deprecation-important-dates-and-migration-guidance
- Shutdown announcement, hashicorp/vagrant#13836: https://github.com/hashicorp/vagrant/issues/13836
- HashiCorp Discuss announcement: https://discuss.hashicorp.com/t/deprecation-of-hcp-vagrant/77619
- PR that moved the schedule up, web-unified-docs#3256: https://github.com/hashicorp/web-unified-docs/pull/3256
- Export tool vagrant-registry-export: https://github.com/hashicorp/vagrant-registry-export
- PR that switched back to MIT, hashicorp/vagrant#13858: https://github.com/hashicorp/vagrant/pull/13858
- macOS port forwarding issue, hashicorp/vagrant#13845: https://github.com/hashicorp/vagrant/issues/13845
- Vagrant-side fix PR, hashicorp/vagrant#13842: https://github.com/hashicorp/vagrant/pull/13842
- Ruby Bug #22223: https://bugs.ruby-lang.org/issues/22223
- Ruby fix, ruby/ruby#18203: https://github.com/ruby/ruby/pull/18203
- Ruby branch maintenance status: https://www.ruby-lang.org/en/downloads/branches/
- ingress-nginx retirement announcement: https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/
- netlab vagrant-libvirt sunset, ipspace/netlab#3879: https://github.com/ipspace/netlab/issues/3879
- ipSpace, Sunsetting vagrant-libvirt: https://blog.ipspace.net/2026/09/sunsetting-vagrant-libvirt/
- Roots, Trellis drops Vagrant support in favor of Lima: https://roots.io/trellis-drops-vagrant-support-in-favor-of-lima/
- Ubuntu documentation on Vagrant: https://ubuntu.com/docs/public-images/public-images-explanation/vagrant/
- KodeKloud CKA course kubeadm-clusters: https://github.com/kodekloudhub/certified-kubernetes-administrator-course/tree/master/kubeadm-clusters
- containerlab on macOS: https://containerlab.dev/macos/
- Docker Desktop license: https://docs.docker.com/subscription/desktop-license/
- LinkedIn post on the HCP Vagrant shutdown that got me started (2026-11-02): https://lnkd.in/p/gd_jB9Dd
