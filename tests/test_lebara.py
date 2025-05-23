import unittest
import os
import logging

from swissmsplib.profiles import read_profile
from swissmsplib.sunrise import SunriseClient, LegacySunriseClient


class TestSunriseClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.__client = cls.__get_client()

    @classmethod
    def tearDownClass(cls):
        pass

    @staticmethod
    def __get_client() -> SunriseClient:
        os.environ["PROFILE_FILE"] = "./.data/profiles.toml"
        profile = read_profile("lebara")

        if not profile.refresh_token:
            raise ValueError("Missing refresh token in profile")

        client = SunriseClient("https://ms.lebara.ch", "lebara")
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


class TestLegacySunriseClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.__client = cls.__get_client()

    @classmethod
    def tearDownClass(cls):
        pass

    @staticmethod
    def __get_client() -> LegacySunriseClient:
        os.environ["PROFILE_FILE"] = "./.data/profiles.toml"
        profile = read_profile("lebara")

        if not profile.refresh_token:
            raise ValueError("Missing refresh token in profile")

        client = SunriseClient("https://ms.lebara.ch", "lebara")
        client.login_with_refresh_token(profile.refresh_token)

        return LegacySunriseClient(client)

    def test_get_account_details(self):
        client = self.__client

        account = client.get_account_details()
        self.assertIsNotNone(account.id)

    def test_get_balance(self):
        client = self.__client

        account = client.get_account_details()

        balance = client.get_balance(account.subscriptions[0].id)
        self.assertGreaterEqual(balance, 0)


if __name__ == "__main__":
    logging.basicConfig()
    unittest.main()
