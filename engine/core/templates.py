"""Procedural template library (shared by every theme).

Each template is a function(**params) -> Canvas using the standard legend.
Recipes can reference templates directly as "tpl:<name>" (with optional params),
so themes reuse them without creating files. Themes only save new assets when
they need a bespoke grid or a frozen variant.
"""
from __future__ import annotations
import random
from .pixel import Canvas

TEMPLATES: dict[str, dict] = {}

# layer order for compositing (lower = further back)
LAYER = {"back": 5, "body": 10, "legs": 20, "boots": 25, "top": 30, "belt": 35,
         "face": 40, "beard": 45, "hair": 50, "hat": 60, "held": 70, "offhand": 72,
         "fx": 90, "base": 10, "outfit": 30, "tile": 0, "object": 50, "creature": 10,
         "backdrop": 0, "icon": 0, "hair_back": 2}


def template(name, category, kind, layer="body", desc="", params=None, tags="", colors=None):
    def deco(fn):
        TEMPLATES[name] = {"fn": fn, "category": category, "kind": kind, "layer": LAYER.get(layer, 50),
                           "slot": layer, "desc": desc, "params": params or {}, "colors": colors or {},
                           "tags": [t for t in tags.split() if t]}
        return fn
    return deco


def build_template(name, params=None):
    t = TEMPLATES[name]
    p = dict(t["params"]); p.update({k: v for k, v in (params or {}).items() if k in t["params"]})
    return t["fn"](**p)


# =====================================================================
#  CHARACTER SPRITES  16x24  (front facing, chibi)
# =====================================================================
SW, SH = 16, 24
GEO = {  # torso x0,x1 ; left arm x0,x1 ; right arm x0,x1
    "slim":   dict(t=(6, 9), la=(4, 5), ra=(10, 11), ll=(6, 7), rl=(8, 9)),
    "normal": dict(t=(5, 10), la=(3, 4), ra=(11, 12), ll=(5, 7), rl=(8, 10)),
    "broad":  dict(t=(4, 11), la=(2, 3), ra=(12, 13), ll=(5, 7), rl=(8, 10)),
}
BUILD = {"build": "normal"}


def _head(cv, c="s", dark="S"):
    cv.rect(5, 2, 6, 1, c).rect(4, 3, 8, 6, c).rect(5, 9, 6, 1, c)
    cv.px(4, 8, dark).px(11, 8, dark).px(5, 9, dark).px(10, 9, dark)
    cv.px(10, 3, "c").px(9, 3, "c")


def _limbs(cv, g, c="s", dark="S", y0=11, y1=16, hands=True):
    for (a, b), inner in ((g["la"], g["la"][1]), (g["ra"], g["ra"][0])):
        cv.rect(a, y0, b - a + 1, y1 - y0 + 1, c)
        cv.vline(inner, y0 + 1, y1, dark)
        if hands:
            cv.rect(a, y1 + 1, b - a + 1, 1, "s")


@template("body", "character", "sprite", "body", "Humanoid base body with eyes. build=slim|normal|broad",
          params={**BUILD, "eyes": True}, tags="humanoid base body person")
def t_body(build="normal", eyes=True):
    g = GEO.get(build, GEO["normal"]); cv = Canvas(SW, SH)
    _head(cv)
    cv.rect(7, 10, 2, 1, "S")
    cv.rect(g["t"][0], 11, g["t"][1] - g["t"][0] + 1, 6, "s")
    _limbs(cv, g)
    cv.rect(g["ll"][0], 17, g["ll"][1] - g["ll"][0] + 1, 5, "s")
    cv.rect(g["rl"][0], 17, g["rl"][1] - g["rl"][0] + 1, 5, "s")
    cv.vline(g["ll"][1], 18, 21, "S")
    cv.rect(g["ll"][0] - 1, 22, g["ll"][1] - g["ll"][0] + 2, 2, "S")
    cv.rect(g["rl"][0], 22, g["rl"][1] - g["rl"][0] + 2, 2, "S")
    if eyes:
        cv.px(6, 6, "e").px(9, 6, "e").px(6, 5, "e").px(9, 5, "e")
    return cv.outline()


# ---------- hair ----------
def _hair_cap(cv):
    cv.rect(5, 1, 6, 1, "h").rect(4, 2, 8, 2, "h").rect(3, 3, 1, 3, "h").rect(12, 3, 1, 3, "h")
    cv.px(4, 4, "h").px(11, 4, "h").px(5, 4, "H").px(10, 4, "H")
    cv.px(9, 1, "j").px(10, 2, "j")


@template("hair_short", "character", "sprite", "hair", "Short hair", tags="hair short")
def t_hair_short():
    cv = Canvas(SW, SH); _hair_cap(cv); cv.px(6, 4, "h").px(7, 4, "H"); return cv.outline()


@template("hair_long", "character", "sprite", "hair", "Long hair past shoulders", tags="hair long")
def t_hair_long():
    cv = Canvas(SW, SH); _hair_cap(cv)
    cv.rect(3, 5, 1, 9, "h").rect(12, 5, 1, 9, "h").rect(2, 8, 1, 6, "H").rect(13, 8, 1, 6, "H")
    cv.px(4, 5, "h").px(11, 5, "h").px(4, 6, "H").px(11, 6, "H")
    return cv.outline()


@template("hair_spiky", "character", "sprite", "hair", "Spiky hair", tags="hair spiky punk")
def t_hair_spiky():
    cv = Canvas(SW, SH); _hair_cap(cv)
    for x in (4, 6, 8, 10):
        cv.px(x, 0, "h").px(x + 1, 0, "j")
    cv.px(3, 2, "h").px(12, 2, "h").px(2, 3, "h").px(13, 3, "h")
    return cv.outline()


@template("hair_bun", "character", "sprite", "hair", "Hair tied in a top bun", tags="hair bun")
def t_hair_bun():
    cv = Canvas(SW, SH); _hair_cap(cv)
    cv.rect(6, 0, 4, 1, "h").px(8, 0, "j")
    return cv.outline()


@template("hair_ponytail", "character", "sprite", "hair", "Ponytail", tags="hair ponytail")
def t_hair_ponytail():
    cv = Canvas(SW, SH); _hair_cap(cv)
    cv.rect(12, 5, 2, 3, "h").rect(13, 8, 2, 4, "h").vline(14, 9, 12, "H")
    return cv.outline()


@template("hair_mohawk", "character", "sprite", "hair", "Mohawk", tags="hair mohawk punk")
def t_hair_mohawk():
    cv = Canvas(SW, SH)
    cv.rect(7, 0, 2, 4, "h").px(7, 0, "j").px(7, 1, "j")
    return cv.outline()


@template("hair_curly", "character", "sprite", "hair", "Big curly hair", tags="hair curly afro")
def t_hair_curly():
    cv = Canvas(SW, SH)
    cv.ellipse(7.5, 3, 5.5, 3.6, "h")
    cv.rect(3, 4, 1, 3, "h").rect(12, 4, 1, 3, "h")
    cv.noise("h", "H", 0.25, seed=3).noise("h", "j", 0.12, seed=5)
    cv.rect(5, 4, 6, 6, ".").rect(4, 5, 8, 5, ".")
    return cv.outline()


@template("beard", "character", "sprite", "beard", "Full beard", tags="beard facial hair")
def t_beard():
    cv = Canvas(SW, SH)
    cv.rect(4, 7, 1, 2, "h").rect(11, 7, 1, 2, "h").rect(5, 8, 6, 2, "h").rect(6, 10, 4, 1, "h")
    cv.rect(7, 8, 2, 1, "r").px(7, 10, "H").px(8, 10, "H")
    return cv


# ---------- tops ----------
def _torso(cv, g, c, y0=11, y1=16):
    cv.rect(g["t"][0], y0, g["t"][1] - g["t"][0] + 1, y1 - y0 + 1, c)


@template("top_shirt", "character", "sprite", "top", "Short-sleeve shirt/tunic with belt", params=dict(BUILD),
          tags="clothes shirt tunic top")
def t_top_shirt(build="normal"):
    g = GEO.get(build, GEO["normal"]); cv = Canvas(SW, SH)
    _torso(cv, g, "t"); _limbs(cv, g, "t", "T", 11, 12, hands=False)
    cv.hline(g["t"][0], g["t"][1], 16, "a").px(7, 16, "v")
    cv.px(7, 11, "T").px(8, 11, "T").px(7, 12, "T")
    cv.vline(g["t"][1], 12, 15, "T")
    return cv.outline()


@template("top_coat", "character", "sprite", "top", "Long coat with sleeves and tails", params=dict(BUILD),
          tags="clothes coat trenchcoat jacket long")
def t_top_coat(build="normal"):
    g = GEO.get(build, GEO["normal"]); cv = Canvas(SW, SH)
    _torso(cv, g, "t", 11, 19); _limbs(cv, g, "t", "T", 11, 16, hands=False)
    cv.vline(7, 12, 19, "a").vline(8, 12, 19, "T")
    cv.px(6, 11, "u").px(9, 11, "u").px(g["t"][0], 11, "u").px(g["t"][1], 11, "u")
    cv.hline(g["t"][0], g["t"][1], 16, "T")
    cv.vline(g["t"][1], 12, 19, "T")
    return cv.outline()


@template("top_robe", "character", "sprite", "top", "Floor-length robe", params=dict(BUILD),
          tags="clothes robe gown mage priest dress")
def t_top_robe(build="normal"):
    g = GEO.get(build, GEO["normal"]); cv = Canvas(SW, SH)
    cv.poly([(g["t"][0], 11), (g["t"][1] + 1, 11), (g["t"][1] + 2, 23), (g["t"][0] - 1, 23)], "t")
    _limbs(cv, g, "t", "T", 11, 16, hands=False)
    cv.vline(7, 11, 22, "a").vline(8, 11, 22, "a")
    cv.hline(g["t"][0], g["t"][1], 15, "A")
    cv.rect(g["la"][0], 16, g["la"][1] - g["la"][0] + 1, 1, "a").rect(g["ra"][0], 16, g["ra"][1] - g["ra"][0] + 1, 1, "a")
    cv.replace("t", "T", mask=lambda x, y: x >= 10 and y > 16)
    return cv.outline()


@template("top_armor", "character", "sprite", "top", "Plate/combat armour with pauldrons", params=dict(BUILD),
          tags="armor armour plate knight soldier combat")
def t_top_armor(build="normal"):
    g = GEO.get(build, GEO["normal"]); cv = Canvas(SW, SH)
    _torso(cv, g, "m"); _limbs(cv, g, "m", "M", 13, 16, hands=False)
    cv.rect(g["la"][0] - 1, 10, g["la"][1] - g["la"][0] + 3, 3, "m").rect(g["ra"][0] - 1, 10, g["ra"][1] - g["ra"][0] + 3, 3, "m")
    cv.px(g["la"][0], 10, "n").px(g["ra"][0], 10, "n")
    cv.hline(g["t"][0], g["t"][1], 16, "a").hline(g["t"][0], g["t"][1], 13, "M")
    cv.px(7, 12, "n").px(7, 14, "n").vline(g["t"][1], 11, 15, "M")
    return cv.outline()


@template("top_jacket", "character", "sprite", "top", "Open jacket over a shirt (accent)", params=dict(BUILD),
          tags="clothes jacket modern leather hoodie")
def t_top_jacket(build="normal"):
    g = GEO.get(build, GEO["normal"]); cv = Canvas(SW, SH)
    _torso(cv, g, "t"); _limbs(cv, g, "t", "T", 11, 16, hands=False)
    cv.rect(7, 11, 2, 6, "a").px(7, 11, "v")
    cv.px(6, 11, "u").px(9, 11, "u").vline(g["t"][1], 12, 16, "T")
    cv.rect(g["la"][0], 16, g["la"][1] - g["la"][0] + 1, 1, "T").rect(g["ra"][0], 16, g["ra"][1] - g["ra"][0] + 1, 1, "T")
    return cv.outline()


@template("top_vest", "character", "sprite", "top", "Sleeveless vest/harness", params=dict(BUILD),
          tags="clothes vest sleeveless harness rogue")
def t_top_vest(build="normal"):
    g = GEO.get(build, GEO["normal"]); cv = Canvas(SW, SH)
    _torso(cv, g, "t"); cv.vline(7, 11, 15, "a").px(8, 13, "a")
    cv.hline(g["t"][0], g["t"][1], 16, "B").px(8, 16, "m").vline(g["t"][1], 12, 15, "T")
    return cv.outline()


@template("cloak", "character", "sprite", "back", "Cloak/cape hanging behind", tags="cloak cape back")
def t_cloak():
    cv = Canvas(SW, SH)
    cv.poly([(3, 10), (13, 10), (15, 22), (1, 22)], "a")
    cv.replace("a", "A", mask=lambda x, y: x > 9 or y > 19)
    return cv.outline()


@template("wings", "character", "sprite", "back", "Wings behind body (feathered/bat by colours)", tags="wings angel demon")
def t_wings():
    cv = Canvas(SW, SH)
    cv.poly([(5, 12), (0, 5), (0, 16), (4, 18)], "k")
    cv.poly([(11, 12), (16, 5), (16, 16), (12, 18)], "k")
    cv.noise("k", "K", 0.3, seed=2)
    return cv.outline()


