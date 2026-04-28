import unittest
import os

from swissmsplib.factory import create_client
from swissmsplib.profiles import read_profile
from swissmsplib.swisscom_service import SwisscomServiceProviderClient


class TestMBudgetClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.__client = cls.__get_client()

    @classmethod
    def tearDownClass(cls):
        cls.__client.logout()

    @staticmethod
    def __get_client() -> SwisscomServiceProviderClient:
        os.environ["PROFILE_FILE"] = "./.data/profiles.toml"
        profile = read_profile("mbudget")

        client: SwisscomServiceProviderClient = create_client("mbudget")  # type: ignore
        client.login(profile.username, profile.password)
        return client

    def test_get_subscriptions(self):
        client = self.__client

        subscriptions = client.get_subscriptions()
        self.assertGreater(len(subscriptions), 0)

    def test_get_prepaid_balance(self):
        client = self.__client

        balance = client.get_prepaid_balance()
        self.assertGreaterEqual(balance, 0)
