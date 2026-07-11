# EyeNet Inspect

## Proposal for an Industrial Visual Inspection Microservice — Copper Tube Surface Defect Detection

**Status**: Proposal  
**Date**: September 7, 2026  
**Author**: PPL Meta Platform Team

---

## 1. Overview

EyeNet Inspect is a new EyeNet application module that extends the platform into **automated industrial visual inspection**. It ingests synchronized streams from multiple high-resolution industrial cameras, runs a trained defect-detection model in real time, and surfaces detected faults (cracks, scratches, surface markings, dimensional deviations) through the existing EyeNet frontend and alerting pipeline.

Unlike the 5 existing EyeNet applications — which focus on human activity (face detection, demographics, presence) — EyeNet Inspect targets **manufacturing quality assurance** on production lines. The core ML model is domain-specific and must be trained on labelled defect data for each inspection case.

This proposal:
1. Defines the service architecture, camera integration, and ML pipeline for EyeNet Inspect.
2. Provides a fully worked example: **3–4 cameras aligned across a 10–20 cm span of a copper tube running at 7 cm/sec, detecting surface cracks and markings**.

---

## 2. Where This Fits in the EyeNet Platform

### 2.1 Existing Platform Capabilities (Reused)

| Existing Component | Role in EyeNet Inspect |
|---|---|
| `ppl-meta-cameras` | Camera registration, RTSP/USB ingestion, recording profiles, streaming session management |
| `ppl-meta-node` | User auth, licence enforcement, tenant scoping |
| `ppl-meta-orchestrator` | Trigger/action pipeline — e.g., "if defect detected → send alert/stop conveyor/activate marker" |
| `ppl-meta-media` | Frame storage, inspection result image archiving, collection management |
| `ppl-meta-matrix` | Multi-line aggregated reporting (e.g., defect rates across production cells) |
| `ppl-meta-authority` | Licence features (`eyenet_inspect`, `inspect_multi_line`) |
| `ppl-meta-frontend` | Dashboards, live annotated streams, inspection reports, alert inbox |
| `ppl-meta-edge-camera` (pattern) | RPI-based edge client for on-device pre-processing and stream relay |
| `ppl-meta-vmeta` (pattern) | ML orchestration pattern — FaceNet → Age/Gender → MVR pipeline; Inspect follows analogous pipeline |

### 2.2 What Is New

| New Component | Purpose |
|---|---|
| **`ppl-meta-inspect`** (new microservice) | Hosts the inspection ML model, manages camera arrays, runs real-time inference, stores defect records |
| **Inspection model** (per-case trained) | Domain-specific defect detector — YOLO-style object detector, segmentation model, or anomaly detector, depending on the inspection task |
| **Multi-camera synchronization logic** | Aligns and stitches (logically, not necessarily as a panorama) frames from 2+ cameras covering overlapping or adjacent fields of view on the same production line |
| **Inspection labelling & training pipeline** | Tooling for collecting good/defective samples, labelling them, training/validating the model, and deploying it as a hot-swappable artefact |
| **Inspect-specific frontend views** | Live multi-camera tile view with defect overlays, defect gallery, line-status dashboard, per-batch quality reports |
| **RPI Inspect Client** (optional, pattern from `ppl-meta-edge-camera`) | Runs on a Raspberry Pi or Jetson Nano co-located with the camera array; handles capture, optional pre-processing, and streaming to the main node over VPN |

---

## 3. Architecture

### 3.1 Service Topology

Inline industrial inspection requires **deterministic low-latency inference** that cannot tolerate network round-trips for every frame. The architecture places a dedicated edge compute unit directly adjacent to the camera array on the production line. Raw frames stay local — only defect metadata and cropped images travel to the EyeNet Node over the LAN.

