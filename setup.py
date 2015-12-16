from setuptools import setup, find_packages

name = "Instrumental"
description = "Instrumentation library from the Mabuchi Lab"
author = "MabuchiLab"
version = "0.3dev"

if __name__ == '__main__':
    setup(
        name = name,
        version = version,
        packages = find_packages(exclude=['build_*.py']),
        package_data = {'': ['*.h', '*/*.h', '*.pyd']},
        author = author,
        author_email = "natezb@stanford.edu",
        description = description,
    )
    print("\nIf this is your first time installing Instrumental, now run "
          "`python post_install.py` to install the config file")
