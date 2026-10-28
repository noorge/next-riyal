"""Parsers for Ehsan listing and detail pages (server-rendered HTML)."""
import re
from bs4 import BeautifulSoup

AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def _num(text):
    """'84,498 ﷼' / '40 مستفيد' / '٧٬٢٣٥' -> float, or None."""
    if text is None:
        return None
    t = str(text).translate(AR_DIGITS).replace(",", "").replace("٬", "")
    m = re.search(r"-?\d+(?:\.\d+)?", t)
    return float(m.group()) if m else None


def _clean(text):
    return re.sub(r"\s+", " ", text).strip() if text else None


HIJRI_MONTHS = {
    "محرم": 1, "صفر": 2, "ربيع الأول": 3, "ربيع الآخر": 4, "ربيع الثاني": 4,
    "جمادى الأولى": 5, "جمادى الأول": 5, "جمادى الآخرة": 6, "جمادى الثانية": 6,
    "رجب": 7, "شعبان": 8, "رمضان": 9, "شوال": 10, "ذو القعدة": 11, "ذو الحجة": 12,
}


def hijri_to_iso(text):
    """'12/جمادى الأولى/1448' -> '2026-10-23' (None if it can't be read)."""
    from hijridate import Hijri
    if not text:
        return None
    parts = [p.strip() for p in text.translate(AR_DIGITS).replace("‏", "").split("/")]
    if len(parts) != 3:
        return None
    day, month, year = parts
    m = HIJRI_MONTHS.get(month) or (int(month) if month.isdigit() else None)
    try:
        return Hijri(int(year), m, int(day)).to_gregorian().isoformat()
    except (TypeError, ValueError):
        return None


def parse_listing(html):
    """Return one dict per opportunity card on a listing page.

    Cards are found by their share button, which both active and completed
    cards have; amounts are read only when the card shows them.
    """
    soup = BeautifulSoup(html, "lxml")
    rows, seen = [], set()
    for share in soup.select("button.share-opportunity[data-caseid]"):
        case_id = int(share["data-caseid"])
        if case_id in seen:
            continue
        seen.add(case_id)
        card = share.find_parent("div", class_="card") or share.parent
        btn = card.select_one("button.add-to-cart")
        link = card.select_one("a.card-title") or card.select_one("a[href]")
        bar = card.select_one(".progress-bar")
        remaining = card.select_one("[data-card-value]")
        collected = None
        for lab in card.select("label"):
            if "تم جمع" in lab.get_text():
                sib = lab.find_next_sibling("span")
                collected = _num(sib.get_text()) if sib else None
        rows.append({
            "case_id": case_id,
            "type": share.get("data-casetype"),
            "title_ar": (btn.get("data-titlear") if btn else None) or share.get("data-casetitle"),
            "title_en": btn.get("data-titleen") if btn else None,
            "url": (btn.get("data-url") if btn else None) or (link["href"] if link else None),
            "progress_pct": _num(bar.get("aria-valuenow")) if bar else None,
            "collected": collected,
            "remaining": _num(remaining["data-card-value"]) if remaining else None,
        })
    return rows


LABEL_FIELDS = {
    "تم جمع": "collected",
    "المبلغ المتبقي": "remaining",
    "عدد المستفيدين": "beneficiaries_target",
    "نوع المستفيدين": "beneficiary_type",
    "المدينة": "city",
    "المنطقة": "region",
}
TEXT_FIELDS = ("beneficiary_type", "city", "region")


def _label_fields(soup, out):
    """Label/value pairs: <span>label</span><label>value</label>."""
    for span in soup.select("span"):
        key = _clean(span.get_text())
        if key in LABEL_FIELDS and LABEL_FIELDS[key] not in out:
            val = span.find_next_sibling("label")
            if val is not None:
                txt = _clean(val.get_text())
                field = LABEL_FIELDS[key]
                out[field] = txt if field in TEXT_FIELDS else _num(txt)


def _partner(soup, out):
    partner = soup.select_one('a[href*="partnerprofile?organizationId="]')
    if partner:
        out["partner_id"] = int(re.search(r"organizationId=(\d+)", partner["href"]).group(1))
        name = partner.find_parent("div").select_one("p")
        out["partner_name"] = _clean(name.get_text()) if name else None


