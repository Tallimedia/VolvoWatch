from app.pkce import code_challenge_s256, generate_code_verifier, generate_state


def test_verifier_length_in_range():
    v = generate_code_verifier()
    assert 43 <= len(v) <= 128


def test_challenge_is_url_safe_and_unpadded():
    challenge = code_challenge_s256(generate_code_verifier())
    assert "=" not in challenge
    assert "+" not in challenge and "/" not in challenge


def test_challenge_is_deterministic():
    v = generate_code_verifier()
    assert code_challenge_s256(v) == code_challenge_s256(v)


def test_known_vector_rfc7636():
    # RFC 7636 Appendix B
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    assert code_challenge_s256(verifier) == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def test_state_is_unique():
    assert generate_state() != generate_state()
