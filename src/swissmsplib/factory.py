from swissmsplib.salt import SaltClient
from swissmsplib.sunrise import SunriseClient
from swissmsplib.swisscom import SwisscomClient


def create_client(provider) -> SaltClient | SwisscomClient | SunriseClient:
    if provider == "salt":
        return SaltClient(
            login_url="https://login.salt.ch",
            service_url="https://my.salt.ch",
            service_name="myaccount-ui-service",
        )
    elif provider == "gomo":
        return SaltClient(
            login_url="https://login.go-mo.ch",
            service_url="https://my.go-mo.ch",
            service_name="myaccount-gomo-ui-service",
        )
    elif provider == "mbudget":
        return SwisscomClient("https://selfcare.m-budget.migros.ch")
    elif provider == "coopmobile":
        return SwisscomClient("https://myaccount.coopmobile.ch")
    elif provider == "yallo":
        return SunriseClient("https://prod.ms.api.yallo.ch", "yallo")
    elif provider == "lebara":
        return SunriseClient("https://prod.ms.api.lebara.ch", "lebara")

    else:
        raise Exception(f"provider {provider} is not supported")
