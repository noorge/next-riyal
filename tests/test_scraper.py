import hashlib
import json
from pathlib import Path

from scraper.crawl import Fetcher, case_details, crawl_listing
from scraper.parse import parse_detail, parse_listing, parse_org_details, parse_report

# Fixtures are raw server responses (what requests receives), not the
# browser's rendered DOM: city/partner/visits are filled in later by JS.
FIX = Path(__file__).parent / "fixtures"
CARD = (FIX / "card.html").read_text(encoding="utf-8")
DETAIL = (FIX / "detail_raw.html").read_text(encoding="utf-8")
DETAIL_DONE = (FIX / "detail_completed_raw.html").read_text(encoding="utf-8")
ORG = (FIX / "org_details.html").read_text(encoding="utf-8")
REPORT = (FIX / "report.html").read_text(encoding="utf-8")


def test_listing_card():
    (row,) = parse_listing(CARD)
    assert row["case_id"] == 82987
    assert row["collected"] == 83825 and row["remaining"] == 196175
    assert row["progress_pct"] == 30


def test_detail_fields_and_consistency():
    d = parse_detail(DETAIL)
    assert d["case_id"] == 82987 and d["case_ref"] == "P83986"
    assert d["initiative_type"] == "Project"
    assert d["case_url"] == "Projects/OrganizationDetails/82987"
    assert d["donation_count"] == 7608 and d["beneficiaries_served"] == 12
    # collected + remaining must equal the original target
    assert d["collected"] + d["remaining"] == d["target"] == 280000
    assert d["is_completed"] is False
    # not in the raw HTML; comes from the OrganizationDetails fragment
    assert "city" not in d


def test_org_details_fragment():
    o = parse_org_details(ORG)
    assert o["city"] == "أملج" and o["beneficiary_type"] == "المواطنون"
    assert o["beneficiaries_target"] == 40
    assert o["partner_id"] == 5247 and o["partner_name"] == "التنمية بسمر الأهلية"


def test_report():
    r = parse_report(REPORT)
    assert r["region"] == "منطقة مكة المكرمة" and r["city"] == "القنفذه"
    assert r["partner_name"] == "جمعية منتجون للأسر المنتجة بمحافظة القنفذة"
    assert r["case_ref"] == "P83989" and r["beneficiary_type"] == "المواطنون"
    assert r["beneficiaries"] == 6 and r["total"] == 150000
    assert r["publish_date"] == "2026-10-11" and r["completed_date"] == "2026-10-23"


def test_report_error_page_is_empty():
    assert parse_report("<html><body>خطأ غير متوقع</body></html>") == {}


def _seed(cache, key, html):
    f = cache / "html" / (hashlib.md5(key.encode()).hexdigest() + ".html")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(html, encoding="utf-8")


def test_pagination_stops_on_repeat(tmp_path):
    # page 1 has the card, page 2 repeats it -> crawler must stop
    _seed(tmp_path, "/projects?projectType=Social&p=1", CARD)
    _seed(tmp_path, "/projects?projectType=Social&p=2", CARD)
    f = Fetcher(tmp_path, offline=True)
    rows = crawl_listing(f, "/projects?projectType=Social", "Social", 10)
    assert len(rows) == 1 and rows[0]["category"] == "Social"


def test_case_details_active(tmp_path):
    url = "/projects/0/82987?amount=null"
    _seed(tmp_path, url, DETAIL)
    post = "POST /projects/0/Projects/OrganizationDetails/82987 " + json.dumps({"id": "82987"})
    _seed(tmp_path, post, ORG)
    _seed(tmp_path, "/visit-count/Project/82987", "6666")
    d = case_details(Fetcher(tmp_path, offline=True),
                     {"case_id": 82987, "url": url, "category": "Social"})
    assert d["city"] == "أملج" and d["partner_id"] == 5247
    assert d["visits"] == 6666 and d["target"] == 280000


def test_case_details_completed_uses_report(tmp_path):
    _seed(tmp_path, "/CompletedInitiatives/Report?projectId=82990", REPORT)
    _seed(tmp_path, "/visit-count/Project/82990", "9640")
    d = case_details(Fetcher(tmp_path, offline=True),
                     {"case_id": 82990, "url": "/projects/0/82990?amount=null", "category": "Completed"})
    assert d["region"] == "منطقة مكة المكرمة" and d["publish_date"] == "2026-10-11"
    assert d["visits"] == 9640


