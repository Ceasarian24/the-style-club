from app import create_app

def test_pages_load():
    client = create_app().test_client()
    for url in ["/login", "/register", "/forgot"]:
        assert client.get(url).status_code == 200
    assert client.get("/product/does-not-exist").status_code == 404
