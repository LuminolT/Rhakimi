from __future__ import annotations

import math
from typing import Iterable, List, Sequence


class ReversibleTableCodec:
    """
    Encode arbitrary UTF-8 text into a string composed only of characters from a user supplied table,
    and decode it back. Codewords are fixed length, generated deterministically from the table.
    """

    LENGTH_FIELD_BYTES = 8
    LENGTH_PREFIX_WIDTH = 4  # number of single-char digits (base=len(table)) that store the codeword length

    def encode(self, table: str, text: str) -> str:
        table_chars = self._validate_table(table)
        payload = text.encode("utf-8")
        prefixed = len(payload).to_bytes(self.LENGTH_FIELD_BYTES, "big") + payload
        sentinel_prefixed = b"\x01" + prefixed
        integer_value = int.from_bytes(sentinel_prefixed, "big")

        codeword_length = self._choose_codeword_length(len(table_chars), integer_value)
        base = len(table_chars) ** codeword_length
        digits = self._int_to_base_digits(integer_value, base)

        header = self._encode_length_prefix(codeword_length, len(table_chars), table_chars)
        encoded_body = "".join(
            self._digit_to_codeword(digit, codeword_length, len(table_chars), table_chars)
            for digit in digits
        )
        return header + encoded_body

    def decode(self, table: str, encoded: str) -> str:
        table_chars = self._validate_table(table)
        char_to_value = {ch: idx for idx, ch in enumerate(table_chars)}

        if len(encoded) < self.LENGTH_PREFIX_WIDTH:
            raise ValueError("Encoded text is too short to contain header.")

        codeword_length = self._decode_length_prefix(encoded[: self.LENGTH_PREFIX_WIDTH], char_to_value, len(table_chars))
        if codeword_length < 1:
            raise ValueError("Encoded codeword length is invalid.")

        base = len(table_chars) ** codeword_length
        body = encoded[self.LENGTH_PREFIX_WIDTH :]
        if len(body) % codeword_length != 0:
            raise ValueError("Encoded text length is not aligned to the expected codeword length.")

        digits: List[int] = []
        for i in range(0, len(body), codeword_length):
            codeword = body[i : i + codeword_length]
            digit = self._codeword_to_digit(codeword, codeword_length, char_to_value, len(table_chars))
            digits.append(digit)

        integer_value = self._base_digits_to_int(digits, base)
        raw_bytes = integer_value.to_bytes(max(1, (integer_value.bit_length() + 7) // 8), "big")
        if not raw_bytes or raw_bytes[0] != 1:
            raise ValueError("Missing sentinel byte; encoded payload is corrupted.")

        prefixed = raw_bytes[1:]
        if len(prefixed) < self.LENGTH_FIELD_BYTES:
            raise ValueError("Encoded payload is too short to contain the length prefix.")

        declared_length = int.from_bytes(prefixed[: self.LENGTH_FIELD_BYTES], "big")
        expected_total = self.LENGTH_FIELD_BYTES + declared_length
        if len(prefixed) != expected_total:
            raise ValueError("Decoded payload length is inconsistent with the declared length.")

        payload = prefixed[self.LENGTH_FIELD_BYTES :]

        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Decoded bytes are not valid UTF-8.") from exc

    def _validate_table(self, table: str) -> Sequence[str]:
        if len(table) < 2:
            raise ValueError("Table must contain at least two characters.")

        seen = set()
        deduped = []
        for ch in table:
            if ch in seen:
                continue
            seen.add(ch)
            deduped.append(ch)

        if len(deduped) < 2:
            raise ValueError("Table must contain at least two distinct characters after removing duplicates.")
        return deduped

    def _choose_codeword_length(self, table_size: int, integer_value: int) -> int:
        max_length = (table_size**self.LENGTH_PREFIX_WIDTH) - 1
        if max_length < 1:
            raise ValueError("Table cannot represent any codeword length.")

        best_length = 1
        best_encoded_chars = math.inf
        for length in range(1, max_length + 1):
            base = table_size**length
            digits = self._count_digits(integer_value, base)
            encoded_chars = digits * length
            if encoded_chars < best_encoded_chars:
                best_encoded_chars = encoded_chars
                best_length = length
        return best_length

    def _encode_length_prefix(self, length: int, table_size: int, table_chars: Sequence[str]) -> str:
        max_length = (table_size**self.LENGTH_PREFIX_WIDTH) - 1
        if length < 1 or length > max_length:
            raise ValueError("Codeword length does not fit in the header.")
        digits = self._int_to_base_fixed_width(length, table_size, self.LENGTH_PREFIX_WIDTH)
        return "".join(table_chars[d] for d in digits)

    def _decode_length_prefix(self, prefix: str, char_to_value: dict[str, int], table_size: int) -> int:
        digits = [self._lookup_value(ch, char_to_value) for ch in prefix]
        length = self._base_digits_to_int(digits, table_size)
        max_length = (table_size**self.LENGTH_PREFIX_WIDTH) - 1
        if length > max_length:
            raise ValueError("Header declares a codeword length that exceeds the representable range.")
        return length

    def _digit_to_codeword(self, digit: int, codeword_length: int, table_size: int, table_chars: Sequence[str]) -> str:
        max_digit = table_size**codeword_length
        if digit < 0 or digit >= max_digit:
            raise ValueError("Digit out of range for the current codebook.")
        indices = self._int_to_base_fixed_width(digit, table_size, codeword_length)
        return "".join(table_chars[i] for i in indices)

    def _codeword_to_digit(
        self, codeword: str, codeword_length: int, char_to_value: dict[str, int], table_size: int
    ) -> int:
        if len(codeword) != codeword_length:
            raise ValueError("Encountered a codeword with invalid length.")
        digits = [self._lookup_value(ch, char_to_value) for ch in codeword]
        digit = self._base_digits_to_int(digits, table_size)
        if digit >= table_size**codeword_length:
            raise ValueError("Encountered a codeword that is outside of the codebook.")
        return digit

    def _int_to_base_digits(self, value: int, base: int) -> List[int]:
        if base < 2:
            raise ValueError("Base must be at least 2.")
        if value == 0:
            return [0]
        digits = []
        while value > 0:
            value, remainder = divmod(value, base)
            digits.append(remainder)
        digits.reverse()
        return digits

    def _base_digits_to_int(self, digits: Iterable[int], base: int) -> int:
        value = 0
        for digit in digits:
            if digit < 0 or digit >= base:
                raise ValueError("Digit outside base range encountered during conversion.")
            value = value * base + digit
        return value

    def _int_to_base_fixed_width(self, value: int, base: int, width: int) -> List[int]:
        digits = self._int_to_base_digits(value, base)
        if len(digits) > width:
            raise ValueError("Value does not fit in the requested width.")
        padding = [0] * (width - len(digits))
        return padding + digits

    def _count_digits(self, value: int, base: int) -> int:
        if value == 0:
            return 1
        count = 0
        while value:
            value //= base
            count += 1
        return count

    def _lookup_value(self, ch: str, lookup: dict[str, int]) -> int:
        if ch not in lookup:
            raise ValueError(f"Encountered character {repr(ch)} that is not in the table.")
        return lookup[ch]
