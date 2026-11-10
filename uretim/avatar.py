#!/usr/bin/env python3
"""GitHub avatarı çeşitleri — atasoy_ logosunun a_ ikonundan.

    python3 uretim/avatar.py          → uretim/avatar/*.svg + *-1024.png

Kurallar logo kitinden (atasoy.dev/logo): renkler sabit, imleç her zaman amber.
GitHub avatarı daire keser ve 20 px'e kadar küçültür; a_ bu yüzden ikondakinden biraz büyük.
"""
import os
import re
import subprocess

KARA, BEYAZ, AMBER = "#0D0F13", "#F3F4F6", "#FFB020"
BURASI = os.path.dirname(os.path.abspath(__file__))
CIKTI = os.path.join(BURASI, "avatar")
IKON = "/root/atasoy-dev/site/ikon.svg"
A_YOLU = re.search(r'<path fill="#F3F4F6" d="([^"]+)"', open(IKON).read()).group(1)

# a: x 49..536, y -560..10 ; imleç: x 700..1200, y -100..0  → görünür kutu 49..1200 × -560..10
def isaret(olcek, harf=BEYAZ, imlec=AMBER, cx=512, cy=520):
    gx = cx - (49 + 1200) / 2 * olcek
    gy = cy + (560 - 10) / 2 * olcek
    return (f'<g transform="translate({gx:.1f} {gy:.1f}) scale({olcek})">'
            f'<path fill="{harf}" d="{A_YOLU}"/>'
            f'<rect x="700" y="-100" width="500" height="100" fill="{imlec}"/></g>')


def svg(ic, defs=""):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" role="img" aria-label="atasoy_">'
            f'<defs>{defs}</defs>{ic}</svg>')


CESIT = {}

# 1 — sade: logo kitindeki ikon, daireye göre büyütülmüş
CESIT["sade"] = svg(f'<rect width="1024" height="1024" fill="{KARA}"/>' + isaret(0.62))

# 2 — vitrin: profilin üst kartıyla aynı zemin (nokta ızgara + sağ üstten kehribar ışık)
CESIT["vitrin"] = svg(
    f'<rect width="1024" height="1024" fill="{KARA}"/>'
    '<rect width="1024" height="1024" fill="url(#izgara)"/>'
    '<rect width="1024" height="1024" fill="url(#isik)"/>' + isaret(0.62),
    '<pattern id="izgara" width="48" height="48" patternUnits="userSpaceOnUse" x="8" y="8">'
    f'<circle cx="3" cy="3" r="2.4" fill="{BEYAZ}" fill-opacity=".08"/></pattern>'
    '<radialGradient id="isik" cx="1" cy="0" r="1.1">'
    f'<stop offset="0" stop-color="{AMBER}" stop-opacity=".30"/>'
    f'<stop offset=".55" stop-color="{AMBER}" stop-opacity=".05"/>'
    f'<stop offset="1" stop-color="{AMBER}" stop-opacity="0"/></radialGradient>')

# 3 — ışıklı imleç: imleç ekranda yanıyormuş gibi altına yumuşak bir parıltı bırakır
CESIT["parilti"] = svg(
    f'<rect width="1024" height="1024" fill="{KARA}"/>'
    '<ellipse cx="660" cy="660" rx="300" ry="170" fill="url(#hale)"/>' + isaret(0.62),
    '<radialGradient id="hale">'
    f'<stop offset="0" stop-color="{AMBER}" stop-opacity=".34"/>'
    f'<stop offset=".5" stop-color="{AMBER}" stop-opacity=".09"/>'
    f'<stop offset="1" stop-color="{AMBER}" stop-opacity="0"/></radialGradient>')

# 4 — açık: beyaz zemin, koyu a, amber imleç (logo kitindeki açık ikon)
CESIT["acik"] = svg(f'<rect width="1024" height="1024" fill="{BEYAZ}"/>' + isaret(0.62, harf=KARA))


def main():
    os.makedirs(CIKTI, exist_ok=True)
    for ad, icerik in CESIT.items():
        yol = os.path.join(CIKTI, f"{ad}.svg")
        open(yol, "w").write(icerik)
        subprocess.run(["rsvg-convert", "-w", "1024", "-h", "1024", yol, "-o",
                        os.path.join(CIKTI, f"{ad}-1024.png")], check=True)
        print("yazıldı", ad)


if __name__ == "__main__":
    main()
