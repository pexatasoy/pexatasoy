#!/usr/bin/env python3
"""GitHub profil sayfasını üretir: assets/*.svg + README.md

    python3 uretim/uret.py

Kaynak: /root/atasoy-dev/site/ortak/projeler.json (portfolyo, tek gerçek)
        + uretim/veri.json (portfolyoda olmayanlar ve üstüne yazılanlar)
Portfolyo değişince bunu yeniden çalıştırmak yeter; site ile profil aynı kalır.
"""
import base64
import io
import json
import os
import re
import urllib.parse
import sys
from xml.sax.saxutils import escape

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yazi  # noqa: E402
from yazi import Kullanim, aile, genislik, sar  # noqa: E402

KOK = yazi.KOK
ASSETS = os.path.join(KOK, "assets")
PORTFOLYO = "/root/atasoy-dev/site/ortak/projeler.json"
GORSEL = "/root/atasoy-dev/site/ortak/gorsel"
LOGO = "/root/atasoy-dev/marka/cikti"

KARA = "#0D0F13"
BEYAZ = "#F3F4F6"
AMBER = "#FFB020"
SOLUK = "#6B6E75"

TUR = {"urun": "PRODUCT", "oyun": "GAME", "musteri": "CLIENT", "arac": "TOOL"}


# ───────────────────────── veri ─────────────────────────

def yukle():
    p = json.load(open(PORTFOLYO))
    v = json.load(open(os.path.join(KOK, "uretim", "veri.json")))
    projeler = {x["id"]: dict(x) for x in p["projeler"]}
    for k, ek in v["ek"].items():
        projeler[k] = {"id": k, **ek}
    for k, ust in v["ustune"].items():
        projeler[k].update(ust)
    durum = {k: d["en"] for k, d in p["durumlar"].items()}
    return p["kisi"], v["bolumler"], projeler, durum


# ───────────────────────── yardımcılar ─────────────────────────

def e(s):
    return escape(str(s), {'"': "&quot;"})


