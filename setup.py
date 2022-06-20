"""RESONAATE Package setup file."""
# Third Party Imports
import setuptools

setuptools.setup(
    name="resonaate",
    description="The Responsive Space Observation Analysis and Autonomous Tasking Engine (RESONAATE) ",
    version="1.4.0",
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
        "concurrent-log-handler>=0.9.19",
        "sqlalchemy>=1.3",
        "matplotlib>=3.3",
        "redis>=3.3.0",
        "pywin32 >= 1.0; platform_system=='Windows'",
    ],
    extras_require={
        "dev": [
            # Linting
            "flake8<4.0",  # Keep flake8 below 4.0 b/c of dep conflict
            "flake8-bugbear==22.4.25",
            "flake8-builtins==1.5.3",
            "flake8-docstrings==1.6.0",
            "flake8-plugin-utils==1.3.2",
            "flake8-pytest-style==1.6.0",
            "flake8-rst-docstrings==0.2.5",
            "pylint==2.14.3",
            # Type Checking
            "mypy==0.961",
            "types-redis==4.2.8",
            "types-sqlalchemy==1.4.38",
            "typing_extensions==4.1.1; python_version < '3.10'",
            # Formatters
            "black==22.3.0",
            "isort[colors]==5.10.1",
            "mdformat==0.7.14",
            "mdformat-myst==0.1.5",
            "mdformat-gfm==0.3.5",
            # Pre-commit stuff
            "pre-commit==2.19.0",
            # Misc.
            "check-manifest>=0.48",
        ],
        "test": [
            "pytest==7.1.2",
            "pytest-datafiles==2.0.1",
            "pytest-randomly==3.12.0",
            "coverage==6.4.1",
        ],
        "doc": [
            "sphinx==5.0.2",
            "sphinx_rtd_theme==1.0.0",
            "myst-parser==0.18.0",
            "sphinx-copybutton==0.5.0",
            "sphinxcontrib-bibtex==2.4.2",
            "sphinxcontrib-mermaid==0.7.1",
            "sphinx-gallery==0.10.1",
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
