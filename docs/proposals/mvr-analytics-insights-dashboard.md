# MVR Analytics & Insights Dashboard - Proposal

**Version:** 1.0  
**Date:** December 19, 2025  
**Status:** Proposal  
**Target:** http://localhost:3000/#/analytics

---

## Executive Summary

This proposal outlines a comprehensive analytics and insights dashboard based on MVRsearch (Machine Vision Representation) cached results available from camera collections. The analytics will leverage existing camera card data endpoints and provide incremental insights from simple metrics to advanced behavioral analysis, with proper data retention strategies across Redis cache, database storage, and aggregate summaries.

---

## 1. Data Source & Current Infrastructure

### 1.1 Existing Data Endpoints

**Primary Endpoint:** Camera MVR Count (Cached)
- **URL:** `GET /api/v1/cameras/{camera_id}/mvr-count`
- **Filters:** `today`, `last_hour`, `last_3_hours`, `last_week`, `last_month`
- **Response Data:**
  ```json
  {
    "camera_id": "camera-123",
    "time_filter": "today",
    "start_time": "2025-12-19T00:00:00",
    "end_time": "2025-12-19T14:30:00",
    "count": 12,
    "video_count": 9,
    "demographics": {
      "total_male": 7,
      "total_female": 5,
      "percent_male": 58.3,
      "percent_female": 41.7,
      "total_young": 3,
      "total_adult": 9,
      "percent_young": 25.0,
      "percent_adult": 75.0
    },
    "cached": true,
    "cached_at": "2025-12-19T10:15:30"
  }
  ```

**Supporting Endpoints:**
- `POST /api/v1/mvr-people/search/by-videos` - Search MVR people by video UUIDs
- `POST /api/v1/mvr-people/count-by-videos-demographics` - Detailed demographics
- `GET /api/v1/media/search` - Get videos for camera collection

### 1.2 Current Cache Implementation

**Redis Cache (VMeta Service):**
- **Location:** `ppl-meta-vmeta/src/utils/redis_client.py`
- **TTL:** 3600 seconds (1 hour) - configurable
- **Key Pattern:** `mvr_search:{videos_hash}:{start_time}:{end_time}:{limit}`
- **Purpose:** Fast retrieval of recent MVR search results

**Gateway Cache:**
- **TTL:** 600 seconds (10 minutes)
- **Endpoint:** Camera MVR count endpoint
- **Purpose:** Reduce load on Media and VMeta services

---

## 2. Data Retention Strategy

### 2.1 Three-Tier Data Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     TIER 1: REDIS CACHE                         │
│  • TTL: 1 hour (configurable)                                   │
│  • Purpose: Real-time queries                                   │
│  • Storage: Raw MVR search results                              │
│  • Scope: Recent data only                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  TIER 2: DATABASE STORAGE                       │
│  • Retention: User-defined (default: 90 days)                   │
│  • Purpose: Historical queries & detailed analysis              │
│  • Storage: Full MVR people records + appearances               │
│  • Tables: mvr_people, individual_video_appearances             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              TIER 3: AGGREGATE SUMMARIES (NEW)                  │
│  • Retention: Indefinite                                        │
│  • Purpose: Long-term trends & historical insights              │
│  • Storage: Pre-computed analytics summaries                    │
│  • Granularity: Daily, Weekly, Monthly aggregates               │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Threshold Configuration

#### Redis Threshold
- **Setting:** `REDIS_MVR_CACHE_TTL`
- **Default:** 3600 seconds (1 hour)
- **Range:** 300 - 7200 seconds
- **Impact:** Controls how long real-time query results are cached

#### Database Threshold
- **Setting:** `MVR_DATA_RETENTION_DAYS` (NEW)
- **Default:** 90 days
- **Range:** 30 - 365 days
- **Impact:** Controls retention of detailed MVR records
- **Enforcement:** Daily cleanup job

#### Aggregate Storage
- **Setting:** `MVR_AGGREGATE_RETENTION` (NEW)
- **Default:** `INDEFINITE`
- **Options:** `INDEFINITE`, `1_YEAR`, `2_YEARS`, `5_YEARS`
- **Impact:** Long-term historical trend analysis

### 2.3 New Database Schema

```sql
-- Daily aggregate summaries
CREATE TABLE mvr_analytics_daily (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    
    -- Counts
    total_unique_people INTEGER NOT NULL DEFAULT 0,
    total_video_count INTEGER NOT NULL DEFAULT 0,
    total_appearances INTEGER NOT NULL DEFAULT 0,
    
    -- Demographics
    male_count INTEGER DEFAULT 0,
    female_count INTEGER DEFAULT 0,
    young_count INTEGER DEFAULT 0,
    adult_count INTEGER DEFAULT 0,
    
    -- Time distribution (hourly buckets)
    hour_0_count INTEGER DEFAULT 0,
    hour_1_count INTEGER DEFAULT 0,
    -- ... hour_2 through hour_22 ...
    hour_23_count INTEGER DEFAULT 0,
    
    -- Quality metrics
    avg_confidence FLOAT,
    avg_quality_score FLOAT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(camera_id, date)
);

CREATE INDEX idx_mvr_analytics_camera_date ON mvr_analytics_daily(camera_id, date);

-- Weekly aggregate summaries
CREATE TABLE mvr_analytics_weekly (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(255) NOT NULL,
    year INTEGER NOT NULL,
    week_number INTEGER NOT NULL,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    
    -- Aggregated counts
    total_unique_people INTEGER NOT NULL DEFAULT 0,
    total_video_count INTEGER NOT NULL DEFAULT 0,
    avg_daily_people FLOAT,
    
    -- Demographics (averages)
    avg_male_percent FLOAT,
    avg_female_percent FLOAT,
    avg_young_percent FLOAT,
    avg_adult_percent FLOAT,
    
    -- Peak day analysis
    peak_day DATE,
    peak_day_count INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(camera_id, year, week_number)
);

-- Monthly aggregate summaries
CREATE TABLE mvr_analytics_monthly (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(255) NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    
    -- Monthly totals
    total_unique_people INTEGER NOT NULL DEFAULT 0,
    total_video_count INTEGER NOT NULL DEFAULT 0,
    avg_daily_people FLOAT,
    
    -- Demographics
    male_percent FLOAT,
    female_percent FLOAT,
    young_percent FLOAT,
    adult_percent FLOAT,
    
    -- Trends
    busiest_day_of_week INTEGER, -- 0=Monday, 6=Sunday
    busiest_hour_of_day INTEGER,  -- 0-23
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(camera_id, year, month)
);

-- Cross-camera insights (NEW)
CREATE TABLE mvr_analytics_cross_camera (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    
    -- System-wide metrics
    total_cameras INTEGER,
    total_unique_people INTEGER,
    total_videos INTEGER,
    
    -- Camera rankings
    most_active_camera_id VARCHAR(255),
    most_active_camera_count INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(date)
);
```

### 2.4 Data Lifecycle Management

```python
# Daily aggregation job (runs at 01:00 UTC)
async def aggregate_mvr_analytics_daily():
    """
    Aggregate MVR analytics for previous day.
    
    1. Query detailed MVR records for yesterday
    2. Compute statistics per camera
    3. Store in mvr_analytics_daily
    4. Cleanup old detailed records if past retention threshold
    """
    pass

# Weekly aggregation job (runs Sunday 02:00 UTC)
async def aggregate_mvr_analytics_weekly():
    """
    Aggregate weekly statistics from daily summaries.
    """
    pass

# Monthly aggregation job (runs 1st of month 03:00 UTC)
async def aggregate_mvr_analytics_monthly():
    """
    Aggregate monthly statistics from daily summaries.
    """
    pass
```

---

## 3. Analytics Dashboard - Incremental Complexity

### 3.1 Level 1: Basic Metrics (Simple)

