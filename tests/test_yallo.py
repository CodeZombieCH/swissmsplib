import unittest
import os
import logging

from swissmsplib.factory import create_client
from swissmsplib.profiles import read_profile
from swissmsplib.sunrise import (
    NextStep,
    SunriseClient,
    create_legacy_sunrise_client,
)

PROVIDER_NAME = "yallo"
PROFILE_NAME = "yallo"


class TestYalloClientLogin(unittest.TestCase):
    @unittest.skip("login requires human interaction")
    def test_login(self):
        os.environ["PROFILE_FILE"] = "./.data/profiles.toml"
        profile = read_profile(PROFILE_NAME)

        client: SunriseClient = create_client(PROVIDER_NAME)  # type: ignore

        context = client.login_send_username(profile.username)
        if context.next_step == NextStep.PASSWORD:
            context = client.login_send_password(context, profile.password)

        if context.next_step != NextStep.CODE:
            raise Exception()

        code = "2fa code here"
        client.login_send_code(context, code)

        refresh_token = client.get_refresh_token()
        self.assertIsNotNone(refresh_token)


class TestYalloClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.__client = cls.__get_client()

    @classmethod
    def tearDownClass(cls):
        pass

    @staticmethod
    def __get_client():
        os.environ["PROFILE_FILE"] = "./.data/profiles.toml"
        profile = read_profile(PROFILE_NAME)

        if not profile.refresh_token:
            raise ValueError("Missing refresh token in profile")

        client: SunriseClient = create_client(PROVIDER_NAME)  # type: ignore
        client.login_with_refresh_token(profile.refresh_token)
        return client

    def test_get_account(self):
        client = self.__client

        account = client.get_account()
        self.assertGreater(account.id, 0)

    def test_get_subscriptions(self):
        client = self.__client

        subscriptions = client.get_subscriptions()

        self.assertGreater(subscriptions[0].id, 0)


class TestLegacyYalloClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.__client = cls.__get_client()

    @classmethod
    def tearDownClass(cls):
        pass

    @staticmethod
    def __get_client():
        os.environ["PROFILE_FILE"] = "./.data/profiles.toml"
        profile = read_profile(PROFILE_NAME)

        if not profile.refresh_token:
            raise ValueError("Missing refresh token in profile")

        client: SunriseClient = create_client(PROVIDER_NAME)  # type: ignore
        client.login_with_refresh_token(profile.refresh_token)

        return create_legacy_sunrise_client(client, PROVIDER_NAME)

    def test_get_account_details(self):
        client = self.__client

        account = client.get_account_details()
        self.assertIsNotNone(account.id)

    def test_get_balance(self):
        client = self.__client

        account = client.get_account_details()

        balance = client.get_balance(account.subscriptions[0].id)
        self.assertIsNone(balance)

    def test_get_rate_plan_status(self):
        client = self.__client

        account = client.get_account_details()

        client.get_rate_plan_status(account.subscriptions[0].id)

    def test_get_current_country(self):
        client = self.__client

        account = client.get_account_details()

        client.get_current_country(account.subscriptions[0].id)

    def test_get_orders(self):
        client = self.__client

        client.get_orders()

    def test_get_bills(self):
        client = self.__client

        bills = client.get_bills()
        self.assertGreater(len(bills), 0)

        first_bill = bills[0]
        self.assertIsNotNone(first_bill.id)

    def test_download_invoice_pdf(self):
        client = self.__client

        bills = client.get_bills()
        self.assertEqual(len(bills), 14)

        pdfBytes = client.download_invoice_pdf(bills[0].invoice_number)
        self.assertGreater(len(pdfBytes), 5)

        # See https://en.wikipedia.org/wiki/List_of_file_signatures
        magicBytes = b"\x25\x50\x44\x46\x2d"  # "%PDF-"
        self.assertEqual(pdfBytes[0:5], magicBytes)


if __name__ == "__main__":
    logging.basicConfig()
    unittest.main()
