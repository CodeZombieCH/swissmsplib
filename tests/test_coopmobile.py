import unittest
import os

from swissmsplib.cookies import _load_cookies, _save_cookies
from swissmsplib.factory import create_client
from swissmsplib.profiles import read_profile
from swissmsplib.swisscom_service import SwisscomServiceProviderClient

PROVIDER_NAME = "coopmobile"
PROFILE_NAME = "coopmobile"


class TestCoopMobileClient(unittest.TestCase):
    client: SwisscomServiceProviderClient

    @classmethod
    def setUpClass(cls):
        cls.client = cls._create_client()

        # Try to login from cookies file
        if cls._login_from_cookies(cls.client):
            print("Logged in from cookies file")
            return

        # Log in with username password
        cls._login(cls.client)

    @classmethod
    def tearDownClass(cls):
        _save_cookies(cls.client.session)

    @staticmethod
    def _create_client() -> SwisscomServiceProviderClient:
        return create_client(PROVIDER_NAME)  # type: ignore

    @staticmethod
    def _login(client: SwisscomServiceProviderClient):
        os.environ["PROFILE_FILE"] = "./.data/profiles.toml"
        profile = read_profile(PROFILE_NAME)

        client.login(profile.username, profile.password)

    @staticmethod
    def _login_from_cookies(client: SwisscomServiceProviderClient) -> bool:
        if not _load_cookies(client.session, PROFILE_NAME):
            return False

        try:
            return client.is_logged_in()
        except:
            return False

    @unittest.skip("Manual test")
    def test_login(self):
        client = self._create_client()
        self._login(client)

        self.assertTrue(client.is_logged_in())

    def test_get_profile(self):
        account_number = self.client.get_profile()

        self.assertIsNotNone(account_number)
        assert account_number is not None

        self.assertGreater(account_number, 0)

    def test_get_subscriptions(self):
        subscriptions = self.client.get_subscriptions()
        self.assertGreater(len(subscriptions), 0)
