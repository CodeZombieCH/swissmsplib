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

PROVIDER_NAME = "lebara"
PROFILE_NAME = "lebara"


class TestLebaraClientLogin(unittest.TestCase):
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


class TestLebaraClient(unittest.TestCase):
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

    def test_get_bootloader(self):
        client = self.__client

        foo = client.get_bootloader()


class TestLegacyLebaraClient(unittest.TestCase):
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
        self.assertIsNotNone(balance)
        self.assertGreaterEqual(balance, 0)  # type: ignore


if __name__ == "__main__":
    logging.basicConfig()
    unittest.main()
