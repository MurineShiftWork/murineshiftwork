# RPi Camera Ensemble - System Specification

## System Overview

A distributed camera control system for synchronized multi-camera acquisition on Raspberry Pi devices. The system orchestrates multiple camera nodes from a central conductor, with each node running an agent that manages local camera acquisition with GPIO-based TTL synchronization.

### Core Components

- **Conductor**: Central orchestrator managing multiple remote camera agents
  - Instantiated via `Conductor.from_config()`
  - Maintains `ensemble` dict registry of remote agents
  - Supports context manager for resource cleanup
- **Agent**: FastAPI server running on each Pi, managing local acquisition
  - REST endpoints: `/status`, `/start`, `/stop/{uuid}`, `/preview`
  - Runs `acquisition.runner.run_local()` for camera control
  - Deployed via systemd service or docker-compose
- **Acquisition**: Camera control layer with TTL timestamp support
  - Factory pattern: `BaseCamera` → `PiCamera` or `PiCamera2`
  - Can be called from Agent, Python process, or CLI directly
- **Config**: Configuration management
  - TOML format with Pydantic validation
  - Hierarchical configuration for conductor, agent, and camera
- **CLI**: Command-line interface with three entry points
  - `conductor`: Orchestration commands
  - `agent`: Local agent server
  - `acquisition`: Direct camera control

## Architecture Layers

```
┌─────────────┐
│  Conductor  │ (Central Control)
│ .ensemble{} │ Registry of remote agents
└──────┬──────┘
       │ HTTP/WebSocket
┌──────▼──────┐
│    Agent    │ (FastAPI per Raspberry Pi)
│  /status    │ Endpoints for control
│  /start     │
│  /stop/{id} │
│  /preview   │
└──────┬──────┘
       │ runner.run_local()
┌──────▼──────┐
│ Acquisition │ (Session Management)
└──────┬──────┘
       │ Factory Pattern
┌──────▼──────┐
│ BaseCamera  │ (Hardware Interface)
│  ├─PiCamera │ Legacy stack
│  └─PiCamera2│ New stack
└─────────────┘
```

## Component Interactions

### Orchestration Flow
```
Conductor orchestrates Agents → Agents run Acquisitions → Acquisitions control Cameras
```

### Camera Factory Pattern
```
Acquisition → CameraConfig → Backend Selection → Camera Instance
                                ├─ AUTO: Detect available
                                ├─ PICAMERA: Force legacy (PiCamera)
                                └─ PICAMERA2: Force new stack (PiCamera2)
```

### TTL Synchronization Flow
```
Frame Capture → TTL OUT Pin → External Trigger
External Event → TTL IN Pin → Timestamp Recording
```

### Session Management
```
Conductor.start_recording() → Agent.start(uuid) → Acquisition.start_recording(uuid)
Conductor.stop_recording()  → Agent.stop(uuid)  → Acquisition.stop_recording(uuid)
```
- Session/acquisition UUIDs prevent accidental stops
- Health check pings maintain connection status

### Deployment Architecture
```
Option 1: systemd service
- Agent runs as system service on each Pi
- Auto-start on boot
- Managed via systemctl

Option 2: docker-compose
- Containerized agents
- Easier dependency management
- Network isolation
```

## Configuration Schema

### Conductor Configuration (TOML)
```toml
[conductor]
name = "main_conductor"
heartbeat_interval = 5.0

[conductor.ensemble]
cam01 = "http://192.168.1.10:8000"
cam02 = "http://192.168.1.11:8000"
cam03 = "http://192.168.1.12:8000"
```

### Agent Configuration (TOML)
```toml
[agent]
instance_name = "cam01"
host = "0.0.0.0"
port = 8000

[agent.acquisition]
data_path = "/data/recordings"
backend = "auto"  # auto, picamera, picamera2
```

### Camera Configuration
- **Resolution**: (width, height) tuple
- **Framerate**: Target FPS
- **TTL Pins**: GPIO pins for input/output synchronization
- **Video Settings**: Quality, format, encoding parameters
- **Preview Settings**: Warmup delay, auto-exposure/white-balance

### Acquisition Configuration
- **Instance Name**: Unique camera identifier
- **Data Path**: Base directory for recordings
- **Acquisition Name**: Experiment/session identifier
- **Backend**: Camera implementation selection
- **Streaming**: Optional network streaming settings


## State Machine

```
IDLE ──preview──> PREVIEW ──record──> RECORDING
 ▲                    │                    │
 └────stop_preview────┘                    │
 ▲                                         │
 └──────────stop_recording─────────────────┘
```

> ! Logic for preview vs recording:
> (Conductor or standalone ->) Agent → Acquisition `create`
> -> `preview start/stop` -> `record start/stop  `
> -> `stop_recording`: from `RECORDING` to `IDLE`


## Usage Patterns

### Python API - Direct Acquisition

```python
from rpi_camera_ensemble.acquisition import (
    Acquisition, AcquisitionConfig, CameraConfig, CameraBackend
)
from pathlib import Path

# Configure camera
camera_config = CameraConfig(
    resolution=(1920, 1080),
    framerate=30,
    ttl_out_pin=8,
    ttl_in_pin=16,
    video_quality=23
)

# Configure acquisition
config = AcquisitionConfig(
    camera_config=camera_config,
    instance_name="cam01",
    data_path=Path("/data"),
    acquisition_name="experiment_001",
    backend=CameraBackend.AUTO
)

# Run acquisition
with Acquisition(config) as acq:
    acq.start_preview()
    session_id = acq.start_recording()
    # ... recording ...
    results = acq.stop_recording(session_id)
```