def test_completed_card_found_without_cart_button():
    (row,) = parse_listing((FIX / "card_completed.html").read_text(encoding="utf-8"))
    assert row["case_id"] == 82990
    assert row["url"] == "/projects/0/82990?amount=null"
    assert row["title_ar"] == "عربات بيع الطعام للأسر المتعففة"


def test_completed_detail():
    d = parse_detail(DETAIL_DONE)
    assert d["case_id"] == 82990 and d["is_completed"] is True
    assert d["target"] == 150000 and d["remaining"] == 0
    assert d["completed_date"] == "2026-10-23"
    assert d["donation_count"] == 11202 and d["beneficiaries_served"] == 6


def test_impact_report_layout():
    r = parse_report((FIX / "report_impact.html").read_text(encoding="utf-8"))
    assert r["report_layout"] == "impact"
    assert r["city"] == "الحائط" and r["partner_name"] == "جمعية البر الخيرية بالوسعة"
    assert r["partner_license"] == "740" and r["beneficiaries"] == 2 and r["total"] == 30000
    assert r["publish_date"] == "2026-09-13" and r["completed_date"] == "2026-09-14"


def test_mosque_and_housing_reports():
    m = parse_report((FIX / "report_mosque.html").read_text(encoding="utf-8"))
    assert m["region"] == "منطقة الرياض" and m["city"] == "السليل"
    assert m["opportunity_type"] == "العناية بالمساجد" and m["total"] == 140792
    assert m["publish_date"] == "2026-10-04" and m["completed_date"] == "2026-10-22"
    h = parse_report((FIX / "report_housing.html").read_text(encoding="utf-8"))
    assert h["region"] is None and h["city"] == "مكة المكرمة"
    assert h["opportunity_type"] == "تملك المسكن" and h["publish_date"] == "2026-10-18"


def test_orphan_card():
    from scraper.parse import parse_orphan_cards
    (row,) = parse_orphan_cards((FIX / "card_orphan.html").read_text(encoding="utf-8"))
    assert row == {"case_id": 215801, "case_ref": "W-215801", "monthly_cost": 400,
                   "completed_date": "2026-10-23", "age_years": 14}
    assert "فلانة" not in str(row)   # the name is never kept


def test_orphan_age_formats():
    from scraper.parse import _age_years
    assert _age_years("أهلاً، أنا فلان وعمري ٧ سنوات") == 7
    assert _age_years("أنا فلان وعمري 6 أشهر") == 0.5
    assert _age_years("أنا فلان وعمري سنتان") == 2
    assert _age_years("كفالة يتيم") is None


def test_cache_is_gzipped_and_readable(tmp_path):
    import gzip
    f = Fetcher(tmp_path, offline=True)
    gz = f.cache / (hashlib.md5(b"/x").hexdigest() + ".html.gz")
    gz.write_bytes(gzip.compress("صفحة".encode()))
    assert f.get("/x") == "صفحة"


def test_orphan_archive_continues_past_repeated_page(tmp_path):
    from scraper.crawl import crawl_orphan_archive
    card = (FIX / "card_orphan.html").read_text(encoding="utf-8")
    other = card.replace("215801", "215802")
    _seed(tmp_path, "/completedinitiatives/orphans?p=1", card)
    _seed(tmp_path, "/completedinitiatives/orphans?p=2", card)    # shifted, all seen
    _seed(tmp_path, "/completedinitiatives/orphans?p=3", other)
    _seed(tmp_path, "/completedinitiatives/orphans?p=4", "<html></html>")
    rows = crawl_orphan_archive(Fetcher(tmp_path, offline=True), 10)
    assert [r["case_id"] for r in rows] == [215801, 215802]


def test_orphan_cards_in_projects_listing_are_skipped_without_ending_the_list(tmp_path):
    project = (FIX / "card_completed.html").read_text(encoding="utf-8")
    orphan = project.replace("عربات بيع الطعام للأسر المتعففة", "أهلاً، أنا فلان وعمري 12 سنة")                     .replace("82990", "70001")
    _seed(tmp_path, "/completed?initiativeType=CompletedProject&p=1", orphan)   # a page of only orphan cards
    _seed(tmp_path, "/completed?initiativeType=CompletedProject&p=2", project)
    rows = crawl_listing(Fetcher(tmp_path, offline=True),
                         "/completed?initiativeType=CompletedProject", "Completed", 5)
    assert [r["case_id"] for r in rows] == [82990]
