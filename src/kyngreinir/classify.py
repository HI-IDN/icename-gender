"""Estimate gender from an Icelandic full name.

The rules, in order -- the first that decides wins:

1. ``dottir``: the last name ends in -dóttir. A patronymic (or matronymic) ending in -dóttir is
   only ever a woman's.
2. ``given_name``: the first given name the register classifies as only a boy's or only a
   girl's name. Given names are every name but the last; a single name is its own given name.
   Hyphenated given names are also looked up part by part ("Anna-Lísa").
3. ``son``: the last name ends in -son. Checked only after the given names, because -son is
   also a family name: "Anna Thorsteinsson" is a woman, and the register says so first.

Anything else is unknown (gender None). The rule that decided is returned with the gender, so
estimates can be reported by how they were made.

`explain()` gives the evidence behind an estimate: what each part of the name says on its own,
how many parts say female and male, and whether they agree.

DISCLAIMER: this is a simple classifier based on which names Iceland's name register lists as
boys' or girls' names, and on the -dóttir/-son convention. It does not infer anyone's sex or
gender; it estimates what a name suggests under naming convention only. Report it in aggregate,
with the unknowns, never as a fact about an individual.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .registry import Register

_default_register: Register | None = None


@dataclass(frozen=True)
class Evidence:
    part: str  # the name part, as written
    source: str  # "register" (a given name) or "suffix" (-dóttir / -son on the last name)
    says: str  # "female", "male", "unisex" or "unknown"


@dataclass(frozen=True)
class Explanation:
    estimate: Estimate
    evidence: list[Evidence]
    female: int  # parts that say female
    male: int  # parts that say male
    unisex: int  # given names registered for both
    unknown: int  # given names not in the register, or only as middle names
    agreement: str  # "unanimous", "conflicting", or "none" (no part says either)


@dataclass(frozen=True)
class Estimate:
    gender: str | None  # "female", "male", or None
    rule: str | None  # "dottir", "given_name", "son", or None
    given_name: str | None = None  # the given name that decided, for rule "given_name"


def _register() -> Register:
    global _default_register
    if _default_register is None:
        _default_register = Register()
    return _default_register


def tokens(name: str) -> list[str]:
    """The name's parts, with commas, titles' dots and extra spaces removed."""
    return [t for t in re.split(r"[\s,]+", name.strip()) if t and t != "."]


def classify(name: str, register: Register | None = None) -> Estimate:
    """Estimate the gender of one full name. See the module docstring for the rules."""
    reg = register or _register()
    parts = tokens(name)
    if not parts:
        return Estimate(None, None)
    last = parts[-1].lower()
    if last.endswith("dóttir"):
        return Estimate("female", "dottir")
    for given in parts[:-1] or parts:
        for candidate in [given, *given.split("-")]:
            g = reg.gender_of(candidate)
            if g in ("male", "female"):
                return Estimate(g, "given_name", candidate)
    if last.endswith("son"):
        return Estimate("male", "son")
    return Estimate(None, None)


def _given_evidence(given: str, reg: Register) -> Evidence:
    says = reg.gender_of(given)
    if says == "unknown" and "-" in given:
        # A hyphenated name not registered whole: the parts that are registered decide.
        said = {reg.gender_of(p) for p in given.split("-")}
        decisive = said & {"female", "male"}
        if len(decisive) == 1:
            says = decisive.pop()
        elif decisive or "unisex" in said:
            says = "unisex"
    return Evidence(given, "register", says)


def explain(name: str, register: Register | None = None) -> Explanation:
    """The estimate with the evidence behind it: every given name's register entry and the
    last name's suffix, counted, and whether the parts that say anything agree."""
    reg = register or _register()
    parts = tokens(name)
    evidence = [_given_evidence(g, reg) for g in (parts[:-1] or parts)]
    if parts:
        last = parts[-1].lower()
        if last.endswith("dóttir"):
            evidence.append(Evidence(parts[-1], "suffix", "female"))
        elif last.endswith("son"):
            evidence.append(Evidence(parts[-1], "suffix", "male"))
    count = {k: sum(e.says == k for e in evidence) for k in ("female", "male", "unisex", "unknown")}
    if count["female"] and count["male"]:
        agreement = "conflicting"
    elif count["female"] or count["male"]:
        agreement = "unanimous"
    else:
        agreement = "none"
    return Explanation(classify(name, reg), evidence, agreement=agreement, **count)
