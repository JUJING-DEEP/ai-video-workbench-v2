from .fixtures import (
    response_data,
    response_error,
)


def test_submit_job_contract_creates_submitted_job(provider_api_harness):
    provider_api_harness.save_settings()
    project_id = provider_api_harness.create_project_with_keyframe()

    response = provider_api_harness.submit(project_id)

    assert response.status_code == 200
    job = response_data(response)["job"]
    assert job["provider"] == "jimeng"
    assert job["status"] == "submitted"
    assert job["submit_id"] == "contract-submit-001"
    assert provider_api_harness.provider_client.calls[0][0] == "submit"
    assert provider_api_harness.provider_client.calls[0][3] == (
        "Camera slowly pushes in for provider contract test."
    )


def test_poll_job_contract_keeps_processing_state(provider_api_harness):
    provider_api_harness.provider_client.statuses = ["processing"]
    provider_api_harness.save_settings()
    project_id = provider_api_harness.create_project_with_keyframe()
    job = response_data(provider_api_harness.submit(project_id))["job"]

    response = provider_api_harness.poll(job["id"])

    assert response.status_code == 200
    polled_job = response_data(response)["job"]
    assert polled_job["status"] == "processing"
    assert polled_job["output_path"] == ""


def test_retrieve_and_bind_contract_creates_remote_asset_and_updates_shot(provider_api_harness):
    provider_api_harness.save_settings()
    project_id = provider_api_harness.create_project_with_keyframe()
    submitted = response_data(provider_api_harness.submit(project_id))["job"]

    response = provider_api_harness.poll(submitted["id"])

    assert response.status_code == 200
    completed = response_data(response)["job"]
    assert completed["status"] == "completed"
    assert completed["result_url"] == "https://jimeng.example/results/contract-job.mp4"
    assert completed["output_path"] == completed["result_url"]
    assert not any(call[0] == "download" for call in provider_api_harness.provider_client.calls)

    assets = provider_api_harness.list_assets(project_id)
    shots = provider_api_harness.list_shots(project_id)
    assert assets[0]["asset_type"] == "video"
    assert assets[0]["source"] == "jimeng"
    assert assets[0]["path"] == completed["result_url"]
    assert shots[0]["video_path"] == completed["output_path"]


def test_timeout_contract_marks_job_timeout_without_binding(provider_api_harness):
    provider_api_harness.provider_client.poll_error = "timeout"
    provider_api_harness.save_settings()
    project_id = provider_api_harness.create_project_with_keyframe()
    submitted = response_data(provider_api_harness.submit(project_id))["job"]

    response = provider_api_harness.poll(submitted["id"])

    assert response.status_code == 504
    error = response_error(response)
    assert error["code"] == "provider_timeout"
    job = response_data(provider_api_harness.get_job(submitted["id"]))["job"]
    assert job["status"] == "timeout"
    assert job["output_path"] == ""
    assert provider_api_harness.list_shots(project_id)[0]["video_path"] == ""


def test_provider_error_contract_marks_job_failed_without_binding(provider_api_harness):
    provider_api_harness.provider_client.poll_error = "provider"
    provider_api_harness.save_settings()
    project_id = provider_api_harness.create_project_with_keyframe()
    submitted = response_data(provider_api_harness.submit(project_id))["job"]

    response = provider_api_harness.poll(submitted["id"])

    assert response.status_code == 502
    job = response_data(provider_api_harness.get_job(submitted["id"]))["job"]
    assert job["status"] == "failed"
    assert "provider" in job["error_message"].lower()
    assert provider_api_harness.list_shots(project_id)[0]["video_path"] == ""


def test_invalid_credentials_contract_rejects_submit(provider_api_harness):
    provider_api_harness.save_settings(access_key="", secret_key="")
    project_id = provider_api_harness.create_project_with_keyframe()

    response = provider_api_harness.submit(project_id)

    assert response.status_code == 400
    assert "credentials" in response_error(response)["message"].lower()


def test_malformed_payload_contract_rejects_missing_keyframe(provider_api_harness):
    provider_api_harness.save_settings()
    project_id = provider_api_harness.client.post(
        "/api/video-workbench/projects",
        json={"title": "Malformed Provider Payload"},
    )["project"]["id"]
    provider_api_harness.client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={
            "text": (
                "第 1 张图片 ▏时间：0:00 — 0:02 ▏模式：B（全新构图）\n"
                "台词：你好 / Hello\n"
                "--- 提示词 ---\n"
                "Scene: Missing keyframe"
            )
        },
    )

    response = provider_api_harness.submit(project_id)

    assert response.status_code == 400
    assert "keyframe" in response_error(response)["message"].lower()


def test_retry_contract_rejects_terminal_poll_without_resubmission(provider_api_harness):
    provider_api_harness.save_settings()
    project_id = provider_api_harness.create_project_with_keyframe()
    submitted = response_data(provider_api_harness.submit(project_id))["job"]
    first_poll = provider_api_harness.poll(submitted["id"])

    response = provider_api_harness.poll(submitted["id"])

    assert first_poll.status_code == 200
    assert response.status_code == 409
    assert "terminal" in response_error(response)["message"].lower()
    submit_calls = [call for call in provider_api_harness.provider_client.calls if call[0] == "submit"]
    assert len(submit_calls) == 1


def test_cancellation_contract_has_no_implicit_cancel_side_effect(provider_api_harness):
    provider_api_harness.provider_client.statuses = ["processing"]
    provider_api_harness.save_settings()
    project_id = provider_api_harness.create_project_with_keyframe()
    submitted = response_data(provider_api_harness.submit(project_id))["job"]

    response = provider_api_harness.poll(submitted["id"])

    assert response.status_code == 200
    job = response_data(response)["job"]
    assert job["status"] == "processing"
    assert job["output_path"] == ""
    assert provider_api_harness.list_shots(project_id)[0]["video_path"] == ""


def test_invalid_response_contract_marks_job_failed(provider_api_harness):
    provider_api_harness.provider_client.statuses = ["invalid"]
    provider_api_harness.save_settings()
    project_id = provider_api_harness.create_project_with_keyframe()
    submitted = response_data(provider_api_harness.submit(project_id))["job"]

    response = provider_api_harness.poll(submitted["id"])

    assert response.status_code == 502
    assert "unknown provider state" in response_error(response)["message"].lower()
    job = response_data(provider_api_harness.get_job(submitted["id"]))["job"]
    assert job["status"] == "failed"
    assert job["output_path"] == ""
    assert provider_api_harness.list_shots(project_id)[0]["video_path"] == ""
