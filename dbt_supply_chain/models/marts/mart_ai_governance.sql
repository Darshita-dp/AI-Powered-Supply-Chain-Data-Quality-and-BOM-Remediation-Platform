-- AI-governance mart: audited AI-call behavior per provider/model/prompt version.
{{ config(schema='marts', materialized='table') }}
select
    provider,
    model,
    prompt_version,
    cast(called_at as date) as call_date,
    count(*) as calls,
    avg(latency_ms) as avg_latency_ms,
    avg(confidence) as avg_confidence,
    sum(case when abstained then 1 else 0 end) as abstentions,
    sum(case when validation_result != 'valid' then 1 else 0 end) as validation_failures
from {{ source('quality', 'ai_call_audit') }}
group by 1, 2, 3, 4
