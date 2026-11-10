"""Yazı tipleri: değişken fontları sabit ağırlığa indirir, metni ölçer,
SVG'ye gömülecek alt küme (woff2, base64) üretir.

SVG'ler GitHub'da <img> olarak açılıyor: dışarıdan font çekemez. Bu yüzden
her SVG kendi kullandığı harfleri içine gömülü taşıyor.
"""
import base64
import io
import os
from functools import lru_cache

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTLAR = os.path.join(KOK, "fontlar")
INDIRILEN = os.path.join(FONTLAR, "indirilen")

# ad -> (kaynak dosya, eksenler, css adı)
TANIM = {
    "baslik": ("Bricolage-var.ttf", {"wght": 700, "opsz": 96, "wdth": 86}, "AB"),
    "baslik2": ("Bricolage-var.ttf", {"wght": 560, "opsz": 36, "wdth": 96}, "AB2"),
    "serif": ("SourceSerif4-var.ttf", {"wght": 400, "opsz": 22}, "AS"),
    "italik": ("SourceSerif4-Italic-var.ttf", {"wght": 400, "opsz": 40}, "ASI"),
    "mono": ("/root/atasoy-dev/marka/kaynak/JetBrainsMono-var.ttf", {"wght": 520}, "AM"),
}


@lru_cache(maxsize=None)
def font(ad):
    kaynak, eksen, _ = TANIM[ad]
    hedef = os.path.join(FONTLAR, f"{ad}.ttf")
    if not os.path.exists(hedef):
        yol = kaynak if os.path.isabs(kaynak) else os.path.join(INDIRILEN, kaynak)
        f = TTFont(yol)
        sabit = instancer.instantiateVariableFont(f, eksen)
        sabit.save(hedef)
    return TTFont(hedef)


@lru_cache(maxsize=None)
def _olcu(ad):
    f = font(ad)
    return f.getBestCmap(), f["hmtx"].metrics, f["head"].unitsPerEm


def genislik(metin, ad, boy, aralik=0.0):
    cmap, hmtx, upm = _olcu(ad)
    t = 0
    for ch in metin:
        g = cmap.get(ord(ch)) or cmap.get(ord("?"))
        t += hmtx[g][0]
    return t * boy / upm + aralik * max(len(metin) - 1, 0)


def sar(metin, ad, boy, en, aralik=0.0):
    """Kelime kelime satıra böler."""
    satirlar, satir = [], ""
    for k in metin.split():
        aday = (satir + " " + k).strip()
        if satir and genislik(aday, ad, boy, aralik) > en:
            satirlar.append(satir)
            satir = k
        else:
            satir = aday
    if satir:
        satirlar.append(satir)
    return satirlar


class Kullanim:
    """Bir SVG'de hangi fontta hangi harfler geçti — sonunda gömülür."""

    def __init__(self):
        self.harf = {}

    def ekle(self, ad, metin):
        self.harf.setdefault(ad, set()).update(metin)

    def css(self):
        parca = []
        for ad, harfler in sorted(self.harf.items()):
            f = font(ad)
            s = subset.Subsetter(subset.Options())
            s.options.flavor = "woff2"
            s.options.layout_features = ["kern", "liga", "calt"]
            s.options.name_IDs = []
            s.options.notdef_outline = False
            s.populate(text="".join(harfler) + " ")
            kopya = TTFont(io.BytesIO(_ham(ad)))
            s.subset(kopya)
            kopya.flavor = "woff2"
            b = io.BytesIO()
            kopya.save(b)
            veri = base64.b64encode(b.getvalue()).decode()
            css_ad = TANIM[ad][2]
            parca.append(
                f"@font-face{{font-family:'{css_ad}';src:url(data:font/woff2;base64,{veri}) format('woff2')}}"
            )
        return "".join(parca)


@lru_cache(maxsize=None)
def _ham(ad):
    font(ad)  # sabit kopya yoksa üretir
    with open(os.path.join(FONTLAR, f"{ad}.ttf"), "rb") as fp:
        return fp.read()


def aile(ad):
    yedek = {
        "baslik": "sans-serif", "baslik2": "sans-serif",
        "serif": "serif", "italik": "serif", "mono": "monospace",
    }[ad]
    return f"'{TANIM[ad][2]}',{yedek}"
