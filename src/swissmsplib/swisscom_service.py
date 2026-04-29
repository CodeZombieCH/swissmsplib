import requests
from bs4 import BeautifulSoup

from swissmsplib.common import ParserException, get_default_user_agent


class SwisscomServiceProviderClient:
    """
    Client for service providers based on the Swisscom network provider
    Currently tested with:
    - Migros Mobile (formerly M-Budget Mobile)
    - Coop Mobile
    """

    def __init__(self, service_url, get_user_agent=get_default_user_agent):
        if not service_url:
            raise ValueError("service_url cannot be empty")
        self.service_url = service_url

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": get_user_agent()})

    def login(self, username, password):
        if not username:
            raise ValueError("username cannot be empty")

        if not password:
            raise ValueError("password cannot be empty")

        # Initial request to get CSRF token
        url = f"{self.service_url}/eCare/de/users/sign_in"
        response = self.session.get(url)
        response.raise_for_status()

        page = BeautifulSoup(response.text, "html.parser")
        # <meta name="csrf-token" content="r3I9c3.....eECuWg==" />
        token_element = page.select('meta[name="csrf-token"]')
        token = token_element[0]["content"]

        url = f"{self.service_url}/eCare/de/users/sign_in"
        body_payload = {
            "authenticity_token": token,
            "user[account]": "",
            "user[id]": username,
            "user[password]": password,
        }
        response = self.session.post(url, data=body_payload)
        response.raise_for_status()

        if "sign_in" in response.url:
            raise RuntimeError("Looks like we are still on the sign in page")

    def logout(self):
        url = f"{self.service_url}/eCare/de/users/sign_out?user_type=prepaid"
        response = self.session.get(url)
        response.raise_for_status()

    def is_logged_in(self) -> bool:
        """
        Checks if client is in a logged in session state
        """
        url = f"{self.service_url}/eCare/wireless/de"
        response = self.session.get(url)
        response.raise_for_status()

        return "sign_in" not in response.url

    def get_profile(self):
        url = f"{self.service_url}/eCare/wireless/de"
        response = self.session.get(url)
        response.raise_for_status()

        self._ensure_logged_in(response)

        page = BeautifulSoup(response.text, "html.parser")
        profile_element = page.select_one("#block_my_profile_content")
        if not profile_element:
            raise ParserException("Failed to parse element for profile")

        account_number: int | None = None
        for item in profile_element.select("ul"):
            label_element = item.select_one(".panel__list__label")
            item_element = item.select_one(".panel__list__item")
            if (
                label_element
                and item_element
                and label_element.text.strip() == "Kundennummer"
            ):
                account_number = int(item_element.text.strip())

        return account_number

    def get_subscriptions(self):
        url = f"{self.service_url}/eCare/prepaid/de"
        response = self.session.get(url)
        response.raise_for_status()

        self._ensure_logged_in(response)

        page = BeautifulSoup(response.text, "html.parser")
        products_element = page.select(".product")

        subscriptions = []
        for product_element in products_element:
            phone_number_element = product_element.select_one(
                ".product__item__phone-number"
            )
            if not phone_number_element:
                # raise ParserException("Failed to parse element for phone number")
                # For prepaid subscriptions, there are two product rows, where only the first one is an actual product
                # => skip product if there is no phone number
                continue

            subscriptions.append(Subscription(phone_number_element.text.strip()))

        return subscriptions

    def get_prepaid_balance(self):
        url = f"{self.service_url}/eCare/prepaid/de/my_consumption"
        response = self.session.get(url)
        response.raise_for_status()

        self._ensure_logged_in(response)

        page = BeautifulSoup(response.text, "html.parser")
        balance_element = page.select_one(
            "#credit_balance .panel__consumption__data--value"
        )

        if not balance_element:
            raise ParserException("Failed to parse element for balance")

        return float(balance_element.text)

    def _ensure_logged_in(self, response: requests.Response):
        if "sign_in" in response.url:
            raise RuntimeError("Looks like we are still on the sign in page")


class Subscription:
    def __init__(self, number):
        self.number = number
