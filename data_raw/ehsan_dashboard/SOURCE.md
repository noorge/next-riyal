# Ehsan statistics page

Figures from Ehsan's public statistics page (https://ehsan.sa/dashboard), read on 27 Oct 2026. The page is live, so the numbers change over time; screenshots of what was read are in `screenshots/`.

**Platform totals since 2021** (`screenshots/statistics_page.png`):

| Figure | Value |
|---|---|
| General donations (إجمالي التبرعات العامة) | SAR 17,629,984,266 |
| Ehsan Waqf Fund donations | SAR 2,540,761,364 |
| Donation transactions (عمليات التبرعات) | 473,582,352 |
| Completed opportunities (الفرص المكتملة) | 33,776 |
| Partner associations (الجمعيات الشريكة) | 3,847 |

The partner-associations page (https://ehsan.sa/dashboard/organizations) also states an average governance score of 91% for partner associations, from NCNP's assessment.

**Partner associations by region** (`partner_associations_by_region.csv`, `screenshots/map_<region>.png`): the map "عدد الجمعيات حسب المناطق" shows each region's count only when the region is clicked, so the 13 counts were read by hand from the map and checked against the screenshots. They sum to 3,571, which is 276 fewer than the 3,847 total: some partners have no region on the map. The map most likely places an association by its headquarters, not by where its projects take place.

The counts could not be read from the page source (they are loaded by script), and the alternative, paging through the partner list eight associations at a time, would have taken about 480 requests to the site.
