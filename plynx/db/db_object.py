import datetime
from abc import ABCMeta, abstractmethod
from collections import namedtuple
from plynx.utils.db_connector import db
from plynx.utils.common import ObjectId

DBObjectField = namedtuple('DBObjectField', ['type', 'default', 'is_list'])


class DBObjectNotFound(Exception):
    """Internal Exception."""
    pass


class ClassNotSavable(Exception):
    """Internal Exception."""
    pass


class DBObject(object):
    """DB Object.
    Abstraction of an object in the DB.

    Args:
        obj_dict    (dict, None):   Representation of the object. If None, an object with default fields will be created.
    """

    FIELDS = {}
    DB_COLLECTION = ''

    def __init__(self, obj_dict=None):
        self.__init_fields(obj_dict)
        self._dirty = True

    def is_dirty(self):
        return self._dirty

    def __setattr__(self, key, value):
        self.__dict__['_dirty'] = True
        self.__dict__[key] = value

    def __init_fields(self, obj_dict):
        obj_dict = obj_dict or {}
        for field_name, object_field in self.FIELDS.iteritems():
            obj_value = obj_dict.get(field_name, None)
            if obj_value:
                if object_field.is_list:
                    value = [
                        object_field.type(v) for v in obj_value
                    ]
                else:
                    value = object_field.type(obj_value)
            else:
                # Use default value
                value = object_field.default() if callable(object_field.default) else object_field.default
            setattr(self, field_name, value)

    @classmethod
    def load(cls, _id):
        """Load object from db.

        Args:
            _id     (str, ObjectId):    ID of the object in DB
        """
        obj_dict = getattr(db, cls.DB_COLLECTION).find_one({'_id': ObjectId(_id)})
        if not obj_dict:
            raise DBObjectNotFound(
                'Object `{_id}` not found in `{collection}` collection'.format(
                    _id=_id,
                    collection=cls.DB_COLLECTION,
                )
            )
        return cls.from_dict(obj_dict)

    def save(self, force=False):
        """"""
        if not self.__class__.DB_COLLECTION:
            raise ClassNotSavable(
                "Class `{}` is not savable.".format(
                    self.__class__.__name__
                )
            )
        if not self.is_dirty() and not force:
            return True

        now = datetime.datetime.utcnow()

        obj_dict = self.to_dict()
        obj_dict["update_date"] = now

        getattr(db, self.__class__.DB_COLLECTION).find_one_and_update(
            {'_id': obj_dict['_id']},
            {
                "$setOnInsert": {"insertion_date": now},
                "$set": obj_dict
            },
            upsert=True,
        )

        self._dirty = False
        return True

    @classmethod
    def from_dict(cls, obj_dict):
        """Create object from dict representation.

        Args:
            obj_dict    (dict):     Representation of the object,
                                    i.e. {'name': 'Obj Name', 'size': 12}

        """
        return cls(obj_dict)

    @staticmethod
    def __to_dict_single_element(value):
        if isinstance(value, DBObject):
            return value.to_dict()
        return value

    def to_dict(self):
        """Create a dictionary from an object."""
        res = {}
        for field_name, object_field in self.FIELDS.iteritems():
            if object_field.is_list:
                value = [
                    self.__to_dict_single_element(element) for element in getattr(self, field_name)
                ]
            else:
                value = self.__to_dict_single_element(getattr(self, field_name))
            res[field_name] = value
        return res

    def copy(self):
        """Make a copy

        Returns:
            A copy of the Object
        """
        return self.__class__(self.to_dict())

    """
    TODO REMOVE?
    def __getattr__(self, name):
        if name.startswith('__') and name.endswith('__'):
            return super(NodeCache, self).__getattr__(name)
        raise Exception("Can't get attribute '{}'".format(name))
    """
