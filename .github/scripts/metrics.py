"""Builds a real GitHub metrics section from the GitHub GraphQL API
and writes it into README.md between the METRICS markers.
Uses only the standard library and the built-in GITHUB_TOKEN."""
import json, os, re, sys, urllib.request
from datetime import datetime, timezone, date

USER = os.environ.get("GH_USER", "Amalendu7407")
TOKEN = os.environ["GITHUB_TOKEN"] if "GITHUB_TOKEN" in os.environ else None

QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    createdAt
    followers { totalCount }
    following { totalCount }
    repositories(ownerAffiliation: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        stargazerCount
        forkCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
    pullRequests { totalCount }
    mergedPRs: pullRequests(states: MERGED) { totalCount }
    issues { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        payload = json.load(r)
    if "errors" in payload:
        sys.exit(f"GraphQL error: {payload['errors']}")
    return payload["data"]["user"]


def streaks(days):
    counts = [(date.fromisoformat(d["date"]), d["contributionCount"]) for d in days]
    counts.sort()
    longest = run = 0
    for _, c in counts:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    # current streak: walk back from today (today may still be 0)
    current = 0
    i = len(counts) - 1
    if i >= 0 and counts[i][1] == 0:
        i -= 1
    while i >= 0 and counts[i][1] > 0:
        current += 1
        i -= 1
    return current, longest


def bar(pct, width=20):
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


def render(u):
    repos = u["repositories"]["nodes"]
    stars = sum(r["stargazerCount"] for r in repos)
    forks = sum(r["forkCount"] for r in repos)
    cc = u["contributionsCollection"]
    cal = cc["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    current, longest = streaks(days)

    langs = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    total = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda x: -x[1])[:6]

    joined = datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)

    out = []
    out.append("| 📌 Overview | | 🔥 Last 12 months | |")
    out.append("|---|---|---|---|")
    out.append(f"| 📦 Public repos | **{u['repositories']['totalCount']}** | 📝 Contributions | **{cal['totalContributions']}** |")
    out.append(f"| ⭐ Stars earned | **{stars}** | 💾 Commits | **{cc['totalCommitContributions']}** |")
    out.append(f"| 🍴 Forks | **{forks}** | 🔀 Pull requests | **{cc['totalPullRequestContributions']}** |")
    out.append(f"| 👥 Followers | **{u['followers']['totalCount']}** | 🐞 Issues | **{cc['totalIssueContributions']}** |")
    out.append(f"| ➡️ Following | **{u['following']['totalCount']}** | 👀 PR reviews | **{cc['totalPullRequestReviewContributions']}** |")
    out.append(f"| 🔀 PRs opened (all time) | **{u['pullRequests']['totalCount']}** | ✅ PRs merged (all time) | **{u['mergedPRs']['totalCount']}** |")
    out.append(f"| 📅 On GitHub since | **{joined.strftime('%b %Y')}** | 🔥 Streak (current / longest) | **{current} / {longest} days** |")
    out.append("")
    out.append("**Top languages (by code in my public repos)**")
    out.append("")
    out.append("| Language | Share | |")
    out.append("|---|---|---|")
    for name, size in top:
        pct = size / total * 100
        out.append(f"| {name} | {pct:.1f}% | `{bar(pct)}` |")
    out.append("")
    out.append(f"<sub>Real data from the GitHub API, auto-updated on {now.strftime('%d %b %Y, %H:%M UTC')}. Public activity only.</sub>")
    return "\n".join(out)


def write_readme(block):
    with open("README.md", encoding="utf-8") as f:
        s = f.read()
    pat = re.compile(r"(<!--METRICS:START-->).*?(<!--METRICS:END-->)", re.S)
    if not pat.search(s):
        sys.exit("Markers <!--METRICS:START--> / <!--METRICS:END--> not found in README.md")
    s = pat.sub(lambda m: f"{m.group(1)}\n{block}\n{m.group(2)}", s)
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(s)


if __name__ == "__main__":
    if not TOKEN:
        sys.exit("GITHUB_TOKEN is not set")
    write_readme(render(fetch()))
    print("README metrics updated")
