"""Episode + planning routes (design §12.4)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import get_current_user, require_project_owner
from ..repositories import episodes as ep_repo
from ..repositories import personas as persona_repo
from ..repositories import projects as projects_repo
from ..schemas import CreateEpisodeRequest, EpisodeOut
from ..services.persona_service import require_persona_usable
from ..services.queue import get_queue

router = APIRouter(tags=["episodes"])


def _owned_episode(episode_id: str, user: dict) -> dict:
    ep = ep_repo.get_episode(episode_id)
    if ep is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Episode not found.")
    project = projects_repo.get_project(str(ep["project_id"]))
    if project is None or str(project["user_id"]) != str(user["id"]):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your episode.")
    return ep


@router.post("/api/projects/{project_id}/episodes", response_model=EpisodeOut,
             status_code=status.HTTP_201_CREATED)
def create_episode(body: CreateEpisodeRequest,
                   project: dict = Depends(require_project_owner)):
    labels = [p.speaker_label for p in body.personas]
    if len(set(labels)) != len(labels):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Speaker labels must be unique.")
    if sum(1 for p in body.personas if p.role == "host") != 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Exactly one participant must have role 'host'.")

    # Resolve + safety-check every persona before creating anything (§19.1).
    resolved = []
    for p in body.personas:
        ver = persona_repo.get_version(p.persona_id, p.version)
        if ver is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Persona {p.persona_id} {p.version} not found. Seed personas first.")
        asset = persona_repo.get_asset(p.persona_id) or {"id": p.persona_id}
        require_persona_usable(asset, ver)
        resolved.append((p, str(ver["id"])))

    ep = ep_repo.create_episode(
        project_id=str(project["id"]), title=body.title,
        target_language=body.target_language,
        target_duration_seconds=body.target_duration_seconds, format_=body.format,
        audience=body.audience, style=body.style,
        settings={"goal": body.goal} if body.goal else {},
    )
    parts = []
    for i, (p, version_id) in enumerate(resolved):
        ep_repo.add_persona(str(ep["id"]), version_id, p.role, p.speaker_label, i)
        parts.append({"persona_id": p.persona_id, "version": p.version,
                      "role": p.role, "speaker_label": p.speaker_label})
    return EpisodeOut.from_row(ep, parts)


@router.get("/api/episodes/{episode_id}", response_model=EpisodeOut)
def get_episode(episode_id: str, user: dict = Depends(get_current_user)):
    ep = _owned_episode(episode_id, user)
    parts = [{"persona_id": r["persona_id"], "version": r["version"],
              "role": r["role"], "speaker_label": r["speaker_label"]}
             for r in ep_repo.list_personas(episode_id)]
    return EpisodeOut.from_row(ep, parts)


@router.post("/api/episodes/{episode_id}/discussion-plan",
             status_code=status.HTTP_202_ACCEPTED)
def generate_plan(episode_id: str, user: dict = Depends(get_current_user)):
    """Enqueue role-context + discussion-plan generation. Re-running regenerates
    a new plan version (design §9 regenerate outline)."""
    ep = _owned_episode(episode_id, user)
    ep_repo.set_episode_status(episode_id, "generating")
    job = get_queue().enqueue(
        "episode_planning", {"episode_id": episode_id},
        project_id=str(ep["project_id"]), episode_id=episode_id,
    )
    return {"job_id": str(job["id"]), "status": "queued"}


@router.get("/api/episodes/{episode_id}/discussion-plan")
def get_plan(episode_id: str, user: dict = Depends(get_current_user)):
    _owned_episode(episode_id, user)
    plan = ep_repo.get_latest_plan(episode_id)
    if plan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "No discussion plan yet. Generate one first.")
    return {"episode_id": episode_id, "version": plan["version"],
            "status": plan["status"], "plan": plan["plan_json"]}


@router.get("/api/episodes/{episode_id}/role-context")
def get_role_context(episode_id: str, user: dict = Depends(get_current_user)):
    _owned_episode(episode_id, user)
    return {
        "episode_id": episode_id,
        "cards": [
            {"speaker_label": c["speaker_label"], "version": c["version"],
             "card": c["card_json"]}
            for c in ep_repo.latest_cards(episode_id)
        ],
    }