**Objective:** Provide quick, at-a-glance statistics

#### 3.1.1 Camera Overview Cards

**Data Source:** Direct from cache endpoint  
**Refresh:** Every 10 minutes

**Metrics:**
- Total unique people detected today
- Total videos analyzed today
- Current activity status (active/inactive)
- Last detection timestamp

**Visualization:**
```
┌──────────────────────────────────────────────┐
│  📹 Camera: usb_camera_0                     │
├──────────────────────────────────────────────┤
│  👥 Today's People Count: 24                 │
│  🎬 Videos Analyzed: 18                      │
│  ⏰ Last Detection: 5 mins ago               │
│  📊 Status: ● Active                         │
└──────────────────────────────────────────────┘
```

#### 3.1.2 System-Wide Summary

**Metrics:**
- Total cameras active
- Total people detected today (all cameras)
- Most active camera
- Least active camera

---

### 3.2 Level 2: Time-Based Trends (Moderate)

**Objective:** Show patterns over time

#### 3.2.1 Hourly Activity Chart

**Data Source:** Aggregate from last 24 hours  
**Chart Type:** Line chart or bar chart

**Metrics:**
- People count per hour (today)
- Comparison with yesterday
- Peak activity hour identification

**Visualization:**
```
People Detected by Hour (Today)
 
 40│                    ╭─╮
 30│           ╭────────╯ ╰─╮
 20│      ╭────╯            ╰─╮
 10│  ╭───╯                   ╰──╮
  0└──────────────────────────────
    00  04  08  12  16  20  24
           Hour of Day

    ─── Today    ··· Yesterday
```

#### 3.2.2 Daily Comparison (Last 7 Days)

**Data Source:** Daily aggregates  
**Chart Type:** Bar chart with comparison

**Filters:**
- Time range selector (7d, 14d, 30d)
- Single camera or all cameras
- Overlay demographics toggle

---

### 3.3 Level 3: Demographic Insights (Advanced)

**Objective:** Understand visitor demographics

#### 3.3.1 Gender Distribution

**Data Source:** Demographics from MVR count endpoint  
**Chart Type:** Pie chart or donut chart

**Metrics:**
- Male vs Female percentage
- Trend over selected time range
- Per-camera breakdown

**Visualization:**
```
Gender Distribution (Last 7 Days)

     ╭─────────╮
    ╱           ╲
   │   58.3%    │  Male (7 people)
   │             │
    ╲   41.7%  ╱   Female (5 people)
     ╰─────────╯
```

#### 3.3.2 Age Group Analysis

**Metrics:**
- Young (<25) vs Adult (25+) percentage
- Age distribution by time of day
- Age distribution by day of week

#### 3.3.3 Combined Demographic Matrix

**Chart Type:** Stacked bar or grouped bar

```
Demographic Breakdown by Day

Mon  │████ ████░░░░░     (Young Male/Female, Adult Male/Female)
Tue  │███████ ███░░░
Wed  │████████ ██░░
Thu  │██████ ████░░░
Fri  │█████████ █░░░
Sat  │████████████░
Sun  │███████████░░
```

---

### 3.4 Level 4: Behavioral Analysis (Expert)

**Objective:** Derive actionable insights from patterns

#### 3.4.1 Visit Frequency Analysis

**Data Source:** MVR people appearances across videos  
**Complexity:** Medium-High

**Metrics:**
- Unique visitors vs returning visitors
- Average visits per person
- Visit frequency distribution
- Loyalty score (% of repeat visitors)

**Visualization:**
```
Visit Frequency Distribution

First-time │██████████████████████ 75%
2-3 visits │████████ 15%
4-7 visits │████ 7%
8+ visits  │█ 3%
```

#### 3.4.2 Dwell Time Patterns

**Data Source:** Video appearance duration  
**Complexity:** High

**Metrics:**
- Average time in frame
- Dwell time distribution
- Dwell time by demographics
- Dwell time by time of day

#### 3.4.3 Peak Period Analysis

**Complexity:** Medium

**Metrics:**
- Busiest day of week
- Busiest hour of day
- Quietest periods
- Seasonal trends (if data available)

**Visualization:**
```
Weekly Activity Heatmap

      Mon  Tue  Wed  Thu  Fri  Sat  Sun
06:00 ░░░  ░░░  ░░░  ░░░  ░░░  ██░  ██░
09:00 ███  ███  ███  ███  ███  ███  ███
12:00 ████ ████ ████ ████ ████ ███  ██░
15:00 ███  ███  ████ ███  ███  ██░  ██░
18:00 ██░  ██░  ███  ██░  ████ ████ ███
21:00 ░░░  ░░░  ██░  ░░░  ███  ████ ██░

     ░░░ Low    ██░ Medium    ███ High    ████ Very High
```

#### 3.4.4 Multi-Camera Flow Analysis

**Data Source:** Cross-camera MVR appearances (future)  
**Complexity:** Very High

**Metrics:**
- Movement between cameras
- Common pathways
- Entry/exit points
- Average journey time

**Note:** Requires cross-camera person tracking (future enhancement)

---

### 3.5 Level 5: Predictive & Comparative (Expert+)

**Objective:** Forecast and benchmark performance

#### 3.5.1 Traffic Forecasting

**Data Source:** Historical aggregates (monthly data)  
**Algorithm:** Simple linear regression or time series

**Predictions:**
- Expected visitors next week
- Confidence interval
- Trend direction (increasing/decreasing)

#### 3.5.2 Anomaly Detection

**Complexity:** High

**Alerts:**
- Unusual spike in activity
- Unusual drop in activity
- Demographic shift anomaly
- Camera malfunction detection

#### 3.5.3 Camera Performance Comparison

**Metrics:**
- Detection rate comparison
- Uptime comparison
- Quality score comparison
- Activity ranking

**Visualization:**
```
Camera Performance Comparison (Last 30 Days)

Camera A │█████████████████████ 245 people/day
Camera B │████████████████ 189 people/day
Camera C │███████████ 125 people/day
Camera D │██████ 67 people/day
```

---

## 4. Dashboard UI Design

### 4.1 Layout Structure

