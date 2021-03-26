from setuptools import setup
from setuptools import find_packages

setup(
    name="pybpod_tools",
    version="0.0.1",
    packages=find_packages(),
    url="-",
    license="-",
    author="LBR",
    author_email="L.B.Rollik@pm.me",
    description="PyBpod protocols",
    python_requires='>=3.8'
    install_requires=[
        "opencv-python",
        "PyQtWebEngine"
        "numpy",
        "scipy",
        "pandas",
        "matplotlib",
        "pybpod"
    ],
)
