import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from http.cookiejar import MozillaCookieJar

import requests

from swissmsplib.common import ParserException, get_default_user_agent


class NextStep(Enum):
    PASSWORD = 1
    CODE = 2


class LoginContext:
    def __init__(self, username, next_step: NextStep) -> None:
        self.username = username
        self.next_step = next_step

    def set_next_step(self, next_step: NextStep):
        self.next_step = next_step


class SwisscomNetworkProviderClient:
    """
    Client for the Swisscom network provider
    """

    COOKIE_FILE_PATH = ".data/swisscom.cookies.txt"

    def __init__(self, service_url, get_user_agent=get_default_user_agent):
        if not service_url:
            raise ValueError("service_url cannot be empty")
        self.service_url = service_url

        # https://www.swisscom.ch/myswisscom

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": get_user_agent()})

    def initialize(self):
        self.get_profile()

    def _load_cookies(self):
        self.cookies = MozillaCookieJar(filename=self.COOKIE_FILE_PATH)
        self.session.cookies = self.cookies  # type: ignore

        if os.path.exists(self.COOKIE_FILE_PATH):
            self.cookies.load(filename=self.COOKIE_FILE_PATH, ignore_discard=True)
            return True
        else:
            return False

    def _save_cookies(self):
        if self.cookies:
            self.cookies.save(filename=self.COOKIE_FILE_PATH, ignore_discard=True)

    def login_send_username(self, username: str) -> LoginContext:
        if not username:
            raise ValueError("username cannot be empty")

        # Initial request to get cookies and login request ID
        # https://www.swisscom.ch/myswisscom/home
        url = f"{self.service_url}/home"
        response = self.session.get(url)
        response.raise_for_status()

        # We expect to get redirected to the following page:
        # https://login.scl.swisscom.ch/login?loginRequest=
        if not "/login?" in response.url:
            raise RuntimeError("Expected redirection to `/login` page")

        # Send username
        url = "https://login.scl.swisscom.ch/submit-username"
        body_payload = {
            "identifier": username,
            "dummyPasswordField": "",
        }
        response = self.session.post(url, data=body_payload)
        response.raise_for_status()

        return LoginContext(username=username, next_step=NextStep.PASSWORD)

    def login_send_password(self, context: LoginContext, password):
        if not password:
            raise ValueError("password cannot be empty")

        # Send username + password
        url = "https://login.scl.swisscom.ch/submit-password"
        body_payload = {
            "username": context.username,
            "password": password,
        }
        response = self.session.post(url, data=body_payload)
        response.raise_for_status()

        # https://login.scl.swisscom.ch/show-sms-view
        if response.url.endswith("/show-sms-view"):
            # 2FA flow with SMS required
            return LoginContext(username=context.username, next_step=NextStep.CODE)

        if response.url.endswith("show-two-fa-info"):
            # 2FA configuration required
            raise RuntimeError("The Swisscom website requires the setup of 2FA")

        # passkey-enrollment/hint
        if "/passkey-enrollment/hint" in response.url:
            raise RuntimeError("The Swisscom website wants you to setup passkey")

        raise RuntimeError("Unknown state")

    def login_send_code(self, context: LoginContext, code: str) -> None:
        if not code:
            raise ValueError("code cannot be empty")

        # 2FA code
        # https://login.scl.swisscom.ch/verify-sms-code
        url = "https://login.scl.swisscom.ch/verify-sms-code"
        body_payload = {"code": code}
        response = self.session.post(url, data=body_payload)
        response.raise_for_status()

        # We expect to be redirected to the home page
        # https://www.swisscom.ch/myswisscom/home
        if not "/home" in response.url:
            raise RuntimeError("Expected redirection to `/home` page")

    def login_using_cookie(self, value):

        #
        self.session.cookies.set(
            name="metis.session", value=value, domain=".login.scl.swisscom.ch", path="/"
        )

        # Initial request to get cookies and login request ID
        # https://www.swisscom.ch/myswisscom/home
        url = f"{self.service_url}/home"
        response = self.session.get(url)
        response.raise_for_status()

        new_session = self.session.cookies.get(
            name="metis.session", domain=".login.scl.swisscom.ch", path="/"
        )
        print(new_session)

    def login_from_cookie_file(self):
        self._load_cookies()

    def check_logged_in(self):
        self.get_profile()

    def get_profile(self):
        # https://www.swisscom.ch/oce/gp/v1/user/v2/profile
        url = "https://www.swisscom.ch/oce/gp/v1/user/v2/profile"
        response = self.session.get(url, headers=self._get_api_headers())
        response.raise_for_status()

        data = response.json()
        scn = data.get("userInventoryScn")
        if not len(scn):
            raise ParserException()
        self.scn = scn

    def get_products(self):
        if not self.scn:
            raise RuntimeError(
                "Invalid state: client initialization not complete (scn missing)"
            )

        # https://www.swisscom.ch/oce/fda/assets/products/v3?scn=&withPrice=true
        url = f"https://www.swisscom.ch/oce/fda/assets/products/v3?scn={self.scn}&withPrice=true"
        response = self.session.get(url, headers=self._get_api_headers())
        response.raise_for_status()

        data = response.json()
        products = data.get("mobilePrepaids")

        p: list[MobilePrepaidProduct] = []
        for product in products:
            p.append(MobilePrepaidProduct.from_dict(product))

        return p

    def get_prepaid_balance(self, subscription_id: str):
        if not self.scn:
            raise RuntimeError(
                "Invalid state: client initialization not complete (scn missing)"
            )

        if not subscription_id:
            raise ValueError("Missing subscription ID")

        url = f"https://www.swisscom.ch/oce/soe/basip/v2/customers/{self.scn}/subscriptions/{subscription_id}/prepaidBalance?language=en"
        response = self.session.get(url, headers=self._get_api_headers())
        response.raise_for_status()

        data = response.json()
        return MobilePrepaidBalance.from_dict(data)

    def _get_api_headers(self):
        # https://www.swisscom.ch/oce/gp
        return {
            "X-OCE-CLIENT": "care-next",
            "X-OCE-CLIENT-VERSION": "agent-1.0.0-9999-12-31-23-59-59",
        }


@dataclass
class MobilePrepaidProduct:
    subscription_id: str
    type: str
    abo_name: str
    status: str

    @staticmethod
    def from_dict(obj):
        subscription_id = obj.get("subscriptionId")
        type = obj.get("type")
        abo_name = obj.get("aboName")
        status = obj.get("status")

        if not subscription_id:
            raise ValueError("Missing subscription ID")

        return MobilePrepaidProduct(
            subscription_id=subscription_id, type=type, abo_name=abo_name, status=status
        )


@dataclass
class MobilePrepaidBalance:
    amount: float
    balance_state: str
    last_activity_timestamp: datetime
    subscriber_status_reason: str

    @staticmethod
    def from_dict(obj):
        amount_raw = obj.get("amount")
        amount = float(amount_raw)

        balance_state = obj.get("balanceState")

        last_activity_timestamp_raw = obj.get("lastActivityTimestamp")
        last_activity_timestamp = datetime.fromisoformat(last_activity_timestamp_raw)

        subscriber_status_reason = obj.get("subscriberStatusReason")

        return MobilePrepaidBalance(
            amount=amount,
            balance_state=balance_state,
            last_activity_timestamp=last_activity_timestamp,
            subscriber_status_reason=subscriber_status_reason,
        )
