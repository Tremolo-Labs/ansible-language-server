"""Static Jinja2 filter and test fallbacks.

Used when Ansible isn't available for dynamic extraction.
These lists are maintained manually and should cover common cases.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class FilterInfo:
    """Jinja2 filter metadata."""

    name: str
    description: str
    source: str = "ansible"  # "ansible" or "jinja2"
    example: Optional[str] = None


@dataclass(frozen=True)
class TestInfo:
    """Jinja2 test metadata."""

    name: str
    description: str
    source: str = "ansible"  # "ansible" or "jinja2"
    example: Optional[str] = None


# =============================================================================
# Ansible Jinja2 Filters
# =============================================================================

JINJA_FILTERS: dict[str, FilterInfo] = {
    # Data encoding
    "b64encode": FilterInfo(
        "b64encode",
        "Base64 encode a string",
        example="{{ 'hello' | b64encode }}",
    ),
    "b64decode": FilterInfo(
        "b64decode",
        "Base64 decode a string",
        example="{{ encoded | b64decode }}",
    ),
    "to_json": FilterInfo(
        "to_json",
        "Convert value to JSON string",
        example="{{ myvar | to_json }}",
    ),
    "from_json": FilterInfo(
        "from_json",
        "Parse JSON string to value",
        example="{{ json_string | from_json }}",
    ),
    "to_yaml": FilterInfo(
        "to_yaml",
        "Convert value to YAML string",
        example="{{ myvar | to_yaml }}",
    ),
    "from_yaml": FilterInfo(
        "from_yaml",
        "Parse YAML string to value",
        example="{{ yaml_string | from_yaml }}",
    ),
    "to_nice_json": FilterInfo(
        "to_nice_json",
        "Convert to pretty-printed JSON",
        example="{{ myvar | to_nice_json }}",
    ),
    "to_nice_yaml": FilterInfo(
        "to_nice_yaml",
        "Convert to pretty-printed YAML",
        example="{{ myvar | to_nice_yaml }}",
    ),
    # String manipulation
    "quote": FilterInfo(
        "quote",
        "Shell-quote a string for safe use in commands",
        example="{{ filename | quote }}",
    ),
    "regex_search": FilterInfo(
        "regex_search",
        "Search string with regex, return match or empty",
        example="{{ text | regex_search('pattern') }}",
    ),
    "regex_replace": FilterInfo(
        "regex_replace",
        "Replace regex matches in string",
        example="{{ text | regex_replace('old', 'new') }}",
    ),
    "regex_findall": FilterInfo(
        "regex_findall",
        "Find all regex matches in string",
        example="{{ text | regex_findall('\\\\d+') }}",
    ),
    "regex_escape": FilterInfo(
        "regex_escape",
        "Escape special regex characters",
        example="{{ user_input | regex_escape }}",
    ),
    "splitext": FilterInfo(
        "splitext",
        "Split filename into base and extension",
        example="{{ 'file.txt' | splitext }}",
    ),
    "basename": FilterInfo(
        "basename",
        "Get filename from path",
        example="{{ '/path/to/file.txt' | basename }}",
    ),
    "dirname": FilterInfo(
        "dirname",
        "Get directory from path",
        example="{{ '/path/to/file.txt' | dirname }}",
    ),
    "expanduser": FilterInfo(
        "expanduser",
        "Expand ~ to home directory",
        example="{{ '~/.ssh/id_rsa' | expanduser }}",
    ),
    "expandvars": FilterInfo(
        "expandvars",
        "Expand environment variables in path",
        example="{{ '$HOME/.config' | expandvars }}",
    ),
    "realpath": FilterInfo(
        "realpath",
        "Get absolute path resolving symlinks",
        example="{{ './relative/path' | realpath }}",
    ),
    # Type conversion
    "bool": FilterInfo(
        "bool",
        "Convert to boolean",
        example="{{ 'yes' | bool }}",
    ),
    "int": FilterInfo(
        "int",
        "Convert to integer",
        source="jinja2",
        example="{{ '42' | int }}",
    ),
    "float": FilterInfo(
        "float",
        "Convert to float",
        source="jinja2",
        example="{{ '3.14' | float }}",
    ),
    "string": FilterInfo(
        "string",
        "Convert to string",
        source="jinja2",
        example="{{ 42 | string }}",
    ),
    "list": FilterInfo(
        "list",
        "Convert to list",
        source="jinja2",
        example="{{ 'abc' | list }}",
    ),
    # Collection manipulation
    "combine": FilterInfo(
        "combine",
        "Merge multiple dicts, later values override",
        example="{{ dict1 | combine(dict2) }}",
    ),
    "dict2items": FilterInfo(
        "dict2items",
        "Convert dict to list of {key, value} dicts",
        example="{{ mydict | dict2items }}",
    ),
    "items2dict": FilterInfo(
        "items2dict",
        "Convert list of {key, value} dicts to dict",
        example="{{ item_list | items2dict }}",
    ),
    "flatten": FilterInfo(
        "flatten",
        "Flatten nested lists",
        example="{{ nested_list | flatten }}",
    ),
    "unique": FilterInfo(
        "unique",
        "Remove duplicates from list",
        example="{{ mylist | unique }}",
    ),
    "union": FilterInfo(
        "union",
        "Set union of two lists",
        example="{{ list1 | union(list2) }}",
    ),
    "intersect": FilterInfo(
        "intersect",
        "Set intersection of two lists",
        example="{{ list1 | intersect(list2) }}",
    ),
    "difference": FilterInfo(
        "difference",
        "Set difference of two lists",
        example="{{ list1 | difference(list2) }}",
    ),
    "symmetric_difference": FilterInfo(
        "symmetric_difference",
        "Symmetric set difference of two lists",
        example="{{ list1 | symmetric_difference(list2) }}",
    ),
    "zip": FilterInfo(
        "zip",
        "Zip lists together",
        example="{{ list1 | zip(list2) | list }}",
    ),
    "zip_longest": FilterInfo(
        "zip_longest",
        "Zip lists, padding shorter with fillvalue",
        example="{{ list1 | zip_longest(list2, fillvalue='') | list }}",
    ),
    "product": FilterInfo(
        "product",
        "Cartesian product of lists",
        example="{{ list1 | product(list2) | list }}",
    ),
    "permutations": FilterInfo(
        "permutations",
        "All permutations of list",
        example="{{ mylist | permutations | list }}",
    ),
    "combinations": FilterInfo(
        "combinations",
        "All combinations of list",
        example="{{ mylist | combinations(2) | list }}",
    ),
    # Conditional/default
    "mandatory": FilterInfo(
        "mandatory",
        "Fail if value is undefined",
        example="{{ required_var | mandatory }}",
    ),
    "default": FilterInfo(
        "default",
        "Provide default if undefined or empty",
        source="jinja2",
        example="{{ myvar | default('fallback') }}",
    ),
    "ternary": FilterInfo(
        "ternary",
        "Conditional value selection (like ternary operator)",
        example="{{ condition | ternary('yes', 'no') }}",
    ),
    # Hashing
    "hash": FilterInfo(
        "hash",
        "Hash string with given algorithm",
        example="{{ password | hash('sha512') }}",
    ),
    "password_hash": FilterInfo(
        "password_hash",
        "Generate password hash for /etc/shadow",
        example="{{ password | password_hash('sha512') }}",
    ),
    "checksum": FilterInfo(
        "checksum",
        "MD5 checksum of string",
        example="{{ data | checksum }}",
    ),
    # IP address
    "ipaddr": FilterInfo(
        "ipaddr",
        "Validate and manipulate IP addresses",
        example="{{ '192.168.1.1' | ipaddr }}",
    ),
    "ipv4": FilterInfo(
        "ipv4",
        "Filter for IPv4 addresses",
        example="{{ addresses | ipv4 }}",
    ),
    "ipv6": FilterInfo(
        "ipv6",
        "Filter for IPv6 addresses",
        example="{{ addresses | ipv6 }}",
    ),
    # Jinja2 builtins
    "upper": FilterInfo(
        "upper",
        "Convert string to uppercase",
        source="jinja2",
        example="{{ name | upper }}",
    ),
    "lower": FilterInfo(
        "lower",
        "Convert string to lowercase",
        source="jinja2",
        example="{{ name | lower }}",
    ),
    "capitalize": FilterInfo(
        "capitalize",
        "Capitalize first letter",
        source="jinja2",
        example="{{ name | capitalize }}",
    ),
    "title": FilterInfo(
        "title",
        "Title-case string",
        source="jinja2",
        example="{{ name | title }}",
    ),
    "trim": FilterInfo(
        "trim",
        "Strip whitespace from both ends",
        source="jinja2",
        example="{{ text | trim }}",
    ),
    "replace": FilterInfo(
        "replace",
        "Replace substring",
        source="jinja2",
        example="{{ text | replace('old', 'new') }}",
    ),
    "join": FilterInfo(
        "join",
        "Join list elements with separator",
        source="jinja2",
        example="{{ mylist | join(', ') }}",
    ),
    "split": FilterInfo(
        "split",
        "Split string by separator",
        source="jinja2",
        example="{{ csv | split(',') }}",
    ),
    "first": FilterInfo(
        "first",
        "Get first element of list",
        source="jinja2",
        example="{{ mylist | first }}",
    ),
    "last": FilterInfo(
        "last",
        "Get last element of list",
        source="jinja2",
        example="{{ mylist | last }}",
    ),
    "length": FilterInfo(
        "length",
        "Get length of list or string",
        source="jinja2",
        example="{{ mylist | length }}",
    ),
    "sort": FilterInfo(
        "sort",
        "Sort list",
        source="jinja2",
        example="{{ mylist | sort }}",
    ),
    "reverse": FilterInfo(
        "reverse",
        "Reverse list or string",
        source="jinja2",
        example="{{ mylist | reverse | list }}",
    ),
    "map": FilterInfo(
        "map",
        "Apply filter to each element",
        source="jinja2",
        example="{{ users | map(attribute='name') | list }}",
    ),
    "select": FilterInfo(
        "select",
        "Filter elements by test",
        source="jinja2",
        example="{{ numbers | select('even') | list }}",
    ),
    "reject": FilterInfo(
        "reject",
        "Filter elements by inverse test",
        source="jinja2",
        example="{{ numbers | reject('even') | list }}",
    ),
    "selectattr": FilterInfo(
        "selectattr",
        "Filter objects by attribute test",
        source="jinja2",
        example="{{ users | selectattr('active') | list }}",
    ),
    "rejectattr": FilterInfo(
        "rejectattr",
        "Filter objects by inverse attribute test",
        source="jinja2",
        example="{{ users | rejectattr('admin') | list }}",
    ),
    "groupby": FilterInfo(
        "groupby",
        "Group items by attribute",
        source="jinja2",
        example="{{ users | groupby('department') }}",
    ),
    "batch": FilterInfo(
        "batch",
        "Split list into chunks",
        source="jinja2",
        example="{{ items | batch(3) | list }}",
    ),
    "slice": FilterInfo(
        "slice",
        "Slice list into N sublists",
        source="jinja2",
        example="{{ items | slice(3) | list }}",
    ),
    "random": FilterInfo(
        "random",
        "Get random element from list",
        source="jinja2",
        example="{{ mylist | random }}",
    ),
    "shuffle": FilterInfo(
        "shuffle",
        "Shuffle list randomly",
        example="{{ mylist | shuffle }}",
    ),
    "min": FilterInfo(
        "min",
        "Get minimum value",
        source="jinja2",
        example="{{ numbers | min }}",
    ),
    "max": FilterInfo(
        "max",
        "Get maximum value",
        source="jinja2",
        example="{{ numbers | max }}",
    ),
    "sum": FilterInfo(
        "sum",
        "Sum numeric values",
        source="jinja2",
        example="{{ numbers | sum }}",
    ),
    "abs": FilterInfo(
        "abs",
        "Absolute value",
        source="jinja2",
        example="{{ number | abs }}",
    ),
    "round": FilterInfo(
        "round",
        "Round to N decimal places",
        source="jinja2",
        example="{{ 3.14159 | round(2) }}",
    ),
    "indent": FilterInfo(
        "indent",
        "Indent text by N spaces",
        source="jinja2",
        example="{{ text | indent(4) }}",
    ),
    "wordwrap": FilterInfo(
        "wordwrap",
        "Wrap text at N characters",
        source="jinja2",
        example="{{ text | wordwrap(80) }}",
    ),
    "truncate": FilterInfo(
        "truncate",
        "Truncate string to N characters",
        source="jinja2",
        example="{{ text | truncate(50) }}",
    ),
    "center": FilterInfo(
        "center",
        "Center string in N characters",
        source="jinja2",
        example="{{ text | center(80) }}",
    ),
    "format": FilterInfo(
        "format",
        "Format string (like sprintf)",
        source="jinja2",
        example="{{ '%s: %d' | format(name, count) }}",
    ),
    "safe": FilterInfo(
        "safe",
        "Mark string as safe (no escaping)",
        source="jinja2",
        example="{{ html | safe }}",
    ),
    "escape": FilterInfo(
        "escape",
        "Escape HTML special characters",
        source="jinja2",
        example="{{ user_input | escape }}",
    ),
    "urlencode": FilterInfo(
        "urlencode",
        "URL-encode string",
        source="jinja2",
        example="{{ query | urlencode }}",
    ),
    "filesizeformat": FilterInfo(
        "filesizeformat",
        "Format bytes as human-readable size",
        source="jinja2",
        example="{{ bytes | filesizeformat }}",
    ),
    "pprint": FilterInfo(
        "pprint",
        "Pretty-print for debugging",
        source="jinja2",
        example="{{ complex_var | pprint }}",
    ),
    "tojson": FilterInfo(
        "tojson",
        "Safe JSON for embedding in HTML/JS",
        source="jinja2",
        example="{{ data | tojson }}",
    ),
}


# =============================================================================
# Ansible Jinja2 Tests
# =============================================================================

JINJA_TESTS: dict[str, TestInfo] = {
    # Task result tests
    "failed": TestInfo(
        "failed",
        "True if task result indicates failure",
        example="when: result is failed",
    ),
    "succeeded": TestInfo(
        "succeeded",
        "True if task result indicates success",
        example="when: result is succeeded",
    ),
    "success": TestInfo(
        "success",
        "Alias for succeeded",
        example="when: result is success",
    ),
    "changed": TestInfo(
        "changed",
        "True if task result indicates change",
        example="when: result is changed",
    ),
    "skipped": TestInfo(
        "skipped",
        "True if task was skipped",
        example="when: result is skipped",
    ),
    "unreachable": TestInfo(
        "unreachable",
        "True if host was unreachable",
        example="when: result is unreachable",
    ),
    "reachable": TestInfo(
        "reachable",
        "True if host was reachable",
        example="when: result is reachable",
    ),
    "started": TestInfo(
        "started",
        "True if async task has started",
        example="when: async_result is started",
    ),
    "finished": TestInfo(
        "finished",
        "True if async task has finished",
        example="when: async_result is finished",
    ),
    # File tests
    "file": TestInfo(
        "file",
        "True if path is a regular file",
        example="when: path is file",
    ),
    "directory": TestInfo(
        "directory",
        "True if path is a directory",
        example="when: path is directory",
    ),
    "link": TestInfo(
        "link",
        "True if path is a symbolic link",
        example="when: path is link",
    ),
    "exists": TestInfo(
        "exists",
        "True if path exists",
        example="when: path is exists",
    ),
    "mount": TestInfo(
        "mount",
        "True if path is a mount point",
        example="when: path is mount",
    ),
    "abs": TestInfo(
        "abs",
        "True if path is absolute",
        example="when: path is abs",
    ),
    "same_file": TestInfo(
        "same_file",
        "True if two paths refer to same file",
        example="when: path1 is same_file(path2)",
    ),
    # Pattern matching
    "match": TestInfo(
        "match",
        "True if string matches regex at start",
        example="when: name is match('^prefix')",
    ),
    "search": TestInfo(
        "search",
        "True if string contains regex match",
        example="when: text is search('pattern')",
    ),
    "regex": TestInfo(
        "regex",
        "True if string matches full regex",
        example="when: value is regex('^\\\\d+$')",
    ),
    # Version comparison
    "version": TestInfo(
        "version",
        "Compare version strings",
        example="when: version is version('2.0', '>=')",
    ),
    "version_compare": TestInfo(
        "version_compare",
        "Alias for version test",
        example="when: ver is version_compare('1.0', '>')",
    ),
    # Collection tests
    "subset": TestInfo(
        "subset",
        "True if list is subset of another",
        example="when: small_list is subset(big_list)",
    ),
    "superset": TestInfo(
        "superset",
        "True if list is superset of another",
        example="when: big_list is superset(small_list)",
    ),
    "contains": TestInfo(
        "contains",
        "True if collection contains value",
        example="when: mylist is contains('item')",
    ),
    "all": TestInfo(
        "all",
        "True if all items are truthy",
        example="when: checks is all",
    ),
    "any": TestInfo(
        "any",
        "True if any item is truthy",
        example="when: options is any",
    ),
    # Boolean tests
    "truthy": TestInfo(
        "truthy",
        "True if value is truthy (not empty, false, none)",
        example="when: value is truthy",
    ),
    "falsy": TestInfo(
        "falsy",
        "True if value is falsy",
        example="when: value is falsy",
    ),
    # Type tests
    "vault_encrypted": TestInfo(
        "vault_encrypted",
        "True if value is vault-encrypted",
        example="when: secret is vault_encrypted",
    ),
    # Jinja2 builtins
    "defined": TestInfo(
        "defined",
        "True if variable is defined",
        source="jinja2",
        example="when: myvar is defined",
    ),
    "undefined": TestInfo(
        "undefined",
        "True if variable is undefined",
        source="jinja2",
        example="when: myvar is undefined",
    ),
    "none": TestInfo(
        "none",
        "True if value is None",
        source="jinja2",
        example="when: value is none",
    ),
    "boolean": TestInfo(
        "boolean",
        "True if value is a boolean",
        source="jinja2",
        example="when: flag is boolean",
    ),
    "integer": TestInfo(
        "integer",
        "True if value is an integer",
        source="jinja2",
        example="when: count is integer",
    ),
    "float": TestInfo(
        "float",
        "True if value is a float",
        source="jinja2",
        example="when: ratio is float",
    ),
    "number": TestInfo(
        "number",
        "True if value is numeric",
        source="jinja2",
        example="when: value is number",
    ),
    "string": TestInfo(
        "string",
        "True if value is a string",
        source="jinja2",
        example="when: name is string",
    ),
    "mapping": TestInfo(
        "mapping",
        "True if value is a dict/mapping",
        source="jinja2",
        example="when: config is mapping",
    ),
    "iterable": TestInfo(
        "iterable",
        "True if value is iterable",
        source="jinja2",
        example="when: items is iterable",
    ),
    "sequence": TestInfo(
        "sequence",
        "True if value is a sequence",
        source="jinja2",
        example="when: items is sequence",
    ),
    "callable": TestInfo(
        "callable",
        "True if value is callable",
        source="jinja2",
        example="when: func is callable",
    ),
    "sameas": TestInfo(
        "sameas",
        "True if values are same object",
        source="jinja2",
        example="when: a is sameas(b)",
    ),
    "escaped": TestInfo(
        "escaped",
        "True if value is escaped",
        source="jinja2",
        example="when: text is escaped",
    ),
    "in": TestInfo(
        "in",
        "True if value is in container",
        source="jinja2",
        example="when: item is in(mylist)",
    ),
    "eq": TestInfo(
        "eq",
        "True if values are equal",
        source="jinja2",
        example="when: value is eq(other)",
    ),
    "equalto": TestInfo(
        "equalto",
        "Alias for eq",
        source="jinja2",
        example="when: value is equalto(other)",
    ),
    "ne": TestInfo(
        "ne",
        "True if values are not equal",
        source="jinja2",
        example="when: value is ne(other)",
    ),
    "lt": TestInfo(
        "lt",
        "True if value is less than",
        source="jinja2",
        example="when: count is lt(10)",
    ),
    "le": TestInfo(
        "le",
        "True if value is less than or equal",
        source="jinja2",
        example="when: count is le(10)",
    ),
    "gt": TestInfo(
        "gt",
        "True if value is greater than",
        source="jinja2",
        example="when: count is gt(0)",
    ),
    "ge": TestInfo(
        "ge",
        "True if value is greater than or equal",
        source="jinja2",
        example="when: count is ge(1)",
    ),
    "even": TestInfo(
        "even",
        "True if number is even",
        source="jinja2",
        example="when: index is even",
    ),
    "odd": TestInfo(
        "odd",
        "True if number is odd",
        source="jinja2",
        example="when: index is odd",
    ),
    "divisibleby": TestInfo(
        "divisibleby",
        "True if number is divisible by N",
        source="jinja2",
        example="when: count is divisibleby(3)",
    ),
    "upper": TestInfo(
        "upper",
        "True if string is uppercase",
        source="jinja2",
        example="when: text is upper",
    ),
    "lower": TestInfo(
        "lower",
        "True if string is lowercase",
        source="jinja2",
        example="when: text is lower",
    ),
}


# =============================================================================
# Lookup Plugins
# =============================================================================

LOOKUP_NAMES: list[str] = [
    "config",
    "csvfile",
    "dict",
    "env",
    "file",
    "fileglob",
    "first_found",
    "indexed_items",
    "ini",
    "inventory_hostnames",
    "items",
    "lines",
    "list",
    "nested",
    "password",
    "pipe",
    "random_choice",
    "sequence",
    "subelements",
    "template",
    "together",
    "unvault",
    "url",
    "varnames",
    "vars",
]


# =============================================================================
# Helper Functions
# =============================================================================

def get_filter_names() -> list[str]:
    """Get list of all filter names."""
    return list(JINJA_FILTERS.keys())


def get_test_names() -> list[str]:
    """Get list of all test names."""
    return list(JINJA_TESTS.keys())


def get_filter_info(name: str) -> FilterInfo | None:
    """Get filter info by name."""
    return JINJA_FILTERS.get(name)


def get_test_info(name: str) -> TestInfo | None:
    """Get test info by name."""
    return JINJA_TESTS.get(name)
