"""hub_usage_fetch 단위 테스트. 네트워크·subprocess 는 전부 mock 한다 — 이 테스트는 실제
Keychain·API 를 절대 건드리지 않는다(불변식 A-SEC). U26~U33
(docs/prps/hub-card-interactions-and-usage.md 「테스트 계획」)."""

import http.client
import json
import os
import subprocess
import sys
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "hub", "bin"))

import hub_usage_fetch  # noqa: E402  (sys.path 조정 후 임포트)

FETCH_NOW_MS = 1_786_433_120_000
_CANARY_TOKEN = "canary-token-must-never-leak-into-a-failure-path"  # 테스트 전용 가짜 값


def _keychain_result(returncode: int = 0, stdout: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


def _valid_keychain_stdout(token: str = "test-only-fake-token") -> str:
    return json.dumps({"claudeAiOauth": {"accessToken": token}})


def _http_error(status_code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(hub_usage_fetch.USAGE_API_URL, status_code, "error", {}, None)


def _mock_response(body_text: str) -> mock.MagicMock:
    response = mock.MagicMock()
    response.read.return_value = body_text.encode("utf-8")
    response.__enter__.return_value = response
    return response


class ReadOauthAccessTokenTest(unittest.TestCase):
    """U26~U28 — Keychain 읽기 실패 3경로는 모두 None(사유 구분은 fetch_rate_limit_capture 몫)."""

    def test_u26_security_command_missing_returns_none(self) -> None:
        with mock.patch.object(hub_usage_fetch.subprocess, "run", side_effect=FileNotFoundError()):
            self.assertIsNone(hub_usage_fetch.read_oauth_access_token())

    def test_u27_non_zero_exit_returns_none(self) -> None:
        with mock.patch.object(hub_usage_fetch.subprocess, "run", return_value=_keychain_result(returncode=1)):
            self.assertIsNone(hub_usage_fetch.read_oauth_access_token())

    def test_u28_output_not_json_returns_none(self) -> None:
        with mock.patch.object(hub_usage_fetch.subprocess, "run", return_value=_keychain_result(stdout="not json")):
            self.assertIsNone(hub_usage_fetch.read_oauth_access_token())

    def test_u28_missing_token_field_returns_none(self) -> None:
        stdout = json.dumps({"claudeAiOauth": {"refreshToken": "x"}})
        with mock.patch.object(hub_usage_fetch.subprocess, "run", return_value=_keychain_result(stdout=stdout)):
            self.assertIsNone(hub_usage_fetch.read_oauth_access_token())

    def test_valid_token_is_returned(self) -> None:
        stdout = _valid_keychain_stdout("test-only-fake-token")
        with mock.patch.object(hub_usage_fetch.subprocess, "run", return_value=_keychain_result(stdout=stdout)):
            self.assertEqual(hub_usage_fetch.read_oauth_access_token(), "test-only-fake-token")

    def test_u33_keychain_subprocess_uses_list_args_without_shell(self) -> None:
        """U33 — subprocess.run 이 리스트 인자 + shell 미지정으로 호출된다."""
        stdout = _valid_keychain_stdout()
        with mock.patch.object(hub_usage_fetch.subprocess, "run", return_value=_keychain_result(stdout=stdout)) as mocked_run:
            hub_usage_fetch.read_oauth_access_token()
        call_args, call_kwargs = mocked_run.call_args
        self.assertIsInstance(call_args[0], list)
        self.assertNotIn("shell", call_kwargs)


class FetchRateLimitCaptureTest(unittest.TestCase):
    """U26~U32 — fetch_rate_limit_capture 의 전체 실패/성공 경로(3-튜플 반환, 개정 반영)."""

    def _patch_keychain(self, **kwargs):
        return mock.patch.object(hub_usage_fetch.subprocess, "run", return_value=_keychain_result(**kwargs))

    def _fetch_with_http_outcome(self, urlopen_mock: mock.Mock, token: str = "test-only-fake-token"):
        with self._patch_keychain(stdout=_valid_keychain_stdout(token)), \
             mock.patch.object(hub_usage_fetch.urllib.request, "urlopen", urlopen_mock):
            return hub_usage_fetch.fetch_rate_limit_capture(FETCH_NOW_MS)

    def test_u26_credential_unavailable_when_security_missing(self) -> None:
        with mock.patch.object(hub_usage_fetch.subprocess, "run", side_effect=FileNotFoundError()):
            capture, reason, detail = hub_usage_fetch.fetch_rate_limit_capture(FETCH_NOW_MS)
        self.assertIsNone(capture)
        self.assertEqual(reason, "credential_unavailable")
        self.assertIsNone(detail)

    def test_u27_credential_unavailable_when_non_zero_exit(self) -> None:
        with self._patch_keychain(returncode=1):
            capture, reason, detail = hub_usage_fetch.fetch_rate_limit_capture(FETCH_NOW_MS)
        self.assertIsNone(capture)
        self.assertEqual(reason, "credential_unavailable")

    def test_u28_credential_unparsable_when_output_not_json(self) -> None:
        with self._patch_keychain(stdout="not json"):
            capture, reason, detail = hub_usage_fetch.fetch_rate_limit_capture(FETCH_NOW_MS)
        self.assertIsNone(capture)
        self.assertEqual(reason, "credential_unparsable")

    def test_u28_credential_unparsable_when_token_field_missing(self) -> None:
        with self._patch_keychain(stdout=json.dumps({"claudeAiOauth": {"refreshToken": "x"}})):
            capture, reason, detail = hub_usage_fetch.fetch_rate_limit_capture(FETCH_NOW_MS)
        self.assertEqual(reason, "credential_unparsable")

    def test_u29_http_401_is_unauthorized(self) -> None:
        _capture, reason, _detail = self._fetch_with_http_outcome(mock.Mock(side_effect=_http_error(401)))
        self.assertEqual(reason, "http_unauthorized")

    def test_u29_http_403_is_unauthorized(self) -> None:
        _capture, reason, _detail = self._fetch_with_http_outcome(mock.Mock(side_effect=_http_error(403)))
        self.assertEqual(reason, "http_unauthorized")

    def test_u29_http_429_is_rate_limited(self) -> None:
        _capture, reason, _detail = self._fetch_with_http_outcome(mock.Mock(side_effect=_http_error(429)))
        self.assertEqual(reason, "http_rate_limited")

    def test_u29_http_500_is_http_error(self) -> None:
        _capture, reason, _detail = self._fetch_with_http_outcome(mock.Mock(side_effect=_http_error(500)))
        self.assertEqual(reason, "http_error")

    def test_u30_url_error_is_network_error(self) -> None:
        _capture, reason, _detail = self._fetch_with_http_outcome(
            mock.Mock(side_effect=urllib.error.URLError("timed out"))
        )
        self.assertEqual(reason, "network_error")

    def test_u30_timeout_is_network_error(self) -> None:
        _capture, reason, _detail = self._fetch_with_http_outcome(mock.Mock(side_effect=TimeoutError()))
        self.assertEqual(reason, "network_error")

    def test_unclassified_http_client_exceptions_are_sealed_to_network_error(self) -> None:
        """검수 Major — http.client.HTTPException 계열(OSError 가 아니다)이 urlopen·응답 읽기
        도중 나도 경계를 넘지 않고 network_error 로 접혀야 한다(불변식 A-SEC 경계 봉합)."""
        unclassified_exceptions = (
            http.client.IncompleteRead(partial=b""),
            http.client.BadStatusLine("garbage"),
        )
        for exception in unclassified_exceptions:
            with self.subTest(exception=type(exception).__name__):
                capture, reason, detail = self._fetch_with_http_outcome(mock.Mock(side_effect=exception))
                self.assertIsNone(capture)
                self.assertEqual(reason, "network_error")
                self.assertIsNone(detail)

    def test_u31_200_with_unparseable_body_is_schema_mismatch(self) -> None:
        capture, reason, detail = self._fetch_with_http_outcome(
            mock.Mock(return_value=_mock_response(json.dumps({"unexpected": "shape"})))
        )
        self.assertIsNone(capture)
        self.assertEqual(reason, "schema_mismatch")
        self.assertIsNotNone(detail)
        self.assertIn("/unexpected <str>", detail)

    def test_success_returns_capture_and_no_failure(self) -> None:
        body = json.dumps(
            {
                "five_hour": {"utilization": 23, "resets_at": "2026-08-13T18:00:00+00:00"},
                "seven_day": {"utilization": 41, "resets_at": "2026-08-20T00:00:00+00:00"},
            }
        )
        capture, reason, detail = self._fetch_with_http_outcome(mock.Mock(return_value=_mock_response(body)))
        self.assertIsNotNone(capture)
        self.assertIsNone(reason)
        self.assertIsNone(detail)

    def test_u32_no_failure_path_leaks_the_token_string(self) -> None:
        """불변식 A-SEC — 어떤 실패 경로의 반환값에도 토큰 문자열이 없다."""
        outcomes = []
        with mock.patch.object(hub_usage_fetch.subprocess, "run", side_effect=FileNotFoundError()):
            outcomes.append(hub_usage_fetch.fetch_rate_limit_capture(FETCH_NOW_MS))
        with self._patch_keychain(returncode=1):
            outcomes.append(hub_usage_fetch.fetch_rate_limit_capture(FETCH_NOW_MS))
        with self._patch_keychain(stdout="not json"):
            outcomes.append(hub_usage_fetch.fetch_rate_limit_capture(FETCH_NOW_MS))
        for status_code in (401, 429, 500):
            outcomes.append(
                self._fetch_with_http_outcome(mock.Mock(side_effect=_http_error(status_code)), token=_CANARY_TOKEN)
            )
        outcomes.append(
            self._fetch_with_http_outcome(mock.Mock(side_effect=urllib.error.URLError("x")), token=_CANARY_TOKEN)
        )
        outcomes.append(
            self._fetch_with_http_outcome(
                mock.Mock(return_value=_mock_response(json.dumps({"unexpected": "shape"}))), token=_CANARY_TOKEN
            )
        )
        for outcome in outcomes:
            self.assertNotIn(_CANARY_TOKEN, repr(outcome))


if __name__ == "__main__":
    unittest.main()
