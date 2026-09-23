"""Письмо-возражение → кандидаты доводов по каталогу objections.json (ключевые слова)."""
from __future__ import annotations

import re

PATTERNS = {
    "not_podryad": r"поставк|оказани\w+ услуг|аренд|не является договором подряда|купли[- ]продажи",
    "not_capital_object": r"некапитальн|не является объектом капитального|разрешени\w+ на строительство не требу|временн\w+ (?:сооружени|постройк)|текущ\w+ ремонт|благоустройств",
    "customer_not_developer": r"субподряд|генеральн\w+ подрядчик|генподрядчик|заказчик не является застройщиком|не застройщик",
    "below_threshold": r"(?:менее|ниже|не превышает)\s+(?:10|десяти)\s*(?:млн|миллион)|ниже порога|3\s*(?:млн|миллион)",
    "not_competitive": r"без (?:проведения )?торгов|без конкурентн|прям\w+ договор|единственн\w+ поставщик|не по 44|не по 223|коммерческ\w+ (?:закупк|тендер)",
    "executed": r"исполнен\w* (?:в полном объ[её]ме|полностью)|работы (?:выполнены|приняты|завершены)|итогов\w+ акт|акт\w* (?:приемки|приёмки)|обязательства (?:исполнены|прекращены)",
    "terminated": r"расторгнут|расторжени|отказ\w* от исполнения",
    "works_not_in_list": r"не влия\w+ на безопасность|не входят в перечень|перечн\w+ (?:624|видов работ)|не требу\w+ допуск",
    "state_exempt": r"учреждени|унитарн\w+ предприяти|ГУП|МУП|государственн\w+ (?:предприяти|компани)|исключени\w+ ч\.?\s*2\.2",
    "individual_housing": r"индивидуальн\w+ жилищн|ИЖС|садов\w+ дом|вспомогательн\w+ (?:использовани|постройк)|блокированн",
    "design_threshold": r"проектн\w+ работ\w* .{0,60}(?:млн|порог)|изыскани\w* .{0,60}(?:млн|порог)",
    "technical_customer_is_intermediary": r"техническ\w+ заказчик",
    "before_2026": r"до 1 марта 2026|до 01\.03\.2026|заключ[её]н (?:в|до) 202[0-5]",
    "price_includes_supply": r"оборудовани\w* .{0,80}(?:исключить|не включ|вычесть)|стоимость материалов|поставк\w+ оборудования",
    "not_member_at_signing": r"не (?:являлись|были) членом|вступил\w* в СРО (?:после|позже)|на момент (?:заключения|подписания) .{0,60}не (?:состоял|являл)",
}


def split_units(text: str) -> list[str]:
    """Письмо → предложения (доводы обычно идут по одному на предложение)."""
    text = re.sub(r"\r", "", text)
    out = []
    for p in re.split(r"\n\s*\n|\n(?=\s*(?:\d+[.)]|[-–•]))", text):
        p = re.sub(r"\s+", " ", p).strip()
        if not p:
            continue
        out.extend(s.strip() for s in re.split(r"(?<=[.!?;])\s+(?=[А-ЯA-Z«\d(])", p) if s.strip())
    return out


def detect_claims(text: str) -> list[dict]:
    """→ [{type, quote, score}]: лучший тип на предложение; соседние предложения одного типа склеиваются."""
    out = []
    for unit in split_units(text):
        low = unit.lower()
        best, best_n = None, 0
        for typ, pat in PATTERNS.items():
            n = len(re.findall(pat, low, re.I))
            if n > best_n:
                best, best_n = typ, n
        if not best:
            continue
        if out and out[-1]["type"] == best and len(out[-1]["quote"]) + len(unit) < 600:
            out[-1]["quote"] += " " + unit
            out[-1]["score"] += best_n
        else:
            out.append({"type": best, "quote": unit[:500], "score": best_n})
    return out


def letter_meta(text: str) -> dict:
    d = re.search(r"(\d{2}\.\d{2}\.\d{4})", text[:1500])
    n = re.search(r"(?:исх\.?|№)\s*([\w\-/]+)", text[:1500])
    frm = re.search(r"(ООО|АО|ПАО|ИП)\s*[«\"][^»\"]+[»\"]", text[:3000])
    cn = re.search(r"(?:контракт|договор)\w*\s*№\s*([^\s,;)]+)", text, re.I)
    return {"date": _iso(d.group(1)) if d else None, "number": n.group(1) if n else None,
            "from": frm.group(0) if frm else "", "contract_number": cn.group(1) if cn else None}


def _iso(s):
    m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", s)
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None
