import datetime
import json
import time
from dataclasses import dataclass

import dateutil.relativedelta
import requests
from bs4 import BeautifulSoup

from swissmsplib.common import ParserException, get_default_user_agent


def time_ms():
    return time.time_ns() // 1_000_000


class SaltClient:
    """
    Client for the Salt network provider
    """

    def __init__(
        self,
        login_url: str,
        service_url: str,
        service_name: str,
        get_user_agent=get_default_user_agent,
    ):
        if not login_url:
            raise ValueError("login_url cannot be empty")
        self.login_url = login_url

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

        url = f"{self.login_url}/cas-external/login?service={self.service_url}/&lang=de"

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
            f"{self.login_url}/cas-external/logout?service={self.service_url}/?v={time_ms()}&lang=en"
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

        subscriptions: list[Subscription] = []
        for s in data:
            subscriptions.append(Subscription.from_dict(s))

        return subscriptions

    def get_subscription(self, id: int):
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

    def get_bills(self, billing_account_id: int):
        # https://my.go-mo.ch/myaccount-gomo-ui-service/protected/v1/billing/<subscription_id>/accountSummary?_=<timestamp>
        response = self.session.get(
            f"{self.service_url}/{self.service_name}/protected/v1/billing/{billing_account_id}/accountSummary?_={time_ms()}"
        )
        response.raise_for_status()

        data = response.json()

        invoices: list[Invoice] = []
        for event in data:
            if event["eventType"] != "INVOICE":
                continue

            invoices.append(Invoice.from_dict(event))

        return invoices

    def download_bill_pdf(self, billing_account_id: int, invoice_id: int):
        # https://my.go-mo.ch/myaccount-gomo-ui-service/protected/v1/billing/<billing_account_id>/invoice/<invoice_id>?_=<timestamp>
        response = self.session.get(
            f"{self.service_url}/{self.service_name}/protected/v1/billing/{billing_account_id}/invoice/{invoice_id}?_={time_ms()}"
        )
        response.raise_for_status()

        return response.content


@dataclass
class Subscription:
    id: int
    number: str
    # Only available if post-paid, not for pre-paid
    billing_account_id: int | None

    @staticmethod
    def from_dict(obj) -> "Subscription":
        id = int(obj.get("id"))
        number = obj.get("number")

        billing_account_id_raw = obj.get("billingAccountId")
        if billing_account_id_raw:
            billing_account_id = int(billing_account_id_raw)
        else:
            billing_account_id = None

        return Subscription(id=id, number=number, billing_account_id=billing_account_id)


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


@dataclass
class BillingPeriod:
    startDate: datetime.date
    endDate: datetime.date

    @staticmethod
    def from_dict(obj) -> "BillingPeriod":
        _start_date = datetime.datetime.strptime(obj.get("startDate"), "%d.%m.%Y")
        _end_date = datetime.datetime.strptime(obj.get("endDate"), "%d.%m.%Y")

        return BillingPeriod(_start_date, _end_date)


@dataclass
class Invoice:
    invoice_id: int
    due_date: str
    billing_period: BillingPeriod | None
    total_amount: int
    date: str
    amount: int
    entry_type: str
    event_type: str
    invoice_type: str
    has_archive: bool

    @staticmethod
    def from_dict(obj) -> "Invoice":
        _invoice_id = int(obj.get("invoiceId"))
        _due_date = str(obj.get("dueDate"))
        _total_amount = int(obj.get("totalAmount"))
        _date = str(obj.get("date"))
        _amount = int(obj.get("amount"))
        _entry_type = str(obj.get("entryType"))
        _event_type = str(obj.get("eventType"))
        _invoice_type = str(obj.get("invoiceType"))
        _has_archive = bool(obj.get("hasArchive"))

        _billingPeriod = None
        if obj.get("billingPeriod"):
            _billingPeriod = BillingPeriod.from_dict(obj.get("billingPeriod"))

        return Invoice(
            _invoice_id,
            _due_date,
            _billingPeriod,
            _total_amount,
            _date,
            _amount,
            _entry_type,
            _event_type,
            _invoice_type,
            _has_archive,
        )