# ---------- legs / boots ----------
@template("legs_pants", "character", "sprite", "legs", "Trousers", tags="pants trousers legs")
def t_legs_pants():
    cv = Canvas(SW, SH)
    cv.rect(5, 17, 3, 5, "l").rect(8, 17, 3, 5, "l").vline(7, 18, 21, "L").hline(5, 10, 17, "L")
    return cv.outline()


@template("legs_skirt", "character", "sprite", "legs", "Skirt/kilt", tags="skirt kilt legs")
def t_legs_skirt():
    cv = Canvas(SW, SH)
    cv.poly([(5, 17), (11, 17), (12, 21), (4, 21)], "l")
    for x in (5, 7, 9, 11):
        cv.px(x, 20, "L")
    return cv.outline()


@template("boots", "character", "sprite", "boots", "Boots", tags="boots shoes feet")
def t_boots():
    cv = Canvas(SW, SH)
    cv.rect(5, 20, 3, 2, "b").rect(8, 20, 3, 2, "b").rect(4, 22, 4, 2, "B").rect(8, 22, 4, 2, "B")
    cv.px(5, 20, "b").hline(4, 7, 22, "b").hline(8, 11, 22, "b")
    return cv.outline()


# ---------- hats ----------
@template("hat_hood", "character", "sprite", "hat", "Hood framing the face", tags="hood hat cloak rogue")
def t_hat_hood():
    cv = Canvas(SW, SH)
    cv.rect(5, 0, 6, 1, "a").rect(4, 1, 8, 2, "a").rect(3, 3, 2, 8, "a").rect(11, 3, 2, 8, "a")
    cv.rect(5, 3, 6, 1, "A").rect(4, 10, 8, 1, "a").rect(12, 4, 1, 6, "A")
    return cv.outline()


@template("hat_helmet", "character", "sprite", "hat", "Metal helmet with visor slit", tags="helmet armor knight soldier")
def t_hat_helmet():
    cv = Canvas(SW, SH)
    cv.rect(5, 0, 6, 1, "m").rect(4, 1, 8, 5, "m").rect(3, 3, 1, 5, "m").rect(12, 3, 1, 5, "m")
    cv.hline(4, 11, 5, "x").px(6, 5, "g").px(9, 5, "g").px(6, 1, "n").px(7, 1, "n").vline(11, 1, 4, "M")
    return cv.outline()


@template("hat_cap", "character", "sprite", "hat", "Cap with brim", tags="cap hat modern")
def t_hat_cap():
    cv = Canvas(SW, SH)
    cv.rect(5, 0, 6, 1, "a").rect(4, 1, 8, 2, "a").hline(3, 12, 3, "A").px(6, 1, "v")
    return cv.outline()


@template("hat_wizard", "character", "sprite", "hat", "Tall pointed hat with brim", tags="wizard witch hat mage")
def t_hat_wizard():
    cv = Canvas(SW, SH)
    cv.poly([(8, -1), (12, 3.5), (4, 3.5)], "a")
    cv.hline(2, 13, 3, "a").hline(3, 12, 4, "A").hline(5, 10, 2, "v")
    return cv.outline()


@template("hat_wide", "character", "sprite", "hat", "Wide-brim hat (cowboy/ranger/detective)", tags="hat cowboy fedora detective ranger")
def t_hat_wide():
    cv = Canvas(SW, SH)
    cv.rect(5, 0, 6, 3, "a").hline(1, 14, 3, "a").hline(2, 13, 4, "A").hline(5, 10, 2, "k")
    return cv.outline()


@template("crown", "character", "sprite", "hat", "Crown/circlet", tags="crown royal king queen")
def t_crown():
    cv = Canvas(SW, SH)
    cv.hline(4, 11, 2, "a").px(4, 1, "a").px(7, 0, "a").px(8, 0, "a").px(11, 1, "a").px(6, 1, "a").px(9, 1, "a").px(7, 2, "g").px(8, 2, "g")
    return cv.outline()


@template("horns", "character", "sprite", "hat", "Horns", tags="horns demon tiefling beast")
def t_horns():
    cv = Canvas(SW, SH)
    cv.px(4, 2, "k").px(3, 1, "k").px(3, 0, "z").px(11, 2, "k").px(12, 1, "k").px(12, 0, "z")
    return cv.outline()


@template("ears_pointy", "character", "sprite", "face", "Pointed ears (elf etc.)", tags="ears elf pointy")
def t_ears():
    cv = Canvas(SW, SH)
    cv.px(3, 5, "s").px(2, 4, "s").px(12, 5, "s").px(13, 4, "s")
    return cv.outline()


@template("mask", "character", "sprite", "face", "Lower-face mask/respirator", tags="mask bandana respirator")
def t_mask():
    cv = Canvas(SW, SH)
    cv.rect(4, 7, 8, 3, "a").px(7, 8, "A").px(8, 8, "A")
    return cv


@template("goggles", "character", "sprite", "face", "Goggles/visor over eyes", tags="goggles visor glasses cyber")
def t_goggles():
    cv = Canvas(SW, SH)
    cv.hline(4, 11, 5, "m").rect(5, 5, 2, 2, "g").rect(9, 5, 2, 2, "g").px(5, 5, "f")
    return cv


@template("eyepatch", "character", "sprite", "face", "Eyepatch", tags="eyepatch pirate")
def t_eyepatch():
    cv = Canvas(SW, SH)
    cv.line(4, 3, 11, 6, "o"); cv.rect(8, 5, 3, 2, "o")
    return cv


@template("tail", "character", "sprite", "back", "Tail", tags="tail beast demon lizard")
def t_tail():
    cv = Canvas(SW, SH)
    cv.line(10, 17, 14, 19, "k").line(14, 19, 15, 15, "k").line(10, 18, 14, 20, "K")
    return cv.outline()


# ---------- held items (right hand x11-12,y17 ; left hand x3-4,y17) ----------
@template("held_sword", "item", "sprite", "held", "Sword in right hand", tags="sword blade weapon melee")
def t_held_sword():
    cv = Canvas(SW, SH)
    cv.vline(14, 6, 15, "n").vline(15, 7, 15, "m").px(14, 5, "n")
    cv.hline(12, 15, 16, "a").rect(13, 17, 1, 2, "w")
    return cv.outline(skip="")


@template("held_staff", "item", "sprite", "held", "Staff with glowing orb", tags="staff magic wand weapon")
def t_held_staff():
    cv = Canvas(SW, SH)
    cv.vline(13, 4, 23, "w").ellipse(13, 2.5, 1.6, 1.6, "g").px(13, 2, "f")
    return cv.outline()


@template("held_dagger", "item", "sprite", "held", "Dagger/knife", tags="dagger knife weapon")
def t_held_dagger():
    cv = Canvas(SW, SH)
    cv.vline(13, 13, 16, "n").px(12, 17, "a").px(14, 17, "a").px(13, 18, "w")
    return cv.outline()


@template("held_gun", "item", "sprite", "held", "Pistol/blaster", tags="gun pistol blaster ranged firearm")
def t_held_gun():
    cv = Canvas(SW, SH)
    cv.hline(12, 15, 16, "m").px(15, 15, "M").rect(13, 17, 1, 2, "M").px(14, 16, "g")
    return cv.outline()


@template("held_rifle", "item", "sprite", "held", "Rifle/long gun held diagonally", tags="rifle gun ranged firearm")
def t_held_rifle():
    cv = Canvas(SW, SH)
    cv.line(9, 19, 15, 10, "m").line(10, 19, 15, 11, "M").px(15, 10, "n")
    return cv.outline()


@template("held_bow", "item", "sprite", "held", "Bow", tags="bow ranged archer weapon")
def t_held_bow():
    cv = Canvas(SW, SH)
    for y, x in zip(range(9, 24), [13, 14, 14, 15, 15, 15, 15, 15, 15, 15, 14, 14, 13]):
        cv.px(x, y, "w")
    cv.vline(13, 9, 21, "y")
    return cv.outline()


@template("held_axe", "item", "sprite", "held", "Axe/hammer", tags="axe hammer weapon melee")
def t_held_axe():
    cv = Canvas(SW, SH)
    cv.vline(13, 8, 19, "w").rect(14, 8, 2, 4, "m").px(15, 8, "n").px(12, 9, "m")
    return cv.outline()


@template("held_torch", "item", "sprite", "held", "Torch/flare", tags="torch fire light")
def t_held_torch():
    cv = Canvas(SW, SH)
    cv.vline(13, 13, 18, "w").rect(12, 11, 3, 2, "g").px(13, 10, "f").px(13, 11, "f")
    return cv.outline()


@template("offhand_shield", "item", "sprite", "offhand", "Shield on left arm", tags="shield defense")
def t_offhand_shield():
    cv = Canvas(SW, SH)
    cv.poly([(0, 12), (5, 12), (5, 17), (2.5, 20), (0, 17)], "m")
    cv.vline(2, 13, 18, "a").hline(1, 4, 14, "a").px(1, 12, "n")
    return cv.outline()


@template("offhand_lantern", "item", "sprite", "offhand", "Lantern in left hand", tags="lantern light")
def t_offhand_lantern():
    cv = Canvas(SW, SH)
    cv.rect(2, 18, 3, 3, "g").px(3, 19, "f").hline(2, 4, 17, "m").hline(2, 4, 21, "m")
    return cv.outline()


@template("offhand_book", "item", "sprite", "offhand", "Book/tablet in left hand", tags="book tome tablet")
def t_offhand_book():
    cv = Canvas(SW, SH)
    cv.rect(1, 15, 4, 4, "a").vline(4, 15, 18, "y").px(2, 16, "A")
    return cv.outline()


# =====================================================================
#  PORTRAITS 32x32 (bust, for dialogue)
# =====================================================================
PW = PH = 32


def _in_head(x, y):
    return ((x - 15.5) / 7.6) ** 2 + ((y - 13) / 8.6) ** 2 <= 1


@template("p_base", "portrait", "portrait", "base", "Portrait base: head, neck, shoulders (skin)",
          params={"jaw": "normal"}, tags="portrait base head")
def t_p_base(jaw="normal"):
    cv = Canvas(PW, PH)
    cv.poly([(3, 32), (29, 32), (27, 25), (20, 22.5), (12, 22.5), (5, 25)], "s")
    cv.rect(13, 19, 6, 5, "S")
    cv.ellipse(15.5, 13, 7.6, 8.6, "s")
    if jaw == "square":
        cv.rect(10, 17, 12, 3, "s").rect(11, 20, 10, 1, "s")
    elif jaw == "narrow":
        cv.replace("s", ".", mask=lambda x, y: y >= 19 and (x < 13 or x > 18))
    cv.rect(7, 12, 1, 4, "s").rect(24, 12, 1, 4, "s").px(7, 13, "S").px(24, 13, "S")
    # shading right side of face
    cv.replace("s", "S", mask=lambda x, y: _in_head(x, y) and not _in_head(x + 1.6, y) and x > 16)
    cv.px(11, 8, "c").px(12, 7, "c").px(13, 7, "c")
    return cv.outline()


def _eye(cv, x, y, right=False, style="open"):
    # eye occupies x..x+2, y..y+1
    if style == "open":
        cv.hline(x, x + 2, y - 1, "o")
        cv.hline(x, x + 2, y, "y").hline(x, x + 2, y + 1, "y")
        px = x + (0 if right else 1)
        cv.rect(px, y, 2, 2, "e").px(px + (1 if not right else 0), y, "y")
    elif style == "wide":
        cv.hline(x, x + 2, y - 2, "o")
        cv.rect(x, y - 1, 3, 3, "y").px(x + 1, y, "e").px(x + 1, y + 1, "e")
    elif style == "happy":
        cv.px(x, y + 1, "o").px(x + 1, y, "o").px(x + 2, y + 1, "o")
    elif style == "closed":
        cv.hline(x, x + 2, y + 1, "o")
    elif style == "squeeze":
        if right:
            cv.px(x + 2, y - 1, "o").px(x + 1, y, "o").px(x + 2, y + 1, "o")
        else:
            cv.px(x, y - 1, "o").px(x + 1, y, "o").px(x, y + 1, "o")
    elif style == "narrow":
        cv.hline(x, x + 2, y, "o").hline(x, x + 2, y + 1, "y")
        cv.rect(x + (0 if right else 1), y + 1, 2, 1, "e")


def _brow(cv, x, y_out, y_in, right=False):
    # 3px brow; y_out = outer end, y_in = inner end
    xs = [x, x + 1, x + 2]
    ys = [y_out, round((y_out + y_in) / 2), y_in] if not right else [y_in, round((y_out + y_in) / 2), y_out]
    for xx, yy in zip(xs, ys):
        cv.px(xx, yy, "H")


def _mouth(cv, style):
    if style == "flat":
        cv.hline(14, 17, 18, "r")
    elif style == "smile":
        cv.hline(14, 17, 18, "r").px(13, 17, "r").px(18, 17, "r")
    elif style == "grin":
        cv.hline(13, 18, 17, "r").hline(14, 17, 18, "y").hline(14, 17, 19, "r")
    elif style == "frown":
        cv.hline(14, 17, 18, "r").px(13, 19, "r").px(18, 19, "r")
    elif style == "o":
        cv.rect(15, 18, 2, 2, "r").px(14, 18, "o").px(17, 19, "o")
    elif style == "smirk":
        cv.hline(14, 16, 18, "r").px(17, 17, "r")
    elif style == "grimace":
        cv.rect(13, 18, 6, 2, "r").hline(14, 17, 18, "y")
    elif style == "thin":
        cv.hline(14, 17, 18, "S")


