from os import path

from setuptools import find_packages
from setuptools import setup

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

with open(path.join(this_directory, "LICENSE"), encoding="utf-8") as f:
    license_text = f.read()


setup(
    name="murine_shift_work",
    version="0.2.2",
    description="Murine Shift Work: Data acquisition software framework (developed for murine research)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=[
        "configobj",
        "tqdm",
        "rich",
        "pyzmq",  # for remote ephys module
        # "PyQt5",  # fixme: remove for platform compatibility
        # "pyqtgraph",  # fixme: remove for platform compatibility
        # "PySimpleGUI",  # fixme: remove for platform compatibility
        # "myterial",  # fixme: only useful for plotting
        "numpy",
        "scipy",
        "pandas",
        # "matplotlib",  # fixme: not required at all. only in water/sound calibration plotting
        # "seaborn",  # fixme: not required at all. only in water/sound calibration plotting
        "pybpod-api",  # for pybpod.
        "safe-and-collaborative-architecture",  # for pybpod.
        "sounddevice",  # for sound output. might require: sudo apt-get install libportaudio2
        "rpi_camera_colony",  # for video recordings
    ],
    extras_require={
        "dev": [
            "black",
            "pytest-cov",
            "pytest",
            "gitpython",
            "coverage>=5.0.3",
            "bump2version",
            "pre-commit",
            "flake8",
        ],
    },
    python_requires=">=3.6",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "murineshiftwork = murine_shift_work.__init__:run_cli",
            "remote-ephys-controller = murine_shift_work.__init__:run_remote_ephys",
        ],
    },
    url="https://llrrr@bitbucket.org/lbrcoding/murine_shift_work.git",
    author="Lars B. Rollik",
    author_email="L.B.Rollik@protonmail.com",
    license=license_text,
    zip_safe=True,
    include_package_data=True,
)