```
┌──────────────────────────────────────────────────────────────────────┐
│  PRODUCTION LINE — Copper Tube Extrusion                            │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ Camera 1 │  │ Camera 2 │  │ Camera 3 │  │ Camera 4 │           │
│  │ (GigE)   │  │ (GigE)   │  │ (GigE)   │  │ (GigE)   │           │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘           │
│       │             │             │             │                  │
│       └─────────────┴──────┬──────┴─────────────┘                  │
│                            │  GigE cables (≤10m)                   │
│               ┌────────────▼──────────────┐                        │
│               │  INDUSTRIAL EDGE PC       │  Fanless, DIN-rail     │
│               │                           │  Jetson Orin / i7      │
│               │  ┌─────────────────────┐  │                        │
│               │  │ C++ Inference Engine │  │  Hot path (<5ms)      │
│               │  │  • Frame grabber     │  │                        │
│               │  │  • Preprocessing     │  │                        │
│               │  │  • TensorRT infer    │  │                        │
│               │  │  • GPIO pass/fail    │──┼──▶ conveyor stop /    │
│               │  └─────────┬───────────┘  │    marker actuator     │
│               │            │ defect events │                        │
│               │  ┌─────────▼───────────┐  │                        │
│               │  │ Python Inspect API  │  │  Warm path             │
│               │  │  • Defect DB (SQLite)│  │  (REST + WS)          │
│               │  │  • Local ring buffer │  │                        │
│               │  │  • REST/WS endpoint  │  │                        │
│               │  └─────────┬───────────┘  │                        │
│               └────────────┼──────────────┘                        │
│                            │                                       │
└────────────────────────────┼───────────────────────────────────────┘
                             │  LAN (defect metadata + cropped images only)
┌────────────────────────────┼───────────────────────────────────────┐
│  EYENET NODE (control room / anywhere on LAN)                      │
│                            │                                       │
│  ┌─────────────────────────▼─────────────────────────────────┐    │
│  │  ppl-meta-cameras (existing)                               │    │
│  │  • Camera registration & health monitoring                 │    │
│  │  • Recording profiles (on-demand, not continuous)          │    │
│  │  • Does NOT ingest raw inspection frames                   │    │
│  └───────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐    │
│  │  ppl-meta-orchestrator (existing)                          │    │
│  │  • Receives defect events from edge PC                     │    │
│  │  • "on_defect" trigger → Slack/Teams/webhook/marking       │    │
│  │  • Batch reporting triggers                                │    │
│  └───────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐    │
│  │  ppl-meta-frontend (existing, extended)                    │    │
│  │  • EyeNet Inspect dashboard tab                            │    │
│  │  • Proxies to edge PC's REST/WS for live feed              │    │
│  │  • Defect gallery & reports (queried from edge PC)         │    │
│  └───────────────────────────────────────────────────────────┘    │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

**Key design principle**: The C++ inference engine on the edge PC emits a hardware GPIO signal (pass/fail) within **<5 ms** of a defect detection — fast enough to stop a conveyor or fire a reject actuator. The EyeNet Node receives defect records asynchronously for dashboards, alerts, and archival. Full-resolution frames are stored in a local ring buffer on the edge PC and only persisted to disk when a defect is detected, minimizing storage and network overhead.


### 3.2 Camera Integration Strategy

For inline industrial inspection, all cameras connect directly to the **edge PC** co-located at the production line — not to the EyeNet Node over the network. This eliminates network latency from the inference hot path.

| Path | Camera Protocol | Ingestion Method | When to Use |
|---|---|---|---|
| **A — Direct SDK on Edge PC (recommended)** | GigE Vision / USB3 Vision | C++ inference engine links vendor SDK (Basler Pylon, Allied Vision Vimba, FLIR Spinnaker) directly; frames never leave the edge PC's memory | Primary path for inline inspection — lowest latency, hardware trigger support, GPIO integration |
| **B — RTSP/USB via gstreamer/FFmpeg on Edge PC** | RTSP / USB UVC | C++ inference engine captures via gstreamer or FFmpeg APIs; slightly higher latency than SDK but camera-agnostic | Cameras that only support RTSP or UVC; lower-cost USB cameras |
| **C — Remote Camera via Dedicated Link** | GigE over fiber extender | Camera is physically distant (>10m) from edge PC; fiber or active GigE extender bridges the gap; same SDK integration as Path A | Cameras in harsh environments where the edge PC cannot be placed |

For the copper tube example, **Path A** is the recommended approach — 4× GigE Vision cameras connected via ≤10m Ethernet cables to a fanless industrial edge PC mounted on the production line frame. The C++ inference engine uses the vendor SDK for zero-copy frame access and hardware-triggered synchronized capture. `ppl-meta-cameras` on the EyeNet Node registers cameras for health monitoring and on-demand recording only — it does **not** ingest raw inspection frames.

### 3.3 ML Pipeline (Inference Flow)

```
Camera Array (3–4 synchronized GigE cameras)
       │
       ▼
 Frame Grabber / Capture Worker
  • Hardware-triggered simultaneous capture (GPIO or PTP sync)
  • Each frame tagged with camera_id + sequence_num + timestamp
       │
       ▼
 Pre-Processing Queue (per camera)
  • Crop to ROI (region of interest) if cameras cover more than the tube
  • Resize to model input resolution
  • Normalize pixel values
  • Optional: apply CLAHE / histogram equalization for contrast
       │
       ▼
 Inference Engine (TensorRT / ONNX Runtime)
  • YOLOv8-nano or YOLOv8-small trained on defect dataset
  • Runs on GPU if available, falls back to CPU + OpenVINO on Intel
  • Batch size = 1 (per camera), real-time priority
       │
       ▼
 Post-Processing & Deduplication
  • NMS (non-maximum suppression) per frame
  • Cross-camera deduplication: if a single physical defect spans
    the boundary between two adjacent cameras, merge overlapping
    bounding boxes into one defect record
  • Assign severity score based on defect class + confidence + size
       │
       ▼
 Defect Record Persisted
  • Defect ID, timestamp, camera_id(s), bounding box, class, confidence,
    severity, cropped defect image path, full-frame reference
       │
       ▼
 Orchestrator Trigger
  • "on_defect" event fires → alert, conveyor stop, marking actuator,
    Slack/Teams notification, or webhook
```

### 3.4 Model Lifecycle

```
┌──────────────────────────────────────────────────────────────┐
│  OFFLINE / SETUP PHASE                                       │
│                                                              │
│  1. Data Collection                                          │
│     • Run production line, capture frames from all cameras   │
│     • Collect ~500–2000 good samples + ~200–500 defect       │
│       samples per defect class                               │
│     • Defect samples can be real (from production) or        │
│       artificially introduced (scratched/cracked tubes)      │
│                                                              │
│  2. Labelling                                                │
│     • Bounding box annotation (YOLO format) or polygon       │
│       annotation (segmentation format)                       │
│     • Tools: LabelImg, CVAT, Roboflow, or custom tool        │
│                                                              │
│  3. Training                                                 │
│     • Base model: YOLOv8n/s pretrained on COCO               │
│     • Fine-tune on defect dataset, 100–300 epochs            │
│     • Data augmentation: rotation (±5°), brightness/contrast │
│       jitter, Gaussian noise, slight blur (simulate motion)  │
│     • Validate on held-out test split; target mAP@0.5 > 0.85 │
│                                                              │
│  4. Export & Optimize                                        │
│     • Export to ONNX → convert to TensorRT (FP16 or INT8)    │
│     • Measure inference latency on target hardware           │
│     • Package as versioned .trt or .onnx artefact            │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  ONLINE / RUNTIME                                            │
│                                                              │
│  • ppl-meta-inspect loads model on startup                   │
│  • Hot-swap: POST /api/v1/inspect/models/activate {version}  │
│    loads a new model without restarting the service          │
│  • Model version recorded in every defect record for         │
│    traceability                                              │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 3.5 Language & Performance Architecture

