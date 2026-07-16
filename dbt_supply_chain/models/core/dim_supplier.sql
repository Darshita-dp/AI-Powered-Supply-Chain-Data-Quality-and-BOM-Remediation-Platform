select
    supplier_id as supplier_key,
    supplier_name,
    supplier_name_normalized,
    country,
    currency,
    payment_terms,
    source_system,
    status,
    created_date
from {{ ref('stg_suppliers') }}
