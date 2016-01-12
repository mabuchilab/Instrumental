import os
import os.path
import sys
from setuptools import setup, find_packages

name = "Instrumental"
description = "Instrumentation library from the Mabuchi Lab"
author = "MabuchiLab"
version = "0.3dev"

# Check for cffi
try:
    import cffi
    build_cffi_modules = True
except ImportError:
    build_cffi_modules = False

# Find all cffi build scripts
keywords = {}
if build_cffi_modules:
    keywords['setup_requires'] = ["cffi>=1.0.0"]
    modules = []
    for dirpath, dirnames, filenames in os.walk('instrumental'):
        basename = os.path.basename(dirpath)
        for fname in filenames:
            if basename == '_cffi_build' and fname.startswith('build_'):
                modules.append(os.path.join(dirpath, fname) + ':ffi')
    keywords['cffi_modules'] = modules

if __name__ == '__main__':
    setup(
        name = name,
        version = version,
        packages = find_packages(exclude=['*._cffi_build']),
        package_data = {'': ['*.h', '*.pyd']},
        author = author,
        author_email = "natezb@stanford.edu",
        description = description,
        **keywords
    )

    if not build_cffi_modules:
        print("\nPython cffi is not installed, so CFFI modules were not built. If you would like "
              "to use cffi-based drivers, first install cffi, then rebuild Instrumental")

    if 'install' in sys.argv:
        print("\nIf this is your first time installing Instrumental, now run "
              "`python post_install.py` to install the config file")