Inline industrial inspection imposes latency constraints that Python alone cannot meet. The `ppl-meta-inspect` service is split into two processes running on the same edge PC, communicating via a lightweight IPC mechanism (Unix domain socket or ZeroMQ in-process queue):

#### Hot Path — C++ Inference Engine

| Responsibility | Technology | Rationale |
|---|---|---|
| Frame grabber | Vendor C++ SDK (Basler Pylon, Allied Vision Vimba) | Zero-copy DMA transfer from camera to system memory; hardware trigger handling; sub-ms jitter |
| Image preprocessing | OpenCV C++ (`cv::resize`, `cv::cvtColor`, `cv::normalize`) | SIMD-accelerated; avoids Python GIL and memory copies |
| Model inference | TensorRT C++ API | Direct GPU execution without Python interpreter overhead; FP16/INT8 quantization; ~1–3 ms per inference on Jetson Orin |
| GPIO pass/fail output | `libgpiod` or vendor GPIO library | Hardware-level signal within <5 ms of defect detection; triggers conveyor stop, air ejector, or marking actuator |
| Inter-process communication | ZeroMQ (PUB/SUB) or Unix domain socket | Sends defect event structs to the Python API process with nanosecond overhead |

**Language choice**: C++17 with CMake build system. C++ provides direct access to camera vendor SDKs (all C/C++), zero-overhead TensorRT bindings, and deterministic memory management — no garbage collection pauses. Rust was evaluated as an alternative (memory safety, modern tooling) but rejected because industrial camera SDKs are exclusively C/C++ and wrapping them in Rust FFI adds complexity without performance benefit.

**Build & deployment**: CMake-based build producing a single statically-linked binary. Packaged as a Docker container with the vendor SDK runtime and CUDA/TensorRT libraries. Deployed to the edge PC via the same Docker Compose pattern used by all EyeNet services.

#### Warm Path — Python Inspect API

| Responsibility | Technology | Rationale |
|---|---|---|
| REST / WebSocket API | FastAPI (Python) | Consistent with all other EyeNet services; rapid development |
| Defect database | SQLite (local) | Zero-config embedded DB on the edge PC; no network dependency |
| Ring buffer for raw frames | Circular buffer on NVMe SSD | Stores last N seconds of full-res frames; persisted to defect records only on trigger |
| Defect record forwarding | HTTP POST to EyeNet Node | Asynchronous, non-blocking; batched if needed |
| Model management & hot-swap | File watcher + TensorRT runtime reload | REST endpoint triggers model file swap; C++ engine picks up change via IPC signal |

**Why Python for the warm path**: The API layer handles infrequent operations (defect queries, reports, model management) where Python's development speed and compatibility with the existing EyeNet codebase outweigh any performance concern. The Python process does not touch raw frames — it receives already-processed defect events from the C++ engine.

#### Timing Budget (per frame, 4 cameras at 30 fps = 33.3 ms window)

| Stage | Time Budget | Notes |
|---|---|---|
| Frame capture (4 cameras, hardware-synced) | <1 ms | GigE Vision hardware trigger + DMA transfer |
| Preprocessing (4× crop + resize + normalize) | ~2–4 ms | OpenCV SIMD, parallelized across cameras |
| Inference (4× YOLOv8n, batch size 1) | ~4–8 ms | TensorRT FP16 on Jetson Orin; ~1–2 ms each |
| NMS + cross-camera dedup | ~1 ms | Per-frame, per-camera |
| GPIO output (if defect detected) | <1 ms | Hardware-triggered immediately after NMS |
| Defect event → Python API (IPC) | <0.5 ms | ZeroMQ in-process |
| **Total hot-path latency** | **~7–14 ms** | Well within 33.3 ms frame budget |

The C++ hot path completes in under half the frame budget, leaving ample headroom for occasional frame bursts or model warm-up. The GPIO signal fires within 5 ms of defect detection, meeting industrial inline requirements for conveyor control or part rejection.

---

## 4. API Specification (ppl-meta-inspect)

### 4.1 REST Endpoints

```
# Line & Camera Management
POST   /api/v1/inspect/lines                                    # Register a new inspection line
GET    /api/v1/inspect/lines                                    # List all inspection lines
GET    /api/v1/inspect/lines/{line_id}                          # Get line details + status
PUT    /api/v1/inspect/lines/{line_id}                          # Update line configuration
DELETE /api/v1/inspect/lines/{line_id}                          # Decommission a line

POST   /api/v1/inspect/lines/{line_id}/cameras                  # Add camera to line
GET    /api/v1/inspect/lines/{line_id}/cameras                  # List cameras on line
PUT    /api/v1/inspect/lines/{line_id}/cameras/{camera_id}      # Update camera ROI, calibration
DELETE /api/v1/inspect/lines/{line_id}/cameras/{camera_id}      # Remove camera from line

# Model Management
GET    /api/v1/inspect/models                                   # List available model versions
POST   /api/v1/inspect/models/activate                          # Hot-swap active model {version}
GET    /api/v1/inspect/models/active                            # Get currently active model info

# Inspection Control
POST   /api/v1/inspect/lines/{line_id}/start                    # Start inspection on line
POST   /api/v1/inspect/lines/{line_id}/stop                     # Stop inspection on line
POST   /api/v1/inspect/lines/{line_id}/pause                    # Pause inspection (e.g., maintenance)
GET    /api/v1/inspect/lines/{line_id}/status                   # Running / Stopped / Paused / Error

# Defect Records
GET    /api/v1/inspect/lines/{line_id}/defects                  # Query defects (paginated, filterable)
       ?from=&to=&class=&min_severity=&camera_id=&limit=&offset=
GET    /api/v1/inspect/defects/{defect_id}                      # Single defect detail + images
GET    /api/v1/inspect/defects/{defect_id}/image                # Cropped defect image
GET    /api/v1/inspect/defects/{defect_id}/frame                # Full annotated frame

# Reporting
GET    /api/v1/inspect/lines/{line_id}/reports/summary          # Defect counts by class/severity
       ?from=&to=
GET    /api/v1/inspect/lines/{line_id}/reports/trend            # Defect rate over time
       ?from=&to=&interval=hour|day|shift
```

