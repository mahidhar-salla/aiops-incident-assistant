from aiops_assistant.redact import redact


def test_scrubs_pii_and_secrets():
    text = (
        "user login ok email=sam12@example.com src_ip=203.0.113.9 card=4111 1111 1111 1234 "
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
