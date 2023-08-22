---
test-type: doctest
---

# Test options

Test options are boolean flags or named values that apply to a test.

Options can be specified in three locations:

- Test type configuration
- Test file front-matter
- Tests via comments

## Test type configuration

TODO: This is all a hand wave at this point. Project config *should*
support new options but until we implement any options at all, this is
futuristic. Project config *must* support setting default values for
existing options (e.g. `case`, `match`, etc.)

Sample TOML formatting for the simplest possible case.

``` toml
[tool.groktest]

options = "-case +match"
```

## Front matter

Test file front-matter is used to set options that apply to tests
defined in that file. Options in front-matter for a file do not apply to
tests defined in other files.

```
---
test-options: +match -case
---
```
