# Demo Script — Crédit Agricole Bot

This script walks through the key features of the bot in a logical order. Each section is a self-contained conversation thread.

> **Setup reminder:** MCP server must be running (`python mcp_server/server.py`) and Rasa Inspector open before starting.

---

## 1. Welcome

**Goal:** Show the greeting flow and bot personality.

| Role | Message |
|------|---------|
| User | `Bonjour` |
| Bot | Welcome message with capabilities overview |

---

## 2. FAQ — Knowledge Base (Enterprise Search)

**Goal:** Show that the bot answers financial questions using the FAISS knowledge base.

| Role | Message |
|------|---------|
| User | `Comment fonctionne un livret A ?` |
| Bot | Explanation from the savings knowledge base |
| User | `Quelles sont les règles de déductibilité des intérêts d'emprunt ?` |
| Bot | Answer from the taxation knowledge base |
| User | `Qu'est-ce qu'une assurance vie ?` |
| Bot | Answer from the insurance knowledge base |

---

## 3. Card Questions — ReAct Sub-Agent + MCP

**Goal:** Show the `cards_agent` sub-agent calling MCP tools dynamically.

| Role | Message |
|------|---------|
| User | `Liste mes cartes actives` |
| Bot | List of active cards with brand, type, last 4 digits, expiry |
| User | `Est-ce qu'une de mes cartes va expirer dans les 3 prochains mois ?` |
| Bot | Answer based on expiry dates from the MCP `get_cards` tool |
| User | `J'ai des cartes sur le dark web ?` |
| Bot | Dark web exposure status |

---

## 4. Payment Questions — ReAct Sub-Agent + MCP

**Goal:** Show the `payments_agent` sub-agent with aggregation and filtering.

| Role | Message |
|------|---------|
| User | `Dans quelle ville ai-je fait le plus de paiements ?` |
| Bot | Top city with transaction count and total amount |
| User | `Combien ai-je dépensé en restaurants ?` |
| Bot | Total spending for restaurant MCC category |
| User | `Montre-moi mes 5 dernières transactions` |
| Bot | Most recent transactions with merchant, amount, date |

---

## 5. Personal Profile — REST Action

**Goal:** Show the `view_profile` flow calling the MCP REST endpoint.

| Role | Message |
|------|---------|
| User | `Montre-moi mes informations personnelles` |
| Bot | Profile card: address, age, gender, annual income, credit score, number of cards |

---

## 6. Address Update — CALM Flow + REST Action

**Goal:** Show a structured multi-step CALM flow with confirmation and data write.

| Role | Message |
|------|---------|
| User | `Je veux changer mon adresse` |
| Bot | `Quelle est votre nouvelle adresse postale ?` |
| User | `25 bis rue de la Santé, Paris 75013` |
| Bot | Confirmation message with the new address |
| User | *(clicks "Oui, confirmer")* |
| Bot | `Votre adresse a bien été mise à jour.` |

**Verify the update:**

| Role | Message |
|------|---------|
| User | `Montre-moi mes informations personnelles` |
| Bot | Profile with the new address |

---

## 7. Topic Switching (Bonus)

**Goal:** Show that the bot handles context switching between domains cleanly.

| Role | Message |
|------|---------|
| User | `Liste mes cartes actives` |
| Bot | Card list |
| User | `Et mes dernières transactions ?` |
| Bot | Recent transactions (switches to payments sub-agent) |
| User | `C'est quoi le taux d'usure ?` |
| Bot | Financial FAQ answer (switches to Enterprise Search) |

---

## Tips for a Smooth Demo

- The demo user is **client ID 825** (hardcoded in `action_session_start.py`)
- If the bot seems stuck, open Rasa Inspector and check the flow stack
- The MCP server logs show every tool call in real time — useful to show the ReAct reasoning
- Address updates persist in-memory for the duration of the MCP server session
