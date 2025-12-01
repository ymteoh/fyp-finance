# generate_forecast_zips.py
import os
import zipfile

# -------------------------------
# Shared Currency Configuration (copy directly from settings.py)
# -------------------------------
currency_options = [
    "MYR", "USD", "EUR", "JPY", "GBP", "AUD", "CAD", "CHF", "CNY", "SEK",
    "NZD", "KRW", "SGD", "NOK", "MXN", "BRL", "ZAR", "RUB", "TRY", "AED",
    "INR", "PHP", "IDR", "THB", "VND", "PKR", "BDT", "LKR", "MMK", "EGP"
]

forecast_dir = "income_expense_forecast"
output_dir = "forecast_zips"
os.makedirs(output_dir, exist_ok=True)

def get_currency_files(currency):
    files = []
    for f in os.listdir(forecast_dir):
        if f.endswith((".csv", ".png", ".md")):
            if currency == "MYR":
                # For MYR: exclude files with _<other_currency>.
                if not any(f"_{c}." in f for c in currency_options if c != "MYR"):
                    files.append(f)
            else:
                # For others: include only files with _<currency>.
                if f"_{currency}." in f:
                    files.append(f)
    return files

# Generate ZIP for each currency
for currency in currency_options:
    files = get_currency_files(currency)
    if files:
        zip_path = os.path.join(output_dir, f"forecasts_{currency}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                zf.write(os.path.join(forecast_dir, f), f)
        print(f"✅ Created {zip_path} ({len(files)} files)")
    else:
        print(f"⚠️ No files for {currency}")