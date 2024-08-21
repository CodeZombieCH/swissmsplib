from bs4 import BeautifulSoup
import requests

from swissmsplib.useragent import get_default_user_agent 


class SwisscomClient:
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
            "utf8": "✓",
            "authenticity_token": token,
            "user[id]": username,
            "user[password]": password,
            "user[reseller]": 33,
            "button": "",
        }
        response = self.session.post(url, data=body_payload)
        response.raise_for_status()

    def logout(self):
        url = f"{self.service_url}/eCare/de/users/sign_out?user_type=prepaid"
        response = self.session.get(url)
        response.raise_for_status()

    def get_subscriptions(self):
        url = f"{self.service_url}/eCare/prepaid/de"
        response = self.session.get(url)
        response.raise_for_status()

        page = BeautifulSoup(response.text, "html.parser")
        products_element = page.select(".product")

        subscriptions = []
        for product_element in products_element:
            phone_number_element = product_element.select_one(
                ".product__item__phone-number"
            )
            subscriptions.append(Subscription(phone_number_element.text.strip()))

        return subscriptions


class Subscription:
    def __init__(self, number):
        self.number = number
