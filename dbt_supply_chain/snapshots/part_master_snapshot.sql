{% snapshot part_master_snapshot %}
{{
    config(
        target_schema='staging',
        unique_key='part_id',
        strategy='check',
        check_cols=['description', 'uom', 'lifecycle_status', 'standard_cost',
                    'lead_time_days', 'primary_plant'],
    )
}}
-- Slowly-changing history of part master attributes.
select * from {{ ref('stg_part_master') }}
{% endsnapshot %}