FACES = {
    #            eyes      brow out,in     mouth
    "neutral":   ("open",   (10, 10),       "flat"),
    "happy":     ("happy",  (9, 9),         "smile"),
    "laugh":     ("happy",  (9, 9),         "grin"),
    "angry":     ("narrow", (9, 11),        "frown"),
    "sad":       ("open",   (11, 9),        "frown"),
    "surprised": ("wide",   (8, 8),         "o"),
    "smirk":     ("narrow", (10, 9),        "smirk"),
    "hurt":      ("squeeze", (10, 11),      "grimace"),
    "calm":      ("closed", (10, 10),       "smile"),
    "determined": ("narrow", (10, 11),      "thin"),
    "scared":    ("wide",   (11, 8),        "grimace"),
}


def _make_face(expr):
    def fn():
        eyes, (bo, bi), mouth = FACES[expr]
        cv = Canvas(PW, PH)
        _eye(cv, 11, 13, False, eyes); _eye(cv, 18, 13, True, eyes)
        _brow(cv, 11, bo, bi, False); _brow(cv, 18, bo, bi, True)
        cv.px(16, 16, "S").px(15, 16, "S")
        _mouth(cv, mouth)
        return cv
    return fn


for _e in FACES:
    template(f"p_face_{_e}", "portrait", "portrait", "face", f"Face expression: {_e}", tags=f"face expression {_e}")(_make_face(_e))


def _p_cap(cv, low=10):
    for y in range(0, low + 1):
        for x in range(PW):
            if ((x - 15.5) / 8.6) ** 2 + ((y - 12.4) / 9.4) ** 2 <= 1:
                cv.px(x, y, "h")
    # fringe
    for x in range(9, 23):
        if (x * 7) % 5 < 3:
            cv.px(x, low + 1, "h")
    cv.rect(8, low, 2, 5, "h").rect(22, low, 2, 5, "h")


def _p_hairshade(cv, seed=1):
    cv.replace("h", "H", mask=lambda x, y: x > 19 or (y > 9 and (x < 10 or x > 21)))
    cv.px(12, 5, "j").px(13, 4, "j").px(14, 4, "j").px(11, 6, "j")
    return cv


@template("p_hair_short", "portrait", "portrait", "hair", "Short hair", tags="hair short")
def t_p_hair_short():
    cv = Canvas(PW, PH); _p_cap(cv, 9); return _p_hairshade(cv).outline()


@template("p_hair_long", "portrait", "portrait", "hair", "Long hair (front strands). Pair with p_hair_back.", tags="hair long")
def t_p_hair_long():
    cv = Canvas(PW, PH); _p_cap(cv, 9)
    cv.rect(7, 10, 3, 16, "h").rect(22, 10, 3, 16, "h").rect(6, 16, 2, 11, "H").rect(24, 16, 2, 11, "H")
    return _p_hairshade(cv).outline()


@template("p_hair_back", "portrait", "portrait", "hair_back", "Hair mass behind head/shoulders (for long styles)",
          tags="hair back long")
def t_p_hair_back():
    cv = Canvas(PW, PH)
    cv.ellipse(15.5, 13, 10, 10, "H").rect(5, 13, 22, 15, "H")
    cv.noise("H", "h", 0.12, seed=7)
    return cv.outline()


@template("p_hair_spiky", "portrait", "portrait", "hair", "Spiky hair", tags="hair spiky punk")
def t_p_hair_spiky():
    cv = Canvas(PW, PH); _p_cap(cv, 8)
    for i, x in enumerate(range(8, 24, 3)):
        cv.poly([(x, 5), (x + 3, 5), (x + 1.5 - (1 if i % 2 else -1), 0)], "h")
    return _p_hairshade(cv).outline()


@template("p_hair_bun", "portrait", "portrait", "hair", "Hair in a bun", tags="hair bun")
def t_p_hair_bun():
    cv = Canvas(PW, PH); _p_cap(cv, 8); cv.ellipse(15.5, 2.5, 3.2, 2.6, "h")
    return _p_hairshade(cv).outline()


@template("p_hair_mohawk", "portrait", "portrait", "hair", "Mohawk", tags="hair mohawk punk")
def t_p_hair_mohawk():
    cv = Canvas(PW, PH); cv.rect(14, 0, 4, 9, "h").px(14, 0, "j").px(14, 1, "j").vline(17, 1, 8, "H")
    return cv.outline()


@template("p_hair_curly", "portrait", "portrait", "hair", "Big curly/afro hair", tags="hair curly afro")
def t_p_hair_curly():
    cv = Canvas(PW, PH); cv.ellipse(15.5, 10, 11.5, 9.5, "h")
    cv.replace("h", ".", mask=lambda x, y: y >= 10 and 10 <= x <= 21)
    cv.replace("h", ".", mask=lambda x, y: y >= 12 and 9 <= x <= 22)
    cv.noise("h", "H", 0.3, seed=11).noise("h", "j", 0.1, seed=12)
    return cv.outline()


@template("p_hair_bob", "portrait", "portrait", "hair", "Chin-length bob", tags="hair bob")
def t_p_hair_bob():
    cv = Canvas(PW, PH); _p_cap(cv, 9); cv.rect(7, 10, 3, 10, "h").rect(22, 10, 3, 10, "h")
    return _p_hairshade(cv).outline()


@template("p_hair_slick", "portrait", "portrait", "hair", "Slicked-back / undercut", tags="hair slick undercut")
def t_p_hair_slick():
    cv = Canvas(PW, PH)
    for y in range(0, 9):
        for x in range(PW):
            if ((x - 15.5) / 8.2) ** 2 + ((y - 12.4) / 9.0) ** 2 <= 1:
                cv.px(x, y, "h")
    for x in range(10, 22, 3):
        cv.px(x, 6, "j")
    return cv.outline()


# ---- outfits ----
def _shoulders(cv, c):
    cv.poly([(3, 32), (29, 32), (27, 25), (20, 23), (12, 23), (5, 25)], c)


@template("p_outfit_shirt", "portrait", "portrait", "outfit", "Simple shirt/tunic with V collar", tags="outfit shirt tunic")
def t_p_outfit_shirt():
    cv = Canvas(PW, PH); _shoulders(cv, "t")
    cv.poly([(13, 23), (19, 23), (16, 27)], "s")
    cv.line(13, 23, 16, 27, "T").line(19, 23, 16, 27, "T")
    cv.replace("t", "T", mask=lambda x, y: x > 22)
    return cv.outline()


@template("p_outfit_coat", "portrait", "portrait", "outfit", "Coat with lapels and collar", tags="outfit coat jacket trench")
def t_p_outfit_coat():
    cv = Canvas(PW, PH); _shoulders(cv, "t")
    cv.poly([(13, 23), (19, 23), (16, 30)], "a")
    cv.poly([(11, 22), (14, 23), (15, 31), (12, 27)], "u").poly([(21, 22), (18, 23), (17, 31), (20, 27)], "T")
    cv.replace("t", "T", mask=lambda x, y: x > 22)
    return cv.outline()


@template("p_outfit_armor", "portrait", "portrait", "outfit", "Armour with pauldrons and gorget", tags="outfit armor armour plate knight soldier")
def t_p_outfit_armor():
    cv = Canvas(PW, PH); _shoulders(cv, "m")
    cv.ellipse(6, 27, 4.2, 3.5, "m").ellipse(25, 27, 4.2, 3.5, "M")
    cv.rect(12, 21, 8, 4, "M").hline(12, 19, 22, "n")
    cv.px(4, 25, "n").px(5, 25, "n").px(15, 28, "a").px(16, 28, "a").px(15, 29, "a").px(16, 29, "a")
    return cv.outline()


@template("p_outfit_robe", "portrait", "portrait", "outfit", "Robe with high collar", tags="outfit robe mage priest")
def t_p_outfit_robe():
    cv = Canvas(PW, PH); _shoulders(cv, "t")
    cv.poly([(10, 20), (13, 23), (19, 23), (22, 20), (22, 25), (16, 28), (10, 25)], "a")
    cv.poly([(13, 23), (19, 23), (16, 27)], "s")
    cv.vline(16, 28, 31, "A").replace("t", "T", mask=lambda x, y: x > 22)
    return cv.outline()


@template("p_outfit_hoodie", "portrait", "portrait", "outfit", "Hoodie / hood down behind neck", tags="outfit hoodie hood modern")
def t_p_outfit_hoodie():
    cv = Canvas(PW, PH); _shoulders(cv, "t")
    cv.poly([(9, 22), (23, 22), (21, 26), (11, 26)], "T")
    cv.poly([(13, 23), (19, 23), (16, 26)], "s")
    cv.vline(14, 27, 30, "y").vline(18, 27, 30, "y")
    return cv.outline()


@template("p_outfit_uniform", "portrait", "portrait", "outfit", "Uniform with buttons and badge", tags="outfit uniform military officer police crew")
def t_p_outfit_uniform():
    cv = Canvas(PW, PH); _shoulders(cv, "t")
    cv.rect(12, 21, 8, 3, "t").hline(12, 19, 21, "a")
    cv.vline(16, 24, 31, "T")
    for y in (25, 28, 31):
        cv.px(17, y, "a")
    cv.rect(8, 26, 3, 2, "a").px(9, 26, "g").hline(4, 8, 25, "a").hline(24, 28, 25, "a")
    cv.replace("t", "T", mask=lambda x, y: x > 23)
    return cv.outline()


@template("p_outfit_rags", "portrait", "portrait", "outfit", "Ragged/worn clothes", tags="outfit rags peasant poor worn")
def t_p_outfit_rags():
    cv = Canvas(PW, PH); _shoulders(cv, "t")
    cv.poly([(12, 23), (20, 23), (16, 26)], "s")
    cv.noise("t", "T", 0.2, seed=4).noise("t", "a", 0.05, seed=9)
    for x in (6, 11, 19, 25):
        cv.px(x, 31, ".")
    return cv.outline()


# ---- portrait hats / extras ----
@template("p_hat_hood", "portrait", "portrait", "hat", "Hood framing the face", tags="hood hat cloak")
def t_p_hat_hood():
    cv = Canvas(PW, PH)
    cv.ellipse(15.5, 13, 11, 12, "a").rect(4, 18, 24, 8, "a")
    cv.replace("a", ".", mask=lambda x, y: ((x - 15.5) / 7.2) ** 2 + ((y - 14) / 8.5) ** 2 <= 1)
    cv.replace("a", "A", mask=lambda x, y: x > 20 or y > 22)
    return cv.outline()


@template("p_hat_helmet", "portrait", "portrait", "hat", "Helmet with cheek guards", tags="helmet armor knight soldier")
def t_p_hat_helmet():
    cv = Canvas(PW, PH)
    for y in range(0, 11):
        for x in range(PW):
            if ((x - 15.5) / 9.2) ** 2 + ((y - 12) / 10) ** 2 <= 1:
                cv.px(x, y, "m")
    cv.rect(6, 9, 3, 9, "m").rect(23, 9, 3, 9, "M").hline(7, 24, 10, "M")
    cv.vline(15, 2, 9, "n").vline(16, 2, 9, "a")
    return cv.outline()


@template("p_hat_cap", "portrait", "portrait", "hat", "Cap with brim", tags="cap hat modern")
def t_p_hat_cap():
    cv = Canvas(PW, PH)
    for y in range(1, 9):
        for x in range(PW):
            if ((x - 15.5) / 8.8) ** 2 + ((y - 10) / 9) ** 2 <= 1:
                cv.px(x, y, "a")
    cv.hline(6, 25, 9, "A").hline(5, 26, 10, "A").px(15, 1, "v")
    return cv.outline()


@template("p_hat_wizard", "portrait", "portrait", "hat", "Pointed wizard/witch hat", tags="wizard witch hat mage")
def t_p_hat_wizard():
    cv = Canvas(PW, PH)
    cv.poly([(19, -1), (23, 7), (8, 7)], "a").rect(3, 7, 26, 2, "A").hline(9, 22, 6, "k")
    return cv.outline()


@template("p_hat_wide", "portrait", "portrait", "hat", "Wide-brim hat (fedora/cowboy/ranger)", tags="hat fedora cowboy detective ranger")
def t_p_hat_wide():
    cv = Canvas(PW, PH)
    cv.rect(9, 1, 14, 6, "a").rect(1, 7, 30, 2, "A").hline(9, 22, 6, "k").px(12, 1, "v")
    return cv.outline()


@template("p_crown", "portrait", "portrait", "hat", "Crown", tags="crown royal")
def t_p_crown():
    cv = Canvas(PW, PH)
    cv.rect(9, 3, 14, 3, "a").hline(9, 22, 5, "A")
    for x in (9, 13, 18, 22):
        cv.px(x, 2, "a").px(x, 1, "a")
    cv.px(15, 4, "g").px(16, 4, "g")
    return cv.outline()


@template("p_headband", "portrait", "portrait", "hat", "Headband/bandana", tags="headband bandana")
def t_p_headband():
    cv = Canvas(PW, PH)
    cv.rect(8, 8, 16, 2, "a").rect(24, 9, 2, 1, "a").rect(25, 10, 2, 3, "A")
    return cv.outline()


@template("p_horns", "portrait", "portrait", "hat", "Horns", tags="horns demon beast")
def t_p_horns():
    cv = Canvas(PW, PH)
    cv.poly([(9, 7), (12, 5), (7, 0)], "k").poly([(22, 7), (19, 5), (24, 0)], "K")
    return cv.outline()