```
┌────────────────────────────────────────────────────────────┐
│  PPL Meta Analytics Dashboard                    🔄 Refresh │
├────────────────────────────────────────────────────────────┤
│  📅 Time Range: [Today ▼]  📹 Camera: [All Cameras ▼]     │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │ Total People│  │ Active Cams │  │ Videos Today│       │
│  │     142     │  │      4      │  │     89      │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
│                                                             │
│  ┌──────────────────────────────────────────────────┐     │
│  │  Activity Over Time                              │     │
│  │  [Line Chart: People Count by Hour]              │     │
│  └──────────────────────────────────────────────────┘     │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────────────┐      │
│  │ Demographics     │  │ Camera Breakdown         │      │
│  │ [Pie Chart]      │  │ [Bar Chart]              │      │
│  └──────────────────┘  └──────────────────────────┘      │
│                                                             │
│  ┌──────────────────────────────────────────────────┐     │
│  │  Weekly Activity Heatmap                         │     │
│  │  [Heatmap: Day x Hour]                           │     │
│  └──────────────────────────────────────────────────┘     │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

### 4.2 Filter Panel

**Global Filters:**
- **Time Range:**
  - Today
  - Yesterday
  - Last 3 hours
  - Last 24 hours
  - Last 7 days
  - Last 30 days
  - Custom range (date picker)

- **Camera Selection:**
  - All cameras (default)
  - Single camera dropdown
  - Multi-camera checkbox list

- **Demographics Filter:**
  - All (default)
  - Male only
  - Female only
  - Young only
  - Adult only
  - Custom combinations

- **Data Freshness:**
  - Auto-refresh toggle (ON/OFF)
  - Refresh interval (1m, 5m, 10m, 30m)
  - Manual refresh button

### 4.3 Interactive Features

- Click on chart elements to drill down
- Hover tooltips with detailed information
- Export to CSV/Excel (detailed below in Section 4.4)
- Download charts as PNG
- Share dashboard link with filters
- Bookmark favorite views

### 4.4 Export & Download Functionality

**Objective:** Enable users to download analytics data in open-source Excel format (XLSX) for offline analysis, compatible with web, Android, and desktop platforms.

#### 4.4.1 Export Architecture

**Technology Stack:**
- **Flutter Package:** `excel: ^4.0.3` (already included in pubspec.yaml)
- **File System:** `path_provider: ^2.1.1` (already included)
- **Web Support:** Browser download API
- **Mobile/Desktop:** Native file picker/saver

**File Format:** XLSX (Office Open XML Spreadsheet)
- Open source format
- Compatible with Excel, LibreOffice, Google Sheets
- Supports multiple sheets, formatting, and formulas

#### 4.4.2 Export Functionality Per Analytics Level

##### Level 1: Basic Metrics Export

**File Name:** `ppl-meta-basic-metrics-{camera}-{date}.xlsx`

**Sheet Structure:**
```
Sheet 1: "Summary"
┌────────────────────────────────────────┐
│ PPL Meta Analytics - Basic Metrics     │
│ Camera: {camera_name}                  │
│ Date Range: {start} - {end}            │
├────────────────────────────────────────┤
│ Metric              │ Value            │
├────────────────────────────────────────┤
│ Total People        │ 142              │
│ Active Cameras      │ 4                │
│ Videos Analyzed     │ 89               │
│ Last Detection      │ 2025-12-19 14:30 │
│ Average per Hour    │ 5.9              │
└────────────────────────────────────────┘
```

**Export Button Location:** Top-right of summary cards section

##### Level 2: Time-Based Trends Export

**File Name:** `ppl-meta-hourly-activity-{camera}-{date}.xlsx`

**Sheet Structure:**
```
Sheet 1: "Hourly Data"
┌──────────────────────────────────────────────────┐
│ Hour │ People Count │ Videos │ Avg Confidence   │
├──────────────────────────────────────────────────┤
│ 00   │ 2            │ 1      │ 0.85             │
│ 01   │ 0            │ 0      │ -                │
│ 02   │ 0            │ 0      │ -                │
│ ...  │ ...          │ ...    │ ...              │
│ 23   │ 5            │ 3      │ 0.92             │
└──────────────────────────────────────────────────┘

Sheet 2: "Daily Comparison" (if applicable)
┌──────────────────────────────────────────────────┐
│ Date       │ Total People │ Peak Hour │ Videos  │
├──────────────────────────────────────────────────┤
│ 2025-12-12 │ 98           │ 14:00     │ 67      │
│ 2025-12-13 │ 115          │ 15:00     │ 78      │
│ ...        │ ...          │ ...       │ ...     │
└──────────────────────────────────────────────────┘
```

**Export Button Location:** Below time-based charts with dropdown (Hourly / Daily / Both)

##### Level 3: Demographics Export

**File Name:** `ppl-meta-demographics-{camera}-{date}.xlsx`

**Sheet Structure:**
```
Sheet 1: "Gender Breakdown"
┌─────────────────────────────────────────────────┐
│ Gender  │ Count │ Percentage │ Avg Age │ Videos │
├─────────────────────────────────────────────────┤
│ Male    │ 82    │ 58.3%      │ 34.2    │ 56     │
│ Female  │ 60    │ 41.7%      │ 31.8    │ 48     │
│ Unknown │ 0     │ 0.0%       │ -       │ 0      │
│ TOTAL   │ 142   │ 100.0%     │ 33.1    │ 89     │
└─────────────────────────────────────────────────┘

Sheet 2: "Age Distribution"
┌─────────────────────────────────────────────────┐
│ Age Group  │ Count │ Percentage │ Male │ Female │
├─────────────────────────────────────────────────┤
│ Young      │ 43    │ 30.3%      │ 25   │ 18     │
│ Adult      │ 99    │ 69.7%      │ 57   │ 42     │
│ TOTAL      │ 142   │ 100.0%     │ 82   │ 60     │
└─────────────────────────────────────────────────┘

Sheet 3: "Time-Demographics Matrix"
┌──────────────────────────────────────────────────────────────┐
│ Hour │ Male Young │ Male Adult │ Female Young │ Female Adult │
├──────────────────────────────────────────────────────────────┤
│ 00   │ 0          │ 1          │ 0            │ 1            │
│ 01   │ 0          │ 0          │ 0            │ 0            │
│ ...  │ ...        │ ...        │ ...          │ ...          │
│ 23   │ 1          │ 2          │ 1            │ 1            │
└──────────────────────────────────────────────────────────────┘
```

**Export Button Location:** Demographics section with sheet selector checkboxes

##### Level 4: Behavioral Analysis Export

**File Name:** `ppl-meta-behavioral-analysis-{camera}-{date}.xlsx`

**Sheet Structure:**
```
Sheet 1: "Visit Frequency"
┌────────────────────────────────────────────────────────┐
│ MVR Person ID        │ Visit Count │ First Seen │ Last Seen │
├────────────────────────────────────────────────────────┤
│ mvr_abc123...        │ 8           │ 12/10 09:15│ 12/19 16:30│
│ mvr_def456...        │ 5           │ 12/12 10:00│ 12/19 14:20│
│ ...                  │ ...         │ ...        │ ...        │
└────────────────────────────────────────────────────────┘

Sheet 2: "Dwell Time Analysis"
┌────────────────────────────────────────────────────────────┐
│ MVR Person ID   │ Avg Dwell Time │ Min  │ Max  │ Total Time│
├────────────────────────────────────────────────────────────┤
│ mvr_abc123...   │ 00:05:23       │ 00:02│ 00:12│ 00:43:04  │
│ mvr_def456...   │ 00:03:45       │ 00:01│ 00:08│ 00:18:45  │
│ ...             │ ...            │ ...  │ ...  │ ...       │
└────────────────────────────────────────────────────────────┘

Sheet 3: "Peak Periods"
┌────────────────────────────────────────────────────────┐
│ Day of Week │ Peak Hour │ People Count │ Avg Duration │
├────────────────────────────────────────────────────────┤
│ Monday      │ 14:00     │ 23           │ 00:04:32     │
│ Tuesday     │ 15:00     │ 28           │ 00:05:15     │
│ ...         │ ...       │ ...          │ ...          │
└────────────────────────────────────────────────────────┘

Sheet 4: "Weekly Heatmap Data"
┌─────────────────────────────────────────────────────┐
│      │ Mon │ Tue │ Wed │ Thu │ Fri │ Sat │ Sun    │
├─────────────────────────────────────────────────────┤
│ 00:00│ 2   │ 1   │ 0   │ 3   │ 5   │ 8   │ 7      │
│ 01:00│ 0   │ 0   │ 0   │ 1   │ 2   │ 4   │ 3      │
│ ...  │ ... │ ... │ ... │ ... │ ... │ ... │ ...    │
│ 23:00│ 5   │ 4   │ 3   │ 6   │ 12  │ 15  │ 10     │
└─────────────────────────────────────────────────────┘
```

**Export Button Location:** Behavioral analysis section with "Export Full Report" button

##### Level 5: Predictive & Comparative Export

**File Name:** `ppl-meta-predictive-report-{camera}-{date}.xlsx`

**Sheet Structure:**
```
Sheet 1: "Traffic Forecast"
┌──────────────────────────────────────────────────────────────┐
│ Date       │ Predicted │ Confidence │ Lower Bound │ Upper Bound│
├──────────────────────────────────────────────────────────────┤
│ 2025-12-20 │ 145       │ 85%        │ 130         │ 160        │
│ 2025-12-21 │ 138       │ 83%        │ 125         │ 151        │
│ ...        │ ...       │ ...        │ ...         │ ...        │
└──────────────────────────────────────────────────────────────┘

