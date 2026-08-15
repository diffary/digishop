from httpx import ASGITransport, AsyncClient

from app.main import create_app


async def test_unknown_path_returns_detail(client):
    r = await client.get("/no-such-path")
    assert r.status_code == 404
    assert "detail" in r.json()


async def test_unhandled_exception_returns_uniform_500():
    app = create_app()

    @app.get("/boom")
    async def boom():
        raise RuntimeError("secret internals")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/boom")

    assert r.status_code == 500
    assert r.json() == {"detail": "Internal server error"}
    assert "secret internals" not in r.text
