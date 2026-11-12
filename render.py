"""Digital Stash image renderer.

Turns a day's content file (JSON) into on-brand PNGs using fixed templates,
so every post looks consistent no matter who writes the text.

Usage:
    python render.py posts/2026-11-13/day.json
Writes one PNG per item next to the JSON file (e.g. posts/2026-11-13/pin-1.png).

Day JSON shape:
{
  "items": [
    {"file": "pin-1", "template": "list", "size": "pin",
     "tag": "FREE PRINTABLE", "title": ["30 Good Deeds", "Kids Can Do"], "highlight": "This Ramadan",
     "items": ["Help set the iftar table", "..."], "note": "+ a free 30-star tracker to print",
     "footer": "Little Lanterns · ages 4–10"},
    {"file": "pin-2", "template": "steps", "size": "pin", "tag": "10-MINUTE SETUP",
     "title": ["A Ramadan Corner", "for Kids"], "subtitle": "No crafting skills needed.",
     "steps": [["Pick one corner", "A shelf or a small table is enough."], ...], "footer": "..."},
    {"file": "pin-3", "template": "lanterns", "size": "pin", "tag": "RAMADAN COUNTDOWN",
     "title": ["Color one lantern", "each night"], "highlight": "until Eid",
     "caption": "Free printable · print at home tonight", "footer": "Little Lanterns"},
    {"file": "ig-1", "template": "bignumber", "size": "ig", "number": "88 days",
     "title": "until Ramadan. Start these 3 small traditions now.",
     "cards": [["Start a deeds jar", "One note for every kind thing they do."], ...],
     "footer": "Comment LANTERN for 3 free pages"}
  ]
}
Templates: list, steps, lanterns, bignumber. Sizes: pin (1000x1500), ig (1080x1350), square (1080x1080).
Keep every claim true: never invent reviews, numbers of customers, or sales.
"""
import html, json, pathlib, shutil, subprocess, sys

NAVY, GOLD, CREAM, TEAL, ROSE = "#1d1b3a", "#f2b84b", "#fff9ef", "#3fa796", "#e9877b"
SIZES = {"pin": (1000, 1500), "ig": (1080, 1350), "square": (1080, 1080)}
e = html.escape

BASE = """<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&family=Nunito:wght@600;700;800&display=block" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0}
body{width:%(w)dpx;height:%(h)dpx;overflow:hidden;font-family:Nunito,sans-serif;color:%(navy)s}
h1,.f{font-family:Fredoka,sans-serif}
.stars{position:absolute;inset:0;background-image:radial-gradient(3px 3px at 12%% 18%%,#fff9 50%%,transparent 51%%),radial-gradient(2px 2px at 32%% 8%%,#fff7 50%%,transparent 51%%),radial-gradient(3px 3px at 82%% 14%%,#fff9 50%%,transparent 51%%),radial-gradient(2px 2px at 64%% 26%%,#fff6 50%%,transparent 51%%),radial-gradient(2px 2px at 90%% 40%%,#fff7 50%%,transparent 51%%)}
.tag{display:inline-block;background:%(gold)s;color:%(navy)s;font-weight:800;border-radius:999px;padding:10px 26px;font-size:30px}
.foot{position:absolute;left:0;right:0;bottom:44px;text-align:center;font-family:Fredoka;font-weight:600;font-size:30px}
li{display:flex;gap:18px;align-items:center;padding:9px 0}
</style></head><body>%(body)s</body></html>"""


def lantern(fill, w):
    return (f'<svg width="{w}" viewBox="0 0 60 92"><g stroke="{NAVY}" stroke-width="2.4" stroke-linejoin="round">'
            f'<line x1="30" y1="0" x2="30" y2="8"/><circle cx="30" cy="11" r="3.5" fill="none"/>'
            f'<path d="M20,15 L40,15 L46,25 L14,25 Z" fill="{NAVY}"/>'
            f'<path d="M14,25 L9,35 L9,67 L14,77 L46,77 L51,67 L51,35 L46,25 Z" fill="{fill}"/>'
            f'<path d="M22,38 Q30,29 38,38 L38,64 L22,64 Z" fill="#fff6dc"/>'
            f'<path d="M20,77 L40,77 L36,86 L24,86 Z" fill="{NAVY}"/></g></svg>')


def title_html(lines, highlight=None, color=GOLD):
    out = "<br>".join(e(t) for t in lines)
    if highlight:
        out += f'<br><span style="color:{color}">{e(highlight)}</span>'
    return out


def t_list(c):
    items = "".join(f'<li><span style="color:{GOLD};font-size:40px">★</span>{e(i)}</li>' for i in c["items"])
    note = f'<li style="color:#8e8ab0;font-weight:600">{e(c["note"])}</li>' if c.get("note") else ""
    return f"""<div style="position:relative;height:100%;background:{NAVY};color:#fff;padding:90px 70px">
<div class="stars"></div><div style="position:relative">
<span class="tag">{e(c.get('tag',''))}</span>
<h1 style="font-size:92px;line-height:1.02;margin-top:34px">{title_html(c['title'], c.get('highlight'))}</h1>
<ul style="list-style:none;margin-top:56px;background:#fff;color:{NAVY};border-radius:36px;padding:44px 48px;font-size:38px;font-weight:700;line-height:1.35">{items}{note}</ul>
</div><div class="foot" style="color:#fff">{e(c.get('footer',''))}</div></div>"""


