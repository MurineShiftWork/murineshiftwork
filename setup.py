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
    version="0.1.0.dev0",
    description="Murine Shift Work: Behaviour protocols via pybpod",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=[
        "configobj",
        # "opencv-python==3.4.5.20",
        # "PyQtWebEngine",
        "pyqtgraph",
        "numpy",
        "scipy",
        "pandas",
        "matplotlib",
        "pybpod-api",
        "safe-collaborative-architecture",  # required by pybpod
        "sounddevice",  # might require: sudo apt-get install libportaudio2
        "tqdm",
        # "gitpython",
        "rich",
        "myterial",
        "PySimpleGUI",
        "rpi_camera_colony @ git+https://llrrr@bitbucket.org/lbrcoding/rpi_camera_colony_dev.git#egg=rpi_camera_colony",
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
            "msw_gui = murine_shift_work.__init__:run_gui",
            "murineshiftwork = murine_shift_work.__init__:run_cli",
        ],
    },
    url="URL-URL-URL",
    author="Lars B. Rollik",
    author_email="L.B.Rollik@protonmail.com",
    license=license_text,
    zip_safe=True,
    include_package_data=True,
)
