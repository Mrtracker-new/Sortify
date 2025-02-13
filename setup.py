from setuptools import setup

setup(
    name="FileOrganizer",
    version="1.0",
    description="A File Organization System",
    author="Your Name",
    packages=['core', 'ui'],
    install_requires=[
        'PyQt6',
        'pathlib',
    ],
    entry_points={
        'console_scripts': [
            'fileorganizer=main:main',
        ],
    },
) 