def t_steps(c):
    rows = "".join(
        f'<div style="display:flex;gap:26px;align-items:flex-start;padding:20px 0;border-bottom:2px dashed #ece4d4">'
        f'<span class="f" style="flex:none;width:70px;height:70px;border-radius:50%;background:{GOLD};display:grid;place-items:center;font-size:38px;font-weight:700">{n}</span>'
        f'<div><div class="f" style="font-size:42px;font-weight:600">{e(a)}</div><div style="font-size:31px;color:#5d5978">{e(b)}</div></div></div>'
        for n, (a, b) in enumerate(c["steps"], 1))
    sub = f'<p style="font-size:36px;color:#5d5978;margin-top:16px">{e(c["subtitle"])}</p>' if c.get("subtitle") else ""
    return f"""<div style="position:relative;height:100%;background:#fff;padding:90px 70px">
<span class="tag" style="background:{TEAL};color:#fff">{e(c.get('tag',''))}</span>
<h1 style="font-size:88px;line-height:1.04;margin-top:30px">{title_html(c['title'], c.get('highlight'), TEAL)}</h1>{sub}
<div style="margin-top:30px">{rows}</div>
<div style="display:flex;justify-content:center;gap:30px;margin-top:36px">{lantern(GOLD,90)}{lantern(TEAL,90)}{lantern(ROSE,90)}</div>
<div class="foot" style="color:{NAVY}">{e(c.get('footer',''))}</div></div>"""


def t_lanterns(c):
    colors = [GOLD, TEAL, ROSE] * 3
    grid = "".join(
        f'<div style="display:grid;justify-items:center;gap:6px">{lantern(colors[i] if i < 8 else "#fff", 104)}'
        f'<span class="f" style="font-size:28px;font-weight:600">{i + 1}</span></div>' for i in range(15))
    return f"""<div style="position:relative;height:100%;background:{CREAM};padding:90px 70px">
<span class="tag">{e(c.get('tag',''))}</span>
<h1 style="font-size:86px;line-height:1.04;margin-top:30px">{title_html(c['title'], c.get('highlight'), TEAL)}</h1>
<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:22px 10px;margin-top:56px;background:#fff;border-radius:36px;padding:40px 30px;border:3px solid #ece4d4">{grid}</div>
<p style="font-size:36px;font-weight:700;text-align:center;margin-top:40px">{e(c.get('caption',''))}</p>
<div class="foot" style="color:{NAVY}">{e(c.get('footer',''))}</div></div>"""


def t_bignumber(c):
    cards = "".join(
        f'<div style="background:#ffffff14;border-radius:28px;padding:28px 34px;margin-top:22px">'
        f'<div class="f" style="font-size:46px;font-weight:600;color:{GOLD}">{e(a)}</div>'
        f'<div style="font-size:34px;color:#e4e1f7">{e(b)}</div></div>' for a, b in c.get("cards", []))
    return f"""<div style="position:relative;height:100%;background:{NAVY};color:#fff;padding:90px 80px">
<div class="stars"></div><div style="position:relative">
<div class="f" style="font-size:150px;font-weight:700;color:{GOLD};line-height:1">{e(c['number'])}</div>
<h1 style="font-size:66px;line-height:1.1;margin-top:10px">{e(c['title'])}</h1>{cards}</div>
<div class="foot" style="color:#fff">{e(c.get('footer',''))}</div></div>"""


TEMPLATES = {"list": t_list, "steps": t_steps, "lanterns": t_lanterns, "bignumber": t_bignumber}


def find_browser():
    for p in ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "google-chrome",
              "chromium", "chromium-browser", "google-chrome-stable"]:
        if shutil.which(p) or pathlib.Path(p).exists():
            return p
    return None


def shoot(html_path, png_path, w, h):
    browser = find_browser()
    if browser:
        subprocess.run([browser, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                        f"--window-size={w},{h}", "--virtual-time-budget=6000",
                        f"--screenshot={png_path}", f"file://{html_path}"], capture_output=True, check=False)
        if png_path.exists():
            return
    # Fallback: Playwright (pip install playwright && python -m playwright install --with-deps chromium)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": w, "height": h})
        page.goto(f"file://{html_path}")
        page.wait_for_timeout(2500)
        page.screenshot(path=str(png_path))
        b.close()


def main(day_json):
    day_json = pathlib.Path(day_json).resolve()
    data = json.loads(day_json.read_text(encoding="utf-8"))
    out = []
    for item in data["items"]:
        w, h = SIZES[item.get("size", "pin")]
        body = TEMPLATES[item["template"]](item)
        html_path = day_json.parent / f"{item['file']}.html"
        png_path = day_json.parent / f"{item['file']}.png"
        html_path.write_text(BASE % {"w": w, "h": h, "navy": NAVY, "gold": GOLD, "body": body}, encoding="utf-8")
        shoot(html_path, png_path, w, h)
        html_path.unlink()
        if not png_path.exists():
            sys.exit(f"Rendering failed for {item['file']}")
        out.append(str(png_path))
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1])
