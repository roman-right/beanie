# Relations

The document can contain links to other documents in their fields.

*Only top-level fields are fully supported for now.*

The following field types are supported:

- `Link[...]`
- `Optional[Link[...]]`
- `List[Link[...]]`
- `Optional[List[Link[...]]]`

Also, backward links are supported:

- `BackLink[...]`
- `Optional[BackLink[...]]`
- `List[BackLink[...]]`
- `Optional[List[BackLink[...]]]`

Direct link to the document:

```python
from beanie import Document, Link


class Door(Document):
    height: int = 2
    width: int = 1


class House(Document):
    name: str
    door: Link[Door]
```

Optional direct link to the document:

```python
from typing import Optional

from beanie import Document, Link


class Door(Document):
    height: int = 2
    width: int = 1


class House(Document):
    name: str
    door: Optional[Link[Door]]
```

List of the links:

```python
from typing import List

from beanie import Document, Link


class Window(Document):
    x: int = 10
    y: int = 10


class House(Document):
    name: str
    door: Link[Door]
    windows: List[Link[Window]]
```

Optional list of the links:

```python
from typing import List, Optional
 
from beanie import Document, Link
 
class Window(Document):
    x: int = 10
    y: int = 10
 
class Yard(Document):
    v: int = 10
    y: int = 10
 
class House(Document):
    name: str
    door: Link[Door]
    windows: List[Link[Window]]
    yards: Optional[List[Link[Yard]]]
```

Other link patterns are not supported at this moment. If you need something more specific for your use-case, 
please open an issue on the GitHub page - <https://github.com/roman-right/beanie>

## Write

The following write methods support relations:

- `insert(...)`
- `replace(...)`
- `save(...)`

To apply a write method to the linked documents, you should pass the respective `link_rule` argument

```python
house.windows = [Window(x=100, y=100)]
house.name = "NEW NAME"

# The next call will insert a new window object and replace the house instance with updated data
await house.save(link_rule=WriteRules.WRITE)

# `insert` and `replace` methods will work the same way
```

Otherwise, Beanie can ignore internal links with the `link_rule` parameter `WriteRules.DO_NOTHING`

```python
house.door.height = 3
house.name = "NEW NAME"

# The next call will just replace the house instance with new data, but the linked door object will not be synced
await house.replace(link_rule=WriteRules.DO_NOTHING)

# `insert` and `save` methods will work the same way
```

## Fetch

### Prefetch

You can fetch linked documents on the find query step using the `fetch_links` parameter 

```python
houses = await House.find(
    House.name == "test", 
    fetch_links=True
).to_list()
```
Supported find methods:
- `find`
- `find_one`
- `get`

Beanie uses the single aggregation query under the hood to fetch all the linked documents. 
This operation is very effective.

If a direct link is referred to a non-existent document, 
after fetching it will remain the object of the `Link` class.

Fetching will ignore non-existent documents for the list of links fields.

#### Search by linked documents fields

If the `fetch_links` parameter is set to `True`, search by linked documents fields is available.

By field of the direct link:

```python
houses = await House.find(
    House.door.height == 2,
    fetch_links=True
).to_list()
```

By list of links:

```python
houses = await House.find(
    House.windows.x > 10,
    fetch_links=True
).to_list()
```

Search by `id` of the linked documents works using the following syntax:

```python
houses = await House.find(
    House.door.id == "DOOR_ID_HERE"
).to_list()
```

It works the same way with `fetch_links` equal to `True` and `False` and for `find_many` and `find_one` methods.

#### Nested links

With Beanie you can set up nested links. Document can even link to itself. This can lead to infinite recursion. To prevent this, or to decrease the database load, you can limit the nesting depth during find operations.

```python
from beanie import Document, Link
from typing import Optional

class SelfLinkedSample(Document):
    name: str
    left: Optional[Link["SelfLinkedSample"]]
    right: Optional[Link["SelfLinkedSample"]]
```

You can set up depth for all linked documents independently of the field:

```python

await SelfLinkedSample.find(
    SelfLinkedSample.name == "test",
    fetch_links=True,
    nesting_depth=2
).to_list()
```

Or you can set up depth for a specific field:

```python
await SelfLinkedSample.find(
    SelfLinkedSample.name == "test",
    fetch_links=True,
    nesting_depths_per_field={
        "left": 1,
        "right": 2
    }
).to_list()
```

Also, you can set up the maximum nesting depth on the document definition level. You can read more about this [here](/tutorial/defining-a-document/#nested-documents-depth).

### On-demand fetch

If you don't use prefetching, linked documents will be presented as objects of the `Link` class. 

You can fetch them manually afterwards.

To fetch all the linked documents, you can use the `fetch_all_links` method

```python
await house.fetch_all_links()
```

It will fetch all the linked documents and replace `Link` objects with them.

Otherwise, you can fetch a single field:

```python
await house.fetch_link(House.door)
```

This will fetch the Door object and put it into the `door` field of the `house` object.

## Delete

Delete method works the same way as write operations, but it uses other rules.

To delete all the links on the document deletion, 
you should use the `DeleteRules.DELETE_LINKS` value for the `link_rule` parameter:

```python
await house.delete(link_rule=DeleteRules.DELETE_LINKS)
```

To keep linked documents, you can use the `DO_NOTHING` rule:

```python
await house.delete(link_rule=DeleteRules.DO_NOTHING)
```

## Back Links

To init the back link you should have a document with the direct or list of links to the current document.

```python
from typing import List

from beanie import Document, BackLink, Link
from pydantic import Field


class House(Document):
    name: str
    door: Link["Door"]
    owners: List[Link["Person"]]

    
class Door(Document):
    height: int = 2
    width: int = 1
    house: BackLink[House] = Field(original_field="door")

    
class Person(Document):
    name: str
    house: List[BackLink[House]] = Field(original_field="owners")
```

The `original_field` parameter is required for the back link field.

Back links support all the operations that normal links support, but are virtual. This means that when searching the database, you will need to include `fetch_links=True` (see [Finding documents](find.md)), or you will recieve an empty 'BackLink' virtual object. It is not possible to `fetch()` this virtual link after the initial search.

## Limitations

- Find operations with the `fetch_links` parameter can not be used in the chaning with `delete` and `update` methods.
