"""Dice expressions: '1d20+5', '2d6+1d4-1', '4d6kh3', 'd100', '3d6!'(exploding)."""
from __future__ import annotations
import re, secrets

TERM = re.compile(r"([+-]?)\s*(?:(\d*)d(\d+)(?:(kh|kl)(\d+))?(!)?|(\d+))", re.I)


def _d(n):
    return secrets.randbelow(n) + 1


def roll(expr: str, mode: str | None = None):
    expr = (expr or "1d20").replace(" ", "").lower()
    total, parts, d20_nat = 0, [], None
    pos = 0
    for m in TERM.finditer(expr):
        if m.start() != pos:
            raise ValueError(f"bad dice expression near '{expr[pos:]}'")
        pos = m.end()
        sign = -1 if m.group(1) == "-" else 1
        if m.group(7):
            v = int(m.group(7)); total += sign * v
            parts.append({"mod": sign * v})
            continue
        n = int(m.group(2) or 1); sides = int(m.group(3))
        if n > 100 or sides > 1000:
            raise ValueError("too many dice")
        adv = None
        if sides == 20 and n == 1 and mode in ("adv", "advantage", "dis", "disadvantage"):
            a, b = _d(20), _d(20)
            adv = [a, b]
            rolls = [max(a, b) if mode.startswith("adv") else min(a, b)]
        else:
            rolls = []
            for _ in range(n):
                r = _d(sides); rolls.append(r)
                while m.group(6) and r == sides and len(rolls) < 50:
                    r = _d(sides); rolls.append(r)
        kept = list(rolls)
        if m.group(4):
            k = int(m.group(5)); kept = sorted(rolls, reverse=(m.group(4) == "kh"))[:k]
        sub = sum(kept) * sign; total += sub
        part = {"dice": f"{n}d{sides}", "rolls": rolls, "kept": kept, "sign": sign}
        if adv:
            part["adv_pair"] = adv
        if sides == 20 and n == 1 and d20_nat is None:
            d20_nat = kept[0]
        parts.append(part)
    if pos != len(expr):
        raise ValueError(f"bad dice expression near '{expr[pos:]}'")
    return {"expr": expr, "total": total, "parts": parts, "nat": d20_nat,
            "crit": d20_nat == 20, "fumble": d20_nat == 1}
