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
      totalPullRequestReviewContributions
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


def rank_of(commits, prs, issues, reviews, stars, followers):
    def exp_cdf(x):
        return 1 - 2 ** -x

    def log_cdf(x):
        return x / (1 + x)

    parts = [
        (2, exp_cdf(commits / 250)),
        (3, exp_cdf(prs / 50)),
        (1, exp_cdf(issues / 25)),
        (1, exp_cdf(reviews / 2)),
        (4, log_cdf(stars / 50)),
        (1, log_cdf(followers / 10)),
    ]
    total = sum(w for w, _ in parts)
    pct = (1 - sum(w * v for w, v in parts) / total) * 100
    levels = ["S", "A+", "A", "A-", "B+", "B", "B-", "C+", "C"]
    limits = [1, 12.5, 25, 37.5, 50, 62.5, 75, 87.5, 100]
    for lv, lim in zip(levels, limits):
        if pct <= lim:
            return lv, pct
    return "C", pct


def stats_card(u):
    stars = sum(r["stargazerCount"] for r in u["repositories"]["nodes"])
    cc = u["contributionsCollection"]
    commits = cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
    prs = u["pullRequests"]["totalCount"]
    issues = u["issues"]["totalCount"]
    reviews = cc.get("totalPullRequestReviewContributions", 0)
    followers = u["followers"]["totalCount"]
    grade, pct = rank_of(commits, prs, issues, reviews, stars, followers)
    rows = [
        ("Total stars", stars),
        ("Commits, last year", commits),
        ("Pull requests", prs),
        ("Issues", issues),
        ("Contributed to", u["repositoriesContributedTo"]["totalCount"]),
        ("Contributions, last year", cc["contributionCalendar"]["totalContributions"]),
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
    circ = 276.5
    target = circ * pct / 100
    out.append(
        f'<g class="fade" style="animation-delay:.3s">'
        f'<circle cx="378" cy="112" r="44" stroke="{BORDER}" stroke-width="7"/>'
        f'<circle cx="378" cy="112" r="44" stroke="{VIOLET}" stroke-width="7" stroke-linecap="round" '
        f'stroke-dasharray="{circ}" stroke-dashoffset="{circ}" transform="rotate(-90 378 112)">'
        f'<animate attributeName="stroke-dashoffset" from="{circ}" to="{target:.1f}" begin=".4s" dur="1.6s" fill="freeze"/></circle>'
        f'<text x="378" y="122" font-size="28" font-weight="800" fill="{CREAM}" text-anchor="middle">{grade}</text>'
        f'<text x="378" y="178" font-size="12" font-weight="600" fill="{LILAC}" text-anchor="middle">Rank {grade}</text>'
        f'<text x="378" y="196" font-size="11" fill="{MUTED}" text-anchor="middle">Top {max(pct, 0.1):.1f}% on GitHub</text></g>'
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
    weeks = u["contributionsCollection"]["contributionCalendar"]["weeks"]
    W, H = 900, 178
    cell, gap = 9.6, 2.3
    pitch = cell + gap
    gx, gy = 22, 74
    hx, hy = 790.0, 116.0
    rs = 22.0
    theta_e = 44.0
    T = 16.0
    counts = sorted(d["contributionCount"] for wk in weeks for d in wk["contributionDays"] if d["contributionCount"] > 0)

    def level(c):
        if c == 0 or not counts:
            return 0
        q = [counts[int(len(counts) * f)] for f in (.25, .5, .75)]
        return 1 + sum(c > t for t in q)

    shades = ["#161026", "#3B1A63", "#5B21B6", "#7A16C9", "#C084FC"]
    red = (225, 29, 72)

    def rgb(hx_):
        return tuple(int(hx_[k:k + 2], 16) for k in (1, 3, 5))

    def mix(c1, c2, t):
        return "#%02X%02X%02X" % tuple(round(a + (b - a) * t) for a, b in zip(c1, c2))

    def lens(x, y):
        dx, dy = x - hx, y - hy
        d = math.hypot(dx, dy) or 1e-6
        d2 = (d + math.sqrt(d * d + 4 * theta_e * theta_e)) / 2
        return hx + dx * d2 / d, hy + dy * d2 / d

    def simulate(x0, y0):
        gm = 1.0
        x, y = x0 - hx, y0 - hy
        r = math.hypot(x, y)
        vc = math.sqrt(gm / r)
        vx, vy = -y / r * vc * 0.32, x / r * vc * 0.32
        dt = 0.02 * r ** 1.5 / 400
        samples = [(x, y, 0.0, r)]
        t_obs = 0.0
        last = 0.0
        step = None
        for _ in range(200000):
            ax, ay = -gm * x / r ** 3, -gm * y / r ** 3
            vx += ax * dt
            vy += ay * dt
            vx *= 0.9995
            vy *= 0.9995
            x += vx * dt
            y += vy * dt
            r = math.hypot(x, y)
            dil = 1 / math.sqrt(max(1 - rs / r, 0.04)) if r > rs else 5
            t_obs += dt * dil
            samples.append((x, y, t_obs, r))
            if r <= rs * 1.02:
                break
        return samples

    raw = []
    statics = []
    for wi, wk in enumerate(weeks):
        for d in wk["contributionDays"]:
            row = (date.fromisoformat(d["date"]).weekday() + 1) % 7
            x = gx + wi * pitch + cell / 2
            y = gy + row * pitch + cell / 2
            lx, ly = lens(x, y)
            statics.append(f'<rect x="{lx - cell/2:.1f}" y="{ly - cell/2:.1f}" width="{cell}" height="{cell}" rx="2" fill="{shades[0]}"/>')
            lv = level(d["contributionCount"])
            if lv:
                raw.append((lx, ly, lv))

    sims = [(lx, ly, lv, simulate(lx, ly)) for lx, ly, lv in raw]
    t_max = max((sm[-1][2] for *_, sm in sims), default=1)
    scale_t = 9.0 / t_max
    movers = []
    for lx, ly, lv, sm in sims:
        total = sm[-1][2]
        n = 9
        picks = []
        k = 0
        for m in range(n + 1):
            target = total * (m / n) ** 0.85
            while k < len(sm) - 1 and sm[k][2] < target:
                k += 1
            picks.append(sm[k])
        rel = 0.6 + ((int(lx * 7) * 31 + int(ly * 13) * 17) % 100) / 250
        times = [rel + p[2] * scale_t for p in picks]
        end = times[-1]
        pts = [(hx + p[0], hy + p[1]) for p in picks]
        angs = []
        prev = None
        for m in range(len(pts)):
            a2 = pts[min(m + 1, len(pts) - 1)]
            a1 = pts[max(m - 1, 0)]
            ang = math.degrees(math.atan2(a2[1] - a1[1], a2[0] - a1[0]))
            if prev is not None:
                while ang - prev > 180:
                    ang -= 360
                while ang - prev < -180:
                    ang += 360
            angs.append(ang)
            prev = ang
        angs[0] = 0 if abs(angs[0]) < 90 else angs[0]
        stretch = [1 + 2.4 * (rs / p[3]) ** 2 for p in picks]
        kt = [0.0] + [t / T for t in times] + [0.9, 0.901, 1.0]
        kts = ";".join(f"{v:.3f}".lstrip("0") or "0" for v in kt)
        mv = [pts[0]] + pts + [pts[-1], pts[0], pts[0]]
        mvs = ";".join(f"{a:.0f},{b:.0f}" for a, b in mv)
        rot = [0.0, 0.0] + angs[1:] + [angs[-1], 0.0, 0.0]
        rots = ";".join(f"{v:.0f}" for v in rot)
        sc = ["1 1", "1 1"] + [f"{st:.2f} {max(1 / st, .25):.2f}" for st in stretch[1:-1]] + ["0 0", "0 0", "0 0", "1 1"]
        scs = ";".join(sc)
        base = rgb(shades[lv])
        heat = [min(1, (rs / p[3]) ** 1.2 * 1.6) for p in picks]
        cols = [shades[lv]] + [mix(base, red, h) for h in heat] + [mix(base, red, 1), shades[lv], shades[lv]]
        fills = ";".join(cols)
        op = ["1"] + [f"{max(0, 1 - max(0, (rs * 1.6 - p[3]) / (rs * 0.6))):.2f}" for p in picks] + ["0", "0", "1"]
        ops = ";".join(op)
        a = f'dur="{T:g}s" repeatCount="indefinite" keyTimes="{kts}"'
        movers.append(
            f'<rect x="{-cell/2}" y="{-cell/2}" width="{cell}" height="{cell}" rx="2" fill="{shades[lv]}">'
            f'<animateMotion {a} values="{mvs}" calcMode="linear"/>'
            f'<animateTransform attributeName="transform" type="rotate" additive="sum" {a} values="{rots}"/>'
            f'<animateTransform attributeName="transform" type="scale" additive="sum" {a} values="{scs}"/>'
            f'<animate attributeName="fill" {a} values="{fills}"/></rect>'
        )

    disk = []
    for k, (rx, ry, w_, dash, dur, op_) in enumerate([
        (52, 9, 3.2, "120 60 40 30", 3.2, 1), (66, 12, 2.4, "80 50 140 40", 4.4, .9),
        (82, 15, 1.8, "60 90 30 70", 6, .8), (102, 19, 1.2, "40 120 70 90", 8.5, .6),
    ]):
        disk.append(
            f'<ellipse rx="{rx}" ry="{ry}" stroke="url(#doppler)" stroke-width="{w_}" stroke-linecap="round" opacity="{op_}" '
            f'pathLength="1000" stroke-dasharray="{dash}"><animate attributeName="stroke-dashoffset" values="0;1000" dur="{dur}s" repeatCount="indefinite"/></ellipse>'
        )
    disk_g = "".join(disk)
    hole = f"""<defs>
<linearGradient id="doppler" x1="-110" y1="0" x2="110" y2="0" gradientUnits="userSpaceOnUse">
<stop offset="0" stop-color="#FFFFFF"/><stop offset=".35" stop-color="{CREAM}"/><stop offset=".7" stop-color="{VIOLET}"/><stop offset="1" stop-color="#4C1D95"/>
</linearGradient>
<radialGradient id="halo" cx=".5" cy=".5" r=".5"><stop offset=".3" stop-color="{VIOLET}" stop-opacity=".45"/><stop offset="1" stop-color="{PURPLE}" stop-opacity="0"/></radialGradient>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<clipPath id="back"><rect x="-130" y="-60" width="260" height="60"/></clipPath>
<clipPath id="front"><rect x="-130" y="0" width="260" height="60"/></clipPath>
</defs>
<g transform="translate({hx} {hy}) rotate(-8)">
<circle class="pulse" r="60" fill="url(#halo)"/>
<g clip-path="url(#back)" filter="url(#glow)">{disk_g}</g>
<g filter="url(#glow)" opacity=".95">
<path d="M-40,-2 A40,36 0 0 1 40,-2" stroke="url(#doppler)" stroke-width="5" stroke-linecap="round"/>
<path d="M-34,4 A34,26 0 0 0 34,4" stroke="url(#doppler)" stroke-width="2" stroke-linecap="round" opacity=".7"/>
</g>
<circle r="{rs * 1.3:.1f}" fill="#030106"/>
<circle r="{rs * 1.36:.1f}" stroke="{CREAM}" stroke-width="1.3" filter="url(#glow)"><animate attributeName="stroke-opacity" values=".6;1;.6" dur="3s" repeatCount="indefinite"/></circle>
<g clip-path="url(#front)" filter="url(#glow)">{disk_g}</g>
</g>"""
    total = u["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    body = (
        f'<text x="22" y="34" font-size="17" font-weight="600" fill="{VIOLET}">Event Horizon</text>'
        f'<text x="22" y="54" font-size="12" fill="{MUTED}">{total} contributions in the last year, falling in under gravity</text>'
        + "<g>" + "".join(statics) + "</g>" + hole + "<g>" + "".join(movers) + "</g>"
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" role="img" aria-label="Contribution graph falling into a black hole">
<style>
text {{ font-family: {FONT}; }}
@keyframes pulse {{ 0%,100% {{ opacity: .55 }} 50% {{ opacity: 1 }} }}
.pulse {{ animation: pulse 4s ease-in-out infinite }}
</style>
{body}
</svg>
"""

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
