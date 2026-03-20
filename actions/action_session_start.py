from datetime import datetime
from typing import Any, Dict, List, Text

from rasa_sdk import Action, Tracker
from rasa_sdk.events import ActionExecuted, SessionStarted, SlotSet


class ActionSessionStart(Action):
    def name(self) -> Text:
        return "action_session_start"

    def set_current_date(self) -> List[Dict[Text, Any]]:
        current_date = datetime.now().strftime("%d/%m/%Y")
        return [SlotSet("current_date", current_date)]

    def set_mcp_client_id(self) -> List[Dict[Text, Any]]:
        # Demo user — corresponds to client_id 825 in the MCP datasets
        return [SlotSet("mcp_client_id", 825)]

    def run(
        self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        return (
            self.set_current_date()
            + self.set_mcp_client_id()
            + [ActionExecuted("action_listen")]
        )
