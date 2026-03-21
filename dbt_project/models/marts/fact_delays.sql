with arrivals as (
    select
        ingestion_date,
        extract(hour from ingestion_timestamp) as hour,
        line_code,
        station_code,
        time_remaining_seconds,
        is_delayed,
        delay_seconds
    from {{ ref('stg_arrivals') }}
),

metrics as (
    select
        ingestion_date,
        hour,
        line_code,
        station_code,
        count(*) as total_arrivals,
        sum(case when is_delayed then 1 else 0 end) as delayed_count,
        sum(case when is_delayed then delay_seconds else 0 end) as total_delay_seconds,
        avg(time_remaining_seconds) as avg_wait_time_seconds,
        max(time_remaining_seconds) as max_wait_time_seconds,
        min(time_remaining_seconds) as min_wait_time_seconds
    from arrivals
    group by ingestion_date, hour, line_code, station_code
)

select
    ingestion_date,
    hour,
    line_code,
    station_code,
    total_arrivals,
    delayed_count,
    total_delay_seconds,
    avg_wait_time_seconds,
    max_wait_time_seconds,
    min_wait_time_seconds,
    case when total_arrivals > 0 
        then round(delayed_count * 100.0 / total_arrivals, 2) 
        else 0 
    end as delay_percentage
from metrics