def parse_org_details(html):
    """Fragment the detail page loads by JS (POST Projects/OrganizationDetails/<id>):
    beneficiaries target, beneficiary type, city and implementing partner."""
    soup = BeautifulSoup(html, "lxml")
    out = {}
    _label_fields(soup, out)
    _partner(soup, out)
    return out


def _greg(text):
    """'11‏/10‏/2026 م' -> '2026-10-11'."""
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", (text or "").translate(AR_DIGITS).replace("‏", ""))
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def parse_report(html):
    """Completed-opportunity report (/CompletedInitiatives/Report?projectId=<id>).

    Three header/value tables: region/city, association, case ref, type;
    beneficiary type, count, publish date, completion date; total amount.
    """
    soup = BeautifulSoup(html, "lxml")
    cells = {}
    for table in soup.select("table"):
        heads = [_clean(th.get_text()) for th in table.select("thead th")]
        row = table.select_one("tbody tr")
        if row is None:
            continue
        for head, td in zip(heads, row.select("td")):
            cells[head] = td
    if not cells:
        return _parse_impact_report(soup)

    def text(head):
        td = cells.get(head)
        return _clean(td.get_text(" ")) if td is not None else None

    region = city = None
    loc = cells.get("المنطقة/ المدينة")
    if loc is not None:
        reg = loc.select_one("span")
        region = _clean(reg.get_text()).rstrip("/ ").strip() if reg else None
        if reg:
            reg.extract()
        city = _clean(loc.get_text()) or None
    else:
        city = text("المدينة")   # housing reports: city only
    return {
        "region": region,
        "city": city,
        "partner_name": text("الجهة"),
        "case_ref": text("رقم الفرصة"),
        "opportunity_type": text("نوع الفرصة"),
        "beneficiary_type": text("نوع المستفيد"),
        "beneficiaries": _num(text("عدد المستفيدين")),
        "publish_date": _greg(text("تاريخ نشر الفرصة")),
        "completed_date": _greg(text("تاريخ اكتمال الفرصة")),
        "total": _num(text("المبلغ الإجمالي")),
    }


def _parse_impact_report(soup):
    """Second report layout ("تقرير الأثر"): label/label pairs plus the publish
    date in the header. Has the partner's license number but no region or
    beneficiary type."""
    pairs = {}
    for box in soup.select("div.d-flex.flex-column"):
        labels = box.find_all("label", recursive=False)
        if len(labels) == 2:
            pairs[_clean(labels[0].get_text())] = _clean(labels[1].get_text(" "))
    publish = None
    head = soup.find("label", string=re.compile("تاريخ نشر الفرصة"))
    if head is not None and head.find_next_sibling("div") is not None:
        publish = _greg(head.find_next_sibling("div").get_text())
    if not pairs and publish is None:
        return {}
    return {
        "city": pairs.get("المدينة"),
        "partner_name": pairs.get("الشريك المنفذ"),
        "partner_license": pairs.get("رقم الترخيص"),
        "beneficiaries": _num(pairs.get("عدد المستفيدين")),
        "publish_date": publish,
        "completed_date": _greg(pairs.get("تاريخ اكتمال المشروع") or pairs.get("تاريخ اكتمال الفرصة")),
        "total": _num(pairs.get("المبلغ الإجمالي")),
        "report_layout": "impact",
    }


AGE_WORDS = {"سنة واحدة": 1, "عام واحد": 1, "سنتان": 2, "سنتين": 2, "عامان": 2, "عامين": 2}


def _age_years(title):
    """'أهلاً، أنا ريفان وعمري 14 سنة' -> 14.0. Months are converted to years.
    Only the number is kept; the name in the title is never stored."""
    t = (title or "").translate(AR_DIGITS)
    m = re.search(r"عمري\s*(\d+(?:\.\d+)?)\s*(أشهر|شهور|شهر|سنوات|سنة|أعوام|عام)?", t)
    if m:
        n = float(m.group(1))
        return round(n / 12, 2) if m.group(2) in ("أشهر", "شهور", "شهر") else n
    for word, n in AGE_WORDS.items():
        if re.search(r"عمري\s*" + word, t):
            return float(n)
    return None


