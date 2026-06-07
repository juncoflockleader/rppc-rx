import pytest

from app.workers import handlers


def test_all_pipeline_job_types_registered():
    expected = {
        "source_ingestion", "claim_extraction", "embedding", "episode_planning",
        "script_generation", "script_qa", "voice_direction", "audio_render",
        "audio_mix", "export_package",
    }
    assert expected <= set(handlers.registered_job_types())


def test_unknown_job_type_raises():
    with pytest.raises(KeyError):
        handlers.get_handler("no_such_job")


def test_later_milestone_handlers_are_stubs():
    # voice_direction lands in M7; still a stub.
    fn = handlers.get_handler("voice_direction")
    with pytest.raises(NotImplementedError):
        fn("job", {})
