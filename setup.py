from setuptools import setup
from setuptools import find_packages

setup(
    name='pybpod_lbr',
    version='0.0.1',
    packages=find_packages(),
    url='-',
    license='-',
    author='LBR',
    author_email='L.B.Rollik@pm.me',
    description='PyBpod protocols',
    install_requires=[
        "numpy",
        "scipy",
        "pandas",
        "matplotlib",
    ],
)
