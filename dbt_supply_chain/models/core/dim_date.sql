-- Calendar spanning history through planning horizon.
{% set start_date = "'2015-01-01'" %}
{% set end_date = "'2028-12-31'" %}

with spine as (
    {% if target.type == 'duckdb' %}
    select unnest(generate_series(date {{ start_date }}, date {{ end_date }}, interval 1 day)) as d
    {% else %}
    select dateadd(day, seq4(), to_date({{ start_date }})) as d
    from table(generator(rowcount => 5115))
    {% endif %}
)
select
    cast(d as date) as date_key,
    extract(year from d) as year,
    extract(month from d) as month,
    extract(day from d) as day,
    extract(quarter from d) as quarter
from spine
