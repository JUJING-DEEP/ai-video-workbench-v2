from pathlib import Path


def test_readme_contains_five_minute_onboarding_flow():
    readme = Path(__file__).resolve().parents[3] / "README.md"
    text = readme.read_text(encoding="utf-8").lower()

    required_phrases = [
        "git clone",
        "python -m pip install -r requirements.txt",
        "npm ci",
        "uvicorn app.main:app --reload --port 8000",
        "npm run dev",
        "provider settings",
        "create project",
        "import storyboard",
        "generate keyframe",
        "generate video",
        "export render plan",
    ]

    missing = [phrase for phrase in required_phrases if phrase not in text]
    assert missing == []
