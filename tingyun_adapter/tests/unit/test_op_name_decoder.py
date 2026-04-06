import unittest

from tingyun_adapter.normalizers.op_name_decoder import decode_op_name, encode_op_name


class OpNameDecoderTests(unittest.TestCase):
    def test_decode_plain_value(self) -> None:
        decoded = decode_op_name("SELECT 1")
        self.assertEqual(decoded.decoded, "SELECT 1")
        self.assertFalse(decoded.is_encoded)

    def test_decode_ty_base64(self) -> None:
        decoded = decode_op_name("tyBase64_RVZBTA")
        self.assertEqual(decoded.decoded, "EVAL")
        self.assertTrue(decoded.is_encoded)

    def test_encode_plain_value(self) -> None:
        encoded = encode_op_name("EVAL")
        self.assertEqual(encoded, "tyBase64_RVZBTA")


if __name__ == "__main__":
    unittest.main()
