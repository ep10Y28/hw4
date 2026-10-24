# Campus Customs Shop + Chatbot (MGT 409 HW4)

A storefront for **Campus Customs** (Yale Bulldog Blue, 57 Broadway, New Haven), with an AI shop assistant.

- **Front end:** React + Vite + TypeScript (`frontend/`)
- **Back end:** Python FastAPI (`backend/main.py`), whose brain is a **PydanticAI agent** calling OpenAI models through the course Portkey gateway
- **Data:** a local SQLite database (`data/campus_customs.db`) with the catalogue, inventory by size, users, and chat history

Shoppers can browse and filter products, create an account, and chat with "Ask the counter". The chat answers price and stock questions from the database, puts matching products on the page as cards, remembers logged-in shoppers, and knows which product page they're on.

## 1. Place the data pack (not in git)

The database and product photos are **not** in this repo. Unzip the course `data.zip` into this folder so you have:

```
hw4/
└── data/
    ├── campus_customs.db
    └── products/          # product images referenced by the catalogue
```

## 2. Add your API key

```bash
cp .env.example .env
```

Open `.env` and set `PORTKEY_API_KEY` to your own key. `.env` is git-ignored; never commit it.

## 3. Run the back end (Terminal 1)

Requires Python 3.10+.

```bash
pip3 install -r requirements.txt
cd backend
uvicorn main:app --reload --port 8000
```

If `uvicorn` isn't found, use `python3 -m uvicorn main:app --reload --port 8000`.

You should see `Shop agent ready (model: gpt-5.6-terra, prompt: prompt.md)`. On first start the backend adds a `sessions` table and a `results_label` column to the database if they're missing.

## 4. Run the front end (Terminal 2)

Requires Node 20.19+ (or 22.12+).

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. Vite forwards `/api` and `/images` to the backend on port 8000, so keep both terminals running.

**Test account:** `test@campuscustoms.yale.edu` / `password`, or create your own.

## What's where

```
hw4/
├── AI_prompts.md            # log of my prompts to the AI coding assistant, one section per problem
├── requirements.txt         # backend Python packages
├── .env.example             # placeholder keys only
├── README.md
├── frontend/                # Vite React TypeScript app
│   └── src/                 # pages/, components/, api.ts (all backend calls), auth.tsx, chatResults.tsx
├── backend/
│   ├── main.py              # FastAPI app: products, images, auth, /api/chat (run with uvicorn main:app)
│   ├── agent.py             # the PydanticAI agent: tools, dynamic instructions, output check, run loop
│   ├── tools.py             # tool logic: catalogue search + filters, price, stock, product cards, Portkey model
│   ├── models.py            # Pydantic types: agent output, tool results, API contract, ShopDeps
│   ├── prompts/prompt.md    # agent instructions: voice, tools, honesty, memory, safety rules
│   ├── auth.py              # signup/login, PBKDF2 passwords, hashed session tokens
│   ├── history.py           # saved chat history for logged-in shoppers
│   ├── guardrails.py        # input/output safety checks (redaction, injection blocking)
│   └── audit.py             # append-only audit trail writer
└── output/
    ├── harness.md           # how the whole system works: data, models, tools, safety, specs
    ├── design.md            # Problem 10 design write-up
    ├── usability.md         # Problem 9 improvements
    ├── app_check.html       # Problem 11 live-site test report (open in a browser)
    ├── app_check_images/    # screenshots used by app_check.html
    └── audit_trail.json     # append-only log of agent-loop activity
```

The agent itself is the four files `backend/prompts/prompt.md`, `agent.py`, `tools.py`, and `models.py`. The other backend modules are the harness around it. Start with **`output/harness.md`** for the full picture, including loop limits, result caps, and safety rules.
