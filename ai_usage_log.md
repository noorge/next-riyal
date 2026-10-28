# AI usage log

Required by the hackathon rules. Each entry: what the AI was asked for, what it produced, and how the output was checked.

Tools: Claude (claude.ai chat), then Claude Code in VS Code.

## 2026-10-23: planning (Claude chat)

- **Asked:** explain the nonprofit (third) sector, assess whether the brief's three ideas fit one project, and find open Saudi data.
  **Produced:** sector overview, the coverage-gap project design, and a list of candidate sources (Ehsan, NCNP directory, GASTAT, open data portal).
  **Verified:** sources checked by web search with links kept in `docs/conversation_log.md`. Final design decisions were made by the participant, not the AI.

## 2026-10-23: Ehsan scraper (Claude chat)

- **Asked:** write a scraper for ehsan.sa from page HTML captured in the browser.
  **Produced:** `scraper/parse.py`, `scraper/crawl.py`, tests.
  **Verified:** unit tests on real HTML fixtures (6 passing). Internal consistency check (collected + remaining = target). Live first-page run of every section on the local machine, with card counts compared against what the browser shows. Hijri date conversion checked against the page's "last donation 3 hours ago" for a case completed the same day.
  **Data handling:** only program-level public fields are collected. No personal data is stored, and no private data was given to the AI. Only public page HTML was shared.

## 2026-10-23: scraper v2 (Claude Code)

- **Asked:** check why live completed rows had no city or association, add the completed report page, and get the scraper ready for a full crawl.
  **Found:** the raw server HTML has no city, beneficiaries or partner. The site loads them with JavaScript after the page opens (`details.js`), and the first fixtures had been copied from the browser's rendered page, so the tests passed while the live data was empty. Claude read `details.js` and found the two background requests (details fragment and visit count).
  **Produced:** `parse_report`, `parse_org_details`, per-case fetch logic in `crawl.py`, retry and error handling, new tests on raw server responses (10 passing).
  **Verified:** one-page live crawl of every section with fill rates checked per field and section. Fragment values compared with what the browser shows for case 82987 (أملج, 40 beneficiaries, التنمية بسمر الأهلية). Report values for 82990 match the report page (publish 11 Oct, completed 23 Oct, 150,000). Checked that the completed listing ignores `projectType` (same IDs with and without the filter), so the cause has to be inferred.
  **Data handling:** titles and descriptions of individual family and orphan cases are no longer stored.

## 2026-10-24/25: remaining sections and orphan archive (Claude Code)

- **Asked:** cover all four Ehsan sections (projects, housing, orphans, mosques), then collect orphan sponsorship stats without personal data.
  **Found:** each section has its own completed archive and its own report page; reports come in two layouts; case IDs are numbered per section (65 mosque/housing ID collisions caused skipped rows until the crawler keyed on type + ID). The completed orphan archive ignores the site's filters (page count rose instead of falling with a region filter), so per-region orphan counts are not available from listings.
  **Produced:** report parsing for mosques/housing and the impact layout, `parse_orphan_cards` and a listing-only orphan crawl, gzip page cache, tests (16 passing). The orphan test fixture is a real card with the child's name replaced by a placeholder.
  **Verified:** fill rates per section after each crawl; a 20-page live orphan check (177 cards, age/cost/date parsed for all, no titles missed).
  **Decisions (by the participant):** no full per-child orphan crawl (time, storage, privacy); no satisfaction toolkit; no NCNP scraper.

## 2026-10-26: cause and target-group labels from titles (Claude Code)

