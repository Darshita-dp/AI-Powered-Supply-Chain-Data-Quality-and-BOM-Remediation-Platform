select
    supplier_id,
    supplier_name,
    {{ norm_whitespace('upper(supplier_name)') }} as supplier_name_normalized,
    upper(trim(country)) as country,
    upper(trim(currency)) as currency,
    upper(trim(payment_terms)) as payment_terms,
    source_system,
    upper(trim(status)) as status,
    try_cast(created_date as date) as created_date,
    _ingestion_batch_id,
    _row_hash
from {{ source('raw', 'suppliers') }}
