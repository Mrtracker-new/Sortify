from setuptools import setup

setup(
    name="Sortify",
    version="1.0",
    description="A File Organization System",
    author="Rolan Lobo",
    packages=['core', 'ui'],
    install_requires=[
        'PyQt6',
        'apscheduler',
        'nltk',
        'spacy',
        'opencv-python',
        'scikit-learn',
        'watchdog',
        'pillow',
    ],
    entry_points={
        'console_scripts': [
            'sortify=main:main',
        ],
    },
)
