# Stream of Coding

- [x] if pre-encoder callback, replace standard encoder with TimestampH264Encoder
- [x] clarify areas of concern between base/impl and config
- [x] integrate camera status with acquisition status
- [x] make sure that config/acquisition params are passed from acq->camera
- [x] Acquisition has to make TTL Emitter/Receiver
  -> then pass Emitter.trigger as pre-encoder callback
  -> Receiver.start recording on acquisition start
- [x] TEST with __main__ for Acquisition before putting into AcquisitionProcess
- [x] AcquisitionProcess has to implement message pattern to handle commands/status (api->AcqProcess->Acquisition)
- [x] Conductor should make session uuid -> hand it down to Agent -> file naming for Acquisition
  -> save main uuid and then make per-device dataset IDs? Dir structure? /subject/session/device/files ?
- [/] copy data after each acquisition or have central webpage that warns when `df -h` overflows?

================================================================
- [x] ok we have designed the new Acq/Cam config structure, need to integrate this
- [x] fixed the config classes for Camera/TTL/Picamera2
- [x] ! make default config for camera
- [x] now we need to check that this actually runs the Camera object and the method work
- [x] can make object, first check: `initialize_hardware`, works
- [x] finish start_preview/rec methods in Impl -> then test preview/rec
  - update picam2 implementation to correctly set given camera Config & fix params after `start_recording`
- [x] Acq config -> Acq object & passing info (file paths!) to Camera
- [x] then test running test acquisitions on `alexandria`
- [x] once we know that the Acq/Cam/picam2 work, move on to `Agent` + API + AcqProcess
- [x] acq config -> files, ttl, camera (base / impl / encoder) param flow works => test
- [x] AgentStatus should return storage available in data dir
- [x] AcqProcess: take Agent-like config -> start Acq/Cam + listen to commands
  - DEBUG
    - [x] get config, init of Acq object
    - [x] handler methods: start_preview, start_recording, stop, get_status
    - [x] stop should trigger process stop after sending Log info
    - [x] general process logger as Mixin class for Process
    - [x] AcqProcess Manager needs direct control methods that handle the Command messages
- [x] API endpoints to call AcqProcess methods
- [x] `Agent` loop to start API server + AcqProcess, then infinite lifecyle/KeyboardInterrupt

================================================================
DEBUG for: Agent/Process/Acq
- [x] Acq Process methods work
- [x] Agent starting/stopping Acq Process works
- [x] Agent passing other commands to acq process works in test method instead of `run-forever`
  - but it's more complicated as doing this manually requires calls to disk check/make paths, then start process
- [x] Agent-API endpoints & req/resp models defined & call correct command on process manager
  - [x] Agent refuse acquisition, if disk space insufficient for `max-recording-time * video quality => estimated video size`
- [x] return actual `framerate` for debugging -> /acquisition/status or config ?
    - we get the total number of frames from TTL emitter for now
- [x] Integrate log system, so that Agent gets all logs from Process/Acq/Camera via log_queue -> catch in Agent log files

================================================================
- [x] Agent CLI + run method
- [x] Agent-as-a-Service -> `systemd`
- [x] test Agent in Service

================================================================
- [ ] AgentClient on its own
- [ ] Conductor from config vs ConductorConfig
- [ ] Conductor heartbeat/recording duration tasks -> no threads ?
- [ ] Conductor contextmanager
- [ ] CLI for Acquisition via AgentClient [assume Agent is running]
- [ ] CLI for Conductor to run ensemble from template config
- [ ] test Agent service + Conductor contextmanager

================================================================
NPX manipulator tracking
- manipulator API client to get position/status
  - axis order/direction switches for real-world matching model
- coordinate system: manipulator ~ atlas [MRI stretch + -5° pitch + bregma-lambda distance]
  + relative from bregma/zero
- position database
 - save position with label + timestamp (e.g. subject, session, ...)
 - load positions by selection (e.g. all for subject)
 - frontend
   - display atlas
   - controls to set manipulator/atlas/position options
- > live update of manipulator position on frontend
- > external comms: send CCF region list to OpenEphys


