import os
import os.path
from setuptools import setup, find_packages
from distutils.ccompiler import new_compiler

description = "Library with high-level drivers for lab equipment"
classifiers = [
    'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    'Intended Audience :: Science/Research',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
]

# Load metadata from __about__.py
base_dir = os.path.dirname(__file__)
about = {}
with open(os.path.join(base_dir, 'instrumental', '__about__.py')) as f:
    exec(f.read(), about)

# Load driver info
with open(os.path.join(base_dir, 'instrumental', 'driver_info.py')) as f:
    namespace = {}
    exec(f.read(), namespace)
    driver_info = namespace['driver_info']
extras = {k:v['imports'] for k,v in driver_info.items()}

# Check for cffi
post_install_msgs = []
try:
    import cffi

    try:
        new_compiler().compile(b'')
        build_cffi_modules = True
    except:
        build_cffi_modules = False
        post_install_msgs.append(
            "No C compiler was found, so cffi modules were not built. If you would like to use "
            "cffi-based drivers that require compilation, first install a suitable compiler, "
            "then reinstall Instrumental. See the cffi installation documentation for more details on "
            "installing an appropriate compiler for your platform.")
except:
    build_cffi_modules = False
    post_install_msgs.append(
        "Python cffi was not installed, so cffi modules were not built. If you would like to use "
        "cffi-based drivers that require compilation, first install cffi and a suitable compiler, "
        "then reinstall Instrumental. See the cffi installation documentation for more details on "
        "installing an appropriate compiler for your platform.")


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
        name = about['__distname__'],
        version = about['__version__'],
        packages = find_packages(exclude=['*._cffi_build']),
        package_data = {
            '': ['*.h', '*.pyd'],
            'instrumental': ['instrumental.conf.default']
        },
        author = about['__author__'],
        author_email = about['__email__'],
        description = description,
        long_description = '\n'.join(open("README.rst").read().splitlines()[2:]),
        url = about['__url__'],
        license = about['__license__'],
        classifiers = classifiers,
        install_requires = ['numpy', 'scipy', 'pint>=0.7', 'future'],
        extras_require = extras,
        **keywords
    )

    if post_install_msgs:
        print("\n" + "\n\n".join(post_install_msgs))
