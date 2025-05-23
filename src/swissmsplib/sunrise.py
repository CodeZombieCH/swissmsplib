from enum import Enum
import requests
import jwt
from datetime import datetime, timezone, timedelta

from swissmsplib.common import get_default_user_agent


class NextStep(Enum):
    PASSWORD = 1
    CODE = 2


class LoginContext:
    def __init__(
        self, username, next_step: NextStep, secret: str | None = None
    ) -> None:
        self.username = username
        self.next_step = next_step

    def set_next_step(self, next_step: NextStep):
        self.next_step = next_step

    def set_secret(self, secret):
        self.secret = secret


class Subscriptions:
    def __init__(
        self,
        id: int,
        identifier,
        subscription_owner_id,
        product_code,
        subscription_status,
    ) -> None:
        self.id = id
        self.identifier = identifier
        self.subscription_owner_id = subscription_owner_id
        self.product_code = product_code
        self.subscriptionStatus = subscription_status


class Account:
    def __init__(self, id: int) -> None:
        self.id = id


class SunriseClient:
    access_token: str | None = None

    def __init__(
        self, service_url, service_name, get_user_agent=get_default_user_agent
    ):
        if not service_url:
            raise ValueError("service_url cannot be empty")
        self.service_url = service_url

        if not service_name:
            raise ValueError("service_name cannot be empty")
        self.service_name = service_name

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": get_user_agent()})

    def login_send_username(self, username: str) -> LoginContext:
        if not username:
            raise ValueError("username cannot be empty")

        # Initial request to get cookies
        # Expected to return a 401 and a cookie
        url = self.service_url + "/identity/selfcare/refresh-token"
        response = self.session.post(url)

        url = self.service_url + "/identity/selfcare/login"
        headers = {
            "Accept-Language": "en-US,en;q=0.5",
            "Accept": "application/json, text/plain, */*",
        }
        request_payload = {
            "method": "phone",
            "brand": self.service_name,
            "value": username,
            "language": "en",
        }
        response = self.session.post(url, headers=headers, json=request_payload)

        # Handle case where password is set, and therefore required
        if response.status_code == 400:
            response_payload = response.json()
            if response_payload["error"] == "ERR_PASSWORD_REQUIRED":
                return LoginContext(username=username, next_step=NextStep.PASSWORD)
            else:
                raise Exception(f"unknown error {response_payload['error']}")

        response.raise_for_status()

        secret = self.__extract_secret(response)
        return LoginContext(username=username, next_step=NextStep.CODE, secret=secret)

    def login_send_password(self, context: LoginContext, password):
        url = self.service_url + "/identity/selfcare/login"
        headers = {
            "Accept-Language": "en-US,en;q=0.5",
            "Accept": "application/json, text/plain, */*",
        }
        request_payload = {
            "method": "phone",
            "brand": self.service_name,
            "language": "en",
            "value": context.username,  # phone number
            "password": password,
        }
        response = self.session.post(url, headers=headers, json=request_payload)
        response.raise_for_status()

        secret = self.__extract_secret(response)
        context.set_secret(secret)
        context.set_next_step(NextStep.CODE)
        return context

    def login_send_code(self, context: LoginContext, code: str) -> None:
        # Code received via SMS

        url = self.service_url + "/identity/selfcare/validate"
        headers = {
            "Accept-Language": "en-US,en;q=0.5",
            "Accept": "application/json, text/plain, */*",
        }
        request_payload = {
            "secret": context.secret,
            "code": code,
        }
        response = self.session.post(url, headers=headers, json=request_payload)
        response.raise_for_status()

        response_payload = response.json()

        access_token = response_payload["accessToken"]

        self.__set_access_token(access_token)

    def login_with_refresh_token(self, refresh_token: str):
        """
        Login with a refresh token, which is valid for a month
        """
        self.session.cookies.set("selfcare", refresh_token)

    def get_subscriptions(self):
        self.check_access_token()

        url = self.service_url + "/selfcare/subscriptions"
        headers = {
            "Accept-Language": "en-US,en;q=0.5",
            "Accept": "application/json, text/plain, */*",
        }

        response = self.session.get(url, headers=headers)
        response.raise_for_status()

        response_body = response.json()

        subscriptions: list[Subscriptions] = []
        for s in response_body:
            subscriptions.append(
                Subscriptions(
                    id=int(s["id"]),
                    identifier=s["identifier"],
                    subscription_owner_id=s["subscriptionOwnerId"],
                    product_code=s["productCode"],
                    subscription_status=s["subscriptionStatus"],
                )
            )

        return subscriptions

    def get_account(self):
        self.check_access_token()

        url = self.service_url + "/selfcare/account"
        headers = {
            "Accept-Language": "en-US,en;q=0.5",
            "Accept": "application/json, text/plain, */*",
        }

        response = self.session.get(url, headers=headers)
        response.raise_for_status()

        response_body = response.json()
        return Account(int(response_body["accountId"]))

    def get_bootloader(self):
        # https://ms.lebara.ch/rest/service/bootloader?rfe_id=<unused-id>
        url = self.service_url + "/rest/service/bootloader"
        headers = {
            "Accept-Language": "en-US,en;q=0.5",
            "Accept": "application/json, text/plain, */*",
        }

        response = self.session.post(url, headers=headers)
        response.raise_for_status()

        response_payload = response.json()
        print(response_payload)

    def __set_access_token(self, access_token: str):
        if not access_token:
            raise Exception("Failed to retrieve access token")

        self.access_token = access_token
        self.session.headers.update({"Authorization": "Bearer " + access_token})

        with open(f"{self.service_name}.access-token.txt", "w") as f:
            f.write(access_token)

    def __refresh_access_token(self):
        """
        Refreshes the access token using the refresh token stored in the cookies
        """

        # This request expects a refresh token to be set via cookies
        # The response will set the refresh token again, theoretically updating the refresh token
        # The response payload contains the access token
        url = self.service_url + "/identity/selfcare/refresh-token"
        headers = {
            "Accept-Language": "en-US,en;q=0.5",
            "Accept": "application/json, text/plain, */*",
        }

        response = self.session.post(url, headers=headers)
        response.raise_for_status()

        response_payload = response.json()

        access_token = response_payload["accessToken"]

        self.__set_access_token(access_token)

    def check_access_token(self):
        if not self.access_token:
            self.__refresh_access_token()
            return

        decoded = jwt.decode(
            jwt=self.access_token,
            options={"verify_signature": False},
        )

        expiry_timestamp = decoded["exp"]
        expiry = datetime.fromtimestamp(
            int(expiry_timestamp),
            timezone.utc,
        )
        if datetime.now(timezone.utc) > expiry + timedelta(seconds=5):
            # token expired
            self.__refresh_access_token()

    def __extract_secret(self, response):
        response_payload = response.json()

        secret = response_payload["secret"]
        if secret == "":
            raise ValueError("secret cannot be empty")

        password_found = response_payload["passwordfound"]

        return secret


