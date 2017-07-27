def pytest_addoption(parser):
    parser.addoption("--instrument", action="store", help="Name of instrument to test")
