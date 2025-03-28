from setuptools import setup, find_packages

setup(
    name='netmonitor',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'typer[all]',
        'psutil',
        'rich',
    ],
    entry_points={
        'console_scripts': [
            'netmonitor=netmonitor.cli:app',
        ],
    },
)