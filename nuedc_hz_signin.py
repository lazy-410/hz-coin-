#!/usr/bin/env python3
"""
Auto sign in to NUEDC training website and get daily Hz coins.

Login path:
NUEDC -> myTI SSO -> login.ti.com -> NUEDC

Usage:
  python scripts/nuedc_hz_signin.py
  python scripts/nuedc_hz_signin.py --username "you@example.com" --password "your_password"
  python scripts/nuedc_hz_signin.py --cookie-file .nuedc_cookies.txt --verbose

Credentials can also be provided with env vars:
  NUEDC_TI_USERNAME
  NUEDC_TI_PASSWORD
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from dataclasses import dataclass
from http.cookiejar import MozillaCookieJar
from typing import Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests import Session
from requests.cookies import create_cookie


NUEDC_HOME = "https://www.nuedc-training.com.cn/"
NUEDC_SIGN_URL = "https://www.nuedc-training.com.cn/index/mall/sign"
MYTI_LOGIN_PAGE = "https://www.nuedc-training.com.cn/index/login/myti_login"


@dataclass
class SignResult:
    status: int
    info: str
    sign_count: Optional[int]
    raw: Dict

    @property
    def ok(self) -> bool:
        return self.status in (0, 1)

    @property
    def need_login(self) -> bool:
        return self.status == 2


class BindingRequiredError(RuntimeError):
    """Raised when myTI login succeeds but NUEDC account binding is required."""


class NuedcHzSigner:
    def __init__(
        self,
        username: str,
        password: str,
        timeout: int = 30,
        verbose: bool = False,
        cookie_file: Optional[str] = None,
    ) -> None:
        self.username = username.strip()
        self.password = password
        self.timeout = timeout
        self.verbose = verbose
        self.cookie_file = cookie_file

        self.session = Session()
        self.session.trust_env = False
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/121.0.0.0 Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;"
                    "q=0.9,image/avif,image/webp,*/*;q=0.8"
                ),
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
        )

    def _log(self, message: str) -> None:
        if self.verbose:
            print(f"[debug] {message}")

    def load_cookies(self) -> None:
        if not self.cookie_file:
            return
        if not os.path.exists(self.cookie_file):
            self._log(f"cookie file not found: {self.cookie_file}")
            return

        jar = MozillaCookieJar(self.cookie_file)
        jar.load(ignore_discard=True, ignore_expires=True)
        for c in jar:
            self.session.cookies.set_cookie(
                create_cookie(
                    name=c.name,
                    value=c.value,
                    domain=c.domain,
                    path=c.path,
                    secure=c.secure,
                    expires=c.expires,
                )
            )
        self._log(f"cookies loaded: {len(jar)}")

    def save_cookies(self) -> None:
        if not self.cookie_file:
            return
        jar = MozillaCookieJar(self.cookie_file)
        for c in self.session.cookies:
            jar.set_cookie(c)
        jar.save(ignore_discard=True, ignore_expires=True)
        self._log(f"cookies saved: {len(jar)}")

    @staticmethod
    def _extract_form(soup: BeautifulSoup, selector: Optional[str] = None) -> Tuple[str, Dict[str, str]]:
        form = soup.select_one(selector) if selector else soup.find("form")
        if not form:
            raise RuntimeError("Failed to find form in page.")

        action = form.get("action")
        if not action:
            raise RuntimeError("Form action is missing.")

        payload: Dict[str, str] = {}
        for inp in form.find_all("input"):
            name = inp.get("name")
            if not name:
                continue
            payload[name] = inp.get("value", "")
        return action, payload

    def _request_sign(self) -> SignResult:
        self._log("requesting sign endpoint")
        r = self.session.get(
            NUEDC_SIGN_URL,
            timeout=self.timeout,
            headers={
                "Referer": NUEDC_HOME,
                "X-Requested-With": "XMLHttpRequest",
            },
        )

        try:
            data = r.json()
        except Exception:
            if "index/login" in r.url:
                return SignResult(status=2, info="need login", sign_count=None, raw={})
            raise RuntimeError(
                f"Unexpected sign response (status={r.status_code}, url={r.url})."
            ) from None

        status = int(data.get("status", -1))
        info = str(data.get("info", ""))
        sign_count = None
        if isinstance(data.get("data"), dict):
            count = data["data"].get("sign_count")
            if count is not None:
                try:
                    sign_count = int(count)
                except Exception:
                    sign_count = None

        return SignResult(status=status, info=info, sign_count=sign_count, raw=data)

    def login_via_ti(self) -> None:
        self._log("opening myTI login entry page")
        r = self.session.get(
            MYTI_LOGIN_PAGE,
            params={"referer": NUEDC_HOME},
            timeout=self.timeout,
        )
        soup = BeautifulSoup(r.text, "html.parser")
        myti_btn = soup.select_one("a.loginMyti-btn1")
        if not myti_btn or not myti_btn.get("href"):
            raise RuntimeError("myTI login entry not found.")
        sso_go = urljoin(r.url, myti_btn["href"])
        self._log(f"sso_go: {sso_go}")

        self._log("opening nuedc sso redirect page")
        r = self.session.get(sso_go, timeout=self.timeout)
        soup = BeautifulSoup(r.text, "html.parser")
        auto_link = soup.select_one("a#href")
        if not auto_link or not auto_link.get("href"):
            raise RuntimeError("SSO redirect link not found.")
        sp_login = urljoin(r.url, auto_link["href"])
        self._log(f"sp login: {sp_login}")

        self._log("posting SAMLRequest to TI")
        r = self.session.get(sp_login, timeout=self.timeout)
        soup = BeautifulSoup(r.text, "html.parser")
        action, payload = self._extract_form(soup)
        ti_sso_url = urljoin(r.url, action)
        r = self.session.post(
            ti_sso_url,
            data=payload,
            timeout=self.timeout,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://sp.nuedc-training.com.cn",
                "Referer": sp_login,
            },
        )

        self._log("submitting TI username/password")
        if "SAMLResponse" not in r.text:
            soup = BeautifulSoup(r.text, "html.parser")
            action, login_payload = self._extract_form(
                soup, "form.paged-form-container, form[method='post']"
            )
            login_url = urljoin(r.url, action)
            login_payload["pf.username"] = self.username.lower()
            login_payload["pf.pass"] = self.password
            login_payload["loginbutton"] = "login"

            r = self.session.post(
                login_url,
                data=login_payload,
                timeout=self.timeout,
                allow_redirects=True,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "https://login.ti.com",
                    "Referer": r.url,
                },
            )

        self._log("consuming TI SAMLResponse to NUEDC")
        if "SAMLResponse" not in r.text:
            raise RuntimeError(
                "TI login did not return SAMLResponse. "
                "Check username/password, or verify if extra challenge is required."
            )

        soup = BeautifulSoup(r.text, "html.parser")
        saml_form = soup.find("form")
        if not saml_form or not saml_form.get("action"):
            raise RuntimeError("SAMLResponse form is missing.")

        saml_action = urljoin(r.url, saml_form["action"])
        saml_payload: Dict[str, str] = {}
        for inp in saml_form.find_all("input"):
            name = inp.get("name")
            if not name:
                continue
            saml_payload[name] = inp.get("value", "")

        r = self.session.post(
            saml_action,
            data=saml_payload,
            timeout=self.timeout,
            allow_redirects=True,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://login.ti.com",
                "Referer": r.url,
            },
        )

        host = urlparse(r.url).netloc
        if "nuedc-training.com.cn" not in host:
            raise RuntimeError(f"SSO callback not completed, current url: {r.url}")
        if urlparse(r.url).path.startswith("/index/saml/binding"):
            raise BindingRequiredError(
                "myTI account is not bound to a NUEDC account yet. "
                "Open https://www.nuedc-training.com.cn/index/saml/binding in a browser, "
                "complete binding (bind existing account or register a new one), then rerun this script."
            )

    def sign(self) -> SignResult:
        result = self._request_sign()
        if not result.need_login:
            return result

        self._log("not logged in, running TI SSO login")
        self.login_via_ti()
        result = self._request_sign()
        return result


def build_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Auto login (myTI SSO) and daily sign-in for NUEDC Hz coin."
    )
    parser.add_argument("--username", default=os.getenv("NUEDC_TI_USERNAME", "").strip())
    parser.add_argument("--password", default=os.getenv("NUEDC_TI_PASSWORD", ""))
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds.")
    parser.add_argument(
        "--cookie-file",
        default=".nuedc_cookies.txt",
        help="Optional cookie file path (Mozilla format).",
    )
    parser.add_argument("--no-cookie", action="store_true", help="Disable cookie persistence.")
    parser.add_argument("--verbose", action="store_true", help="Show debug logs.")
    return parser.parse_args()


def main() -> int:
    args = build_args()

    username = args.username or input("TI username/email: ").strip()
    password = args.password or getpass.getpass("TI password: ")
    if not username or not password:
        print("ERROR: username/password is required.", file=sys.stderr)
        return 2

    cookie_file = None if args.no_cookie else args.cookie_file
    signer = NuedcHzSigner(
        username=username,
        password=password,
        timeout=args.timeout,
        verbose=args.verbose,
        cookie_file=cookie_file,
    )

    try:
        signer.load_cookies()
        result = signer.sign()
        signer.save_cookies()
    except BindingRequiredError as exc:
        print(f"ACTION REQUIRED: {exc}", file=sys.stderr)
        return 3
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if result.status == 1:
        msg = "Sign-in succeeded"
    elif result.status == 0:
        msg = "Already signed in today"
    elif result.status == 2:
        msg = "Still not logged in"
    else:
        msg = "Unknown status"

    if result.sign_count is not None:
        print(f"{msg}; streak={result.sign_count}; info={result.info}")
    else:
        print(f"{msg}; info={result.info}")

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
