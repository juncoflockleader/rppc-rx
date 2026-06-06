"""Episode planning pipeline (design §11.3-11.4, §17.2 job_4/job_5).

For an episode: build one role context card per participant (using project
source claims + that persona's canon), then a discussion plan over all of them.
Runs as the `episode_planning` job. Step functions stay modular for later
job-splitting.
"""
from __future__ import annotations

import logging
from typing import Callable, List, Optional

from ..providers.embeddings import get_embedding_provider
from ..providers.llm import get_llm_provider
from ..repositories import claims as claims_repo
from ..repositories import episodes as ep_repo
from ..repositories import personas as persona_repo
from . import generator

log = logging.getLogger("planning")

ProgressFn = Optional[Callable[[float], None]]


def _tick(progress: ProgressFn, value: float) -> None:
    if progress:
        progress(value)


def _canon_for(participant: dict, query_vec) -> tuple:
    """Return (concepts, snippets) from the participant's persona canon, if any."""
    hits = persona_repo.search_canon(str(participant["persona_version_id"]), query_vec, k=4)
    concepts: List[str] = []
    snippets: List[str] = []
    for h in hits:
        for c in (h.get("concepts") or []):
            if c not in concepts:
                concepts.append(c)
        snippets.append(h["text"][:300])
    return concepts, snippets


def plan_episode(episode_id: str, progress: ProgressFn = None) -> dict:
    episode = ep_repo.get_episode(episode_id)
    if episode is None:
        raise ValueError(f"episode {episode_id} not found")
    participants = ep_repo.list_personas(episode_id)
    if not participants:
        raise ValueError("episode has no participants")

    project_id = str(episode["project_id"])
    source_claims = claims_repo.list_claims_for_project(project_id)
    goal = (episode.get("settings") or {}).get("goal") or episode.get("title") or ""

    provider = get_llm_provider()
    embedder = get_embedding_provider()
    query_vec = embedder.embed([goal or "podcast discussion"])[0]

    # 1. Role context cards (one per speaker), as a fresh version set.
    card_version = ep_repo.next_card_version(episode_id)
    cards = []
    n = len(participants)
    for i, p in enumerate(participants):
        concepts, snippets = _canon_for(p, query_vec)
        card = generator.build_role_context(
            provider, goal, p, source_claims, concepts, snippets)
        ep_repo.insert_card(episode_id, str(p["persona_version_id"]),
                            p["speaker_label"], card_version, card)
        cards.append(card)
        _tick(progress, 0.1 + 0.6 * (i + 1) / n)

    # 2. Discussion plan over all participants + cards.
    plan = generator.build_discussion_plan(provider, episode, participants,
                                           source_claims, cards)
    plan_row = ep_repo.create_plan(episode_id, plan)
    _tick(progress, 0.95)

    ep_repo.set_episode_status(episode_id, "planned")
    return {
        "episode_id": episode_id,
        "cards": len(cards),
        "plan_version": plan_row["version"],
        "beats": len(plan.get("beats", [])),
    }
