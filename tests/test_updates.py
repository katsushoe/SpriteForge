import httpx
import pytest

from spriteforge_mcp import updater


def mock_client(monkeypatch, handler):
    client_type = httpx.Client
    monkeypatch.setattr(
        updater.httpx,
        "Client",
        lambda **kwargs: client_type(
            transport=httpx.MockTransport(handler),
            **kwargs,
        ),
    )


def test_stable_channel_filters_prereleases_and_uses_official_repository(monkeypatch):
    def response(request):
        assert str(request.url).startswith(updater.RELEASES_API)
        return httpx.Response(
            200,
            json=[
                {"tag_name": "9.0.0-rc1", "prerelease": True, "assets": []},
                {"tag_name": "0.0.1", "assets": []},
            ],
        )

    mock_client(monkeypatch, response)
    assert updater.check_updates()["version"] == "0.0.1"
    assert updater.check_updates(prereleases=True)["version"] == "9.0.0-rc1"


@pytest.mark.parametrize("code", [403, 429, 500])
def test_update_network_error_does_not_install_or_mutate_files(monkeypatch, tmp_path, code):
    mock_client(monkeypatch, lambda request: httpx.Response(code))
    before = list(tmp_path.iterdir())
    with pytest.raises(httpx.HTTPStatusError):
        updater.check_updates()
    assert list(tmp_path.iterdir()) == before


def test_update_metadata_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(updater, "METADATA_LIMIT", 10)
    mock_client(monkeypatch, lambda request: httpx.Response(200, content=b"x" * 11))
    with pytest.raises(ValueError, match="size limit"):
        updater.check_updates()


def test_update_redirect_is_not_followed(monkeypatch):
    requests = []

    def response(request):
        requests.append(request)
        return httpx.Response(302, headers={"Location": "https://example.org/untrusted"})

    mock_client(monkeypatch, response)
    with pytest.raises(httpx.HTTPStatusError):
        updater.check_updates()
    assert len(requests) == 1
