"""
Generates the animated SVGs for the GitHub profile README.
Every graphic is built twice (light + dark) so it matches the viewer's GitHub theme.
Fonts (Instrument Serif, DM Mono, Inter) are subset to the exact glyphs used
and embedded, because GitHub renders SVGs as <img> and can't load web fonts.

Run:  python3 scripts/build.py   (needs fonttools; fonts path in FONT_DIR)
"""
import base64, hashlib, io, math, os, sys
from xml.sax.saxutils import escape
from fontTools.ttLib import TTFont
from fontTools import subset

FONT_DIR = os.environ.get("FONT_DIR", "fonts")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets")
os.makedirs(OUT, exist_ok=True)

FONT_FILES = {
    "serif":  "instrument-serif-latin-400-normal.woff",
    "serifI": "instrument-serif-latin-400-italic.woff",
    "mono":   "dm-mono-latin-400-normal.woff",
    "monoM":  "dm-mono-latin-500-normal.woff",
    "sans":   "inter-latin-400-normal.woff",
    "sansM":  "inter-latin-500-normal.woff",
}
FONTS = {k: TTFont(os.path.join(FONT_DIR, v)) for k, v in FONT_FILES.items()}

PAL = {
    "light": dict(bg="#fdfcf9", card="#ffffff", ink="#141414", muted="#6b6863", faint="#a39f97",
                  line="#e7e4dc", accent="#2e7d32", amber="#b45309", soft="#eef5ee", dot="#d9d5cb"),
    "dark":  dict(bg="#0a0a0a", card="#111111", ink="#f4f4f4", muted="#8a8a8a", faint="#575757",
                  line="#242424", accent="#4caf50", amber="#f59e0b", soft="#122016", dot="#2a2a2a"),
}


def adv(font, text, size, ls=0.0):
    f = FONTS[font]
    cmap, hmtx, upem = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    w = 0
    for ch in text:
        g = cmap.get(ord(ch))
        w += hmtx[g][0] if g else upem * 0.5
    return w * size / upem + ls * max(0, len(text) - 1)


def wrap(font, text, size, width):
    lines, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if adv(font, t, size) <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def h(s, n=4):
    d = hashlib.sha256(s.encode()).hexdigest()
    return f"0x{d[:n]}…{d[-n:]}"


class SVG:
    def __init__(self, w, hgt, theme, title):
        self.w, self.h, self.p, self.title = w, hgt, PAL[theme], title
        self.els, self.used, self.css = [], {}, []

    def text(self, x, y, s, font, size, fill, anchor="start", ls=0, extra="", cls=""):
        self.used.setdefault(font, set()).update(s)
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        l = f' letter-spacing="{ls}"' if ls else ""
        c = f' class="{cls}"' if cls else ""
        self.els.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="P{font}" font-size="{size}" fill="{fill}"{a}{l}{c} {extra}>{escape(s)}</text>')

    def raw(self, s):
        self.els.append(s)

    def fontface(self):
        out = []
        for name, chars in self.used.items():
            opts = subset.Options()
            opts.flavor = "woff"
            opts.layout_features = ["kern", "liga"]
            opts.name_IDs = []
            opts.notdef_outline = True
            sub = subset.Subsetter(opts)
            sub.populate(text="".join(sorted(chars)) + " ")
            f = TTFont(os.path.join(FONT_DIR, FONT_FILES[name]))
            sub.subset(f)
            buf = io.BytesIO()
            f.flavor = "woff"
            f.save(buf)
            b = base64.b64encode(buf.getvalue()).decode()
            out.append(f"@font-face{{font-family:P{name};src:url(data:font/woff;base64,{b}) format('woff');}}")
        return "".join(out)

    def render(self):
        style = self.fontface() + "".join(self.css) + \
            "@media (prefers-reduced-motion:reduce){*{animation:none!important}.rm-hide{display:none}}"
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(self.title)}">'
                f'<title>{escape(self.title)}</title><style>{style}</style>' + "".join(self.els) + "</svg>")


