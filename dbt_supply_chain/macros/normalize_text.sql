{#- Adapter-safe normalization helpers. Originals are always preserved in the
    staging models; these produce additional *_normalized columns. -#}

{% macro norm_upper_trim(col) -%}
    upper(trim({{ col }}))
{%- endmacro %}

{% macro norm_part_number(col) -%}
    {#- strip separators and spaces, uppercase: cross-system comparable key.
        DuckDB needs the 'g' flag to replace all matches; Snowflake replaces all
        by default. -#}
    {%- if target.type == 'duckdb' -%}
        regexp_replace(upper(trim({{ col }})), '[^A-Z0-9]', '', 'g')
    {%- else -%}
        regexp_replace(upper(trim({{ col }})), '[^A-Z0-9]', '')
    {%- endif -%}
{%- endmacro %}

{% macro norm_whitespace(col) -%}
    {%- if target.type == 'duckdb' -%}
        regexp_replace(trim({{ col }}), '\s+', ' ', 'g')
    {%- else -%}
        regexp_replace(trim({{ col }}), '\\s+', ' ')
    {%- endif -%}
{%- endmacro %}
