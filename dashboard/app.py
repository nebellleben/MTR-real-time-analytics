"""
MTR Wait Time Analysis Dashboard
A comprehensive Streamlit dashboard for analyzing MTR train wait times.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime, timedelta
import os

# Page config
st.set_page_config(
    page_title="MTR Wait Time Analysis",
    page_icon="🚇",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #666;
    }
</style>
""",
    unsafe_allow_html=True,
)


MTR_LINE_COLORS = {
    "Tsuen Wan Line": "#ED1D24",
    "Kwun Tong Line": "#00A040",
    "Island Line": "#0075C2",
    "Tseung Kwan O Line": "#7D4990",
    "Tung Chung Line": "#F7943E",
    "Airport Express": "#00888C",
    "Disneyland Resort Line": "#D4849A",
    "East Rail Line": "#5FC0D3",
    "Tuen Ma Line": "#9A3B26",
    "South Island Line": "#B5D334",
}


def get_line_color(line_name):
    return MTR_LINE_COLORS.get(line_name, "#1f77b4")


@st.cache_resource
def get_bigquery_client():
    """Get BigQuery client with service account credentials for Streamlit Cloud"""
    if "gcp_service_account" in st.secrets:
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"]
        )
        return bigquery.Client(credentials=credentials, project="de-zoomcamp-485516")
    else:
        return bigquery.Client(project="de-zoomcamp-485516")


@st.cache_data(ttl=300)
def load_data(_client, hours_back=24):
    """Load data from BigQuery"""
    query = f"""
    WITH raw_data AS (
        SELECT
            arrival_id,
            line_code,
            line_name,
            station_code,
            time_remaining as time_remaining_seconds,
            direction,
            ingestion_timestamp,
            ingestion_date,
            EXTRACT(HOUR FROM arrival_time) as hour,
            EXTRACT(DATE FROM ingestion_timestamp) as date
        FROM `de-zoomcamp-485516.mtr_analytics.raw_arrivals`
        WHERE ingestion_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours_back} HOUR)
    )
    SELECT * FROM raw_data
    ORDER BY ingestion_timestamp desc
    """
    df = _client.query(query).to_dataframe()
    df["time_remaining_minutes"] = df["time_remaining_seconds"] / 60
    return df


@st.cache_data(ttl=300)
def load_hourly_stats(_client, days_back=7):
    """Load hourly statistics from BigQuery"""
    query = f"""
    WITH hourly_stats AS (
        SELECT
            ingestion_date,
            EXTRACT(HOUR FROM arrival_time) as hour,
            line_code,
            line_name,
            station_code,
            COUNT(*) as sample_count,
            AVG(time_remaining) as avg_wait_seconds,
            STDDEV(time_remaining) as std_wait_seconds,
            MIN(time_remaining) as min_wait_seconds,
            MAX(time_remaining) as max_wait_seconds
        FROM `de-zoomcamp-485516.mtr_analytics.raw_arrivals`
        WHERE ingestion_date >= DATE_SUB(CURRENT_DATE(), INTERVAL {days_back} DAY)
        GROUP BY ingestion_date, hour, line_code, line_name, station_code
    )
    SELECT 
        *,
        avg_wait_seconds + 2 * COALESCE(std_wait_seconds, 0) as upper_bound_seconds,
        GREATEST(0, avg_wait_seconds - 2 * COALESCE(std_wait_seconds, 0)) as lower_bound_seconds
    FROM hourly_stats
    ORDER BY ingestion_date, hour, line_code
    """
    df = _client.query(query).to_dataframe()
    for col in [
        "avg_wait_seconds",
        "std_wait_seconds",
        "min_wait_seconds",
        "max_wait_seconds",
        "upper_bound_seconds",
        "lower_bound_seconds",
    ]:
        if col in df.columns:
            df[col.replace("_seconds", "_minutes")] = df[col] / 60
    return df


