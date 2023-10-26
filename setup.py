from setuptools import setup, find_packages
# git needs to be installed on the PC and not be used by another program

setup(
    name='PyCoverageAnalyzer',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'xmltodict',
        'matplotlib',
        'requests',
        'unidiff',
        'pandas',
        'plotly',
        'dash',
        'dash-bootstrap-components',
        'python-dotenv',
    ],
)
