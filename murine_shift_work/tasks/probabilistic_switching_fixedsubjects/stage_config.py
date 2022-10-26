serial_port = "/dev/ttyUSB0"
pmin = 1
pmax = 999
vel = 200
config_for_all_stages = {
    "stage_tower_setup_default": {
        "connection": {
            "serial_port": serial_port,
            "baudrate": 115200,
            "timeout": 0.1,
        },
        "axes": {
            "x": {
                "id": 11,  # motor ID
                # "position_unit": "raw",  # raw, deg  # FIXME: only support RAW units for commands
                "position_min": pmin,  # 0 - 1023 for raw or 60-300(?) for deg
                "position_max": pmax,
                "velocity_max": vel,  # 0=max, 1-255
                "operating_mode": "OP_POSITION",  # OP_...
                # "position_to_meter": 0.001,  # scale factor
            },
            "y": {
                "id": 12,  # motor ID
                # "position_unit": "raw",  # raw, deg  # FIXME: only support RAW units for commands
                "position_min": pmin,  # 0 - 1023 for raw or 60-300(?) for deg
                "position_max": pmax,
                "velocity_max": vel,  # 0=max, 1-255
                "operating_mode": "OP_POSITION",  # OP_...
                # "position_to_meter": 0.001,  # scale factor
            },
            "z": {
                "id": 13,  # motor ID
                # "position_unit": "raw",  # raw, deg  # FIXME: only support RAW units for commands
                "position_min": pmin,  # 0 - 1023 for raw or 60-300(?) for deg
                "position_max": pmax,
                "velocity_max": vel,  # 0=max, 1-255
                "operating_mode": "OP_POSITION",  # OP_...
                # "position_to_meter": 0.001,  # scale factor
            },
        },
        "known_positions": {
            # "mid": {"x": {"position_raw": 400}},
            # "back": {"x": {"velocity_max": 50, "position_raw": 280}},
            # "front": {"x": {"velocity_max": 250, "position_raw": 550}},
        },
    },
    "stage_tower_setup_1": {
        "connection": {
            "serial_port": serial_port,
            "baudrate": 115200,
            "timeout": 0.1,
        },
        "axes": {
            "x": {
                "id": 11,  # motor ID
                # "position_unit": "raw",  # raw, deg  # FIXME: only support RAW units for commands
                "position_min": 100,  # 0 - 1023 for raw or 60-300(?) for deg
                "position_max": 600,
                "velocity_max": vel,  # 0=max, 1-255
                "operating_mode": "OP_POSITION",  # OP_...
                # "position_to_meter": 0.001,  # scale factor
            },
            "y": {
                "id": 12,  # motor ID
                # "position_unit": "raw",  # raw, deg  # FIXME: only support RAW units for commands
                "position_min": 300,  # 0 - 1023 for raw or 60-300(?) for deg
                "position_max": 800,
                "velocity_max": vel,  # 0=max, 1-255
                "operating_mode": "OP_POSITION",  # OP_...
                # "position_to_meter": 0.001,  # scale factor
            },
            "z": {
                "id": 13,  # motor ID
                # "position_unit": "raw",  # raw, deg  # FIXME: only support RAW units for commands
                "position_min": 280,  # 0 - 1023 for raw or 60-300(?) for deg
                "position_max": 500,
                "velocity_max": vel,  # 0=max, 1-255
                "operating_mode": "OP_POSITION",  # OP_...
                # "position_to_meter": 0.001,  # scale factor
            },
        },
        "known_positions": {
            "mid": {
                "x": {"position_raw": 400},
                "y": {"position_raw": 570},
                "z": {"position_raw": 400},
            },
            # "last": {"x": {"position_raw": 250}, "y": {"position_raw": 250}, "z": {"position_raw": 250}},
            "back": {"y": {"velocity_max": 250, "position_raw": 750}},
            "front": {"y": {"velocity_max": 250, "position_raw": 530}},
        },
    },
}
