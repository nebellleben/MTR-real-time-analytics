with arrivals as (
    select
        ingestion_date,
        extract(hour from scheduled_arrival_time) as hour,
        line_code,
        line_name,
        is_delayed,
        delay_seconds
    from {{ ref('stg_arrivals') }}
),

metrics as (
    select
        ingestion_date,
        hour,
        line_code,
        line_name,
        count(*) as total_arrivals,
        sum(case when is_delayed then 1 else 0 end) as delayed_count,
        sum(delay_seconds) as total_delay_seconds,
        case
            when count(*) > 0 
            then round(sum(delay_seconds) / count(*), 2)
            else 0
        end as avg_delay_seconds,
        max(delay_seconds) as max_delay_seconds,
        min(delay_seconds) as min_delay_seconds,
        case
            when count(*) > 0 
            then round(sum(case when is_delayed then 1 else 0 end) * 100.0 / count(*), 2)
            else 0
        end as delay_percentage
    from arrivals
    group by ingestion_date, hour, line_code, line_name
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
from metrics
where total_arrivals > 0
