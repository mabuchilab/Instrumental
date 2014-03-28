from setuptools import setup, find_packages

name = "Instrumental"
description = "Instrumentation library for the Mabuchi Lab"
author = "MabuchiLab"
version = "0.1.0"

if __name__ == '__main__':
    setup(
        name = name,
        version = version,
        packages = find_packages(),
        author = author,
        author_email = "natezb@stanford.edu",
        description = description,
    )