def frame(s, r=20, fill=None):
    p = s.p
    s.raw(f'<rect x="0.75" y="0.75" width="{s.w-1.5}" height="{s.h-1.5}" rx="{r}" '
          f'fill="{fill or p["bg"]}" stroke="{p["line"]}" stroke-width="1.5"/>')


def arrow_ne(x, y, size, color, sw=1.8):
    # small north-east arrow drawn as a path (fonts don't carry the glyph)
    a = size
    return (f'<path d="M{x:.1f} {y+a:.1f} L{x+a:.1f} {y:.1f} M{x+a*0.35:.1f} {y:.1f} L{x+a:.1f} {y:.1f} '
            f'L{x+a:.1f} {y+a*0.65:.1f}" fill="none" stroke="{color}" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')


def arrow_e(x, y, size, color, sw=1.6):
    a = size
    return (f'<path d="M{x:.1f} {y:.1f} L{x+a:.1f} {y:.1f} M{x+a-a*0.38:.1f} {y-a*0.32:.1f} L{x+a:.1f} {y:.1f} '
            f'L{x+a-a*0.38:.1f} {y+a*0.32:.1f}" fill="none" stroke="{color}" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')


def pulse_dot(s, cx, cy, color, r=4, delay=0):
    s.raw(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>'
          f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="1.5" '
          f'class="pulse" style="animation-delay:{delay}s"/>')


PULSE_CSS = (".pulse{transform-box:fill-box;transform-origin:center;animation:pulse 2.2s ease-out infinite}"
             "@keyframes pulse{0%{transform:scale(1);opacity:.9}80%,100%{transform:scale(3.2);opacity:0}}")


# ---------------------------------------------------------------- HERO
CHAIN = [
    ("2021", "Airdrop hunter", "then a Fiverr service"),
    ("2022", "Self-taught Solidity", "YouTube channel live"),
    ("2023", "The 820x lesson", "risk first, always"),
    ("2025", "OWL AI", "then HashlySpace"),
    ("2026", "Habeas, Orbis, Nexis", "shipped on Stellar"),
    ("Nov '26", "Devcon 8 India", "mining"),
]


def fit(font, text, size, width, min_size=9):
    while adv(font, text, size) > width and size > min_size:
        size -= 0.5
    return size


