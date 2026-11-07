
# Common Hindi number words for merchant transactions

HINDI_NUMBERS = {
    "शून्य": 0, "एक": 1, "दो": 2, "तीन": 3,
    "चार": 4, "पांच": 5, "पाँच": 5,
    "छह": 6, "सात": 7, "आठ": 8, "नौ": 9,
    "दस": 10, "ग्यारह": 11, "बारह": 12,
    "तेरह": 13, "चौदह": 14, "पंद्रह": 15,
    "सोलह": 16, "सत्रह": 17, "अठारह": 18,
    "उन्नीस": 19, "बीस": 20,
    "तीस": 30, "चालीस": 40, "पचास": 50,
    "साठ": 60, "सत्तर": 70, "अस्सी": 80,
    "नब्बे": 90
}

# Roman Hindi equivalents
ROMAN_NUMBERS = {
    "zero": 0, "ek": 1, "do": 2, "teen": 3,
    "chaar": 4, "char": 4, "paanch": 5, "panch": 5,
    "chhe": 6, "cheh": 6, "saat": 7, "aath": 8,
    "nau": 9, "das": 10, "gyarah": 11,
    "barah": 12, "terah": 13, "chaudah": 14,
    "pandrah": 15, "solah": 16, "satrah": 17,
    "atharah": 18, "unnis": 19, "bees": 20,
    "tees": 30, "chalees": 40, "chaalis": 40,
    "pachaas": 50, "saath": 60, "sattar": 70,
    "assi": 80, "nabbe": 90
}


def number_to_hindi(number):
    """Convert common amounts to Hindi words."""
    ones = [
        "", "एक", "दो", "तीन", "चार", "पांच",
        "छह", "सात", "आठ", "नौ"
    ]

    teens = [
        "दस", "ग्यारह", "बारह", "तेरह", "चौदह",
        "पंद्रह", "सोलह", "सत्रह", "अठारह", "उन्नीस"
    ]

    tens = [
        "", "", "बीस", "तीस", "चालीस", "पचास",
        "साठ", "सत्तर", "अस्सी", "नब्बे"
    ]

    def under_1000(n):
        words = []

        if n >= 100:
            words.append(ones[n // 100])
            words.append("सौ")
            n %= 100

        if 10 <= n <= 19:
            words.append(teens[n - 10])
        elif n >= 20:
            words.append(tens[n // 10])
            n %= 10

        if 0 < n < 10:
            words.append(ones[n])

        return " ".join(words)

    number = int(number)

    if number == 0:
        return "शून्य"

    if number < 0 or number > 999999:
        raise ValueError("Supported range: 0 to 999999")

    parts = []

    if number >= 100000:
        parts.append(under_1000(number // 100000))
        parts.append("लाख")
        number %= 100000

    if number >= 1000:
        parts.append(under_1000(number // 1000))
        parts.append("हजार")
        number %= 1000

    if number > 0:
        parts.append(under_1000(number))

    return " ".join(parts)


def hindi_to_number(text):
    """Convert supported Hindi/romanized number phrases to integers."""

    text = text.lower().replace("-", " ")
    tokens = text.split()

    # Handle numeric transcripts directly
    if text.strip().isdigit():
        return int(text.strip())

    values = {**HINDI_NUMBERS, **ROMAN_NUMBERS}

    total = 0
    current = 0

    for token in tokens:
        if token in values:
            current += values[token]

        elif token in ("सौ", "sau"):
            current = max(current, 1) * 100

        elif token in ("हजार", "hazaar", "hazar"):
            total += max(current, 1) * 1000
            current = 0

        elif token in ("लाख", "lakh"):
            total += max(current, 1) * 100000
            current = 0

    return total + current


# Quick tests
if __name__ == "__main__":
    print("450 ->", number_to_hindi(450))
    print("450 Hindi ->", hindi_to_number("चार सौ पचास"))
    print("450 Roman ->", hindi_to_number("chaar sau pachaas"))
    print("1250 ->", number_to_hindi(1250))
