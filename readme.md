# Udhaar 

**A voice-powered digital khata for local shopkeepers.**

Udhaar Voice helps shopkeepers record customer credit and payments using voice instead of maintaining a physical notebook.

Speak a transaction, review the extracted details, and save it to a digital ledger. You can also generate payment reminders in Indian languages.

Built using **Gnani AI Prisma and Timbre** for the Great Indian AI Internship Challenge 2026.

## The Problem

Many small shopkeepers still manage udhaar through notebooks. Tracking payments, calculating balances and reminding customers manually can be difficult.

Most digital bookkeeping tools also rely on typing, which isn't always convenient for shopkeepers who prefer speaking in their local language.

## How It Works

For example, a shopkeeper says:

> Ramesh ne 500 rupaye udhaar liye.

Udhaar Voice extracts the customer name, amount and transaction type. The shopkeeper reviews the details and saves the entry.

When Ramesh pays ₹200, the balance automatically updates to ₹300.

## Features

- **Voice-based entry:** Record transactions directly through the browser.
- **Speech-to-text:** Convert audio into text using Gnani AI Prisma.
- **Information extraction:** Extract customer name, amount and pending days.
- **Credit and payment tracking:** Record transactions and validate repayments.
- **Digital ledger:** Store customers and transactions in Supabase.
- **Balance tracking:** Calculate outstanding amounts and view transaction history.
- **Voice reminders:** Generate and play payment reminders using Gnani AI Timbre.

### Language Support

The application is configured for 10 Indian language options:

Hindi, English, Bengali, Gujarati, Kannada, Malayalam, Marathi, Punjabi, Tamil and Telugu.

- Hindi and English: validated for the main voice-to-ledger demonstration.
- Transaction classification: validated for Hindi and English.
- Reminder generation: configured for the supported language options.

Language support and accuracy may vary, and further testing is needed across different accents and speaking styles.

## Tech Stack

| Component | Technology |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python, FastAPI |
| Speech-to-Text | Gnani AI Prisma |
| Text-to-Speech | Gnani AI Timbre |
| Database | Supabase (PostgreSQL) |
| Audio Processing | FFmpeg |

## Project Structure

```text
Udhaar/
├── main.py
├── config.py
├── routes/
│   ├── customers.py
│   ├── transactions.py
│   └── voice_ledger.py
├── services/
│   └── ledger_service.py
├── schemas/
│   ├── transaction.py
│   └── voice_ledger.py
├── database/
│   └── supabase_client.py
├── test_recorder.html
├── requirements.txt
└── .env
```

## Getting Started

**1. Clone the repository**

```bash
git clone YOUR_REPOSITORY_URL
cd Udhaar
```

**2. Create a virtual environment**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

Make sure FFmpeg is installed.

**4. Configure environment variables**

Create a `.env` file:

```env
GNANI_API_KEY=your_gnani_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_SECRET_KEY=your_supabase_secret_key
```

Create the `customers` and `transactions` tables and the `customer_balances` view in Supabase using the database schema.

Never commit your `.env` file or expose the Supabase secret key in frontend code.

**5. Run the backend**

```bash
python -m uvicorn main:app --reload
```

API documentation: `http://127.0.0.1:8000/docs`

**6. Run the frontend**

Open another terminal:

```bash
python3 -m http.server 5500
```

Visit `http://localhost:5500/test_recorder.html` and allow microphone access.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/transcribe` | Convert audio to text |
| POST | `/extract` | Extract transaction details |
| POST | `/remind` | Generate reminder audio |
| POST | `/ledger/from-voice` | Save a voice transaction |
| GET | `/customers/` | Get customers and balances |
| POST | `/customers/` | Create a customer |
| POST | `/transactions/credit` | Record credit |
| POST | `/transactions/payment` | Record payment |
| GET | `/transactions/{customer_id}/history` | View transaction history |

## Demo

1. Record: "Ramesh ne 500 rupaye udhaar liye."
2. Review and save the ₹500 credit.
3. Record: "Ramesh ne 200 rupaye wapas diye."
4. Save the payment.
5. Show the updated outstanding balance: **₹300**.
6. Generate and play a voice reminder.

## What's Next

- Automated voice-call reminders.
- WhatsApp Business integration.
- Better customer matching using phone numbers.
- Merchant authentication and multi-shop support.
- Improved multilingual transaction classification.

---

**Built with Gnani AI, FastAPI and Supabase.**

*Making bookkeeping as simple as speaking.*