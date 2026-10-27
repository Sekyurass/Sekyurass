"""Helper kecil untuk membuat SVG bergaya terminal (hanya stdlib)."""
from xml.sax.saxutils import escape as esc

BG = "#0D1117"; PANEL = "#0B0F14"; BORDER = "#30363D"
BLUE = "#58A6FF"; VIOLET = "#A371F7"; GREEN = "#3FB950"
MUTED = "#8B949E"; TEXT = "#E6EDF3"; ORANGE = "#FFA657"; RED = "#FF7B72"
MONO = "'SF Mono','Cascadia Code',Menlo,Consolas,'DejaVu Sans Mono',monospace"
CW = 8.4  # lebar karakter monospace pada font-size 14


def pad(s, width):
    s = str(s)
    if len(s) > width:
        s = s[: width - 1] + "…"
    return s.ljust(width)


def fit(text, limit):
    text = str(text)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def wipe(x0, y, segs, begin, size=14, cw=CW):
    """Teks berwarna + penutup yang bergeser per karakter (efek mengetik)."""
    n = sum(len(t) for t, _ in segs)
    tspans = "".join(f'<tspan fill="{c}">{esc(t)}</tspan>' for t, c in segs)
    text = (f'<text x="{x0}" y="{y}" font-family="{MONO}" font-size="{size}" '
            f'xml:space="preserve">{tspans}</text>')
    if n == 0:
        return text, begin
    W = n * cw + 10
    step = min(0.04, 1.2 / (n + 1))
    xs = ";".join(f"{x0 + i * cw:.1f}" for i in range(n + 2))
    ws = ";".join(f"{max(W - i * cw, 0):.1f}" for i in range(n + 2))
    dur = (n + 1) * step
    cover = (f'<rect class="cv" x="{x0}" y="{y - size - 2}" width="{W:.1f}" height="{size + 8}" fill="{PANEL}">'
             f'<animate attributeName="x" values="{xs}" calcMode="discrete" begin="{begin:.2f}s" dur="{dur:.2f}s" fill="freeze"/>'
             f'<animate attributeName="width" values="{ws}" calcMode="discrete" begin="{begin:.2f}s" dur="{dur:.2f}s" fill="freeze"/>'
             f'</rect>')
    return text + cover, begin + dur


def terminal(title, blocks, aria, width=900):
    """blocks: [(perintah, [baris_output])], baris_output = [(teks, warna), ...]"""
    y, t, out = 70, 0.4, []
    for cmd, lines in blocks:
        el, t = wipe(28, y, [("$ ", GREEN), (cmd, TEXT)], t)
        out.append(el); t += 0.1; y += 24
        for segs in lines:
            el, t = wipe(28, y, segs, t)
            out.append(el); t += 0.04; y += 22
        y += 14
    prompt_y = y - 8
    H = prompt_y + 24
    cursor = (f'<text x="28" y="{prompt_y}" font-family="{MONO}" font-size="14" fill="{GREEN}">$ </text>'
              f'<rect x="46" y="{prompt_y - 13}" width="8" height="17" fill="{BLUE}" opacity="0">'
              f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1s" begin="{t:.2f}s" repeatCount="indefinite"/></rect>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{H}" viewBox="0 0 {width} {H}" role="img" aria-label="{esc(aria)}">
<rect width="{width}" height="{H}" rx="12" fill="{PANEL}" stroke="{BORDER}"/>
<path d="M0 12a12 12 0 0 1 12-12h{width-24}a12 12 0 0 1 12 12v26H0z" fill="#161B22"/>
<line x1="0" y1="38" x2="{width}" y2="38" stroke="{BORDER}"/>
<circle cx="22" cy="19" r="5.5" fill="#FF5F56"/><circle cx="42" cy="19" r="5.5" fill="#FFBD2E"/><circle cx="62" cy="19" r="5.5" fill="{GREEN}"/>
<text x="{width//2}" y="23" text-anchor="middle" font-family="{MONO}" font-size="12" fill="{MUTED}">{esc(title)}</text>
{''.join(out)}
{cursor}
</svg>'''
