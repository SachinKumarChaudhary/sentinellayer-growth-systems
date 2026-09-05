import email
from email.message import EmailMessage

import pytest

from sentinellayer_growth_engine.imap_inbound import ImapInboundProvider, parse_message


def test_parse_message_extracts_thread_and_source_send_id():
    msg = EmailMessage()
    msg["Message-ID"] = "<reply@example.com>"
    msg["From"] = "Buyer <buyer@example.com>"
    msg["Subject"] = "Re: Sentinel"
    msg["In-Reply-To"] = "<send@example.com>"
    msg["X-SL-Send-Id"] = "11111111-1111-4111-8111-111111111111"
    msg.set_content("Interested, let's talk.")
    parsed = parse_message("42", msg.as_bytes())
    assert parsed.uid == "42"
    assert parsed.sender_email == "buyer@example.com"
    assert parsed.thread_key == "<send@example.com>"
    assert parsed.source_send_id == "11111111-1111-4111-8111-111111111111"
    assert parsed.body_text == "Interested, let's talk."


def test_imap_requires_tls_port():
    with pytest.raises(ValueError):
        ImapInboundProvider(host="imap.example.com", username="u", password="p", port=143)


def test_parse_html_fallback():
    msg = EmailMessage()
    msg["Message-ID"] = "<html@example.com>"
    msg["From"] = "buyer@example.com"
    msg["Subject"] = "Hello"
    msg.add_alternative("<html><body><p>Hello <b>there</b></p></body></html>", subtype="html")
    parsed = parse_message("7", msg.as_bytes())
    assert "Hello" in parsed.body_text
    assert "there" in parsed.body_text
