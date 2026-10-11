# osc8link

Build, detect and strip OSC 8 terminal hyperlinks

## Install

```
pip install osc8link
```

## Usage

```python
from osc8link import link, strip, contains_link, iter_links

# Build a clickable hyperlink for a terminal that supports OSC 8.
cell = link("https://example.com", "Example")
print(cell)

# Attach an id so a terminal can treat split segments as one link.
link("https://example.com", "Example", id="ref-1")

# Remove the escape sequences, keeping only the visible text.
strip(cell)              # "Example"

# Check whether a string carries a hyperlink.
contains_link(cell)      # True
contains_link("plain")   # False

# Walk every link as a (url, text) pair.
for url, text in iter_links(cell):
    print(url, text)     # https://example.com Example
```

Links are emitted with the `ESC \` string terminator. On parse, both `ESC \`
and `BEL` terminators are accepted, so sequences from any terminal are read
correctly.

## Why

OSC 8 is the escape sequence terminals render as a clickable hyperlink:
`ESC ] 8 ; params ; URI ESC \` around the text, closed by `ESC ] 8 ; ; ESC \`.
Full terminal toolkits know how to emit it, but the primitive is buried inside
them. There is no small, typed, zero-dependency package that just builds,
detects and strips the sequence: the alternatives are inline snippets copied
between projects, a Rust crate and a C# package. This fills that gap.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
