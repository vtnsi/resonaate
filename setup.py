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
        "mjolnir>=1.3.1",
    ],
    extras_require={
        "dev": [
            # Linting
            "flake8",
            "flake8-bugbear==23.3.12",
            "flake8-builtins==2.1.0",
            "flake8-docstrings==1.7.0",
            "flake8-plugin-utils==1.3.2",
            "flake8-pytest-style==1.7.2",
            "flake8-rst-docstrings==0.3.0",
            "pylint==2.17.0",
            # Type Checking
            "mypy==1.1.1",
            "types-sqlalchemy==1.4.53.34",
            "typing_extensions==4.1.1; python_version < '3.10'",
            # Formatters
            "black==23.1.0",
            "isort[colors]==5.12.0",
            "mdformat==0.7.16",
            "mdformat-myst==0.1.5",
            "mdformat-gfm==0.3.5",
            # Pre-commit stuff
            "pre-commit==3.2.0",
            # Misc.
            "check-manifest>=0.48",
        ],
        "test": [
            "pytest==7.2.2",
            "pytest-datafiles==3.0.0",
            "pytest-randomly==3.12.0",
            "coverage[toml]==7.2.2; python_version < '3.11'",
            "coverage==7.2.1; python_version >= '3.11'",
            "pytest-cov==4.0.0",
        ],
        "doc": [
            "sphinx==6.1.3",
            "sphinx_rtd_theme==1.2.0",
            "myst-parser==1.0.0",
            "sphinx-copybutton==0.5.1",
            "sphinxcontrib-bibtex==2.5.0",
            "sphinxcontrib-mermaid==0.8.1",
            "sphinx-gallery==0.12.2",
            "importlib-metadata==6.0.0; python_version < '3.10'",
        ],
    },
    entry_points={
        "console_scripts": [
            "resonaate=resonaate:main",
        ]
    },
    zip_safe=False,
)
