import pytest

from app.video_workbench.video_provider import MockVideoProvider
from app.video_workbench.video_provider_registry import get_video_provider
from app.video_workbench.providers.jimeng_provider import JimengProvider


def test_provider_registry_returns_mock():
    assert isinstance(get_video_provider("mock"), MockVideoProvider)


def test_provider_registry_returns_jimeng():
    assert isinstance(get_video_provider("jimeng"), JimengProvider)


def test_provider_registry_rejects_unknown_provider():
    with pytest.raises(ValueError):
        get_video_provider("missing-provider")
