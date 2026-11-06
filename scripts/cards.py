import json
import math
import os
import sys
import urllib.request
from datetime import date
from html import escape

BG = "#0B0716"
BORDER = "#3B1A63"
PURPLE = "#7A16C9"
VIOLET = "#A855F7"
LILAC = "#C084FC"
CREAM = "#F3EBDD"
TEXT = "#CEC8F2"
MUTED = "#8F86D8"
FONT = "-apple-system, 'Segoe UI', Roboto, Ubuntu, Helvetica, Arial, sans-serif"

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, ISSUE, REPOSITORY]) { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100, orderBy: {field: STARGAZERS, direction: DESC}) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch(login, token):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "profile-cards"},
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(json.dumps(data["errors"]))
    return data["data"]["user"]


def frame(w, h, title, inner):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none" role="img" aria-label="{escape(title)}">
<style>
text {{ font-family: {FONT}; }}
@keyframes fade {{ from {{ opacity: 0; transform: translateY(6px) }} to {{ opacity: 1; transform: translateY(0) }} }}
@keyframes grow {{ from {{ transform: scaleX(0) }} to {{ transform: scaleX(1) }} }}
@keyframes draw {{ to {{ stroke-dashoffset: 0 }} }}
@keyframes show {{ to {{ opacity: 1 }} }}
@keyframes pulse {{ 0%,100% {{ opacity: .5 }} 50% {{ opacity: 1 }} }}
.fade {{ opacity: 0; animation: fade .6s ease forwards }}
.grow {{ transform-box: fill-box; transform-origin: left; transform: scaleX(0); animation: grow 1.1s ease forwards }}
.pulse {{ animation: pulse 2.4s ease-in-out infinite }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; opacity: 1 !important; transform: none !important; stroke-dashoffset: 0 !important }} }}
</style>
<rect x=".75" y=".75" width="{w - 1.5}" height="{h - 1.5}" rx="16" fill="{BG}" stroke="{BORDER}" stroke-width="1.5"/>
<text x="26" y="38" font-size="17" font-weight="600" fill="{VIOLET}">{escape(title)}</text>
{inner}
</svg>
"""


def short(n):
    if n >= 1000:
        return f"{n / 1000:.1f}k".replace(".0k", "k")
    return str(n)


def stats_card(u):
    stars = sum(r["stargazerCount"] for r in u["repositories"]["nodes"])
    cc = u["contributionsCollection"]
    rows = [
        ("Total stars", stars),
        ("Commits, last year", cc["totalCommitContributions"] + cc["restrictedContributionsCount"]),
        ("Pull requests", u["pullRequests"]["totalCount"]),
        ("Issues", u["issues"]["totalCount"]),
        ("Contributed to", u["repositoriesContributedTo"]["totalCount"]),
        ("Public repos", u["repositories"]["totalCount"]),
    ]
    out = []
    for i, (label, val) in enumerate(rows):
        y = 72 + i * 24
        out.append(
            f'<g class="fade" style="animation-delay:{0.15 + i * 0.12:.2f}s">'
            f'<circle cx="32" cy="{y - 4}" r="3" fill="{LILAC if i % 2 else VIOLET}"/>'
            f'<text x="44" y="{y}" font-size="13" fill="{TEXT}">{escape(label)}</text>'
            f'<text x="300" y="{y}" font-size="13" font-weight="700" fill="{CREAM}" text-anchor="end">{short(val)}</text></g>'
        )
    total = cc["contributionCalendar"]["totalContributions"]
    out.append(
        f'<g class="fade" style="animation-delay:.3s">'
        f'<circle cx="378" cy="118" r="44" stroke="{BORDER}" stroke-width="7"/>'
        f'<circle cx="378" cy="118" r="44" stroke="{VIOLET}" stroke-width="7" stroke-linecap="round" '
        f'stroke-dasharray="276.5" stroke-dashoffset="276.5" transform="rotate(-90 378 118)" '
        f'style="animation: draw 1.6s ease .4s forwards"/>'
        f'<text x="378" y="122" font-size="20" font-weight="700" fill="{CREAM}" text-anchor="middle">{short(total)}</text>'
        f'<text x="378" y="182" font-size="11" fill="{MUTED}" text-anchor="middle">contributions, last year</text></g>'
    )
    return frame(460, 220, "GitHub Stats", "\n".join(out))


def langs_card(u, top=6):
    sizes = {}
    colors = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            n = e["node"]["name"]
            sizes[n] = sizes.get(n, 0) + e["size"]
            colors[n] = e["node"]["color"] or LILAC
    items = sorted(sizes.items(), key=lambda kv: kv[1], reverse=True)[:top]
    total = sum(v for _, v in items) or 1
    palette = [VIOLET, LILAC, CREAM, PURPLE, "#E9D5FF", "#9333EA"]
    out = []
    x = 26
    bar_w = 408
    for i, (name, val) in enumerate(items):
        w = bar_w * val / total
        out.append(
            f'<rect class="grow" style="animation-delay:{0.2 + i * 0.1:.2f}s" x="{x:.2f}" y="56" width="{max(w, 1):.2f}" height="10" fill="{palette[i % len(palette)]}"/>'
        )
        x += w
    out.insert(0, f'<clipPath id="bar"><rect x="26" y="56" width="{bar_w}" height="10" rx="5"/></clipPath><g clip-path="url(#bar)"><rect x="26" y="56" width="{bar_w}" height="10" fill="{BORDER}"/>')
    out.append("</g>")
    for i, (name, val) in enumerate(items):
        col, row = i % 2, i // 2
        cx = 32 + col * 210
        cy = 100 + row * 34
        pct = 100 * val / total
        out.append(
            f'<g class="fade" style="animation-delay:{0.5 + i * 0.1:.2f}s">'
            f'<circle cx="{cx}" cy="{cy - 4}" r="5" fill="{palette[i % len(palette)]}"/>'
            f'<text x="{cx + 14}" y="{cy}" font-size="13" fill="{TEXT}">{escape(name)}</text>'
            f'<text x="{cx + 186}" y="{cy}" font-size="12" fill="{MUTED}" text-anchor="end">{pct:.1f}%</text></g>'
        )
    if not items:
        out.append(f'<text x="26" y="110" font-size="13" fill="{MUTED}">No public code yet</text>')
    return frame(460, 220, "Top Languages", "\n".join(out))


def activity_card(u, days=31):
    all_days = [d for w in u["contributionsCollection"]["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    all_days = [d for d in all_days if d["date"] <= date.today().isoformat()][-days:]
    counts = [d["contributionCount"] for d in all_days]
    w, h = 900, 300
    left, right, top, bottom = 56, 24, 64, 48
    pw, ph = w - left - right, h - top - bottom
    peak = max(max(counts, default=0), 4)
    step = pw / max(len(counts) - 1, 1)
    pts = [(left + i * step, top + ph - ph * c / peak) for i, c in enumerate(counts)]

    def smooth(points):
        if not points:
            return ""
        d = f"M{points[0][0]:.1f},{points[0][1]:.1f}"
        for i in range(1, len(points)):
            x0, y0 = points[i - 1]
            x1, y1 = points[i]
            mx = (x0 + x1) / 2
            d += f" C{mx:.1f},{y0:.1f} {mx:.1f},{y1:.1f} {x1:.1f},{y1:.1f}"
        return d

    line = smooth(pts)
    area = f"{line} L{pts[-1][0]:.1f},{top + ph} L{pts[0][0]:.1f},{top + ph} Z" if pts else ""
    out = [
        f'<defs><linearGradient id="ar" x1="0" y1="{top}" x2="0" y2="{top + ph}" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="{PURPLE}" stop-opacity=".55"/><stop offset="1" stop-color="{PURPLE}" stop-opacity="0"/></linearGradient>'
        f'<clipPath id="reveal"><rect x="0" y="0" width="0" height="{h}"><animate attributeName="width" from="0" to="{w}" dur="2s" begin=".2s" fill="freeze"/></rect></clipPath></defs>'
    ]
    for i in range(5):
        y = top + ph * i / 4
        val = round(peak * (4 - i) / 4)
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{w - right}" y2="{y:.1f}" stroke="{BORDER}" stroke-dasharray="3 5"/>')
        out.append(f'<text x="{left - 12}" y="{y + 4:.1f}" font-size="11" fill="{MUTED}" text-anchor="end">{val}</text>')
    for i, d in enumerate(all_days):
        if i % 5 == 0 or i == len(all_days) - 1:
            label = date.fromisoformat(d["date"]).strftime("%b %d")
            anchor = "end" if i == len(all_days) - 1 else "middle"
            out.append(f'<text x="{pts[i][0]:.1f}" y="{h - 20}" font-size="11" fill="{MUTED}" text-anchor="{anchor}">{label}</text>')
    out.append(f'<g clip-path="url(#reveal)"><path d="{area}" fill="url(#ar)"/>')
    out.append(f'<path d="{line}" stroke="{VIOLET}" stroke-width="2.6" stroke-linecap="round"/>')
    for i, (x, y) in enumerate(pts):
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.4" fill="{CREAM}" stroke="{PURPLE}" stroke-width="1.5"><title>{all_days[i]["date"]}: {counts[i]}</title></circle>')
    out.append("</g>")
    if pts:
        x, y = pts[-1]
        out.append(f'<circle class="pulse" cx="{x:.1f}" cy="{y:.1f}" r="8" stroke="{LILAC}" stroke-width="1.5"/>')
    total = sum(counts)
    out.append(f'<text x="{w - right}" y="38" font-size="12" fill="{MUTED}" text-anchor="end">{total} contributions in the last {len(counts)} days</text>')
    return frame(w, h, "Daily Activity", "\n".join(out))


def blackhole_card(u, card_path=None):
    import re
    weeks = u["contributionsCollection"]["contributionCalendar"]["weeks"]
    w, h = 900, 212
    cell, gap = 9.6, 2.3
    pitch = cell + gap
    gx, gy = 22, 96
    img_w = 250
    img_h = img_w * 570 / 940
    img_x, img_y = 640, 46
    hx, hy = img_x + img_w * .649, img_y + img_h * .502
    counts = sorted(d["contributionCount"] for wk in weeks for d in wk["contributionDays"] if d["contributionCount"] > 0)
    def level(c):
        if c == 0 or not counts:
            return 0
        q = [counts[int(len(counts) * f)] for f in (.25, .5, .75)]
        return 1 + sum(c > t for t in q)
    shades = ["#161026", "#3B1A63", "#5B21B6", "#7A16C9", "#C084FC"]
    T = 14.0
    art = ""
    if card_path and os.path.exists(card_path):
        m = re.search(r'<image href="(data:image/png;base64,[^"]+)" x="450"', open(card_path).read())
        if m:
            art = m.group(1)
    out = [
        f'<defs><radialGradient id="hg" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#9333EA" stop-opacity=".55"/><stop offset="1" stop-color="#7A16C9" stop-opacity="0"/></radialGradient>'
        f'<filter id="bl" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="9"/></filter></defs>',
        f'<circle class="pulse" cx="{hx:.1f}" cy="{hy:.1f}" r="80" fill="url(#hg)" filter="url(#bl)"/>',
    ]
    statics = []
    movers = []
    maxd = 0
    cells = []
    for wi, wk in enumerate(weeks):
        for d in wk["contributionDays"]:
            di = date.fromisoformat(d["date"]).weekday()
            row = (di + 1) % 7
            x = gx + wi * pitch + cell / 2
            y = gy + row * pitch + cell / 2
            lv = level(d["contributionCount"])
            dist = math.hypot(hx - x, hy - y)
            maxd = max(maxd, dist)
            cells.append((x, y, lv, dist, d))
    for x, y, lv, dist, d in cells:
        statics.append(f'<rect x="{x - cell/2:.1f}" y="{y - cell/2:.1f}" width="{cell}" height="{cell}" rx="2" fill="{shades[0]}"/>')
        if lv == 0:
            continue
        a0 = math.atan2(y - hy, x - hx)
        r0 = dist
        pts = [(x, y)]
        n = 10
        for k in range(1, n + 1):
            t = k / n
            r = r0 * (1 - t) ** 1.15
            a = a0 + 2.2 * math.pi * t ** 3
            f = 0.38 + 0.62 * (1 - t) ** 0.5
            dy0 = (y - hy) * (1 - t) ** 1.15
            px = hx + r * math.cos(a)
            py = hy + r * math.sin(a) * f * 0.5 + dy0 * 0.5
            pts.append((px, py))
        path = "M" + " ".join(f"{px:.0f},{py:.0f}" for px, py in pts)
        rnd = ((int(x * 7) * 31 + int(y * 13) * 17) % 100) / 100
        start = 0.4 + 6.0 * dist / maxd + rnd * 0.6
        travel = 1.5 + rnd * 0.5
        a = start / T
        b = (start + travel) / T
        kt = f"0;{a:.3f};{b:.3f};.86;.861;1"
        movers.append(
            f'<rect x="{-cell/2}" y="{-cell/2}" width="{cell}" height="{cell}" rx="2" fill="{shades[lv]}">'
            f'<animateMotion dur="{T:g}s" repeatCount="indefinite" path="{path}" keyPoints="0;0;1;1;0;0" keyTimes="{kt}" calcMode="linear"/>'
            f'<animateTransform attributeName="transform" type="scale" additive="sum" dur="{T:g}s" repeatCount="indefinite" values="1;1;0;0;0;1" keyTimes="{kt}"/></rect>'
        )
    out.append("<g>" + "".join(statics) + "</g>")
    hole = f'<ellipse cx="{hx:.1f}" cy="{hy+1:.1f}" rx="{img_w*.12:.1f}" ry="{img_w*.088:.1f}" fill="#040208"/>'
    if art:
        hole += (f'<g><animateTransform attributeName="transform" type="rotate" values="-3 {hx:.1f} {hy:.1f};3 {hx:.1f} {hy:.1f};-3 {hx:.1f} {hy:.1f}" dur="10s" repeatCount="indefinite"/>'
                 f'<image href="{art}" x="{img_x}" y="{img_y}" width="{img_w}" height="{img_h:.1f}"/></g>')
    else:
        hole += f'<ellipse cx="{hx:.1f}" cy="{hy:.1f}" rx="70" ry="26" stroke="{CREAM}" stroke-width="5" transform="rotate(-10 {hx:.1f} {hy:.1f})"/>'
    out.append(hole)
    out.append("<g>" + "".join(movers) + "</g>")
    total = u["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    out.append(f'<text x="26" y="62" font-size="12" fill="{MUTED}">{total} contributions pulled past the event horizon in the last year</text>')
    return frame(w, h, "Event Horizon", "\n".join(out))


def main():
    login = sys.argv[1]
    out_dir = sys.argv[2]
    src = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "-" else None
    if src:
        with open(src) as f:
            u = json.load(f)
    else:
        u = fetch(login, os.environ["GITHUB_TOKEN"])
    os.makedirs(out_dir, exist_ok=True)
    card = sys.argv[4] if len(sys.argv) > 4 else "card.svg"
    cards = (
        ("stats.svg", stats_card(u)),
        ("langs.svg", langs_card(u)),
        ("activity.svg", activity_card(u)),
        ("blackhole.svg", blackhole_card(u, card)),
    )
    for name, svg in cards:
        with open(os.path.join(out_dir, name), "w") as f:
            f.write(svg)


if __name__ == "__main__":
    main()
