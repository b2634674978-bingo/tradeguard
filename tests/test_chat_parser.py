from tradeguard.chat_parser import parse_export

ANDROID_CHAT = """12/31/25, 10:23 PM - +1 555 010 4477: Hi, we need 2kg sample for our US client
12/31/25, 10:24 PM - You: Sample is 50 USD + shipping
12/31/25, 10:25 PM - +1 555 010 4477: No, sample should be free. We order big later.
1/1/26, 9:00 AM - +1 555 010 4477: Please send to this address, urgent
"""

IOS_CHAT = """[31/12/2025, 22:23:45] Mike: Hi
[31/12/2025, 22:24:00] You: Hello
[31/12/2025, 22:25:00] Mike: Sample is free, we pay after order
This is a multi-line reply
with a second line
[31/12/2025, 22:26:00] Mike: <Media omitted>
"""


def test_parse_android_chat():
    result = parse_export(ANDROID_CHAT, "chat.txt")
    assert result.message_count == 4
    assert result.phones[0].norm == "15550104477"
    assert result.phones[0].confidence == "high"
    assert result.first_ts.year == 2025
    assert result.last_ts.day == 1
    labels = [signal.label for signal in result.signals]
    assert "免费样品" in labels


def test_parse_ios_chat_multiline():
    result = parse_export(IOS_CHAT.encode("utf-8"), "chat.txt")
    assert result.message_count == 4
    assert "multi-line reply" in result.messages[-2].text
    assert result.media_count == 1
    assert result.senders[0][0] == "Mike"


def test_system_messages_are_ignored():
    text = (
        "[31/12/2025, 22:23:45] Messages and calls are end-to-end encrypted. "
        "No one outside of this chat, not even WhatsApp, can read or listen to them.\n"
        "[31/12/2025, 22:24:00] Mike: hello\n"
    )
    result = parse_export(text)
    assert result.message_count == 1
    assert all(not message.is_system for message in result.messages if message.sender == "Mike")


def test_empty_input_has_warning():
    result = parse_export("", "empty.txt")
    assert result.message_count == 0
    assert result.warnings


def test_dates_and_amounts_are_not_treated_as_phones():
    text = "[31/12/2025, 22:23:45] Mike: Order 2024-05-01 total 12,000 USD, tracking 123456789\n"
    result = parse_export(text)
    assert not any(phone.norm == "20240501" for phone in result.phones)
