import pytest

from rhakimi import ReversibleTableCodec


@pytest.mark.parametrize(
    ("table", "message"),
    [
        ("ab", ""),
        ("哈基米", "Hello, 世界"),
        ("0123456789ABCDEF", "Binary-ish payload"),
    ],
)
def test_roundtrip_basic(table: str, message: str) -> None:
    codec = ReversibleTableCodec()
    encoded = codec.encode(table, message)
    decoded = codec.decode(table, encoded)
    assert decoded == message
    assert set(encoded).issubset(set(table))


def test_table_deduplicates_preserving_order() -> None:
    table = "哈哈哈哈哈一二三四"
    deduped = "哈一二三四"
    codec = ReversibleTableCodec()
    message = "repeat chars should dedupe"
    encoded = codec.encode(table, message)
    decoded = codec.decode(table, encoded)
    assert decoded == message
    assert set(encoded).issubset(set(deduped))


def test_table_requires_two_distinct_chars() -> None:
    codec = ReversibleTableCodec()
    with pytest.raises(ValueError):
        codec.encode("哈", "too short")
    with pytest.raises(ValueError):
        codec.decode("哈", "哈")
