with line_data as (
    select distinct
        line_code,
        line_name,
        case line_code
            when 'TCL' then '#F7943D'
            when 'EAL' then '#5EB6E4'
            when 'TML' then '#9B27B0'
            when 'TKL' then '#7B68EE'
            when 'KTL' then '#00A86D'
            when 'TWL' then '#E2231A'
            when 'ISL' then '#0075C2'
            when 'SIL' then '#B5D99A'
            when 'DRL' then '#FF69B4'
            when 'AEL' then '#00A0E0'
            else '#808080'
        end as line_color,
        case 
            when line_code in ('ISL', 'KTL', 'TWL', 'TKL') then true
            else false
        end as is_urban
    from {{ ref('stg_arrivals') }}
)

select 
    line_code,
    line_name,
    line_color,
    is_urban
from line_data
