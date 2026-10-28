# Where should the next riyal go?

An entry to هاكاثون تحليل البيانات في القطاع غير الربحي 2 (Kafaat + PASDS).

**The question:** which region × cause pairs should come first for grants and support to associations? The analysis covers every donation opportunity in the Projects area of Ehsan, Saudi Arabia's national giving platform, from February 2021 to October 2026 (9,788 opportunities, SAR 1.9B raised).

**The answer in brief:** the Eastern Region first (6 of the 15 priority pairs), then Riyadh, Makkah, Madinah and Jazan. In 12 pairs donors already fund what is posted at a normal pace, so the gap is how little is posted; only 3 pairs need grants or matching funds.

| | |
|---|---|
| Notebook (runs in Colab) | [Open in Colab](https://colab.research.google.com/github/noorge/next-riyal/blob/main/analysis.ipynb) |
| Executive summary (Arabic and English) | [`report/executive_summary.pdf`](report/executive_summary.pdf) |
| Use of AI | [`ai_usage_log.md`](ai_usage_log.md) |

## Run the analysis

In Colab: open the link above and choose *Runtime → Run all*. The first cell fetches this repository and installs three small libraries.

On a computer:

```bash
pip install -r requirements.txt
jupyter nbconvert --to notebook --execute --inplace analysis.ipynb
```

The notebook reads only the small files below and rebuilds everything else (clean data, figures, tables).

## Folders

| Path | What it holds |
|---|---|
| `analysis.ipynb` | The analysis: 1 Cleaning, 2 Who gets funded, 3 The coverage gap, 4 Timing, 5 Predicting slow funding, 6 Recommendations, Appendix |
| `viz.py`, `labels.py` | Chart and table style; rules that label each opportunity's cause from its title |
| `data_raw/2026-10-23/opportunities.csv` | The raw table collected from Ehsan (the notebook's input) |
| `data_raw/gastat/`, `data_raw/ehsan_dashboard/` | Census 2022 population by region; partner associations by region from Ehsan's statistics page, with sources and screenshots |
| `validation/` | Hand checks: regions filled by hand, a random sample of cause labels |
| `data_clean/` | Clean table, data dictionary and cleaning log (written by the notebook) |
| `outputs/` | Figures and result tables (written by the notebook) |
| `report/` | Executive summary (PDF and its HTML source). `python report/charts_ar.py` redraws its Arabic charts into `outputs/figures/ar/` (Tajawal font in `report/fonts/`, OFL licence) |
| `scraper/`, `tests/` | The data collector and its parser tests |

## Privacy

No personal data is stored. Titles and descriptions of individual family and orphan cases were dropped at collection, and all analysis is aggregated to region × cause. The raw HTML cache (about 2 GB) and the parser test fixtures (raw Ehsan pages, some describing individual cases) are not published, so `tests/` runs only on the original machine.

# The scraper

Collects donation opportunities from ehsan.sa (listing pages + each opportunity's detail page) into one CSV.

## Run

```bash
pip install -r requirements.txt
python -m pytest -q tests                                   # parser tests, no internet needed
python -m scraper.crawl --sections projects --max-pages 2   # quick live test
python -m scraper.crawl                                     # full crawl
```

Output goes to `data_raw/<date>/opportunities.csv`. Every page fetched is cached in `data_raw/<date>/html/`, so `--offline` re-parses a snapshot without touching the site. Requests are spaced 1.5 s apart (`--delay` to change).

## Columns

From the listing card: `case_id, type, title_ar, title_en, url, progress_pct, collected_card, remaining_card, category, page`.

Active opportunities, from the detail page: `case_ref, target, collected, remaining, beneficiaries_served, donation_count, last_donation_ago, description, initiative_type`. From the details fragment the page loads with JavaScript (`POST .../Projects/OrganizationDetails/<id>`): `beneficiaries_target, beneficiary_type, city, partner_id, partner_name`.

Completed opportunities, from the report page (`/CompletedInitiatives/Report?projectId=<id>`): `region, city, partner_name, case_ref, opportunity_type, beneficiary_type, beneficiaries, publish_date, completed_date, total`. Add `--completed-details` to also fetch their detail pages (`donation_count`), at about twice the crawl time.

All cases: `visits` from `/visit-count/<type>/<id>`.

`category` comes from the filter the card was found under (Education, Feeding, Housing, Health, Religious, Social, Environmental, Technical, plus HousingPlatform, Mosques, CompletedMosques, CompletedHousing and Completed). Orphan sponsorship (`--sections orphans`, `completed_orphans`) and international relief (`--sections rescue`) are out of scope and opt-in only. Individual orphan sponsorships that Ehsan listed among 2022's projects (titled "أهلاً، أنا <name> وعمري <age>") are skipped at collection, so no child's name is stored. The completed listing ignores the category filter, so completed rows have no cause and are classified from their titles in the analysis.

Completed orphan sponsorships (`--sections completed_orphans`, opt-in; not used in the analysis because the archive server takes ~11 s per page): a listing-only pass over `/completedinitiatives/orphans` written to `data_raw/<date>/orphans.csv` with `case_id, case_ref, monthly_cost, completed_date, age_years, page`. Age is read from the card title and the child's name is discarded. The cards carry no region, city or association, and no detail pages are fetched.

New pages are cached gzip-compressed (`.html.gz`); older `.html` cache files are still read.

## Notes

- The raw HTML does not contain city, beneficiaries or partner. The site's JavaScript loads them after the page opens, so test fixtures are raw server responses, not pages copied from the browser's inspector.
- Housing-platform and orphan cases describe individual families and children, so their titles and descriptions are not stored.
- Funding speed comes from each completed report's publish and completion dates, so one snapshot is enough.
- Only program-level fields are collected. No personal data is stored.
