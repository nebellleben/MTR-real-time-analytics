with station_data as (
    select distinct
        station_code,
        line_code,
        dest_station,
        platform
    from {{ ref('stg_arrivals') }}
),

ranked_stations as (
    select
        station_code,
        line_code,
        count(distinct line_code) over (partition by station_code) as line_count
    from station_data
)

select distinct
    station_code,
    line_code,
    case when line_count > 1 then true else false end as is_interchange
from ranked_stations
