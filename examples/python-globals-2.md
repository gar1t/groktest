---
[tool.groktest]

python.init = """
def greet():
    print("Hi hi hi")
"""

# """ hack to fix syntax highlighting in VS Code
---

This example shows a deeper configuation using TOML. In this case the
configuration follows the naming convention used in `pyproject.toml` to
init Python globals.

    >>> greet()
    Hi hi hi