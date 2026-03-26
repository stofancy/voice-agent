"""
Agent Router for Voice Agent.

Routes user requests to appropriate specialized agents based on intent classification.
"""

import re
from typing import Optional, Tuple
from loguru import logger

from .base import BaseAgent


BOOKING_KEYWORDS = [
    "book",
    "booking",
    "hotel",
    "flight",
    "reserve",
    "reservation",
    "stay",
    "accommodation",
    "room",
]

QUERY_KEYWORDS = [
    "weather",
    "temperature",
    "search",
    "find",
    "what",
    "who",
    "when",
    "where",
    "how",
    "time",
    "date",
    "information",
    "look up",
    "check",
]


class AgentRouter:
    """
    Routes user requests to appropriate agent based on intent.

    Uses keyword-based classification to determine if a request
    should be handled by a booking agent or query agent.
    """

    def __init__(
        self,
        booking_agent: Optional[BaseAgent] = None,
        query_agent: Optional[BaseAgent] = None,
        default_agent: Optional[BaseAgent] = None,
    ):
        """
        Initialize router with agents.

        Args:
            booking_agent: Agent for booking intents
            query_agent: Agent for query intents
            default_agent: Default agent for unclassified requests
        """
        self._booking_agent = booking_agent
        self._query_agent = query_agent
        self._default_agent = default_agent

    def classify_intent(self, text: str) -> Tuple[str, float]:
        """
        Classify user intent from input text.

        Args:
            text: User input text

        Returns:
            Tuple of (intent_type, confidence_score)
        """
        text_lower = text.lower()

        booking_score = 0.0
        for keyword in BOOKING_KEYWORDS:
            if keyword in text_lower:
                booking_score += 1.0

        query_score = 0.0
        for keyword in QUERY_KEYWORDS:
            if keyword in text_lower:
                query_score += 1.0

        if booking_score > 0 and booking_score >= query_score:
            logger.info(f"🎯 Intent classified as BOOKING (score: {booking_score})")
            return ("booking", min(booking_score / len(BOOKING_KEYWORDS), 1.0))

        if query_score > 0:
            logger.info(f"🎯 Intent classified as QUERY (score: {query_score})")
            return ("query", min(query_score / len(QUERY_KEYWORDS), 1.0))

        logger.info("🎯 Intent classified as DEFAULT (no keywords matched)")
        return ("default", 0.5)

    def route(self, text: str) -> BaseAgent:
        """
        Route request to appropriate agent.

        Args:
            text: User input text

        Returns:
            Selected agent instance
        """
        intent, confidence = self.classify_intent(text)

        if intent == "booking" and self._booking_agent is not None:
            logger.info(f"🧭 Routing to BookingAgent (confidence: {confidence:.2f})")
            return self._booking_agent

        if intent == "query" and self._query_agent is not None:
            logger.info(f"🧭 Routing to QueryAgent (confidence: {confidence:.2f})")
            return self._query_agent

        if self._default_agent is not None:
            logger.info(f"🧭 Routing to DefaultAgent (confidence: {confidence:.2f})")
            return self._default_agent

        if self._booking_agent is not None:
            logger.info("🧭 No matching agent found, defaulting to BookingAgent")
            return self._booking_agent

        if self._query_agent is not None:
            logger.info("🧭 No matching agent found, defaulting to QueryAgent")
            return self._query_agent

        raise ValueError("No agents configured for routing")

    def set_agents(
        self,
        booking_agent: Optional[BaseAgent] = None,
        query_agent: Optional[BaseAgent] = None,
        default_agent: Optional[BaseAgent] = None,
    ) -> None:
        """
        Update agents at runtime.

        Args:
            booking_agent: Agent for booking intents
            query_agent: Agent for query intents
            default_agent: Default agent for unclassified requests
        """
        if booking_agent is not None:
            self._booking_agent = booking_agent
        if query_agent is not None:
            self._query_agent = query_agent
        if default_agent is not None:
            self._default_agent = default_agent
