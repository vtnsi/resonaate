import setuptools

setuptools.setup(
    name="resonaate",
    description="The Responsive Space Observation Analysis and Autonomous Tasking Engine (RESONAATE) ",
    version="1.1.0",
    packages=setuptools.find_packages('src'),
    package_dir={'': 'src'},
    package_data={
        "": ["default.config"],
        "external_data": ["*"],
        "example_data": ["*"],
    },
    install_requires=[
        "numpy>=1.19",
        "scipy>=1.6",
        "concurrent-log-handler>=0.9.19",
        "sqlalchemy>=1.3",
        "matplotlib>=3.3",
        "pyyaml>=5.3",
        "jplephem>=2.9",
        "redis>=3.2.0",
        "munkres>=1.1",
    ],
    entry_points={
        'console_scripts': [
            'resonaate=resonaate.__main__:main',
        ]
    }
)
