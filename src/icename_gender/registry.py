"""Þjóðskrá's Mannanafnaskrá (the Icelandic given/middle-name register), read through the
persisted GraphQL search behind island.is/leit-i-mannanafnaskra.

There is no documented public API or bulk dataset for this register. The search page is a
client-rendered app whose search box calls a stable, unauthenticated GraphQL endpoint; it is
called here directly with plain HTTP and the few headers CloudFront and Apollo's CSRF guard
require.

A snapshot of the whole register ships with the package (data/mannanafnaskra.csv), so
classifying needs no network. `fetch_all()` and `icename-gender registry-fetch` refresh it.

Entry shape: {"id": int, "icelandicName": str (lowercase), "type": str, "status": "Sam"|"Haf",
"verdict": "dd.mm.yyyy"|None, "url": str|None}.

`type` says who the name is registered for: "DR"/"RDR" = drengjanafn (a boy's name), "ST"/"RST"
= stúlknanafn (a girl's name); anything else (e.g. "MI", millinafn) is not gendered. `status`
"Haf" (rejected) is kept by default: a rejected name is still evidence of the intended gender.

PRIVACY: the register is about names, not people. Nothing here sends a person's name anywhere
unless the caller passes it to search().
"""

from __future__ import annotations

import csv
import json
import time
from collections.abc import Callable, Iterable
from importlib import resources
from pathlib import Path

import requests

ENDPOINT = "https://island.is/api/graphql"
REFERER = "https://island.is/leit-i-mannanafnaskra"
OPERATION = "GetIcelandicNameBySearch"
# A persisted-query hash the search page itself sends; stable as long as island.is does not
# change the query server-side. If every search fails with "PersistedQueryNotFound", re-derive
# it from the network tab of REFERER for the same operationName.
PERSISTED_SHA256 = "9ad0fe7dfad99b8acf592ad0ed4c9052d431e3a10fce79979d113c3b22f5bd73"

HEADERS = {
    # CloudFront in front of island.is blocks requests without a browser-shaped User-Agent.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    # Apollo's CSRF guard rejects a simple cross-site GET unless one of these is present.
    "Content-Type": "application/json",
    "apollo-require-preflight": "true",
    "apollographql-client-name": "cms-web-client",
    "apollographql-client-version": "0.1",
    "Referer": REFERER,
}

MALE_TYPES = {"DR", "RDR"}
FEMALE_TYPES = {"ST", "RST"}
FIELDS = ["id", "icelandicName", "type", "status", "verdict", "url"]

# The Icelandic alphabet. A single letter is a substring query returning every name that
# contains it, so the letters overlap heavily and fetch_all() dedupes by id.
ALPHABET = list("aábcdðeéfghiíjklmnoópqrstuúvwxyýzþæö")


def search(
    query: str, *, session: requests.Session | None = None, timeout: float = 20
) -> list[dict]:
    """One search, as the site's search box makes it: substring, case-insensitive,
    accent-sensitive ("Gudmundur" finds nothing; "Guðmundur" does)."""
    params = {
        "operationName": OPERATION,
        "variables": json.dumps({"input": {"q": query}}, separators=(",", ":")),
        "extensions": json.dumps(
            {"persistedQuery": {"version": 1, "sha256Hash": PERSISTED_SHA256}},
            separators=(",", ":"),
        ),
    }
    http = session or requests
    r = http.get(ENDPOINT, params=params, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    body = r.json()
    if "errors" in body:
        raise RuntimeError(f"Mannanafnaskrá query failed for {query!r}: {body['errors']}")
    return body["data"]["getIcelandicNameBySearch"]


def fetch_all(
    *, delay: float = 0.15, on_progress: Callable[[int, int, str, int], None] | None = None
) -> list[dict]:
    """The whole register: one query per letter, deduped by id, sorted by name."""
    seen: dict[int, dict] = {}
    with requests.Session() as s:
        for i, letter in enumerate(ALPHABET, 1):
            for entry in search(letter, session=s):
                seen[entry["id"]] = entry
            if on_progress:
                on_progress(i, len(ALPHABET), letter, len(seen))
            if delay:
                time.sleep(delay)
    return sorted(seen.values(), key=lambda e: (e["icelandicName"], e["id"]))


def write_csv(entries: Iterable[dict], path: Path) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        for e in entries:
            w.writerow({k: e.get(k) for k in FIELDS})


def read_csv(path: Path | None = None) -> list[dict]:
    """A register CSV; the snapshot bundled with the package when no path is given."""
    if path is None:
        text = resources.files("icename_gender").joinpath("data/mannanafnaskra.csv")
        with text.open(encoding="utf-8") as f:
            return list(csv.DictReader(f))
    with Path(path).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


class Register:
    """Name -> gender lookup over a register (by default the bundled snapshot)."""

    def __init__(self, entries: Iterable[dict] | None = None, *, approved_only: bool = False):
        self._genders: dict[str, set[str]] = {}
        for e in read_csv() if entries is None else entries:
            if approved_only and e["status"] != "Sam":
                continue
            if e["type"] in MALE_TYPES:
                gender = "male"
            elif e["type"] in FEMALE_TYPES:
                gender = "female"
            else:
                continue
            self._genders.setdefault(e["icelandicName"].lower(), set()).add(gender)

    def gender_of(self, given_name: str) -> str:
        """"male", "female", "unisex" (registered as both) or "unknown" (not found, or only
        as a middle name)."""
        g = self._genders.get(given_name.strip().lower(), set())
        if len(g) == 2:
            return "unisex"
        return next(iter(g)) if g else "unknown"
