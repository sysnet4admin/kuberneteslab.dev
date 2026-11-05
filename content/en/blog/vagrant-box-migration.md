---
title: "Where should Vagrant boxes go when Vagrant Cloud shuts down?"
date: 2026-11-05T08:25:00+09:00
draft: false
tags: ["vagrant", "hcp-vagrant", "box", "cloudflare-r2", "github-releases", "github-pages", "virtualbox"]
categories: ["Tools"]
description: "When HCP Vagrant (formerly Vagrant Cloud) shuts down on December 31, 2026, any Vagrantfile that only names a box will fail in every environment that downloads that box for the first time. This post looks at how other projects are responding and where boxes can be hosted, then covers the trade-offs I measured while moving the sysnet4admin boxes to Cloudflare R2 and GitHub (Releases and Pages), what to check before December 31, and what to keep an eye on after the move."
summary: "How Vagrantfiles behave after Vagrant Cloud shuts down, how other projects are responding, where boxes can be hosted, the trade-offs between Cloudflare R2 and GitHub, and how I set up the sysnet4admin boxes with a checklist for after the move."
ShowToc: true
TocOpen: true
cover:
    image: "/images/og/vagrant-box-migration.jpg"
    alt: "Where should Vagrant boxes go when Vagrant Cloud shuts down?"
    hidden: true
---

