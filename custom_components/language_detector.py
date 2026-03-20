import logging
from typing import Any, Dict, List, Text
from rasa.engine.graph import ExecutionContext, GraphComponent
from rasa.engine.recipes.default_recipe import DefaultV1Recipe
from rasa.engine.storage.resource import Resource
from rasa.engine.storage.storage import ModelStorage
from rasa.shared.core.events import SlotSet
from rasa.shared.core.trackers import DialogueStateTracker
from rasa.shared.nlu.training_data.message import Message
from rasa.shared.nlu.training_data.training_data import TrainingData
from ftlangdetect import detect

LANGUAGE_SLOT = "language"
logger = logging.getLogger(__name__)

ALLOWED_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "pt": "Portuguese",
    "de": "German"
}

@DefaultV1Recipe.register(
    [DefaultV1Recipe.ComponentType.MESSAGE_FEATURIZER], is_trainable=False
)
class LanguageDetector(GraphComponent):
    """Custom component to detect the user's input language only at the start of conversation."""

    def __init__(self):
        pass

    @staticmethod
    def create(
        config: Dict[Text, Any],
        model_storage: ModelStorage,
        resource: Resource,
        execution_context: ExecutionContext,
    ) -> GraphComponent:
        return LanguageDetector()

    def detect_language(self, text: Text) -> str:
        """Detects the language of a given text using ftlangdetect."""
        if not isinstance(text, str) or not text.strip():
            return "unknown"

        try:
            result = detect(text=text, low_memory=False)
            detected_language = result.get("lang", "unknown")
            confidence = result.get("score", 0.0)

            if detected_language not in ALLOWED_LANGUAGES or confidence < 0.3:
                detected_language = "en"  # Default to English if not allowed or confidence is too low
            return detected_language
        except Exception as e:
            logger.warning(f"Language detection failed ({e}); defaulting to 'en'.")
            return "en"

    def process_training_data(self, training_data: TrainingData) -> TrainingData:
        """Processes training data to add detected language information."""
        for message in training_data.training_examples:
            text = message.get("text", "")
            language = self.detect_language(text)
            if language:
                message.set("language", language)
                logger.debug(f"Set language '{language}' for text: {text}")
        return training_data

    def process(
        self,
        messages: List[Message],
        tracker: DialogueStateTracker = None,
        **kwargs: Any,
    ) -> List[Message]:
        """Processes messages during inference and sets the detected language only at the start of conversation."""

        # Check if language is already set in the slot
        existing_language = tracker.get_slot(LANGUAGE_SLOT) if tracker else None

        for message in messages:
            text = message.get("text", "")

            # Only detect the language if it's not set yet
            if not existing_language:
                language = self.detect_language(text)
                message.set("language", language, add_to_output=True)

                if tracker:
                    tracker.update(SlotSet(LANGUAGE_SLOT, language))
                    logger.info(f"Detected language '{language}' and set it in slot '{LANGUAGE_SLOT}'")
            else:
                # Use existing language and ensure it's set in messages
                message.set("language", existing_language, add_to_output=True)

        return messages
