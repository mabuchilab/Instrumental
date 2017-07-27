import os
import os.path
import sys
import pytest
import py.path
from instrumental import instrument, conf

sys.path.append(os.path.dirname(__file__))
DRIVER_DIR = py.path.local(__file__).dirpath()
instruments = {}
inst_names = []
inst_map = {}


def pytest_collection_modifyitems(session, config, items):
    global instruments
    instruments = {}
    inst_names_str = config.getoption('--instrument')

    inst_names = inst_names_str.split(',') if inst_names_str else ()
    for inst_name in inst_names:
        params = conf.instruments[inst_name]
        try:
            category, driver = params['module'].split('.')
            instruments[(category, driver, params['classname'])] = params
        except KeyError:
            pass

    deselected = []
    remaining = []
    for item in items:
        # Leave non-driver tests alone
        item_dir = item.getparent(pytest.Module).fspath.dirpath()
        if DRIVER_DIR not in item_dir.parts():
            remaining.append(item)
            continue

        inst_key = inst_key_from_item(item)
        if inst_key in instruments:
            remaining.append(item)
        else:
            deselected.append(item)

    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = remaining


def inst_key_from_item(item):
    test_fname = item.getparent(pytest.Module).fspath.basename
    base, _ = test_fname.rsplit('.')
    _, category, driver = base.split('_')
    test_class = item.getparent(pytest.Class)

    if not test_class:
        return None

    return (category, driver, test_class.name[4:])


def pytest_runtest_setup(item):
    global current_instrument
    inst_key = inst_key_from_item(item)
    params = instruments[inst_key]
    current_instrument = instrument(params)


@pytest.fixture(scope="class")
def inst():
    return current_instrument