================================================================
DEBUG for: Conductor
- [ ] write AgentConnection interface class to use API version-specific calls
- [ ] Conductor with attribute .agents -> list of Agent instances + poll their status
  -> need a small class to hold the Agent info & manage communication (`AgentConnection`?==API endpoints)
    -> API endpoints: status, preview, start recording, stop (both preview and recording)
- Conductor
  - Conductor.from_ensemble_acquisition_config(acq_config)
    - check that Agent urls are reachable
    - make AgentConnections for each Agent
  - initialize acquisition
    - for each AgentConnection, send AcqConfig
    - Agent initializes acquisition Process -- NO recording yet
  - monitor status / heartbeat -> update AgentStatus[agent+acq info] for each AgentConnection
  - `start_preview`/`start_recording`/`stop_acquisition`
    - for each AgentConnection, call respective method
  - AgentConnection: hold actual API endpoint urls + methods to call API endpoints
  - Conductor
      - heartbeat/status check on Agents
      - start preview / _start_preview_one(agent_name) / stop_preview
      - start acquisition / _start_acquisition_one(agent_name) / stop_acquisition
      - get_agent_status(agent_name)
      - get_acquisition_status(agent_name)
      - stop all / shutdown all
- integration test for using `Conductor` as object / in contextmanager / from CLI

================================================================
DEBUG for: CLI
- [ ] agent, with service
- [ ] conductor, which should mirror conductor init/enter method args

-> [ ] CLEAN UP pydantic models in `config` (mixed settings and API models)
- CLIs
  - Acquisition CLI to test Acquisition object standalone
  - Agent CLI to start Agent service
  - Conductor CLI to run acquisition from EnsembleAcqConfig file


================================================================
Install systemd service
```shell

sudo cp rce-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rce-agent
sudo systemctl start rce-agent

```

================================================================
"""
Input
    CameraConfig (picamera2, ttl)
    AcquisitionSettings (max duration)
    instance_name == Agent.instance_name

Then we make:
    Camera
    write metadata once camera returns as initialized, blocking anyway
        -> Acquisition config & Camera.get_camera_controls
    TTLEmitter -> .trigger == pre_encoder_callback
    TTLReceiver -> start recording

Methods
    (prop) state: pass from camera ?
    start_preview -> camera.start_preview
    start_recording -> TTLReceiver.start_recording + camera.start_recording
    stop -> if TTLReceiver recording, stop_recording. then try to stop camera
    write_camera_metadata
    get_status: camera.state, camera.acq-start-time, camera.last-error,
        instance_name, self.config

- metadata: Agent writes requested Acquisition config & Camera.get_camera_controls
"""

================================================================
## Install venv on rpi to run required package versions
```shell
sudo apt update
sudo apt install python3-picamera2 --no-install-recommends

mkdir ~/venvs
python -m venv ~/venvs/rce --system-site-packages
source venvs/rce/bin/activate
pip install --upgrade pip
pip install "pydantic>2" fastapi numpy
```
================================================================

"""
Logic for config

- on each RPi, start Agent with AgentConfig: data dir, log dir, api host/port to expose, ...
    - agents should run as system services -> systemd service files ?

- create Conductor
    - for acquisition, give Conductor an AcquisitionConfig
        - either as contextmanager (with Conductor.start_acquisition(acq_config): ...)
        - or as method call (session_id = Conductor().start_acquisition(acq_config))

    -> Conductor needs AgentStatus model to save heartbeat/recording status from Agents

    - acquisition parameters for:
        - cameras (resolution, framerate, saturation, ...)
        - TTL params
        - acquisition name for file naming / metadata
        - heartbeat interval to check on Agents
        - max acquisition time

============================

AgentConfig
    - api host/port
    - log level/file location

AcquisitionConfig (acquisition-specific & camera-specific)
    - max acquisition time
    - hearbeat interval to check on Acq Agents

    - Agent / CameraConfig
    - TTLParams
    - AcquisitionFiles

    - [added during runtime] AcquisitionMetadata

============================
- how to match AcqConfigs with specific camera resolutions to cameras on Agents?
    -> not an issue if Conductor does not need to know about Agents before starting acquisition
- data dirs on RPIs are in standard location, so that copy scripts are straightforward
"""



