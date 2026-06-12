import os
import unittest

from swissmsplib.factory import create_client
from swissmsplib.profiles import read_profile
from swissmsplib.salt import SaltClient

PROVIDER_NAME = "salt"
PROFILE_NAME = "salt"


class TestSaltClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.__client = cls.__get_client()

    @classmethod
    def tearDownClass(cls):
        cls.__client.logout()

    @staticmethod
    def __get_client() -> SaltClient:
        os.environ["PROFILE_FILE"] = "./.data/profiles.toml"
        profile = read_profile(PROFILE_NAME)

        client: SaltClient = create_client(PROVIDER_NAME)  # type: ignore
        client.login(profile.username, profile.password)
        return client

    def test_get_subscriptions(self):
        client = self.__client

        subscriptions = client.get_subscriptions()
        self.assertGreater(len(subscriptions), 0)
