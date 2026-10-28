from aiops_assistant.redact import redact


def test_scrubs_pii_and_secrets():
    text = (
        "user login ok email=sam12@example.com src_ip=203.0.113.9 card=4111 1111 1111 1111 "
        "password=hunter2 Authorization: Bearer abcdefghijklmnop key AKIAABCDEFGHIJKLMNOP"
    )
    out, counts = redact(text)
    for leaked in ("sam12@", "203.0.113.9", "4111", "hunter2", "abcdefghijklmnop", "AKIAABCDEFGHIJKLMNOP"):
        assert leaked not in out
    assert counts["EMAIL"] == 1 and counts["CARD"] == 1 and counts["IPV4"] == 1


def test_keeps_private_infra_ips_and_timestamps():
    text = "2026-09-14T02:00:55Z lookup ledger.internal on 10.96.0.10:53: i/o timeout after 30000ms"
    out, counts = redact(text)
    assert out == text and counts == {}


def test_scrubs_colon_and_json_secrets():
    text = 'db password: hunter2 cfg {"api_key": "sk-live-123abc", "client_secret":"s3cr3t"} token=abc.def'
    out, counts = redact(text)
    for leaked in ("hunter2", "sk-live-123abc", "s3cr3t", "abc.def"):
        assert leaked not in out
    assert '"api_key": "[REDACTED]"' in out and "password: [REDACTED]" in out
    assert counts["SECRET"] == 4


def test_scrubs_basic_auth_header():
    out, counts = redact("GET /v1/x Authorization: Basic dXNlcjpodW50ZXIy status=401")
    assert "dXNlcjpodW50ZXIy" not in out
    assert "Authorization: Basic [REDACTED] status=401" in out and counts["BASIC"] == 1


def test_leaves_secret_words_in_prose_alone():
    text = 'rotated secret billing-db-credentials version=7 FATAL: password authentication failed for user "app"'
    out, counts = redact(text)
    assert out == text and counts == {}


def test_scrubs_sin_written_with_spaces():
    out, counts = redact("customer sin=046 454 286 updated; legacy id 123-45-6789")
    assert "046 454 286" not in out and "123-45-6789" not in out
    assert counts["SIN_SSN"] == 2


def test_keeps_spaced_numbers_that_are_not_sins():
    text = "batch sizes 100 200 300 processed"
    out, counts = redact(text)
    assert out == text and counts == {}


def test_card_needs_valid_luhn():
    out, counts = redact("card=4111-1111-1111-1111 ref=4111111111111234")
    assert "4111-1111-1111-1111" not in out and "ref=4111111111111234" in out
    assert counts == {"CARD": 1}


def test_keeps_epoch_ms_timestamps():
    # 1760918400000 fails Luhn; 1760918400001 passes it but cannot be a card (starts with 1).
    text = "ts=1760918400000 retry_at=1760918400001 order=1234567890123"
    out, counts = redact(text)
    assert out == text and counts == {}


def test_scrubs_phone_numbers():
    text = "callback 416-555-0199 or (647) 555 0123, sms +1 905.555.0142, intl +442079460958"
    out, counts = redact(text)
    for leaked in ("555-0199", "555 0123", "555.0142", "+442079460958"):
        assert leaked not in out
    assert counts == {"PHONE": 4}


def test_phone_and_sin_get_their_own_labels():
    out, counts = redact("phone 416-555-0199 sin 046-454-286 ssn 123-45-6789")
    assert out == "phone [PHONE] sin [SIN_SSN] ssn [SIN_SSN]"
    assert counts == {"PHONE": 1, "SIN_SSN": 2}


def test_phone_pattern_leaves_dates_ips_and_durations_alone():
    text = "2026-09-14T02:00:55Z 10.96.0.10:53 took 120 ms, v2.14.0, 3 of 10 pods"
    out, counts = redact(text)
    assert out == text and counts == {}


def test_scrubs_secret_keys_with_a_prefix():
    # Env-style and prefixed config keys: the keyword is the last part of a longer name.
    text = (
        "env DB_PASSWORD=hunter2 GITHUB_TOKEN=ghp_abc123def456 aws_secret_access_key = wJalrXUtnFEMI/K7MDENG "
        'cfg {"db_password": "pa55word", "stripe_api_key": "sk_live_abc123"} '
        "spring.datasource.password: s3cr3t refresh_token=abc.def.ghi secret_key=k3y"
    )
    out, counts = redact(text)
    for leaked in ("hunter2", "ghp_abc123def456", "wJalrXUtnFEMI", "pa55word", "sk_live_abc123", "s3cr3t", "abc.def"):
        assert leaked not in out
    assert "k3y" not in out
    assert "DB_PASSWORD=[REDACTED]" in out and '"db_password": "[REDACTED]"' in out
    assert counts == {"SECRET": 8}


def test_keeps_keys_that_only_start_with_a_secret_word():
    text = "token_expiry=3600 password_reset=true max_tokens=4096 tokenizer=bpe secretary=alice"
    out, counts = redact(text)
    assert out == text and counts == {}


def test_scrubs_the_whole_quoted_secret_value():
    # A quoted value used to be cut at the first space, comma, semicolon or brace, so the rest of the secret
    # went into the prompt.
    text = (
        'password="correct horse battery" {"client_secret": "a b,c;d}e"} '
        'secret: \'x,y z\' api_key="k1 k2" pwd="" user=app'
    )
    out, counts = redact(text)
    for leaked in ("horse", "battery", "b,c", "d}e", "y z", "k2"):
        assert leaked not in out
    assert 'password="[REDACTED]"' in out
    assert '"client_secret": "[REDACTED]"}' in out
    assert "secret: '[REDACTED]'" in out
    assert 'api_key="[REDACTED]"' in out
    assert 'pwd="" user=app' in out
    assert counts == {"SECRET": 4}


def test_unclosed_quote_redacts_to_end_of_line_only():
    out, counts = redact('password="abc def\nnext line ok')
    assert out == 'password="[REDACTED]\nnext line ok'
    assert counts == {"SECRET": 1}
