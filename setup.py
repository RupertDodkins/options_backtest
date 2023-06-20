from setuptools import setup, find_packages

setup(
    name="options_backtest",
    version="0.1",
    author="Rupert Dodkins",
    description="A package for backtesting options strategies",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url="https://github.com/RupertDodkins/options_backtest/",
    packages=find_packages(where="src/options_backtest"),
    package_dir={"": "src/options_backtest"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Affero General Public License v3 (AGPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        # Add your package's dependencies here
        'plotly',
        'kaleido',
        'scipy'
    ],
)