### 4.2 WebSocket (Live Feed)

```
WS /api/v1/inspect/lines/{line_id}/live
  → Streams annotated frames (JPEG, base64) with defect overlays
  → Client can subscribe to specific cameras or all cameras on the line
  → Defect events sent as JSON messages interleaved with frames
```

### 4.3 Database Schema (ppl-meta-inspect)

```sql
CREATE TABLE inspection_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    product_type VARCHAR(255),           -- e.g., "copper_tube_22mm"
    line_speed_cm_per_sec REAL,          -- conveyor/process speed
    span_width_cm REAL,                  -- total width covered by camera array
    status VARCHAR(50) DEFAULT 'stopped', -- running, stopped, paused, error
    active_model_version VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE line_cameras (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    line_id UUID NOT NULL REFERENCES inspection_lines(id) ON DELETE CASCADE,
    camera_uuid VARCHAR(255) NOT NULL,   -- references ppl-meta-cameras Camera.uuid
    position_index INTEGER NOT NULL,     -- 0-based position in the array (left to right)
    roi_x INTEGER, roi_y INTEGER,        -- region of interest within camera frame
    roi_w INTEGER, roi_h INTEGER,
    coverage_offset_cm REAL,             -- start position of this camera's coverage on the span (cm)
    coverage_width_cm REAL,              -- width this camera covers (cm)
    pixels_per_mm REAL,                  -- calibration: pixels per millimeter at the object plane
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (line_id, position_index)
);

CREATE TABLE defect_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    line_id UUID NOT NULL REFERENCES inspection_lines(id),
    camera_id UUID REFERENCES line_cameras(id),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    defect_class VARCHAR(100) NOT NULL,  -- e.g., "crack", "scratch", "pit", "marking"
    confidence REAL NOT NULL,            -- 0.0–1.0
    bbox_x INTEGER, bbox_y INTEGER,      -- bounding box in camera pixel coordinates
    bbox_w INTEGER, bbox_h INTEGER,
    severity VARCHAR(20) DEFAULT 'medium', -- low, medium, high, critical
    physical_size_mm REAL,               -- estimated physical size from calibration
    position_on_span_cm REAL,            -- position along the 10–20 cm span
    cropped_image_path VARCHAR(512),      -- local path to cropped defect image
    full_frame_path VARCHAR(512),         -- local path to annotated full frame
    model_version VARCHAR(100),           -- which model version detected this
    merged_from_camera_ids JSONB,         -- if cross-camera merge, list of source cameras
    reviewed BOOLEAN DEFAULT FALSE,       -- human-verified flag
    review_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_defects_line_time ON defect_records (line_id, timestamp DESC);
CREATE INDEX idx_defects_class ON defect_records (line_id, defect_class);
```

---

## 5. Worked Example: Copper Tube Surface Inspection

### 5.1 Physical Setup — Circumferential Array (Around the Tube)

The cameras must cover the **full circumference** of the current tube segment passing through the inspection station. A single top-down camera only sees the upper arc of the tube surface. To inspect 360° around the tube, 3–4 cameras are arranged at different angles around the tube's cross-section, each covering a ~90°–120° arc of the surface.

The "10–20 cm wide span" refers to the **axial length of tube visible in each camera's field of view** — the segment of tube being inspected at any given instant along the direction of travel.

```
         ← TUBE MOVES THROUGH INSPECTION STATION AT 7 cm/sec ←
    ═══════════════════════════════════════════════════════════════
    
    Cross-Section View (looking along the tube, into the page):
    
                ┌──────┐
                │  C1  │   Top camera
                │      │   Sees upper 90°–120° of tube surface
                └──┬───┘
                   │
          ┌────────┼────────┐
          │ C4      ○       │ C2    ○ = tube cross-section (Ø 22 mm)
          │ (left)  │(right)│       C1–C4 = cameras at different angles
          └────────┼────────┘
                   │
                ┌──┴───┐
                │  C3  │   Bottom camera (via mirror or direct mount)
                │      │   Sees lower 90°–120° of tube surface
                └──────┘
    
    Axial field of view per camera: ~10–20 cm along the tube length
    Circumferential coverage per camera: ~90°–120° of tube surface
    Total coverage: full 360° circumference × 10–20 cm axial span
```

Each camera is angled to view a different quadrant of the tube's surface. At a working distance of 15–25 cm with macro lenses, each camera easily covers its assigned arc with overlap between neighbors, eliminating blind spots around the circumference.

With 3–4 cameras at 30 fps and 7 cm/sec tube speed:

- **Time each point on the tube surface is in view**: 10–20 cm ÷ 7 cm/sec = **1.4–2.9 seconds** (entire axial span crossing the inspection station)
- **Frames captured per point per camera**: ~43–86 frames at 30 fps (double at 60 fps)
- **Full 360° coverage**: Each point on the tube surface is seen by at least one camera as the tube rotates through the inspection zone. If the tube does not rotate, every camera sees its assigned arc continuously — collectively covering the full circumference.

