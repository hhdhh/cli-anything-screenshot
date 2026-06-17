from setuptools import setup, find_packages

setup(
    name="cli-anything-screenshot",
    version="0.1.0",
    description="CLI harness for the macOS Screenshot.app GUI, built on the CLI-Anything methodology.",
    long_description="See SKILL.md and README.md for the agent-facing and human-facing descriptions.",
    long_description_content_type="text/markdown",
    packages=find_packages(include=["cli_anything.*"]),
    python_requires=">=3.10",
    install_requires=["click>=8.0"],
    extras_require={
        "dev": ["pytest>=7.0"],
    },
    entry_points={
        "console_scripts": [
            "cli-anything-screenshot=cli_anything.screenshot.screenshot_cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Operating System :: MacOS :: MacOS X",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