def renk_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def parlaklik(h):
    def k(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = renk_rgb(h)
    return 0.2126 * k(r) + 0.7152 * k(g) + 0.0722 * k(b)


def karsitlik(a, b):
    la, lb = sorted((parlaklik(a), parlaklik(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def nokta_rengi(p):
    """Durum noktası markanın vurgusuyla; zemin üstünde seçilmiyorsa yazı rengiyle."""
    r = p["renk"]
    return r["vurgu"] if karsitlik(r["vurgu"], r["zemin"]) >= 1.9 else r["yazi"]


def gorsel_yolu(p, tur):
    """tur: 'site' ya da 'tel'"""
    if tur == "tel":
        ad = p.get("tel")
        return os.path.join(GORSEL, ad) if ad else None
    if p.get("gorsel_yol"):
        return os.path.join(KOK, p["gorsel_yol"])
    if "gorsel_yol" in p and p["gorsel_yol"] is None:
        return None
    ad = p.get("gorsel")
    if not ad or ad == p.get("tel"):
        return None
    return os.path.join(GORSEL, ad)


def resim(yol, en, boy, olcek=1.0):
    """Kutuyu dolduracak şekilde üstten kırpar, webp data URI döner."""
    im = Image.open(yol).convert("RGB")
    hw, hh = int(en * olcek), int(boy * olcek)
    oran = max(hw / im.width, hh / im.height)
    im = im.resize((max(hw, round(im.width * oran)), max(hh, round(im.height * oran))), Image.LANCZOS)
    x = (im.width - hw) // 2
    im = im.crop((x, 0, x + hw, hh))
    b = io.BytesIO()
    im.save(b, "WEBP", quality=80, method=6)
    return "data:image/webp;base64," + base64.b64encode(b.getvalue()).decode()


class Svg:
    def __init__(self, en, boy, etiket):
        self.en, self.boy, self.etiket = en, boy, etiket
        self.k = Kullanim()
        self.defs = []
        self.govde = []
        self.css = []

    def yazi(self, x, y, metin, font, boy, renk, saydam=1.0, hiza="start", aralik=0.0, ek=""):
        self.k.ekle(font, metin)
        ls = f' letter-spacing="{aralik}"' if aralik else ""
        op = f' fill-opacity="{saydam}"' if saydam < 1 else ""
        self.govde.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="{aile(font)}" font-size="{boy}" '
            f'fill="{renk}"{op} text-anchor="{hiza}"{ls}{ek}>{e(metin)}</text>'
        )
        return genislik(metin, font, boy, aralik)

    def ekle(self, s):
        self.govde.append(s)

    def bitir(self, yol):
        hareket = (
            "@keyframes nabiz{0%{transform:scale(1);opacity:.85}100%{transform:scale(3.4);opacity:0}}"
            ".nabiz{transform-box:fill-box;transform-origin:center;animation:nabiz 2.6s ease-out infinite}"
            "@keyframes yanip{0%,49.9%{opacity:1}50%,100%{opacity:0}}"
            ".yanip{animation:yanip 1.1s infinite}"
            "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
        )
        stil = self.k.css() + hareket + "".join(self.css)
        icerik = (
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'viewBox="0 0 {self.en} {self.boy}" width="{self.en}" height="{self.boy}" '
            f'role="img" aria-label="{e(self.etiket)}">'
            f"<title>{e(self.etiket)}</title>"
            f"<style>{stil}</style>"
            f'<defs>{"".join(self.defs)}</defs>'
            f'{"".join(self.govde)}</svg>'
        )
        with open(yol, "w") as f:
            f.write(icerik)
        return len(icerik)


GOLGE = (
    '<filter id="golge" x="-20%" y="-20%" width="140%" height="150%">'
    '<feDropShadow dx="0" dy="22" stdDeviation="26" flood-color="#000" flood-opacity=".30"/></filter>'
)


def tarayici(s, x, y, en, boy, veri, alan, koyu=False, id_="t"):
    """Tarayıcı penceresi: üst şerit, adres, altında ekran görüntüsü."""
    zem = "#1C1D21" if koyu else "#FFFFFF"
    ser = "#2A2B30" if koyu else "#F1F1EF"
    nok = "#4A4C52" if koyu else "#D3D3CF"
    yaz = "#9A9CA3" if koyu else "#6E6E69"
    s.defs.append(f'<clipPath id="{id_}"><rect x="{x}" y="{y}" width="{en}" height="{boy}" rx="18"/></clipPath>')
    s.ekle(f'<g filter="url(#golge)"><rect x="{x}" y="{y}" width="{en}" height="{boy}" rx="18" fill="{zem}"/></g>')
    s.ekle(f'<g clip-path="url(#{id_})">')
    s.ekle(f'<rect x="{x}" y="{y}" width="{en}" height="46" fill="{ser}"/>')
    for i in range(3):
        s.ekle(f'<circle cx="{x + 26 + i * 20}" cy="{y + 23}" r="6" fill="{nok}"/>')
    if alan:
        pw = min(en - 220, 420)
        s.ekle(f'<rect x="{x + en / 2 - pw / 2}" y="{y + 11}" width="{pw}" height="24" rx="12" fill="{zem}" fill-opacity=".85"/>')
        s.yazi(x + en / 2, y + 28, alan, "mono", 14, yaz, hiza="middle")
    s.ekle(f'<image x="{x}" y="{y + 46}" width="{en}" height="{boy - 46}" href="{veri}" preserveAspectRatio="xMidYMin slice"/>')
    s.ekle("</g>")


def telefon(s, x, y, en, veri, aci=0, id_="p"):
    boy = en * 2.17
    rx = en * 0.17
    k = en * 0.045
    cx, cy = x + en / 2, y + boy / 2
    s.defs.append(
        f'<clipPath id="{id_}"><rect x="{x + k}" y="{y + k}" width="{en - 2 * k}" height="{boy - 2 * k}" rx="{rx - k}"/></clipPath>'
    )
    s.ekle(f'<g transform="rotate({aci} {cx:.1f} {cy:.1f})">')
    s.ekle(f'<g filter="url(#golge)"><rect x="{x}" y="{y}" width="{en}" height="{boy:.1f}" rx="{rx:.1f}" fill="#0B0B0C"/></g>')
    s.ekle(f'<rect x="{x + 1.5}" y="{y + 1.5}" width="{en - 3}" height="{boy - 3:.1f}" rx="{rx - 1:.1f}" fill="none" stroke="#3A3A3E" stroke-width="2"/>')
    s.ekle(
        f'<image clip-path="url(#{id_})" x="{x + k}" y="{y + k}" width="{en - 2 * k}" height="{boy - 2 * k:.1f}" '
        f'href="{veri}" preserveAspectRatio="xMidYMin slice"/>'
    )
    iw = en * 0.3
    s.ekle(f'<rect x="{cx - iw / 2:.1f}" y="{y + k + en * 0.03:.1f}" width="{iw:.1f}" height="{en * 0.085:.1f}" rx="{en * 0.0425:.1f}" fill="#0B0B0C"/>')
    s.ekle("</g>")


def durum_rozeti(s, x, y, p, durum, boy=17, hiza="start"):
    """● LIVE — canlı olanın noktası nabız gibi atar."""
    metin = durum[p["durum"]].upper()
    r = p["renk"]
    nr = nokta_rengi(p)
    w = genislik(metin, "mono", boy, 2) + boy * 2.4 + 22
    x0 = x - w if hiza == "end" else x
    h = boy * 2
    s.ekle(f'<rect x="{x0:.1f}" y="{y - h * 0.68:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{h / 2:.1f}" fill="{r["yazi"]}" fill-opacity=".07" stroke="{r["yazi"]}" stroke-opacity=".16"/>')
    cx, cy = x0 + boy * 1.15, y - h * 0.68 + h / 2
    if p["durum"] == "yayinda":
        s.ekle(f'<circle class="nabiz" cx="{cx:.1f}" cy="{cy:.1f}" r="{boy * 0.3:.1f}" fill="none" stroke="{nr}" stroke-width="2"/>')
    s.ekle(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{boy * 0.3:.1f}" fill="{nr}"/>')
    s.yazi(x0 + boy * 2.1, cy + boy * 0.36, metin, "mono", boy, r["yazi"], 0.85, aralik=2)
    return w


def cipler(s, x, y, etiketler, renk, boy=17):
    for t in etiketler:
        t = t.upper()
        w = genislik(t, "mono", boy, 1.5) + boy * 1.8
        h = boy * 2.2
        s.ekle(f'<rect x="{x:.1f}" y="{y - h * 0.68:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{h / 2:.1f}" fill="none" stroke="{renk}" stroke-opacity=".35" stroke-width="1.5"/>')
        s.yazi(x + boy * 0.9, y + boy * 0.06 + 1, t, "mono", boy, renk, 0.8, aralik=1.5)
        x += w + boy * 0.6
    return x


def baslik_sigdir(metin, font, boy, en):
    while boy > 20 and genislik(metin, font, boy) + boy * 0.55 > en:
        boy -= 2
    return boy


def alt_cizgi(s, x, y, boy, renk):
    """Başlığın sonundaki _ — atasoy_ logosundaki çizginin her projede kendi rengi."""
    s.ekle(f'<rect x="{x + boy * 0.08:.1f}" y="{y - boy * 0.11:.1f}" width="{boy * 0.42:.1f}" height="{boy * 0.11:.1f}" fill="{renk}"/>')


def alan_adi(link):
    if not link:
        return None
    return link.split("://", 1)[1].rstrip("/")


def platform(p):
    return [("Phone" if x == "Telefon" else x) for x in p.get("platform", [])]


def kart_zemini(s, p, rx):
    r = p["renk"]
    s.defs.append(f'<clipPath id="kart"><rect width="{s.en}" height="{s.boy}" rx="{rx}"/></clipPath>')
    s.ekle(f'<rect width="{s.en}" height="{s.boy}" rx="{rx}" fill="{r["zemin"]}"/>')
    s.ekle('<g clip-path="url(#kart)">')


# ───────────────────────── kapak (tam genişlik) ─────────────────────────

def kapak(p, no, durum):
    W, H = 1600, 660
    r = p["renk"]
    s = Svg(W, H, f'{p["ad"]} — {p["en"]["kisa"]}')
    s.defs.append(GOLGE)
    kart_zemini(s, p, 40)
    sol = p.get("gorsel_tarafi", "sag") == "sol"
    x0 = 860 if sol else 76
    kol = 660

    # arka planda dev sayı — dergi sayfası numarası gibi
    s.yazi(x0 - 18, H + 70, f"{no:02d}", "baslik", 560, r["yazi"], 0.045)

    # görseller
    site = gorsel_yolu(p, "site")
    tel = gorsel_yolu(p, "tel")
    koyu = parlaklik(r["zemin"]) < 0.2
    if sol:
        if site:
            tarayici(s, -120, 118, 860, 560, resim(site, 860, 514), alan_adi(p.get("link")), koyu)
        if tel:
            telefon(s, 560 if site else 260, 210 if site else 120, 210 if site else 250, resim(tel, 200, 440, 1.0), 5 if site else -4)
    else:
        if site:
            tarayici(s, 860, 118, 860, 560, resim(site, 860, 514), alan_adi(p.get("link")), koyu)
        if tel:
            telefon(s, 780 if site else 1060, 210 if site else 120, 210 if site else 250, resim(tel, 200, 440, 1.0), -5 if site else 4)

    # yazılar
    etiket = f'NO. {no:02d}  ·  {TUR[p["tur"]]}'
    w = s.yazi(x0, 104, etiket, "mono", 20, r["yazi"], 0.6, aralik=3)
    durum_rozeti(s, x0 + w + 28, 104, p, durum, 17)

    bb = baslik_sigdir(p["ad"], "baslik", 124, kol)
    tw = s.yazi(x0 - 4, 232, p["ad"], "baslik", bb, r["yazi"])
    alt_cizgi(s, x0 - 4 + tw, 232, bb, r["vurgu"] if karsitlik(r["vurgu"], r["zemin"]) > 1.3 else r["yazi"])

    y = 300
    for satir in sar(p["en"]["kisa"], "italik", 40, kol)[:2]:
        s.yazi(x0, y, satir, "italik", 40, r["yazi"])
        y += 50
    y += 18
    satirlar = sar(p["en"]["metin"], "serif", 26, kol - 20)
    sigan = max(0, int((H - 112 - y) // 40) + 1)
    if len(satirlar) > sigan:
        satirlar = satirlar[:sigan]
        satirlar[-1] = satirlar[-1].rstrip(".,;:") + "…"
    for satir in satirlar:
        s.yazi(x0, y, satir, "serif", 26, r["yazi"], 0.78)
        y += 40

    xs = cipler(s, x0, H - 66, platform(p), r["yazi"], 16)
    a = alan_adi(p.get("link"))
    if a:
        s.yazi(xs + 14, H - 64, f"{a}  ↗", "mono", 19, r["yazi"], 0.9)
    s.ekle("</g>")
    return s


# ───────────────────────── kısa kart (yarım genişlik) ─────────────────────────

def kisa(p, no, durum):
    W, H = 800, 500
    r = p["renk"]
    s = Svg(W, H, f'{p["ad"]} — {p["en"]["kisa"]}')
    s.defs.append(GOLGE)
    kart_zemini(s, p, 32)
    x0 = 44

    site = gorsel_yolu(p, "site")
    tel = gorsel_yolu(p, "tel")
    koyu = parlaklik(r["zemin"]) < 0.2
    gorsel_var = True
    if tel and (p.get("tel_oncelik") or not site):
        telefon(s, 560, 150, 190, resim(tel, 180, 400), 7)
    elif site:
        tarayici(s, 430, 168, 560, 380, resim(site, 560, 334), None, koyu)
    else:
        gorsel_var = False
        # görsel yoksa: projenin baş harfi, kartın sağ altından taşan dev bir harf
        harf = p["ad"][0]
        s.yazi(W + 30, H + 96, harf, "baslik", 430, r["vurgu"], 0.9 if karsitlik(r["vurgu"], r["zemin"]) > 1.3 else 0.12, hiza="end")

    kol = 370 if gorsel_var else 400
    s.yazi(x0, 66, f'NO. {no:02d}  ·  {TUR[p["tur"]]}', "mono", 16, r["yazi"], 0.6, aralik=2.4)
    durum_rozeti(s, W - 40, 66, p, durum, 14, hiza="end")

    bb = baslik_sigdir(p["ad"], "baslik", 66, kol + 40)
    tw = s.yazi(x0 - 2, 156, p["ad"], "baslik", bb, r["yazi"])
    alt_cizgi(s, x0 - 2 + tw, 156, bb, r["vurgu"] if karsitlik(r["vurgu"], r["zemin"]) > 1.3 else r["yazi"])

    y = 206
    for satir in sar(p["en"]["kisa"], "italik", 28, kol)[:3]:
        s.yazi(x0, y, satir, "italik", 28, r["yazi"])
        y += 36
    y += 8
    metin = p["en"].get("metin", "")
    satirlar = sar(metin, "serif", 19, kol)
    sigan = max(0, int((H - 120 - y) // 27))
    if len(satirlar) > sigan:
        satirlar = satirlar[:sigan]
        if satirlar:
            satirlar[-1] = satirlar[-1].rstrip(".,;") + "…"
    for satir in satirlar:
        s.yazi(x0, y, satir, "serif", 19, r["yazi"], 0.72)
        y += 27

    xs = cipler(s, x0, H - 48, platform(p), r["yazi"], 13)
    a = alan_adi(p.get("link"))
    if a and xs + genislik(a, "mono", 15) + 40 < (430 if gorsel_var else W - 40):
        s.yazi(xs + 8, H - 46, f"{a} ↗", "mono", 15, r["yazi"], 0.85)
    s.ekle("</g>")
    return s


# ───────────────────────── açık kaynak kartı (yarım genişlik) ─────────────────────────

def ad_satirlari(ad, en, boy):
    """CamelCase adı en fazla iki satıra böler (sığıyorsa tek satır); yazı boyunu sığana kadar küçültür."""
    parca = re.findall(r"[A-Z][a-z]*|[^A-Z]+", ad)
    while boy > 24:
        if genislik(ad, "baslik", boy) + boy * 0.55 <= en:
            return [ad], boy
        if len(parca) > 1:
            k = min(range(1, len(parca)), key=lambda i: abs(len("".join(parca[:i])) - len("".join(parca[i:]))))
            ust, alt = "".join(parca[:k]), "".join(parca[k:])
            if max(genislik(ust, "baslik", boy), genislik(alt, "baslik", boy) + boy * 0.55) <= en:
                return [ust, alt], boy
        boy -= 2
    return [ad], boy


def acik_kart(p, a, no):
    """Açık kaynak projesi: lisans hapı, repo adresi; görsel ya sağda telefon ya da altta pencere."""
    W, H = 800, 560
    r = a["renk"]
    s = Svg(W, H, f'{p["ad"]} — {a["en"]["kisa"]} (open source, {a["lisans"]})')
    s.defs.append(GOLGE)
    kart_zemini(s, {"renk": r}, 32)
    x0 = 44
    koyu = parlaklik(r["zemin"]) < 0.2
    vurgu = r["vurgu"] if karsitlik(r["vurgu"], r["zemin"]) > 1.3 else r["yazi"]
    yerlesim = a.get("yerlesim", "sag")
    gorsel = os.path.join(KOK, a["gorsel"])

    if yerlesim == "sag":
        telefon(s, 556, 150, 196, resim(gorsel, 186, 412), 6, id_="ap")
        kol = 400
    else:
        kol = W - 2 * x0

    # üst satır: numara + "açık kaynak", sağda lisans hapı
    s.yazi(x0, 66, f"NO. {no:02d}  ·  OPEN SOURCE", "mono", 16, r["yazi"], 0.6, aralik=2.4)
    lis = a["lisans"].upper()
    lw = genislik(lis, "mono", 14, 2) + 30
    s.ekle(f'<rect x="{W - 40 - lw:.1f}" y="47" width="{lw:.1f}" height="28" rx="14" fill="{vurgu}" fill-opacity=".14" stroke="{vurgu}" stroke-opacity=".45"/>')
    s.yazi(W - 40 - lw / 2, 66, lis, "mono", 14, vurgu, 1, hiza="middle", aralik=2)

    # başlık (uzun ad iki satıra bölünür) + _
    satirlar, bb = ad_satirlari(p["ad"], kol, 66)
    y = 98 + bb * 0.82
    for i, satir in enumerate(satirlar):
        tw = s.yazi(x0 - 2, y, satir, "baslik", bb, r["yazi"])
        if i == len(satirlar) - 1:
            alt_cizgi(s, x0 - 2 + tw, y, bb, vurgu)
        y += bb * 0.98
    y += 34 - bb * 0.98 + bb * 0.2

    for satir in sar(a["en"]["kisa"], "italik", 28, kol)[:2]:
        s.yazi(x0, y, satir, "italik", 28, r["yazi"])
        y += 36

    if yerlesim == "sag":
        y += 8
        satirlar = sar(a["en"]["metin"], "serif", 19, kol)
        sigan = max(0, int((H - 126 - y) // 27))
        if len(satirlar) > sigan:
            satirlar = satirlar[:sigan]
            if satirlar:
                satirlar[-1] = satirlar[-1].rstrip(".,;") + "…"
        for satir in satirlar:
            s.yazi(x0, y, satir, "serif", 19, r["yazi"], 0.72)
            y += 27
        alt_y = H - 74
    else:
        alt_y = y + 18

    xs = cipler(s, x0, alt_y, a["etiket"], r["yazi"], 13)
    s.yazi(x0, alt_y + 40, f'github.com/{a["repo"]}  ↗', "mono", 15, r["yazi"], 0.85)

    if yerlesim == "alt":
        gy = alt_y + 70
        gw = W - 2 * x0
        gh = H - gy + 40
        s.defs.append(f'<clipPath id="ap"><rect x="{x0}" y="{gy}" width="{gw}" height="{gh}" rx="16"/></clipPath>')
        s.ekle(f'<g filter="url(#golge)"><rect x="{x0}" y="{gy}" width="{gw}" height="{gh}" rx="16" fill="#000"/></g>')
        s.ekle(f'<image clip-path="url(#ap)" x="{x0}" y="{gy}" width="{gw}" height="{gh}" href="{resim(gorsel, gw, gh)}" preserveAspectRatio="xMidYMin slice"/>')
        s.ekle(f'<rect x="{x0 + .75}" y="{gy + .75}" width="{gw - 1.5}" height="{gh}" rx="16" fill="none" stroke="#fff" stroke-opacity="{.14 if koyu else .5}" stroke-width="1.5"/>')
    s.ekle("</g>")
    return s


# ───────────────────────── müşteri kartı ─────────────────────────

def musteri(p, no, durum):
    W, H = 800, 500
    r = p["renk"]
    s = Svg(W, H, f'{p["ad"]} — {p["en"]["kisa"]}')
    s.defs.append(GOLGE)
    kart_zemini(s, p, 32)
    site = gorsel_yolu(p, "site")
    ust = 280
    if site:
        s.ekle(f'<image x="0" y="0" width="{W}" height="{ust}" href="{resim(site, W, ust)}" preserveAspectRatio="xMidYMin slice"/>')
        s.defs.append(
            f'<linearGradient id="sonum" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{r["zemin"]}" stop-opacity="0"/>'
            f'<stop offset=".55" stop-color="{r["zemin"]}" stop-opacity=".7"/>'
            f'<stop offset="1" stop-color="{r["zemin"]}" stop-opacity="1"/></linearGradient>'
        )
        s.ekle(f'<rect x="0" y="{ust - 190}" width="{W}" height="192" fill="url(#sonum)"/>')
    else:
        # görsel yok: adı, kartın üst yarısını dolduran iri ve soluk bir şerit olarak
        for i in range(3):
            s.yazi(-30 + i * 60, 110 + i * 92, (p["ad"] + "   ") * 3, "baslik", 96, r["yazi"], 0.07 - i * 0.015)
        s.ekle(f'<rect x="44" y="{ust - 36}" width="64" height="9" fill="{r["vurgu"]}"/>')

    x0 = 44
    s.yazi(x0, ust + 40, f'NO. {no:02d}  ·  CLIENT', "mono", 15, r["yazi"], 0.6, aralik=2.2)
    a = alan_adi(p.get("link"))
    if a:
        s.yazi(W - 40, ust + 40, f"{a} ↗", "mono", 15, r["yazi"], 0.75, hiza="end")
    bb = baslik_sigdir(p["ad"], "baslik", 56, W - 100)
    tw = s.yazi(x0 - 2, ust + 112, p["ad"], "baslik", bb, r["yazi"])
    alt_cizgi(s, x0 - 2 + tw, ust + 112, bb, r["vurgu"] if karsitlik(r["vurgu"], r["zemin"]) > 1.3 else r["yazi"])
    y = ust + 156
    for satir in sar(p["en"]["kisa"], "italik", 26, W - 90)[:2]:
        s.yazi(x0, y, satir, "italik", 26, r["yazi"], 0.9)
        y += 34
    s.ekle("</g>")
    return s


# ───────────────────────── tezgâh listesi (açık/koyu) ─────────────────────────

def ad_yaz(s, ad, x, b, en, yaz):
    """Proje adını sütuna sığdırır: sığmazsa CamelCase'i iki satıra böler (NoMoreStupidKeyboard / SettingsForReal)."""
    if genislik(ad, "baslik2", 36) <= en:
        s.yazi(x, b, ad, "baslik2", 36, yaz)
        return
    parca = re.findall(r"[A-Z][a-z]*|[^A-Z]+", ad)
    if len(parca) > 1:
        # iki satırın genişliği en yakın olacak bölme noktası
        k = min(range(1, len(parca)), key=lambda i: abs(len("".join(parca[:i])) - len("".join(parca[i:]))))
        ust, alt = "".join(parca[:k]), "".join(parca[k:])
        boy = 30
        while boy > 18 and max(genislik(ust, "baslik2", boy), genislik(alt, "baslik2", boy)) > en:
            boy -= 1
        s.yazi(x, b - boy * 0.52, ust, "baslik2", boy, yaz)
        s.yazi(x, b + boy * 0.5, alt, "baslik2", boy, yaz)
        return
    boy = 36
    while boy > 18 and genislik(ad, "baslik2", boy) > en:
        boy -= 1
    s.yazi(x, b, ad, "baslik2", boy, yaz)


def tezgah(liste, ilk_no, durum, koyu):
    yaz = BEYAZ if koyu else "#111215"
    W = 1600
    satir = 84
    H = satir * len(liste) + 8
    s = Svg(W, H, "Workbench: " + ", ".join(p["ad"] for p in liste))
    for i, p in enumerate(liste):
        y = i * satir
        if i:
            s.ekle(f'<rect x="0" y="{y}" width="{W}" height="1.5" fill="{yaz}" fill-opacity=".12"/>')
        b = y + satir / 2 + 10
        s.yazi(0, b - 1, f"{ilk_no + i:02d}", "mono", 20, yaz, 0.45, aralik=2)
        ad_yaz(s, p["ad"], 84, b + 2, 366, yaz)
        aciklama = p["en"]["kisa"]
        while genislik(aciklama, "serif", 27) > 660:
            aciklama = aciklama.rsplit(" ", 1)[0].rstrip(",") + "…"
        s.yazi(470, b, aciklama, "serif", 27, yaz, 0.78)
        s.yazi(1390, b - 1, " · ".join(x.upper() for x in platform(p)), "mono", 15, yaz, 0.55, hiza="end", aralik=1.5)
        # durum: renkli nokta + yazı
        renk = {"yayinda": "#2FB574", "test": "#E3A21A", "yapim": "#5B8DEF", "prototip": "#A07BE0", "inceleme": "#E3A21A"}[p["durum"]]
        t = durum[p["durum"]].upper()
        tw = genislik(t, "mono", 15, 1.5)
        if p["durum"] == "yayinda":
            s.ekle(f'<circle class="nabiz" cx="{W - tw - 22:.1f}" cy="{b - 6:.1f}" r="5.5" fill="none" stroke="{renk}" stroke-width="2"/>')
        s.ekle(f'<circle cx="{W - tw - 22:.1f}" cy="{b - 6:.1f}" r="5.5" fill="{renk}"/>')
        s.yazi(W, b - 1, t, "mono", 15, yaz, 0.75, hiza="end", aralik=1.5)
    return s


# ───────────────────────── bölüm başlığı (açık/koyu) ─────────────────────────

def bolum_basligi(b, sira, koyu):
    yaz = BEYAZ if koyu else "#111215"
    W, H = 1600, 250
    s = Svg(W, H, f'{b["kicker"]} — {b["baslik"]}')
    s.ekle(f'<rect x="0" y="62" width="40" height="9" fill="{AMBER}"/>')
    s.yazi(58, 72, f'{sira:02d}  —  {b["kicker"].upper()}', "mono", 21, yaz, 0.7, aralik=4)
    s.yazi(-4, 168, b["baslik"], "baslik", 86, yaz)
    s.yazi(0, 222, b["giris"], "italik", 32, yaz, 0.62)
    return s


# ───────────────────────── kapak görseli (hero) ─────────────────────────

def logo_yollari():
    import re
    svg = open(os.path.join(LOGO, "atasoy-logo-hareketli.svg")).read()
    return re.search(r'<path fill="#0D0F13" d="([^"]+)"', svg).group(1)


def hero(kisi, projeler, durum):
    W, H = 1600, 640
    s = Svg(W, H, "atasoy_ — Efe Atasoy. I build products, from idea to app store, solo, on one server.")
    s.defs.append(
        '<pattern id="izgara" width="32" height="32" patternUnits="userSpaceOnUse">'
        f'<circle cx="2" cy="2" r="1.3" fill="{BEYAZ}" fill-opacity=".07"/></pattern>'
        '<clipPath id="kart"><rect width="1600" height="640" rx="40"/></clipPath>'
        '<linearGradient id="sonum" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".22" stop-color="#fff" stop-opacity="1"/>'
        '<stop offset=".78" stop-color="#fff" stop-opacity="1"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        '<mask id="maske" maskUnits="userSpaceOnUse" x="1060" y="40" width="540" height="560">'
        '<rect x="1060" y="40" width="540" height="560" fill="url(#sonum)"/></mask>'
    )
    s.ekle(f'<rect width="{W}" height="{H}" rx="40" fill="{KARA}"/>')
    s.ekle('<g clip-path="url(#kart)">')
    s.ekle(f'<rect width="{W}" height="{H}" fill="url(#izgara)"/>')
    # sağ kenarda kehribar ışık
    s.defs.append(
        '<radialGradient id="isik" cx="1" cy="0" r="1"><stop offset="0" stop-color="#FFB020" stop-opacity=".16"/>'
        '<stop offset="1" stop-color="#FFB020" stop-opacity="0"/></radialGradient>'
    )
    s.ekle(f'<rect width="{W}" height="{H}" fill="url(#isik)"/>')

    # logo: atasoy + yanıp sönen _
    o = 0.205
    s.ekle(f'<g transform="translate(88 {96 + 765 * o:.1f}) scale({o})">'
           f'<path fill="{BEYAZ}" d="{logo_yollari()}"/>'
           f'<rect class="yanip" x="3525" y="-100" width="500" height="100" fill="{AMBER}"/></g>')

    s.yazi(92, 360, kisi["ad"], "italik", 44, "#A9ADB5")
    s.yazi(90, 432, "I build products, from idea", "baslik2", 52, BEYAZ)
    s.yazi(90, 494, "to app store, solo, on one server.", "baslik2", 52, BEYAZ)
    s.yazi(92, 576, "ATASOY.DEV   ·   CHAINMEDIA.CO", "mono", 19, SOLUK, aralik=3.5)

    # sağda kalkış tabelası gibi akan proje listesi
    s.ekle(f'<rect x="1040" y="70" width="1.5" height="500" fill="{BEYAZ}" fill-opacity=".1"/>')
    liste = [p for p in projeler if p["tur"] != "arac"]
    adim = 66
    toplam = adim * len(liste)
    s.css.append(
        f"@keyframes ak{{from{{transform:translateY(0)}}to{{transform:translateY(-{toplam}px)}}}}"
        f".ak{{animation:ak {len(liste) * 2.6:.0f}s linear infinite}}"
    )
    s.ekle('<g mask="url(#maske)"><g class="ak">')
    for tur in range(2):
        for i, p in enumerate(liste):
            y = 110 + (tur * len(liste) + i) * adim
            renk = p["renk"]["vurgu"] if parlaklik(p["renk"]["vurgu"]) > 0.08 else p["renk"]["zemin"]
            if parlaklik(renk) < 0.08:
                renk = BEYAZ
            s.ekle(f'<rect x="1096" y="{y - 13}" width="18" height="5" fill="{renk}"/>')
            s.yazi(1132, y, p["ad"], "baslik2", 32, BEYAZ, 0.92)
            s.yazi(1540, y - 3, durum[p["durum"]].upper(), "mono", 13, SOLUK, hiza="end", aralik=2)
    s.ekle("</g></g>")
    s.ekle("</g>")
    return s


# ───────────────────────── README ─────────────────────────

def picture(ad, alt, en="100%"):
    return (
        f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/{ad}-dark.svg">'
        f'<img src="assets/{ad}-light.svg" alt="{e(alt)}" width="{en}"></picture>'
    )


def gorsel_link(p, ad, en):
    img = f'<img src="assets/{ad}.svg" alt="{e(p["ad"] + " — " + p["en"]["kisa"])}" width="{en}">'
    return f'<a href="{e(p["link"])}">{img}</a>' if p.get("link") else img


def main():
    os.makedirs(ASSETS, exist_ok=True)
    kisi, bolumler, projeler, durum = yukle()
    boyut = {}

    sira = []  # hero listesi için görünme sırası
    for b in bolumler:
        for anahtar in ("kapak", "kisa", "musteri", "liste"):
            sira += [projeler[k] for k in b.get(anahtar, [])]

    boyut["hero"] = hero(kisi, sira, durum).bitir(os.path.join(ASSETS, "hero.svg"))

    md = []
    md.append('<a href="https://atasoy.dev"><img src="assets/hero.svg" alt="atasoy_ — Efe Atasoy. I build products, from idea to app store, solo, on one server." width="100%"></a>')
    md.append("")
    md.append(f'<p>{e(kisi["en"]["giris"])}</p>')
    md.append("")
    md.append('<p><a href="https://atasoy.dev"><b>atasoy.dev</b></a> &nbsp;·&nbsp; '
              '<a href="https://chainmedia.co"><b>chainmedia.co</b></a> &nbsp;·&nbsp; '
              f'<a href="{e(kisi["iletisim_link"])}">{e(kisi["en"]["iletisim_baslik"])} ↗</a></p>')

    v = json.load(open(os.path.join(KOK, "uretim", "veri.json")))
    acik = v.get("acik_kaynak", {})
    acik_yayinda = v.get("acik_kaynak_yayinda", False) or os.environ.get("ACIK_ONIZLE") == "1"
    acik_projeler = set(acik) if acik_yayinda else set()
    bolumler = [b for b in bolumler if b["id"] != "opensource" or acik_yayinda]
    for b in bolumler:
        if b.get("liste"):
            b["liste"] = [k for k in b["liste"] if k not in acik_projeler]

    no = 1
    for bi, b in enumerate(bolumler, 1):
        for koyu in (False, True):
            ad = f'h-{b["id"]}-{"dark" if koyu else "light"}'
            boyut[ad] = bolum_basligi(b, bi, koyu).bitir(os.path.join(ASSETS, ad + ".svg"))
        md += ["", "<br>", "", picture(f'h-{b["id"]}', f'{b["kicker"]} — {b["baslik"]}'), ""]

        for k in b.get("kapak", []):
            p = projeler[k]
            ad = f"kapak-{k}"
            boyut[ad] = kapak(p, no, durum).bitir(os.path.join(ASSETS, ad + ".svg"))
            md += [f"<p>{gorsel_link(p, ad, '100%')}</p>", ""]
            no += 1

        for anahtar, cizici, onek in (("kisa", kisa, "kart"), ("musteri", musteri, "musteri")):
            ogeler = b.get(anahtar, [])
            for i in range(0, len(ogeler), 2):
                parca = []
                for k in ogeler[i:i + 2]:
                    p = projeler[k]
                    ad = f"{onek}-{k}"
                    boyut[ad] = cizici(p, no, durum).bitir(os.path.join(ASSETS, ad + ".svg"))
                    parca.append(gorsel_link(p, ad, "49.4%"))
                    no += 1
                md += ["<p>" + "\n".join(parca) + "</p>", ""]

        if b.get("acik"):
            parca = []
            for k in b["acik"]:
                p, ak = projeler[k], acik[k]
                ad = f"acik-{k}"
                boyut[ad] = acik_kart(p, ak, no).bitir(os.path.join(ASSETS, ad + ".svg"))
                img = f'<img src="assets/{ad}.svg" alt="{e(p["ad"] + " — " + ak["en"]["kisa"])}" width="49.4%">'
                parca.append(f'<a href="https://github.com/{ak["repo"]}">{img}</a>')
                no += 1
            md += ["<p>" + "\n".join(parca) + "</p>", ""]
            yildiz = " &nbsp; ".join(
                f'<a href="https://github.com/{acik[k]["repo"]}"><img src="https://img.shields.io/github/stars/{acik[k]["repo"]}'
                f'?style=flat-square&label={urllib.parse.quote(projeler[k]["ad"][:12] + ("…" if len(projeler[k]["ad"]) > 12 else ""))}&logo=github" alt="{e(projeler[k]["ad"])} stars"></a>'
                for k in b["acik"])
            md += [f'<p align="center">{yildiz}</p>', ""]

        if b.get("liste"):
            liste = [projeler[k] for k in b["liste"]]
            for koyu in (False, True):
                ad = f'bench-{"dark" if koyu else "light"}'
                boyut[ad] = tezgah(liste, no, durum, koyu).bitir(os.path.join(ASSETS, ad + ".svg"))
            md += [picture("bench", "Workbench: " + "; ".join(f'{p["ad"]} — {p["en"]["kisa"]}' for p in liste)), ""]
            no += len(liste)

    md += [
        "", "<br>", "",
        "<p><b>How it runs.</b> One server: Caddy in front, every product as its own process, PostgreSQL behind. "
        "Web apps in Next.js and TypeScript, phone apps in Swift and Kotlin, desktop tools in Rust, games in Pixi and Godot. "
        "iOS builds go through GitHub Actions on macOS straight to TestFlight.</p>",
        "",
        "<p><sub>Most of the code lives in private repositories. Happy to walk you through any of it.</sub></p>",
        "",
        '<p><a href="https://atasoy.dev"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.svg">'
        '<img src="assets/logo-light.svg" alt="atasoy_" height="28"></picture></a></p>',
        "",
    ]
    # alt logo: hazır hareketli logolar
    for kaynak, hedef in (("atasoy-logo-hareketli.svg", "logo-light.svg"), ("atasoy-logo-beyaz-hareketli.svg", "logo-dark.svg")):
        with open(os.path.join(LOGO, kaynak)) as f, open(os.path.join(ASSETS, hedef), "w") as g:
            g.write(f.read())

    with open(os.path.join(KOK, "README.md"), "w") as f:
        f.write("\n".join(md))

    toplam = sum(boyut.values())
    for k, v in sorted(boyut.items(), key=lambda x: -x[1])[:6]:
        print(f"  {k:28s} {v / 1024:7.1f} KB")
    print(f"{len(boyut)} svg, toplam {toplam / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()
