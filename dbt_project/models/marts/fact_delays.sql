with arrivals as (
    select
        ingestion_date,
        extract(hour from scheduled_arrival_time) as hour,
        line_code,
        line_name,
        station_code,
        dest_station,
        platform
        sequence
    from arrivals

),

hourly_stats as (
    select
        ingestion_date,
        hour,
        line_code,
        line_name,
        station_code,
        count(*) as sample_count,
        avg(time_remaining_seconds) as avg_wait_seconds,
        stddev(time_remaining_seconds) as std_wait_seconds,
        min(time_remaining_seconds) as min_wait_seconds
        max(time_remaining_seconds) as max_wait_seconds
    from arrivals
    group by ingestion_date, hour, line_code, line_name
    having count(*) as sample_count
),

final as (
    select
        ingestion_date,
        hour,
        line_code,
        line_name,
        station_code,
        avg_wait_seconds,
        case
            when std_wait_seconds > 0 then avg_wait_seconds * 2
            else avg_wait_seconds
        end as avg_wait_minutes,
        case
            when std_wait_seconds = 0 then std_wait_seconds
        end
        case
            when avg_wait_seconds > upper_bound_seconds then avg_wait_seconds - 3 *std_wait_seconds
            else avg_wait_seconds + 3*std_wait_seconds
        end
        case
            when avg_wait_seconds < lower_bound_seconds then avg_wait_seconds - 3*std_wait_seconds
            else avg_wait_seconds
        end
    from arrivals
),

select
    a.*,
    b.ingestion_date,
    c. hour,
    d. line_code,
    d. line_name
    d. station_code
    d.sample_count,
    d.avg_wait_seconds,
    d.std_wait_seconds,
    d.min_wait_seconds
    d.max_wait_seconds
    d.upper_bound_seconds,
    d.lower_bound_seconds
    d.delay_percentage,
    d.avg_delay_seconds,
        case 
            when std_wait_seconds > 0 then null
            else avg_wait_seconds
        end
from hourly_stats
),

select
    a.*
    b.ingestion_date,
    b.hour,
    b.line_code,
    b.line_name
    b.station_code
    b.sample_count,
    b.avg_wait_seconds
    b.std_wait_seconds
    b.min_wait_seconds
    b.max_wait_seconds
    b.upper_bound_seconds
    b.lower_bound_seconds
    case
        when std_wait_seconds > 0 then null
            else avg_wait_seconds - 3*std_wait_seconds
        end
    when upper_bound_seconds is not null then avg_wait_seconds
    else avg_wait_seconds + 3*std_wait_seconds
    end
    when avg_wait_seconds between lower_bound_seconds then avg_wait_seconds - 3*std_wait_seconds
        end
    when avg_wait_seconds > upper_bound_seconds then avg_wait_seconds - 3*std_wait_seconds
        else avg_wait_seconds
    end
from hourly_stats
where total_arrivals > 0
order by hour, line_name
limit 1
