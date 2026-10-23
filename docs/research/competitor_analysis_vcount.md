# V-Count BoostBI — Competitive Teardown & Deep Architecture Analysis

**Target Platform:** [V-Count BoostBI](https://boostbi.v-count.com)  
**Access Account Analyzed:** `demo` (Retail Client Organization)  
**Date of Inspection:** March 2026 / Live Production Audit  
**Author:** AI Systems Architect & Product Strategy (ADLabs)

---

## Executive Summary

**V-Count** is one of the world's largest retail footfall analytics vendors, operating in over 120+ countries with 40,000+ sensors installed for global retail brands like Sephora, Samsung, Lego, and Whirlpool.

Their cloud intelligence platform, **BoostBI** (`https://boostbi.v-count.com`), represents an enterprise-grade business intelligence and retail decision platform. While V-Count originated as a hardware sensor manufacturer (overhead stereo/ToF counters), BoostBI has evolved into a full-stack retail intelligence suite that correlates **Visitor Footfall + POS Sales Transactions + In-Store Spatial Behavior + Staff Shift Rosters + Weather Patterns**.

### Key High-Level Findings from Live Platform Audit:
1. **Core Value Equation:** V-Count's entire reporting model connects raw physical traffic directly to business revenue:
   $$\text{Conversion Rate} = \frac{\text{POS Transactions}}{\text{Visitor Footfall}} \times 100$$
   $$\text{Shopper Yield} = \frac{\text{Total Sales Revenue}}{\text{Visitor Footfall}}$$
2. **Unified Data Mesh:** BoostBI is not just a people counter; it cross-references camera footfall with **weather indices, employee shift rosters, POS transactions, Wi-Fi MAC tracking, and promotional campaign calendars**.
3. **Hardware Dependency (V-Count's Major Vulnerability):** V-Count relies heavily on proprietary ceiling-mounted sensors (Ultima AI, Nano, Heatmap v1/v2, Queue sensors). Retailers must purchase and physically install expensive dedicated hardware above every doorway and ceiling zone.
4. **Architectural Transition:** BoostBI's shell is a server-rendered PHP/Apache monolith utilizing Highcharts/Highstock, Fabric.js, and jQuery with dynamic AJAX fragment injection. However, newer modules like **Visitor Flow** are modern React Single-Page Applications (SPAs).

---

## 1. System Architecture & Tech Stack (Live Audit)

### 1.1 Architecture Flowchart

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             V-Count IoT / Edge Devices                           │
│  [Ultima AI Stereo]   [Nano Overhead]   [Queue Sensor]   [Wi-Fi / BLE Sniffers]  │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │ HTTPS / MQTT (JSON / XML)
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                            V-Count Cloud Ingestion                               │
│              Endpoints: https://cloud.v-count.com/api/v4/...                     │
│  - Realtime Occupancy (2s poll/push)          - Hourly In/Out Batches            │
│  - Queue Depth & Service Times                - Sensor Healthcheck (OHC)         │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           BoostBI Application Platform                           │
│  - Authentication: PHP Session + Signed JWT (Claims: userId, userType, uid)      │
│  - Integrations: Nebim ERP, POS REST API / SFTP, OpenWeather API                 │
│  - Background Jobs: Automated PDF/CSV Email Dispatch, People Traffic Index      │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         BoostBI Frontend Client Tier                             │
│  - Framework: Hybrid (Bootstrap 3.3 + jQuery Core + React Webpack SPA for Flow)  │
│  - Visualization: Highcharts & Highstock (Sankey, 3D, Heatmaps, Annotations)     │
│  - Spatial/Canvas: Fabric.js + Simpleheat + canvasAreaDraw.js (Floorplan zones)   │
│  - Data Grid: Handsontable (Excel-like Shift & Sales input) + DataTables HTML5   │
│  - Real-Time Comms: Socket.io (Live Occupancy, Queue push notifications)         │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Authentication & Session Flow
* **Session Management:** Standard dual-layer auth. Form submission to `https://boostbi.v-count.com/user/login` generates an Apache `PHPSESSID` cookie along with an authorization JWT token:
  ```json
  {
    "typ": "JWT",
    "alg": "HS256"
  }.{
    "iat": 1788879921,
    "exp": 1788966321,
    "data": {
      "userId": 115,
      "userType": "RETAIL_CLIENT",
      "uid": 129
    }
  }
  ```
* **CSRF & Request Signing:** Dynamic AJAX requests use a per-session 64-character hex `token` parameter (e.g. `token: "1f9fb29531be6a..."`) to authorize client-side requests against endpoints under `/overview/ajax/*`.

---

## 2. Comprehensive Breakdown of All Dashboard Modules

### 2.1 Executive Overview Dashboard (`/overview/dashboard`)

The landing screen for retail executives and regional managers. It summarizes macro performance across the store network.

#### Key KPI Cards
* **Street to Store Conversion (Draw-in Rate / Capture Rate):** Percentage of pedestrians passing the storefront who actually enter:
  $$\text{Draw-in Rate} = \frac{\text{Store In-Traffic}}{\text{Street / Corridor Passerby Traffic}} \times 100$$
* **Traffic (Footfall):** Total incoming customer count with period-over-period percentage change (e.g., `▲3.27%`).
* **Transactions:** Total cash register receipts imported from the POS system (e.g., `42`, `▼2.33%`).
* **Conversion Rate:** Percentage of visitors who made a purchase (e.g., `0.20%`).
* **ATV (Average Transaction Value):** Average basket spend per paying customer:
  $$\text{ATV} = \frac{\text{Total Sales Revenue}}{\text{Total Transactions}}$$
* **Sales Revenue:** Total net sales currency value.

#### Core Analytical Widgets
1. **Conversion Rate vs Traffic Chart:** Dual-axis visualization showing traffic volume (bars) overlaid with conversion rate % (line). Demonstrates whether traffic surges translate into sales or result in lost customers due to long lines or unassisted shoppers.
2. **Traffic vs Transaction Chart:** Direct correlation of store visitor volume against cash register throughput.
3. **Best Performing Stores Ranking:** League table ranking all branch locations by footfall, conversion rate, and revenue lift.
4. **Last 7 Days Trend Analysis:** Intraday comparison across the last 7 calendar days to reveal day-of-week patterns.
5. **Widget Settings Engine:** Configurable widget layout allowing users to reorder, toggle, and pin specific KPI widgets.

---

### 2.2 General Level Network Analytics (`/overview/generalLevel`)

Used by corporate headquarters to analyze trends across multi-store chains, cities, and regions.

| Sub-Tab | Endpoint | Purpose & Features |
| :--- | :--- | :--- |
| **General Insight** | `/overview/ajax/getGeneralInsight` | Multi-metric interactive time-series chart with dropdowns for: *Traffic, Sales, Transaction, ATV, Conversion Rate, Average Basket Size, Units, Stock, Units/Stock, Sales/Sqft, Revenue/Stock, Shopper Yield, Traffic/Sqft, Street Traffic (Camera), Street Traffic (Wi-Fi), Group Traffic, In/Out*. Includes **Timeline Annotations** to mark sales campaigns, weather storms, or store renovations. |
| **Performance Analysis** | `/overview/ajax/getGeneralPerformance` | Store-to-store benchmarking, target vs actual KPI tracking, quartile segmentation (Top 25% vs Bottom 25% stores). |
| **Hourly Visitor Statistics** | `/overview/ajax/getGeneralHourly` | Intraday footfall distribution across operating hours (e.g., 10:00 to 22:00) to pinpoint morning, lunch, and evening traffic peaks. |
| **Store Group Analysis** | `/overview/ajax/getGeneralGroups` | Hierarchical rollups: Global &rarr; Country &rarr; Region &rarr; City &rarr; Mall/High-street cluster. |
| **Realtime Occupancy** | `/overview/ajax/getGeneralRealtimeOccupancy` | Live head count in real-time across all stores simultaneously. Includes color-coded green/amber/red status based on max safety thresholds. |
| **Wi-Fi Analytics** | `/overview/ajax/getGeneralWifi` | Passive Wi-Fi/BLE sniffer data: Passerby vs Visitors, Dwell Time distribution, Visit Frequency (New vs Repeat visitors). |
| **Demographic Analysis** | `/overview/ajax/getGeneralDemographicAnalysis` | AI facial detection at store entrances: Male/Female split, Age Brackets (e.g. 18-24, 25-34, 35-44, 45-54, 55+), Top Demographic Group, and Demographic Gaze/Attention Time. |
| **Summary Dashboard** | `/overview/ajax/getGeneralSummaryDashboard` | High-level C-suite rollup summary. |

---

### 2.3 Store Level Analytics (`/overview/storeLevel`)

Dedicated deep-dive views for individual store managers, visual merchandisers, and operations heads.

#### 1. Visitor Analysis (`/overview/ajax/storeLevelAnalysis`)
* **Door Comparison (`/overview/ajax/getDoorComparison`):** Compares traffic across individual entrances (e.g., Main Street Entrance vs Parking Garage Entrance vs Mall Atrium Entrance). Helps optimize window displays and security placement.
* **Weather Integration (`/overview/ajax/getStoreWeather`):** Correlates hourly and daily footfall with external weather conditions (sunny, rainy, snowy, ambient temperature) to determine how weather impacts retail traffic.
* **Traffic vs Sales (`/overview/ajax/getStoreTrafficvsSale`):** Compares in-store customer count with cashier sales curves.

#### 2. Heatmap Analytics (`/overview/ajax/storeLevelHeatmapAnalysis`)
* **Hardware Support:** Uses `heatmapOptionGroup` (2D sensors) and `heatmapv2OptionGroup` (3D stereo sensors).
* **Visualization:** Floorplan overlay showing customer dwell hot-spots, high-traffic corridors, and dead zones.
* **Merchandising Impact:** Validates whether promotional end-caps and featured product displays attract customer dwell time.

#### 3. Zone Analytics (`/overview/ajax/storeLevelZoneAnalysis`)
* **Department Breakdown:** Configurable geometric zones (e.g., Men's Apparel, Women's Shoes, Cosmetics, Electronics, Fitting Rooms, Checkout).
* **Metrics Tracked:** Zone Traffic, Zone Dwell Time, Zone Transition Rate, and Zone Attraction Rate.

#### 4. Visitor Flow & Pathmap (`/overview/visitorFlow` & `/overview/ajax/getStorePathmap`)
* **Customer Journey Mapping:** Built on a modern React SPA using Sankey diagrams and trajectory graphs.
* **Path Sequencing:** Visualizes the paths customers take through the store (e.g., Entrance &rarr; Promo Table &rarr; Fitting Room &rarr; POS Cashier vs Entrance &rarr; Browsing &rarr; Exit without purchase).
* **Bottleneck Detection:** Identifies store layout chokepoints and circulation inefficiencies.

#### 5. Queue Management (`/overview/ajax/getStoreQueue` & `/options/queue`)
* **Key Metrics:**
  * **Queue Type:** Cashier checkout, customer service, fitting room queue.
  * **Number of Individuals:** Current and historical queue length.
  * **Average Waiting Time:** Mean queue wait time before reaching the counter.
  * **Abandonment Rate (Balking/Reneging):** Number and percentage of customers who join the queue but leave before being served due to excessive wait times.
  * **10-Minute Breakdown:** Granular 10-minute intervals showing cashier queue spikes.
  * **Push Notifications & Alarms:** Alerts store managers when queue wait times exceed defined service-level thresholds (e.g., alert if queue > 5 people or wait > 4 minutes).

#### 6. Pick Sense (`/overview/pickSense`)
* **Product Interaction Detection:** Monitors product interaction on display tables or shelves (how many times an item is picked up, held, or examined).

#### 7. Customer vs. Staff Filtering (`/overview/ajax/getStoreCustomerstaff`)
* Filters out store staff movements from customer traffic data using staff MAC ID filtering, wearable badges, or staff uniform detection.

---

### 2.4 Staff Optimization & Operational Tools

#### Staff Optimizer (`/overview/staffOptimizer`) & Shifts (`/options/shifts/all`)
* **Customer-to-Staff Ratio (CSR):** Calculates the ratio of shoppers on the sales floor per available employee.
* **Overstaffing vs Understaffing:** Identifies operational hours where the store is understaffed (resulting in missed sales conversions) or overstaffed (resulting in wasted labor costs).
* **Shift Scheduling:** Handsontable spreadsheet tool allowing store managers to import and plan staff rosters directly aligned with predicted peak footfall hours.

#### Online Healthcheck Control (OHC) (`/options/ohc`)
* **Device Heartbeat Monitoring:** Centralized monitoring of all cameras and edge sensors across all stores.
* **Automated Alerting:** Flags cameras that are offline, obstructed, misaligned (camera angle shifted), or reporting zero traffic during business hours.

#### Data Integration & ERP Ingestion
* **Nebim ERP Integration (`/options/nebim`):** Direct native connector for Nebim retail ERP.
* **Sales Integration (`/options/importSales`):** Automated POS ingestion via REST API, SFTP, or manual CSV/Excel upload.
* **Staff MAC IDs (`/options/staffMacids`):** Whitelist table of employee mobile device MAC addresses to suppress false Wi-Fi tracking positives.

---

## 3. V-Count Public Cloud API Architecture

From the official V-Count REST API documentation (`cloud.v-count.com/api/v4/`), their backend exposes:

| Endpoint | Method | Key Parameters | Data Payload / Output |
| :--- | :--- | :--- | :--- |
| `/api/v4/vcountapi` | `GET` | `username`, `password`, `start_date`, `end_date`, `store_id` | Hourly In/Out people count per store and door. |
| `/api/v4/vcountapi_daily` | `GET` | `username`, `password`, `start_date`, `end_date`, `store_id` | Daily consolidated In/Out counts. |
| `/api/v4/occupancy` | `GET` | `username`, `password`, `start_date`, `end_date`, `store_id` | 1-minute interval live occupancy curve. |
| `/api/v4/realtime_occupancy_sec` | `GET` | `username`, `password`, `store_id` | Real-time live occupancy polled every 2 seconds (returns `occupancy`, `maxOccupancy`). |
| `/api/v4/group_information` | `GET` | `username`, `password` | Organization hierarchy (groups, countries, regions, stores, door mappings). |
| `/api/v4/average_traffic` | `GET` | `username`, `password`, `period` | Hourly average baseline traffic across historical weeks. |
| `/api/v4/import_count` | `POST` | `username`, `password`, `data` (JSON/XML array) | Allows third-party sensors/CCTV to push footfall counts into V-Count cloud. |

---

## 4. Competitive Analysis: V-Count vs. ADLabs

| Dimension | V-Count BoostBI | ADLabs Solution | Competitive Advantage / Gap |
| :--- | :--- | :--- | :--- |
| **Camera Hardware** | **Proprietary Sensors Required** (Ultima AI, Nano 3D). Retailers must buy new hardware. | **Existing CCTV Compatible (BYOC)** via RTSP/ONVIF streams. | **Massive Win for ADLabs:** Zero new camera purchases; utilizes existing store CCTV. |
| **Edge Compute** | Embedded SoC inside individual sensors or proprietary hubs. | **Mac mini (Apple Silicon) on-premise edge appliance.** | **Win for ADLabs:** High-density edge AI handling 4–12 camera streams on a single compact Mac mini. |
| **CapEx Cost** | High ($500–$1,500+ per sensor + installation + cabling per doorway). | Low (One Mac mini per store + software license). | **Win for ADLabs:** 70–80% lower upfront CapEx for multi-camera stores. |
| **Footfall Counting** | Overhead vertical 3D stereo counting (98%+ accuracy). | Angled CCTV overhead/perspective tracking with ByteTrack/BoT-SORT. | **Challenge for ADLabs:** Perspective CCTV cameras have occlusion challenges that must be engineered carefully. |
| **POS & Conversion Tracking** | Mature integrations (Nebim, SAP, custom API, CSV import). | Must be built / integrated into pilot stores. | **V-Count advantage:** ADLabs must build straightforward POS CSV/webhook ingestion early. |
| **Heatmaps & Spatial Tracking** | Ceiling-mounted tracking sensors (`G_` and `Z_` devices). | Multi-camera CCTV homography / floor projection on Mac mini. | **Parity/Opportunity:** ADLabs can provide unified store floor tracking across existing cameras. |
| **Queue Management** | Dedicated queue sensors (`Q_` devices) with 10-min wait/abandonment stats. | Bounding box dwell time & queue line tracking via CCTV. | **Win for ADLabs:** Standard CCTV covers checkout lanes without buying dedicated queue hardware. |
| **Staff Optimization** | Staff MAC ID exclusion, staff roster vs traffic correlation. | Face/uniform/badge detection or manual shift input. | **Feature Opportunity:** ADLabs can offer visual uniform/badge detection, eliminating MAC ID hassle. |
| **Dashboard UI / UX** | Legacy PHP + Highcharts monolith + modern React SPA for Flow. | Modern, unified Fast-API + React / Next.js or Tailwind dashboard. | **Win for ADLabs:** Cleaner, faster, modern real-time Web UI without legacy bloat. |

---

## 5. Strategic Recommendations & Roadmap for ADLabs

To effectively beat V-Count in commercial retail pitches, ADLabs should adopt the following product strategy:

### 1. Match the Table-Stakes Metrics (What Retailers Actually Buy)
Do not stop at just displaying "People In / People Out". Retailers evaluate ROI using business metrics:
* **Footfall (Traffic) & Hourly Distributions**
* **POS Integration:** Ingest transaction receipts to compute **Conversion Rate %**, **Average Transaction Value (ATV)**, and **Shopper Yield**.
* **Dwell Time & Zone Analytics:** Track how long shoppers spend in specific merchandise areas.
* **Door / Entrance Comparison:** If a store has multiple cameras/doors, show the relative draw of each.

### 2. Double-Down on V-Count's Pain Points (Your Pitch Weapons)
* **"No New Hardware Needed":** Pitch directly to retailers who balk at V-Count's $1,000/door sensor cost. ADLabs connects directly to the Hikvision, Dahua, Axis, or Hanwha NVR already in their ceiling.
* **Eliminate Staff MAC ID Hassle:** Instead of asking staff to register their personal phone MAC addresses (which fails due to modern iOS/Android MAC address randomization), use computer vision to detect staff by uniform color, apron, lanyard, or designated cashier zones.
* **Unified Queue & Checkout Alerting:** Use checkout-facing CCTV to alert managers via WhatsApp or Telegram when queue length exceeds 4 people, preventing cart abandonment.

### 3. Immediate MVP Dashboard Priorities for ADLabs
1. **Executive Overview Page:** KPI cards for Traffic, Transactions, Conversion Rate, Peak Hour, and Average Dwell Time.
2. **Intraday Hourly Traffic Curve:** Bar chart showing footfall by hour with baseline averages.
3. **Zone Dwell & Heatmap:** Floorplan canvas or camera view overlay showing customer dwell concentration.
4. **Queue Monitor:** Real-time queue count and cashier service time.
5. **Daily PDF Email Digest:** Automated end-of-day summary sent to store managers at store closing time.
