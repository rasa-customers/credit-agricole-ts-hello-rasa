import logging
from typing import Any, Dict, List, Text

import requests
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

logger = logging.getLogger(__name__)

MCP_BASE_URL = "http://localhost:8000"


class ActionGetProfile(Action):
    def name(self) -> Text:
        return "action_get_profile"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        client_id = tracker.get_slot("mcp_client_id")

        if not client_id:
            dispatcher.utter_message(response="utter_profile_error")
            return []

        try:
            response = requests.get(
                f"{MCP_BASE_URL}/user-profile",
                params={"user_id": int(client_id)},
                timeout=10,
            )
            data = response.json()

            if response.ok and data.get("success"):
                p = data["profile"]
                dispatcher.utter_message(
                    text=(
                        f"Voici vos informations personnelles :\n"
                        f"- **Adresse** : {p.get('address', 'N/A')}\n"
                        f"- **Âge** : {p.get('current_age', 'N/A')} ans\n"
                        f"- **Genre** : {p.get('gender', 'N/A')}\n"
                        f"- **Revenu annuel** : {p.get('yearly_income', 'N/A')}\n"
                        f"- **Score de crédit** : {p.get('credit_score', 'N/A')}\n"
                        f"- **Nombre de cartes** : {p.get('num_credit_cards', 'N/A')}"
                    )
                )
            else:
                logger.error(f"Profile fetch failed: {data}")
                dispatcher.utter_message(response="utter_profile_error")

        except requests.RequestException as e:
            logger.error(f"MCP server unreachable: {e}")
            dispatcher.utter_message(response="utter_profile_error")

        return []
