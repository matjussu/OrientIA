from unittest.mock import patch, MagicMock
from src.collect.onisep import authenticate, fetch_formations


def test_authenticate_returns_token():
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {"token": "jwt_fake_token"}

    with patch("src.collect.onisep.requests.post", return_value=fake_response) as mock_post:
        token = authenticate("a@b.c", "pw")
        assert token == "jwt_fake_token"
        mock_post.assert_called_once()


def test_fetch_formations_uses_token_and_app_id():
    fake = MagicMock()
    fake.status_code = 200
    fake.json.return_value = {"results": [{"nom": "Master IA"}]}

    with patch("src.collect.onisep.requests.get", return_value=fake) as mock_get:
        data = fetch_formations("tok", "appid", query="intelligence artificielle")
        assert data == [{"nom": "Master IA"}]
        headers = mock_get.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer tok"
        assert headers["Application-ID"] == "appid"