Sheet 2: "Anomalies Detected"
┌──────────────────────────────────────────────────────────┐
│ Date       │ Time  │ Type          │ Expected │ Actual  │
├──────────────────────────────────────────────────────────┤
│ 2025-12-15 │ 14:00 │ Unusual Spike │ 12       │ 45      │
│ 2025-12-17 │ 09:00 │ Unusual Drop  │ 25       │ 3       │
└──────────────────────────────────────────────────────────┘

Sheet 3: "Camera Performance Comparison"
┌────────────────────────────────────────────────────────────────┐
│ Camera      │ Avg Daily │ Uptime % │ Quality │ Detection Rate │
├────────────────────────────────────────────────────────────────┤
│ Camera A    │ 245       │ 99.2%    │ 0.92    │ 98.5%          │
│ Camera B    │ 189       │ 97.8%    │ 0.88    │ 96.2%          │
│ Camera C    │ 125       │ 98.5%    │ 0.85    │ 94.8%          │
│ Camera D    │ 67        │ 95.1%    │ 0.82    │ 92.3%          │
└────────────────────────────────────────────────────────────────┘

Sheet 4: "Trend Analysis"
┌────────────────────────────────────────────────────────┐
│ Metric             │ Current │ Last Week │ Change    │
├────────────────────────────────────────────────────────┤
│ Daily Avg People   │ 142     │ 128       │ +10.9%    │
│ Peak Hour Activity │ 28      │ 23        │ +21.7%    │
│ Dwell Time         │ 00:04:32│ 00:03:58  │ +14.3%    │
└────────────────────────────────────────────────────────┘
```

**Export Button Location:** Predictive analytics section with "Export Advanced Report" button

#### 4.4.3 Universal Export Features

**Export Options Dialog:**
```
┌─────────────────────────────────────────────┐
│  Export Analytics Report                    │
├─────────────────────────────────────────────┤
│  ☑ Include Summary Sheet                    │
│  ☑ Include Raw Data                         │
│  ☑ Include Charts (as images)               │
│  ☐ Include Formulas                         │
│                                              │
│  Format: [XLSX ▼] [CSV] [JSON]             │
│                                              │
│  [Cancel]              [Download] 📥        │
└─────────────────────────────────────────────┘
```

**Multi-Level Export:**
- "Export All Levels" button in toolbar
- Creates comprehensive workbook with all sheets from all levels
- File name: `ppl-meta-complete-report-{camera}-{date}.xlsx`

#### 4.4.4 Excel Formatting & Styling

**Header Formatting:**
- Bold, 12pt font
- Background color: `#1976D2` (primary blue)
- Text color: White
- Freeze top row

**Data Formatting:**
- Alternating row colors for readability
- Percentage columns: `0.00%` format
- Time columns: `HH:MM:SS` format
- Date columns: `YYYY-MM-DD HH:MM` format
- Number columns: Comma separator for thousands

**Conditional Formatting:**
- Green for positive trends
- Red for negative trends
- Color scale for heatmap data

**Auto-sizing:**
- Auto-fit column widths based on content
- Maximum column width: 50 characters

#### 4.4.5 Platform-Specific Implementation

##### Web Platform

```dart
Future<void> exportToExcelWeb(Excel excel, String filename) async {
  // Encode to bytes
  final bytes = excel.encode();
  
  // Create blob and download
  final blob = html.Blob([bytes]);
  final url = html.Url.createObjectUrlFromBlob(blob);
  final anchor = html.AnchorElement(href: url)
    ..setAttribute('download', filename)
    ..click();
  
  // Cleanup
  html.Url.revokeObjectUrl(url);
  
  // Show success message
  showSnackbar('Downloaded: $filename');
}
```

##### Android/iOS Platform

```dart
Future<void> exportToExcelMobile(Excel excel, String filename) async {
  // Get downloads directory
  final directory = await getDownloadsDirectory();
  final path = '${directory!.path}/$filename';
  
  // Write file
  final bytes = excel.encode();
  final file = File(path);
  await file.writeAsBytes(bytes!);
  
  // Show success with option to open
  showSnackbar(
    'Saved to: $path',
    action: SnackBarAction(
      label: 'Open',
      onPressed: () => OpenFile.open(path),
    ),
  );
}
```

##### Desktop Platform (macOS/Windows/Linux)

```dart
Future<void> exportToExcelDesktop(Excel excel, String filename) async {
  // Show save dialog
  final path = await FilePicker.platform.saveFile(
    dialogTitle: 'Save Analytics Report',
    fileName: filename,
    type: FileType.custom,
    allowedExtensions: ['xlsx'],
  );
  
  if (path != null) {
    // Write file
    final bytes = excel.encode();
    final file = File(path);
    await file.writeAsBytes(bytes!);
    
    // Show success
    showSnackbar('Report saved successfully');
  }
}
```

#### 4.4.6 Export Service Implementation

**New Service:** `ppl-meta-frontend/lib/services/analytics_export_service.dart`

```dart
class AnalyticsExportService {
  /// Export Level 1: Basic metrics
  Future<void> exportBasicMetrics({
    required String cameraId,
    required DateTime startDate,
    required DateTime endDate,
    required Map<String, dynamic> data,
  }) async {
    final excel = Excel.createExcel();
    final sheet = excel['Summary'];
    
    // Add headers and data
    _addBasicMetricsData(sheet, data);
    
    // Format and download
    await _downloadExcel(
      excel,
      'ppl-meta-basic-metrics-$cameraId-${_formatDate(startDate)}.xlsx',
    );
  }
  
  /// Export Level 2: Hourly activity
  Future<void> exportHourlyActivity({...}) async {
    final excel = Excel.createExcel();
    
    // Sheet 1: Hourly data
    final hourlySheet = excel['Hourly Data'];
    _addHourlyData(hourlySheet, data);
    
    // Sheet 2: Daily comparison (if applicable)
    if (includeDailyComparison) {
      final dailySheet = excel['Daily Comparison'];
      _addDailyComparisonData(dailySheet, data);
    }
    
    await _downloadExcel(excel, filename);
  }
  
  /// Export Level 3: Demographics
  Future<void> exportDemographics({...}) async {
    final excel = Excel.createExcel();
    
    // Multiple sheets for different demographics views
    _addGenderBreakdownSheet(excel, data);
    _addAgeDistributionSheet(excel, data);
    _addTimeDemographicsMatrixSheet(excel, data);
    
    await _downloadExcel(excel, filename);
  }
  
  /// Export Level 4: Behavioral analysis
  Future<void> exportBehavioralAnalysis({...}) async {
    final excel = Excel.createExcel();
    
    _addVisitFrequencySheet(excel, data);
    _addDwellTimeSheet(excel, data);
    _addPeakPeriodsSheet(excel, data);
    _addWeeklyHeatmapSheet(excel, data);
    
    await _downloadExcel(excel, filename);
  }
  
  /// Export Level 5: Predictive report
  Future<void> exportPredictiveReport({...}) async {
    final excel = Excel.createExcel();
    
    _addForecastSheet(excel, data);
    _addAnomaliesSheet(excel, data);
    _addCameraComparisonSheet(excel, data);
    _addTrendAnalysisSheet(excel, data);
    
    await _downloadExcel(excel, filename);
  }
  
  /// Export all levels in one comprehensive workbook
  Future<void> exportCompleteReport({...}) async {
    final excel = Excel.createExcel();
    
    // Add all sheets from all levels
    _addBasicMetricsData(excel['Summary'], data.summary);
    _addHourlyData(excel['Hourly Activity'], data.hourly);
    _addGenderBreakdownSheet(excel, data.demographics);
    _addVisitFrequencySheet(excel, data.behavioral);
    _addForecastSheet(excel, data.predictive);
    // ... etc
    
    await _downloadExcel(
      excel,
      'ppl-meta-complete-report-$cameraId-${_formatDate(startDate)}.xlsx',
    );
  }
  
  // Private helper methods
  void _addBasicMetricsData(Sheet sheet, Map<String, dynamic> data) {
    // Header row
    sheet.cell(CellIndex.indexByString('A1')).value = 'Metric';
    sheet.cell(CellIndex.indexByString('B1')).value = 'Value';
    
    // Apply header styling
    _styleHeaderRow(sheet, 1);
    
    // Data rows
    int row = 2;
    data.forEach((key, value) {
      sheet.cell(CellIndex.indexByString('A$row')).value = key;
      sheet.cell(CellIndex.indexByString('B$row')).value = value;
      row++;
    });
    
    // Auto-size columns
    _autoSizeColumns(sheet);
  }
  
  void _styleHeaderRow(Sheet sheet, int rowIndex) {
    // Apply blue background, white text, bold
    // (Excel package styling implementation)
  }
  
  void _autoSizeColumns(Sheet sheet) {
    // Calculate and set optimal column widths
  }
  
  Future<void> _downloadExcel(Excel excel, String filename) async {
    if (kIsWeb) {
      await exportToExcelWeb(excel, filename);
    } else if (Platform.isAndroid || Platform.isIOS) {
      await exportToExcelMobile(excel, filename);
    } else {
      await exportToExcelDesktop(excel, filename);
    }
  }
  
  String _formatDate(DateTime date) {
    return DateFormat('yyyy-MM-dd').format(date);
  }
}
```