def hero(theme):
    W, H = 1200, 470
    s = SVG(W, H, theme, "Prashant Mishra — Web3 builder and funded trader from India. Build. Explore. Learn. Iterate.")
    p = s.p
    s.css.append(PULSE_CSS)
    s.css.append(
        ".hx{animation:hxo .12s linear both}.lt{animation:lti .45s cubic-bezier(.2,.7,.2,1) both}"
        "@keyframes hxo{from{opacity:1}to{opacity:0}}"
        "@keyframes lti{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}"
        ".f1{animation:fl .16s steps(1) infinite}.f2{animation:fl .16s steps(1) infinite reverse}"
        "@keyframes fl{0%{opacity:1}50%{opacity:0}}"
        ".fade{animation:fade .8s ease-out both}@keyframes fade{from{opacity:0}to{opacity:1}}"
        ".pk{animation:pk 7s cubic-bezier(.45,0,.2,1) infinite}"
        "@keyframes pk{0%{transform:translateX(0);opacity:0}6%{opacity:1}88%{opacity:1}100%{transform:translateX(var(--d));opacity:0}}"
        ".ants{animation:ants 1.2s linear infinite}@keyframes ants{to{stroke-dashoffset:-16}}"
        ".blink{animation:blink 1.1s steps(1) infinite}@keyframes blink{50%{opacity:0}}"
    )
    frame(s, 22)
    # dotted texture, faded with a gradient mask
    s.raw(f'<defs><pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse">'
          f'<circle cx="2" cy="2" r="1.1" fill="{p["dot"]}"/></pattern>'
          f'<radialGradient id="fadeg" cx="0.82" cy="0.18" r="0.55"><stop offset="0" stop-color="#fff"/>'
          f'<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
          f'<mask id="dm"><rect width="{W}" height="{H}" fill="url(#fadeg)"/></mask></defs>'
          f'<rect x="2" y="2" width="{W-4}" height="{H-4}" rx="21" fill="url(#dots)" mask="url(#dm)"/>')

    # top bar
    s.text(48, 60, "BLOCK #0 · GENESIS", "monoM", 13, p["muted"], ls=2)
    tw = adv("mono", "PRASHANTX.ME", 13, 2)
    s.text(W - 48, 60, "PRASHANTX.ME", "mono", 13, p["muted"], anchor="end", ls=2)
    bw = adv("monoM", "BUILDING", 13, 2)
    bx = W - 48 - tw - 28 - bw
    s.text(bx, 60, "BUILDING", "monoM", 13, p["accent"], ls=2)
    pulse_dot(s, bx - 14, 55.5, p["accent"], 3.5)

    # mined name
    name, size, x, y = "Prashant Mishra", 118, 44, 200
    hexes = "9f3ac1e27b0d84f6a5c2"
    for i, ch in enumerate(name):
        cw = adv("serif", ch, size)
        if ch != " ":
            d = 0.35 + i * 0.075
            s.text(x, y, ch, "serif", size, p["ink"], cls="lt", extra=f'style="animation-delay:{d:.2f}s"')
            cx = x + cw / 2
            hx1, hx2 = hexes[i % len(hexes)], hexes[(i * 7 + 3) % len(hexes)]
            s.raw(f'<g class="hx rm-hide" style="animation-delay:{d:.2f}s">')
            s.text(cx, y - 14, hx1, "mono", 54, p["amber"], anchor="middle", cls="f1")
            s.text(cx, y - 14, hx2, "mono", 54, p["amber"], anchor="middle", cls="f2")
            s.raw("</g>")
        x += cw
    name_end = x

    s.raw('<g class="fade" style="animation-delay:1.6s">')
    s.text(48, 248, "Web3 builder and funded trader from India.", "sans", 22, p["ink"])
    mx = 48
    for word, col in [("Build.", p["muted"]), ("Explore.", p["muted"]), ("Learn.", p["muted"]), ("Iterate.", p["accent"])]:
        s.text(mx, 284, word, "serifI", 26, col)
        mx += adv("serifI", word + " ", 26)
    s.raw("</g>")

    # stats column
    sx = W - 48
    s.raw(f'<line x1="{W-260}" y1="98" x2="{W-260}" y2="268" stroke="{p["line"]}" stroke-width="1.5"/>')
    s.raw('<g class="fade" style="animation-delay:1.9s">')
    for k, (val, lab) in enumerate([("13", "PROJECTS SHIPPED"), ("$3k+", "FUNDED PAYOUTS"), ("4%", "MAX DRAWDOWN RULE")]):
        yy = 132 + k * 58
        s.text(sx, yy, val, "serif", 40, p["ink"], anchor="end")
        s.text(sx, yy + 19, lab, "mono", 11.5, p["muted"], anchor="end", ls=1.6)
    s.raw("</g>")
    assert name_end < W - 280, name_end

    # chain
    top, bh, x0, gap = 322, 120, 48, 18
    n = len(CHAIN)
    bw = (W - 96 - gap * (n - 1)) / n
    cy = top + bh / 2
    s.raw(f'<line x1="{x0+20}" y1="{cy}" x2="{W-68}" y2="{cy}" stroke="{p["line"]}" stroke-width="1.5"/>')
    dist = (n - 1) * (bw + gap)
    s.raw(f'<g class="pk" style="--d:{dist:.0f}px"><rect x="{x0+bw-6:.1f}" y="{cy-3}" width="34" height="6" rx="3" '
          f'fill="{p["accent"]}"/></g>')
    for i, (yr, title, det) in enumerate(CHAIN):
        bx = x0 + i * (bw + gap)
        last = i == n - 1
        stroke = p["amber"] if last else p["line"]
        dash = ' stroke-dasharray="6 4" class="ants"' if last else ""
        s.raw(f'<g class="fade" style="animation-delay:{2.1 + i*0.12:.2f}s">')
        s.raw(f'<rect x="{bx:.1f}" y="{top}" width="{bw:.1f}" height="{bh}" rx="12" fill="{p["card"]}" '
              f'stroke="{stroke}" stroke-width="1.5"{dash}/>')
        tag = f"#{i}  " + ("pending" if last else h(yr + title, 3))
        s.text(bx + 14, top + 25, tag, "mono", 12, p["amber"] if last else p["faint"], ls=0.4)
        s.text(bx + 14, top + 62, yr, "serif", 32, p["ink"])
        s.text(bx + 14, top + 87, title, "sansM", fit("sansM", title, 15, bw - 26), p["ink"])
        if last:
            s.text(bx + 14, top + 107, "mining", "sans", 14, p["amber"])
            s.text(bx + 14 + adv("sans", "mining", 14), top + 107, "...", "sans", 14, p["amber"], cls="blink")
        else:
            s.text(bx + 14, top + 107, det, "sans", fit("sans", det, 14, bw - 26), p["muted"])
        s.raw("</g>")
    return s.render()


