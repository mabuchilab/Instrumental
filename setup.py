import os
import os.path
from setuptools import setup, find_packages

name = "Instrumental"
description = "Library with high-level drivers for lab equipment"
author = "Nate Bogdanowicz"
url = 'https://github.com/mabuchilab/Instrumental'
version = "0.2.1"
license = "GPLv3"
classifiers = [
    'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    'Intended Audience :: Science/Research',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
]

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
        package_data = {
            '': ['*.h', '*.pyd'],
            'instrumental': ['instrumental.conf.default']
        },
        author = author,
        author_email = "natezb@stanford.edu",
        description = description,
        long_description = '\n'.join(open("README.rst").read().splitlines()[2:]),
        url = url,
        classifiers = classifiers,
        install_requires = ['numpy', 'scipy', 'pint>=0.6'],
        **keywords
    )

    if not build_cffi_modules:
        print("\nPython cffi is not installed, so CFFI modules were not built. If you would like "
              "to use cffi-based drivers, first install cffi, then rebuild Instrumental")
