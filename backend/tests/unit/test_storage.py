import pytest

from app.services.storage import LocalStorage, source_key


def test_put_get_roundtrip(tmp_path):
    s = LocalStorage(str(tmp_path))
    uri = s.put("a/b/c.txt", b"hello")
    assert uri.startswith("file://")
    assert s.get("a/b/c.txt") == b"hello"


def test_delete_prefix(tmp_path):
    s = LocalStorage(str(tmp_path))
    s.put("users/u/projects/p/sources/x/original.txt", b"data")
    s.delete_prefix("users/u/projects/p")
    with pytest.raises(FileNotFoundError):
        s.get("users/u/projects/p/sources/x/original.txt")


def test_path_traversal_blocked(tmp_path):
    s = LocalStorage(str(tmp_path))
    with pytest.raises(ValueError):
        s.put("../escape.txt", b"x")


def test_source_key_layout():
    key = source_key("u1", "p1", "s1", "original.pdf")
    assert key == "users/u1/projects/p1/sources/s1/original.pdf"