@template("p_beard", "portrait", "portrait", "beard", "Full beard", tags="beard facial hair")
def t_p_beard():
    cv = Canvas(PW, PH)
    cv.poly([(8, 13), (10, 13), (12, 17), (19, 17), (21, 13), (23, 13), (22, 19), (16, 24), (9, 19)], "h")
    cv.rect(14, 18, 4, 1, "r").noise("h", "H", 0.25, seed=2)
    return cv.outline()


@template("p_mustache", "portrait", "portrait", "beard", "Mustache", tags="mustache facial hair")
def t_p_mustache():
    cv = Canvas(PW, PH)
    cv.hline(13, 18, 17, "h").px(12, 18, "h").px(19, 18, "h")
    return cv


@template("p_glasses", "portrait", "portrait", "face", "Glasses", tags="glasses spectacles")
def t_p_glasses():
    cv = Canvas(PW, PH)
    cv.rect(10, 12, 5, 4, "m").rect(17, 12, 5, 4, "m").rect(11, 13, 3, 2, ".").rect(18, 13, 3, 2, ".").hline(15, 16, 13, "m")
    return cv


@template("p_visor", "portrait", "portrait", "face", "Tech visor/goggles across eyes", tags="visor goggles cyber tech")
def t_p_visor():
    cv = Canvas(PW, PH)
    cv.rect(8, 12, 16, 4, "g").hline(8, 23, 12, "f").hline(8, 23, 15, "G").px(7, 13, "m").px(24, 13, "m")
    return cv.outline()


@template("p_eyepatch", "portrait", "portrait", "face", "Eyepatch", tags="eyepatch pirate")
def t_p_eyepatch():
    cv = Canvas(PW, PH)
    cv.line(8, 9, 23, 13, "o").rect(18, 12, 4, 4, "o")
    return cv


@template("p_scar", "portrait", "portrait", "face", "Scar across the eye", tags="scar wound")
def t_p_scar():
    cv = Canvas(PW, PH)
    cv.line(11, 10, 14, 17, "r")
    return cv


@template("p_mask", "portrait", "portrait", "face", "Lower-face mask/respirator", tags="mask bandana respirator")
def t_p_mask():
    cv = Canvas(PW, PH)
    cv.poly([(9, 15), (22, 15), (21, 20), (16, 22), (10, 20)], "a")
    cv.px(14, 18, "A").px(17, 18, "A")
    return cv.outline()


@template("p_marks", "portrait", "portrait", "face", "Glowing facial marks/tattoo/cyber lines", tags="tattoo marks runes cyber glow")
def t_p_marks():
    cv = Canvas(PW, PH)
    cv.vline(10, 16, 19, "g").px(11, 19, "g").vline(21, 16, 19, "g").px(20, 19, "g").px(15, 7, "g").px(16, 7, "g")
    return cv


@template("p_ears_pointy", "portrait", "portrait", "face", "Pointed ears", tags="ears elf pointy")
def t_p_ears():
    cv = Canvas(PW, PH)
    cv.poly([(8, 12), (8, 16), (3, 9)], "s").poly([(24, 12), (24, 16), (29, 9)], "S")
    return cv.outline()


@template("p_earring", "portrait", "portrait", "face", "Earring", tags="earring jewelry")
def t_p_earring():
    cv = Canvas(PW, PH)
    cv.px(24, 16, "a").px(24, 17, "a")
    return cv


# =====================================================================
#  CREATURES  (colour via primary/secondary/glow slots)
# =====================================================================
@template("cr_slime", "creature", "sprite", "creature", "Slime/ooze/blob 16x16", tags="slime ooze blob jelly",
          colors={"primary": "#5fbf4a"})
def t_cr_slime():
    cv = Canvas(16, 16)
    cv.poly([(2, 15), (14, 15), (13, 8), (10, 4), (6, 4), (3, 8)], "p")
    cv.ellipse(8, 10, 5.5, 5, "p")
    cv.replace("p", "P", mask=lambda x, y: y >= 13 or x >= 12)
    cv.px(5, 6, "q").px(6, 5, "q").px(5, 7, "q")
    cv.rect(6, 9, 1, 2, "e").rect(9, 9, 1, 2, "e")
    return cv.outline()


@template("cr_bat", "creature", "sprite", "creature", "Bat/small flyer 16x16", tags="bat flyer wing swarm",
          colors={"primary": "#5a4a6a", "eyes": "#ff4a4a"})
def t_cr_bat():
    cv = Canvas(16, 16)
    cv.poly([(8, 6), (1, 3), (0, 10), (3, 8), (5, 11), (8, 9)], "p")
    cv.poly([(8, 6), (15, 3), (16, 10), (13, 8), (11, 11), (8, 9)], "p")
    cv.ellipse(8, 8, 2.2, 3, "P").px(7, 7, "e").px(9, 7, "e").px(6, 4, "P").px(10, 4, "P")
    return cv.outline()


@template("cr_beast", "creature", "sprite", "creature", "Four-legged beast (wolf/hound/cat) 24x16",
          params={"horns": False}, tags="beast wolf dog hound cat quadruped animal",
          colors={"primary": "#7a6a5a", "eyes": "#ffd84a"})
def t_cr_beast(horns=False):
    cv = Canvas(24, 16)
    cv.ellipse(12, 8, 7, 3.5, "p")
    cv.poly([(16, 6), (22, 5), (23, 8), (20, 10), (16, 10)], "p")
    cv.poly([(17, 5), (18, 2), (19, 5)], "P")
    cv.rect(6, 10, 2, 5, "P").rect(9, 10, 2, 5, "p").rect(14, 10, 2, 5, "P").rect(17, 10, 2, 5, "p")
    cv.line(5, 7, 1, 4, "p").line(5, 8, 1, 5, "P")
    cv.px(21, 6, "e").px(23, 7, "o")
    cv.replace("p", "P", mask=lambda x, y: y >= 10 and x < 16)
    cv.px(10, 5, "q").px(11, 5, "q").px(12, 5, "q")
    if horns:
        cv.line(19, 4, 21, 1, "k")
    return cv.outline()


@template("cr_spider", "creature", "sprite", "creature", "Spider/insect/crawler 16x16", tags="spider insect bug crawler",
          colors={"primary": "#3a3040", "eyes": "#ff3a3a"})
def t_cr_spider():
    cv = Canvas(16, 16)
    for s in (-1, 1):
        for i, y in enumerate((6, 8, 10, 12)):
            x0 = 8 + s * 3
            cv.line(x0, 9, x0 + s * 4, y - 2, "P").line(x0 + s * 4, y - 2, x0 + s * 6, y + 2, "P")
    cv.ellipse(8, 10, 3.5, 3, "p").ellipse(8, 6, 2.2, 2, "p")
    cv.px(7, 5, "e").px(9, 5, "e").px(7, 6, "e").px(9, 6, "e").px(7, 9, "q")
    return cv.outline()


@template("cr_skeleton", "creature", "sprite", "creature", "Skeleton/undead humanoid 16x24", tags="skeleton undead bones",
          colors={"primary": "#e8e0c8", "eyes": "#ff5a3a"})
def t_cr_skeleton():
    cv = Canvas(16, 24)
    cv.rect(5, 2, 6, 6, "p").rect(6, 8, 4, 2, "p").px(6, 5, "x").px(9, 5, "x").px(6, 5, "e").px(9, 5, "e")
    cv.px(7, 9, "o").px(8, 9, "o").vline(7, 10, 17, "p")
    for y in (12, 14, 16):
        cv.hline(5, 10, y, "p")
    cv.vline(4, 11, 17, "p").vline(11, 11, 17, "p").rect(5, 17, 6, 1, "P")
    cv.vline(6, 18, 23, "p").vline(9, 18, 23, "p").px(5, 23, "p").px(10, 23, "p")
    return cv.outline()


@template("cr_ghost", "creature", "sprite", "creature", "Ghost/spirit/wraith 16x24", tags="ghost spirit wraith undead phantom",
          colors={"primary": "#bfe6f0", "eyes": "#1a2a3a"})
def t_cr_ghost():
    cv = Canvas(16, 24)
    cv.ellipse(8, 8, 5.5, 6, "p").rect(3, 8, 11, 10, "p")
    for i, x in enumerate(range(3, 14, 2)):
        cv.rect(x, 18, 1, 2 + (i % 2) * 2, "p")
    cv.rect(5, 7, 2, 3, "e").rect(9, 7, 2, 3, "e").rect(7, 12, 2, 2, "e")
    cv.replace("p", "q", mask=lambda x, y: x < 6 and y < 10)
    cv.replace("p", "P", mask=lambda x, y: x > 11)
    return cv.outline()


@template("cr_golem", "creature", "sprite", "creature", "Hulking golem/robot/brute 24x24", tags="golem robot mech brute construct big",
          colors={"primary": "#8a8070", "glow": "#ff9a3a"})
def t_cr_golem():
    cv = Canvas(24, 24)
    cv.rect(7, 2, 10, 7, "p").rect(3, 9, 18, 9, "p").rect(0, 10, 4, 10, "P").rect(20, 10, 4, 10, "P")
    cv.rect(5, 18, 5, 6, "P").rect(14, 18, 5, 6, "P")
    cv.hline(9, 14, 5, "g").px(10, 5, "f").px(13, 5, "f")
    cv.rect(10, 12, 4, 3, "g").px(11, 13, "f")
    cv.noise("p", "q", 0.06, seed=8).hline(3, 20, 17, "P")
    return cv.outline()


@template("cr_serpent", "creature", "sprite", "creature", "Serpent/worm/eel 24x16", tags="serpent snake worm eel naga",
          colors={"primary": "#4a8a5a", "eyes": "#ffdd33"})