# ---------------------------------------------------------------- PROJECT CARDS
PROJECTS = [
    ("habeas", "Habeas", "STELLAR · SOROBAN", "LIVE · TESTNET", True,
     "Before anyone freezes or takes your tokens, they have to say why. Due process, written into a smart contract.",
     ["Soroban", "54 tests", "Hackathon"]),
    ("orbis", "Orbis", "STELLAR · ZK", "LIVE · TESTNET", True,
     "AI agents buy services privately. Winner is proven, payment settles on Stellar, receipts are audit-ready.",
     ["ZK proofs", "AI agents", "Soroban"]),
    ("nexis", "Nexis", "MANTLE · XMTP", "LIVE · TESTNET", True,
     "Tinder, but for Web3 founders and investors. Swipe, match, build.",
     ["XMTP", "Soulbound NFTs", "React"]),
    ("estateeth", "EstateETH", "ETHEREUM · SOLIDITY", "SMART CONTRACT DAPP", False,
     "Own a slice of a property. Transfer the deed without a middleman.",
     ["Solidity", "IPFS", "Hardhat"]),
    ("satyavote", "SatyaVote", "ETHEREUM", "LIVE · SATYAVOTE.COM", True,
     "Voting where every ballot is on-chain and anyone can check the count.",
     ["Solidity", "web3.js", "React"]),
    ("dewallet", "DeWallet", "EVM · BROWSER", "LIVE APP", True,
     "A simple wallet that lives in your browser. Your keys, your coins.",
     ["BIP-39", "ethers.js", "React"]),
]


def card(theme, idx, pr):
    slug, title, chain, status, live, tagline, tags = pr
    W, H = 600, 320
    s = SVG(W, H, theme, f"{title}: {tagline}")
    p = s.p
    s.css.append(PULSE_CSS)
    frame(s, 18, p["card"])
    s.text(30, 46, chain, "monoM", 13, p["muted"], ls=1.8)
    col = p["accent"] if live else p["muted"]
    stw = adv("mono", status, 12.5, 1.4)
    s.text(W - 30, 46, status, "mono", 12.5, col, anchor="end", ls=1.4)
    if live:
        pulse_dot(s, W - 30 - stw - 13, 42, col, 3.2, delay=idx * 0.35)
    else:
        s.raw(f'<circle cx="{W-30-stw-13:.1f}" cy="42" r="3.2" fill="none" stroke="{col}" stroke-width="1.4"/>')
    s.text(28, 118, title, "serif", 50, p["ink"])
    s.text(28 + adv("serif", title, 50) + 10, 118, f"#{idx+1:02d}", "mono", 12, p["faint"])
    for k, line in enumerate(wrap("sans", tagline, 20, W - 64)[:3]):
        s.text(30, 160 + k * 29, line, "sans", 20, p["muted"])
    tx = 30
    for t in tags:
        tw = adv("mono", t, 14) + 26
        s.raw(f'<rect x="{tx:.1f}" y="254" width="{tw:.1f}" height="36" rx="18" fill="none" stroke="{p["line"]}" stroke-width="1.4"/>')
        s.text(tx + 13, 277, t, "mono", 14, p["ink"])
        tx += tw + 8
    s.raw(f'<circle cx="{W-50}" cy="272" r="20" fill="{p["soft"]}"/>' + arrow_ne(W - 56, 266, 12, p["accent"], 2))
    return s.render()