### 5.2 Camera Positioning Details

```
    Side View (along the tube's direction of travel):
    
                                         C1
    ← Tube motion (7 cm/sec) ←         (top)
    ═══════════════════════════    ─────●─────  ← camera ring
                                         │
    ◀──── 10–20 cm axial FOV ────▶      C2,C4
                                   (left/right at same axial position)
                                         │
                                        C3
                                      (bottom)
    
    All cameras are mounted at the same axial position (single inspection
    station). Each camera's field of view spans 10–20 cm along the tube
    length at the object plane. The working distance is 15–25 cm.
```

Cameras are mounted on a rigid ring or bracket surrounding the tube path. All cameras share the same axial position — they view the same 10–20 cm segment of tube simultaneously, but from different angular positions. This single-station design keeps the mechanical setup simple while achieving full circumferential coverage.

For the bottom camera (C3), if direct mounting under the tube is obstructed by the conveyor or supports, a **45° mirror** placed below the tube reflects the bottom surface to a camera mounted to the side — a standard industrial machine-vision technique.



### 5.3 Camera Specifications

| Parameter | Value | Rationale |
|---|---|---|
| **Sensor resolution** | 2448 × 2048 (5 MP) or higher | At 0.05 mm/pixel, a 5 MP sensor covers ~12 cm × 10 cm field of view |
| **Sensor type** | Global shutter CMOS | Eliminates rolling shutter distortion on moving tube |
| **Lens** | 35–50 mm macro or telecentric | Telecentric eliminates perspective error for measurement; macro resolves fine cracks |
| **Working distance** | 15–25 cm | Enough clearance above the moving tube; compatible with lighting |
| **Frame rate** | ≥30 fps (60 fps preferred) | At 30 fps and 7 cm/sec, each point is captured multiple times; 60 fps gives double the samples for better defect confidence |
| **Interface** | GigE Vision (PoE) | Single cable for power + data; standard industrial protocol; works with existing LAN |
| **Synchronization** | Hardware trigger via GPIO or IEEE 1588 PTP | All 4 cameras fire simultaneously to avoid spatial offset between frames |
| **Recommended models** | Basler ace2 (a2A2448-75gc), FLIR Blackfly S (BFS-PGE-50S5), or equivalent | Proven industrial cameras with GigE, global shutter, 5 MP |

### 5.4 Lighting

| Requirement | Solution |
|---|---|
| **Uniform illumination** | 2× LED line lights or dome light positioned to avoid specular reflection off the copper's shiny surface |
| **Crack enhancement** | Dark-field illumination (light at oblique angle) — cracks scatter light and appear bright against a dark background |
| **Color marking detection** | White LED ring light + polarizer to cut glare — surface markings show as contrast deviations |
| **Strobe sync** | Lights strobed in sync with camera trigger to freeze motion and reduce heat |

### 5.5 Defect Classes and Detection

| Defect Class | Visual Signature | ML Detection Approach | Min. Size |
|---|---|---|---|
| **Crack** | Dark linear feature with branching; may be hairline (<0.1 mm wide) | Bounding box + "crack" class; model learns to distinguish cracks from scratches by morphology | 0.1 mm × 2 mm |
| **Scratch** | Linear groove, uniform width, often parallel to tube axis; bottom may show bare copper | Bounding box + "scratch" class; model trained on scratch vs crack differentiation | 0.2 mm × 5 mm |
| **Pit / Pinhole** | Small dark circular depression | Bounding box + "pit" class | Ø 0.3 mm |
| **Surface marking** | Discoloration, stain, or printed marking defect; may be lighter or darker than surrounding | Bounding box + "marking" class; may require additional color-space preprocessing | 1 mm² |
| **Dent** | Shallow depression without surface break; visible as distortion of reflected light pattern | May require structured light or laser line projection in addition to 2D camera | Ø 2 mm |

### 5.6 Throughput Calculation (On-Edge Inference)

All inference runs locally on the edge PC adjacent to the cameras — no network latency in the hot path. At 7 cm/sec tube speed with 4 cameras covering a ~10 cm axial segment:

- **Tubes per minute**: For a standard 3-meter tube, each tube takes 300 cm ÷ 7 cm/sec = **42.9 seconds** to pass through the inspection zone → **~1.4 tubes/minute**
- **Frames per tube per camera**: 42.9 sec × 30 fps = **1,287 frames**
- **Total frames per tube (4 cameras)**: **~5,150 frames**
- **Inference requirement on edge PC**: 4 cameras × 30 fps = **120 inferences/sec**

**Per-frame timing budget** (33.3 ms at 30 fps, per camera):

| Stage | Jetson Orin NX (TensorRT FP16) | Intel i7-13700H (OpenVINO INT8) |
|---|---|---|
| Grabber DMA | <1 ms | <1 ms |
| Preprocess (crop, resize, normalize) | ~2 ms | ~3 ms |
| Inference (YOLOv8n) | ~1–2 ms | ~8–12 ms |
| NMS + dedup | ~1 ms | ~1 ms |
| GPIO signal (if defect) | <1 ms | <1 ms |
| **Total per camera** | **~5–7 ms** | **~14–18 ms** |
| **Total for 4 cameras (serialized)** | **~20–28 ms** | **~56–72 ms** |

The Jetson Orin can process all 4 cameras within the 33.3 ms frame window. The Intel CPU path exceeds it — but with parallel inference across 4 CPU cores (OpenVINO multi-stream), total latency drops to ~20–25 ms, which fits. The recommended edge hardware is therefore a **GPU-accelerated platform** (Jetson Orin or x86 + discrete GPU) to guarantee headroom.

