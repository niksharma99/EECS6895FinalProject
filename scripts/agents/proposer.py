"""Proposer wrapper."""

from __future__ import annotations

from scripts.agents.judge import parse_judgment
from scripts.agents.prompts import build_prompt
from scripts.agents.schemas import ProposerResponse


class Proposer:
    def __init__(self, client):
        self.client = client
        self.model_id = client.model_id

    def answer(self, record: dict, text: str | None = None) -> ProposerResponse:
        prompt = build_prompt(record, text)
        raw = self.client.complete(prompt["system"], prompt["user"], record["options"])
        return parse_judgment(raw, record["options"])