# ---------------------------------------------------------------- STACK
STACK = [
    ("CHAINS", ["Ethereum", "Stellar", "Base", "Mantle"]),
    ("CONTRACTS", ["Solidity", "Soroban", "Hardhat", "OpenZeppelin", "ERC-20 / 721"]),
    ("FRONTEND", ["React", "TypeScript", "Tailwind", "ethers.js", "web3.js"]),
    ("INFRA", ["IPFS", "Chainlink", "XMTP", "ZK proofs", "AI agents"]),
]


def stack(theme):
    W = 1200
    # layout pass for height
    colw, gapc = 252, 32
    rows_bottom = 0
    layout = []
    for c, (head, items) in enumerate(STACK):
        x0 = 48 + c * (colw + gapc)
        x, y = x0, 140
        pills = []
        for it in items:
            w = adv("sans", it, 15.5) + 30
            if x + w > x0 + colw:
                x, y = x0, y + 42
            pills.append((x, y, w, it))
            x += w + 8
        rows_bottom = max(rows_bottom, y + 34)
        layout.append((x0, head, pills))
    H = rows_bottom + 92
    s = SVG(W, H, theme, "Stack: Ethereum, Stellar, Base, Mantle, Solidity, Soroban, React, TypeScript, IPFS, Chainlink, XMTP, ZK proofs")
    p = s.p
    s.css.append(".fade{animation:fade .7s ease-out both}@keyframes fade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}")
    frame(s, 20)
    s.text(48, 58, "STACK", "monoM", 13, p["muted"], ls=2)
    s.text(W - 48, 58, "what I actually ship with", "serifI", 20, p["faint"], anchor="end")
    for c, (x0, head, pills) in enumerate(layout):
        s.raw(f'<g class="fade" style="animation-delay:{0.15 + c*0.15:.2f}s">')
        s.text(x0, 104, f"0{c+1}", "mono", 12, p["faint"], ls=1.5)
        s.text(x0 + 30, 104, head, "monoM", 12, p["accent"], ls=1.8)
        s.raw(f'<line x1="{x0}" y1="118" x2="{x0+colw}" y2="118" stroke="{p["line"]}" stroke-width="1.5"/>')
        for (x, y, w, it) in pills:
            s.raw(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="34" rx="17" fill="{p["card"]}" stroke="{p["line"]}" stroke-width="1.4"/>')
            s.text(x + 15, y + 22.5, it, "sans", 15.5, p["ink"])
        s.raw("</g>")
    q = "AI writes most of my code. I decide what gets built, read every line, and don't ship what I can't explain."
    s.raw(f'<line x1="48" y1="{H-62}" x2="{W-48}" y2="{H-62}" stroke="{p["line"]}" stroke-width="1.5" stroke-dasharray="2 5"/>')
    s.text(48, H - 28, q, "serifI", fit("serifI", q, 22, W - 96), p["muted"])
    return s.render()


# ---------------------------------------------------------------- TICKETS
def ticket_shell(s, stub_x):
    p = s.p
    W, H = s.w, s.h
    s.raw(f'<defs><mask id="nt"><rect width="{W}" height="{H}" fill="#fff"/>'
          f'<circle cx="{stub_x}" cy="0" r="13" fill="#000"/><circle cx="{stub_x}" cy="{H}" r="13" fill="#000"/></mask></defs>'
          f'<g mask="url(#nt)"><rect x="0.75" y="0.75" width="{W-1.5}" height="{H-1.5}" rx="18" fill="{p["card"]}" '
          f'stroke="{p["line"]}" stroke-width="1.5"/>'
          f'<circle cx="{stub_x}" cy="0" r="13.75" fill="none" stroke="{p["line"]}" stroke-width="1.5"/>'
          f'<circle cx="{stub_x}" cy="{H}" r="13.75" fill="none" stroke="{p["line"]}" stroke-width="1.5"/></g>'
          f'<line x1="{stub_x}" y1="22" x2="{stub_x}" y2="{H-22}" stroke="{p["line"]}" stroke-width="1.5" stroke-dasharray="4 6"/>')


def barcode(s, x, y, w, hgt, seed):
    p = s.p
    d = hashlib.sha256(seed.encode()).digest() * 4
    cx, i = x, 0
    bars = []
    while cx < x + w - 2:
        bw = 1 + d[i] % 3
        if i % 2 == 0:
            bars.append(f'<rect x="{cx:.1f}" y="{y}" width="{bw}" height="{hgt}" fill="{p["ink"]}" opacity="0.85"/>')
        cx += bw + (1 if i % 2 else 0.6)
        i += 1
    s.raw("".join(bars))


def trade_ticket(theme):
    W, H, stub = 600, 360, 448
    s = SVG(W, H, theme, "Off-chain: Topstep certified funded trader. $3,000+ in funded payouts. 4% max drawdown rule. 2023: caught an 820x run and watched it vanish.")
    p = s.p
    s.css.append(PULSE_CSS)
    ticket_shell(s, stub)
    s.text(30, 48, "OFF-CHAIN · TRADE TICKET", "monoM", 12, p["muted"], ls=1.8)
    s.text(28, 106, "Funded trader", "serif", 48, p["ink"])
    rows = [("FIRM", "Topstep, certified"), ("PAYOUTS", "$3,000+"), ("RISK RULE", "4% max drawdown"),
            ("MARKETS", "Gold, BTC, EURUSD, US100, Oil")]
    for k, (lab, val) in enumerate(rows):
        yy = 152 + k * 34
        s.text(30, yy, lab, "mono", 11.5, p["faint"], ls=1.5)
        s.text(140, yy, val, "sansM", fit("sansM", val, 16, stub - 170), p["ink"])
        s.raw(f'<line x1="30" y1="{yy+12}" x2="{stub-28}" y2="{yy+12}" stroke="{p["line"]}" stroke-width="1" stroke-dasharray="2 4"/>')
    for k, line in enumerate(["2023: caught an ~820x run and watched it vanish.", "Risk first, ever since."]):
        s.text(30, 310 + k * 24, line, "serifI", 18.5, p["muted"] if k == 0 else p["accent"])
    # stub
    cx = (stub + W) / 2
    s.text(cx, 52, "TKT", "mono", 11, p["faint"], anchor="middle", ls=2)
    s.text(cx, 104, "820x", "serif", 46, p["ink"], anchor="middle")
    s.text(cx, 126, "THE LESSON", "mono", 10, p["muted"], anchor="middle", ls=1.5)
    barcode(s, stub + 28, 160, W - stub - 56, 120, "prashant-820x")
    s.text(cx, 308, "RISK", "monoM", 11, p["accent"], anchor="middle", ls=2)
    s.text(cx, 326, "MANAGED", "monoM", 11, p["accent"], anchor="middle", ls=2)
    return s.render()


def mumbai_pass(theme):
    W, H, stub = 600, 360, 448
    s = SVG(W, H, theme, "Next block, November 2026, Mumbai: India Blockchain Week (builder), Devcon 8 India (first Devcon), ETHGlobal Mumbai (hacker).")
    p = s.p
    s.css.append(PULSE_CSS)
    ticket_shell(s, stub)
    s.text(30, 48, "NEXT BLOCK · BOARDING", "monoM", 12, p["muted"], ls=1.8)
    pulse_dot(s, stub - 34, 43.5, p["amber"], 3.5)
    s.text(28, 106, "Mumbai, Nov '26", "serif", 48, p["ink"])
    rows = [("01–02", "India Blockchain Week", "builder"), ("03–06", "Devcon 8 India", "my first Devcon"),
            ("NOV", "ETHGlobal Mumbai", "hacker, selected")]
    for k, (d, name, role) in enumerate(rows):
        yy = 152 + k * 48
        s.text(30, yy, d, "monoM", 13, p["accent"], ls=0.5)
        s.text(104, yy, name, "sansM", 16.5, p["ink"])
        s.text(104, yy + 19, role, "sans", 13, p["muted"])
    s.text(30, 322, "Going too? Say hi.", "serifI", 21, p["muted"])
    cx = (stub + W) / 2
    s.text(cx, 52, "TO", "mono", 11, p["faint"], anchor="middle", ls=2)
    s.text(cx, 108, "BOM", "serif", 54, p["ink"], anchor="middle")
    s.text(cx, 130, "MUMBAI", "mono", 10, p["muted"], anchor="middle", ls=1.5)
    barcode(s, stub + 28, 160, W - stub - 56, 120, "devcon8-bom")
    s.text(cx, 308, "SEAT", "mono", 11, p["faint"], anchor="middle", ls=2)
    s.text(cx, 326, "BUILDER", "monoM", 11, p["accent"], anchor="middle", ls=2)
    return s.render()


# ---------------------------------------------------------------- LOOP FOOTER
def loop(theme):
    W, H = 1200, 110
    s = SVG(W, H, theme, "Build. Explore. Learn. Iterate.")
    p = s.p
    s.css.append(".hl{opacity:0;animation:hl 8s ease-in-out infinite}"
                 "@keyframes hl{0%{opacity:0}4%{opacity:1}24%{opacity:1}28%{opacity:0}100%{opacity:0}}")
    words = ["Build", "Explore", "Learn", "Iterate"]
    size, arw, gapw = 40, 30, 34
    total = sum(adv("serif", w, size) for w in words) + len(words) * (arw + 2 * gapw) - gapw
    x = (W - total) / 2
    y = 70
    for i, w in enumerate(words):
        s.text(x, y, w, "serif", size, p["faint"])
        s.text(x, y, w, "serif", size, p["accent"], cls="hl", extra=f'style="animation-delay:{i*2}s"')
        x += adv("serif", w, size) + gapw
        if i < len(words) - 1:
            s.raw(arrow_e(x, y - 12, arw, p["faint"]))
        else:
            # loop-back mark
            s.raw(f'<path d="M{x+4:.1f} {y-26} a13 13 0 1 1 -2 18" fill="none" stroke="{p["faint"]}" stroke-width="1.6" stroke-linecap="round"/>'
                  f'<path d="M{x-4:.1f} {y-12} l6 3 l1 -7" fill="none" stroke="{p["faint"]}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>')
        x += arw + gapw
    return s.render()


def write(name, svg):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(svg)


if __name__ == "__main__":
    for t in ("light", "dark"):
        write(f"hero-{t}.svg", hero(t))
        for i, pr in enumerate(PROJECTS):
            write(f"card-{pr[0]}-{t}.svg", card(t, i, pr))
        write(f"stack-{t}.svg", stack(t))
        write(f"ticket-{t}.svg", trade_ticket(t))
        write(f"mumbai-{t}.svg", mumbai_pass(t))
        write(f"loop-{t}.svg", loop(t))
    print("ok")
