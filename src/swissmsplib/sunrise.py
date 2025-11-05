import base64
import random
import string
import requests
import jwt
from enum import Enum
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

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
        self.secret = secret

    def set_next_step(self, next_step: NextStep):
        self.next_step = next_step

    def set_secret(self, secret):
        self.secret = secret


@dataclass
class Subscriptions:
    id: int
    identifier: str
    subscription_owner_id: str
    product_code: str
    subscription_status: str


class Account:
    def __init__(self, id: int) -> None:
        self.id = id


class SunriseClient:
    """
    A client for the sunrise REST API.
    Sunrise calls it the microServiceEndpoint
    ```
    microServiceEndpoint = 'https://prod.ms.api.' + brand + '.ch/'
    ```
    """

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

        if "@" not in username:
            raise ValueError("username is expected to represent an email address")

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
            "method": "email",
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
            "method": "email",
            "brand": self.service_name,
            "language": "en",
            "value": context.username,
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
        # Check if token is not expired
        # Raises error if expired
        claims = jwt.decode(
            refresh_token,
            algorithms=["RS256"],
            options={"verify_signature": False, "verify_exp": "verify_signature"},
        )

        if claims["type"] == "refresh_token":
            raise Exception("invalid token type")

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

    def get_refresh_token(self):
        return self.session.cookies.get("selfcare")

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


@dataclass
class LegacySubscription:
    id: str


@dataclass
class LegacyAccount:
    id: str
    subscriptions: list[LegacySubscription]


@dataclass
class LegacyBill:
    id: str
    invoice_number: str
    start_date: datetime
    end_date: datetime
    status: str
    amount: float


class LegacySunriseClient:
    """
    A client for the legacy sunrise REST API.
    Sunrise calls it the yolBackendEndpoint
    ```
    yolBackendEndpoint = 'https://rest.' + brand + '.ch/rest/service/'
    ```
    """

    def __init__(self, client: SunriseClient, service_url: str) -> None:
        if not service_url:
            raise ValueError("service_url cannot be empty")
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

    def get_balance(self, subscription_id: str) -> float | None:
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
        if response_body["data"]["balance"]:
            # Balance present, most likely a pre-paid subscription
            return float(response_body["data"]["balance"])
        else:
            # Balance missing, most likely a post-paid subscription
            return None

    def get_rate_plan_status(self, subscription_id: str):
        self.client.check_access_token()

        # https://rest.lebara.ch/rest/service/getRatePlanStatus?rfe_id=
        url = self.service_url + "/rest/service/getRatePlanStatus"
        headers = {
            "Accept-Language": "en-US,en;q=0.5",
            "Accept": "application/json, text/plain, */*",
        }
        self.__set_legacy_headers(headers)
        request_payload = {"subscriptionId": subscription_id}

        response = self.client.session.post(url, headers=headers, json=request_payload)
        response.raise_for_status()

        self.__get_legacy_headers(response.headers)  # type: ignore

        response_payload = response.json()

        # TODO: do something with the response
        return response_payload

    def get_current_country(self, subscription_id: str):
        self.client.check_access_token()

        # https://rest.yallo.ch/rest/service/getCurrentCountry?rfe_id=
        url = self.service_url + "/rest/service/getCurrentCountry"
        headers = {
            "Accept-Language": "en-US,en;q=0.5",
            "Accept": "application/json, text/plain, */*",
        }
        self.__set_legacy_headers(headers)
        request_payload = {"subscriptionId": subscription_id}

        response = self.client.session.post(url, headers=headers, json=request_payload)
        response.raise_for_status()

        self.__get_legacy_headers(response.headers)  # type: ignore

        response_payload = response.json()

        # TODO: do something with the response
        return response_payload

    def get_orders(self):
        self.client.check_access_token()

        # https://rest.yallo.ch/rest/service/getOrders?rfe_id=
        url = self.service_url + "/rest/service/getOrders"
        headers = {
            "Accept-Language": "en-US,en;q=0.5",
            "Accept": "application/json, text/plain, */*",
        }
        self.__set_legacy_headers(headers)

        response = self.client.session.post(url, headers=headers)
        response.raise_for_status()

        self.__get_legacy_headers(response.headers)  # type: ignore

        response_payload = response.json()
        # TODO: do something with the response
        return response_payload

    def get_bills(self):
        self.client.check_access_token()

        # ****************************************
        # WARNING
        # ****************************************
        # This is a special request!
        # It requires an empty JSON object `{}` as request payload,
        # otherwise it will fail

        # https://rest.yallo.ch/rest/service/getBills?rfe_id=
        url = self.service_url + "/rest/service/getBills"
        headers = {
            "Accept-Language": "en-US,en;q=0.5",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
        }
        self.__set_legacy_headers(headers)

        response = self.client.session.post(url, headers=headers, data="{}")
        response.raise_for_status()

        self.__get_legacy_headers(response.headers)  # type: ignore

        response_payload = response.json()

        bills_response = response_payload["data"]["bills"]
        bills: list[LegacyBill] = []
        for bill_response in bills_response:
            # For some reasons, open invoices appear twice,
            # where one of the invoices has an empty invoice number

            # Looks like an int, but API represents it as string
            id = bill_response["id"]

            # Looks like an int, but API represents it as string
            invoice_number = bill_response["invoiceNumber"]

            if not bill_response["startDate"]:
                continue
            start_date = datetime.fromisoformat(bill_response["startDate"])

            if not bill_response["endDate"]:
                continue
            end_date = datetime.fromisoformat(bill_response["endDate"])

            status = bill_response["status"]
            amount = float(bill_response["amount"])

            bills.append(
                LegacyBill(
                    id=id,
                    invoice_number=invoice_number,
                    start_date=start_date,
                    end_date=end_date,
                    status=status,
                    amount=amount,
                )
            )
        bills.sort(key=lambda x: x.start_date)
        return bills

    def download_invoice_pdf(self, invoice_number: str):
        self.client.check_access_token()

        # https://rest.yallo.ch/rest/service/getInvoicePdf?rfe_id=
        url = self.service_url + "/rest/service/getInvoicePdf"
        headers = {
            "Accept-Language": "en-US,en;q=0.5",
            "Accept": "application/json, text/plain, */*",
        }
        self.__set_legacy_headers(headers)
        request_payload = {"invoiceNumber": invoice_number}

        response = self.client.session.post(url, headers=headers, json=request_payload)
        response.raise_for_status()

        self.__get_legacy_headers(response.headers)  # type: ignore

        # Why send binary payload, when you can warp it in a JSON and bse64 encode it 😕
        response_payload = response.json()

        base64_pdf_payload = response_payload["data"]["pdfData"]
        return base64.b64decode(base64_pdf_payload)

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

    def __get_random_id(self, n):
        return "".join(
            random.choice(
                string.ascii_lowercase + string.ascii_uppercase + string.digits
            )
            for _ in range(n)
        )

    def __get_random_rfe_id(self):
        # P = window.yolSessionId + "_" + randomString(10).toLowerCase(),
        return self.__get_random_id(10) + "_" + self.__get_random_id(10).lower()


def create_legacy_sunrise_client(
    client: SunriseClient, provider
) -> LegacySunriseClient:

    if provider == "yallo":
        return LegacySunriseClient(client, "https://rest.yallo.ch")
    elif provider == "lebara":
        return LegacySunriseClient(client, "https://rest.lebara.ch")
    else:
        raise Exception(f"provider {provider} is not supported")
