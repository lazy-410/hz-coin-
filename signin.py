#!/usr/bin/env python3
"""
Auto sign in to NUEDC training website and get daily Hz coins.
Modified for web integration.
"""

from __future__ import annotations
import os
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

    def get_user_info(self) -> Dict:
        """
        获取用户信息和赫兹币余额
        """
        self._log("getting user info and Hz coins")
        r = self.session.get(NUEDC_HOME, timeout=self.timeout)
        
        # 保存页面内容到临时文件，方便调试
        with open("temp_page.html", "w", encoding="utf-8") as f:
            f.write(r.text)
        self._log("page content saved to temp_page.html for debugging")
        
        soup = BeautifulSoup(r.text, "html.parser")
        
        # 查找用户信息和赫兹币余额
        user_info = {
            "username": "",
            "hz_coins": 0
        }
        
        # 尝试从页面中提取用户名
        # 尝试多种可能的选择器
        username_selectors = [
            ".user-info .name",
            ".username",
            ".user-name",
            "#username",
            ".user span"
        ]
        
        for selector in username_selectors:
            username_elem = soup.select_one(selector)
            if username_elem:
                user_info["username"] = username_elem.text.strip()
                self._log(f"found username using selector '{selector}': {user_info['username']}")
                break
        
        # 尝试从页面中提取赫兹币余额
        # 方法1: 直接查找包含赫兹币的文本
        hz_texts = soup.find_all(text=lambda text: text and "赫兹币" in text)
        self._log(f"found {len(hz_texts)} elements containing '赫兹币'")
        
        for hz_text in hz_texts:
            # 查找包含此文本的元素
            hz_container = hz_text.parent
            # 查找容器内所有可能包含数字的元素
            for elem in hz_container.find_all(['span', 'div', 'p', 'b', 'strong']):
                text = elem.text.strip()
                # 提取数字
                import re
                numbers = re.findall(r'\d+', text)
                if numbers:
                    try:
                        hz_coins = int(numbers[0])
                        user_info["hz_coins"] = hz_coins
                        self._log(f"found Hz coins: {hz_coins} in element: {elem}")
                        return user_info
                    except Exception as e:
                        self._log(f"error parsing Hz coins: {e}")
        
        # 方法2: 尝试常见的赫兹币选择器
        hz_selectors = [
            ".hz-coin .num",
            ".hz-num",
            ".coin-num",
            "#hz-coin",
            ".user-info .coin"
        ]
        
        for selector in hz_selectors:
            hz_elem = soup.select_one(selector)
            if hz_elem:
                try:
                    text = hz_elem.text.strip()
                    import re
                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        hz_coins = int(numbers[0])
                        user_info["hz_coins"] = hz_coins
                        self._log(f"found Hz coins using selector '{selector}': {hz_coins}")
                        return user_info
                except Exception as e:
                    self._log(f"error with selector '{selector}': {e}")
        
        # 方法3: 全局搜索数字，尝试找到可能的赫兹币余额
        all_text = soup.get_text()
        import re
        all_numbers = re.findall(r'\d+', all_text)
        # 查找较大的数字，可能是赫兹币余额
        large_numbers = [int(num) for num in all_numbers if int(num) > 0]
        if large_numbers:
            # 取最大的几个数字作为候选
            large_numbers.sort(reverse=True)
            # 假设赫兹币余额是较大的数字之一
            for num in large_numbers[:5]:  # 检查前5个最大的数字
                user_info["hz_coins"] = num
                self._log(f"guessing Hz coins as: {num}")
                break
        
        self._log(f"final user info: {user_info}")
        return user_info

    def sign(self) -> Tuple[SignResult, Dict]:
        result = self._request_sign()
        if not result.need_login:
            user_info = self.get_user_info()
            return result, user_info

        self._log("not logged in, running TI SSO login")
        self.login_via_ti()
        result = self._request_sign()
        user_info = self.get_user_info()
        return result, user_info


def run_signin(username: str, password: str, verbose: bool = False) -> Dict:
    """
    运行签到并返回结果
    """
    try:
        signer = NuedcHzSigner(
            username=username,
            password=password,
            verbose=verbose
        )
        result, user_info = signer.sign()
        
        return {
            "success": result.ok,
            "status": result.status,
            "info": result.info,
            "sign_count": result.sign_count,
            "user_info": user_info,
            "message": f"签到{'成功' if result.status == 1 else '失败' if result.status != 0 else '已完成'}: {result.info}"
        }
    except BindingRequiredError as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"需要绑定账号: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"签到失败: {str(e)}"
        }
