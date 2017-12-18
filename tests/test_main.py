from instrumental import list_instruments


def test_list_instruments():
    list_instruments()


def test_import_all():
    import instrumental
    for attr in dir(instrumental):
        getattr(instrumental, attr)
