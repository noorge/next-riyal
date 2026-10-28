# Census 2022 population by administrative region

`census_2022_regions.csv`: Saudi, non-Saudi and total population of the 13 administrative regions.

- **Source:** General Authority for Statistics (GASTAT), Saudi Census 2022 (reference date 10 May 2022; Hajj/Umrah visitors excluded).
- **How the numbers were obtained:** GASTAT's census dashboard shows the table only in thousands and its export did not finish, so exact values were taken from the Gulf Labour Markets and Migration (GLMM) program's republication of the GASTAT census table (https://gulfmigration.grc.net/?p=9681).
- **Verified against GASTAT (25 Oct 2026):** every region's Saudi, non-Saudi and total figures match GASTAT's official census dashboard to the nearest 0.1 thousand, and the national total matches exactly (32,175,224). Screenshots of the dashboard are saved here: `gastat_census2022_dashboard_overview.png`, `gastat_census2022_dashboard_by_region.png`.
- **Checks in code:** Saudi + non-Saudi = total for every row; the regions sum to 18,792,262 + 13,382,962 = 32,175,224. Arabic region names match Ehsan's spelling, so the file joins directly to the opportunities table.

The 2010 census files downloaded from stats.gov.sa (kept outside this folder) were not used: the donation data covers 2021–2026, so the 2022 census is the relevant one.