- **Asked:** give completed projects a cause and a target group, since Ehsan's completed archive has none.
  **Produced:** `labels.py`, two ordered, human-readable keyword rule lists (cause = what is provided, using Ehsan's own project types; target group = who receives it). Claude drafted and iterated the rules against the data; the principle and the checks were set by the participant.
  **Verified:** (1) agreement with Ehsan's own cause on all 29 open projects: 29/29; (2) only 38 of 7,425 completed projects (37 after the fixes below) match no rule and are left as "Other"; (3) a hand check of 100 randomly sampled projects (`validation/title_labels_check.csv`), with accuracy reported in the notebook.
  **Found on the way:** 940 "projects" from 2022 were individual orphan sponsorships with the child's name in the title. The scraper now skips those cards at collection, so no child's name is stored.
  **Hand check result:** 97/100 causes and 98/100 target groups correct. The corrections from the hand check led to four rule fixes (patient transport, funeral washing rooms and sewing machines are Social; Quran circles are not counted as needy students). The reported accuracy is for the rules before these fixes.

## 2026-10-26/27: sections 2 and 3, regions and the association side (Claude Code)

- **Asked:** compare causes and regions fairly, find under-covered region × cause pairs, then explain why little is posted in some regions.
  **Produced:** sections 2 and 3 of the notebook; the coverage and speed measures with a ±5-point noise tolerance; section 3.5, which splits value posted per resident into four parts (partner associations per resident, share that post projects, opportunities per posting association, average size).
  **Changed by the participant's review:** totals were reframed as what associations post, not donor preference, because every completed opportunity is fully funded; donor response is compared per opportunity, by speed. Headlines that the data did not support ("housing grows every year", "most gaps are supply gaps") were replaced by headlines computed from the data.
  **Data added by hand:** 8 missing regions were looked up by the participant (`validation/manual_regions.csv`, with how each was checked). Partner-association counts per region were read by the participant from the map on Ehsan's statistics page, with screenshots (`data_raw/ehsan_dashboard/`). Platform totals cited in the notebook come from the same page.
  **Verified:** the four parts multiply exactly to each region's value per resident (asserted in code); the region counts sum to 3,571 of Ehsan's 3,847 partners, and the difference is documented.

## 2026-10-27: section 4 (timing) and the launch period (Claude Code)

- **Asked:** does the time of posting (Hijri month, salary day, weekday) change how fast opportunities are funded?
  **First version:** each month was compared with what its mix of causes would predict. On review, the participant noticed that this "expected" share was about 66% for every month, so the adjustment did nothing, and asked whether the year was taken into account.
  **Found because of that question:** Ehsan's first six months (Feb–Jul 2021, 792 opportunities) were very slow (25% funded within a week, against 70% afterwards) while donors were still discovering the platform. Because the launch fell in Sha'ban and Ramadan 1442, it distorted the month comparison and every other speed comparison.
  **Fix:** a `launch_period` flag in cleaning (1.5). These opportunities stay in all totals but are left out of speed comparisons in sections 2–4. Months are compared with the average of their own Hijri year, with a year-by-year table.
  **What changed:** Ramadan went from "normal pace" to "faster than its year in 3 of 5 years". Sha'ban stays the slowest, below its year in 5 of 5 years. In section 3, Eastern Health, Eastern Social and Riyadh Religious moved from "neglected" to "supply gap" (their slowness came from the launch period), and Jazan Religious became neglected. Eastern Housing stays the clearest neglected pair (−21 points). Empty days-to-fund values were also being counted as "not funded within a week" in some rates; they are now ignored.

## 2026-10-27: section 5, predicting slow funding (Claude Code)

- **Asked:** a simple, honest model that predicts on posting day whether an opportunity will take more than a week to be funded.
  **Produced:** three models compared (cause only, logistic regression, gradient-boosted trees) using only what is known at posting. Each was tested with five-fold time-series cross-validation on Aug 2021–Jul 2025 and on a held-out final 15 months (Aug 2025–Oct 2026). Also a watch-list chart and permutation importance. Metrics are in `outputs/model_metrics.csv`.
  **Leakage checks:** page visits and donation counts were excluded (they build up after posting). In a first version, a missing beneficiary count was the strongest predictor. A check showed it reflects a change in the layout of Ehsan's housing and mosque report pages (missing counts were mostly slow in 2022–2024 and mostly fast in 2025–2026), not donor behaviour. Missing counts are now filled with the median, and the model is not told which were missing. The test AUC fell from 0.75 to 0.65, and the lower, honest figure is the one reported.
  **Result:** a modest model. Flagging the riskiest 20% catches 31% of slow opportunities (43% of the flagged are slow, against 28% overall). The cause-only model is no better than chance on the newest data. The notebook states that the model is a watch list for early support, not a reason to reject or rank down an opportunity.

## 2026-10-28: section 5, second version (Claude Code)

- **Asked by the participant:** whether the modest score (AUC 0.65) came from using simple models, and to redo the section with four extra posting-day features and a check of larger models.
  **Produced:** four features known at posting: amount per beneficiary, days until salary day, the association's track record (slow share among its opportunities already completed on the posting day, so no future information leaks in), and competition (opportunities open on Ehsan that day and new ones posted in the week before). Validation changed to a year-by-year check: each of two validation years (Aug 2023–Jul 2024, Aug 2024–Jul 2025) is predicted by a model trained only on earlier data; the model is chosen on these, and the final 15 months are used once, as the test.
  **Result:** the new features raised the AUC in all three periods (+0.03 to +0.05); final test AUC 0.70. Competition works in reverse: busy weeks, above all Ramadan, fund faster. Days until salary day adds almost nothing, and this is reported.
  **A tempting result that was rejected:** trees with no depth limit scored 0.75 on the final test, but lower than the chosen model on both validation years. Picking them because of the test score would have meant tuning to the test, so the smaller model was kept and both results are shown (5.3). Before reporting, truncating the test period was also checked, to rule out distortion from opportunities still open when the data was collected; the results did not change.
- **Question from the participant:** why training and test are split by time rather than at random.
  **Produced:** a check in 5.2. The same model was tested on five random splits of the same size: average AUC 0.82, against 0.70 on the latest 15 months. The random figure is inflated by near-copies (similar opportunities from one association in the same week) and by mixing years; the time-based figure is the one reported, because the model would be used on future opportunities.

## 2026-10-28: section 6, recommendations, and section 5 reframed (Claude Code)

- **Asked:** a recommendations section drawing on sections 2–5.
  **Produced:** a table of ten recommendations, each with who acts, the evidence (computed in the notebook, with the section number) and how to tell a year later whether it worked; a closing chart of the 15 priority region × cause pairs; a short list of caveats.
  **Changed by the participant:** the first draft also recommended that Ehsan run the model as a watch list and publish cleaner data. The participant removed both: the model was built to understand how donors respond, not as a tool for the platform. The model recommendations were rewritten as lessons about donors for associations and funders, and section 5 was reframed the same way (5.4 now asks how much of slow funding can be seen in advance; 5.6 lists the limits of what the model shows).
