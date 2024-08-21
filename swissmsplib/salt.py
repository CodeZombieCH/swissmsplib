from bs4 import BeautifulSoup
import datetime
import requests
import time
import json
import dateutil.relativedelta

import useragent


class SaltClient:
    def __init__(
        self, service_url, service_name, get_user_agent=useragent.get_default_user_agent
    ):
        if not service_url:
            raise ValueError("service_url cannot be empty")
        self.service_url = service_url

        if not service_name:
            raise ValueError("service_name cannot be empty")
        self.service_name = service_name

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": get_user_agent()})

    def login(self, username, password):
        if not username:
            raise ValueError("username cannot be empty")

        if not password:
            raise ValueError("password cannot be empty")

        url = f"https://login.salt.ch/cas-external/login?service={self.service_url}/&lang=de"

        response = self.session.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        execution = soup.select('input[name="execution"]')[0].get("value")

        payload = {
            # TODO: Encode
            "username": username,
            "password": password,
            "execution": execution,
            "_eventId": "submit",
            "geolocation": "",
        }
        self.session.post(url, data=payload)
        response.raise_for_status()

    def logout(self):
        response = self.session.get(
            f"https://login.salt.ch/cas-external/logout?service={self.service_url}/?v={time_ms()}&lang=en"
        )
        response.raise_for_status()

    def status(self):
        response = self.session.get(
            f"{self.service_url}/{self.service_name}/protected/v1/application/status?_={time_ms()}"
        )
        response.raise_for_status()

        with open("status.json", "w", encoding="utf-8") as f:
            json.dump(response.json(), f, ensure_ascii=False, indent=4)

    def get_subscriptions(self):
        response = self.session.get(
            f"{self.service_url}/{self.service_name}/protected/v1/subscription/list?_={time_ms()}"
        )
        response.raise_for_status()

        data = response.json()

        subscriptions = []
        for s in data:
            id = int(s["id"])
            number = s["number"]

            subscriptions.append(Subscription(id, number))

        return subscriptions

    def get_subscription(self, id):
        response = self.session.get(
            f"{self.service_url}/{self.service_name}/protected/v1/subscription/mobile/{id}/costcontrol/EN?_={time_ms()}"
        )
        response.raise_for_status()

        # Debug
        # with open(f"{id}.costcontrol.json", "w", encoding="utf-8") as f:
        #     json.dump(response.json(), f, ensure_ascii=False, indent=4)

        data = response.json()

        type_data = None
        for t in data["types"]:
            if t["type"] == "DATA":
                type_data = t
                break

        if type_data is None:
            raise ParserException("Failed to retrieve data usage")

        national_data = None
        for z in type_data["zones"]:
            if z["zoneName"] == "NATIONAL":
                national_data = z
                break

        if national_data is None:
            raise ParserException("Failed to retrieve data usage")

        counters = national_data["counters"]

        period_end = datetime.datetime.fromisoformat(counters["validUntil"])
        period_start = period_end - dateutil.relativedelta.relativedelta(months=1)
        period_total_seconds = (period_start - period_end).total_seconds()
        period_used_seconds = (
            period_start - datetime.datetime.now(datetime.timezone.utc)
        ).total_seconds()
        period_used_percentage = (
            100 * float(period_used_seconds) / float(period_total_seconds)
        )

        parsed_counters = Counters(
            percentUsed=int(counters["percentUsed"]),
            volumeUsed=int(counters["volumeUsed"]),
            volumeRemaining=int(counters["volumeRemaining"]),
            volumeTotal=int(counters["volumeTotal"]),
            validUntil=period_end,
            period_percent_used=period_used_percentage,
        )

        return parsed_counters


class Subscription:
    def __init__(self, id, number):
        self.id = id
        self.number = number


class Counters:
    def __init__(
        self,
        percentUsed,
        volumeRemaining,
        volumeTotal,
        volumeUsed,
        validUntil,
        period_percent_used,
    ):
        self.percentUsed = percentUsed
        self.volumeRemaining = volumeRemaining
        self.volumeTotal = volumeTotal
        self.volumeUsed = volumeUsed
        self.validUntil = validUntil
        self.period_percent_used = period_percent_used


class ParserException(Exception):
    pass


def time_ms():
    return time.time_ns() // 1_000_000