**Network traffic to EyeNet Node**: Only defect events + cropped images travel over LAN — approximately 200–500 KB/sec (assuming 1–2 defects per tube) vs. the 1.2 GB/sec of raw frames that would be required to send 4× 5 MP streams at 30 fps uncompressed. This makes the architecture practical even over standard Gigabit Ethernet.

### 5.7 Edge Compute Hardware

| Component | Recommended (GPU) | Budget (CPU-Only) |
|---|---|---|
| **Platform** | NVIDIA Jetson Orin NX 16GB (industrial module) | Intel NUC 14 Pro (i7-13700H, 32 GB RAM) |
| **GPU / Accelerator** | 1024-core Ampere GPU, 32 TOPS (INT8) | Intel Iris Xe iGPU + OpenVINO |
| **Storage** | 512 GB NVMe SSD (for ring buffer + defect archive) | Same |
| **Networking** | 2× GigE (1× for cameras + 1× for node uplink) | Same |
| **I/O** | GPIO header for pass/fail signal, 2× USB 3.2 for peripherals | USB GPIO adapter (e.g., Numato Lab) |
| **Enclosure** | Fanless, DIN-rail mountable, IP40+ | Same |
| **Power** | 15–25 W typical (PoE-powered option via PD switch) | 30–45 W typical |
| **OS** | Ubuntu 22.04 LTS + JetPack 6.0 | Ubuntu 22.04 LTS |
| **Est. Cost** | ~€800–1,200 | ~€600–900 |

The Jetson Orin is recommended for production — it guarantees the timing budget with significant headroom and supports hardware-accelerated video encoding for on-demand recording. The Intel NUC path is acceptable for lower frame rates (15–20 fps) or fewer cameras (2–3) and serves as a development/prototyping platform.

### 5.8 Data Collection and Training Plan (Copper Tube Example)

**Step 1 — Collect Good Samples**
- Run 50–100 tubes through the inspection station with all 4 cameras recording at 30 fps.
- Randomly sample 2,000 frames across all cameras (500 per camera), ensuring variety in lighting conditions and tube positions.
- Label all as "good" (no defect) for the background class.

**Step 2 — Collect Defect Samples**
- Artificially introduce defects on 20–30 scrap tubes:
  - Cracks: Use a scribe or scoring tool to create hairline surface cracks.
  - Scratches: Drag steel wool or abrasive paper along the surface.
  - Pits: Impact with a center punch.
  - Markings: Apply ink, tape residue, or oxidized spots.
- Run these defective tubes through the inspection station.
- Annotate every frame containing a defect with bounding boxes and class labels (use CVAT or LabelImg).

**Step 3 — Train**
- Base model: `yolov8n.pt` (pretrained on COCO)
- Training dataset: 1,500 good (background-only) + 500 defect frames (with ~800 bounding box annotations total)
- Split: 80% train / 10% val / 10% test
- Augmentation: horizontal flip, ±10° rotation, ±30% brightness/contrast, motion blur (3–5 px kernel), Gaussian noise (σ=5)
- Epochs: 200 (early stopping if mAP plateaus for 30 epochs)
- Target metrics: mAP@0.5 ≥ 0.90, recall ≥ 0.95 (minimize false negatives — missing a crack is worse than a false alarm)
- Export: ONNX → TensorRT FP16

**Step 4 — Validate**
- Run 20 tubes (10 good, 10 with known defects) through the system.
- Measure: precision, recall, false-positive rate, inference latency.
- Tune confidence threshold to balance false positives vs. false negatives.
- If recall < 0.95, collect more defect samples and retrain.

### 5.9 Orchestrator Integration (Example Rules)

```
Trigger: on_defect
  Conditions:
    - defect_class IN ("crack", "pit")
    - severity IN ("high", "critical")
  Actions:
    1. Send Slack notification to #quality-alerts channel
       "🔴 CRITICAL: {defect_class} detected on Line 1 at {timestamp}
        Severity: {severity} | Position: {position_on_span_cm} cm
        View: {defect_image_url}"
    2. Activate marking spray nozzle at position {position_on_span_cm + offset}
    3. Log to quality database
    4. Increment defect counter for current batch

Trigger: on_batch_complete
  Conditions:
    - batch_size reached (e.g., 100 tubes)
  Actions:
    1. Generate PDF quality report
    2. Email report to quality_manager@factory.com
    3. If defect_rate > 2%: escalate to shift supervisor
```

---

## 6. Frontend Integration

### 6.1 EyeNet Inspect Dashboard (New Tab)

The frontend gains an "Inspect" tab (alongside Presence, Signage, Vradar, Gate, Sentinel). This tab contains:

| View | Description |
|---|---|
| **Line Overview** | Cards for each inspection line showing: status (running/stopped), current production speed, defect count today, defect rate %, last defect timestamp |
| **Live Feed** | Multi-camera tile view (2×2 grid for 4 cameras); annotated frames with bounding boxes drawn in real time; click a bounding box to see defect detail |
| **Defect Gallery** | Scrollable grid of cropped defect images; filter by class, severity, camera, date range; sort by timestamp or severity |
| **Defect Detail** | Large cropped image + full annotated frame; metadata (class, confidence, severity, size, position); review/approve button; notes field |
| **Reports** | Trend chart (defects/hour over time), Pareto chart (defects by class), per-batch summary table; export to CSV/PDF |

### 6.2 Frontend Service Client

A new Dart client (`lib/services/inspect_client.dart`) in `ppl-meta-frontend` communicates with `ppl-meta-inspect`'s REST and WebSocket endpoints. This follows the same pattern as the existing `authority_status_client.dart` and `vpn_status_client.dart`.

---

## 7. Licence Model

