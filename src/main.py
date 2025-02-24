import datetime
import hashlib
import logging

import requests
from environs import Env
from flask import Flask, Response, request
from icalendar import Calendar, Event

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

env = Env()
env.read_env()


PORKBUN_API_SECRET = env.str("PORKBUN_API_SECRET", default=None)
PORKBUN_API_KEY = env.str("PORKBUN_API_KEY", default=None)

app = Flask(__name__)


@app.route("/calendar.ics")
def calendar():
    # Allow API credentials to be provided via Basic Auth
    auth = request.authorization
    if auth:
        log.info(auth)
        api_key = auth.username
        api_secret = auth.password
    else:
        api_key = PORKBUN_API_KEY
        api_secret = PORKBUN_API_SECRET

    if not api_key or not api_secret:
        headers = {"WWW-Authenticate": 'Basic realm="Login Required"'}
        return Response("Missing Porkbun API credentials", status=401, headers=headers)

    try:
        domains = list_domains(api_key, api_secret)
        log.info(f"{len(domains)} domains found")
    except requests.HTTPError as e:
        # Mirror whatever error returned by the API
        log.error(f"Porkbun API error: {e.response.text}")
        return Response(str(e), status=e.response.status_code)
    response_text = generate_icalendar(domains)
    response = Response(response_text, content_type="text/calendar")
    response.headers["Content-Disposition"] = "attachment; filename=calendar.ics"
    return response


def list_domains(key: str | None, secret: str | None):
    api_base = "https://api.porkbun.com/api/json/v3"
    body = {
        "secretapikey": secret,
        "apikey": key,
        "includeLabels": "yes",
    }
    resp = requests.post(f"{api_base}/domain/listAll", json=body)
    resp.raise_for_status()
    data = resp.json()
    return data.get("domains", [])


def parse_datetime(date_str):
    return datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")


def generate_icalendar(domains):
    name = "Porkbun Domains"
    description = "Calendar for Porkbun domain renewals."
    refresh_interval = "P1W"
    cal = Calendar(
        version="2.0",
        prodid="-//Porkbun//Domain Calendar v1.0//EN",
        name=name,
        description=description,
        method="PUBLISH",
    )
    cal.add("last-modified", datetime.datetime.utcnow())
    cal.add("refresh-interval", refresh_interval)
    cal.add("x-wr-calname", name)
    cal.add("x-wr-caldesc", description)
    cal.add("x-published-ttl", refresh_interval)
    cal.add("x-wr-timezone", "UTC")
    for domain in domains:
        name = domain["domain"]
        event = Event(uid=hashlib.md5(name.encode()).hexdigest(), summary=f"🐷 {name}")
        event.add("transp", "TRANSPARENT")
        event.add("dtstart", parse_datetime(domain["expireDate"]))
        event.add("dtend", parse_datetime(domain["expireDate"]))
        event.add("rrule", {"freq": "YEARLY"})
        cal.add_component(event)

    return cal.to_ical()


if __name__ == "__main__":
    app.run()
