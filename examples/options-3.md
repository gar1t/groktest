---
test-options: |
  +wildcard=…
  -case
---

Test options may be specified across multiple lines in YAML config, as
shown above.

    >>> 'HELLO'
    'hello'

    >>> 'HELLO'
    'H…O'