| Tier | Feature |
|---|---|
| **EyeNet Inspect Lite** | 1 inspection line, 2 cameras, 2 defect classes, basic reporting |
| **EyeNet Inspect Business** | 3 inspection lines, 4 cameras/line, unlimited defect classes, trend reports, orchestrator actions |
| **EyeNet Inspect Enterprise** | Unlimited lines & cameras, custom model hosting, multi-site aggregation via Matrix, API access for external MES/SCADA integration |

New authority licence features: `eyenet_inspect`, `inspect_multi_line`, `inspect_custom_model`.

---

## 8. Implementation Phases

### Phase 1 — Python Foundation + C++ Prototype (6–8 weeks)
- Scaffold `ppl-meta-inspect` Python API (FastAPI, SQLAlchemy, Docker) following service-template
- Database schema (inspection lines, cameras, defects) with SQLite for edge deployment
- REST API for line/camera CRUD, defect querying, model management
- Single-camera C++ inference engine prototype:
  - CMake project with OpenCV + ONNX Runtime (CPU) for development
  - Frame grabber using gstreamer (camera-agnostic for prototyping)
  - Basic inference loop (capture → preprocess → infer → log)
  - IPC bridge (ZeroMQ) to Python API for defect event delivery
- Python-C++ IPC contract defined (protobuf or flatbuffers message schema)
- Frontend "Inspect" tab skeleton + line overview card

### Phase 2 — Multi-Camera Edge Pipeline (6–8 weeks)
- Upgrade C++ engine to multi-camera:
  - Vendor SDK integration (Basler Pylon or Allied Vision Vimba) replacing gstreamer
  - Hardware trigger synchronization (GPIO or PTP)
  - Parallel frame processing (one thread per camera)
- Cross-camera deduplication logic in C++ post-processing
- GPIO pass/fail output integration (`libgpiod`)
- Edge PC provisioning automation (Ansible or shell scripts for Jetson/NUC setup)
- Python API deployment on edge PC (Docker Compose, same pattern as other EyeNet services)
- Model training pipeline:
  - Data collection tooling (frame capture with camera_id + position metadata)
  - Labelling guide + CVAT/Roboflow setup
  - YOLOv8 training scripts with augmentation config
  - TensorRT export script
- Model hot-swap: REST endpoint triggers C++ engine model reload via IPC
- Frontend live multi-camera tile view + defect overlay

### Phase 3 — Production Hardening (4–6 weeks)
- TensorRT integration in C++ engine (replace ONNX Runtime for GPU targets)
- Automatic CPU/GPU fallback: C++ engine detects available accelerator at startup
- Performance profiling & optimization:
  - Benchmark against timing budget (Section 3.5)
  - Optimize preprocessing pipeline (CUDA streams, pinned memory)
  - Validate GPIO latency < 5 ms with oscilloscope
- Orchestrator trigger integration (`on_defect`, `on_batch_complete`)
- Reporting engine (summary, trend, batch reports) in Python API
- CI/CD pipeline for C++ build (CMake + Docker multi-stage build, artefact publishing)
- Frontend defect gallery + reports
- 24-hour soak test on production line (no defects missed, no false stops)

### Phase 4 — Enterprise & Matrix (3–4 weeks)
- Multi-line management (multiple edge PCs → single EyeNet Node)
- Matrix aggregation (defect rates across factories, cross-line quality trends)
- MES/SCADA integration webhooks (REST or OPC-UA bridge from Python API)
- Authority licence features (`eyenet_inspect`, `inspect_multi_line`, `inspect_custom_model`)
- Production deployment guide (edge PC provisioning, network setup, camera calibration)
- Operator training materials

---

## 9. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **Insufficient defect samples for training** | Model fails to detect rare defects | Use data augmentation aggressively; consider anomaly detection (autoencoder) as fallback for rare classes; synthetic defect generation (GAN-based) as last resort |
| **False positives disrupt production** | Operator trust erodes; line stoppages for false alarms | Conservative initial threshold; human-in-the-loop review mode for first 2 weeks; easy "dismiss" action in UI |
| **Copper surface reflectivity causes glare** | False detections or missed defects due to blown-out regions | Polarizer + dark-field illumination; HDR capture mode (alternating exposure); in-paint glare regions in preprocessing |
| **Inference latency exceeds frame budget** | Cannot keep up with 30–60 fps × 4 cameras on CPU-only hardware | Jetson Orin (GPU) as recommended spec; reduce resolution/fps as fallback; skip-frame strategy (infer every Nth frame, but capture all) |
| **Vibration or tube wobble** | Frames blurry; inconsistent defect positioning | Mechanical dampening on camera mount; shorter exposure time with brighter strobe lighting; motion deblur in preprocessing |
| **C++ codebase complexity** | Slower development velocity; harder debugging; team must be proficient in C++17/CMake | Phase 1 starts with Python-only prototyping to validate the model; C++ introduced in Phase 2 only after model is proven; well-defined IPC contract isolates C++ and Python concerns; CI/CD with sanitizers (ASan, TSan) and static analysis (clang-tidy) from day one |
| **Vendor SDK lock-in** | Switching camera brands requires C++ code changes | Abstract frame grabber interface (`IGrabber`) with SDK-specific implementations behind it; gstreamer fallback for development/testing without hardware |

---

## 10. Conclusion

EyeNet Inspect extends the platform's proven microservice architecture, camera management, and trigger/action pipeline into the industrial inspection domain. The copper tube example demonstrates that with 4 synchronized 5 MP global-shutter cameras, proper lighting, and a trained YOLOv8 defect detector, the system can reliably detect surface cracks, scratches, pits, and markings on a tube moving at 7 cm/sec — all running on the same class of mini PC hardware that EyeNet already deploys.

