---
option-functions: custom_types
---

    >> # +skiprest

    >> 1  # +notskip
    1

    >> 1  # -notskip
    2

TODO:

Skip option should accept an Any value plus info on the test, including
other options. It should be possible to something weird like this.

    >> 1  # +weird skips when +x=1 and +y=2

That's a grotesque edge case though so maybe it's not a good idea to
bother with it.

This is maybe a better case.

    >> 1  # +skip-if-day=Tuesday

I think we have separate config for `skip-function` and
`transform-functions`. Use `option_skip_` and `option_transform_`
prefixes though. This will let us handle the different signatures
cleanly.
