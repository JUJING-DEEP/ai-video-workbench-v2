import pytest

from .fixtures import CONTRACT_STATUSES, ContractProviderAdapter


def test_contract_status_fixture_declares_required_statuses():
    assert CONTRACT_STATUSES == {
        "pending",
        "submitted",
        "processing",
        "completed",
        "failed",
        "timeout",
        "cancelled",
    }


def test_contract_interface_runs_submit_poll_download_bind_in_order(contract_provider):
    job = contract_provider.submit({"keyframe_path": "/renders/keyframe.png"})

    processing_job = contract_provider.poll(job)
    completed_job = contract_provider.poll(processing_job)
    video_bytes = contract_provider.download(completed_job)
    bound_job = contract_provider.bind(completed_job, video_bytes)

    assert bound_job.status == "completed"
    assert bound_job.bound is True
    assert bound_job.output_path.endswith(f"{bound_job.id}.mp4")
    assert bound_job.events == ["submit", "poll", "poll", "download", "bind"]


def test_contract_rejects_invalid_credentials():
    provider = ContractProviderAdapter("future-real-jimeng-provider", valid_credentials=False)

    with pytest.raises(PermissionError, match="Invalid provider credentials"):
        provider.submit({"keyframe_path": "/renders/keyframe.png"})


def test_contract_rejects_malformed_payload():
    provider = ContractProviderAdapter("mock-provider", malformed_payload=True)

    with pytest.raises(ValueError, match="Malformed provider payload"):
        provider.submit({"keyframe_path": "/renders/keyframe.png"})


def test_contract_rejects_invalid_provider_response():
    provider = ContractProviderAdapter("future-real-jimeng-provider", invalid_response=True)
    job = provider.submit({"keyframe_path": "/renders/keyframe.png"})

    with pytest.raises(ValueError, match="Invalid provider response"):
        provider.poll(job)


def test_contract_supports_cancellation_before_terminal_state():
    provider = ContractProviderAdapter("future-real-jimeng-provider", states=["processing"])
    job = provider.submit({"keyframe_path": "/renders/keyframe.png"})
    provider.poll(job)

    cancelled = provider.cancel(job)

    assert cancelled.status == "cancelled"
    assert cancelled.bound is False
    assert cancelled.events == ["submit", "poll", "cancel"]


def test_contract_rejects_cancellation_after_completion(contract_provider):
    job = contract_provider.submit({"keyframe_path": "/renders/keyframe.png"})
    contract_provider.poll(job)
    completed = contract_provider.poll(job)

    with pytest.raises(RuntimeError, match="Cannot cancel terminal"):
        contract_provider.cancel(completed)


def test_contract_retry_is_limited_to_failed_or_timed_out_jobs():
    provider = ContractProviderAdapter("future-real-jimeng-provider", states=["provider-error"])
    job = provider.submit({"keyframe_path": "/renders/keyframe.png"})
    failed = provider.poll(job)

    retried = provider.retry(failed)

    assert retried.status == "submitted"
    assert retried.attempts == 2
    assert retried.events == ["submit", "poll", "retry"]

    with pytest.raises(RuntimeError, match="Can only retry"):
        provider.retry(retried)

    retried.status = "failed"
    with pytest.raises(RuntimeError, match="retry budget"):
        provider.retry(retried)
