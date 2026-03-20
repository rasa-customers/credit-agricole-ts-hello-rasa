# Hello Rasa — Export & Customization Guide

## Step 1 — Open the project in Hello Rasa

Click the button below to load this repository directly into Hello Rasa:

[![Open in Hello Rasa](https://img.shields.io/badge/Open%20in%20Hello%20Rasa-7b61ff?style=for-the-badge)](https://hello.rasa.com/go?repo=rasa-customers/credit-agricole-ts-hello-rasa)

Hello Rasa will clone the repository, build the Rasa image, and deploy the bot automatically.

---

## Step 2 — Expose the local MCP server with ngrok

Hello Rasa runs in the cloud and cannot reach `localhost:8000`. You need to expose your local MCP server publicly using ngrok.

**Start the MCP server locally:**
```bash
python mcp_server/server.py
```

**In a second terminal, start ngrok:**
```bash
ngrok http 8000
```

ngrok will print a public URL like:
```
Forwarding   https://abcd-1234.ngrok-free.app -> http://localhost:8000
```

Copy that URL — you'll need it in the next step.

---

## Step 3 — Update the MCP server URL in Hello Rasa

Hello Rasa is currently configured to use `http://localhost:8000/mcp` (which only works when running locally). You need to update it to point to your ngrok URL.

1. In Hello Rasa, open the **Code** tab
2. Open `endpoints.yml`
3. Replace the MCP server URL:

```yaml
mcp_servers:
  - name: credit_agricole_mcp
    url: "https://abcd-1234.ngrok-free.app/mcp"   # ← your ngrok URL
    type: http
```

4. Click **Save** — Hello Rasa will redeploy the bot with the updated endpoint

> **Note:** Your ngrok URL changes every time you restart ngrok (unless you have a paid plan with a static domain). Remember to update `endpoints.yml` each session.

---

## Step 4 — Verify the deployment

Once the build is complete, Hello Rasa will display a chat interface. Send a first message to confirm the bot is responding:

```
Bonjour
```

You should see the welcome message. If the bot does not respond, check the build logs in the Hello Rasa interface.

---

## Step 5 — Modify a flow

**Use case:** You want to change the behavior of an existing flow (e.g., add a step, change a description, update a collect).

1. In Hello Rasa, open the **Code** tab
2. Navigate to `data/flows/` and open the flow you want to edit (e.g., `address.yml` to modify the address update flow)
3. Make your changes directly in the editor
4. Click **Save** — Hello Rasa will automatically retrain the model and redeploy

**Example:** Change the address flow to also collect a phone number:
```yaml
steps:
  - collect: physical_address
    ask_before_filling: true
  - collect: phone_number        # new step
    ask_before_filling: true
  - action: utter_confirm_address
  ...
```

---

## Step 6 — Modify a sub-agent prompt

**Use case:** You want to change how the cards or payments sub-agent behaves — its tone, what data it focuses on, or its instructions.

1. In Hello Rasa, open the **Code** tab
2. Navigate to `sub_agents/cards_agent/prompt_template.jinja2` (or `payments_agent/`)
3. Edit the prompt instructions directly

**Tips for effective prompt edits:**
- Add explicit instructions for edge cases (e.g., "If the user asks about a card that doesn't exist, say so clearly")
- Change the response format (e.g., "Always present cards in a bulleted list")
- Adjust the tone (e.g., "Respond in a formal, professional tone")
- After editing, click **Save** — the sub-agent prompt is loaded at runtime, no retrain needed

---

## Step 7 — Modify a response (utter)

**Use case:** You want to change the wording of a bot message.

1. In Hello Rasa, open the **Code** tab
2. Navigate to `domain/` and open the relevant domain file:
   - `domain/address.yml` — address update and profile responses
   - `domain/default_flows.yml` — general responses (greeting, help, error messages)
3. Find the response key you want to edit (e.g., `utter_address_update_success`) and change the `text` value
4. Click **Save** — Hello Rasa will retrain and redeploy

**Example:** Make the success message more enthusiastic:
```yaml
  utter_address_update_success:
    - text: "Parfait ! Votre adresse a bien été mise à jour. 🎉"
      metadata:
        rephrase: false
```

---

## Reference — Key files to customize

| What you want to change | File |
|---|---|
| Flow logic and steps | `data/flows/<flow_name>.yml` |
| Cards sub-agent behavior | `sub_agents/cards_agent/prompt_template.jinja2` |
| Payments sub-agent behavior | `sub_agents/payments_agent/prompt_template.jinja2` |
| Bot responses (utters) | `domain/address.yml`, `domain/default_flows.yml` |
| LLM model / temperature | `config.yml`, `sub_agents/*/config.yml` |
| MCP server tools | `mcp_server/server.py` |
| Knowledge base content | `docs/*.txt` |
