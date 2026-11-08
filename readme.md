# Udhaar 

**A voice-powered digital khata for local shopkeepers.**

Udhaar Voice helps shopkeepers record customer credit and payments using voice instead of maintaining a physical notebook.

Speak a transaction, review the extracted details, and save it to a digital ledger. You can also generate payment reminders in Indian languages.

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

Enable Email auth in Supabase Dashboard → Authentication → Providers. The
backend verifies every bearer access token with Supabase Auth; it never trusts a
merchant ID from the browser. Customer, transaction, dashboard, and correction
APIs require `Authorization: Bearer <access_token>`.

Create the browser configuration file from the template:

```bash
cp frontend-config.js frontend-config.local.js
```

Set `UDHAAR_SUPABASE_URL` and `UDHAAR_SUPABASE_PUBLISHABLE_KEY` in
`frontend-config.local.js`. The HTML loads the safe example first and then
automatically overrides it with the local file when present. The
publishable/anon key is intended for browser use; never put
`SUPABASE_SECRET_KEY` in frontend files.

Create the `customers` and `transactions` tables and the `customer_balances` view in Supabase using the database schema.

For atomic transaction validation and duplicate prevention, run
[`database/migrations/20261108_atomic_transactions.sql`](database/migrations/20261108_atomic_transactions.sql)
in the Supabase SQL editor after the base tables exist. This adds the transaction
idempotency key and the `record_transaction` RPC used by the API.

Then run
[`database/migrations/20261108_merchant_auth_rls.sql`](database/migrations/20261108_merchant_auth_rls.sql).
It adds merchant ownership, RLS policies, audited correction support, and the
merchant-aware transaction RPC. Existing rows remain unassigned (`merchant_id`
is `NULL`) and are intentionally not visible to any new merchant. Assign demo
rows manually only after identifying the correct Supabase Auth user.

Migration order:

1. Base `customers`, `transactions`, and balance view.
2. `20261108_atomic_transactions.sql`.
3. `20261108_merchant_auth_rls.sql`.

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


## What's Next

- Automated voice-call reminders.
- WhatsApp Business integration.
- Better customer matching using phone numbers.
- Merchant authentication and multi-shop support.
- Improved multilingual transaction classification.

---

**Built with Gnani AI, FastAPI and Supabase.**

*Making bookkeeping as simple as speaking.*