def t_cr_serpent():
    cv = Canvas(24, 16)
    pts = [(2, 12), (5, 13), (8, 12), (11, 10), (14, 11), (17, 12), (19, 9), (19, 6)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        cv.line(x0, y0, x1, y1, "p").line(x0, y0 + 1, x1, y1 + 1, "P")
    cv.ellipse(19.5, 4.5, 3, 2.4, "p").px(20, 4, "e").line(22, 5, 23, 6, "r")
    return cv.outline()


@template("cr_eye", "creature", "sprite", "creature", "Floating eye/orb/drone 16x16", tags="eye orb drone floating beholder watcher",
          colors={"primary": "#9a5a8a", "eyes": "#2a1a2a"})
def t_cr_eye():
    cv = Canvas(16, 16)
    cv.ellipse(8, 8, 6, 6, "p").ellipse(8, 8, 3.5, 3.5, "y").ellipse(8, 8, 1.6, 1.6, "e")
    cv.px(5, 4, "q").px(6, 3, "q").replace("p", "P", mask=lambda x, y: y > 11)
    return cv.outline()


@template("cr_drone", "creature", "sprite", "creature", "Hover drone/bot 16x16", tags="drone robot bot machine scifi",
          colors={"primary": "#7a8494", "glow": "#ff3a3a"})
def t_cr_drone():
    cv = Canvas(16, 16)
    cv.rect(4, 5, 8, 6, "p").rect(0, 4, 4, 2, "m").rect(12, 4, 4, 2, "m").rect(6, 7, 4, 2, "g").px(7, 7, "f")
    cv.vline(6, 11, 13, "M").vline(9, 11, 13, "M").hline(4, 11, 10, "P")
    return cv.outline()


@template("cr_plant", "creature", "sprite", "creature", "Carnivorous plant/treant sprout 16x24", tags="plant vine treant flower",
          colors={"primary": "#4a8a3a", "secondary": "#c0304a"})
def t_cr_plant():
    cv = Canvas(16, 24)
    cv.vline(7, 10, 22, "P").vline(8, 10, 22, "p").poly([(8, 16), (2, 13), (4, 18)], "p").poly([(8, 19), (14, 15), (12, 21)], "p")
    cv.ellipse(8, 6, 5, 4.5, "k").poly([(4, 7), (12, 7), (8, 11)], "x").hline(5, 11, 7, "y")
    cv.rect(3, 22, 10, 2, "W")
    return cv.outline()


@template("cr_rat", "creature", "sprite", "creature", "Rat/vermin/small critter 16x16", tags="rat vermin critter small animal",
          colors={"primary": "#7a6a6a", "eyes": "#ff3a3a"})
def t_cr_rat():
    cv = Canvas(16, 16)
    cv.ellipse(7, 11, 4.5, 2.6, "p").poly([(10, 9), (14, 11), (10, 13)], "p").px(11, 9, "q").px(12, 10, "e")
    cv.line(2, 11, 0, 8, "r").px(5, 14, "P").px(9, 14, "P")
    return cv.outline()


@template("cr_drake", "creature", "sprite", "creature", "Drake/dragon/large winged beast 32x24", tags="dragon drake wyvern boss big",
          colors={"primary": "#a03a2a", "secondary": "#e0b04a", "eyes": "#ffee55"})
def t_cr_drake():
    cv = Canvas(32, 24)
    cv.poly([(12, 8), (4, 0), (2, 10), (10, 12)], "K").poly([(18, 8), (26, 1), (28, 10), (20, 12)], "K")
    cv.ellipse(15, 14, 7, 5, "p").rect(9, 17, 3, 6, "P").rect(18, 17, 3, 6, "P")
    cv.line(22, 12, 26, 6, "p").line(23, 12, 27, 6, "p").ellipse(28, 5, 3.2, 2.4, "p")
    cv.px(29, 4, "e").px(27, 2, "k").px(26, 1, "k").line(8, 15, 2, 20, "p").line(8, 16, 1, 21, "P")
    cv.hline(11, 19, 17, "k").hline(12, 18, 18, "k").px(13, 11, "q").px(14, 10, "q")
    return cv.outline()


# =====================================================================
#  TILES 16x16  (map)  primary = main material, secondary = accent
# =====================================================================
def _tile(fn):
    return fn


@template("tile_floor_stone", "tile", "tile", "tile", "Stone flagstone floor", tags="floor stone dungeon",
          colors={"primary": "#5a5866"})
def t_floor_stone(seed=1):
    cv = Canvas(16, 16).rect(0, 0, 16, 16, "p")
    cv.hline(0, 15, 7, "P").hline(0, 15, 15, "P").vline(5, 0, 7, "P").vline(11, 8, 15, "P")
    cv.noise("p", "q", 0.05, seed=seed).noise("p", "P", 0.04, seed=seed + 1)
    return cv


@template("tile_floor_wood", "tile", "tile", "tile", "Wooden plank floor", tags="floor wood planks tavern house",
          colors={"wood": "#7a5030"})
def t_floor_wood():
    cv = Canvas(16, 16).rect(0, 0, 16, 16, "w")
    for y in (3, 7, 11, 15):
        cv.hline(0, 15, y, "W")
    for y, x in ((1, 4), (5, 11), (9, 2), (13, 9)):
        cv.px(x, y, "W")
    cv.noise("w", "i", 0.04, seed=3)
    return cv


@template("tile_floor_metal", "tile", "tile", "tile", "Metal deck plates", tags="floor metal deck scifi ship industrial",
          colors={"metal": "#6a7280"})
def t_floor_metal():
    cv = Canvas(16, 16).rect(0, 0, 16, 16, "m")
    cv.hline(0, 15, 0, "n").vline(0, 0, 15, "n").hline(0, 15, 15, "M").vline(15, 0, 15, "M")
    for x, y in ((2, 2), (13, 2), (2, 13), (13, 13)):
        cv.px(x, y, "M")
    cv.hline(4, 11, 7, "M").hline(4, 11, 9, "M")
    return cv


@template("tile_floor_tile", "tile", "tile", "tile", "Checkered tiles (palace/lab/diner)", tags="floor tile checker palace lab",
          colors={"primary": "#d8d0c0", "secondary": "#8a8070"})
def t_floor_tile():
    cv = Canvas(16, 16)
    for y in range(16):
        for x in range(16):
            cv.px(x, y, "p" if ((x // 8) + (y // 8)) % 2 == 0 else "k")
    return cv


@template("tile_grass", "tile", "tile", "tile", "Grass/meadow", tags="grass ground outdoor field",
          colors={"secondary": "#4f8a3b"})
def t_grass():
    cv = Canvas(16, 16).rect(0, 0, 16, 16, "k")
    cv.noise("k", "K", 0.12, seed=21).noise("k", "z", 0.08, seed=22)
    for x, y in ((3, 4), (10, 9), (6, 13)):
        cv.px(x, y, "z").px(x + 1, y - 1, "z")
    return cv


@template("tile_dirt", "tile", "tile", "tile", "Dirt/earth/mud ground", tags="dirt ground path mud earth",
          colors={"primary": "#7a5a3a"})
def t_dirt():
    return Canvas(16, 16).rect(0, 0, 16, 16, "p").noise("p", "P", 0.14, seed=31).noise("p", "q", 0.06, seed=32)


@template("tile_sand", "tile", "tile", "tile", "Sand/desert/beach", tags="sand desert beach dunes",
          colors={"primary": "#d8b878"})
def t_sand():
    cv = Canvas(16, 16).rect(0, 0, 16, 16, "p").noise("p", "P", 0.06, seed=41)
    cv.hline(2, 6, 5, "q").hline(9, 13, 11, "q")
    return cv


@template("tile_snow", "tile", "tile", "tile", "Snow/ice ground", tags="snow ice frozen winter",
          colors={"primary": "#e4eef6"})
def t_snow():
    return Canvas(16, 16).rect(0, 0, 16, 16, "p").noise("p", "P", 0.06, seed=51).noise("p", "q", 0.1, seed=52)


@template("tile_water", "tile", "tile", "tile", "Water (impassable unless swimming)", tags="water river lake sea liquid",
          colors={"primary": "#2f5f9a"})
def t_water():
    cv = Canvas(16, 16).rect(0, 0, 16, 16, "p")
    for x, y in ((2, 3), (9, 6), (4, 11), (11, 13)):
        cv.hline(x, x + 3, y, "q").px(x + 1, y + 1, "P")
    return cv


@template("tile_lava", "tile", "tile", "tile", "Lava/acid/toxic pool (glow)", tags="lava acid toxic hazard fire pool",
          colors={"glow": "#ff6a1a"})
def t_lava():
    cv = Canvas(16, 16).rect(0, 0, 16, 16, "g").noise("g", "G", 0.2, seed=61).noise("g", "f", 0.1, seed=62)
    return cv


@template("tile_void", "tile", "tile", "tile", "Pit/chasm/void", tags="pit chasm void hole abyss",
          colors={"primary": "#0e0c14"})
def t_void():
    cv = Canvas(16, 16).rect(0, 0, 16, 16, "P").noise("P", "p", 0.05, seed=71)
    return cv


@template("tile_road", "tile", "tile", "tile", "Paved road/cobblestone", tags="road street cobble path",
          colors={"primary": "#6a6460"})
def t_road():
    cv = Canvas(16, 16).rect(0, 0, 16, 16, "p")
    for y in range(0, 16, 4):
        off = 2 if (y // 4) % 2 else 0
        cv.hline(0, 15, y, "P")
        for x in range(off, 16, 5):
            cv.vline(x, y, y + 3, "P")
    cv.noise("p", "q", 0.05, seed=81)
    return cv


@template("tile_wall_brick", "tile", "tile", "tile", "Brick/masonry wall (solid)", tags="wall brick masonry dungeon castle solid",
          colors={"primary": "#6a5a58"})
def t_wall_brick():
    cv = Canvas(16, 16).rect(0, 0, 16, 16, "p")
    for y in range(0, 16, 4):
        cv.hline(0, 15, y + 3, "P")
        off = 4 if (y // 4) % 2 else 0
        for x in range(off, 16, 8):
            cv.vline(x, y, y + 2, "P")
        cv.hline(0, 15, y, "q")
    return cv


@template("tile_wall_rock", "tile", "tile", "tile", "Natural rock/cave wall (solid)", tags="wall rock cave cliff solid",
          colors={"primary": "#4a4450"})
def t_wall_rock():
    cv = Canvas(16, 16).rect(0, 0, 16, 16, "p")
    cv.ellipse(4, 4, 4, 3, "q").ellipse(12, 10, 4, 4, "q").ellipse(3, 13, 3, 2, "q")
    cv.noise("p", "P", 0.25, seed=91).noise("q", "p", 0.2, seed=92)
    return cv


@template("tile_wall_metal", "tile", "tile", "tile", "Metal bulkhead wall (solid)", tags="wall metal bulkhead scifi solid",
          colors={"metal": "#4a5260", "glow": "#3ad0ff"})
def t_wall_metal():
    cv = Canvas(16, 16).rect(0, 0, 16, 16, "M").rect(1, 1, 14, 6, "m").rect(1, 9, 14, 6, "m")
    cv.hline(1, 14, 1, "n").hline(1, 14, 9, "n").hline(3, 12, 8, "g")
    return cv


@template("tile_wall_wood", "tile", "tile", "tile", "Wooden wall/palisade (solid)", tags="wall wood cabin palisade solid",
          colors={"wood": "#6a4428"})
def t_wall_wood():
    cv = Canvas(16, 16).rect(0, 0, 16, 16, "w")
    for x in (3, 7, 11, 15):
        cv.vline(x, 0, 15, "W")
    cv.px(1, 3, "i").px(5, 9, "i").px(9, 5, "i").px(13, 12, "i")
    return cv


@template("tile_wall_hedge", "tile", "tile", "tile", "Hedge/dense foliage wall (solid)", tags="wall hedge foliage forest bush solid",
          colors={"secondary": "#2f6a2f"})
def t_wall_hedge():
    cv = Canvas(16, 16).rect(0, 0, 16, 16, "k")
    for cx, cy in ((3, 3), (11, 4), (6, 10), (13, 12), (1, 13)):
        cv.ellipse(cx, cy, 3, 3, "z")
    cv.noise("k", "K", 0.3, seed=101).noise("z", "k", 0.2, seed=102)
    return cv


@template("tile_door", "tile", "tile", "tile", "Closed door", tags="door closed entrance",
          colors={"wood": "#7a4a2a", "primary": "#6a5a58"})
def t_door():
    cv = Canvas(16, 16).rect(0, 0, 16, 16, "p").rect(3, 1, 10, 15, "w")
    cv.vline(6, 1, 15, "W").vline(9, 1, 15, "W").px(11, 8, "a").hline(3, 12, 1, "i")
    return cv


@template("tile_door_open", "tile", "tile", "tile", "Open doorway", tags="door open doorway entrance",
          colors={"wood": "#7a4a2a", "primary": "#6a5a58"})
def t_door_open():
    cv = Canvas(16, 16).rect(0, 0, 16, 16, "p").rect(3, 1, 10, 15, "x").rect(3, 1, 2, 15, "w")
    return cv


@template("tile_stairs_down", "tile", "tile", "tile", "Stairs down / exit", tags="stairs down exit descend",
          colors={"primary": "#5a5866"})
def t_stairs_down():
    cv = Canvas(16, 16).rect(0, 0, 16, 16, "p")
    for i, y in enumerate(range(2, 16, 3)):
        cv.rect(1 + i, y, 14 - 2 * i, 2, "P").hline(1 + i, 14 - i, y, "q")
    cv.rect(6, 14, 4, 2, "x")
    return cv


@template("tile_stairs_up", "tile", "tile", "tile", "Stairs up", tags="stairs up ascend",
          colors={"primary": "#5a5866"})
def t_stairs_up():
    cv = Canvas(16, 16).rect(0, 0, 16, 16, "P")
    for i, y in enumerate(range(13, 0, -3)):
        cv.rect(1 + i, y, 14 - 2 * i, 2, "p").hline(1 + i, 14 - i, y, "q")
    return cv


@template("tile_bridge", "tile", "tile", "tile", "Bridge/walkway planks over water or pit", tags="bridge walkway planks",
          colors={"wood": "#8a5a34", "primary": "#2f5f9a"})
def t_bridge():
    cv = Canvas(16, 16).rect(0, 0, 16, 16, "p").rect(2, 0, 12, 16, "w")
    for y in range(1, 16, 3):
        cv.hline(2, 13, y, "W")
    cv.vline(2, 0, 15, "i").vline(13, 0, 15, "W")
    return cv


@template("tile_tree", "tile", "tile", "tile", "Tree (top-down canopy, solid)", tags="tree forest obstacle solid",
          colors={"secondary": "#3a7a3a", "wood": "#5a3a22"})
def t_tree():
    cv = Canvas(16, 16).rect(0, 0, 16, 16, "k").noise("k", "K", 0.12, seed=111)
    cv.ellipse(8, 7, 6.5, 6, "K").ellipse(7, 6, 5, 4.5, "k").ellipse(6, 5, 2.5, 2, "z").rect(7, 13, 2, 3, "w")
    return cv


@template("tile_rock", "tile", "tile", "tile", "Boulder on ground (solid)", tags="rock boulder obstacle solid",
          colors={"primary": "#7a7470", "secondary": "#4f8a3b"})
def t_rock():
    cv = Canvas(16, 16).rect(0, 0, 16, 16, "k").noise("k", "K", 0.12, seed=121)
    cv.ellipse(8, 9, 6, 4.5, "P").ellipse(7, 8, 5, 3.5, "p").px(5, 6, "q").px(6, 6, "q")
    return cv


@template("tile_pillar", "tile", "tile", "tile", "Pillar/column (solid)", tags="pillar column ruins temple solid",
          colors={"primary": "#8a8490"})
def t_pillar():
    cv = Canvas(16, 16).rect(0, 0, 16, 16, "P").noise("P", "p", 0.1, seed=131)
    cv.ellipse(8, 8, 5, 5, "q").ellipse(8, 8, 3.5, 3.5, "p").px(6, 6, "z")
    return cv


@template("tile_rubble", "tile", "tile", "tile", "Rubble/debris floor (difficult terrain)", tags="rubble debris ruins difficult",
          colors={"primary": "#5a5866"})
def t_rubble():
    cv = Canvas(16, 16).rect(0, 0, 16, 16, "p").noise("p", "P", 0.1, seed=141)
    for cx, cy, r in ((4, 4, 2), (11, 6, 2.5), (6, 12, 1.8), (13, 13, 1.5)):
        cv.ellipse(cx, cy, r, r * 0.8, "q").px(int(cx), int(cy + r * 0.8), "P")
    return cv


# =====================================================================
#  OBJECTS 16x16 (placed on map or in scenes)
# =====================================================================
@template("obj_chest", "object", "sprite", "object", "Treasure chest/lootbox", params={"open": False},
          tags="chest loot treasure container box", colors={"wood": "#8a5a2a", "accent": "#e0b040"})
def t_obj_chest(open=False):
    cv = Canvas(16, 16)
    cv.rect(2, 7, 12, 7, "w").hline(2, 13, 10, "W")
    if open:
        cv.rect(2, 3, 12, 4, "W").rect(3, 7, 10, 2, "x").px(6, 7, "g").px(9, 7, "a").px(8, 6, "a")
    else:
        cv.rect(2, 4, 12, 4, "w").hline(2, 13, 4, "i")
    cv.rect(7, 8, 2, 3, "a").vline(2, 4, 13, "a").vline(13, 4, 13, "a")
    return cv.outline()


@template("obj_crate", "object", "sprite", "object", "Crate/supply box", tags="crate box supplies container",
          colors={"wood": "#9a6a3a"})
def t_obj_crate():
    cv = Canvas(16, 16).rect(2, 3, 12, 12, "w")
    cv.hline(2, 13, 3, "i").line(3, 4, 12, 13, "W").line(12, 4, 3, 13, "W")
    for x, y in ((2, 3), (13, 3), (2, 14), (13, 14)):
        cv.px(x, y, "W")
    return cv.outline()


@template("obj_barrel", "object", "sprite", "object", "Barrel/drum/canister", tags="barrel drum canister container",
          colors={"wood": "#7a4a2a", "metal": "#6a6a70"})
def t_obj_barrel():
    cv = Canvas(16, 16).ellipse(8, 9, 5, 6, "w").rect(4, 4, 8, 11, "w")
    cv.hline(3, 12, 6, "m").hline(3, 12, 12, "m").vline(6, 4, 14, "i").vline(11, 4, 14, "W")
    cv.ellipse(8, 3.5, 4, 1.4, "W")
    return cv.outline()


@template("obj_table", "object", "sprite", "object", "Table/desk", tags="table desk furniture",
          colors={"wood": "#8a5a34"})
def t_obj_table():
    cv = Canvas(16, 16).rect(1, 5, 14, 5, "w").hline(1, 14, 5, "i").hline(1, 14, 9, "W")
    cv.rect(2, 10, 2, 5, "W").rect(12, 10, 2, 5, "W")
    return cv.outline()


@template("obj_chair", "object", "sprite", "object", "Chair/stool", tags="chair stool seat furniture",
          colors={"wood": "#8a5a34"})
def t_obj_chair():
    cv = Canvas(16, 16).rect(5, 2, 6, 7, "w").rect(4, 9, 8, 2, "w").rect(4, 11, 1, 4, "W").rect(11, 11, 1, 4, "W")
    cv.hline(5, 10, 2, "i")
    return cv.outline()


@template("obj_bed", "object", "sprite", "object", "Bed/bunk/cot", tags="bed bunk cot rest furniture",
          colors={"wood": "#7a4a2a", "accent": "#a03a3a"})
def t_obj_bed():
    cv = Canvas(16, 16).rect(2, 1, 12, 14, "w").rect(3, 2, 10, 4, "y").rect(3, 6, 10, 8, "a").hline(3, 12, 6, "v")
    return cv.outline()


@template("obj_shelf", "object", "sprite", "object", "Bookshelf/cabinet", tags="bookshelf shelf cabinet books library",
          colors={"wood": "#6a4428"})
def t_obj_shelf():
    cv = Canvas(16, 16).rect(1, 0, 14, 16, "w")
    for y in (1, 6, 11):
        for i, x in enumerate(range(2, 14)):
            cv.rect(x, y, 1, 4, ["a", "k", "p", "t", "y"][(x * 7 + y) % 5])
        cv.hline(1, 14, y + 4, "W")
    return cv.outline()


@template("obj_torch", "object", "sprite", "object", "Wall torch/sconce/lamp (light source)", tags="torch sconce lamp light fire",
          colors={"glow": "#ffae3a"})
def t_obj_torch():
    cv = Canvas(16, 16).rect(7, 7, 2, 7, "w").hline(6, 9, 7, "m").ellipse(8, 4.5, 2.2, 3, "g").px(8, 4, "f").px(8, 5, "f")
    return cv.outline()


@template("obj_lamppost", "object", "sprite", "object", "Street lamp/lantern post (16x24)", tags="lamp post streetlight lantern light",
          colors={"metal": "#3a3a44", "glow": "#ffe08a"})
def t_obj_lamppost():
    cv = Canvas(16, 24).vline(8, 5, 22, "m").hline(6, 10, 23, "M").rect(6, 1, 5, 4, "g").px(8, 2, "f").hline(6, 10, 0, "m").hline(6, 10, 5, "m")
    return cv.outline()


@template("obj_campfire", "object", "sprite", "object", "Campfire/brazier", tags="campfire fire brazier rest light",
          colors={"glow": "#ff8a2a", "wood": "#6a4428"})
def t_obj_campfire():
    cv = Canvas(16, 16)
    cv.line(3, 14, 12, 11, "w").line(3, 11, 12, 14, "W")
    cv.poly([(4, 12), (12, 12), (10, 6), (8, 2), (6, 6)], "g").poly([(6, 12), (10, 12), (8, 6)], "f")
    return cv.outline()


@template("obj_altar", "object", "sprite", "object", "Altar/pedestal/shrine", tags="altar pedestal shrine ritual",
          colors={"primary": "#8a8490", "glow": "#c07aff"})
def t_obj_altar():
    cv = Canvas(16, 16).rect(2, 8, 12, 7, "p").rect(1, 7, 14, 2, "q").rect(4, 10, 8, 4, "P")
    cv.ellipse(8, 4, 2.2, 2.2, "g").px(7, 3, "f")
    return cv.outline()


@template("obj_statue", "object", "sprite", "object", "Statue (16x24)", tags="statue monument idol",
          colors={"primary": "#9a948a"})
def t_obj_statue():
    cv = Canvas(16, 24)
    cv.rect(6, 1, 4, 4, "p").rect(5, 5, 6, 8, "p").rect(3, 6, 2, 6, "p").rect(11, 6, 2, 6, "p").rect(6, 13, 4, 5, "p")
    cv.rect(2, 18, 12, 5, "P").hline(2, 13, 18, "q").replace("p", "P", mask=lambda x, y: x >= 9)
    return cv.outline()


@template("obj_sign", "object", "sprite", "object", "Signpost/notice board", tags="sign signpost notice board",
          colors={"wood": "#8a5a34"})
def t_obj_sign():
    cv = Canvas(16, 16).rect(7, 7, 2, 9, "W").rect(2, 2, 12, 6, "w").hline(4, 11, 4, "W").hline(4, 9, 6, "W")
    return cv.outline()


@template("obj_lever", "object", "sprite", "object", "Lever/switch/button", tags="lever switch button mechanism",
          colors={"metal": "#7a7a84", "accent": "#d04a3a"})
def t_obj_lever():
    cv = Canvas(16, 16).rect(4, 11, 8, 4, "m").hline(4, 11, 11, "n").line(8, 11, 11, 4, "M").ellipse(11, 3.5, 1.5, 1.5, "a")
    return cv.outline()


@template("obj_trap", "object", "sprite", "object", "Spike trap/floor hazard", tags="trap spikes hazard",
          colors={"metal": "#9aa0aa"})
def t_obj_trap():
    cv = Canvas(16, 16)
    for x, y in ((3, 4), (8, 4), (13, 4), (5, 9), (10, 9), (3, 14), (8, 14), (13, 14)):
        cv.poly([(x - 1.5, y + 1), (x + 1.5, y + 1), (x, y - 2)], "m")
        cv.px(x, y - 1, "n")
    return cv.outline()


@template("obj_bones", "object", "sprite", "object", "Bones/remains", tags="bones remains skull corpse",
          colors={"primary": "#e0d8c0"})
def t_obj_bones():
    cv = Canvas(16, 16).rect(4, 4, 5, 4, "p").px(5, 5, "x").px(7, 5, "x").rect(5, 8, 3, 1, "p")
    cv.line(9, 12, 14, 9, "p").line(2, 13, 7, 14, "p").px(10, 7, "P")
    return cv.outline()


@template("obj_terminal", "object", "sprite", "object", "Computer terminal/console/machine", tags="terminal computer console machine scifi",
          colors={"metal": "#4a5260", "glow": "#3aff9a"})
def t_obj_terminal():
    cv = Canvas(16, 16).rect(2, 2, 12, 9, "m").rect(3, 3, 10, 7, "G")
    cv.hline(4, 9, 4, "g").hline(4, 11, 6, "g").hline(4, 7, 8, "f").rect(4, 11, 8, 4, "M").hline(5, 10, 12, "n")
    return cv.outline()


@template("obj_crystal", "object", "sprite", "object", "Crystal/gem cluster/relic", tags="crystal gem relic shard magic",
          colors={"glow": "#7ae0ff"})
def t_obj_crystal():
    cv = Canvas(16, 16)
    cv.poly([(6, 15), (10, 15), (9, 3), (7, 3)], "g").poly([(2, 15), (6, 15), (4, 8)], "G").poly([(10, 15), (14, 15), (12, 6)], "G")
    cv.vline(7, 4, 13, "f")
    return cv.outline()


@template("obj_pot", "object", "sprite", "object", "Pot/urn/vase/jar", tags="pot urn vase jar container",
          colors={"primary": "#a06a4a"})
def t_obj_pot():
    cv = Canvas(16, 16).ellipse(8, 10, 5, 5, "p").rect(6, 3, 4, 3, "p").hline(5, 10, 3, "P").px(5, 8, "q").px(5, 9, "q")
    return cv.outline()


@template("obj_cauldron", "object", "sprite", "object", "Cauldron/vat", tags="cauldron vat pot brew",
          colors={"metal": "#3a3a40", "glow": "#7aff5a"})
def t_obj_cauldron():
    cv = Canvas(16, 16).ellipse(8, 10, 6, 4.5, "m").ellipse(8, 7, 5.5, 1.6, "g").px(6, 4, "f").px(10, 3, "f").rect(3, 14, 2, 2, "M").rect(11, 14, 2, 2, "M")
    return cv.outline()


@template("obj_grave", "object", "sprite", "object", "Gravestone/tomb marker", tags="grave tombstone cemetery",
          colors={"primary": "#7a7a80"})
def t_obj_grave():
    cv = Canvas(16, 16).rect(4, 4, 8, 11, "p").ellipse(8, 4, 4, 2.5, "p").hline(6, 9, 7, "P").vline(8, 5, 10, "P").hline(2, 13, 15, "W")
    return cv.outline()


@template("obj_portal", "object", "sprite", "object", "Portal/gate/rift (16x24)", tags="portal gate rift teleport magic",
          colors={"primary": "#5a5866", "glow": "#b05aff"})
def t_obj_portal():
    cv = Canvas(16, 24).ellipse(8, 11, 7, 10, "p").ellipse(8, 11, 5, 8, "g").ellipse(8, 11, 3, 5, "f").ellipse(8, 11, 1.4, 2.5, "G")
    return cv.outline()


@template("obj_fence", "object", "sprite", "object", "Fence/barricade section", tags="fence barricade barrier",
          colors={"wood": "#7a5030"})
def t_obj_fence():
    cv = Canvas(16, 16)
    for x in (1, 7, 13):
        cv.rect(x, 3, 2, 12, "w").px(x, 3, "i")
    cv.hline(0, 15, 6, "W").hline(0, 15, 11, "W")
    return cv.outline()


@template("obj_vehicle", "object", "sprite", "object", "Cart/wagon/car/vehicle (32x16)", tags="vehicle cart wagon car transport",
          colors={"primary": "#8a3a2a", "metal": "#3a3a40"})
def t_obj_vehicle():
    cv = Canvas(32, 16).rect(3, 4, 26, 7, "p").rect(8, 1, 14, 4, "P").rect(10, 2, 4, 2, "g").rect(16, 2, 4, 2, "g")
    cv.ellipse(8, 12, 3, 3, "m").ellipse(24, 12, 3, 3, "m").px(8, 12, "n").px(24, 12, "n").hline(3, 28, 4, "q")
    return cv.outline()


# ---- items (also usable as inventory icons) ----
@template("item_potion", "item", "icon", "icon", "Potion/vial/stim", tags="potion vial flask heal consumable stim",
          colors={"glow": "#e04a5a"})
def t_item_potion():
    cv = Canvas(16, 16).rect(6, 1, 4, 2, "w").rect(7, 3, 2, 3, "y").ellipse(8, 10, 5, 5, "g").hline(4, 12, 8, "y")
    cv.px(6, 9, "f").px(6, 10, "f").replace("g", "G", mask=lambda x, y: y > 12)
    return cv.outline()


@template("item_scroll", "item", "icon", "icon", "Scroll/letter/document", tags="scroll letter note document paper",
          colors={"detail": "#e8dcb8"})
def t_item_scroll():
    cv = Canvas(16, 16).rect(3, 3, 10, 10, "d").rect(2, 2, 12, 2, "D").rect(2, 12, 12, 2, "D")
    for y in (6, 8, 10):
        cv.hline(5, 10, y, "x")
    return cv.outline()


@template("item_key", "item", "icon", "icon", "Key/keycard", tags="key keycard access unlock",
          colors={"accent": "#e0b040"})
def t_item_key():
    cv = Canvas(16, 16).ellipse(5, 5, 3.5, 3.5, "a").px(5, 5, ".").px(4, 5, ".").line(7, 7, 13, 13, "a").px(12, 10, "a").px(11, 11, "a").px(10, 12, "A")
    return cv.outline()


@template("item_coins", "item", "icon", "icon", "Coins/money/credits", tags="coins money gold credits currency",
          colors={"accent": "#f0c040"})
def t_item_coins():
    cv = Canvas(16, 16)
    for cx, cy in ((5, 11), (11, 11), (8, 7)):
        cv.ellipse(cx, cy, 3.4, 2.6, "a").px(cx - 1, cy - 1, "v").hline(cx - 2, cx + 2, cy + 2, "A")
    return cv.outline()


@template("item_gem", "item", "icon", "icon", "Gem/jewel/data-chip", tags="gem jewel treasure valuable",
          colors={"glow": "#4ad0ff"})
def t_item_gem():
    cv = Canvas(16, 16).poly([(3, 6), (6, 2), (10, 2), (13, 6), (8, 14)], "g").hline(3, 12, 6, "f").px(6, 3, "f").replace("g", "G", mask=lambda x, y: x > 9)
    return cv.outline()


@template("item_food", "item", "icon", "icon", "Food/ration", tags="food ration bread meal consumable",
          colors={"wood": "#c08040"})
def t_item_food():
    cv = Canvas(16, 16).ellipse(8, 9, 6, 4, "w").hline(3, 13, 12, "W").px(5, 7, "i").px(8, 6, "i").px(11, 7, "i")
    return cv.outline()


@template("item_sword", "item", "icon", "icon", "Sword/blade icon", tags="sword blade weapon icon",
          colors={})
def t_item_sword():
    cv = Canvas(16, 16).line(4, 11, 13, 2, "n").line(5, 11, 13, 3, "m").line(2, 9, 6, 13, "a").line(2, 14, 4, 12, "w")
    return cv.outline()


@template("item_gun", "item", "icon", "icon", "Gun icon", tags="gun pistol firearm icon", colors={})
def t_item_gun():
    cv = Canvas(16, 16).rect(2, 5, 12, 3, "m").hline(2, 13, 5, "n").rect(3, 8, 3, 5, "w").px(7, 8, "M").px(8, 9, "M")
    return cv.outline()


@template("item_armor", "item", "icon", "icon", "Armour/vest icon", tags="armor armour vest icon", colors={})
def t_item_armor():
    cv = Canvas(16, 16).poly([(2, 3), (6, 2), (8, 4), (10, 2), (14, 3), (13, 14), (3, 14)], "m").vline(8, 5, 13, "M").px(4, 4, "n")
    return cv.outline()


@template("item_bag", "item", "icon", "icon", "Bag/pouch/backpack", tags="bag pouch backpack satchel", colors={"wood": "#8a5a34"})
def t_item_bag():
    cv = Canvas(16, 16).ellipse(8, 10, 5.5, 4.5, "w").rect(5, 4, 6, 3, "w").hline(5, 10, 6, "a").px(5, 9, "i")
    return cv.outline()


@template("item_tool", "item", "icon", "icon", "Tool/wrench/lockpick kit", tags="tool wrench lockpick kit gadget", colors={})
def t_item_tool():
    cv = Canvas(16, 16).line(3, 13, 10, 6, "m").line(4, 13, 11, 6, "M").ellipse(11, 5, 3, 3, "m").px(12, 4, ".").px(13, 3, ".")
    return cv.outline()


@template("item_book", "item", "icon", "icon", "Book/tome/journal", tags="book tome journal", colors={"accent": "#8a3a3a"})
def t_item_book():
    cv = Canvas(16, 16).rect(3, 2, 10, 12, "a").vline(3, 2, 13, "A").rect(5, 13, 8, 1, "y").hline(6, 10, 5, "v").hline(6, 9, 7, "v")
    return cv.outline()


@template("item_ring", "item", "icon", "icon", "Ring/amulet/trinket", tags="ring amulet trinket jewelry", colors={"accent": "#e0b040"})
def t_item_ring():
    cv = Canvas(16, 16).ellipse(8, 9, 5, 5, "a").ellipse(8, 9, 3, 3, ".").ellipse(8, 3.5, 2, 2, "g")
    return cv.outline()


# =====================================================================
#  BACKDROPS 96x54 (scene mode, 16:9)
# =====================================================================
BW, BH = 96, 54


def _sky(cv, top="P", mid="p", low="q", y_end=40):
    band = y_end / 3
    for y in range(y_end):
        c = top if y < band else (mid if y < 2 * band else low)
        for x in range(BW):
            # dither at band borders
            if abs(y - band) < 1.5 and (x + y) % 2 == 0:
                c2 = mid if y >= band else top
            elif abs(y - 2 * band) < 1.5 and (x + y) % 2 == 0:
                c2 = low if y >= 2 * band else mid
            else:
                c2 = c
            cv.px(x, y, c2)


@template("bd_outdoor", "backdrop", "backdrop", "backdrop",
          "Outdoor landscape: sky, celestial body, far hills, treeline/spires, ground. primary=sky, secondary=land, glow=sun/moon, detail=far hills",
          params={"seed": 1, "trees": "pine", "celestial": True},
          tags="outdoor landscape forest field sky wilderness", colors={"primary": "#4a6aa8", "secondary": "#3f6a3a", "glow": "#fff0b0", "detail": "#6a7aa0"})
def t_bd_outdoor(seed=1, trees="pine", celestial=True):
    rnd = random.Random(seed); cv = Canvas(BW, BH)
    _sky(cv, "P", "p", "q", 40)
    if celestial:
        cv.ellipse(72, 10, 5, 5, "g").ellipse(71, 9, 3, 3, "f")
    for x in range(BW):  # far hills
        h = 30 + int(4 * __import__("math").sin(x / 9 + seed) + 3 * __import__("math").sin(x / 4.3))
        cv.vline(x, h, 40, "d")
    for x in range(BW):
        h = 36 + int(2 * __import__("math").sin(x / 6 + seed * 2))
        cv.vline(x, h, 44, "D")
    x = 0
    while x < BW:
        th = rnd.randint(8, 16)
        if trees == "pine":
            cv.poly([(x - 4, 44), (x + 4, 44), (x, 44 - th)], "K")
        elif trees == "round":
            cv.ellipse(x, 44 - th / 2, 4, th / 2, "K")
        elif trees == "none":
            pass
        x += rnd.randint(4, 8)
    cv.rect(0, 44, BW, 10, "k").noise("k", "z", 0.06, seed=seed).noise("k", "K", 0.08, seed=seed + 1)
    return cv


@template("bd_interior", "backdrop", "backdrop", "backdrop",
          "Interior room: back wall, floor, window, torches/lights. primary=wall, wood=floor, glow=lights, secondary=window sky",
          params={"window": True, "lights": 2, "beams": True},
          tags="interior room indoor tavern hall house chamber", colors={"primary": "#5a4a48", "wood": "#6a4428", "glow": "#ffb04a", "secondary": "#2a3a6a"})
def t_bd_interior(window=True, lights=2, beams=True):
    cv = Canvas(BW, BH).rect(0, 0, BW, 40, "p")
    for y in range(0, 40, 5):
        cv.hline(0, BW - 1, y, "P")
        off = 6 if (y // 5) % 2 else 0
        for x in range(off, BW, 12):
            cv.vline(x, y, y + 4, "P")
    cv.noise("p", "q", 0.02, seed=5)
    if beams:
        cv.rect(0, 0, BW, 3, "W").rect(10, 0, 3, 40, "W").rect(83, 0, 3, 40, "W")
    if window:
        cv.rect(40, 8, 16, 16, "W").rect(42, 10, 12, 12, "k").vline(47, 10, 21, "W").hline(42, 53, 15, "W").px(44, 12, "z").px(50, 17, "g")
    for i in range(lights):
        x = 24 if i == 0 else 70
        cv.rect(x, 18, 2, 5, "w").ellipse(x + 0.5, 15.5, 1.8, 2.6, "g").px(x, 15, "f")
    cv.rect(0, 40, BW, 14, "w")
    for y in (43, 47, 51):
        cv.hline(0, BW - 1, y, "W")
    cv.hline(0, BW - 1, 40, "i")
    return cv


@template("bd_city", "backdrop", "backdrop", "backdrop",
          "City skyline/street at night: primary=sky, secondary=buildings, glow=lit windows/neon, road at bottom",
          params={"seed": 3, "neon": True}, tags="city town street urban skyline night cyberpunk",
          colors={"primary": "#1a1a3a", "secondary": "#2a2a40", "glow": "#ffd86a", "accent": "#ff3aa0"})
def t_bd_city(seed=3, neon=True):
    rnd = random.Random(seed); cv = Canvas(BW, BH)
    _sky(cv, "P", "p", "q", 44)
    for i in range(18):
        cv.px(rnd.randrange(BW), rnd.randrange(20), "y")
    x = -2
    while x < BW:  # far buildings
        w = rnd.randint(6, 12); h = rnd.randint(12, 28)
        cv.rect(x, 44 - h, w, h, "K"); x += w
    x = -3
    while x < BW:  # near buildings
        w = rnd.randint(8, 16); h = rnd.randint(8, 22)
        cv.rect(x, 44 - h, w, h, "k")
        for wy in range(44 - h + 2, 42, 3):
            for wx in range(x + 1, x + w - 1, 3):
                if rnd.random() < 0.45:
                    cv.px(wx, wy, "g")
        if neon and rnd.random() < 0.35:
            cv.rect(x + 1, 44 - h + 1, min(w - 2, 6), 2, "a")
        x += w + rnd.randint(0, 2)
    cv.rect(0, 44, BW, 10, "m").hline(0, BW - 1, 44, "n")
    for x in range(2, BW, 10):
        cv.hline(x, x + 4, 49, "d")
    return cv


@template("bd_cave", "backdrop", "backdrop", "backdrop",
          "Cave/dungeon/underground: primary=rock, glow=crystals/fungus, secondary=pool",
          params={"seed": 7, "crystals": True}, tags="cave dungeon underground cavern mine tunnel",
          colors={"primary": "#3a3444", "glow": "#5ae0c0", "secondary": "#1a2a3a"})
def t_bd_cave(seed=7, crystals=True):
    rnd = random.Random(seed); cv = Canvas(BW, BH).rect(0, 0, BW, BH, "P")
    cv.ellipse(48, 30, 44, 24, "p").ellipse(48, 32, 30, 16, "q").noise("q", "p", 0.15, seed=seed)
    for x in range(0, BW, 5):  # stalactites
        L = rnd.randint(3, 12)
        cv.poly([(x, 0), (x + 4, 0), (x + 2, L)], "P")
    for x in range(0, BW, 7):
        L = rnd.randint(3, 8)
        cv.poly([(x, BH), (x + 5, BH), (x + 2.5, BH - L)], "P")
    cv.rect(0, 46, BW, 8, "P").ellipse(60, 47, 12, 2, "k")
    if crystals:
        for _ in range(6):
            x = rnd.randrange(4, BW - 4); y = rnd.choice([44, 45, 46])
            cv.poly([(x - 2, y + 2), (x + 2, y + 2), (x, y - 5)], "g").px(x, y - 3, "f")
    cv.noise("P", "p", 0.03, seed=seed)
    return cv


@template("bd_void", "backdrop", "backdrop", "backdrop",
          "Abstract void/space/dreamscape with stars and nebula: primary=void, glow=stars, accent=nebula",
          params={"seed": 9}, tags="void space stars cosmic dream abstract astral night sky",
          colors={"primary": "#140f24", "glow": "#e8e0ff", "accent": "#6a3a8a"})
def t_bd_void(seed=9):
    rnd = random.Random(seed); cv = Canvas(BW, BH).rect(0, 0, BW, BH, "P")
    cv.ellipse(30, 20, 26, 10, "p").ellipse(66, 34, 24, 9, "p")
    cv.noise("p", "A", 0.25, seed=seed).noise("P", "p", 0.05, seed=seed + 1)
    for _ in range(60):
        cv.px(rnd.randrange(BW), rnd.randrange(BH), "g")
    for _ in range(6):
        x, y = rnd.randrange(BW), rnd.randrange(BH)
        cv.px(x, y, "f").px(x - 1, y, "G").px(x + 1, y, "G").px(x, y - 1, "G").px(x, y + 1, "G")
    return cv


@template("bd_ruins", "backdrop", "backdrop", "backdrop",
          "Ruins/temple/courtyard under open sky: primary=sky, detail=stone, secondary=ground/moss",
          params={"seed": 4}, tags="ruins temple courtyard ancient columns",
          colors={"primary": "#b0806a", "detail": "#a09a90", "secondary": "#5a6a3a", "glow": "#ffe0a0"})
def t_bd_ruins(seed=4):
    rnd = random.Random(seed); cv = Canvas(BW, BH)
    _sky(cv, "P", "p", "q", 42)
    cv.ellipse(20, 12, 4, 4, "g")
    for x in (8, 26, 62, 80):
        h = rnd.randint(18, 32)
        cv.rect(x, 44 - h, 6, h, "d").rect(x - 1, 44 - h, 8, 2, "D").vline(x + 4, 44 - h + 2, 43, "D")
    cv.rect(24, 16, 44, 4, "d").hline(24, 67, 19, "D")
    cv.rect(0, 42, BW, 12, "k").noise("k", "K", 0.12, seed=seed).noise("k", "D", 0.05, seed=seed + 2)
    return cv


@template("bd_tech", "backdrop", "backdrop", "backdrop",
          "Sci-fi/industrial interior: metal panels, pipes, screens. metal=walls, glow=lights/screens",
          params={"screens": True}, tags="scifi spaceship lab industrial facility bunker interior tech",
          colors={"metal": "#3a4250", "glow": "#3ad0ff", "accent": "#ff8a3a"})
def t_bd_tech(screens=True):
    cv = Canvas(BW, BH).rect(0, 0, BW, 42, "m")
    for x in range(0, BW, 16):
        cv.vline(x, 0, 41, "M").vline(x + 1, 0, 41, "n")
    cv.hline(0, BW - 1, 6, "M").rect(0, 3, BW, 2, "a").hline(0, BW - 1, 36, "M")
    for x in (18, 50):
        if screens:
            cv.rect(x, 12, 24, 14, "M").rect(x + 1, 13, 22, 12, "G")
            for y in (15, 18, 21):
                cv.hline(x + 3, x + 3 + (y * 7) % 16, y, "g")
    cv.rect(0, 42, BW, 12, "M")
    for x in range(0, BW, 6):
        cv.vline(x, 42, 53, "m")
    cv.hline(0, BW - 1, 42, "g")
    return cv


# =====================================================================
#  UI / STATUS ICONS 12x12 (hand-drawn grids)
# =====================================================================
ICONS = {
    "ic_heart": ({"p": "#e0304a"}, """
............
..pp....pp..
.pqpp..pppp.
.pqpppppppp.
.pppppppppp.
.ppppppppPp.
..ppppppPP..
...ppppPP...
....ppPP....
.....PP.....
............
............""", "health hp life heart resource"),
    "ic_drop": ({"p": "#3a8aff"}, """
............
.....pp.....
.....pp.....
....pppp....
...pppppp...
...pqpppp...
..pqpppppp..
..pqppppPp..
..ppppppPp..
...ppppPP...
....pPPP....
............""", "mana mp magic water drop resource"),
    "ic_bolt": ({"p": "#ffd23a"}, """
............
......ppp...
.....ppp....
....ppp.....
...pppppp...
.....ppp....
....ppp.....
...ppp......
..pp........
.p..........
............
............""", "energy stamina power lightning resource shock"),
    "ic_shield": ({"p": "#9aa4b1", "a": "#c9a24a"}, """
............
.pppppppppp.
.pqqpaapppp.
.pqppaapppP.
.pqaaaaaapP.
.pqaaaaaapP.
.ppppaapppP.
..pppaappP..
..ppppppPP..
...ppppPP...
....pPPP....
............""", "defense armor ac shield protection"),
    "ic_coin": ({"p": "#f0c040"}, """
............
....pppp....
..pqqppppp..
..pqppPPpp..
.pqppPpppPp.
.pqpppPPpPp.
.pqpppppPPp.
.ppppPPppPp.
..ppppPPpP..
..pppppPPP..
....PPPP....
............""", "gold coin money currency credits"),
    "ic_star": ({"p": "#ffe04a"}, """
............
.....pp.....
.....pp.....
....pqpp....
pppppqpppppp
.pppqppppPp.
..pppppppP..
..pppppppP..
..ppp..pppP.
.ppP....pPP.
.p........P.
............""", "xp experience level star inspired"),
    "ic_skull": ({"p": "#e8e0c8"}, """
............
...pppppp...
..pppppppp..
.pppppppppp.
.pxxpppxxpp.
.pxxpppxxpP.
.ppppxppppP.
..pppppppP..
...p.p.pP...
...pppppP...
............
............""", "death skull danger kill doom cursed"),
    "ic_eye": ({"p": "#f4f1ea", "e": "#3a6aa8"}, """
............
............
....pppp....
..pp....pp..
.p..eeee..p.
p..eexxee..p
p..eexxee..p
.p..eeee..p.
..pp....pp..
....pppp....
............
............""", "perception awareness sight watch eye wisdom"),
    "ic_eye_closed": ({"p": "#9aa4b1"}, """
............
............
............
............
p..........p
.pp......pp.
...pppppp...
..p..p..p...
.p...p...p..
............
............
............""", "hidden stealth sneak invisible hide"),
    "ic_flame": ({"p": "#ff6a1a", "q": "#ffd23a"}, """
......p.....
.....pp.....
....ppp..p..
...pppp.pp..
..ppppppppp.
..pppqqpppp.
.pppqqqqppp.
.ppqqqqqqpp.
.ppqqqqqqpp.
..ppqqqqpp..
...pppppp...
............""", "burning fire flame heat"),
    "ic_poison": ({"p": "#6ad03a"}, """
.......q....
......p.....
.....ppp.q..
....ppppp...
...ppqpppp..
...pqppppp..
..ppqppppPp.
..ppppppPPp.
..pppppPPPp.
...ppppPPp..
....ppPPp...
............""", "poisoned poison toxic venom acid sick"),
    "ic_stun": ({"p": "#ffe04a"}, """
............
..p......p..
.ppp....ppp.
..p......p..
............
.....p......
....ppp.....
.....p......
............
..p.....p...
.ppp...ppp..
..p.....p...""", "stunned dazed confused dizzy"),
    "ic_halo": ({"p": "#ffe88a"}, """
............
..pppppppp..
.pp......pp.
..pppppppp..
............
.....pp.....
....pqpp....
...pqppPp...
....pppP....
.....pP.....
............
............""", "blessed holy blessing divine protected"),
    "ic_blood": ({"p": "#c0203a"}, """
............
...p........
...p....p...
..ppp...p...
..pqp..ppp..
..ppp..pqp..
...p...ppp..
........p...
....p.......
...ppp......
...ppp......
............""", "bleeding blood wound hurt"),
    "ic_snow": ({"p": "#bfe6ff"}, """
.....pp.....
..p..pp..p..
...p.pp.p...
....pppp....
.pp.pppp.pp.
pppppqqppppp
pppppqqppppp
.pp.pppp.pp.
....pppp....
...p.pp.p...
..p..pp..p..
.....pp.....""", "frozen cold ice slowed chill"),
    "ic_sleep": ({"p": "#9ab0ff"}, """
......pppppp
..........p.
.........p..
........pppp
pppppp......
....p.......
...p........
..p.........
.pppppp.....
............
............
............""", "sleeping asleep unconscious rest"),
    "ic_fear": ({"p": "#c07aff"}, """
............
..pp....pp..
..pp....pp..
..pp....pp..
..pp....pp..
..pp....pp..
..pp....pp..
............
..pp....pp..
..pp....pp..
............
............""", "frightened fear scared panic alarm"),
    "ic_charm": ({"p": "#ff7ac0"}, """
............
............
..pp..pp....
.pqpppppp...
.pppppppp...
..pppppp..p.
...pppp..ppp
....pp..pqpp
........pppp
.........pp.
............
............""", "charmed love affection romance"),
    "ic_sweat": ({"p": "#7ad0ff"}, """
............
.pp.........
.pp..p......
pppp.p......
pqpp.pp.....
pppp.ppp....
.pp..pqp....
.....ppp....
.....pp.....
............
............
............""", "exhausted tired fatigue exhaustion"),
    "ic_chain": ({"p": "#9aa4b1"}, """
............
.ppp........
p...p.......
p...pp......
.p.p..p.....
..p..p.p....
....p.p..p..
.....p..p.p.
......pp...p
.......p...p
........ppp.
............""", "restrained grappled bound chained paralyzed"),
    "ic_arrow_down": ({"p": "#d0a070"}, """
............
....pppp....
....pppp....
....pppp....
....pppp....
.pppppppppp.
..pppppppp..
...pppppp...
....pppp....
.....pp.....
............
............""", "prone down fallen knocked"),
    "ic_hourglass": ({"p": "#d8c9a8", "g": "#ffd23a"}, """
............
.pppppppppp.
..pgggggp...
...pgggp....
....pgp.....
.....p......
....p.p.....
...p.g.p....
..p.ggg.p...
.pppppppppp.
............
............""", "time clock slowed hasted turn wait"),
    "ic_brain": ({"p": "#e89ab0"}, """
............
...pp.pp....
..pqpppqpp..
.pqpppppppp.
.pppppqpppp.
.pqpppppppP.
.pppppppPPp.
..pppppPPp..
....ppp.....
.....pp.....
............
............""", "sanity mind intelligence psyche will"),
    "ic_fist": ({"p": "#e0a878"}, """
............
..pppppppp..
.pqqpqpqpqp.
.pqppppppppp
.ppppppppppp
.ppppppppPpp
.pppppppPPp.
..pppppPPp..
...ppppPp...
...ppppPp...
............
............""", "strength might power fist brawn"),
    "ic_feather": ({"p": "#e8e0d0"}, """
..........pp
........pppp
.......ppqp.
......ppqp..
.....ppqpp..
....ppqpp...
...ppqpp....
..ppqpp.....
..pqpp......
..q.........
.q..........
q...........""", "dexterity agility reflex speed feather"),
    "ic_mask": ({"p": "#e0c070"}, """
............
.pppppppppp.
.pppppppppp.
.pxxpppxxpp.
.pxxpppxxpp.
.pppppppppp.
.ppppppppPp.
..pp.pp.pP..
...pppppP...
....pppP....
............
............""", "charisma presence charm deception social mask"),
    "ic_scroll": ({"p": "#e8dcb8"}, """
............
.PPPPPPPPPP.
..pppppppp..
..pxxxxxpp..
..pppppppp..
..pxxxxpp...
..pppppppp..
..pxxxxxpp..
..pppppppp..
.PPPPPPPPPP.
............
............""", "quest journal note log scroll lore"),
    "ic_bag": ({"p": "#9a6a3a"}, """
............
....pppp....
...p....p...
..pppppppp..
.pppqqppppp.
.ppqppppppp.
.ppqpppppPp.
.pppppppPPp.
.ppppppPPPp.
..pppppPPp..
............
............""", "inventory bag items backpack"),
    "ic_map": ({"p": "#d8c9a8", "a": "#c0304a"}, """
............
.ppp.ppp.pp.
.ppPppp.pPp.
.pPpppPpppp.
.pppPppppap.
.ppppPPpaap.
.pppppPpppp.
.ppPPpppPpp.
.pppppPpppp.
.ppp.ppp.pp.
............
............""", "map location explore travel"),
    "ic_pin": ({"p": "#e0304a"}, """
............
....pppp....
...pppppp...
..ppqqpppp..
..pqppyppp..
..pppyyppp..
...pppppp...
....pppp....
.....pp.....
.....p......
............
............""", "marker pin location objective waypoint"),
    "ic_dice": ({"p": "#f4f1ea", "e": "#1a1523"}, """
............
.pppppppppp.
.peppppppep.
.pppppppppp.
.pppppppppp.
.ppppeppppp.
.pppppppppp.
.pppppppppp.
.peppppppep.
.pppppppppp.
............
............""", "dice roll luck random chance"),
    "ic_sun": ({"p": "#ffd23a"}, """
.....p......
.p...p...p..
..p.....p...
....ppp.....
...ppppp....
ppppqpppp.pp
...ppppp....
....ppp.....
..p.....p...
.p...p...p..
.....p......
............""", "day sun daytime noon light"),
    "ic_moon": ({"p": "#e8e0c0"}, """
............
....ppp.....
...pp.......
..pp........
..pp........
..pp........
..ppp.......
...pppp..p..
....ppppp...
............
............
............""", "night moon dark evening"),
    "ic_rain": ({"p": "#9ab0c8", "g": "#5a9aff"}, """
............
...pppp.....
..pppppppp..
.pppppppppp.
.pppppppppp.
............
..g..g..g...
.g..g..g....
............
...g..g..g..
..g..g..g...
............""", "rain weather storm wet"),
    "ic_swords": ({"m": "#c8d0da"}, """
............
p..........p
.p........p.
..p......p..
...p....p...
....p..p....
.....pp.....
....p..p....
..wp....pw..
.ww......ww.
w..........w
............""", "combat fight battle encounter attack"),
    "ic_bang": ({"p": "#ffd23a"}, """
............
.....pp.....
.....pp.....
.....pp.....
.....pp.....
.....pp.....
.....pp.....
............
.....pp.....
.....pp.....
............
............""", "alert important quest new objective"),
    "ic_gear": ({"p": "#9aa4b1"}, """
............
....p..p....
..pppppppp..
..pp....pp..
.pp......pp.
..p..pp..p..
..p..pp..p..
.pp......pp.
..pp....pp..
..pppppppp..
....p..p....
............""", "settings tech gear machine battery integrity system"),
    "ic_music": ({"p": "#c0a0ff"}, """
............
.....ppppp..
.....p...p..
.....p...p..
.....p...p..
.....p...p..
...ppp.ppp..
..pppp.ppp..
..ppp..pp...
............
............
............""", "inspired song music bard morale"),
    "ic_run": ({"p": "#7ad08a"}, """
............
......pp....
......pp....
....pppp....
...p.ppp.p..
..p..pp.....
.....ppp....
....p..p....
...p....p...
..p.....p...
............
............""", "hasted speed fast movement run"),
}


def _make_icon(rows):
    def fn():
        cv = Canvas.from_rows([r for r in rows.strip("\n").split("\n")])
        # 12x12 art centred on 14x14 canvas for outline room
        out = Canvas(14, 14).paste(cv, 1, 1)
        return out.outline()
    return fn


from .pixel import STD_LEGEND as _SL
for _name, (_cols, _rows, _tags) in ICONS.items():
    _c = {_SL.get(k, k): v for k, v in _cols.items()}
    template(_name, "icon", "icon", "icon", f"UI icon: {_tags.split()[0]}", tags=_tags, colors=_c)(_make_icon(_rows))
