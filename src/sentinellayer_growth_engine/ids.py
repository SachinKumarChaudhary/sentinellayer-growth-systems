import uuid


def deterministic_message_id(send_id: str, domain: str = "sentinellayer.invalid") -> str:
    namespace = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
    value = uuid.uuid5(namespace, send_id)
    return f"<{value}@{domain}>"