def parse_orphan_cards(html):
    """Completed orphan-sponsorship cards (/completedinitiatives/orphans).

    Keeps only case id/ref, monthly sponsorship cost, completion date and age.
    Cards carry no region, city or association.
    """
    soup = BeautifulSoup(html, "lxml")
    rows, seen = [], set()
    for share in soup.select("button.share-opportunity[data-caseid]"):
        case_id = int(share["data-caseid"])
        if case_id in seen:
            continue
        seen.add(case_id)
        card = share.find_parent("div", class_="card") or share.parent
        pairs = {}
        for lab in card.select("label"):
            val = lab.find_next_sibling("span")
            if val is not None:
                pairs[_clean(lab.get_text())] = _clean(val.get_text())
        cost = card.find(string=re.compile("تكلفة الكفالة"))
        rows.append({
            "case_id": case_id,
            "case_ref": pairs.get("رقم الحالة"),
            "monthly_cost": _num(cost) if cost else None,
            "completed_date": _greg(pairs.get("تاريخ الاكتمال")),
            "age_years": _age_years(share.get("data-casetitle")),
        })
    return rows


def parse_detail(html):
    """Return the fields shown on an opportunity's detail page."""
    soup = BeautifulSoup(html, "lxml")
    out = {}

    case_input = soup.select_one('input[name="CartItems[0].caseId"]')
    out["case_id"] = int(case_input["value"]) if case_input else None
    main = soup.select_one("#maincontent")
    if main is not None:
        if out["case_id"] is None and main.get("data-case-id"):
            out["case_id"] = int(main["data-case-id"])
        out["initiative_type"] = main.get("data-initiative-type")
        out["case_url"] = main.get("data-case-url")
    # Only pages with this placeholder load the OrganizationDetails fragment.
    out["has_more_details"] = soup.select_one("#moreDetails") is not None

    ref = soup.find(string=re.compile("رقم الحالة"))
    out["case_ref"] = _clean(ref.find_parent("span").find_next_sibling("span").get_text()) if ref else None

    # Original target lives on the detail-page cart button (data-maxamount),
    # while the card's data-maxamount is the remaining balance.
    btn = soup.select_one("form#details_donation button.add-to-cart")
    out["target"] = _num(btn.get("data-maxamount")) if btn else None
    bar = soup.select_one(".progress-bar")
    out["progress_pct"] = _num(bar.get("aria-valuenow")) if bar else None

    _label_fields(soup, out)

    # Completed pages have no cart button, so fall back to collected + remaining.
    if out.get("target") is None and out.get("collected") is not None:
        out["target"] = out["collected"] + (out.get("remaining") or 0)
    out["is_completed"] = soup.select_one('img[src*="complete-case-badge"]') is not None

    desc = soup.select_one("div.min-h-72px.mt-3.px-3")
    out["description"] = _clean(desc.get_text()) if desc else None

    _partner(soup, out)

    # Statistic boxes at the bottom of the page
    for box in soup.select("div.card.flex-row"):
        label = box.select_one("span.text-sm-medium")
        if not label:
            continue
        key = _clean(label.get_text())
        value = box.select_one(".text-xl-bold")
        if key == "الزيارات":
            out["visits"] = _num(value.get_text())
        elif key == "عدد عمليات التبرع":
            out["donation_count"] = _num(value.get_text())
        elif key == "عدد المستفيدين":
            out["beneficiaries_served"] = _num(value.get_text())
        elif key == "تاريخ اكتمال الفرصة":
            out["completed_hijri"] = _clean(value.get_text().replace("‏", ""))
            out["completed_date"] = hijri_to_iso(out["completed_hijri"])
        elif key.startswith("آخر عملية تبرع"):
            num = value.select_one("span")
            unit = value.select_one("small")
            out["last_donation_ago"] = " ".join(
                _clean(x.get_text()) for x in (num, unit) if x is not None
            ) or None
    return out
