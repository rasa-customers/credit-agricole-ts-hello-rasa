import logging
from typing import Any, Dict, List, Text

import requests
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

logger = logging.getLogger(__name__)

MCP_BASE_URL = "http://localhost:8000"


class ActionUpdateAddress(Action):
    def name(self) -> Text:
        return "action_update_address"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        client_id = tracker.get_slot("mcp_client_id")
        new_address = tracker.get_slot("physical_address")

        if not client_id or not new_address:
            dispatcher.utter_message(response="utter_address_update_error")
            return []

        try:
            response = requests.post(
                f"{MCP_BASE_URL}/update-address",
                json={"user_id": int(client_id), "new_address": new_address},
                timeout=10,
            )
            data = response.json()

            if response.ok and data.get("success"):
                dispatcher.utter_message(response="utter_address_update_success")
            else:
                logger.error(f"Address update failed: {data}")
                dispatcher.utter_message(response="utter_address_update_error")

        except requests.RequestException as e:
            logger.error(f"MCP server unreachable: {e}")
            dispatcher.utter_message(response="utter_address_update_error")

        return [SlotSet("physical_address", None)]
