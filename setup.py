from setuptools import find_packages
from setuptools import setup

setup(
    name="murine_shift_work",
    version="0.0.1",
    packages=find_packages(),
    url="-",
    license="-",
    author="LBR",
    author_email="L.B.Rollik@pm.me",
    description="Shift Work: Behaviour acquisition with PyBpod",
    install_requires=[
        "opencv-python",
        "PyQtWebEngine",
        "pyqtgraph",
        "numpy",
        "scipy",
        "pandas",
        "matplotlib",
        "pybpod",
        "sounddevice",  # might require: sudo apt-get install libportaudio2
        "pre-commit",
        "tqdm",
        "gitpython",
        "rich",
        "myterial",
    ],
    extras_require={
        "video": [
            "rpi_camera_colony @ git+https://llrrr@bitbucket.org/lbrcoding/rpi_camera_colony.git#egg=rpi_camera_colony"
        ],
        "dev": [],
    },
)
