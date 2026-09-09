# TinyFish Monthly Operating Model

The enrichment worker runs one bounded daily cycle. It processes up to 40 never-enriched companies, then refreshes up to 10 companies whose latest completed enrichment is at least 7 days old. Refresh selection prioritizes urgent/active/interest accounts and then the stalest scores.

TinyFish remains Search + Fetch only. The daily safety ceilings are 27 Search/minute, 450 Search/hour, 135 fetched URLs/minute, and 900 fetched URLs/day. New-company research may fetch up to 10 URLs per company; refreshes use at most 8.

Refreshes are evidence refreshes, not outreach. Contact verification and approval gates remain separate.
