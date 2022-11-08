from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt") as f:
    required = f.read().splitlines()

with open("requirements-dev.txt") as f:
    required_dev = f.read().splitlines()

setup(
    name="darsia",
    version="0.0.1",
    description="Darcy scale image analysis toolbox",
    keywords="darcy image analysis porous media flow",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    package_data={"darsia": ["py.typed"]},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python ::3",
        "Programming Language :: Python ::3.10"
        "License :: OSI Approved :: Apache v2 License",
        "Operating System :: Linux, Windows",
    ],
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=required,
    extras_require={
        "dev": required_dev,
    },
    python_requires=">=3",
    url="https://github.com/pmgbergen/DarSIA.git",
    author="Erlend Storvik, Jan Nordbotten and Jakub Wiktor Both",
    maintainer="Erlend Storvik",
    maintainer_email="erlend.storvik@uib.no",
    platforms=["Linux", "Windows"],
    license="Apache v2",
)
