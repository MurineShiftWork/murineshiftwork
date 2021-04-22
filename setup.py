from setuptools import find_packages
from setuptools import setup

setup(
    name="pybpod_tools",
    version="0.0.1",
    packages=find_packages(),
    url="-",
    license="-",
    author="LBR",
    author_email="L.B.Rollik@pm.me",
    description="PyBpod protocols",
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
)