### Python API - Agent Server

```python
from rpi_camera_ensemble.agent import Agent
from rpi_camera_ensemble.acquisition.runner import run_local

# Start agent server with config
agent = Agent.from_config("agent_config.toml")
agent.run(host="0.0.0.0", port=8000)

# Agent REST API endpoints:
# GET  /status          - Current state and statistics. Also returns UUID, so that session can be stopped manually.
# POST /start           - Start recording, returns session UUID
# POST /stop/{uuid}     - Stop recording with UUID validation
# POST /preview         - Start/stop preview mode

# Direct local execution (called by agent internally)
run_local(config)  # Runs acquisition without agent server
```

### Python API - Conductor Orchestration

```python
from rpi_camera_ensemble.conductor import Conductor

# Initialize conductor with config
with Conductor.from_config("conductor_config.toml") as conductor:
    # conductor.ensemble contains registry of remote agents
    # e.g., {"cam01": "http://192.168.1.10:8000",
    #        "cam02": "http://192.168.1.11:8000"}

    # Check health of all agents
    conductor.health_check_all()

    # Start all cameras with synchronized session
    conductor.start_preview_all()
    session_id = conductor.start_recording_all()

    # Stop specific camera with UUID validation
    conductor.stop_recording("cam01", session_id)

    # Stop all cameras with UUID validation
    conductor.stop_recording_all(session_id)
```

### CLI - Acquisition Mode

```bash
# Direct camera control on single Pi
rpi-camera acquire \
    --config camera_config.toml \
    --name experiment_001 \
    --duration 60

# With TTL settings
rpi-camera acquire \
    --resolution 1920x1080 \
    --fps 30 \
    --ttl-out 8 \
    --ttl-in 16 \
    --output /data/recordings
```

### CLI - Agent Mode

```bash
# Start agent server on each Pi
rpi-camera agent \
    --config agent_config.toml \
    --host 0.0.0.0 \
    --port 8000

# Deploy via systemd service
sudo systemctl enable rpi-camera-agent
sudo systemctl start rpi-camera-agent
sudo systemctl status rpi-camera-agent

# Or deploy via docker-compose
docker-compose up -d agent
```

### CLI - Conductor Mode

```bash
# Start conductor for orchestration
rpi-camera conductor \
    --config conductor_config.toml

# Interactive conductor shell
rpi-camera conductor shell
>>> conductor.status()
>>> conductor.start_all()
>>> conductor.stop_all()
```

## File Organization

### Output Structure
```
/data/
├── experiment_001/
│   ├── cam01_20250114_143022.h264
│   ├── cam01_20250114_143022_metadata.json
│   ├── cam01_20250114_143022_ttl_out.csv
│   └── cam01_20250114_143022_ttl_in.csv
└── experiment_002/
    └── ...
```

### Package Structure
```
rpi_camera_ensemble/
├── acquisition/
│   ├── base_cam.py      # Abstract camera interface
│   ├── picam.py         # Legacy PiCamera implementation
│   ├── picam2.py        # PiCamera2 implementation
│   └── acquisition.py   # Main acquisition controller
├── agent/
│   ├── agent.py         # Agent server logic
│   └── api.py           # FastAPI endpoints
├── conductor/
│   └── conductor.py     # Orchestration logic
├── config/
│   ├── schema.py        # Pydantic models
│   └── loader.py        # TOML/JSON loaders
├── cli/
│   └── main.py          # Click CLI commands
└── protocol/
    └── messages.py      # Communication protocol

```

## Communication Protocol

### Health Check
```json
{"type": "ping", "timestamp": 1234567890}
{"type": "pong", "timestamp": 1234567890, "state": "idle"}
```

### Commands
```json
{"type": "command", "action": "start", "session_id": "uuid-here"}
{"type": "command", "action": "stop", "session_id": "uuid-here"}
```

### Status
```json
{
    "type": "status",
    "state": "recording",
    "session_id": "uuid-here",
    "frames": 1500,
    "duration": 50.0
}
```

## Development Process

### Phase 1: Core Components
1. Implement base camera abstraction
2. Create PiCamera/PiCamera2 implementations
3. Build acquisition controller with state management
4. Add TTL GPIO support and timestamp recording

### Phase 2: Agent Layer
1. Create FastAPI server with REST endpoints
2. Implement session management
3. Add health check and status reporting
4. Create systemd service configuration

### Phase 3: Conductor
1. Build conductor orchestration logic
2. Implement ensemble management
3. Add WebSocket support for real-time updates
4. Create coordination protocols

### Phase 4: CLI & Configuration
1. Create Click-based CLI interface
2. Implement TOML/JSON configuration loading
3. Add configuration validation with Pydantic
4. Create example configurations

### Phase 5: Testing & Deployment
1. Unit tests for camera implementations
2. Integration tests for agent/conductor
3. Docker containerization
4. Documentation and examples

## Key Design Decisions

- **Dual Camera Stack Support**: Maintains compatibility with legacy PiCamera while supporting new PiCamera2
- **UUID Session Management**: Prevents accidental stops and enables tracking
- **TTL Timestamp Synchronization**: Hardware-level frame synchronization via GPIO
- **Factory Pattern**: Runtime camera backend selection based on availability
- **State Machine**: Clear acquisition states preventing invalid operations
- **Distributed Architecture**: Scales from single camera to multi-node ensemble