In the [previous post](https://kuberneteslab.dev/en/blog/vagrant-after-hcp-shutdown/) I looked at how **HCP Vagrant** shuts down on December 31, 2026, and how Vagrant itself has had no release since 2.4.9. HCP Vagrant is the public service that Vagrant, HashiCorp's virtual machine (VM) management tool, downloads **boxes** (the image files Vagrant uses to create VMs) from, and it was called Vagrant Cloud until it became part of HCP (HashiCorp Cloud Platform) in 2024. This post covers where to move boxes before the shutdown.

I publish seven boxes for Kubernetes and Ansible labs under the sysnet4admin account, and `CentOS-k8s` alone has 19,650 downloads (as of November 2). The lab Vagrantfiles in my books and courses use these box names too, so while moving them I also looked at how other projects were responding, and in Korea I found no public response other than two personal repositories that moved to GitHub Releases. So I wrote up what I researched and measured for anyone who publishes or uses boxes.

The short answer is that the most common approach is to put the box files and a **catalog** (`metadata.json`, a JSON file listing a box's versions and file URLs) on static hosting and set the catalog URL in `config.vm.box_url` in the Vagrantfile, and I chose the same approach. For hosting I use Cloudflare R2, Cloudflare's object storage service, as the primary store, with GitHub Releases (files attached to releases in a GitHub repository) and GitHub Pages (GitHub's static site hosting) as a backup. Neither R2 nor GitHub costs anything at my scale, but each has weak points, so I decided one alone was not enough. Everything here is as of November 3, 2026.

## How Vagrantfiles behave after December 31

Let's start with how existing Vagrantfiles behave after the shutdown. I read the Vagrant source, served a catalog from a local HTTP server, and pointed the default server address (`https://vagrantcloud.com`) at a closed port to simulate the shutdown. The result depended on how the Vagrantfile and environment variables were set and on whether the box had already been downloaded, as shown below.

| Case | After December 31 |
|---|---|
| The Vagrantfile only names the box, and it has never been downloaded | Fails (`BoxAddShortNotFound`) |
| `box_url` set to the new catalog URL | Downloads from the new catalog, and SHA-256 checks and `vagrant box outdated` work too |
| Vagrantfile unchanged, `VAGRANT_SERVER_URL` set to a new address | Works with static hosting alone (when the `/<account>/<box>` path at that address returns the catalog as `application/json`) |
| Box already downloaded | Keeps working, and a failed update check only prints a warning |

![A flow that asks whether the box is already downloaded, whether box_url is set, and whether VAGRANT_SERVER_URL is set, leading to the result after December 31](/images/vagrant-box-after-shutdown-en.svg "Checking how your Vagrantfile behaves after December 31")

The first case is hit hardest because, given only a box name, Vagrant looks up `{server}/api/v2/vagrant/<name>` and then `{server}/<name>`, and returns an error if both fail. That means any environment downloading the box for the first time fails, such as a new CI runner, a new laptop, or a reinstalled machine. A machine that already has the box is fine for now, but `vagrant box update` keeps looking at the address saved when the box was first added (`~/.vagrant.d/boxes/<name>/metadata_url`), so you need to run `vagrant box add` once from the new catalog to change it.

A few more behaviors are worth knowing when you use `box_url`. Vagrant sends a HEAD request to that URL and treats it as a catalog if the Content-Type is `application/json`, and as a single box file otherwise, based on the final response after redirects. The catalog's `name` must match `config.vm.box` exactly, including case, or you get a `BoxAddNameMismatch` error. And if you set `box_url` to an array, Vagrant falls back to the next URL when one fails, but only for box file URLs: setting two or more catalog URLs results in a `BoxAddMetadataMultiURL` error.

Because my test pointed the default server at a closed port, I could not confirm whether the real vagrantcloud.com will refuse connections, return 404, or show some other page after December 31. HashiCorp's promised static archive that would redirect existing addresses during the transition had not appeared as of November 3 either, so for now it is safest to assume that a Vagrantfile naming only the box will fail on first download.

## How other projects are responding

So how are other projects handling this? HashiCorp has not released a replacement registry (a service like HCP Vagrant that lets you find and download boxes by name), so everyone has to host their own, and box publishers have taken four approaches.

| Approach | What it means | Examples |
|---|---|---|
| Static hosting and `box_url` | Put box files and a catalog on static hosting and set the catalog URL in the Vagrantfile. The most common approach | Oracle Linux (this way from the start), one personal box repository in Korea |
| `VAGRANT_SERVER_URL` | Users set the address in an environment variable and the Vagrantfile only names the box | AlmaLinux |
| Build it yourself | For images that cannot be redistributed, ship only build scripts and let users build them | Some network device images with license restrictions, Windows evaluation images |
| Stop publishing boxes | Stop releasing boxes, or drop Vagrant for something else (some before the shutdown announcement) | Arch Linux, Ubuntu (from 24.04), projects that only used Vagrant in CI |

Among these, official distributions differ depending on where their box files live. Distributions that keep files on their own servers and only registered the URLs on HCP Vagrant keep their files after December 31 and just can no longer be found by name, while those that uploaded files to HCP Vagrant lose the files too. Here is how each distribution stands.

| Distribution | Box file or catalog location | Status |
|---|---|---|
| AlmaLinux | Own storage (`vagrant.almalinux.org`) | Announced its catalog on November 2; supports both `VAGRANT_SERVER_URL` and `box_url` |
| Oracle Linux | JSON catalog on `oracle.github.io` | Used `box_url` from the start, so nothing changes |
| Ubuntu | `cloud-images.ubuntu.com` | Older box files remain. No boxes from 24.04 |
| CentOS | `cloud.centos.org` | Files remain. No announcement |
| Rocky Linux | `dl.rockylinux.org` | The VirtualBox amd64 entry for `rockylinux/9` points at a removed 9.6 path and already returns 404 |
| Fedora | Distribution servers | Registration on HCP Vagrant stopped at 41. 44 boxes are on the servers but there is no catalog |
| Debian | HCP Vagrant | The latest box (2026-05-19) is libvirt only, and the maintainer said they plan to maintain trixie64 boxes for libvirt |
| Kali, FreeBSD | HCP Vagrant | No announcement. Kali 2026.3 has no box, and FreeBSD stopped at 13.4 in 2024 |

Boxes maintained outside the distributions are in more varied shape. gusztavvargadr, who publishes 51 boxes, has already put the box files on Cloudflare R2 and is choosing between a static catalog announced through `box_url` and a registry server announced through `VAGRANT_SERVER_URL`, with a decision planned for early November and a switch in December (#614). chef/bento, on the other hand, has had no maintainer response to a proposal to move to the GitLab package registry and GitLab Pages (#1699), and its last activity was on October 6. lavabit/robox, which published the generic/* boxes, only has a comment saying the maintainer has been away for a long time and its status is unknown (#311). Jeff Geerling, author of "Ansible for DevOps" and mentioned in the previous post, has not announced anything about his boxes either, and their files are all on HCP Vagrant.

People have also reported pitfalls. In one case, re-releasing a box with a lower version (0.3.0 after 1.1.0) left users who already had 1.1.0 on 1.1.0. There is also an issue (theforeman/foremanctl#886) saying HCP Vagrant often returned 502 errors in September and October, so downloads can fail even before the shutdown. Another issue (theforeman/foremanctl#903) reported that Vagrant still looked up the registry even with `box_url` set, but there `box_url` pointed at a box file, not a catalog. I confirmed from the source and by testing that Vagrant does not look up the registry when `box_url` points at a catalog.

## Hosting options I looked at

So where can boxes go? Here are the hosting services compared by whether Vagrant can download from them without extra setup.

| Hosting | Single file size | Cost | Can Vagrant use it directly? |
|---|---|---|---|
| GitHub Releases | Under 2 GiB, 1,000 assets per release | Free, no bandwidth limit | Boxes yes. Catalogs no (`application/octet-stream`) |
| GitHub Pages | 1 GB per site, 100 GB per month recommended | Free | Catalogs yes (`.json` URLs) |
| GitLab generic package registry | 5 GB | Free for public projects | From the chef/bento#1699 summary; not checked myself |
| Cloudflare R2 | About 4.995 GiB in a single upload | $0.015 per GB per month, 10 GB free, free egress | Yes. Used with a custom domain |
| Amazon S3 | N/A | Storage and egress charges | Yes. HashiCorp's guide only shows pointing at box files directly |
| Internet Archive | Recommended maximum about 500 GB | Free | Yes. No guarantee of permanent preservation |
| Zenodo | 50 GB and 100 files per record | Free | Boxes likely yes; catalogs not tested |
| Hugging Face | 500 GB | Free (best effort) | Catalogs no (`text/plain`). Boxes are not machine learning data, so it does not fit the policy either |
| ghcr.io, Docker Hub (OCI, Open Container Initiative) | 10 GB per layer on ghcr.io | Free for public | No. Even anonymous requests need a token exchange, which Vagrant does not do |
| JFrog Artifactory | N/A | Paid | Yes. Has a Vagrant repository type |

Whether Vagrant can use a host directly came down mostly to the catalog's Content-Type. As covered above, Vagrant only reads a response as a catalog when it is `application/json`, and in my tests GitHub Releases served assets as `application/octet-stream`, so only box files could go there. GitHub Pages served a file without an extension as `application/octet-stream`, so the catalog only worked with `.json` at the end of the URL. Object storage such as Cloudflare R2 or Amazon S3, on the other hand, lets you set the Content-Type per object at upload, so you can serve a catalog at an extensionless URL like `/sysnet4admin/Ubuntu-k8s`, and that is what lets static hosting alone support the `VAGRANT_SERVER_URL` approach.

So there is no need to run a registry server with an API like HCP Vagrant's. There are open source servers that implement the same API, but most are small, stopped development between 2015 and 2023, and the recent ones are reference implementations.

## Cloudflare R2 vs. GitHub

From these I chose Cloudflare R2 and GitHub (Releases and Pages). Unlike S3, R2 does not charge for egress, so more downloads do not mean transfer costs, and GitHub is free. But when I uploaded the same boxes to both and measured, each came out ahead on different items. I measured from a corporate network in Seoul (LG U+) and from two GitHub Actions runners in the US, and the corporate network caps out around 120 to 140 Mbps, so I could not tell the two apart on speed in Korea. Here are the measured items together with what I checked in the documentation.

| Item | Cloudflare R2 | GitHub Releases and Pages | Better |
|---|---|---|---|
| Single file size | About 4.995 GiB in one upload, about 4.995 TiB in multipart | Under 2 GiB | R2 |
| Cost | Free up to 10 GB, then $0.015 per GB per month, free egress | Free | Same at small scale |
| Payment method | An R2 subscription needs a payment method, and requests fail if payment fails | Not needed | GitHub |
| Catalog URL | Can serve JSON at an extensionless URL, so `VAGRANT_SERVER_URL` works too | Pages URLs need `.json`, and `VAGRANT_SERVER_URL` does not work | R2 |
| PoP serving Korea (measured) | Cloudflare Hong Kong. Not cached | Seoul cache of Fastly, the CDN GitHub uses | GitHub |
| Speed (measured) | Same as GitHub on the Korean corporate network (about 14 to 15 MB/s). Full file 23 to 45 MB/s in the US | Full file 52 to 82 MB/s in the US | GitHub |
| Requests without login | No known limit on custom-domain requests | Limits tightened from May 2025, and three outages affected only requests without login | R2 |
| Download counts | Countable per object with the GraphQL Analytics API (token needed) | `download_count` per asset, visible to anyone via the API (counting rules are not documented) | GitHub |
| Immutability | Not checked. Verified with the SHA-256 in the catalog | With immutable releases enabled, assets cannot change, and SHA-256 is exposed via the API | GitHub |
| Terms of service risk | R2 is not named among the exceptions to the large-file clause, so it needs interpretation, and content is blocked when a complaint comes in | Excessive bandwidth clause, and a DMCA (Digital Millennium Copyright Act) notice can disable the whole repository | Both have some |
| SLA (Service Level Agreement) | 99.9% monthly, but credits are based on fees paid, so nothing within the free tier (not confirmed whether it applies to free usage) | No SLA on the free plan | Same |

Somewhat unexpectedly, GitHub was faster in the US. Looking into why, first, Cloudflare says it serves free-plan traffic "wherever there is spare room", and my blog domain is on the free plan too, which appears to be why requests from Korea went to Hong Kong. On top of that, Cloudflare decides what to cache by file extension by default, and `.box`, `.json`, and extensionless files are not on the default list, so they are not cached. Even with a cache rule, the free plan does not cache files over 512 MB, so boxes (0.7 to 1 GB) still are not cached. Each request therefore appears to go all the way to the bucket in the Asia-Pacific region, and from the US, far from the bucket, R2 was slower than GitHub. That said, the runners I used in the US sit on Microsoft's network and GitHub release assets live in Azure Blob Storage, which may have favored GitHub. And in Korea I only measured on the LG U+ corporate network, so other carriers such as KT and SK Broadband were outside what I measured.

![For Seoul, Phoenix, and Boydton, one row each showing the PoP and bucket a request passed through on Cloudflare R2 and GitHub, alongside the measured speed](/images/vagrant-box-path-speed-en.svg "Where box requests went and how fast they were, by location")

If speed was R2's weak point, GitHub's was how it handles requests without login. Vagrant always downloads boxes without logging in, and when GitHub tightened limits on requests without login on May 8, 2025, it did not publish the numbers or say whether Releases and Pages were included. Separately, there were outages that affected only requests without login on December 22, 2025 (31 minutes, requests from inside GitHub Actions), June 8, 2026 (about 2 hours), and August 12 to 13 (about 7.7 hours in total), all in UTC, and for the latter two GitHub said signed-in users were not affected. I could not confirm how the tighter limits apply when dozens of students in a classroom share one public IP and download the same box at once. However, in a test that sent 100 HEAD requests from one IP, 10 at a time, none of the four URLs (Releases, Pages, the R2 catalog, and the R2 box) were blocked.

Downloading a box from GitHub Releases also redirects to a signed URL, and for these box files that URL was valid for one hour. When a transfer breaks, re-running Vagrant requests the original URL again and resumes (per the source), so it gets a fresh URL and continues. I did not test whether a single transfer longer than 60 minutes gets cut off, though. That can happen where many people share one line: downloading 1 GB in 60 minutes needs about 2.2 Mbps, which is roughly what each person gets when 45 people share a 100 Mbps line. There are also reports that the signed URL host changed to `release-assets.githubusercontent.com` around late April 2025, and there were cases where downloads failed on corporate networks that only allow listed hosts. If you cannot download boxes on a school or corporate network, that host change may be the reason.

So neither side wins on everything, and it makes sense to choose by situation.

- To start small without a payment method, GitHub Releases (box files) with GitHub Pages (catalog)
- If you have boxes over 2 GiB, object storage such as R2 or S3
- If you need to offer `VAGRANT_SERVER_URL` because a Vagrantfile cannot be changed, as with printed books, or you want short URLs, R2 with a custom domain
- If many people download from one public IP, as in a classroom, R2 rather than GitHub, whose limits on requests without login are not published

## How I set up the sysnet4admin boxes

So I put the sysnet4admin boxes on both R2 and GitHub, serving them from R2 normally and from GitHub when R2 has trouble. Users connect to a single address, `box.kuberneteslab.dev`, and if something goes wrong I enable failover redirect rules in Cloudflare that I created in advance and keep disabled, which send requests to GitHub. The figure below shows the setup.

![Requests go through box.kuberneteslab.dev to Cloudflare R2 normally, to GitHub Pages and Releases after failover, and straight to the Pages URLs if Cloudflare itself is down](/images/vagrant-box-topology-en.svg "How box.kuberneteslab.dev routes requests to the backends")

So you add one line to the Vagrantfile, as below, and where the Vagrantfile cannot be changed, as with printed books, you set `VAGRANT_SERVER_URL=https://box.kuberneteslab.dev`.

```ruby
config.vm.box     = "sysnet4admin/Ubuntu-k8s"
config.vm.box_url = "https://box.kuberneteslab.dev/sysnet4admin/Ubuntu-k8s"
```

At first I considered putting the catalogs on GitHub Pages and printing that address in my books, so the address would not depend on renewing a domain or on a Cloudflare account. But using my own domain as the address lets me serve catalogs at extensionless URLs, so `VAGRANT_SERVER_URL` works too. And because Vagrant stores the original URL rather than the final one after redirects, I can change the redirect target later and the update checks of users who already have the box will follow it. In exchange I have to keep renewing the `kuberneteslab.dev` domain and keep it on Cloudflare for as long as the books are on sale, and I decided these two benefits outweigh that burden.

Failing over from R2 to GitHub could be automated with Cloudflare Workers, Cloudflare's serverless runtime, but that adds code to maintain, so I chose to enable the rules by hand. In my test, the switch took effect within 20 seconds of enabling the rules.

I split the boxes into three groups by where and how often they are used, as shown below.

| Group | Boxes | R2 | GitHub |
|---|---|---|---|
| Group 1 (used often) | `Ubuntu-k8s` 1.0.0 (amd64, arm64) | Uploaded | Copy uploaded |
| Group 2 (used occasionally) | `CentOS-k8s` 0.8.0 | Uploaded | Copy uploaded |
| Group 3 (rarely used) | Network device boxes (`nxosv_v7`, `nxosv_v9`, `VyOS`) | Catalog only | Uploaded |

`CentOS-k8s` has the most downloads, but I moved my courses to Ubuntu boxes, so it is in group 2. The network device boxes are mostly used by older Ansible books and courses, so their files are only on GitHub. I did not move `Rocky8`, which none of my books or courses use, and I did not move the Windows box this time; how to provide it is still being decided. I also moved only the latest version of each box, and if a box needs a fix I will publish a new version such as 1.0.1 after 1.0.0 instead of overwriting the existing one. The exception is `nxosv_v9`: its latest version, 9.3.5, is 3.51 GiB and exceeds the GitHub Releases file size limit (under 2 GiB), so I uploaded 9.2.3 instead.

On GitHub I created two repositories under the `vg-box` organization. `vg-box/k8s` holds copies of the group 1 and 2 boxes and the failover catalogs (on Pages), and `vg-box/ansible` holds the group 3 boxes, split so that a problem with `vg-box/ansible` does not affect `vg-box/k8s` or R2. Each box version gets one release, tagged `<box>-<version>`, with a `SHA256SUMS` file attached to the same release. On the R2 side, the three box files uploaded so far total 2.63 GB, which is within the free tier, so it costs nothing.

There are still two cases where there is no fallback and boxes cannot be downloaded.

**The first is when the Cloudflare proxy goes down.** The address's domain depends on Cloudflare alone, and the redirect rules run on the same proxy, so I expect I would not be able to fail over to GitHub in that case. For that, the boxes can also be downloaded directly from the GitHub Pages URLs (`vg-box.github.io/k8s/...json`).

**The second is when GitHub has a problem.** The group 3 boxes are only on GitHub, so they cannot be downloaded then.

## What to check before December 31

Here is a summary of the above, split into what box publishers and box users should do.

### If you publish boxes

- Create a catalog and set `box_url` to the catalog URL rather than a box file. Pointing `box_url` straight at a box file means you lose versioning and `vagrant box update`.
- Put SHA-256 checksums in the catalog. With a checksum, a download fails when the file differs from the original, so you can tell if a file has changed. In fact, none of the 42 files across my 7 boxes on HCP Vagrant had a checksum registered.
- Keep the existing `<account>/<box>` name, and match the catalog's `name` exactly, including case, so users who already have the box can keep using it under the same name.
- Serve the catalog as `application/json`. To support `VAGRANT_SERVER_URL` as well, put the catalog at an extensionless `/<account>/<box>` path.
- Publish fixed boxes as a new version such as 1.0.1, never a lower one.
- The `metadata.json` written by vagrant-registry-export, the export tool HashiCorp released, points at local paths on the machine that ran it, so rebuild it for the new URLs.
- R2's default address (`r2.dev`) is rate limited and meant for development, so connect a custom domain.
- Do not put boxes in a Git repository or Git LFS (Large File Storage). GitHub does not accept files over 100 MiB in a repository, and GitHub's free LFS plan has 10 GiB of bandwidth per month, which a few box downloads will use up.
- Use the AWS CLI to upload large files to R2. wrangler, Cloudflare's command line tool, only supports files up to 300 MiB.
- HCP Vagrant can return 502 errors even before the shutdown, so download your existing boxes as soon as you can.
- Once you have moved everything, it is worth testing `vagrant box add` with the default server address unreachable. I checked the post-shutdown situation by pointing the default server address at a closed port.

### If you use boxes

- Pin the box version with `config.vm.box_version` and download it now.
- You can write a `metadata.json` for a downloaded file and set it as `box_url`, or add it with `vagrant box add ./metadata.json`, and when you use `box_url`, put the checksum in that catalog as well.
- If the publisher announces a new catalog, run `vagrant box add` once from it to switch the update check address.
- Images that cannot be redistributed have to be built yourself with the publisher's build scripts and Packer, HashiCorp's image build tool.

## What to keep an eye on after the move

Publishers still have things to look after once the boxes have moved. Most of this was HashiCorp's job while boxes lived on HCP Vagrant, and now publishers have to do all of it themselves.

- Domain renewal: the address sits under `kuberneteslab.dev`, so the domain has to keep being renewed before it expires for the address I put in my books to keep working.
- Payment method: if payment fails, R2 buckets become inaccessible and requests fail, and data may be deleted if the payment method is not updated within 30 days. So when the registered card expires, users may not be able to download boxes, and the domain renewal payment needs checking too.
- Failover path: enabling the redirect rules needs the Cloudflare dashboard or API, and in the September 12, 2025 outage both the dashboard and the API were down, and in the November 18 outage the dashboard was affected too. So if Cloudflare itself has a problem, I have to point users to the GitHub Pages URLs instead of relying on the rules.
- Security settings: Vagrant downloads with curl, so it cannot pass a browser challenge. Enabling Cloudflare's bot protection, Bot Fight Mode, or I'm Under Attack mode can therefore make `vagrant box add` fail, so it is worth downloading a box again after changing security settings.
- Download counts: GitHub shows `download_count` directly, but in my tests it did not count every GET request either, and the counting rules are not documented, so I treat it as approximate. Normally R2 serves the boxes, though, so I collect R2's numbers separately with the GraphQL Analytics API.

Apart from that, I also keep watching for changes in Vagrant itself. From the [previous post](https://kuberneteslab.dev/en/blog/vagrant-after-hcp-shutdown/), that means a release under the MIT license, what happens to the bug that makes `vagrant up` fail on macOS 26.7 and later, support for the next VirtualBox version, and whether a release with a newer Ruby ships before Ruby 3.3 reaches end of life.

## Wrapping up

That covers where to move boxes ahead of the HCP Vagrant shutdown. To sum up, a Vagrantfile that only names a box will fail in every environment that downloads it for the first time after December 31, so you need to host the box files and a catalog yourself and point users at them with `box_url` or `VAGRANT_SERVER_URL`. Both Cloudflare R2 and GitHub can run at no cost at my scale, but R2 needs a payment method to be maintained and is slow far from the bucket because nothing is cached, while GitHub has a file size limit and outages that hit requests without login, so I chose to use both.

HashiCorp's promised static archive had not appeared as of November 3, so I suggest moving your boxes rather than waiting for it. I hope this post helps if you publish or use boxes.

## References

- Previous post on the HCP Vagrant shutdown and the state of Vagrant: https://kuberneteslab.dev/en/blog/vagrant-after-hcp-shutdown/
- HCP Vagrant end-of-life page: https://developer.hashicorp.com/hcp/docs/vagrant/hcp-vagrant-eol
- HashiCorp storage migration guide (Amazon S3): https://developer.hashicorp.com/vagrant/vagrant-cloud/hcp-vagrant/storage-providers/aws
- Export tool vagrant-registry-export: https://github.com/hashicorp/vagrant-registry-export
- AlmaLinux Vagrant catalog announcement: https://almalinux.org/blog/2026-11-02-vagrant-catalog/
- gusztavvargadr/packer#614: https://github.com/gusztavvargadr/packer/issues/614
- chef/bento#1699: https://github.com/chef/bento/issues/1699
- lavabit/robox#311: https://github.com/lavabit/robox/issues/311
- theforeman/foremanctl#886: https://github.com/theforeman/foremanctl/issues/886
- theforeman/foremanctl#903: https://github.com/theforeman/foremanctl/issues/903
- About GitHub releases: https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
- GitHub Pages limits: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- GitHub rate limit change for unauthenticated requests (2025-05-08): https://github.blog/changelog/2025-05-08-updated-rate-limits-for-unauthenticated-requests/
- GitHub immutable releases: https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/immutable-releases
- Cloudflare R2 limits: https://developers.cloudflare.com/r2/platform/limits/
- Cloudflare R2 pricing: https://developers.cloudflare.com/r2/pricing/
- Cloudflare R2 public buckets: https://developers.cloudflare.com/r2/buckets/public-buckets/
- Cloudflare default cache behavior: https://developers.cloudflare.com/cache/concepts/default-cache-behavior/
- Cloudflare's commitment to free: https://blog.cloudflare.com/cloudflares-commitment-to-free/
