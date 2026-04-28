from swissmsplib.salt import SaltClient
from swissmsplib.sunrise import SunriseClient
from swissmsplib.swisscom_service import SwisscomServiceProviderClient
from swissmsplib.swisscom_network import SwisscomNetworkProviderClient


def create_client(
    provider,
) -> (
    SaltClient
    | SwisscomServiceProviderClient
    | SunriseClient
    | SwisscomNetworkProviderClient
):
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
        return SwisscomServiceProviderClient("https://selfcare.m-budget.migros.ch")
    elif provider == "coopmobile":
        return SwisscomServiceProviderClient("https://myaccount.coopmobile.ch")
    elif provider == "yallo":
        return SunriseClient("https://prod.ms.api.yallo.ch", "yallo")
    elif provider == "lebara":
        return SunriseClient("https://prod.ms.api.lebara.ch", "lebara")
    elif provider == "swisscom":
        return SwisscomNetworkProviderClient("https://www.swisscom.ch/myswisscom")

    else:
        raise Exception(f"provider {provider} is not supported")
