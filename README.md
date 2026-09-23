# icename-gender

[![CI](https://github.com/HI-IDN/icename-gender/actions/workflows/ci.yml/badge.svg)](https://github.com/HI-IDN/icename-gender/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)

Estimate gender from Icelandic names — from the naming convention and
[Þjóðskrá's name register](https://island.is/leit-i-mannanafnaskra) (Mannanafnaskrá).

> **Disclaimer.** This is a simple classifier based on which names the register lists as
> boys' or girls' names, and on the *-dóttir*/*-son* convention. It does not infer anyone's
> sex or gender: it estimates what a name suggests under naming convention only. Use it for
> aggregate statistics, report the unknowns, and never present it as a fact about a person.

```bash
icename-gender name "Helga Ingimundardóttir"  # female  dottir
icename-gender csv people.csv --column name -o people_gender.csv
```

```python
from icename_gender import classify

classify("Helga Ingimundardóttir")   # Estimate(gender='female', rule='dottir', given_name=None)
```

## The rules

In order; the first that decides wins, and the rule is returned with the gender.

1. **`dottir`** — the last name ends in *-dóttir*. That is only ever a woman's.
2. **`given_name`** — the first given name the register lists only as a boy's name
   (*drengjanafn*) or only as a girl's name (*stúlknanafn*). Given names are every name but the
   last. Unisex names and middle names (*millinöfn*) are passed over; hyphenated names are also
   looked up part by part.
3. **`son`** — the last name ends in *-son*. Checked only after the given names, because *-son*
   is also a family name: "Helga Ingimundarson" is a woman, and her given name says so first.

Anything else is unknown.

## How certain is it?

`explain()` (and `--detail` on the CLI) shows the evidence behind an estimate: what each given
name says in the register, what the last name's suffix says, how many parts say female and
male, and whether they agree.

```bash
icename-gender name "Helga Ingimundarson" --detail
# female  given_name (Helga)
#   Helga          register  female
#   Ingimundarson  suffix    male
#   agreement: conflicting (female 1, male 1, unisex 0, unknown 0)
```

`agreement` is `unanimous` when every part that says anything says the same, `conflicting`
when parts disagree (the estimate then follows the rules above), and `none` when no part says
either. `icename-gender csv --detail` adds `gender_agreement`, `gender_female` and `gender_male`
columns.

Full documentation: <https://hi-idn.github.io/icename-gender/>

## What it deliberately does not do

- **No guessing past the evidence.** A name no rule decides is unknown, not a coin toss, and a
  name registered for both boys and girls is not assigned to either.
- **No claims about people.** This estimates gender from a naming convention. Report it in
  aggregate, with the unknowns, never as a fact about an individual.
- **No personal data.** The register is about names, not people. Classifying runs offline
  against a snapshot bundled with the package; nothing is sent anywhere.

## Install

```bash
pip install git+https://github.com/HI-IDN/icename-gender.git
```

For development:

```bash
git clone git@github.com:HI-IDN/icename-gender.git
cd icename-gender
pip install -e ".[dev]"
pytest
```

## The register

A snapshot of the whole register ships in `src/icename_gender/data/mannanafnaskra.csv`. To refresh
it (about 30 requests to island.is, under a minute):

```bash
icename-gender registry-fetch -o src/icename_gender/data/mannanafnaskra.csv
```

or use a fresh copy without replacing the bundled one: `icename-gender name ... --register my.csv`.

There is no documented public API for the register. Its search page calls an unauthenticated
GraphQL endpoint, which `icename_gender.registry.search()` calls directly; see that module for the
details and what to do if island.is changes the query.

## License

MIT. See [LICENSE](LICENSE).
