"""HTTP client for CLI-to-backend integration.

Provides an async client wrapper for communicating with the
MathAssistant backend server. Used by the CLI to submit questions,
record answers, and retrieve analytics.
"""

from typing import Optional


class MathAssistantBackendClient:
    """Lightweight HTTP client for the MathAssistant backend API."""

    def __init__(
        self,
        base_url: str,
        token: str | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._httpx = None

    @property
    def is_authenticated(self) -> bool:
        return self.token is not None

    def _get_client(self):
        """Lazy-import httpx to avoid dependency when backend is not used."""
        if self._httpx is None:
            import httpx
            self._httpx = httpx
        return self._httpx

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    # ── Auth ──────────────────────────────────────────────

    def login(self, username: str, password: str) -> dict:
        """Login and store the access token. Returns the login response."""
        httpx = self._get_client()
        resp = httpx.post(
            f"{self.base_url}/api/auth/login",
            json={"username": username, "password": password},
        )
        resp.raise_for_status()
        data = resp.json()
        self.token = data["access_token"]
        return data

    def register(self, username: str, email: str, password: str, display_name: str | None = None) -> dict:
        """Register a new account. Returns the user response."""
        httpx = self._get_client()
        resp = httpx.post(
            f"{self.base_url}/api/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password,
                "display_name": display_name,
            },
        )
        resp.raise_for_status()
        return resp.json()

    # ── Questions ─────────────────────────────────────────

    def submit_question(self, content: str, session_id: int | None = None, source: str = "cli") -> dict:
        """Submit a question for tracking and auto-tagging."""
        httpx = self._get_client()
        payload = {"content": content, "source": source}
        if session_id is not None:
            payload["session_id"] = session_id
        resp = httpx.post(
            f"{self.base_url}/api/questions",
            json=payload,
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def get_question(self, question_id: int) -> dict:
        """Get a question with its tags."""
        httpx = self._get_client()
        resp = httpx.get(
            f"{self.base_url}/api/questions/{question_id}",
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def list_questions(
        self,
        page: int = 1,
        per_page: int = 20,
        tag: int | None = None,
        search: str | None = None,
    ) -> dict:
        """List questions for the current user with pagination."""
        httpx = self._get_client()
        params: dict = {"page": page, "per_page": per_page}
        if tag is not None:
            params["tag"] = tag
        if search is not None:
            params["search"] = search
        resp = httpx.get(
            f"{self.base_url}/api/questions/",
            params=params,
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def update_tags(self, question_id: int, tag_ids: list[int]) -> dict:
        """Manually update tags for a question."""
        httpx = self._get_client()
        resp = httpx.put(
            f"{self.base_url}/api/questions/{question_id}/tags",
            json={"tags": [{"knowledge_point_id": tid} for tid in tag_ids]},
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def record_answer(
        self,
        question_id: int,
        is_correct: bool,
        user_answer: str | None = None,
        expected_answer: str | None = None,
        mistake_type: str | None = None,
        time_spent_seconds: int | None = None,
        knowledge_point_id: int | None = None,
    ) -> dict:
        """Record an answer result for a question."""
        httpx = self._get_client()
        payload: dict = {"is_correct": is_correct}
        if user_answer is not None:
            payload["user_answer"] = user_answer
        if expected_answer is not None:
            payload["expected_answer"] = expected_answer
        if mistake_type is not None:
            payload["mistake_type"] = mistake_type
        if time_spent_seconds is not None:
            payload["time_spent_seconds"] = time_spent_seconds
        if knowledge_point_id is not None:
            payload["knowledge_point_id"] = knowledge_point_id
        resp = httpx.post(
            f"{self.base_url}/api/questions/{question_id}/answer",
            json=payload,
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    # ── Analytics ─────────────────────────────────────────

    def get_mastery(self) -> dict:
        """Get mastery scores for all knowledge points."""
        httpx = self._get_client()
        resp = httpx.get(
            f"{self.base_url}/api/analytics/mastery",
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def get_weaknesses(self, limit: int = 5) -> dict:
        """Get the user's top weak areas."""
        httpx = self._get_client()
        resp = httpx.get(
            f"{self.base_url}/api/analytics/weaknesses",
            params={"limit": limit},
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def get_recommendations(self, limit: int = 5) -> dict:
        """Get learning recommendations."""
        httpx = self._get_client()
        resp = httpx.get(
            f"{self.base_url}/api/analytics/recommendations",
            params={"limit": limit},
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def get_mistake_notebook(self, limit: int = 10, **filters) -> dict:
        """Get the user's mistake notebook."""
        httpx = self._get_client()
        params: dict = {"per_page": limit, **filters}
        resp = httpx.get(
            f"{self.base_url}/api/analytics/mistake-notebook",
            params=params,
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def get_summary(self) -> dict:
        """Get overall learning summary."""
        httpx = self._get_client()
        resp = httpx.get(
            f"{self.base_url}/api/analytics/summary",
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    # ── Sessions ──────────────────────────────────────────

    def start_session(self) -> dict:
        """Start a new learning session on the backend."""
        httpx = self._get_client()
        # Sessions are managed via the questions endpoint with session_id
        # For now, we track sessions locally and pass session_id with questions
        return {"session_id": None}

    # ── Knowledge Points ──────────────────────────────────

    def seed_taxonomy(self) -> dict:
        """Seed the default knowledge point taxonomy."""
        httpx = self._get_client()
        resp = httpx.post(
            f"{self.base_url}/api/knowledge-points/seed",
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def get_knowledge_points(self, parent_id: int | None = None, search: str | None = None) -> list[dict]:
        """List knowledge points with optional filters."""
        httpx = self._get_client()
        params = {}
        if parent_id is not None:
            params["parent_id"] = parent_id
        if search is not None:
            params["search"] = search
        resp = httpx.get(
            f"{self.base_url}/api/knowledge-points",
            params=params if params else None,
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()