The primary novel investment is in **per-case model training**: collecting and labelling defect samples, training a domain-specific detector, and validating it for production use. Everything else — camera ingestion, streaming, recording, alerting, user management, frontend dashboards, VPN connectivity, and multi-site aggregation — reuses the existing EyeNet platform infrastructure.

---

## Appendix A: Compatible Camera Models for Copper Tube Inspection

The following 4 industrial GigE Vision cameras meet all requirements defined in Section 5.3: 5+ MP resolution, global shutter, ≥30 fps, PoE, hardware trigger support, and compact form factor suitable for a multi-camera ring bracket.

### A.1 Comparison Table

| Model | Resolution | Max FPS | Sensor | Pixel Size | Lens Mount | PoE | Est. Unit Cost (€) |
|---|---|---|---|---|---|---|---|
| **Basler ace2 a2A2448-75gcPRO** | 2448 × 2048 (5 MP) | 75 fps | Sony IMX547, 2/3", global shutter | 3.45 µm | C-mount | Yes | ~€650 |
| **FLIR Blackfly S BFS-PGE-50S5C-C** | 2448 × 2048 (5 MP) | 50 fps | Sony IMX547, 2/3", global shutter | 3.45 µm | C-mount | Yes | ~€700 |
| **Allied Vision Mako G-508C** | 2464 × 2056 (5.1 MP) | 46 fps | Sony IMX250, 2/3", global shutter | 3.45 µm | C-mount | Yes | ~€750 |
| **IDS uEye CP U3-5080CP-P-G** | 2464 × 2056 (5.1 MP) | 50 fps | Sony IMX250, 2/3", global shutter | 3.45 µm | C-mount | Yes (via PoE splitter) | ~€680 |

All four models share the same Sony Pregius global-shutter CMOS sensor family (IMX547 or IMX250) with 3.45 µm pixel size, giving consistent image characteristics across cameras — important for training a single model that works across all viewing angles.

### A.2 Recommended Lens Pairings

| Lens | Type | Working Distance | Why |
|---|---|---|---|
| **Computar M3514-MP2** | 35 mm, f/1.4, C-mount | 15–30 cm | Sharp macro performance; manual focus/aperture lock for vibration resistance; ~€200 |
| **Edmund Optics 50 mm C Series** | 50 mm, f/2.8, C-mount | 20–40 cm | Longer working distance for more mechanical clearance around the ring; ~€250 |
| **Moritex MTL-5545C** | 55 mm telecentric, C-mount | 18 cm (±5 mm) | Zero perspective error — critical if dimensional measurement (defect sizing) is required; ~€800 |

For the copper tube example, the **35 mm Computar** lens is the recommended starting point — it provides good magnification at the 15–25 cm working distance and balances cost against performance. Upgrade to a telecentric lens if the inspection requires precise defect sizing (e.g., rejecting cracks wider than a specific threshold).

### A.3 Recommended Selection for the 4-Camera Ring

| Position | Camera | Lens | Rationale |
|---|---|---|---|
| C1 (top) | Basler ace2 a2A2448-75gcPRO | Computar 35 mm | Highest frame rate (75 fps) at the primary viewing angle; Basler Pylon SDK is well-supported on Linux ARM64 (Jetson) and x86 |
| C2 (right) | Basler ace2 a2A2448-75gcPRO | Computar 35 mm | Same model for uniform image characteristics; all four share identical exposure/gain/trigger profiles |
| C3 (bottom) | FLIR Blackfly S BFS-PGE-50S5C-C | Computar 35 mm | Slightly different housing profile may fit better in the constrained bottom-mount position (under conveyor); Spinnaker SDK also well-supported |
| C4 (left) | Basler ace2 a2A2448-75gcPRO | Computar 35 mm | Same as C1/2 for uniformity |

**Alternative single-vendor configuration**: Four × FLIR Blackfly S (all identical) simplifies procurement and SDK licensing. The 50 fps max is sufficient for the 30 fps target with headroom.

### A.4 Multi-Camera Synchronization Setup

All four cameras are hardware-synchronized via a shared GPIO trigger line:

```
    ┌──────────────┐
    │ Function     │  GPIO output (strobe)
    │ Generator    │──▶ Line 0 on all 4 cameras (trigger input)
    │ (30 Hz TTL)  │
    └──────────────┘
           │
           └──────────▶ LED strobe controller (sync flash with exposure)
```

- A single TTL function generator (e.g., Arduino Nano or dedicated pulse generator) outputs a 30 Hz square wave.
- The signal is split to all 4 cameras' dedicated trigger input lines via a GPIO breakout board.
- Each camera is configured for "hardware trigger" mode — exposure begins on the rising edge.
- The same signal triggers LED strobes so illumination is synchronized to the exposure window, freezing motion at 7 cm/sec without motion blur.

### A.5 Estimated Camera + Lens Budget (4-Camera Ring)

| Item | Qty | Unit Cost (€) | Total (€) |
|---|---|---|---|
| Basler ace2 a2A2448-75gcPRO | 3 | 650 | 1,950 |
| FLIR Blackfly S BFS-PGE-50S5C-C | 1 | 700 | 700 |
| Computar M3514-MP2 35 mm lens | 4 | 200 | 800 |
| C-mount spacer rings (fine-focus adjustment) | 4 | 15 | 60 |
| GPIO trigger breakout + cables | 1 kit | 80 | 80 |
| GigE PoE injector or PoE switch (8-port) | 1 | 150 | 150 |
| **Total camera + lens hardware** | | | **~€3,740** |

This sits comfortably within a typical industrial inspection station budget. The edge PC hardware (Section 5.7) adds ~€800–1,200, bringing the total per-station hardware cost to approximately **€4,500–5,000**.
