import time

import serial

# AVAILABLE_COMMANDS = {
#     "left_limit": b"A",
#     "left_increment": b"a",
#     "right_limit": b"D",
#     "right_increment": b"d",
#     "forward_limit": b"F",
#     "forward_increment": b"w",
#     "backward_limit": b"R",  # fixme: inconsistent. should be "s"
#     "backward_increment": b"s",
#     "origin_xy": b"H",
#     "origin_right": b"h",  # x=0
# }


class Stage:
    serial_port = None
    baudrate = None
    device = None

    reset_on_connect = True

    stage_range = (-1, 1)
    stage_step_size = 1
    stage_max_steps = (None, None)  # range / step size
    starting_position_in_steps = 0

    _position = 0

    command_increment = b""
    command_decrement = b""
    command_to_min = b""
    command_to_max = b""

    def __init__(
        self,
        serial_port: str = None,
        baudrate: int = 9600,
        reset_on_connect: bool = True,
        stage_range: list = (-1, 1),
        stage_step_size: float = 1.0,
        starting_position_in_steps: int = 0,
        command_increment: bytes = b"",
        command_decrement: bytes = b"",
        command_to_max: bytes = b"",
        command_to_min: bytes = b"",
    ):
        """

        :param serial_port:
        :param baudrate:
        :param reset_on_connect:
        :param stage_range:
        :param stage_step_size:
        :param starting_position_in_steps:
        :param command_increment:
        :param command_decrement:
        :param command_to_max:
        :param command_to_min:
        """
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.device = serial.Serial(port=serial_port, baudrate=baudrate)
        self.reset_on_connect = reset_on_connect

        self.stage_range = stage_range
        self.stage_step_size = stage_step_size
        self.stage_max_steps = [
            round(limit / self.stage_step_size) for limit in self.stage_range
        ]
        self.starting_position_in_steps = starting_position_in_steps
        self.position = self.starting_position_in_steps

        self.command_increment = command_increment
        self.command_decrement = command_decrement
        self.command_to_max = command_to_max
        self.command_to_min = command_to_min

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, p=None):
        self._position = p

    @property
    def position_in_units(self):
        return self.position * self.stage_step_size

    @property
    def at_range_limit(self):
        return (
            True
            if any([self.position >= abs(x) for x in self.stage_max_steps])
            else False
        )

    def move(self, target: bytes = None):
        assert isinstance(target, bytes)
        if self.device is None:
            return False

        self.device.write(target)

    def move_increment(self):
        # if self.at_range_limit:
        #     return False

        self.move(target=self.command_increment)
        self.position += 1
        return True

    def move_decrement(self):
        # if self.at_range_limit:
        #     return False

        self.move(target=self.command_decrement)
        self.position -= 1
        return True

    def move_to_max(self):
        # if self.position == max(self.stage_range):
        #     return False

        self.move(target=self.command_to_max)
        self.position = self.stage_range[-1]

    def move_to_min(self):
        self.move(target=self.command_to_min)
        self.position = self.stage_range[0]

    def reset_to_initial_position(self):
        steps_to_move = self.position - self.starting_position_in_steps
        if steps_to_move == 0:
            return

        for _ in range(abs(steps_to_move)):
            if steps_to_move > 0:
                self.move(target=self.command_decrement)
            else:
                self.move(target=self.command_increment)

            time.sleep(0.100)

        self.position = self.starting_position_in_steps


class XYStageController:
    """API for dual-lick spout actuators

    w, a, s, d = move one increment
    R, A, F, D = most extreme positions
    H = return to (x,y) zero
    h = return to x zero only

    moving from -x:+x corresponds to moving from right:left
    moving from -y:+y corresponds to moving from backward:forward

    origin x,y is most backward, most right position

    ranges
        x/lateral: +/- 7.0 mm ~ 2 * 14 steps
        y/parallel: -9:+10 ~ 2 * 19 steps

    step size in both x and y: 500µm

    """

    serial_port = None
    baudrate = None
    device = None

    reset_on_connect = True

    stage_x = None
    stage_y = None
    _position = None

    class MoveCommands:
        left_limit = b"A"
        left_increment = b"a"

        right_limit = b"D"
        right_increment = b"d"

        forward_limit = b"F"
        forward_increment = b"w"

        backward_limit = b"R"  # inconsistent. should be "s" in arduino code
        backward_increment = b"s"

        origin_xy = b"H"
        origin_x = b"h"

    def __init__(
        self,
        serial_port: str = None,
        baudrate: int = 9600,
        reset_on_connect: bool = True,
        xrange: list = None,  # invert axis step numbering by reversing this tuple
        yrange: list = None,
        step_size_x: float = None,
        step_size_y: float = None,
    ):
        super(XYStageController, self).__init__()
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.device = serial.Serial(port=serial_port, baudrate=baudrate)
        self.reset_on_connect = reset_on_connect

        self.stage_x = Stage(
            serial_port=None,
            baudrate=9600,
            reset_on_connect=True,
            stage_range=xrange,
            stage_step_size=step_size_x,
            starting_position_in_steps=0,
            command_increment=b"a",
            command_decrement=b"d",
            command_to_max=b"A",
            command_to_min=b"D",
        )
        self.stage_x = Stage(
            serial_port=None,
            baudrate=9600,
            reset_on_connect=True,
            stage_range=yrange,
            stage_step_size=step_size_y,
            starting_position_in_steps=0,
            command_increment=b"w",
            command_decrement=b"s",
            command_to_max=b"F",
            command_to_min=b"R",
        )

        if self.reset_on_connect:
            self.move_to_origin()

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, x=None):
        # todo: assert in range
        self._position = x  # KEEP track of position after coming from origin

    def move_to_origin(self):
        self.stage_x.move(target=self.MoveCommands.origin_xy)
        self.stage_x.position = 0
        self.stage_y.position = 0

    def center_x(self):
        self.stage_x.move(target=self.MoveCommands.origin_x)
        self.stage_x.position = 0

    def center_y(self):
        self.stage_y.reset_to_initial_position()
        # starting_position = self.stage_y.position
        # if starting_position == 0:
        #     return
        #
        # for _ in range(abs(starting_position)):
        #     if starting_position > 0:  # move back, else forward
        #         self.move(target=self.MoveCommands.backward_increment)
        #         self.stage_y.decrement_position()
        #     elif starting_position < 0:
        #         self.move(target=self.MoveCommands.forward_increment)
        #         self.stage_y.increment_position()
