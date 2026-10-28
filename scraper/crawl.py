"""Polite crawler for Ehsan donation opportunities.

Usage:
    python -m scraper.crawl                    # full crawl, today's snapshot
    python -m scraper.crawl --sections projects --max-pages 2   # quick test
    python -m scraper.crawl --offline          # re-parse cached HTML only

Raw HTML is cached under data_raw/<snapshot-date>/ so every run can be
reproduced from disk, and an interrupted crawl resumes where it stopped.
Output: data_raw/<date>/opportunities.csv

Per case:
  active     detail page + OrganizationDetails fragment (city, beneficiaries,
             partner; loaded by JS on the site) + visit count
  completed  report page (region/city, partner, beneficiaries, publish and
             completion dates, total) + visit count; detail page only with
             --completed-details
"""
import argparse
import gzip
import hashlib
import json
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests

from scraper.parse import (parse_detail, parse_listing, parse_org_details,
                           parse_orphan_cards, parse_report, _num)

BASE = "https://ehsan.sa"
HEADERS = {"User-Agent": "Mozilla/5.0 (research; nonprofit data hackathon)"}

# Each listing source and the category tag its rows get.
PROJECT_TYPES = ["Education", "Feeding", "Housing", "Health",
                 "Religious", "Social", "Environmental", "Technical"]
SECTIONS = {
    "projects": [(f"/projects?projectType={t}", t) for t in PROJECT_TYPES],
    "housing": [("/housing", "HousingPlatform")],
    "orphans": [("/orphans", "Orphans")],
    "mosques": [("/mosques", "Mosques")],
    "completed": [("/completed?initiativeType=CompletedProject", "Completed")],
    "completed_mosques": [("/completedinitiatives/mosques", "CompletedMosques")],
    "completed_housing": [("/completedinitiatives/housing", "CompletedHousing")],
    # International relief (wells etc.), outside the Saudi regional analysis.
    "rescue": [("/completed?initiativeType=CompletedRescue", "CompletedRescue")],
}
# Orphan sponsorship and international relief are out of scope (see README).
DEFAULT_SECTIONS = [s for s in SECTIONS if s not in ("rescue", "orphans")]
# Completed archives and their report page. Completed orphans (~198k individual
# children) and tyassarat (individual debtors) are deliberately not crawled.
REPORTS = {
    "Completed": "/CompletedInitiatives/Report?projectId={}",
    "CompletedRescue": "/CompletedInitiatives/Report?projectId={}",
    "CompletedMosques": "/CompletedInitiatives/MosqueReport?id={}",
    "CompletedHousing": "/CompletedInitiatives/HousingReport?housingId={}",
}
COMPLETED = set(REPORTS)
# Individual family/child cases: titles and descriptions describe a person
# (name, age, family circumstances), so they are not stored.
PERSONAL = {"HousingPlatform", "Orphans", "CompletedHousing"}
ORPHAN_CARD = r"وعمري\s*\S+"


class Fetcher:
    def __init__(self, cache_dir, delay=1.5, offline=False, retries=3):
        self.cache = Path(cache_dir) / "html"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.delay, self.offline, self.retries = delay, offline, retries
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def get(self, path, post=None):
        """Cached GET (or JSON POST when `post` is given). Returns None on
        HTTP errors, which are not cached so a later run can retry them."""
        key = path if post is None else "POST " + path + " " + json.dumps(post, sort_keys=True)
        f = self.cache / (hashlib.md5(key.encode()).hexdigest() + ".html")
        gz = f.with_suffix(".html.gz")
        if f.exists():
            return f.read_text(encoding="utf-8")
        if gz.exists():
            return gzip.decompress(gz.read_bytes()).decode("utf-8")
        if self.offline:
            return None
        for attempt in range(self.retries):
            time.sleep(self.delay * (1 + 2 * attempt))
            try:
                if post is None:
                    r = self.session.get(BASE + path, timeout=30)
                else:
                    r = self.session.post(BASE + path, json=post, timeout=30)
            except requests.RequestException as e:
                print(f"  ! {path}: {e.__class__.__name__}, retry {attempt + 1}")
                continue
            if not r.ok:
                print(f"  ! {path}: HTTP {r.status_code}")
                return None
            gz.write_bytes(gzip.compress(r.text.encode("utf-8")))
            return r.text
        return None


def crawl_listing(fetcher, path, category, max_pages):
    rows, seen = [], set()
    sep = "&" if "?" in path else "?"
    for p in range(1, max_pages + 1):
        html = fetcher.get(f"{path}{sep}p={p}")
        if html is None:
            break
        cards = [c for c in parse_listing(html) if c["case_id"] not in seen]
        if not cards:          # empty or repeated page = end of list
            break
        for c in cards:
            seen.add(c["case_id"])
            c.update(category=category, page=p)
            if category in PERSONAL:
                c["title_ar"] = c["title_en"] = None
        # In 2022 Ehsan listed individual orphan sponsorships among projects,
        # titled "أهلاً، أنا <name> وعمري <age> سنة". Orphan sponsorship is out of
        # scope, so they are skipped (after the end-of-list check above, since
        # some pages hold nothing else).
        kept = [c for c in cards if not re.search(ORPHAN_CARD, c.get("title_ar") or "")]
        rows.extend(kept)
        print(f"  {category:<16} page {p:>3}: {len(kept)} cards")
    return rows


