from open_ephys_remote.cli import parse_args
from open_ephys_remote.controller import OERemoteController


def run():
    args = parse_args()
    args_dict = args.parse_args().__dict__

    ctrl = OERemoteController(**args_dict)


if __name__ == "__main__":
    run()
