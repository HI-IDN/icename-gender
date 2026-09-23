# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-09-23

### Added

- **`classify()` and the three rules:** *-dóttir*, then the register's given names, then *-son*.
  Given names come before *-son* because *-son* is also a family name. Ported from the
  surname-first rule in HI-IDN/skemman-msc, which counted a woman with a *-son* family name as
  a man.
- **The Mannanafnaskrá client** (`kyngreinir.registry`), moved here from the standalone
  `mannanafnaskra.py` that skemman-msc vendored, with a snapshot of the register bundled.
- **`explain()`:** the evidence behind an estimate -- what each given name and the suffix say,
  counted, and whether they agree (`unanimous`, `conflicting`, `none`).
- **CLI:** `kyngreinir name`, `kyngreinir csv` (both with `--detail`), `kyngreinir registry-fetch`.
