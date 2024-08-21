from swissmsplib.salt import SaltClient
from swissmsplib.swisscom import SwisscomClient


def create_client(provider):
    if provider == "salt":
        return SaltClient("https://my.salt.ch/", "myaccount-ui-service")
    elif provider == "gomo":
        return SaltClient("https://my-gomo.salt.ch/", "myaccount-gomo-ui-service")
    elif provider == "mbudget":
        return SwisscomClient("https://selfcare.m-budget.migros.ch")
    elif provider == "coopmobile":
        return SwisscomClient("https://myaccount.coopmobile.ch")
    else:
        raise Exception(f"provider {provider} is not supported")
