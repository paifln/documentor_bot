"""Telegram text transport with a conservative UTF-16 length bound."""


def split_message(text: str, limit: int = 3500) -> list[str]:
    parts, current, size = [], [], 0
    for character in text:
        width = len(character.encode("utf-16-le")) // 2
        if size + width > limit:
            parts.append("".join(current))
            current, size = [], 0
        current.append(character)
        size += width
    if current:
        parts.append("".join(current))
    return parts


async def answer_long(message, text):
    for part in split_message(text):
        await message.answer(part)
