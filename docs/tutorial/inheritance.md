## Inheritance for multi-model use case

Beanie `Documents` support inheritance as any other Python classes. But there are additional features available if you mark the root model with the parameter `is_root = True` in the inner Settings class.

This behavior is similar to `UnionDoc`, but you don't need an additional entity.
Parent `Document` act like a "controller", that handles proper storing and fetches different `Document` types.
Also, parent `Document` can have some shared attributes which are propagated to all children.
All classes in the inheritance chain can be used as `Link` in foreign `Documents`.

Depending on the business logic, parent `Document` can be like an "abstract" class that is not used to store objects of its type (like in the example below), as well as can be a full-fledged entity, like its children.

### Defining models

To set the root model you have to set `is_root = True` in the inner Settings class. All the inherited documents (on any level) will be stored in the same collection.

```py hl_lines="20 20"
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from beanie import Document, Link, init_beanie


class Vehicle(Document):
    """Inheritance scheme bellow"""
    #               Vehicle
    #              /   |   \
    #             /    |    \
    #        Bicycle  Bike  Car
    #                         \
    #                          \
    #                          Bus
    # shared attribute for all children
    color: str
    
    class Settings:
        is_root = True


class Fuelled(BaseModel):
    """Just a mixin"""
    fuel: Optional[str]


class Bicycle(Vehicle):
    """Derived from Vehicle, will use its collection"""
    frame: int
    wheels: int


class Bike(Vehicle, Fuelled):
    ...


class Car(Vehicle, Fuelled):
    body: str


class Bus(Car, Fuelled):
    """Inheritance chain is Vehicle -> Car -> Bus, it is also stored in Vehicle collection"""
    seats: int
    
    
class Owner(Document):
    vehicles: Optional[List[Link[Vehicle]]]
```

### Inserts

Inserts work the same way as usual

```python
client = AsyncIOMotorClient()
await init_beanie(client.test_db, document_models=[Vehicle, Bicycle, Bike, Car, Bus])

bike_1 = await Bike(color='black', fuel='gasoline').insert()

car_1 = await Car(color='grey', body='sedan', fuel='gasoline').insert()
car_2 = await Car(color='white', body='crossover', fuel='diesel').insert()

bus_1 = await Bus(color='white', seats=80, body='bus', fuel='diesel').insert()
bus_2 = await Bus(color='yellow', seats=26, body='minibus', fuel='diesel').insert()

owner = await Owner(name='John', vehicles=[car_1, car_2, bus_1]).insert()
```

### Find operations

With parameter `with_children = True` the find query results will contain all the children classes' objects.

```python
# this query returns vehicles of all types that have white color, becuase `with_children` is True
white_vehicles = await Vehicle.find(Vehicle.color == 'white', with_children=True).to_list()
# [
#    Bicycle(..., color='white', frame=54, wheels=29),
#    Car(fuel='diesel', ..., color='white', body='crossover'),
#    Bus(fuel='diesel', ..., color='white', body='bus', seats=80)
# ]
```

If the search is based on a child, the query returns this child type and all sub-children (with parameter `with_children=True`)

```python
cars_and_buses = await Car.find(Car.fuel == 'diesel', with_children=True).to_list()
# [
#     Car(fuel='diesel', ..., color='white', body='crossover'),
#     Bus(fuel='diesel', ..., color='white', body='bus', seats=80),
#     Bus(fuel='diesel', ..., color='yellow', body='minibus', seats=26)
# ]
```

If you need to return objects of the specific class only, you can use this class for finding:

```python
# however it is possible to limit by Vehicle type
cars_only = await Car.find().to_list()
# [
#     Car(fuel='gasoline', ..., color='grey', body='sedan'),
#     Car(fuel='diesel', ..., color='white', body='crossover')
# ]
```

To get a single Document it is not necessary to know the type. You can query using the parent class

```python
await Vehicle.get(bus_2.id, with_children=True)
# returns Bus instance:
# Bus(fuel='diesel', ..., color='yellow', body='minibus', seats=26)
```

To delete all Documents in an inheritance tree, you can search with `with_children=True` and then delete:

```python
await Vehicle.find_all(with_children=True).delete()
# will delete documents matching Vehicle, Car, Bus, etc ..
# use with care!
```

Or `with_children=True` can be passed directly to `delete_all()`:

```python
await Vehicle.delete_all(with_children=True)
# will delete documents matching Vehicle, Car, Bus, etc ..
# use with care!
```

### Relations

Linked documents will be resolved into the respective classes

```python
owner = await Owner.get(owner.id, fetch_links=True)

print(owner.vehicles)
# [
#    Car(fuel='diesel', ..., color='white', body='crossover'),
#    Bus(fuel='diesel', ..., color='white', body='bus', seats=80),
#    Car(fuel='gasoline', ..., color='grey', body='sedan')
# ]
```

The same result will be if the owner gets objects without fetching the links, and they will be fetched manually later

### Other

All other operations work the same way as for simple Documents

```python
await Bike.find().update({"$set": {Bike.color: 'yellow'}})
await Car.find_one(Car.body == 'sedan')
```
