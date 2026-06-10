import httpx

from app.services.emailjs_service import EmailJSService


def configure_emailjs_settings(monkeypatch) -> None:
    monkeypatch.setattr("app.services.emailjs_service.settings.EMAILJS_SERVICE_ID", "service")
    monkeypatch.setattr("app.services.emailjs_service.settings.EMAILJS_TEMPLATE_ID", "template")
    monkeypatch.setattr("app.services.emailjs_service.settings.EMAILJS_PUBLIC_KEY", "public")
    monkeypatch.setattr("app.services.emailjs_service.settings.EMAILJS_PRIVATE_KEY", "private")
    monkeypatch.setattr("app.services.emailjs_service.settings.EMAILJS_API_URL", "https://api.emailjs.test/send")


def test_emailjs_service_success(monkeypatch) -> None:
    configure_emailjs_settings(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        payload = request.read().decode()
        assert "private" in payload
        return httpx.Response(200, text="OK")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    service = EmailJSService(client=client)

    result = service.send_email("sales@example.com", {"to_email": "sales@example.com"})

    assert result["success"] is True
    assert result["status_code"] == 200


def test_emailjs_service_retries_timeout(monkeypatch) -> None:
    configure_emailjs_settings(monkeypatch)
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise httpx.TimeoutException("timeout")
        return httpx.Response(200, text="OK")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    service = EmailJSService(client=client)

    result = service.send_email("sales@example.com", {"to_email": "sales@example.com"})

    assert result["success"] is True
    assert attempts["count"] == 2


def test_emailjs_service_retries_http_500(monkeypatch) -> None:
    configure_emailjs_settings(monkeypatch)
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(500, text="temporary")
        return httpx.Response(200, text="OK")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    service = EmailJSService(client=client)

    result = service.send_email("sales@example.com", {"to_email": "sales@example.com"})

    assert result["success"] is True
    assert attempts["count"] == 2


def test_emailjs_service_does_not_retry_http_400(monkeypatch) -> None:
    configure_emailjs_settings(monkeypatch)
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        return httpx.Response(400, text="bad request")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    service = EmailJSService(client=client)

    result = service.send_email("sales@example.com", {"to_email": "sales@example.com"})

    assert result["success"] is False
    assert result["status_code"] == 400
    assert attempts["count"] == 1


def test_emailjs_service_retries_403_without_private_key(monkeypatch) -> None:
    configure_emailjs_settings(monkeypatch)
    access_token_seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = request.read().decode()
        access_token_seen.append("accessToken" in payload)
        if len(access_token_seen) == 1:
            return httpx.Response(403, text="private key rejected")
        return httpx.Response(200, text="OK")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    service = EmailJSService(client=client)

    result = service.send_email("sales@example.com", {"to_email": "sales@example.com"})

    assert result["success"] is True
    assert access_token_seen == [True, False]