"""
CAMERA CONTROLS

AeEnable: True -> turn off before recording
AeFlickerMode: FlickerOff
AnalogueGain: will be fixed with AeEnable=False
AwbEnable: True -> turn off before recording
ExposureTime: -> will be set by FrameDurationLimits
FrameDuration: -> will be set by FrameDurationLimits
FrameDurationLimits: !! FPS !!
NoiseReductionMode: 1=Fast, 0=Off,  lctrl.draft.NoiseReductionModeEnum.Fast -- from libcamera import controls as lctrl
Saturation: 0-32, 1=normal, 0=greyscale
Brightness: -1=dark, 0.0=normal, 1=bright

values to fixate before recording:
    AeEnable=False
    AwbEnable=False
    ExposureTime
    AnalogueGain
    ColourGains
    ColourTemperature
    Brightness
    Saturation

AeConstraintMode: ?
AeExposureMode: ?
AeFlickerMode: FlickerOff
AeFlickerPeriod: ..
AeMeteringMode: ..
AfMetering: Auto
AfMode: Manual
AfPause: only in AfMode-Auto/Continuous
AfSpeed: ..
AfTrigger: ..
AfWindows: ..
AwbMode: ..
Brightness: -1=dark, 0.0=normal, 1=bright
ColourCorrectionMatrix: ..
ColourGains: ..
ColourTemperature: ..
Contrast: ..
DigitalGain: ..
ExposureValue: [in stops], ..
HdrChannel: ..
HdrMode: Off
LensPosition: [dioptres], have no auto zoom
ScalerCrop: [rectangle], ..
SensorTimestamp: [read-only ?]
SensorBlackLevels: ..
Sharpness: 0-16, 1=normal
SyncMode: Off
SyncReady: ..
SyncTimer: ..
SyncFrames: ..

Camera logic
- MAKE INSTANCE
    - get config + default output path/name
    - resolve args:
        framerate->FrameDurationLimits
        resolution->video config streams main/lores
        transform dict -> libcamera.Transform
    - make picam2
    - add video configuration: main, stream, buffer, controls={ esp.: FrameDurationLimits}
    - picam2 start()

- START PREVIEW STREAM: picam2.start_recording(jpeg_encoder, FileOutput(streaming_output), name="lores")
    -> now is previewing -> LOG THE START TIME
- STOP PREVIEW STREAM: picam2.stop_recording() -> set camera state to STOPPED, does not shut down Acquisition
- START VIDEO
    - after warmup (from START TIME): .capture_metadata() -> FREEZE: AeEnable=False, AwbEnable=False, ExposureTime, AnalogueGain, ColourGains

    - encoder: H264 x timestamps
        - framerate, bitrate=None, repeat=False(for stream?), iperiod=None
        - !! CALLBACK METHOD FOR TTL-OUT given inside Cam object, not in config !!
    - FileOutput
    - picam2.start_recording(encoder, output, pts=timestamp file, name="main")
== runs recording ...
- STOP
    - picam2.stop_recording(), no args to stop all
    - picam2.close()

"""


"""
AgentConfig -> Agent
Ensemble Acquisition Config -> Conductor -> splits it and sends only Agent-specific Acq Config
AcquisitionConfig + General settings -> API -> Agent(has AgentInfo: instance_name, data root)

Ensemble-ACQ-CONFIG
- uuid
- start datetime
- max duration
- acq path / basename / timestamp==start time

- camera ensemble [dict, key=instance_name, values=Acq Configs]

ACQ-CONFIG
- ip/port for Agent.API
- CameraConfig

Agent -> AgentInfo(instance_name, data root) + CameraConfig(TTL + Camera) -> Acquisition
Acquisition -> makes full Acq Paths -> Camera, TTL, ...

! camera ensemble keys irrelevant as only url/ip used to send config


CameraAcquisitionConfig
- camera, ttl
- api ip:port

EnsembleAcquisitionConfig
- camera ensemble dict [instance_name: CameraAcquisitionConfig]
- PLUS runtime params like uuid/start time



1. make EnsembleAcquisitionConfig(acq path/name/uuid/time, max(rec), camera list [name: config])
2. Conductor loop: each camera config + params -> send to Agent
3. Agent gets Acq Request, adds data_root / instance_name -> run Acq -> Acq makes paths, runs Camera



"""
