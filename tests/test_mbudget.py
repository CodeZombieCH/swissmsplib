import unittest
import os

from swissmsplib.profiles import read_profile
from swissmsplib.swisscom import SwisscomClient


class TestMBudgetClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.__client = cls.__get_client()

    @classmethod
    def tearDownClass(cls):
        cls.__client.logout()

    @staticmethod
    def __get_client() -> SwisscomClient:
        os.environ["PROFILE_FILE"] = "./.data/profiles.toml"
        profile = read_profile("mbudget")

        client = SwisscomClient("https://selfcare.m-budget.migros.ch")
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
