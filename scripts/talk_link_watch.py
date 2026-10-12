"""Archives 발표 목록(data/talks.yaml)에 빠진 링크 후보를 찾는다.

- YouTube: 영상 링크가 없는 최근 발표를 YouTube 검색 결과에서 찾는다. 올린 채널이 CNCF, 리눅스 재단,
  쿠버네티스 랩 중 하나이고 제목이 발표 제목과 거의 같을 때만 후보로 본다.
- sched: 세션 링크가 없는 발표에 sched_site(행사의 sched 주소)가 적혀 있으면 그 사이트에서 같은 제목의 세션을 찾는다.

찾은 후보를 JSON으로 출력하고 GitHub Actions가 이슈로 연다. data/talks.yaml은 고치지 않는다.
"""
import datetime as dt
import html
import json
import re
import sys
import urllib.parse
import urllib.request

import yaml

UA = {"User-Agent": "Mozilla/5.0 (kuberneteslab.dev talk-link-watch)", "Accept-Language": "en-US,en;q=0.8"}
CHANNELS = {
    "UCvqbFHwN-nwalWPjPUKpvTA": "CNCF",
    "UCfX55Sx5hEFjoC3cNs6mCUQ": "The Linux Foundation",
    "UC-3eHqOX_Qze5dRhCxJD-jw": "KubernetesLab",
}
RECENT_YEARS = 1  # 올해와 작년 발표만 본다


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read().decode("utf-8", "ignore")


def norm(s):
    s = html.unescape(s).lower().replace("’", "'")
    return re.sub(r"[^0-9a-z가-힣]+", " ", s).strip()


def similar(talk, video):
    a, b = norm(talk), norm(video)
    if not a or not b:
        return False
    if a in b:
        return True
    ta, tb = set(a.split()), set(b.split())
    return len(ta & tb) / max(1, len(ta)) >= 0.8


def text(v, lang="en"):
    return v.get(lang) if isinstance(v, dict) else v


def youtube_search(query):
    s = get("https://www.youtube.com/results?search_query=" + urllib.parse.quote(query))
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", s, re.S)
    if not m:
        raise RuntimeError("YouTube 검색 결과 형식이 바뀌었습니다")
    data = json.loads(m.group(1))
    out = []

    def walk(o):
        if isinstance(o, dict):
            if "videoRenderer" in o:
                v = o["videoRenderer"]
                title = "".join(r.get("text", "") for r in v.get("title", {}).get("runs", []))
                runs = v.get("ownerText", {}).get("runs", [{}])
                ch = runs[0].get("navigationEndpoint", {}).get("browseEndpoint", {}).get("browseId", "")
                out.append({"id": v.get("videoId"), "title": title, "channel": ch})
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)

    walk(data)
    return out


def sched_find(site, title):
    s = get(site.rstrip("/") + "/")
    for href, name in re.findall(r"href='(event/[^']+)'[^>]*><span class=\"session-title\">([^<]+)</span>", s):
        if similar(title, name.split(" - ")[0]):
            return site.rstrip("/") + "/" + href.split("/")[0] + "/" + href.split("/")[1]
    return None


def main():
    today = dt.datetime.now(dt.timezone.utc).date()
    talks = yaml.safe_load(open("data/talks.yaml", encoding="utf-8"))["talks"]
    found = []
    for t in talks:
        title = text(t["title"])
        year = int(str(t.get("date") or t.get("year"))[:4])
        labels = " ".join(text(l["label"]) for l in t.get("links", []))
        past = (t.get("date") or "0000") < today.isoformat() if t.get("date") else True
        if "youtube" not in labels.lower() and past and year >= today.year - RECENT_YEARS:
            try:
                for v in youtube_search(title):
                    if v["channel"] in CHANNELS and similar(title, v["title"].split(" - ")[0]):
                        found.append({"kind": "YouTube", "talk": title, "url": f"https://youtu.be/{v['id']}",
                                      "detail": f"{CHANNELS[v['channel']]}: {v['title']}"})
                        break
            except Exception as e:
                print(f"youtube skip {title[:40]}: {e}", file=sys.stderr)
        if t.get("sched_site") and not re.search(r"sched|schedule", labels, re.I):
            try:
                u = sched_find(t["sched_site"], title)
                if u:
                    found.append({"kind": "sched", "talk": title, "url": u, "detail": t["sched_site"]})
            except Exception as e:
                print(f"sched skip {title[:40]}: {e}", file=sys.stderr)
    print(json.dumps(found, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
