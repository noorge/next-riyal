# Data dictionary

Files in `data_clean/`, produced by section 1 of `analysis.ipynb` from the raw file `data_raw/2026-10-23/opportunities.csv` (collected from ehsan.sa on 23 October 2026). Scope: Ehsan's Projects area (general projects, mosque care, housing); see the notebook appendix for what is out of scope.

## opportunities_clean.csv

One row per donation opportunity: 9,788 rows, 18 columns. Money is in Saudi riyals. Dates are Gregorian, `YYYY-MM-DD`.

| Column | Type | Filled | Meaning | Source and cleaning |
|---|---|---|---|---|
| `uid` | text | 100% | Unique ID: section type + Ehsan case ID, e.g. `Project-82979` | Ehsan numbers cases separately per section, so the case ID alone is not unique (1.1) |
| `section` | text | 100% | `projects`, `mosques` or `housing` | From the Ehsan listing the opportunity came from (1.1) |
| `status` | text | 100% | `completed` (fully funded) or `active` (open on collection day) | From the listing (1.1) |
| `cause` | text | 100% | What the opportunity provides: Education, Environmental, Feeding, Health, Housing, Religious, Social, Mosques, or Other | Open projects: Ehsan's own listing category. Completed projects: rules on the title in `labels.py` (1.6). Mosque section: Mosques. Housing section: Housing. `Other` (37 rows) when no rule matches |
| `target_group` | text | 100% | Who receives it: Orphans, Widows & divorced women, Prisoners' families, Patients, People with disabilities, Elderly, Children, Students, Couples marrying, Pilgrims & worshippers, Families in need, General public | Rules on the title in `labels.py` (1.6). `General public` when the title names no group. Hand-checked on 100 random projects: 98% correct |
| `title_ar` | text | 94% | Arabic title | As published. Empty for housing-section cases, whose titles describe individual families (removed at collection for privacy) |
| `region` | text | 99.97% | Administrative region, Arabic, e.g. `منطقة الرياض` | From the report page; where missing, filled from the city, then the association, then by hand (1.3). 3 rows remain unknown |
| `region_en` | text | 99.97% | English region name for charts | Mapped from `region` |
| `region_filled` | yes/no | 100% | True if `region` was filled in (city, association or by hand) | 1.3 |
| `city` | text | 100% | City or governorate, original spelling | Whitespace trimmed (1.2) |
| `partner_name` | text | 99.9% | Implementing association | Whitespace trimmed; checked for spelling variants, none found (1.2) |
| `beneficiaries` | number | 90.5% | Number of beneficiaries | Completed: report page. Open: planned beneficiaries. Values of 0 set to empty (1.8). Counts mix people supported and people reached, so compare only within a cause (1.9) |
| `beneficiary_nationality` | text | 86.4% | `المواطنون` (citizens), `المقيمون بالمملكة` (residents) or both | Ehsan's "beneficiary type"; renamed because nationality is all it records (1.4). Not shown in the older report layout |
| `amount_sar` | number | 100% | Completed: amount raised (equals the target). Open: target amount | Merged from `total` and `target` (1.4). Unknown for 3 rows (report page error) |
| `visits` | number | 100% | Page visits on Ehsan | Visit counter on collection day |
| `publish_date` | date | 99.4% | Date the opportunity was published | Report page; completed opportunities only |
| `completed_date` | date | 99.5% | Date it was fully funded | Report page; completed opportunities only |
| `days_to_fund` | number | 99.1% | `completed_date − publish_date` in days | 1.5. Empty for open opportunities and for 33 rows completed before their publish date (re-published cases) |
| `launch_period` | yes/no | 100% | True if published before 1 Aug 2021, Ehsan's first six months | 1.5. Kept in all totals; left out of speed comparisons (sections 2–4) |

## city_region.csv

The city → region lookup used to fill missing regions (1.3), built from opportunities that show both. 490 cities, none appearing under two regions.

| Column | Meaning |
|---|---|
| `city_key` | Spelling-insensitive city key (1.2 rules) |
| `region` | Region, Arabic |
| `city_example` | One original spelling of the city |
| `n_opportunities` | Opportunities with this city and a known region |

## cleaning_log.csv

Every cleaning step: `step`, `rows_affected`, `note`. Shown as a table at the end of section 1.

## Population (raw input)

`data_raw/gastat/census_2022_regions.csv`: GASTAT Census 2022 population by region (Saudi, non-Saudi, total). Source and checks in `data_raw/gastat/SOURCE.md`.
