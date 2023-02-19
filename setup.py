"""RESONAATE Package setup file."""
# Third Party Imports
import setuptools

setuptools.setup(
    name="resonaate",
    description="The Responsive Space Observation Analysis and Autonomous Tasking Engine (RESONAATE) ",
    version="2.0.0",
    packages=setuptools.find_packages("src"),
    package_dir={"": "src"},
    package_data={
        "": [
            "common/default_behavior.config",
        ],
        "resonaate.physics": [
            "data/geopotential/*",
            "data/eop/*",
            "data/de432s/*",
            "data/nutation/*",
        ],
    },
    install_requires=[
        "numpy>=1.19",
        "scipy>=1.6",
        "sqlalchemy>=1.3",
        "matplotlib>=3.3",
        "mjolnir>=1.3.0",
    ],
    extras_require={
        "dev": [
            # Linting
            "flake8<4.0",  # Keep flake8 below 4.0 b/c of dep conflict
            "flake8-bugbear==23.1.14",
            "flake8-builtins==2.1.0",
            "flake8-docstrings==1.6.0",
            "flake8-plugin-utils==1.3.2",
            "flake8-pytest-style==1.7.2",
            "flake8-rst-docstrings==0.3.0",
            "pylint==2.15.10",
            # Type Checking
            "mypy==0.991",
            "types-sqlalchemy==1.4.53.24",
            "typing_extensions==4.1.1; python_version < '3.10'",
            # Formatters
            "black==22.12.0",
            "isort[colors]==5.11.4",
            "mdformat==0.7.16",
            "mdformat-myst==0.1.5",
            "mdformat-gfm==0.3.5",
            # Pre-commit stuff
            "pre-commit==2.21.0",
            # Misc.
            "check-manifest>=0.48",
        ],
        "test": [
            "pytest==7.2.1",
            "pytest-datafiles==2.0.1",
            "pytest-randomly==3.12.0",
            "coverage[toml]==7.0.4; python_version < '3.11'",
            "coverage==7.0.5; python_version >= '3.11'",
            "pytest-cov==4.0.0",
        ],
        "doc": [
            "sphinx==5.3.0",
            "sphinx_rtd_theme==1.1.1",
            "myst-parser==0.18.1",
            "sphinx-copybutton==0.5.1",
            "sphinxcontrib-bibtex==2.5.0",
            "sphinxcontrib-mermaid==0.7.1",
            "sphinx-gallery==0.11.1",
            "importlib-metadata==4.11.3; python_version < '3.10'",
        ],
    },
    entry_points={
        "console_scripts": [
            "resonaate=resonaate:main",
        ]
    },
    zip_safe=False,
)
