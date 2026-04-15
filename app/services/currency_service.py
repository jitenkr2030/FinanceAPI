CURRENCIES = {
    "USD": {"symbol": "$",    "name": "US Dollar",        "rate": 1.0},
    "EUR": {"symbol": "€",    "name": "Euro",             "rate": 0.92},
    "GBP": {"symbol": "£",    "name": "British Pound",    "rate": 0.79},
    "CAD": {"symbol": "CA$",  "name": "Canadian Dollar",  "rate": 1.36},
    "AUD": {"symbol": "A$",   "name": "Australian Dollar","rate": 1.53},
    "JPY": {"symbol": "¥",    "name": "Japanese Yen",     "rate": 149.5},
    "INR": {"symbol": "₹",    "name": "Indian Rupee",     "rate": 83.2},
}

def get_all_currencies():
    return {code: info["name"] for code, info in CURRENCIES.items()}

def get_currency_symbol(code: str) -> str:
    return CURRENCIES.get(code, {}).get("symbol", code)

def convert_to_usd(amount: float, from_currency: str) -> float:
    rate = CURRENCIES.get(from_currency, {}).get("rate", 1.0)
    return amount / rate

def format_amount(amount: float, currency: str) -> str:
    symbol = get_currency_symbol(currency)
    return f"{symbol}{amount:,.2f}"

def format_pdf_amount(amount: float, currency: str) -> str:
    return f"{currency} {amount:,.2f}"
