import pytest
from scrape.api import scrape


def test_valid_url():
    response = scrape("https://example.com")
    assert response["error_code"] == "SUCCESS"
    assert response["output"] is not None


def test_invalid_url():
    response = scrape("invalid_url")
    assert response["error_code"] == "INVALID_URL"
    assert "Invalid URL" in response["error"]


def test_timeout_error():
    response = scrape("https://httpstat.us/200?sleep=11000")
    assert response["error_code"] == "TIMEOUT_ERROR"