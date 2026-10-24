# AI Prompts Log — MGT 409 HW4: Campus Customs Shop + Chatbot

This file is the log of what I typed to my vibe coder (Claude). There is one section per problem. Each section has the problem number and title, at least one prompt I typed in my own words, and a follow-up prompt if one was needed (with one sentence on what was lacking after the first). Our running site, database writes, and screenshots are the evidence that the work was completed.

---

## Problem 1: Vibe Coder Prompts

**Prompt:**

> Problem 1: Vibe Coder Prompts.
>
> Create AI_Prompts.md and keep it updated as we work.
>
> Put one section for each problem. Each section must include:
>
> -the problem number and title
> -at least one prompt I typed in my own words
> -One follow-up prompt if we needed it
>
> Our running site, database writes, and screenshots are the evidence - we do not need an extra proof essay beyond these prompts

**Follow-up prompt:** None needed.

---

## Problem 2: Analyze the database

**Prompt:**

> Problem 2: Analyze the database
>
> Look at the database data/campus_customs.db and understand the fields of each table.  At a minimum, we should understand: catalogue, inventory, and users.
>
> Start the file output/harness.md. Write down each table and its fields, and one short line on why each field matters for the shop or the chatbot.  We will keep growing this harness file in later problems (models, tools, safety, specs).

**Follow-up prompt:**

> Did you write one short line on why each field matters?

What was missing after the first prompt: several field explanations ran to two sentences, so they were trimmed to one short line each, and the extra detail moved into the Data notes.

---

## Problem 3: Build the Campus Customs website

**Prompt:**

> problem 3: build the campus customs website
>
> Scaffold a React + Vite + TypeScript front end for campus customs.  Put a nav bar at the top that links to the main pages:
> -home
> -products
> -about us
> -log in
> -create account
>
> Pull campus customs-style wording from www.yalebulldogblue.com for home and about us, but write these pages in our own voice based on how you've interacted with me thus far and understand my voice to be.
>
> On the Products page, show product images from the catalogue (use the image paths in the database) with basic product info (name, price, short description).
>
> Make each product open a single-item page (large image on one side, full product text on the other - description, price, sizes/stock when you have them). clicking a card on Products should take the shopper there.
>
> add a chat interface in the bottom right of the site (a floating chat panel is fine). it does not need to talk to an agent yet - a stub that will call our backend later is enough for this problem.
>
> We will need a small API soon to read the database. its fine to start a simple FastAPI app in backend/main.py just to serve products and images, then grow it into the agent backend in problem 5.

**Follow-up prompt:** None needed.

---

## Problem 4: Create account and login

**Prompt:**

> problem 4: create account and login
>
> build a normal create-account / login flow.
>
> -create account: first name, last name, email, password (confirm password is a nice touch)
> -log in: email and password
>
> new accounts go in the users table. make sure to store passwords securely so that hackers (human or AI) cannot access them.
>
> the seed database already has a test user you can use while building:
> -email: test@campuscustoms.yale.edu
> -password: password
> -hash function: pbkdf-hmac-sha256, 120,000 iterations (stored as pbkdf2_sha256$salt$hash)
>
> how login checks a password:
> -you never un-hash the stored value. you re-hash what the user typed and compare
> -read the salt out of the stored string (the middle piece) - do not make a new one at login
> -hash the typed password with that same salt and then compare to the stored hash. use a constant-time compare.
> -signup and login must use hte same hash settings (same function, same salt handling, same iteration count). if they differ, even the right password will not match.
> -surest check: log in as the seeded test user and as a brand-new account you just created in your own app.
>
> confirm you can log in as that user and that a brand new account you create also works.
>
> update output/harness.md with how auth works (what we store for a user and how passwords are protected).

**Follow-up prompt:** None needed.

---

## Problem 5: PydanticAI agent backend

**Prompt:**

> problem 5: pydanticAI agent backend
>
> build the shop chatbot as a pydanticAI agent behind fastAPI, plugged into our front end chat widget. put the API app in backend/main.py - that is the file we run with Uvicorn. keep the agent as these four files next to it:
>
> -backend/prompts/prompt.md
> -backend/agent.py
> -backend/tools.py
> -backend/models.py
>
> in main.py, expose a chat route so a message from the website returns a reply from the agent and whatever else i need for products/auth. we will need my AI model API key for the agent.
>
> put campus customs voice and safety basics into prompts/prompt.md and we will expand tools and safety later. start or update types in models.py for chat replies/product cards as needed.  in output/harness.md, note how the front end talks to fastAPI and how the agent is loaded (prompt file + model).
>
> make sure hte backend runs from the backend/ folder like this:
>
> uvicorn main:app --reload --port 8000

**Follow-up prompt:** None needed.

---

## Problem 6: Tools: product info and stock

**Prompt:**

> problem 6 - tools: product info and stock
>
> give the agent tools that look up real information from campus_customs.db
>
> -product decription
> -price
> -how many are in stock (by size when the customer asks)
>
> the agent must use the database - it should not invent prices or quantities. if a size is out of stock, say so clearly.
>
> expand prompts/prompt.md so the agent knows to call these tools for price and stock questions. add or update return types in models.py.
>
> in output/harness.md, list each tool and explain which model fields you chose for lookup results and why

