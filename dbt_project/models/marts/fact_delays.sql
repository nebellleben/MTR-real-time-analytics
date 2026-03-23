with arrivals as (
    select
        ingestion_date,
        extract(hour from arrival_time) as hour,
        line_code,
        line_name,
        station_code,
        time_remaining_seconds
    from {{ ref('stg_arrivals') }}
),

metrics as (
    select
        ingestion_date,
        hour,
        line_code,
        line_name,
        station_code,
        count(*) as sample_count,
        avg(time_remaining_seconds) as avg_wait_seconds,
        stddev(time_remaining_seconds) as std_wait_seconds,
        min(time_remaining_seconds) as min_wait_seconds,
        max(time_remaining_seconds) as max_wait_seconds
    from arrivals
    group by ingestion_date, hour, line_code, line_name, station_code
),

final as (
    select
        ingestion_date,
        hour,
        line_code,
        line_name,
        station_code,
        sample_count,
        avg_wait_seconds,
        std_wait_seconds,
        min_wait_seconds,
        max_wait_seconds,
        avg_wait_seconds + 2 * COALESCE(std_wait_seconds, 0) as upper_bound_seconds,
        GREATEST(avg_wait_seconds - 2 * COALESCE(std_wait_seconds, 0), 0) as lower_bound_seconds
    from metrics
)

select
    ingestion_date,
    hour,
    line_code,
    line_name,
    station_code,
    sample_count,
    avg_wait_seconds,
    std_wait_seconds,
    min_wait_seconds,
    max_wait_seconds,
    upper_bound_seconds,
    lower_bound_seconds,
    case
        when std_wait_seconds > 0 then
            case
                when avg_wait_seconds > upper_bound_seconds then 'unusually_long'
                when avg_wait_seconds < lower_bound_seconds then 'unusually_short'
                else 'normal'
            end
        else 'normal'
    end as wait_category
from final
where sample_count > 0
