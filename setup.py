# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

from setuptools import setup, find_packages

setup(
    name="tsdbenv",
    version="0.1.0",
    author="Wagner Bianchi",
    author_email="wagnerbianchijr@gmail.com",
    description="PostgreSQL + TimescaleDB environment manager via Docker",
    url="https://github.com/wagnerbianchijr/tsdbenv.git",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "pydantic>=2.0",
        "click>=8.1",
        "docker>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "tsdbenv=tsdbenv.cli:main",
        ]
    },
)