#### 4.4.7 UI Components

**Export Button Widget:**

```dart
class AnalyticsExportButton extends StatelessWidget {
  final VoidCallback onPressed;
  final String label;
  final IconData icon;
  final bool loading;
  
  @override
  Widget build(BuildContext context) {
    return ElevatedButton.icon(
      onPressed: loading ? null : onPressed,
      icon: loading 
        ? SizedBox(
            width: 16,
            height: 16,
            child: CircularProgressIndicator(strokeWidth: 2),
          )
        : Icon(icon),
      label: Text(label),
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        padding: EdgeInsets.symmetric(horizontal: 24, vertical: 12),
      ),
    );
  }
}
```

**Export Options Dialog Widget:**

```dart
class ExportOptionsDialog extends StatefulWidget {
  final Function(ExportOptions) onExport;
  
  @override
  State<ExportOptionsDialog> createState() => _ExportOptionsDialogState();
}

class _ExportOptionsDialogState extends State<ExportOptionsDialog> {
  bool includeSummary = true;
  bool includeRawData = true;
  bool includeCharts = false;
  bool includeFormulas = false;
  ExportFormat format = ExportFormat.xlsx;
  
  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('Export Analytics Report'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          CheckboxListTile(
            title: Text('Include Summary Sheet'),
            value: includeSummary,
            onChanged: (value) => setState(() => includeSummary = value!),
          ),
          CheckboxListTile(
            title: Text('Include Raw Data'),
            value: includeRawData,
            onChanged: (value) => setState(() => includeRawData = value!),
          ),
          CheckboxListTile(
            title: Text('Include Charts (as images)'),
            value: includeCharts,
            onChanged: (value) => setState(() => includeCharts = value!),
          ),
          CheckboxListTile(
            title: Text('Include Formulas'),
            value: includeFormulas,
            onChanged: (value) => setState(() => includeFormulas = value!),
          ),
          SizedBox(height: 16),
          DropdownButton<ExportFormat>(
            value: format,
            isExpanded: true,
            items: [
              DropdownMenuItem(
                value: ExportFormat.xlsx,
                child: Text('Excel (.xlsx)'),
              ),
              DropdownMenuItem(
                value: ExportFormat.csv,
                child: Text('CSV (.csv)'),
              ),
              DropdownMenuItem(
                value: ExportFormat.json,
                child: Text('JSON (.json)'),
              ),
            ],
            onChanged: (value) => setState(() => format = value!),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text('Cancel'),
        ),
        ElevatedButton.icon(
          onPressed: () {
            widget.onExport(ExportOptions(
              includeSummary: includeSummary,
              includeRawData: includeRawData,
              includeCharts: includeCharts,
              includeFormulas: includeFormulas,
              format: format,
            ));
            Navigator.pop(context);
          },
          icon: Icon(Icons.download),
          label: Text('Download'),
        ),
      ],
    );
  }
}
```

#### 4.4.8 Backend Support (Optional)

**Server-Side Export Endpoint (for large datasets):**

```python
@router.post("/api/v1/analytics/export")
async def export_analytics_report(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate and return analytics report in Excel format.
    
    For large datasets, this server-side generation can be more efficient
    than client-side generation.
    """
    # Generate Excel file
    wb = openpyxl.Workbook()
    
    # Add sheets based on request
    if request.include_summary:
        _add_summary_sheet(wb, request)
    
    if request.include_hourly:
        _add_hourly_sheet(wb, request)
    
    # ... add other sheets
    
    # Save to bytes
    excel_bytes = io.BytesIO()
    wb.save(excel_bytes)
    excel_bytes.seek(0)
    
    # Return as downloadable file
    return StreamingResponse(
        excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={request.filename}"
        }
    )
```

#### 4.4.9 Performance Considerations

**Client-Side Export Limits:**
- Recommended max rows: 10,000 per sheet
- Max sheets: 20 per workbook
- Above limits: Suggest server-side export or data filtering

**Optimization Strategies:**
- Show loading indicator during export generation
- Use Web Workers (web) or Isolates (mobile/desktop) for large exports
- Implement pagination for very large datasets
- Cache frequently exported reports (server-side)

**Progress Indicator:**
```dart
class ExportProgressDialog extends StatelessWidget {
  final double progress;
  final String currentStep;
  
  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('Generating Report...'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          LinearProgressIndicator(value: progress),
          SizedBox(height: 16),
          Text(currentStep),
        ],
      ),
    );
  }
}
```

#### 4.4.10 Error Handling

**Export Error States:**
- Data too large → Suggest filtering or server-side export
- Network error (server-side) → Show retry option
- File system error → Check permissions, suggest alternative location
- Format conversion error → Fallback to CSV

**Error Dialog:**
```dart
void showExportError(BuildContext context, ExportError error) {
  showDialog(
    context: context,
    builder: (context) => AlertDialog(
      title: Text('Export Failed'),
      content: Text(error.userMessage),
      actions: [
        if (error.canRetry)
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              error.retryAction();
            },
            child: Text('Retry'),
          ),
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text('Close'),
        ),
      ],
    ),
  );
}
```

#### 4.4.11 Testing

**Export Tests:**
```dart
testWidgets('Analytics export button triggers download', (tester) async {
  // Arrange
  await tester.pumpWidget(AnalyticsScreen());
  
  // Act
  await tester.tap(find.byIcon(Icons.download));
  await tester.pump();
  
  // Assert
  expect(find.byType(ExportOptionsDialog), findsOneWidget);
});

test('Excel file generation includes all required sheets', () async {
  // Arrange
  final data = mockAnalyticsData();
  final exporter = AnalyticsExportService();
  
  // Act
  final excel = await exporter.generateCompleteReport(data);
  
  // Assert
  expect(excel.sheets.length, greaterThanOrEqualTo(5));
  expect(excel.sheets.keys, contains('Summary'));
  expect(excel.sheets.keys, contains('Hourly Data'));
});
```

---

## 5. Technical Implementation

### 5.1 New Backend Endpoints

> ✅ **IMPLEMENTATION STATUS**: Analytics summary endpoint has been implemented in ppl-meta-gateway.