**Follow-up prompt:** None needed.

---

## Problem 7: Chat search that updates the page

**Prompt:**

> problem 7 - chat search that updates the page
>
> now we waill add a neat feature to the site. when a customer asks about a type of item - for example, what hoodies do you have? - the agent should search the catalogue and the website should dynamically show those matching items as product cards (image, name, price, short info).
>
> this is an api contract. the agent returns structured product matches and then the front end renders them on the website. it looks really cool.
>
> after the dynamic product cards are loaded by the new feature, make sure the same single-item page behavior we built in problem 3 still works. each product card - including ones the chat just put on the page - should still open that detail view (large image + full info) when clicked.
>
> update prompts/prompt.md and output/harness.md so it is clear how search results reach the page.

**Follow-up prompt:** None needed.

---

## Problem 8: Customer memory

**Prompt:**

> problem 8- customer memory
>
> when a shopper is logged in, save their chat history in the database in an appropriate table and reload it when they return. the agent should know who is chatting (name, email) - put that in agent deps (or an equivalent clear pattern) and/or tools the agent can call.
>
> also pass enough page context that if someone is on a product page and asks do you have this in pink, the agent knows which item they mean. hint: we can put code into the agent context.
>
> guests can still chat, but history only needs to persist for logged-in users.
>
> document in output/harness.md: how user chat history is stored, what customer fields the agent sees, and how page context is passed

**Follow-up prompt:**

> the messages are still there but it doesnt say welcome back edward as the newest message

What was missing after the first prompt: the reloaded history worked, but the "Welcome back" greeting was placed above the old messages, so it was hidden once the chat scrolled to the bottom. It now appears as the newest message, below the reloaded history.

---

## Problem 9: Usability improvements

**Prompt:**

> problem 9: usability improvements
>
> now that the core shop works, improve it. let's choose and implement:
>
> -2 front-end usability improvements
> -2 agent/backend usability improvements
>
> front-end improvements are things that make the site look better and make it easier to use.
>
> agent/backend improvements are things that make the agent output better, more accurate, or safer. these could be new agent tools or things that make the agent run faster or cheaper.
>
> write output/usability.md before or as we build. for each of the improvements, say:
>
> -what we added
> -why it helps a campus customs shopper or the business
>
> then make sure all improvements actually show up in the running app. graders will read the write-up and look for the features.

**Follow-up prompt** (my choices from the options Claude suggested):

> Front end: Quick-start chat chips, Products page filters. Agent/backend: Filtered search tool, Safety guardrail.

What was missing after the first prompt: the first prompt didn't name which four improvements to build, so I picked two front-end and two agent features from a short list of options.

---

## Problem 10: Style the website

**Prompt:**

> problem 10 - style the website
>
> add creative design so the site feels like a real campus customs storefront. fonts, color, hierarchy, motion, product presentation, chat feel, etc. we get more points for imaginative and innovative design!!!
>
> write output/design.md: what we changed and why it should help customers stick around and buy. keep it concrete and short. Go!

**Follow-up prompt:** None needed.

---

## Problem 11: Site testing (app check)

**Prompt:**

> problem 11 - site testing (app check)
>
> test the live site and document it in output/app_check.html (a page you can double click open). include clear screenshots and short captions for:
>
> -chat checking the inventory level of an item (honest stock/price from the DB)
> -the dynamic search result cards appearing after a category question (e.g. hoodies)
> -one of the usability features we added in problem 9
>
> make the HTML easy to grade - heading for each check, screenshot, one or two sentences on what the screenshot proves.
>
> put the screenshot image files in output/app_check_images/ and link them from app_check.html with relative paths (for example app_check_images/inventory.png).

**Follow-up prompt:** None needed.

---

## Problem 12: Audit trail, safety, finish harness

**Prompt:**

> problem 12 - audit trail, safety, finish harness
>
> keep an append-only output/audit_trail.json of agent-loop activity (time, tool name, short args/result, stop reason). do not wipe it between runs.
>
> also, think of some safety rules to give the agent and put them in prompts/prompt.md.
>
> finish output/harness.md so it is clear how the system works.
>
> -model fields in models.py
> -tools and abilities
> -safety rules
> -specs (loop limits, result caps, models, how to run front + back)

**Follow-up prompt:** None needed.

---

## Problem 13: Push to GitHub and submit the URL

**Prompt:**

> problem 13 - push to github and submit the url
>
> put our code in a folder named hw4 and push it to a public github repository. on canvas, i'll submit the repo url (the link graders can open and clone).
>
> do not put our real .env, campus_customs.db, or product images in the github repo. use .gitignore. include .env.example with placeholders only.
>
> the agent itself is four files under backend/: prompts/prompt.md, agent.py, tools.py, and models.py
>
> README.md should explain how to run the front end and back end after placing the data pack.

**Follow-up prompt:** None needed.

---
