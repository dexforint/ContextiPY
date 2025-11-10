"""Basic import tests to verify package structure."""


def test_import_contextipy() -> None:
    """Test that the main package can be imported."""
    import contextipy

    assert contextipy is not None


def test_import_cli_main() -> None:
    """Test that the CLI main module can be imported."""
    from contextipy.cli import main

    assert main is not None
    assert callable(main)


def test_main_returns_int() -> None:
    """Test that main() returns an integer exit code."""
    from contextipy.cli.main import main

    result = main()
    assert isinstance(result, int)
    assert result == 0
