import os
import unittest
from datetime import datetime

from swissmsplib.factory import create_client
from swissmsplib.profiles import read_profile
from swissmsplib.swisscom_network import NextStep, SwisscomNetworkProviderClient


class TestSwisscomOriginalClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # cls.__client = cls.__get_client()
        pass

    @classmethod
    def tearDownClass(cls):
        # cls.__client.logout()
        pass

    @staticmethod
    def _get_client() -> SwisscomNetworkProviderClient:
        os.environ["PROFILE_FILE"] = "./.data/profiles.toml"
        profile = read_profile("swisscom")

        client: SwisscomNetworkProviderClient = create_client("swisscom")  # type: ignore
        client.login_from_cookie_file()
        client.check_logged_in()
        return client

    def test_2fa_login_flow(self):
        os.environ["PROFILE_FILE"] = "./.data/profiles.toml"
        profile = read_profile("swisscom")

        client: SwisscomNetworkProviderClient = create_client("swisscom")  # type: ignore

        client._load_cookies()

        context = client.login_send_username(profile.username)

        # We expect the password step to follow
        if context.next_step == NextStep.PASSWORD:
            context = client.login_send_password(
                context=context, password=profile.password
            )
        else:
            self.fail("Expect the password step to follow")

        # We expect the code step to follow
        if context.next_step == NextStep.CODE:
            code = ""
            # DEBUG: break here
            context = client.login_send_code(context=context, code=code)
        else:
            self.fail("Expect the code step to follow")

        client._save_cookies()

        client.get_profile()

        client._save_cookies()

        subscriptions = client.get_products()
        self.assertGreater(len(subscriptions), 0)

    def test_login_using_cookie(self):
        client: SwisscomNetworkProviderClient = create_client("swisscom")  # type: ignore
        client.login_using_cookie("59e4665e-5785-40b3-a16e-f9c993104027")

        client.get_profile()

        subscriptions = client.get_products()
        self.assertGreater(len(subscriptions), 0)

    def test_get_products(self):
        client = self._get_client()

        subscriptions = client.get_products()
        self.assertGreater(len(subscriptions), 0)

    def test_get_prepaid_balance(self):
        client = self._get_client()

        subscriptions = client.get_products()
        self.assertGreater(len(subscriptions), 0)

        balance = client.get_prepaid_balance(subscriptions[0].subscription_id)
        self.assertGreater(balance.amount, 0)
        self.assertEqual(balance.balance_state, "SUFFICIENT")
        self.assertGreater(balance.last_activity_timestamp, datetime(2000, 1, 1))
        self.assertEqual(balance.subscriber_status_reason, "ACTIVE")
