import numpy as np
import typing
from typing import Any, Optional, Text, Dict

from rasa.nlu.config import RasaNLUModelConfig
from rasa.nlu.featurizers.featurizer import Featurizer
from rasa.nlu.training_data import Message, TrainingData

if typing.TYPE_CHECKING:
    from spacy.tokens import Doc

from rasa.nlu.constants import (
    TEXT_ATTRIBUTE,
    SPACY_DOCS,
    DENSE_FEATURE_NAMES,
    DENSE_FEATURIZABLE_ATTRIBUTES,
    TOKENS_NAMES,
)


class SpacyFeaturizer(Featurizer):

    provides = [
        DENSE_FEATURE_NAMES[attribute] for attribute in DENSE_FEATURIZABLE_ATTRIBUTES
    ]

    requires = [
        SPACY_DOCS[attribute] for attribute in DENSE_FEATURIZABLE_ATTRIBUTES
    ] + [TOKENS_NAMES[attribute] for attribute in DENSE_FEATURIZABLE_ATTRIBUTES]

    defaults = {
        # Specify what pooling operation should be used to calculate the vector of
        # the CLS token. Available options: 'mean' and 'max'
        "pooling": "mean"
    }

    def __init__(self, component_config: Optional[Dict[Text, Any]] = None):
        super().__init__(component_config)

        self.pooling_operation = self.component_config["pooling"]

    def _features_for_doc(self, doc: "Doc") -> np.ndarray:
        """Feature vector for a single document / sentence / tokens."""
        return np.array([t.vector for t in doc])

    def train(
        self,
        training_data: TrainingData,
        config: Optional[RasaNLUModelConfig] = None,
        **kwargs: Any,
    ) -> None:

        for example in training_data.intent_examples:
            for attribute in DENSE_FEATURIZABLE_ATTRIBUTES:
                self._set_spacy_features(example, attribute)

    def get_doc(self, message: Message, attribute: Text) -> Any:

        return message.get(SPACY_DOCS[attribute])

    def process(self, message: Message, **kwargs: Any) -> None:

        self._set_spacy_features(message)

    def _calculate_cls_vector(self, features: np.ndarray) -> np.ndarray:
        # take only non zeros feature vectors into account
        non_zero_features = np.array([f for f in features if f.any()])

        if self.pooling_operation == "mean":
            return np.mean(features, axis=0, keepdims=True)
        elif self.pooling_operation == "max":
            return np.max(features, axis=0, keepdims=True)
        else:
            raise ValueError(
                f"Invalid pooling operation specified. Available operations are "
                f"'mean' or 'max', but provided value is '{self.pooling_operation}'."
            )

    def _set_spacy_features(self, message: Message, attribute: Text = TEXT_ATTRIBUTE):
        """Adds the spacy word vectors to the messages features."""

        message_attribute_doc = self.get_doc(message, attribute)

        if message_attribute_doc is not None:
            features = self._features_for_doc(message_attribute_doc)

            cls_token_vec = self._calculate_cls_vector(features)
            features = np.concatenate([features, cls_token_vec])

            features = self._combine_with_existing_dense_features(
                message, features, DENSE_FEATURE_NAMES[attribute]
            )
            message.set(DENSE_FEATURE_NAMES[attribute], features)
