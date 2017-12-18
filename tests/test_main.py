from instrumental import list_instruments


def test_list_instruments():
    list_instruments()


def test_import_all():
    import instrumental
    for attr in dir(instrumental):
        try:
            getattr(instrumental, attr)
        except ImportError:
            pass  # Ignore dependencies on matplotlib, numpy, etc.
