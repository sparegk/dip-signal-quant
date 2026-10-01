# EXP-003 universe provenance audit

## What this repository actually has

The preserved [official OEF holdings source](https://www.ishares.com/us/products/239723/ishares-s-p-100-etf/latest-holdings.csv)
has an as-of date of **2026-09-29**, retrieved September 30. Its local SHA-256 is
`c0b501dfd8825fdfa83d286116ce80e788c90e8c6b33b768aded524603fe741c`.
The live URL changes; reproduce using the preserved CSV, not today's endpoint.
The configuration contains the full original selection and source hash.

Re-reading that file confirms exactly 101 rows with Asset Class=Equity and
Location=United States. Normalizing spaces/dots to hyphens gives exactly the
registered 101 symbols (`BRK B` becomes `BRK-B`). Alphabetical ordering, exclusion
of AAPL/AMZN/MSFT/NVDA/GOOGL plus GOOG (same inspected issuer), and benchmark-only
SPY leave **95 names**. No historical performance or chart selected these names.
This is a dated current fund-holdings universe, not proof of exact index composition
or historical liquidity. Multiple share classes are securities, not independent
issuers; GOOG/GOOGL were explicitly excluded together. Other issuer identity links
have not been comprehensively reconstructed.

Local assets provide a single static holdings snapshot, daily revised adjusted
prices, and an interval-validation/membership-mask implementation. They provide
**no sourced historical membership intervals**. The existing `src/universe.py`
supports disjoint `[start_date,end_date)` intervals, adjacency and re-entry; no
new abstraction or invented intervals were needed. An interval file alone cannot
establish when membership was known, identity continuity, or revision history.

## Identity and listing-history examples

These are provenance warnings, not reasons to change EXP-002's sample or results.

| Symbol/history | Observed or documented issue | Research implication |
| --- | --- | --- |
| BNY | Issuer announced BK-to-BNY effective May 21, 2026, with unchanged CUSIPs; cached BNY history starts 2016-09-29. | Current symbol labels historical issuer prices; it was not the contemporaneous historical ticker. |
| GEV / GE | Cached GEV begins March 27, 2024. Issuer distinguished March 27 when-issued trading from April 2 regular-way trading and the GE Aerospace continuation. | First provider bar is not automatically the first regular listing; GE's business identity also changed. |
| SNDK | Cached series begins February 13, 2025; issuer says regular-way independent trading began February 24 following separation from Western Digital. | Earlier provider bars need an explicit trading-status/identity explanation; do not assume old and new SNDK strings represent one continuous security. |
| PLTR / UBER | Cached histories begin September 30, 2020 / May 10, 2019. | No supplied older prices or membership evidence; unequal histories remain explicit. |
| DELL | Provider history covers the requested 2016-09-29 start; Dell's December 28, 2018 notice describes completion of the Class V transaction and the new Class C shares. | Earlier provider observations require explicit share-class/predecessor mapping; a populated series alone does not establish continuity. |
| RTX | Issuer filings document the April 3, 2020 UTC spin-offs and Raytheon merger; the diagnostic RTX-labelled history includes a 2017 offending row. | Historical symbol/business mapping needs separate evidence; the numerical violation is not evidence that the merger caused bad prices. |

The BNY facts come from its [issuer announcement](https://www.bny.com/corporate/global/en/about-us/newsroom/press-release/bny-announces-planned-change-of-stock-ticker-symbol-to-bny-130465.html).
GE dates/trading distinctions come from its [spin-off notice](https://www.gevernova.com/news/press-releases/ge-board-of-directors-approves-spin-off-of-ge-vernova-ge-vernova-and-ge-aerospace-to).
Sandisk's regular-way date comes from its [separation announcement](https://investor.sandisk.com/node/6606/pdf).
Dell's [Class V completion notice](https://www.dell.com/en-uk/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2018~12~dell-technologies-completes-class-v-transaction.htm)
and RTX's [transaction filing](https://investors.rtx.com/static-files/466a15a4-f18e-40cd-aee6-2a451c2f2046)
provide the additional corporate-history dates.
These examples expose missing identity metadata; this is not a complete 95-issuer
corporate-action reconstruction or an attribution of the OHLC numerical defects.
No memberships, delisting prices or predecessor histories were fabricated.

## Practical historical membership sources

Public documentation reviewed for EXP-003; no purchase, signup, contract acceptance
or licensed dataset download was performed.

| Source | Relevant coverage and access | Limitations to resolve before acquisition |
| --- | --- | --- |
| S&P Dow Jones Indices | Official API offers historical constituents and corporate actions/index events; licensed data packages and API/SFTP/SPICE delivery. | Exact S&P 100 start date, announcement-vs-effective fields, retained original vintages and use/redistribution rights require confirmation for the selected product. Public pages are not a free complete membership ledger. |
| Norgate | Published table lists S&P 100 constituent history from September 1989. Platinum-or-higher access includes historical membership via supported integrations/Python, with daily effective membership and delisted-security coverage. | FAQ explicitly omits announcement dates and temporary inclusions. Effective membership is useful but does not alone prove all facts were known at a past signal timestamp. Applicable subscription/history tier, permanent-identity mapping, revision handling and export rights need review. |
| CRSP US Stock Database | Long stock histories (NYSE from December 1925, Nasdaq from December 1972), permanent PERMNO/PERMCO identities, corporate-action and delisting data, subscribed delivery. | Good candidate for a broader historical eligible-stock universe; do not assume a license automatically supplies the required S&P 100 membership/announcement archive. Exact fields, exchanges, rights and access need product confirmation. |

Sources: S&P's [API description](https://www.spglobal.com/spdji/en/landing/topic/api-data-solutions/)
and [licensing overview](https://www.spglobal.com/spdji/en/about-us/data-index-licensing/);
Norgate's [coverage table](https://norgatedata.com/data-content-tables.php),
[membership FAQ](https://norgatedata.com/data-package-faq.php) and
[licensing terms](https://norgatedata.com/subscribe/eula.php);
CRSP's [database description](https://www.crsp.org/research__trashed/crsp-us-stock-databases/).
Norgate's terms distinguish personal use from making data available to another
entity. No legal permission to redistribute data is inferred from its accessibility.

The missing deliverable is a licensed/otherwise permitted, versioned security
master and membership history with permanent IDs, effective and knowledge dates,
share-class/issuer links, additions/removals, revisions and delistings. Before any
future PIT claim, validate the chosen source against independent announcements
and disclose coverage gaps, inferred records and unavailable original vintages.
No current-constituent list or date-filled interval file can substitute for it.

For EXP-003's prospective collection, freeze the **95 requested** names from
October 1 onward and preserve failures. This is prospective decision capture in a
survivor-selected static universe, not reconstructed historical PIT membership.
