from __future__ import annotations

from . import ReversibleTableCodec


def main() -> None:
    codec = ReversibleTableCodec()
    sample_table = "哈基米南北绿豆啊系噶"
    sample_text = "Hello"
    encoded = codec.encode(sample_table, sample_text)
    decoded = codec.decode(sample_table, encoded)
    print(f"Table: {sample_table}")
    print(f"Original: {sample_text}")
    print(f"Encoded: {encoded}")
    print(f"Decoded: {decoded}")


if __name__ == "__main__":
    main()
