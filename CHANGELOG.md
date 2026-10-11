# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

- Add `link` to build an OSC 8 hyperlink from a url and text, with an optional `id`.
- Add `strip` to remove OSC 8 sequences and keep the visible text.
- Add `contains_link` to report whether a string carries a hyperlink.
- Add `iter_links` to yield each hyperlink as a `Link(url, text)` pair.
- Accept both `ESC \` and `BEL` terminators on parse; emit `ESC \` on build.
