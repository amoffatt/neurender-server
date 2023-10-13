from typing import Type, Union, Annotated, List
from pydantic import BaseModel, Field
from pydantic_core import core_schema

def inject_classname_field(cls:BaseModel, field_name:str):
    '''
        Inject a field into cls's pydantic schema
        to be used as a descriptor while deserializing.
        Used by pydantic to select the right class from a Union
        to deserialize an item into
    '''
    class_name = cls.__name__
    schema = cls.__pydantic_core_schema__
    field_schema = core_schema.model_field(
        core_schema.with_default_schema(
            schema=core_schema.literal_schema(
                expected=[class_name]
            ),
            default=class_name,
        )
    )
    schema['schema']['fields'][field_name] = field_schema

def pydantic_union(types:List[Type], descriptor_field='model_type') -> Type:
    '''
    In order for pydantic to distinguish which class should be instantiated
    during deserialization, we must inject a custom field into the class's 
    pydantic schema which stores the expected value for a special descriminator_field
    with value set to the class's name
    '''
    for t in types:
        inject_classname_field(t, descriptor_field)
    union = Union.__getitem__(tuple(types))
    annotated = Annotated[union, Field(discriminator=descriptor_field)]
    return annotated

def pydantic_subclassof(_type:Type, descriptor_field='model_type') -> Type:
    return pydantic_union(subclasses(_type), descriptor_field=descriptor_field)


def subclasses(_type:Type):
    _subclasses = list(_type.__subclasses__())
    return _subclasses + sum([subclasses(s) for s in _subclasses], [])