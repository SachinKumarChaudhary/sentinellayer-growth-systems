-- Prevent repeated enrichment runs from inflating the same normalized intent signal.
-- Identity is the company + normalized signal type + signal date.

create unique index if not exists intent_signals_company_type_date_uq
  on intelligence.intent_signals(company_id, signal_type, signal_date);