def main():
    # Header
    st.markdown(
        '<h1 class="main-header">🚇 MTR Wait Time Analysis</h1>', unsafe_allow_html=True
    )
    st.markdown(
        "Real-time analysis of MTR train waiting times across Hong Kong's metro network"
    )

    # Sidebar
    st.sidebar.title("⚙️ Settings")

    # Initialize client
    client = get_bigquery_client()

    # Load data
    with st.spinner("Loading data from BigQuery..."):
        try:
            df_raw = load_data(client, hours_back=24)
            df_hourly = load_hourly_stats(client, days_back=7)

            if df_raw.empty:
                st.warning(
                    "No data available. Please run the producer to collect data."
                )
                st.stop()
        except Exception as e:
            st.error(f"Error loading data: {e}")
            st.stop()

    # Sidebar filters
    st.sidebar.subheader("Filters")

    # Date range
    dates_available = sorted(df_raw["date"].unique()) if not df_raw.empty else []
    if len(dates_available) > 0:
        selected_date = st.sidebar.selectbox(
            "Select Date", dates_available, index=len(dates_available) - 1
        )
    else:
        selected_date = None

    # Line filter
    lines_available = sorted(df_raw["line_name"].unique()) if not df_raw.empty else []
    selected_lines = st.sidebar.multiselect(
        "Select Lines", lines_available, default=lines_available
    )

    # Hour range
    hours_available = sorted(df_raw["hour"].unique()) if not df_raw.empty else []
    if len(hours_available) > 0:
        hour_range = st.sidebar.slider(
            "Hour Range",
            min_value=0,
            max_value=23,
            value=(int(min(hours_available)), int(max(hours_available))),
        )
    else:
        hour_range = (0, 23)

    # Filter data
    df_filtered = df_raw.copy()
    if selected_date:
        df_filtered = df_filtered[df_filtered["date"] == selected_date]
    if selected_lines:
        df_filtered = df_filtered[df_filtered["line_name"].isin(selected_lines)]
    df_filtered = df_filtered[
        (df_filtered["hour"] >= hour_range[0]) & (df_filtered["hour"] <= hour_range[1])
    ]

    if df_filtered.empty:
        st.warning(
            "No data available for the selected filters. Please adjust your selection or wait for data to be collected."
        )
        st.stop()

    # Metrics row
    st.subheader("📊 Overview Metrics")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(label="Total Arrivals", value=f"{len(df_filtered):,}")
    with col2:
        avg_wait = df_filtered["time_remaining_minutes"].mean()
        st.metric(
            label="Avg Wait Time",
            value=f"{avg_wait:.1f} min" if not pd.isna(avg_wait) else "N/A",
        )
    with col3:
        variance = df_filtered["time_remaining_minutes"].var()
        std_wait = df_filtered["time_remaining_minutes"].std()
        st.metric(
            label="Std Deviation",
            value=f"{std_wait:.1f} min" if not pd.isna(std_wait) else "N/A",
        )
    with col4:
        overall_mean = df_filtered["time_remaining_minutes"].mean()
        overall_std = df_filtered["time_remaining_minutes"].std()
        if pd.isna(overall_std):
            outlier_count = 0
        else:
            outliers = df_filtered[
                (df_filtered["time_remaining_minutes"] > overall_mean + 2 * overall_std)
                | (
                    df_filtered["time_remaining_minutes"]
                    < overall_mean - 2 * overall_std
                )
            ]
            outlier_count = len(outliers)
        st.metric(
            label="Outliers (±2 SD)",
            value=f"{outlier_count:,}",
        )
    with col5:
        lines_active = df_filtered["line_name"].nunique()
        st.metric(label="Active Lines", value=lines_active)

    st.divider()

    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "📈 Hourly Trends",
            "🚇 Line Analysis",
            "🚉 Station Analysis",
            "📊 Distribution",
            "⚠️ Anomalies",
        ]
    )

    # Tab 1: Hourly Trends
    with tab1:
        st.subheader("Hourly Wait Time Trends")

        # Hourly average by line
        hourly_avg = (
            df_filtered.groupby(["hour", "line_name"])["time_remaining_minutes"]
            .mean()
            .reset_index()
        )

        fig_hourly = px.line(
            hourly_avg,
            x="hour",
            y="time_remaining_minutes",
            color="line_name",
            title="Average Wait Time by Hour and Line",
            labels={
                "hour": "Hour of Day",
                "time_remaining_minutes": "Avg Wait Time (min)",
                "line_name": "Line",
            },
            markers=True,
            color_discrete_map=MTR_LINE_COLORS,
        )
        fig_hourly.update_layout(height=500)
        st.plotly_chart(fig_hourly, use_container_width=True)

        st.subheader("Wait Time Heatmap")
        heatmap_data = hourly_avg.pivot(
            index="line_name", columns="hour", values="time_remaining_minutes"
        )

        fig_heatmap = px.imshow(
            heatmap_data,
            labels=dict(x="Hour", y="Line", color="Avg Wait (min)"),
            title="Wait Time Heatmap by Line and Hour",
            aspect="auto",
        )
        fig_heatmap.update_layout(height=400)
        st.plotly_chart(fig_heatmap, use_container_width=True)

    # Tab 2: Line Analysis
    with tab2:
        st.subheader("Line Comparison")

        line_summary = (
            df_filtered.groupby("line_name")
            .agg(
                {
                    "time_remaining_minutes": [
                        "mean",
                        "std",
                        "var",
                        "min",
                        "max",
                        "count",
                    ]
                }
            )
            .round(2)
        )
        line_summary.columns = [
            "Avg Wait (min)",
            "Std Dev",
            "Variance",
            "Min (min)",
            "Max (min)",
            "Count",
        ]
        line_summary = line_summary.reset_index()

        def count_outliers(group):
            mean = group["time_remaining_minutes"].mean()
            std = group["time_remaining_minutes"].std()
            if pd.isna(std):
                return 0
            return (
                (group["time_remaining_minutes"] > mean + 2 * std)
                | (group["time_remaining_minutes"] < mean - 2 * std)
            ).sum()

        outlier_counts = df_filtered.groupby("line_name").apply(count_outliers)
        line_summary["Outliers (±2 SD)"] = outlier_counts.values

        col1, col2 = st.columns(2)

        with col1:
            fig_bar = px.bar(
                line_summary.sort_values("Avg Wait (min)", ascending=True),
                x="Avg Wait (min)",
                y="line_name",
                orientation="h",
                title="Average Wait Time by Line",
                color="line_name",
                color_discrete_map=MTR_LINE_COLORS,
            )
            fig_bar.update_layout(height=500, showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

        with col2:
            fig_box = px.box(
                df_filtered,
                x="line_name",
                y="time_remaining_minutes",
                title="Wait Time Distribution by Line",
                labels={
                    "line_name": "Line",
                    "time_remaining_minutes": "Wait Time (min)",
                },
                color="line_name",
                color_discrete_map=MTR_LINE_COLORS,
            )
            fig_box.update_layout(height=500, xaxis_tickangle=-45, showlegend=False)
            st.plotly_chart(fig_box, use_container_width=True)

        st.subheader("Line Statistics")
        st.dataframe(
            line_summary.style.background_gradient(
                subset=["Avg Wait (min)"], cmap="Blues"
            ),
            use_container_width=True,
        )

    # Tab 3: Station Analysis
    with tab3:
        st.subheader("Station Analysis")

        # Station selector
        stations = sorted(df_filtered["station_code"].unique())
        selected_station = st.selectbox("Select Station", stations)

        # Station data
        station_data = df_filtered[df_filtered["station_code"] == selected_station]

        if not station_data.empty:
            col1, col2 = st.columns(2)

            with col1:
                station_hourly = (
                    station_data.groupby("hour")["time_remaining_minutes"]
                    .mean()
                    .reset_index()
                )
                fig_station = px.bar(
                    station_hourly,
                    x="hour",
                    y="time_remaining_minutes",
                    title=f"Hourly Wait Pattern at {selected_station}",
                    labels={"hour": "Hour", "time_remaining_minutes": "Avg Wait (min)"},
                )
                st.plotly_chart(fig_station, use_container_width=True)

            with col2:
                if station_data["direction"].nunique() > 1:
                    direction_data = (
                        station_data.groupby("direction")["time_remaining_minutes"]
                        .mean()
                        .reset_index()
                    )
                    fig_dir = px.pie(
                        direction_data,
                        values="time_remaining_minutes",
                        names="direction",
                        title="Wait Time by Direction",
                    )
                    st.plotly_chart(fig_dir, use_container_width=True)
                else:
                    st.info("Only one direction available for this station")

        st.subheader("Top 10 Stations by Average Wait Time")
        station_avg = (
            df_filtered.groupby(["station_code", "line_name"])["time_remaining_minutes"]
            .mean()
            .reset_index()
        )
        station_avg = station_avg.nlargest(10, "time_remaining_minutes")

        fig_top_stations = px.bar(
            station_avg,
            x="time_remaining_minutes",
            y="station_code",
            color="line_name",
            orientation="h",
            title="Top 10 Stations with Longest Wait Times",
            labels={
                "time_remaining_minutes": "Avg Wait (min)",
                "station_code": "Station",
            },
            color_discrete_map=MTR_LINE_COLORS,
        )
        fig_top_stations.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_top_stations, use_container_width=True)

    # Tab 4: Distribution
    with tab4:
        st.subheader("Wait Time Distribution")

        col1, col2 = st.columns(2)

        with col1:
            fig_hist = px.histogram(
                df_filtered,
                x="time_remaining_minutes",
                nbins=50,
                title="Overall Wait Time Distribution",
                labels={"time_remaining_minutes": "Wait Time (min)"},
                marginal="box",
            )
            fig_hist.update_layout(height=400)
            st.plotly_chart(fig_hist, use_container_width=True)

        with col2:
            wait_times = df_filtered["time_remaining_minutes"].sort_values()
            cumulative = wait_times.rank(method="first") / len(wait_times)

            fig_cdf = go.Figure()
            fig_cdf.add_trace(
                go.Scatter(x=wait_times, y=cumulative, mode="lines", name="CDF")
            )
            fig_cdf.update_layout(
                title="Cumulative Distribution of Wait Times",
                xaxis_title="Wait Time (min)",
                yaxis_title="Cumulative Probability",
                height=400,
            )
            st.plotly_chart(fig_cdf, use_container_width=True)

        st.subheader("Wait Time Percentiles")
        percentiles = [10, 25, 50, 75, 90, 95, 99]
        percentile_values = df_filtered["time_remaining_minutes"].quantile(
            [p / 100 for p in percentiles]
        )

        percentile_df = pd.DataFrame(
            {
                "Percentile": [f"{p}th" for p in percentiles],
                "Wait Time (min)": [f"{v:.1f}" for v in percentile_values.values],
            }
        )
        st.dataframe(percentile_df, use_container_width=True)

    # Tab 5: Anomalies
    with tab5:
        st.subheader("Anomaly Detection")
        st.markdown(
            "Identifying unusually long or short wait times based on historical patterns"
        )

        if not df_hourly.empty:
            # Calculate anomalies
            df_hourly["is_anomaly"] = (
                df_hourly["avg_wait_seconds"] > df_hourly["upper_bound_seconds"]
            ) | (df_hourly["avg_wait_seconds"] < df_hourly["lower_bound_seconds"])
            df_hourly["anomaly_type"] = df_hourly.apply(
                lambda x: "Unusually Long"
                if x["avg_wait_seconds"] > x["upper_bound_seconds"]
                else (
                    "Unusually Short"
                    if x["avg_wait_seconds"] < x["lower_bound_seconds"]
                    else "Normal"
                ),
                axis=1,
            )

            anomalies = df_hourly[df_hourly["is_anomaly"]]

            # Anomaly summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Anomalies", len(anomalies))
            with col2:
                long_count = len(
                    anomalies[anomalies["anomaly_type"] == "Unusually Long"]
                )
                st.metric("Unusually Long", long_count)
            with col3:
                short_count = len(
                    anomalies[anomalies["anomaly_type"] == "Unusually Short"]
                )
                st.metric("Unusually Short", short_count)

            if not anomalies.empty:
                fig_anomaly = px.scatter(
                    anomalies,
                    x="hour",
                    y="avg_wait_minutes",
                    color="anomaly_type",
                    facet_col="line_name",
                    facet_col_wrap=3,
                    title="Anomalies by Hour and Line",
                    labels={"avg_wait_minutes": "Avg Wait (min)", "hour": "Hour"},
                )
                fig_anomaly.update_layout(height=600)
                st.plotly_chart(fig_anomaly, use_container_width=True)

                st.subheader("Anomaly Details")
                anomaly_display = anomalies[
                    [
                        "ingestion_date",
                        "hour",
                        "line_name",
                        "station_code",
                        "avg_wait_minutes",
                        "upper_bound_minutes",
                        "lower_bound_minutes",
                        "anomaly_type",
                    ]
                ].sort_values("ingestion_date", ascending=False)
                anomaly_display = anomaly_display.rename(
                    columns={
                        "avg_wait_minutes": "Avg Wait (min)",
                        "upper_bound_minutes": "Upper Bound (min)",
                        "lower_bound_minutes": "Lower Bound (min)",
                    }
                )
                st.dataframe(anomaly_display, use_container_width=True)
            else:
                st.info("No anomalies detected in the selected time period")
        else:
            st.info("Insufficient historical data for anomaly detection")

    # Footer
    st.divider()
    st.markdown(
        """
    <div style="text-align: center; color: #666;">
        <p>MTR Wait Time Analysis Dashboard | Data updated every 30 seconds</p>
        <p>Last updated: {}</p>
    </div>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
