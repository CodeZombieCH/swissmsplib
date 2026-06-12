import os
import unittest

from swissmsplib.factory import create_client
from swissmsplib.profiles import read_profile
from swissmsplib.salt import SaltClient

PROVIDER_NAME = "gomo"
PROFILE_NAME = "gomo"


class TestGoMoClient(unittest.TestCase):
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

    def test_get_bills(self):
        client = self.__client

        subscriptions = client.get_subscriptions()
        self.assertGreater(len(subscriptions), 0)

        billing_account_id = subscriptions[0].billing_account_id
        self.assertIsNotNone(billing_account_id)
        assert billing_account_id

        bills = client.get_bills(billing_account_id)
        self.assertGreater(len(bills), 0)

    def test_download_bill_pdf(self):
        client = self.__client

        subscriptions = client.get_subscriptions()
        self.assertGreater(len(subscriptions), 0)

        billing_account_id = subscriptions[0].billing_account_id
        self.assertIsNotNone(billing_account_id)
        assert billing_account_id

        bills = client.get_bills(billing_account_id)
        self.assertGreater(len(bills), 0)

        pdfBytes = client.download_bill_pdf(billing_account_id, bills[0].invoice_id)
        self.assertGreater(len(pdfBytes), 5)

        # See https://en.wikipedia.org/wiki/List_of_file_signatures
        magicBytes = b"\x25\x50\x44\x46\x2d"  # "%PDF-"
        self.assertEqual(pdfBytes[0:5], magicBytes)
