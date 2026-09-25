# Problem Statement: AI Nutrition Assistant Prototype

## Context

Build the prototype of a chatbot that answers questions about food, nutrition, and food safety.

Nothing sits under the model yet, so it answers from its own memory. It will invent claims, and those inventions need to be written down.

This prototype is the container for a later retrieval layer. Milestone 2 slides retrieval under this same app and turns every invented claim into a cited one. The interface, endpoints, and response schema stay exactly as they are. The work now is to build the container the citations land in.

## The Problem

Ask a model how much protein a vegetarian adult needs. The answer arrives in about two seconds, sounds specific, and comes from nobody.

Ask again tomorrow and the number has moved. Ask what a health authority recommends and the model will happily attribute a statement to that authority, whether or not the authority ever said it.

Food is a bad place for this to happen. A wrong answer reads exactly like a right one, and almost nobody goes and checks.

The prototype must make that failure visible and measurable. It must not hide it by hardcoding answers or patching individual cases.

## What Success Looks Like

A public chatbot that:

- Answers questions about food, nutrition, and food safety from the model's own knowledge.
- Returns structured output that always parses against a fixed schema.
- Leaves every claim's source as `null`, on purpose, so Milestone 2 only has to fill the contract in.
- Refuses calorie targets, weight recommendations, and medical advice, enforced in code as well as in the prompt.
- Ships with an empty sources panel that Milestone 2 will fill.
- Includes a failure log of 10 fixed questions, grouped and counted, so Milestone 2 can rerun the same set and compare.

## Product Surface

### 1. Chat Frontend

A message list, an input box, and a sources panel next to the conversation.

The sources panel stays empty this week. Build it now, because Milestone 2 fills it.

### 2. Backend

A chat endpoint, somewhere to store the conversation, and the model call.

Keep the model call on the server, not in the browser.

### 3. Response Schema

The model returns structured output, not prose.

Each response contains:

- Answer text
- A list of claims

Each claim contains:

- Claim text
- A source field

Every source comes back as `null` this week. That is deliberate. The contract is fixed now so Milestone 2 only has to fill it in.

Parse every response against the schema and fail when it does not parse.

### 4. System Prompt

The prompt must state:

- What the assistant does
- How it answers
- How long its answers should be
- What it will not touch

Keep a fixed set of questions and re-run all of them after every prompt change. Fixing one case while quietly breaking three others is the usual way this goes wrong.

### 5. Scope Limits, Enforced in Code

The assistant must not provide:

- Calorie or weight targets
- Recommendations about what anyone should weigh
- Medical advice

It should decline these questions and point the person to a qualified professional.

A line in the prompt will not hold on its own. Put the check in code as well.

### 6. Deploy

Push the project to GitHub and deploy it using Vercel and Railway so the app is live at a public URL.

### 7. The Failure Log

Write 10 questions across these 4 categories:

1. Nutrient requirements
2. Food safety and storage
3. Cooking methods
4. Questions where nobody has a clear answer

Run all 10 questions. For each response, record:

- Claims stated as fact with nothing behind them
- Numbers that shift between runs
- Sources it cited that cannot be found
- Questions it should have declined
- Questions where it hedged into uselessness

Group the failures and count them.

Milestone 2 will run the same 10 questions and compare the results.

Do not hardcode fixes. Record the failures.

## Tools

| Area | Options |
| --- | --- |
| Frontend and backend | [Next.js](https://nextjs.org/) or React with FastAPI |
| Scaffolding | Cursor or Anti-gravity |
| Model | Anthropic or OpenAI API |
| Storage | Supabase, Postgres, or SQLite |
| Deployment | Vercel or Railway |

Both Anthropic and OpenAI have structured output modes. Use structured outputs rather than parsing prose.

## Rules

- Every response must parse against the schema.
- The schema must include a claims list and a source field for each claim.
- Source fields must stay `null`.
- Scope limits must live in code, not only in the prompt.
- The app must be live at a public URL.
- Failures must be recorded, not patched around.
- Model calls must run behind the backend.

## Acceptance Tests

### Consistency

Ask the same question 3 times and compare the substance, not the wording.

A number that moves between runs is the failure that matters most.

Then run the 10 questions and fill in the failure log.

### Scope Limit

Ask the assistant:

- For a daily calorie target
- What someone with a specific condition should eat

Then:

- Rephrase both questions
- Ask them sideways
- Bring them up again after a few unrelated messages

The assistant should decline every time.

## Out of Scope for This Milestone

- Retrieval, citations, and real sources. Sources stay `null`.
- Hardcoded answers or case-by-case patches for model failures.
- Medical advice, calorie targets, and weight recommendations.

## Milestone 2 Boundary

Milestone 2 adds a retrieval layer under this same app. It does not change the interface, endpoints, or response schema. It fills the source fields and the sources panel that this prototype leaves empty, then reruns the same 10 questions to compare failure counts.
