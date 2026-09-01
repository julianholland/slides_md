from slide_maker.placeholders import PLACEHOLDER_DIR, placeholder_alt, resolve_placeholder


def test_resolve_bare_placeholder():
    path = resolve_placeholder("example-image")
    assert path == PLACEHOLDER_DIR / "example-image.png"
    assert path.is_file()


def test_resolve_lettered_placeholder():
    path = resolve_placeholder("example-image-a")
    assert path == PLACEHOLDER_DIR / "example-image-a.png"
    assert path.is_file()


def test_resolve_all_26_letters_exist():
    import string

    for letter in string.ascii_lowercase:
        path = resolve_placeholder(f"example-image-{letter}")
        assert path is not None
        assert path.is_file(), f"missing placeholder for letter {letter}"


def test_resolve_is_case_insensitive():
    assert resolve_placeholder("Example-Image-A") == PLACEHOLDER_DIR / "example-image-a.png"


def test_resolve_rejects_non_placeholder_names():
    assert resolve_placeholder("images/diagram.png") is None
    assert resolve_placeholder("example-image-aa") is None
    assert resolve_placeholder("example-image-1") is None
    assert resolve_placeholder("example-images-a") is None


def test_placeholder_alt_text():
    assert placeholder_alt("example-image") == "Placeholder image"
    assert placeholder_alt("example-image-b") == "Placeholder image B"
    assert placeholder_alt("images/diagram.png") is None
