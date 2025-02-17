# syrupy

<img align="right" width="100px" height="100px" src="https://user-images.githubusercontent.com/2528959/69500147-85d71400-0ec6-11ea-867a-277881278e57.png" alt="Logo">

[![All Contributors](https://img.shields.io/github/all-contributors/syrupy-project/syrupy?color=ee8449&style=flat-square)](#contributors) [![Stage](https://img.shields.io/pypi/status/syrupy)](https://pypi.org/project/syrupy/) [![codecov](https://codecov.io/gh/syrupy-project/syrupy/graph/badge.svg?token=GB9EmYKPAl)](https://codecov.io/gh/syrupy-project/syrupy)

![Pytest>=5.1.0,<9.0.0](https://img.shields.io/badge/pytest-%3E%3D5.1.0,%20%3C9.0.0-green) [![Pypi](https://img.shields.io/pypi/v/syrupy)](https://pypi.org/project/syrupy/) [![Wheel](https://img.shields.io/pypi/wheel/syrupy)](https://pypi.org/project/syrupy/) ![PyPI - Python Version](https://img.shields.io/pypi/pyversions/syrupy) [![PyPI - Downloads](https://img.shields.io/pypi/dm/syrupy)](https://pypi.org/project/syrupy/) [![PyPI - License](https://img.shields.io/pypi/l/syrupy)](./LICENSE)

## Overview

Syrupy is a zero-dependency [pytest](https://docs.pytest.org/en/latest/) snapshot plugin. It enables developers to write tests which assert immutability of computed results.

## Motivation

The most popular snapshot test plugin compatible with pytest has some core limitations which this package attempts to address by upholding some key values:

- Extensible: If a particular data type is not supported, users should be able to easily and quickly add support.
- Idiomatic: Snapshot testing should fit naturally among other test cases in pytest, e.g. `assert x == snapshot` vs. `snapshot.assert_match(x)`.
- Soundness: Snapshot tests should uncover even the most minute issues. Unlike other snapshot libraries, Syrupy will fail a test suite if a snapshot does not exist, not just on snapshot differences.

## Installation

```shell
python -m pip install syrupy
```

### Migration from snapshottest

You cannot use syrupy alongside snapshottest due to argument conflicts. To ease migration, we've made syrupy aware of snapshottest call syntax. Simply uninstall snapshottest and remove old snapshots:

```shell
pip uninstall snapshottest -y;
find . -type d ! -path '*/\.*' -name 'snapshots' | xargs rm -r
```

### Pytest and Python Compatibility

Syrupy will always be compatible with the latest version of Python and Pytest. If you're running an old version of Python or Pytest, you will need to use an older major version of Syrupy:

| Syrupy Version | Python Support | Pytest Support |
| -------------- | -------------- | -------------- |
| 5.x.x          | >3.9           | >=8            |
| 4.x.x          | >3.8.1,        | >=7,   <9      |
| 3.x.x          | >=3.7, <4      | >=5.1, <8      |
| 2.x.x          | >=3.6, <4      | >=5.1, <8      |

## Usage

### Basic Usage

In a pytest test file `test_file.py`:

```python
def test_foo(snapshot):
    actual = "Some computed value!"
    assert actual == snapshot
```

when you run `pytest`, the above test should fail due to a missing snapshot. Re-run pytest with the update snapshots flag like so:

```shell
pytest --snapshot-update
```

A snapshot file should be generated under a `__snapshots__` directory in the same directory as `test_file.py`. The `__snapshots__` directory and all its children should be committed along with your test code.

#### Custom Objects

The default serializer supports all python built-in types and provides a sensible default for custom objects.

#### Representation

If you need to customise your object snapshot, it is as easy as overriding the default `__repr__` implementation.

```python
def __repr__(self) -> str:
    return "MyCustomClass(...)"
```

If you need bypass a custom object representation to use the amber standard, it is easy using the following helpers.

```python
def test_object_as_named_tuple(snapshot):
    assert snapshot == AmberDataSerializer.object_as_named_tuple(obj_with_custom_repr)
```

> See `test_snapshot_object_as_named_tuple_class` for an example on automatically doing this for all nested properties

#### Attributes

If you want to limit what properties are serialized at a class type level you could either:

**A**. Provide a filter function to the snapshot [exclude](#exclude) configuration option.

```py
def limit_foo_attrs(prop, path):
    allowed_foo_attrs = {"do", "not", "serialize", "these", "attrs"}
    return isinstance(path[-1][1], Foo) and prop in allowed_foo_attrs

def test_bar(snapshot):
    actual = Foo(...)
    assert actual == snapshot(exclude=limit_foo_attrs)
```

**B**. Provide a filter function to the snapshot [include](#include) configuration option.

```py
def limit_foo_attrs(prop, path):
    allowed_foo_attrs = {"only", "serialize", "these", "attrs"}
    return isinstance(path[-1][1], Foo) and prop in allowed_foo_attrs

def test_bar(snapshot):
    actual = Foo(...)
    assert actual == snapshot(include=limit_foo_attrs)
```

**C**. Or override the `__dir__` implementation to control the attribute list.

```py
class Foo:
    def __dir__(self):
        return ["only", "serialize", "these", "attrs"]

def test_bar(snapshot):
    actual = Foo(...)
    assert actual == snapshot
```

Both options will generate equivalent snapshots but the latter is only viable when you have control over the class implementation and do not need to share the exclusion logic with other objects.

### CLI Options

These are the cli options exposed to `pytest` by the plugin.

| Option                         | Description                                                                                                                    | Default                                                                                                      |
| ------------------------------ |--------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------|
| `--snapshot-update`            | Snapshots will be updated to match assertions and unused snapshots will be deleted.                                            | `False`                                                                                                      |
| `--snapshot-details`           | Includes details of unused, generated, and updated snapshots (test name and snapshot location) in the final report.                                    | `False`                                                                                                      |
| `--snapshot-warn-unused`       | Prints a warning on unused snapshots rather than fail the test suite.                                                          | `False`                                                                                                      |
| `--snapshot-default-extension` | Use to change the default snapshot extension class.                                                                            | [AmberSnapshotExtension](https://github.com/syrupy-project/syrupy/blob/main/src/syrupy/extensions/amber/__init__.py) |
| `--snapshot-no-colors`         | Disable test results output highlighting. Equivalent to setting the environment variables `ANSI_COLORS_DISABLED` or `NO_COLOR` | Disabled by default if not in terminal.                                                                      |
| `--snapshot-patch-pycharm-diff`| Override PyCharm's default diffs viewer when looking at snapshot diffs. See [IDE Integrations](#ide-integrations)        | `False`                                                                                                      |
| `--snapshot-diff-mode` | Configures how diffs are displayed on assertion failure. If working with very large snapshots, disabling the diff can improve performance. | `detailed` |
| `--snapshot-ignore-file-extensions` | Comma separated list of file extensions to ignore when walking the file tree and discovering used/unused snapshots. | No extensions are ignored by default. |

### Assertion Options

These are the options available on the `snapshot` assertion fixture.
Use of these options are one shot and do not persist across assertions.
For more persistent options see [advanced usage](#advanced-usage).

#### `matcher`

This allows you to match on a property path and value to control how specific object shapes are serialized.

The matcher is a function that takes two keyword arguments.
It should return the replacement value to be serialized or the original unmutated value.

| Argument | Description                                                                                                        |
| -------- | ------------------------------------------------------------------------------------------------------------------ |
| `data`   | Current serializable value being matched on                                                                        |
| `path`   | Ordered path traversed to the current value e.g. `(("a", dict), ("b", dict))` from `{ "a": { "b": { "c": 1 } } }`} |

**NOTE:** Do not mutate the value received as it could cause unintended side effects.

##### Composing Matchers

Multiple matchers can be composed together using `matchers`, e.g.:

```py
from syrupy.matchers import compose_matchers

def test_multiple_matchers(snapshot):
    data = {
        "number": 1,
        "datetime": datetime.datetime.now(),
        "float": 1.3
    }

    assert data == snapshot(
        matcher=compose_matchers(
            path_type(types=(int, float), replacer=lambda *_: "MATCHER_1"),
            path_type(types=(datetime.datetime,), replacer=lambda *_: "MATCHER_2"),
        ),
    )
```

##### Built-In Matchers

Syrupy comes with built-in helpers that can be used to make easy work of using property matchers.

###### `path_type(mapping=None, *, types=(), strict=True, regex=False)`

Easy way to build a matcher that uses the path and value type to replace serialized data.
When strict, this will raise a `ValueError` if the types specified are not matched.

| Argument   | Description                                                                                                                        |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `mapping`  | Dict of path string to tuples of class types, including primitives e.g. (MyClass, UUID, datetime, int, str)                        |
| `types`    | Tuple of class types used if none of the path strings from the mapping are matched                                                 |
| `strict`   | If a path is matched but the value at the path does not match one of the class types in the tuple then a `PathTypeError` is raised |
| `regex`    | If true, the `mapping` key is treated as a regular expression when matching paths                                                  |
| `replacer` | Called with any matched value and result is used as the replacement that is serialized. Defaults to the object type when not given |

```py
from syrupy.matchers import path_type

def test_bar(snapshot):
    actual = {
      "date_created": datetime.now(),
      "value": "Some computed value!!",
    }
    assert actual == snapshot(matcher=path_type({
      "date_created": (datetime,),
      "nested.path.id": (int,),
    }))
```

```py
# name: test_bar
  dict({
    'date_created': datetime,
    'value': 'Some computed value!!',
  })
# ---
```

> NOTE: When `regex` is `True` all matcher mappings are treated as regex patterns

###### `path_value(mapping=None, *, **kwargs)`

Shares the same `kwargs` as `path_type` matcher, with the exception of the `mapping` argument type.
Only runs replacement for objects at a matching path where the value of the mapping also matches the object data string repr.

| Argument  | Description                                                |
| --------- | ---------------------------------------------------------- |
| `mapping` | Dict of path string to object value string representations |

> See `test_regex_matcher_str_value` for example usage.

#### `exclude`

This allows you to filter out object properties from the serialized snapshot.

The exclude parameter takes a filter function that accepts two keyword arguments.
It should return `true` if the property should be excluded, or `false` if the property should be included.

| Argument | Description                                                                                                                                   |
| -------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `prop`   | Current property on the object, could be any hashable value that can be used to retrieve a value e.g. `1`, `"prop_str"`, `SomeHashableObject` |
| `path`   | Ordered path traversed to the current value e.g. `(("a", dict), ("b", dict))` from `{ "a": { "b": { "c": 1 } } }`}                            |

##### Built-In Filters

Syrupy comes with built-in helpers that can be used to make easy work of using the filter options.

###### `props(prop_name, *prop_name)`

Easy way to build a filter that excludes based on string based property names.

Takes an argument list of property names, with support for indexed iterables.

```py
from syrupy.filters import props

def test_bar(snapshot):
    actual = {
      "id": uuid.uuid4(),
      "list": [1,2,3],
    }
    assert actual == snapshot(exclude=props("id", "1"))
```

```py
# name: test_bar
  dict({
    'list': list([
      1,
      3,
    ]),
  })
# ---
```

###### `paths(path_string, *path_strings)`

Easy way to build a filter that uses full path strings delimited with `.`.

Takes an argument list of path strings.

```py
from syrupy.filters import paths

def test_bar(snapshot):
    actual = {
      "date": datetime.now(),
      "list": [1,2,3],
    }
    assert actual == snapshot(exclude=paths("date", "list.1"))
```

```py
# name: test_bar
  dict({
    'list': list([
      1,
      3,
    ]),
  })
# ---
```

#### `include`

This allows you filter an object's properties to a subset using a predicate. This is the opposite of [exclude](#exclude). All the same property filters supporterd by [exclude](#exclude) are supported for `include`.

The include parameter takes a filter function that accepts two keyword arguments.
It should return `true` if the property should be include, or `false` if the property should not be included.

| Argument | Description                                                                                                                                   |
| -------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `prop`   | Current property on the object, could be any hashable value that can be used to retrieve a value e.g. `1`, `"prop_str"`, `SomeHashableObject` |
| `path`   | Ordered path traversed to the current value e.g. `(("a", dict), ("b", dict))` from `{ "a": { "b": { "c": 1 } } }`}

Note that `include` has some caveats which make it a bit more difficult to use than `exclude`. Both `include` and `exclude` are evaluated for each key of an object before traversing down nested paths. This means if you want to include a nested path, you must include all parents of the nested path, otherwise the nested child will never be reached to be evaluated against the include predicate. For example:

```py
obj = {
    "nested": { "key": True }
}
assert obj == snapshot(include=paths("nested", "nested.key"))
```

The extra "nested" is required, otherwise the nested dictionary will never be searched -- it'd get pruned too early.

To avoid adding duplicate path parts, we provide a convenient `paths_include` which supports a list/tuple instead of a string for each path to match:

```py
obj = {
    "other": False,
    "nested": { "key": True }
}
assert obj == snapshot(include=paths_include(["other"], ["nested", "key"]))
```

#### `extension_class`

This is a way to modify how the snapshot matches and serializes your data in a single assertion.

```py
def test_foo(snapshot):
    actual_svg = "<svg></svg>"
    assert actual_svg == snapshot(extension_class=SVGImageSnapshotExtension)
```

#### `diff`

This is an option to snapshot only the diff between the actual object and a previous snapshot, with the `diff` argument being the previous snapshot `index`/`name`.

```py
def test_diff(snapshot):
    actual0 = [1,2,3,4]
    actual1 = [0,1,3,4]

    assert actual0 == snapshot
    assert actual1 == snapshot(diff=0)
    # This is equivalent to the lines above
    # Must use the index name to diff when given
    assert actual0 == snapshot(name='snap_name')
    assert actual1 == snapshot(diff='snap_name')
```

##### Built-In Extensions

Syrupy comes with a few built-in preset configurations for you to choose from. You should also feel free to extend the `AbstractSyrupyExtension` if your project has a need not captured by one our built-ins.

- **`AmberSnapshotExtension`**: This is the default extension which generates `.ambr` files. Serialization of most data types are supported.
  - Line control characters are normalised when snapshots are generated i.e. `\r` and `\n` characters are all written as `\n`. This is to allow interoperability of snapshots between operating systems that use disparate line control characters.
- **`SingleFileSnapshotExtension`**: Unlike the `AmberSnapshotExtension`, which groups all tests within a single test file into a singular snapshot file, this extension creates one `.raw` file per test case. Note that the default behaviour of the SingleFileSnapshotExtension is to write raw bytes to disk. There is no further "serialization" that happens. For this reason, it is not a direct replacement for the Amber extension. The `SingleFileSnapshotExtension` is mostly used as a building block for other extensions such as the image extensions as well as the JSON extension. In the default "binary" mode, attempting to serialize a non-byte-like object will throw a TypeError.
- **`PNGImageSnapshotExtension`**: An extension of single file, this should be used to produce `.png` files from a byte string.
- **`SVGImageSnapshotExtension`**: Another extension of single file. This produces `.svg` files from an svg string.
- **`JSONSnapshotExtension`**: Another extension of single file. This produces `.json` files from dictionaries and lists.

#### `name`

By default, if you make multiple snapshot assertions within a single test case, an auto-increment identifier will be used to index the snapshots. You can override this behaviour by specifying a custom snapshot name to use in place of the auto-increment number.

```py
def test_case(snapshot):
    assert "actual" == snapshot(name="case_a")
    assert "other" == snapshot(name="case_b")
```

> _Warning_: If you use a custom name, you must make sure the name is not re-used within a test case.

### Advanced Usage

By overriding the provided [`AbstractSyrupyExtension`](https://github.com/syrupy-project/syrupy/tree/main/src/syrupy/extensions/base.py) you can implement varied custom behaviours.

See examples of how syrupy can be used and extended in the [test examples](https://github.com/syrupy-project/syrupy/tree/main/tests/examples).

#### Overriding defaults

It is possible to override `include`, `exclude`, `matchers` and `extension_class` on a more global level just once,
instead of every time per test. By default, after every assertion the modified values per snapshot assert are reverted
to their default values. However, it is possible to override those default values with ones you would like persisted,
which will be treated as the new defaults.

To achieve that you can use `snapshot.with_defaults`, which will create new instance of `SnapshotAssertion` with the provided values.

`snapshot.use_extension` is retained for compatibility. However, it is limited to only overriding the default extension class.

#### JSONSnapshotExtension

This extension can be useful when testing API responses, or when you have to deal with long dictionaries that are cumbersome to validate inside a test. For example:

```python
import pytest

from syrupy.extensions.json import JSONSnapshotExtension

@pytest.fixture
def snapshot_json(snapshot):
    return snapshot.with_defaults(extension_class=JSONSnapshotExtension)
    # or return snapshot.use_extension(JSONSnapshotExtension)


def test_api_call(client, snapshot_json):
    resp = client.post("/endpoint")
    assert resp.status_code == 200
    assert snapshot_json == resp.json()
```

API responses often contain dynamic data, like IDs or dates. You can still validate and store other data of a response by leveraging syrupy matchers. For example:

```py
from datetime import datetime

from syrupy.matchers import path_type

def test_api_call(client, snapshot_json):
    resp = client.post("/user", json={"name": "Jane"})
    assert resp.status_code == 201

    matcher = path_type({
      "id": (int,),
      "registeredAt": (datetime,)
    })
    assert snapshot_json(matcher=matcher) == resp.json()
```

The generated snapshot:

```json
{
  "id": "<class 'int'>",
  "registeredAt": "<class 'datetime'>",
  "name": "Jane"
}
```

Or a case where the value needs to be replaced using a condition e.g. file path string

```py
import re

from syrupy.matchers import path_type

def test_matches_generated_string_value(snapshot, tmp_file):
    matcher = path_value(
        mapping={"file_path": r"\w+://(.*/)+dir/filename.txt"},
        replacer=lambda _, match: match[0].replace(match[1], "<tmp-file-path>/"),
        types=(str,),
    )

    assert snapshot(matcher=matcher) == tmp_file
```

The generated snapshot:

```json
{
  "name": "Temp Files",
  "file_path": "scheme://<tmp-file-path>/dir/filename.txt"
}
```

#### Ignoring File Extensions (e.g. DVC Integration)

If using a tool such as [DVC](https://dvc.org/) or other tool where you need to ignore files by file extension, you can update your `pytest.ini` like so:

```ini
[pytest]
addopts = --snapshot-ignore-file-extensions dvc
```

A comma separated list is supported, like so:

```ini
[pytest]
addopts = --snapshot-ignore-file-extensions dvc,tmp,zip
```

### Extending Syrupy

- [Custom defaults](https://github.com/syrupy-project/syrupy/tree/main/tests/examples/test_custom_defaults.py)
- [Custom snapshot directory 1](https://github.com/syrupy-project/syrupy/tree/main/tests/examples/test_custom_snapshot_directory.py)
- [Custom snapshot directory 2](https://github.com/syrupy-project/syrupy/tree/main/tests/examples/test_custom_snapshot_directory_2.py)
- [Custom snapshot name](https://github.com/syrupy-project/syrupy/tree/main/tests/examples/test_custom_snapshot_name.py)
- [Custom object snapshots](https://github.com/syrupy-project/syrupy/tree/main/tests/examples/test_custom_object_repr.py)
- [Custom comparator](https://github.com/syrupy-project/syrupy/tree/main/tests/integration/test_custom_comparator.py)
- [JPEG image extension](https://github.com/syrupy-project/syrupy/tree/main/tests/examples/test_custom_image_extension.py)
- [Built-in image extensions](https://github.com/syrupy-project/syrupy/blob/main/tests/syrupy/extensions/image/test_image_svg.py)

### Inline Snapshots

Syrupy does not support inline snapshots. For inline snapshots, we recommend checking out the [inline-snapshot](https://github.com/15r10nk/inline-snapshot) library.

## IDE Integrations

### PyCharm

The [PyCharm](https://www.jetbrains.com/pycharm/) IDE comes with a built-in tool for visualizing differences between expected and actual results in a test. To properly render Syrupy snapshots in the PyCharm diff viewer, we need to apply a patch to the diff viewer library. To do this, use the `--snapshot-patch-pycharm-diff` flag, e.g.:

In your `pytest.ini`:

```ini
[pytest]
addopts = --snapshot-patch-pycharm-diff
```

See [#675](https://github.com/syrupy-project/syrupy/issues/675) for the original issue.

## Known Limitations

- `pytest-xdist` support only partially exists. There is no issue when it comes to reads however when you attempt to run `pytest --snapshot-update`, if running with more than 1 process, the ability to detect unused snapshots is disabled. See [#535](https://github.com/syrupy-project/syrupy/issues/535) for more information.

_We welcome contributions to patch these known limitations._

## Uninstalling

```python
pip uninstall syrupy
```

If you have decided not to use Syrupy for your project after giving us a try, we'd love to get your feedback. Please create a GitHub issue if applicable.

## Contributing

Feel free to open a PR or GitHub issue. Contributions welcome!

To develop locally, clone this repository and run `. script/bootstrap` to install test dependencies. You can then use `invoke --list` to see available commands.

### See contributing [guide](https://github.com/syrupy-project/syrupy/tree/main/CONTRIBUTING.md)

## Contributors

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://noahnu.com"><img src="https://avatars0.githubusercontent.com/u/1297096?v=4?s=100" width="100px;" alt="Noah"/><br /><sub><b>Noah</b></sub></a><br /><a href="#infra-noahnu" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="#ideas-noahnu" title="Ideas, Planning, & Feedback">🤔</a> <a href="https://github.com/syrupy-project/syrupy/commits?author=noahnu" title="Code">💻</a> <a href="https://github.com/syrupy-project/syrupy/commits?author=noahnu" title="Documentation">📖</a> <a href="https://github.com/syrupy-project/syrupy/commits?author=noahnu" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://emmanuel.ogbizi.com"><img src="https://avatars0.githubusercontent.com/u/2528959?v=4?s=100" width="100px;" alt="Emmanuel Ogbizi"/><br /><sub><b>Emmanuel Ogbizi</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/commits?author=iamogbz" title="Code">💻</a> <a href="#design-iamogbz" title="Design">🎨</a> <a href="#infra-iamogbz" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a> <a href="https://github.com/syrupy-project/syrupy/commits?author=iamogbz" title="Documentation">📖</a> <a href="https://github.com/syrupy-project/syrupy/commits?author=iamogbz" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/adamlazz"><img src="https://avatars3.githubusercontent.com/u/453811?v=4?s=100" width="100px;" alt="Adam Lazzarato"/><br /><sub><b>Adam Lazzarato</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/commits?author=adamlazz" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://mcataford.github.io"><img src="https://avatars2.githubusercontent.com/u/6210361?v=4?s=100" width="100px;" alt="Marc Cataford"/><br /><sub><b>Marc Cataford</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/commits?author=mcataford" title="Code">💻</a> <a href="https://github.com/syrupy-project/syrupy/commits?author=mcataford" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://msrose.github.io"><img src="https://avatars3.githubusercontent.com/u/3495264?v=4?s=100" width="100px;" alt="Michael Rose"/><br /><sub><b>Michael Rose</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/commits?author=msrose" title="Code">💻</a> <a href="https://github.com/syrupy-project/syrupy/commits?author=msrose" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://fashionablenonsense.com/"><img src="https://avatars0.githubusercontent.com/u/3112159?v=4?s=100" width="100px;" alt="Jimmy Jia"/><br /><sub><b>Jimmy Jia</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/commits?author=taion" title="Code">💻</a> <a href="https://github.com/syrupy-project/syrupy/commits?author=taion" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://stevenloria.com"><img src="https://avatars2.githubusercontent.com/u/2379650?v=4?s=100" width="100px;" alt="Steven Loria"/><br /><sub><b>Steven Loria</b></sub></a><br /><a href="#infra-sloria" title="Infrastructure (Hosting, Build-Tools, etc)">🚇</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/arturbalabanov"><img src="https://avatars1.githubusercontent.com/u/3062003?v=4?s=100" width="100px;" alt="Artur Balabanov"/><br /><sub><b>Artur Balabanov</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/commits?author=arturbalabanov" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://huonw.github.io/"><img src="https://avatars1.githubusercontent.com/u/1203825?v=4?s=100" width="100px;" alt="Huon Wilson"/><br /><sub><b>Huon Wilson</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/commits?author=huonw" title="Code">💻</a> <a href="https://github.com/syrupy-project/syrupy/issues?q=author%3Ahuonw" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/eaculb"><img src="https://avatars.githubusercontent.com/u/31480498?v=4?s=100" width="100px;" alt="Elizabeth Culbertson"/><br /><sub><b>Elizabeth Culbertson</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/commits?author=eaculb" title="Code">💻</a> <a href="https://github.com/syrupy-project/syrupy/commits?author=eaculb" title="Tests">⚠️</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/joakimnordling"><img src="https://avatars.githubusercontent.com/u/6637576?v=4?s=100" width="100px;" alt="Joakim Nordling"/><br /><sub><b>Joakim Nordling</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/issues?q=author%3Ajoakimnordling" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/bendidi"><img src="https://avatars.githubusercontent.com/u/22003440?v=4?s=100" width="100px;" alt="Ouail"/><br /><sub><b>Ouail</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/commits?author=bendidi" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/fbjorn"><img src="https://avatars.githubusercontent.com/u/9670990?v=4?s=100" width="100px;" alt="Denis"/><br /><sub><b>Denis</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/commits?author=fbjorn" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/N0124"><img src="https://avatars.githubusercontent.com/u/29734397?v=4?s=100" width="100px;" alt="N0124"/><br /><sub><b>N0124</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/commits?author=N0124" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/dtczest"><img src="https://avatars.githubusercontent.com/u/97055299?v=4?s=100" width="100px;" alt="dtczest"/><br /><sub><b>dtczest</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/issues?q=author%3Adtczest" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/spagh-eddie"><img src="https://avatars.githubusercontent.com/u/58013020?v=4?s=100" width="100px;" alt="Eddie Darling"/><br /><sub><b>Eddie Darling</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/commits?author=spagh-eddie" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/darrenburns"><img src="https://avatars.githubusercontent.com/u/5740731?v=4?s=100" width="100px;" alt="darrenburns"/><br /><sub><b>darrenburns</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/commits?author=darrenburns" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/mhwaage"><img src="https://avatars.githubusercontent.com/u/57612883?v=4?s=100" width="100px;" alt="Magnus Heskestad Waage"/><br /><sub><b>Magnus Heskestad Waage</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/issues?q=author%3Amhwaage" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/herb"><img src="https://avatars.githubusercontent.com/u/139780?v=4?s=100" width="100px;" alt="Herbert Ho"/><br /><sub><b>Herbert Ho</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/issues?q=author%3Aherb" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/tolgaeren"><img src="https://avatars.githubusercontent.com/u/794719?v=4?s=100" width="100px;" alt="Tolga Eren"/><br /><sub><b>Tolga Eren</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/issues?q=author%3Atolgaeren" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://johnkurkowski.com"><img src="https://avatars.githubusercontent.com/u/299487?v=4?s=100" width="100px;" alt="John Kurkowski"/><br /><sub><b>John Kurkowski</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/issues?q=author%3Ajohn-kurkowski" title="Bug reports">🐛</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://www.atharvaarya.tech/"><img src="https://avatars.githubusercontent.com/u/55894364?v=4?s=100" width="100px;" alt="Atharva Arya"/><br /><sub><b>Atharva Arya</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/commits?author=atharva-2001" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/michaljelonek"><img src="https://avatars.githubusercontent.com/u/7791528?v=4?s=100" width="100px;" alt="Michał Jelonek"/><br /><sub><b>Michał Jelonek</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/commits?author=michaljelonek" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/ManiacDC"><img src="https://avatars.githubusercontent.com/u/1823305?v=4?s=100" width="100px;" alt="ManiacDC"/><br /><sub><b>ManiacDC</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/commits?author=ManiacDC" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://schemathesis.io/"><img src="https://avatars.githubusercontent.com/u/1236561?v=4?s=100" width="100px;" alt="Dmitry Dygalo"/><br /><sub><b>Dmitry Dygalo</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/commits?author=Stranger6667" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://allanchain.github.io/"><img src="https://avatars.githubusercontent.com/u/36528777?v=4?s=100" width="100px;" alt="Allan Chain"/><br /><sub><b>Allan Chain</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/issues?q=author%3AAllanChain" title="Bug reports">🐛</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/UltimateLobster"><img src="https://avatars.githubusercontent.com/u/21122724?v=4?s=100" width="100px;" alt="Nir Schulman"/><br /><sub><b>Nir Schulman</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/commits?author=UltimateLobster" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://joostlek.dev"><img src="https://avatars.githubusercontent.com/u/7083755?v=4?s=100" width="100px;" alt="Joost Lekkerkerker"/><br /><sub><b>Joost Lekkerkerker</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/commits?author=joostlek" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/epenet"><img src="https://avatars.githubusercontent.com/u/6771947?v=4?s=100" width="100px;" alt="epenet"/><br /><sub><b>epenet</b></sub></a><br /><a href="https://github.com/syrupy-project/syrupy/commits?author=epenet" title="Tests">⚠️</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This section is automatically generated via tagging the all-contributors bot in a PR:

```text
@all-contributors please add <username> for <contribution type>
```

## License

Syrupy is licensed under [MIT](https://github.com/syrupy-project/syrupy/tree/main/LICENSE).
