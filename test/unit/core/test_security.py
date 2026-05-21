from src.core.security import hash_password, verify_password


def test_hash_password_returns_non_empty_string():
    result = hash_password("mypassword")

    assert isinstance(result, str)
    assert len(result) > 0


def test_hash_password_is_not_plaintext():
    result = hash_password("mypassword")

    assert result != "mypassword"


def test_hash_password_produces_different_hashes_for_same_input():
    hash1 = hash_password("samepassword")
    hash2 = hash_password("samepassword")

    assert hash1 != hash2


def test_verify_password_returns_true_for_correct_plain():
    hashed = hash_password("correct")

    assert verify_password("correct", hashed) is True


def test_verify_password_returns_false_for_wrong_plain():
    hashed = hash_password("correct")

    assert verify_password("wrong", hashed) is False


def test_verify_password_returns_false_for_empty_plain():
    hashed = hash_password("notempty")

    assert verify_password("", hashed) is False
