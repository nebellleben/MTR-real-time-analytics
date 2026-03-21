# Dashboard Setup Guide

 This guide explains how to connect Looker Studio to BigQuery and visualize the MTR transit data.

## Prerequisites

- Google Cloud account with BigQuery API enabled
- Looker Studio access (free with Google account)

## Step 1: Connect BigQuery Data Source

 1. Open [Looker Studio](https://lookerstudio.google.com)
 2. Click "Create" → "Data Source"
 3. Select "BigQuery" connector
 4. Choose your Google Cloud project
 5. Select dataset: `mtr_analytics`
  6. Select table: `fact_delays`

## Step 2: Create Dashboard

### Tile 1: Average Wait Time by Line (Categorical)
- **Chart Type**: Bar Chart
- **Dimension**: `line_code`
- **Metric**: `avg_wait_time_seconds`
- **Sort**: Descending by metric
- **Title**: "Average Wait Time by MTR Line"
- **Description**: "Shows average waiting time in seconds for each MTR line"

### Tile 2: Delay Trends Over Time (Temporal)
- **Chart Type**: Time Series Line Chart
- **Dimension**: `ingestion_date` (Date) + `hour`
- **Metric**: `delayed_count`
- **Breakdown**: `line_code`
- **Title**: "Train Delays Over Time"
- **Description**: "Shows number of delayed trains by hour across different MTR lines"

## Step 3: Additional Tiles (Optional)

### Tile 3: Peak Hour Analysis
- **Chart Type**: Heatmap
- **Dimensions**: `hour`, `station_code`
- **Metric**: `total_arrivals`
- **Title**: "Peak Hour Station Activity"

### Tile 4: Delay Distribution
- **Chart Type**: Pie Chart
- **Dimension**: `line_code`
- **Metric**: `delayed_count`
- **Title**: "Delay Distribution by Line"

## Dashboard Filters
- **Date Range**: Last 7 days
- **Line Filter**: Multi-select dropdown
- **Station Filter**: Multi-select dropdown

## Sharing the Dashboard
 1. Click "Share" button (top right)
 2. Click "Share with others"
  3. Add email addresses or 4. Set permissions (View only recommended)
  5. Copy and share the link
  dashboard link

## Refresh Settings
- Auto-refresh: Every 5 minutes (for real-time feel)
- Manual refresh: Click refresh button
