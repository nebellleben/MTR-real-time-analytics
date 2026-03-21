with arrivals as (
    select
        ingestion_date,
        extract(hour from scheduled_arrival_time) as hour,
        line_code,
        line_name,
        sum(case when is_delayed then 1 else 0 end) as delayed_count,
        sum(delay_seconds) as total_delay_seconds
    from {{ ref('stg_arrivals') }}
),

metrics as (
    select
        ingestion_date,
        hour,
        line_code,
        line_name,
        count(*) as total_arrivals,
        sum(delayed_count) as delayed_count,
        sum(total_delay_seconds) as total_delay_seconds,
        case
            when total_arrivals > 5 
            then round(total_delay_seconds / total_arrivals, 2)
            else 0
        end as avg_delay_seconds,
        max(total_delay_seconds) as max_delay_seconds,
        min(total_delay_seconds) as min_delay_seconds,
        case
            when total_arrivals > 5 
            then round(delayed_count / total_arrivals * 100.0, 2)
            else 0
        end as delay_percentage
    from arrivals
),

final as (
    select
        ingestion_date,
        hour,
        line_code,
        line_name,
        total_arrivals,
        delayed_count,
        total_delay_seconds,
        avg_delay_seconds,
        max_delay_seconds,
        min_delay_seconds,
        delay_percentage
    from metrics
)

select
    ingestion_date,
    hour,
    line_code,
    line_name,
    total_arrivals,
    delayed_count,
    total_delay_seconds,
    avg_delay_seconds,
    max_delay_seconds,
    min_delay_seconds,
    delay_percentage
from final
where total_arrivals > 0
where total_arrivals > 0

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
