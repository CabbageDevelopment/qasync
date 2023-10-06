import os.path
import re

from setuptools import setup

with open("qasync/__init__.py") as f:
    version = re.search(r'__version__\s+=\s+"(.*)"', f.read()).group(1)

desc_path = os.path.join(os.path.dirname(__file__), "README.md")
with open(desc_path, encoding="utf8") as desc_file:
    long_description = desc_file.read()

setup(
    name="qasync",
    version=version,
    url="https://github.com/CabbageDevelopment/qasync",
    author=", ".join(
        ("Sam McCormack", "Gerard Marull-Paretas", "Mark Harviston", "Arve Knudsen")
    ),
    packages=["qasync"],
    python_requires=">=3.6,<4.0",
    license="BSD",
    description="Implementation of the PEP 3156 Event-Loop with Qt.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords=["Qt", "asyncio"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: X11 Applications :: Qt",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