class LegacySunriseClientHeaders:
    SC_AUTHORIZATION = "SCAuthorization"
    RFE_AUTHORIZATION = "RFEAuthorization"


class LegacySubscription:
    def __init__(self, id: str) -> None:
        self.id = id


class LegacyAccount:
    def __init__(self, id: str, subscriptions: list[LegacySubscription]) -> None:
        self.id = id
        self.subscriptions = subscriptions


class LegacySunriseClient:
    def __init__(
        self,
        client: SunriseClient,
        service_url="https://rest.lebara.ch",
    ) -> None:
        self.service_url = service_url
        self.client = client

    def get_account_details(self):
        self.client.check_access_token()

        # https://rest.lebara.ch/rest/service/getAccountDetails?rfe_id=<unused-id>
        url = self.service_url + "/rest/service/getAccountDetails"
        headers = {
            "Accept-Language": "en-US,en;q=0.5",
            "Accept": "application/json, text/plain, */*",
        }
        self.__set_legacy_headers(headers)

        response = self.client.session.post(url, headers=headers)
        response.raise_for_status()

        self.__get_legacy_headers(response.headers)  # type: ignore

        response_payload = response.json()

        subscriptions: list[LegacySubscription] = []
        for s in response_payload["data"]["subscriptions"]:
            subscriptions.append(LegacySubscription(s["subscriptionId"]))

        return LegacyAccount(response_payload["data"]["accountId"], subscriptions)

    def get_balance(self, subscription_id: str):
        self.client.check_access_token()

        # https://rest.lebara.ch/rest/service/getSubscriptionDetails?rfe_id=<unused-id>
        url = self.service_url + "/rest/service/getSubscriptionDetails"
        headers = {
            "Accept-Language": "en-US,en;q=0.5",
            "Accept": "application/json, text/plain, */*",
        }
        self.__set_legacy_headers(headers)
        request_payload = {"subscriptionId": subscription_id}

        response = self.client.session.post(url, headers=headers, json=request_payload)
        response.raise_for_status()

        self.__get_legacy_headers(response.headers)  # type: ignore

        response_body = response.json()
        balance = float(response_body["data"]["balance"])
        return balance

    def __get_legacy_headers(self, headers: dict[str, str]):
        rfe_authorization = headers[LegacySunriseClientHeaders.RFE_AUTHORIZATION]
        if rfe_authorization:
            self.rfe_authorization = rfe_authorization

    def __set_legacy_headers(self, headers: dict[str, str]):
        if self.client.access_token:
            headers[LegacySunriseClientHeaders.SC_AUTHORIZATION] = (
                self.client.access_token
            )
        if hasattr(self, "rfe_authorization") and self.rfe_authorization:
            headers[LegacySunriseClientHeaders.RFE_AUTHORIZATION] = (
                self.rfe_authorization
            )