def crawl_orphan_archive(fetcher, max_pages, patience=3):
    """Listing-only pass over the completed orphan archive (~22k pages).

    The archive grows while we crawl, so cards shift down and some pages repeat
    cards already seen. A repeated page is therefore not the end; stop on an
    empty page or after `patience` pages in a row with nothing new.
    """
    rows, seen, stale = [], set(), 0
    for p in range(1, max_pages + 1):
        html = fetcher.get(f"/completedinitiatives/orphans?p={p}")
        cards = parse_orphan_cards(html) if html else []
        if html is not None and not cards:
            break
        new = [c for c in cards if c["case_id"] not in seen]
        stale = 0 if new else stale + 1
        if stale >= patience:
            break
        for c in new:
            seen.add(c["case_id"])
            c["page"] = p
        rows.extend(new)
        if p % 100 == 0:
            print(f"  orphans page {p}: {len(rows)} cards")
    return rows


def visits(fetcher, initiative_type, case_id):
    txt = fetcher.get(f"/visit-count/{initiative_type or 'Project'}/{case_id}")
    return _num(txt) if txt and len(txt) < 50 else None


def case_details(fetcher, card, completed_details=False):
    """All page-level fields for one listing card."""
    case_id, url = card["case_id"], card["url"]
    out = {"type": card.get("type"), "case_id": case_id}
    completed = card["category"] in COMPLETED
    if not completed or completed_details:
        html = fetcher.get(url)
        if html:
            out.update(parse_detail(html))
            out["case_id"] = case_id
    if completed:
        html = fetcher.get(REPORTS[card["category"]].format(case_id))
        if html:
            out.update({k: v for k, v in parse_report(html).items() if v is not None})
        # Some report layouts leave out the amount; the detail page has it.
        if out.get("total") is None and not completed_details:
            html = fetcher.get(url)
            if html:
                det = parse_detail(html)
                out["total"] = det.get("target")
                out.setdefault("donation_count", det.get("donation_count"))
    elif out.get("has_more_details"):
        # The detail page fills these in with JS from a POST relative to its own URL.
        frag = fetcher.get(urljoin(url, out["case_url"]), post={"id": str(case_id)})
        if frag:
            out.update({k: v for k, v in parse_org_details(frag).items() if v is not None})
    out.pop("case_url", None)
    out.pop("has_more_details", None)
    if card["category"] in PERSONAL:
        out.pop("description", None)
    out["visits"] = visits(fetcher, out.get("initiative_type") or card.get("type"), case_id)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sections", nargs="+", default=DEFAULT_SECTIONS,
                    choices=list(SECTIONS) + ["completed_orphans"])
    ap.add_argument("--max-pages", type=int, default=1000)
    ap.add_argument("--snapshot", default=date.today().isoformat())
    ap.add_argument("--delay", type=float, default=1.5)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--no-details", action="store_true")
    ap.add_argument("--completed-details", action="store_true",
                    help="also fetch detail pages of completed cases (donation_count)")
    args = ap.parse_args()

    out_dir = Path("data_raw") / args.snapshot
    fetcher = Fetcher(out_dir, args.delay, args.offline)

    if "completed_orphans" in args.sections:
        orphans = pd.DataFrame(crawl_orphan_archive(fetcher, 30000))
        orphans["snapshot"] = args.snapshot
        orphans.to_csv(out_dir / "orphans.csv", index=False, encoding="utf-8-sig")
        print(f"Saved {out_dir / 'orphans.csv'}: {len(orphans)} sponsorships")
        args.sections = [s for s in args.sections if s != "completed_orphans"]
        if not args.sections:
            return

    listings = []
    for sec in args.sections:
        for path, category in SECTIONS[sec]:
            listings += crawl_listing(fetcher, path, category, args.max_pages)
    df = pd.DataFrame(listings)
    if df.empty:
        print("No cards found.")
        return
    # Each section numbers its cases separately (mosque 7089 != housing 7089),
    # so a case is identified by type + id.
    key = ["type", "case_id"]
    print(f"{len(df)} listing rows, {len(df.drop_duplicates(key))} unique cases")

    if not args.no_details:
        cards = df.drop_duplicates(key).to_dict("records")
        details = []
        for i, card in enumerate(cards, 1):
            details.append(case_details(fetcher, card, args.completed_details))
            if i % 50 == 0:
                print(f"  details: {i}/{len(cards)}")
        det = pd.DataFrame(details)
        df = df.merge(det, on=key, how="left", suffixes=("_card", ""))

    df["snapshot"] = args.snapshot
    df.to_csv(out_dir / "opportunities.csv", index=False, encoding="utf-8-sig")
    print(f"Saved {out_dir / 'opportunities.csv'}")


if __name__ == "__main__":
    main()