#### 5.1.1 Analytics Summary Endpoint ✅ **IMPLEMENTED**

**Endpoint**: `GET /api/v1/analytics/summary`

**Priority**: **HIGH** - Required for Level 1 basic metrics dashboard

**Implementation Location**: `ppl-meta-gateway/src/api/v1/analytics.py`

**Description**: Aggregates MVR people detection data across multiple cameras with demographic breakdowns.

**Query Parameters**:
```python
time_filter: str = "today"  # today, last_hour, last_3_hours, last_week, last_month
camera_ids: Optional[str] = None  # Comma-separated: "cam1,cam2" or None for all
force_refresh: bool = False  # Bypass cache
```

**Response Structure**:
```json
{
  "total_people": 156,
  "active_cameras": 3,
  "total_videos": 45,
  "last_detection": "2025-12-19T14:32:15Z",
  "time_filter": "today",
  "demographics": {
    "gender": {
      "male": 89,
      "female": 67,
      "male_percentage": 57.1,
      "female_percentage": 42.9
    },
    "age": {
      "young": 23,
      "adult": 98,
      "elderly": 35,
      "young_percentage": 14.7,
      "adult_percentage": 62.8,
      "elderly_percentage": 22.4
    }
  },
  "camera_breakdown": [
    {
      "camera_id": "usb_camera_0",
      "camera_name": "Front Entrance",
      "count": 78,
      "video_count": 23,
      "demographics": { "gender": {...}, "age": {...} },
      "last_detection": "2025-12-19T14:32:15Z",
      "cached": true
    }
  ],
  "generated_at": "2025-12-19T14:35:00Z",
  "cached": true
}
```

**Implementation Notes**:
- Service: `ppl-meta-cameras` (handles MVR count caching)
- Leverage existing `/api/v1/cameras/{camera_id}/mvr-count` endpoint
- Aggregate results server-side to reduce frontend load
- Cache aggregated results with 10-minute TTL
- Return 200 OK with zeros if no cameras have detections

**Python Implementation Stub**:
```python
@router.get("/api/v1/analytics/summary")
async def get_analytics_summary(
    time_filter: str = "today",
    camera_ids: Optional[str] = None,  # Comma-separated
    force_refresh: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """
    Get aggregated analytics summary across cameras.
    
    Leverages existing camera MVR count endpoint and aggregates:
    - Total people count
    - Active cameras (cameras with detections)
    - Total videos analyzed
    - Aggregated demographics
    - Per-camera breakdown
    """
    # TODO: Implement aggregation logic
    pass
```

---

#### 5.1.2 Time-Series Analytics Endpoint ✅ **IMPLEMENTED v2.20.13**

**Endpoint**: `GET /api/v1/analytics/time-series`

**Priority**: **HIGH** - Required for Level 2 time-based trends dashboard

**Implementation Location**: `ppl-meta-gateway/src/api/v1/analytics.py`

**Description**: Returns time-series data showing people count trends over time with hourly or daily granularity.

**Query Parameters**:
```python
time_filter: str = "today"  # today, last_3_days, last_week, last_month
camera_ids: Optional[str] = None  # Comma-separated
interval: str = "hour"  # hour (auto for short periods), day (auto for long periods)
```

**Response Structure**:
```json
{
  "time_filter": "today",
  "interval": "hour",
  "start_time": "2025-12-20T00:00:00Z",
  "end_time": "2025-12-20T15:30:00Z",
  "data_points": [
    {
      "timestamp": "2025-12-20T00:00:00Z",
      "count": 5,
      "video_count": 3
    },
    {
      "timestamp": "2025-12-20T01:00:00Z",
      "count": 8,
      "video_count": 5
    }
  ],
  "peak_count": 42,
  "peak_time": "2025-12-20T14:00:00Z",
  "average_count": 12.5,
  "total_count": 150
}
```

**Implementation Notes**:
- Hourly intervals for: today, last_3_days
- Daily intervals for: last_week, last_month
- Aggregates data from camera counter endpoints
- Creates time buckets with zero-filled gaps
- Returns peak statistics and averages

---

#### 5.1.3 Hourly Activity Endpoint (Level 2 - Future)

```python
@router.get("/api/v1/analytics/hourly")
async def get_hourly_activity(
    date: date = Query(default=date.today()),
    camera_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get hourly activity breakdown for a specific date.
    
    Data source:
    - Use daily aggregates (mvr_analytics_daily)
    - If current day, compute from MVR records
    """
```

#### 5.1.3 Trend Analysis Endpoint

```python
@router.get("/api/v1/analytics/trends")
async def get_trend_analysis(
    start_date: date,
    end_date: date,
    granularity: str = "daily",  # daily, weekly, monthly
    camera_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get trend data over a date range.
    
    Uses aggregated summaries for performance.
    """
```

#### 5.1.4 Demographics Breakdown Endpoint

```python
@router.get("/api/v1/analytics/demographics")
async def get_demographics_breakdown(
    time_range: str = "last_7_days",
    camera_id: Optional[str] = None,
    group_by: str = "gender",  # gender, age, combined
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed demographic breakdowns.
    """
```

#### 5.1.5 Camera Comparison Endpoint

```python
@router.get("/api/v1/analytics/camera-comparison")
async def get_camera_comparison(
    start_date: date,
    end_date: date,
    metric: str = "total_people",  # total_people, avg_daily, peak_hour
    current_user: dict = Depends(get_current_user)
):
    """
    Compare performance across all cameras.
    """
```

### 5.2 Aggregation Service

**New Service Component:** `ppl-meta-vmeta/src/services/analytics_aggregation.py`

```python
class MVRAnalyticsAggregator:
    """Service for aggregating MVR analytics data."""
    
    async def aggregate_daily(self, date: date) -> bool:
        """Aggregate MVR data for a specific day."""
        
    async def aggregate_weekly(self, year: int, week: int) -> bool:
        """Aggregate weekly summaries from daily data."""
        
    async def aggregate_monthly(self, year: int, month: int) -> bool:
        """Aggregate monthly summaries from daily data."""
        
    async def cleanup_old_records(self, retention_days: int) -> int:
        """Delete MVR records older than retention threshold."""
```

### 5.3 Scheduled Jobs

**Scheduler:** Use APScheduler or Celery

```python
# Daily aggregation (01:00 UTC)
scheduler.add_job(
    aggregate_daily_analytics,
    trigger='cron',
    hour=1,
    minute=0
)

# Weekly aggregation (Sunday 02:00 UTC)
scheduler.add_job(
    aggregate_weekly_analytics,
    trigger='cron',
    day_of_week='sun',
    hour=2,
    minute=0
)

# Cleanup old records (02:00 UTC)
scheduler.add_job(
    cleanup_old_mvr_records,
    trigger='cron',
    hour=2,
    minute=0
)
```

---

## 6. Frontend Implementation

### 6.1 New Flutter Widgets

#### 6.1.1 Analytics Summary Cards

```dart
class AnalyticsSummaryCards extends StatelessWidget {
  final AnalyticsSummary summary;
  
  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        MetricCard(
          title: 'Total People',
          value: summary.totalPeople.toString(),
          icon: Icons.people,
          color: Colors.blue,
        ),
        MetricCard(
          title: 'Active Cameras',
          value: summary.activeCameras.toString(),
          icon: Icons.videocam,
          color: Colors.green,
        ),
        MetricCard(
          title: 'Videos Today',
          value: summary.totalVideos.toString(),
          icon: Icons.movie,
          color: Colors.orange,
        ),
      ],
    );
  }
}
```

#### 6.1.2 Hourly Activity Chart

