async def test_register_and_login(client):
    r = await client.post("/auth/register", json={"email": "a@b.c", "password": "pass1234"})
    assert r.status_code == 201

    r = await client.post("/auth/login", json={"email": "a@b.c", "password": "pass1234"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "a@b.c"


async def test_register_duplicate_email(client):
    await client.post("/auth/register", json={"email": "a@b.c", "password": "pass1234"})
    r = await client.post("/auth/register", json={"email": "a@b.c", "password": "other123"})
    assert r.status_code == 409


async def test_register_short_password(client):
    r = await client.post("/auth/register", json={"email": "a@b.c", "password": "short"})
    assert r.status_code == 422


async def test_login_wrong_password(client):
    await client.post("/auth/register", json={"email": "a@b.c", "password": "pass1234"})
    r = await client.post("/auth/login", json={"email": "a@b.c", "password": "wrong-pass"})
    assert r.status_code == 401


async def test_login_unknown_email_same_error(client):
    r = await client.post("/auth/login", json={"email": "ghost@b.c", "password": "whatever1"})
    assert r.status_code == 401


async def test_me_without_token(client):
    r = await client.get("/auth/me")
    assert r.status_code == 401


async def test_me_with_garbage_token(client):
    r = await client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 401


async def test_register_password_over_72_bytes_ascii(client):
    r = await client.post("/auth/register", json={"email": "a@b.c", "password": "a" * 100})
    assert r.status_code == 422


async def test_register_password_over_72_bytes_multibyte(client):
    r = await client.post("/auth/register", json={"email": "a@b.c", "password": "ы" * 40})
    assert r.status_code == 422


async def test_login_password_over_72_bytes(client):
    r = await client.post("/auth/login", json={"email": "a@b.c", "password": "a" * 100})
    assert r.status_code == 422


async def test_register_normalizes_email_case(client):
    r = await client.post(
        "/auth/register", json={"email": "Alice@Example.COM", "password": "pass1234"}
    )
    assert r.status_code == 201
    assert r.json()["email"] == "alice@example.com"


async def test_login_case_insensitive_email(client):
    await client.post("/auth/register", json={"email": "Alice@Example.COM", "password": "pass1234"})
    r = await client.post(
        "/auth/login", json={"email": "ALICE@example.com", "password": "pass1234"}
    )
    assert r.status_code == 200


async def test_register_duplicate_email_case_insensitive(client):
    await client.post("/auth/register", json={"email": "Alice@Example.COM", "password": "pass1234"})
    r = await client.post(
        "/auth/register", json={"email": "alice@example.com", "password": "other123"}
    )
    assert r.status_code == 409
