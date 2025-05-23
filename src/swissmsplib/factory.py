from swissmsplib.salt import SaltClient
from swissmsplib.sunrise import SunriseClient
from swissmsplib.swisscom import SwisscomClient


def create_client(provider) -> SaltClient | SwisscomClient | SunriseClient:
    if provider == "salt":
        return SaltClient("https://my.salt.ch/", "myaccount-ui-service")
    elif provider == "gomo":
        return SaltClient("https://my-gomo.salt.ch/", "myaccount-gomo-ui-service")
    elif provider == "mbudget":
        return SwisscomClient("https://selfcare.m-budget.migros.ch")
    elif provider == "coopmobile":
        return SwisscomClient("https://myaccount.coopmobile.ch")
    elif provider == "yallo":
        return SunriseClient("https://ms.yallo.ch", "yallo")
    elif provider == "lebara":
        return SunriseClient("https://ms.lebara.ch", "lebara")

    else:
        raise Exception(f"provider {provider} is not supported")