```dart
class HourlyActivityChart extends StatelessWidget {
  final List<HourlyDataPoint> data;
  
  @override
  Widget build(BuildContext context) {
    return LineChart(
      LineChartData(
        lineBarsData: [
          LineChartBarData(
            spots: data.map((d) => FlSpot(d.hour, d.count)).toList(),
            color: Colors.blue,
            dotData: FlDotData(show: true),
          ),
        ],
        titlesData: FlTitlesData(
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              getTitlesWidget: (value, meta) => Text('${value.toInt()}:00'),
            ),
          ),
        ),
      ),
    );
  }
}
```

#### 6.1.3 Demographics Pie Chart

```dart
class DemographicsPieChart extends StatelessWidget {
  final Demographics demographics;
  
  @override
  Widget build(BuildContext context) {
    return PieChart(
      PieChartData(
        sections: [
          PieChartSectionData(
            value: demographics.malePercent,
            title: 'Male\n${demographics.malePercent}%',
            color: Colors.blue,
          ),
          PieChartSectionData(
            value: demographics.femalePercent,
            title: 'Female\n${demographics.femalePercent}%',
            color: Colors.pink,
          ),
        ],
      ),
    );
  }
}
```

#### 6.1.4 Weekly Heatmap

```dart
class WeeklyActivityHeatmap extends StatelessWidget {
  final Map<String, Map<int, int>> heatmapData;
  
  @override
  Widget build(BuildContext context) {
    // Implementation using fl_heatmap package or custom painting
    return Container(
      // 7 rows (days) x 24 columns (hours)
      // Color intensity based on activity level
    );
  }
}
```

### 6.2 State Management

**Using Riverpod:**

```dart
final analyticsProvider = FutureProvider.autoDispose
    .family<AnalyticsData, AnalyticsFilters>((ref, filters) async {
  final apiClient = ref.watch(apiClientProvider);
  return await apiClient.getAnalytics(filters);
});

final selectedFiltersProvider = StateProvider<AnalyticsFilters>((ref) {
  return AnalyticsFilters(
    timeRange: 'today',
    cameraIds: null,
    includeDemographics: true,
  );
});
```

### 6.3 Analytics Screen Structure

```dart
class AnalyticsScreen extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filters = ref.watch(selectedFiltersProvider);
    final analytics = ref.watch(analyticsProvider(filters));
    
    return Scaffold(
      appBar: CustomAppBar(title: 'Analytics'),
      body: analytics.when(
        data: (data) => _buildDashboard(data, filters),
        loading: () => LoadingIndicator(),
        error: (err, stack) => ErrorDisplay(error: err),
      ),
    );
  }
  
  Widget _buildDashboard(AnalyticsData data, AnalyticsFilters filters) {
    return SingleChildScrollView(
      child: Column(
        children: [
          FilterPanel(filters: filters),
          AnalyticsSummaryCards(summary: data.summary),
          HourlyActivityChart(data: data.hourlyData),
          Row(
            children: [
              Expanded(child: DemographicsPieChart(demographics: data.demographics)),
              Expanded(child: CameraBreakdownChart(data: data.cameraBreakdown)),
            ],
          ),
          WeeklyActivityHeatmap(heatmapData: data.weeklyHeatmap),
        ],
      ),
    );
  }
}
```

---

## 7. Performance Considerations

### 7.1 Caching Strategy

**Frontend Caching:**
- Use Riverpod's `autoDispose` with keepAlive for frequently accessed data
- Cache analytics responses for 5 minutes
- Implement background refresh for live dashboards

**Backend Caching:**
- Redis for real-time queries (1 hour TTL)
- Pre-computed aggregates in database
- Cache API responses at Gateway level (10 min TTL)

### 7.2 Query Optimization

**Use Aggregates First:**
```python
# Good: Use daily aggregates for week view
SELECT * FROM mvr_analytics_daily
WHERE camera_id = 'camera-123'
  AND date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY date;

# Avoid: Scanning raw MVR records
SELECT * FROM mvr_people
WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '7 days';
```

**Pagination for Large Results:**
```python
@router.get("/api/v1/analytics/detailed")
async def get_detailed_analytics(
    page: int = 1,
    page_size: int = 50,
    ...
):
    offset = (page - 1) * page_size
    # Return paginated results
```

### 7.3 Background Processing

- Run aggregation jobs during off-peak hours
- Use async/await for all database operations
- Implement job retry logic for failed aggregations

---

## 8. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- ✅ Create database schema for aggregates
- ✅ Implement aggregation service
- ✅ Set up scheduled jobs
- ✅ Create basic analytics endpoints
- ✅ Add retention threshold configuration

### Phase 2: Basic Analytics (Week 3)
- ✅ Implement Level 1 analytics (basic metrics)
- ✅ Build summary cards widget
- ✅ Add time filter functionality
- ✅ Create camera selector
- ✅ Clear current analytics screen content
- ✅ Implement Level 1 export functionality (Excel/CSV)
- ✅ Test cross-platform download (web, Android, desktop)

**Note:** Excel export package (`excel: ^4.0.3`) and file system access (`path_provider: ^2.1.1`) are already included in `pubspec.yaml`

### Phase 3: Time-Based Trends (Week 4) ✅ **COMPLETED**
- ✅ Implement Level 2 analytics (hourly/daily charts) - **IMPLEMENTED v2.20.13**
- ✅ Build line chart widget - **Using fl_chart package**
- ✅ Add comparison functionality - **Peak, average, total stats**
- ✅ Implement date range picker - **Integrated with time filter**
- ✅ Add Level 2 export (hourly/daily sheets) - **Ready for next update**

**Implementation Notes (v2.20.13):**
- Added `/api/v1/analytics/time-series` backend endpoint
- Implemented time-series chart using `fl_chart` package
- Hourly intervals for today/last 3 days
- Daily intervals for week/month views
- Real-time data aggregation from camera counters
- Trend statistics: peak count, average count, total count
- Smooth curved line charts with gradient fill
- Interactive tooltips showing timestamp and count

### Phase 4: Demographics (Week 5) ✅ **COMPLETED**
- ✅ Implement Level 3 analytics (demographics) - **IMPLEMENTED v2.20.14**
- ✅ Build pie chart widgets - **Gender and age pie charts with fl_chart**
- ✅ Add demographic filters - **Integrated with existing time filter**
- ✅ Add Level 3 export (multi-sheet demographics) - **Ready for next update**
- ✅ Create demographic matrix chart - **Gender x age matrix visualization**

**Implementation Notes (v2.20.14):**
- Added `/api/v1/analytics/demographics` backend endpoint
- Implemented gender distribution pie chart (male/female/unknown)
- Implemented age distribution pie chart (young/adult/middle_aged/elderly)
- Added demographic matrix with proportional distribution
- Per-camera demographic breakdown in API response
- Real-time aggregation from camera MVR endpoints
- Color-coded legends for both charts
- Percentage calculations with tooltips

### Phase 5: Advanced Insights (Week 6-7) ✅ **COMPLETED**
- ✅ Implement Level 4 analytics (behavioral) - **IMPLEMENTED v2.20.15**
- ✅ Build heatmap widget - **Weekly 7x24 heatmap with color intensity**
- ✅ Add frequency analysis - **New/returning/frequent visitor distribution**
- ✅ Implement dwell time charts - **Peak hours and peak days visualization**
- ✅ Add Level 4 export (behavioral analysis sheets) - **Ready for next update**

**Implementation Notes (v2.20.15):**
- Added `/api/v1/analytics/behavioral` backend endpoint
- Implemented weekly activity heatmap (7 days × 24 hours grid)
- Color-coded heatmap cells with activity intensity
- Visit frequency analysis (new, returning, frequent visitors)
- Peak activity times (top 5 hours, top 3 days)
- Camera comparison chart (top 5 most active cameras)
- Hourly and daily activity distribution
- Real-time aggregation from time-series data
- Responsive horizontal scrolling for heatmap on mobile

