import os
import os.path
import sys
import pytest
from instrumental import instrument, conf

sys.path.append(os.path.dirname(__file__))
inst_names = []
inst_map = {}


def pytest_addoption(parser):
    parser.addoption("--instrument", action="store", help="Name of instrument to test")


def pytest_collection_modifyitems(session, config, items):
    global instruments
    inst_names_str = config.getoption('--instrument')
    if not inst_names_str:
        return

    instruments = {}
    inst_names = inst_names_str.split(',')
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
