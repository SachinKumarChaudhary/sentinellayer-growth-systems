-- Prevent repeated enrichment runs from inflating the same normalized intent signal.
-- Identity is the company + normalized signal type + signal date.
-- Keep the latest observation when earlier enrichment runs already produced duplicates.

with ranked as (
  select
    intent_signal_id,
    row_number() over (
      partition by company_id, signal_type, signal_date
      order by detected_at desc, created_at desc, intent_signal_id desc
    ) as rn
  from intelligence.intent_signals
)
delete from intelligence.intent_signals s
using ranked r
where s.intent_signal_id = r.intent_signal_id
  and r.rn > 1;

create unique index if not exists intent_signals_company_type_date_uq
  on intelligence.intent_signals(company_id, signal_type, signal_date);
