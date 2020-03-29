# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Move some IV and energy data fields from `data` struct to other nested
  data structs (`data_iv` and `data_energy`) in order to avoid use of
  struct embedding. The makes the package compatible with `construct`
  v2.10, which removed the `Embedded` mechanism. This breaks code which
  looks for e.g. `msg.data.energy_act_pos`, which is now in
  `msg.data_energy.act_pos`.

## [1.0.0] - 2019-01-14

Initial release. Minimum viable parser and database storage.

[Unreleased]: https://github.com/endrebjorsvik/kaifa-meter/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/endrebjorsvik/kaifa-meter/releases/tag/v1.0.0