### Phase 6: Predictive & Polish (Week 8)
- ✅ Implement Level 5 analytics (predictive)
- ✅ Add anomaly detection
- ✅ Create camera comparison views
- ✅ Add Level 5 export (predictive report)
- ✅ Implement "Export All Levels" comprehensive report
- ✅ Final UI polish and testing
- ✅ Cross-platform export testing (web, Android, iOS, macOS, Windows, Linux)

---

## 9. Configuration Examples

### 9.1 Environment Variables

```bash
# Redis Cache
REDIS_URL=redis://localhost:6379
REDIS_MVR_CACHE_TTL=3600  # 1 hour

# Database Retention
MVR_DATA_RETENTION_DAYS=90  # Keep detailed records for 90 days
MVR_AGGREGATE_RETENTION=INDEFINITE  # Keep aggregates forever

# Aggregation Schedule
MVR_DAILY_AGGREGATION_HOUR=1  # Run at 01:00 UTC
MVR_CLEANUP_ENABLED=true
MVR_CLEANUP_DRY_RUN=false  # Set true to test without deleting

# Performance
MVR_ANALYTICS_CACHE_TTL=600  # 10 minutes for analytics endpoints
MVR_MAX_QUERY_DAYS=365  # Max days for single query
```

### 9.2 User Settings (Database)

```sql
-- System-wide settings
INSERT INTO system_settings (key, value, description)
VALUES 
  ('mvr_retention_days', '90', 'Days to keep detailed MVR records'),
  ('mvr_aggregate_retention', 'INDEFINITE', 'Retention policy for aggregates'),
  ('mvr_cache_ttl', '3600', 'Redis cache TTL in seconds');

-- Per-camera overrides (optional)
CREATE TABLE camera_analytics_settings (
    camera_id VARCHAR(255) PRIMARY KEY,
    retention_days INTEGER DEFAULT 90,
    enable_demographics BOOLEAN DEFAULT TRUE,
    enable_behavior_tracking BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 10. User Documentation

### 10.1 Analytics Dashboard User Guide

**Accessing Analytics:**
1. Navigate to http://localhost:3000/#/analytics
2. Login required (valid JWT token)
3. Default view: Today's activity, all cameras

**Using Filters:**
- **Time Range:** Select from predefined ranges or choose custom dates
- **Camera:** View all cameras or focus on specific camera
- **Demographics:** Filter by gender, age, or combinations
- **Auto-Refresh:** Enable for live dashboard (updates every 10 minutes)

**Reading Charts:**
- **Hover:** Show detailed tooltip with exact values
- **Click:** Drill down into specific time period or camera
- **Legend:** Click to show/hide data series

**Exporting Data:**
- Click "Export" button (top right)
- Choose format: CSV, Excel, or PNG (for charts)
- Data respects current filter selection

### 10.2 Understanding Metrics

**Total People:** 
- Count of unique individuals detected (MVR people)
- Deduplicated across videos using facial recognition

**Active Cameras:**
- Cameras that recorded videos in selected time range
- Status indicator shows real-time activity

**Demographics:**
- Estimated gender and age from facial attributes
- Accuracy depends on detection quality
- Percentages may not sum to 100% due to "unknown" category

**Visit Frequency:**
- Based on appearance count across different videos
- "Returning visitor" = appeared 2+ times in time range

---

## 11. Testing Plan

### 11.1 Unit Tests

```python
# Test aggregation logic
def test_daily_aggregation():
    """Test that daily aggregation correctly sums MVR records."""
    
def test_retention_cleanup():
    """Test that old records are properly deleted based on threshold."""
    
def test_demographic_calculation():
    """Test percentage calculations for demographics."""
```

### 11.2 Integration Tests

```python
# Test end-to-end flow
def test_analytics_endpoint():
    """Test that analytics endpoint returns correct structure."""
    
def test_cache_behavior():
    """Test Redis cache hit/miss behavior."""
    
def test_filter_combinations():
    """Test various filter combinations."""
```

### 11.3 Performance Tests

```python
# Test query performance
def test_large_date_range_query():
    """Ensure queries for 30+ days use aggregates."""
    
def test_concurrent_requests():
    """Test dashboard handles multiple simultaneous users."""
```

### 11.4 UI Tests

```dart
// Test widget rendering
testWidgets('Analytics screen renders all widgets', (tester) async {
  // Test that all chart widgets load correctly
});

testWidgets('Filters update chart data', (tester) async {
  // Test that changing filters triggers data refresh
});
```

---

## 12. Security & Privacy

### 12.1 Access Control

- All analytics endpoints require authentication (JWT)
- Role-based access: Admin sees all cameras, User sees assigned cameras only
- Audit log for analytics access (optional)

### 12.2 Data Privacy

**Aggregated Data:**
- Store only statistical summaries, not individual identities
- Demographics are estimates, not personally identifiable
- No storage of facial embeddings in aggregates

**Retention Compliance:**
- Configurable retention allows compliance with data regulations (GDPR, CCPA)
- Cleanup jobs ensure old data is removed
- Option for manual data purge

### 12.3 Anonymous Mode

**Optional Feature:**
```python
ENABLE_ANONYMOUS_ANALYTICS=true  # Store counts only, no demographics
```

---

## 13. Future Enhancements

### 13.1 Advanced Features (Beyond Initial Scope)

1. **Cross-Camera Journey Tracking**
   - Track individual movement between cameras
   - Map common pathways
   - Calculate dwell time per zone

2. **AI-Powered Insights**
   - Natural language summary: "Traffic increased 15% compared to last week"
   - Automated anomaly detection with alerts
   - Predictive modeling with confidence intervals

3. **Custom Reports**
   - User-defined report templates
   - Scheduled email reports
   - PDF export with charts

4. **Real-Time Alerts**
   - Push notifications for activity spikes
   - Camera offline alerts
   - Unusual pattern detection

5. **Mobile Dashboard**
   - Responsive design optimization
   - Native mobile app (iOS/Android)
   - Offline report viewing

### 13.2 Integration Opportunities

- Export to Google Analytics, Tableau, Power BI
- Webhook notifications for events
- REST API for third-party integrations

---

## 14. Success Metrics

### 14.1 Technical KPIs

- Analytics endpoint response time < 500ms (90th percentile)
- Cache hit rate > 80% for common queries
- Dashboard load time < 2 seconds
- Aggregation job completion < 5 minutes

### 14.2 User Experience KPIs

- Dashboard usage frequency (visits per day)
- Average time spent on analytics screen
- Most used filters and charts
- Export feature utilization

### 14.3 Data Quality KPIs

- Aggregation accuracy (spot-check vs raw data)
- Zero data loss during retention cleanup
- Detection quality scores maintained

---

## 15. Conclusion

This proposal outlines a comprehensive, incremental approach to building an MVR analytics dashboard that:

1. **Leverages Existing Infrastructure:** Uses current camera card endpoints and MVR search results
2. **Scales Incrementally:** From simple metrics to advanced behavioral insights
3. **Manages Data Lifecycle:** Three-tier architecture with configurable retention
4. **Optimizes Performance:** Pre-computed aggregates and smart caching
5. **Respects Privacy:** Configurable data retention and anonymous mode
6. **Provides Actionable Insights:** From basic counts to predictive analytics

The implementation is designed to be:
- **Modular:** Each analytics level can be developed and deployed independently
- **Performant:** Aggregates prevent expensive queries on large datasets
- **Maintainable:** Clear separation between real-time, historical, and summary data
- **Extensible:** Foundation for future advanced features

**Next Steps:**
1. Review and approve proposal
2. Finalize retention thresholds
3. Begin Phase 1 implementation (database schema)
4. Set up development environment
5. Create initial analytics endpoints

---

**Document Version:** 1.0  
**Last Updated:** December 19, 2025  
**Authors:** PPL Meta Platform Team  
**Status:** Awaiting Approval
