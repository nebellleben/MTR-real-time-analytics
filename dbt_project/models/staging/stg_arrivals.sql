with source as (
    select
        arrival_id,
        line_code,
        line_name,
        station_code,
        station_name,
        dest_station,
        platform,
        sequence,
        arrival_time as scheduled_arrival_time,
        time_remaining as time_remaining_seconds,
        is_delayed,
        delay_seconds,
        ingestion_timestamp,
        ingestion_date
    from {{ source('mtr_analytics', 'raw_arrivals') }}
    where arrival_id is not null
),

deduplicated as (
    select
        arrival_id,
        line_code,
        line_name,
        station_code,
        station_name,
        dest_station,
        platform,
        sequence,
        scheduled_arrival_time,
        time_remaining_seconds,
        is_delayed,
        delay_seconds,
        ingestion_timestamp,
        ingestion_date,
        row_number() over (
            partition by arrival_id
            order by ingestion_timestamp desc
        ) as row_num
    from source
),

final as (
    select
        arrival_id,
        line_code,
        line_name,
        station_code,
        station_name,
        dest_station,
        platform,
        sequence,
        scheduled_arrival_time,
        time_remaining_seconds,
        is_delayed,
        delay_seconds,
        ingestion_timestamp,
        ingestion_date
    from deduplicated
    where row_num = 1
)

select * from final
