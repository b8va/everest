"""
This file is part of the everest project. 
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 13, 2012.
"""
from everest.entities.base import Entity
from everest.entities.utils import new_entity_id
from everest.repositories.memory import Aggregate
from everest.repositories.memory import Repository
from everest.repositories.memory import Session
from everest.testing import Pep8CompliantTestCase
import gc

__docformat__ = 'reStructuredText en'
__all__ = ['JoinedTransactionMemorySessionTestCase',
           'TransactionLessMemorySessionTestCase',
           ]


class _MemorySessionTestCaseBase(Pep8CompliantTestCase):
    _session = None

    def test_basics(self):
        ent = _MyEntity()
        self.assert_is_none(ent.id)
        self.assert_is_none(ent.slug)
        self._session.add(_MyEntity, ent)
        self.assert_true(ent in self._session.get_all(_MyEntity))
        # .add triggered ID generation.
        self.assert_is_not_none(ent.id)
        self.assert_is_not_none(ent.slug)
        self.assert_equal(len(self._session.get_all(_MyEntity)), 1)
        self.assert_true(self._session.get_by_id(_MyEntity, ent.id) is ent)
        self.assert_true(
                        self._session.get_by_slug(_MyEntity, ent.slug) is ent)
        self._session.remove(_MyEntity, ent)
        self.assert_equal(len(list(self._session.iterator(_MyEntity))), 0)
        self.assert_is_none(self._session.get_by_id(_MyEntity, ent.id))
        self.assert_is_none(self._session.get_by_slug(_MyEntity, ent.slug))

    def test_remove_entity_not_in_session_raises_error(self):
        ent = _MyEntity()
        self.assert_raises(ValueError, self._session.remove, _MyEntity, ent)

    def test_replace_entity_not_in_session_raises_error(self):
        ent = _MyEntity()
        self.assert_raises(ValueError, self._session.replace, _MyEntity, ent)

    def test_get_entity_not_in_session(self):
        self.assert_is_none(self._session.get_by_id(_MyEntity, '-1'))


class JoinedTransactionMemorySessionTestCase(_MemorySessionTestCaseBase):
    def set_up(self):
        Pep8CompliantTestCase.set_up(self)
        self._repository = Repository('DUMMY', Aggregate,
                                      join_transaction=True)
        self._session = Session(self._repository)


class TransactionLessMemorySessionTestCase(_MemorySessionTestCaseBase):
    def set_up(self):
        Pep8CompliantTestCase.set_up(self)
        self._repository = Repository('DUMMY', Aggregate)
        self._session = Session(self._repository)

    def test_references(self):
        ent = _MyEntity()
        self._session.add(_MyEntity, ent)
        self.assert_equal(len(self._session.get_all(_MyEntity)), 1)
        # Even with the last external ref gone, the cache should hold a
        # reference to the entities it manages.
        del ent
        gc.collect()
        self.assert_equal(len(self._session.get_all(_MyEntity)), 1)

    def test_id_generation(self):
        ent1 = _MyEntity()
        self._session.add(_MyEntity, ent1)
        ent2 = _MyEntity()
        self._session.add(_MyEntity, ent2)
        self.assert_is_not_none(ent1.id)
        self.assert_is_not_none(ent2.id)
        # entity IDs can be sorted by creation time.
        self.assert_true(ent2.id > ent1.id)

    def test_with_id_without_slug(self):
        ent = _MyEntityNoneSlug(id=0)
        self._session.add(_MyEntityNoneSlug, ent)
        self.assert_true(self._session.get_by_id(_MyEntityNoneSlug, 0) is ent)

    def test_without_id_with_slug(self):
        ent = _MyEntityWithSlug()
        self._session.add(_MyEntityWithSlug, ent)
        self.assert_true(self._session.get_by_slug(_MyEntityWithSlug, 'slug')
                         is ent)

    def test_duplicate_id_raises_error(self):
        ent_id = new_entity_id()
        ent1 = _MyEntity(id=ent_id)
        self._session.add(_MyEntity, ent1)
        ent2 = _MyEntity(id=ent_id)
        self.assert_raises(ValueError, self._session.add, _MyEntity, ent2)

    def test_duplicate_slug_raises_error(self):
        ent1 = _MyEntityWithSlug()
        self._session.add(_MyEntityWithSlug, ent1)
        ent2 = _MyEntityWithSlug()
        self.assert_raises(ValueError,
                           self._session.add, _MyEntityWithSlug, ent2)

    def test_cope_with_numeric_id(self):
        ent = _MyEntity(id=0)
        self._session.add(_MyEntity, ent)
        self.assert_equal(self._session.get_by_id(_MyEntity, ent.id).id,
                          ent.id)
        self.assert_equal(self._session.get_by_slug(_MyEntity, ent.slug).id,
                          ent.id)

    def test_repeated_add_remove(self):
        ent1 = _MyEntityWithSlug()
        self._session.add(_MyEntity, ent1)
        self.assert_true(self._session.get_by_slug(_MyEntity, ent1.slug)
                         is ent1)
        self._session.remove(_MyEntity, ent1)
        self.assert_is_none(self._session.get_by_slug(_MyEntity, ent1.slug))
        ent2 = _MyEntityWithSlug()
        self._session.add(_MyEntity, ent2)
        self.assert_true(self._session.get_by_slug(_MyEntity, ent2.slug)
                         is ent2)
        self._session.remove(_MyEntity, ent2)
        self.assert_is_none(self._session.get_by_slug(_MyEntity, ent2.slug))
        self.assert_true(ent1.id != ent2.id)

    def test_remove_(self):
        ent = _MyEntity()
        self._session.add(_MyEntity, ent)
        self._session.remove(_MyEntity, ent)
        self.assert_equal(len(self._session.get_all(_MyEntity)), 0)

    def test_add_remove_add(self):
        ent1 = _MyEntityWithSlug()
        self._session.add(_MyEntity, ent1)
        ent_id = ent1.id
        self._session.commit()
        self._session.remove(_MyEntity, ent1)
        self._session.add(_MyEntity, ent1)
        self.assert_equal(ent1.id, ent_id)

    def test_replace_without_id_raises_error(self):
        ent1 = _MyEntity(id=0)
        self._session.add(_MyEntity, ent1)
        self._session.commit()
        ent2 = self._session.get_by_id(_MyEntity, 0)
        ent2.id = None
        with self.assert_raises(ValueError) as cm:
            self._session.commit()
        exc_msg = 'Entity ID must not be None.'
        self.assert_equal(str(cm.exception), exc_msg)

    def test_replace_with_different_slug(self):
        ent1 = _MyEntityWithSlug()
        self._session.add(_MyEntityWithSlug, ent1)
        ent_id = ent1.id
        self._session.commit()
        ent2 = self._session.get_by_id(_MyEntityWithSlug, ent_id)
        ent2.slug = 'foo'
        self._session.commit()
        ent3 = self._session.get_by_slug(_MyEntityWithSlug, 'foo')
        self.assert_equal(ent3.id, ent_id)

    def test_failing_commit_duplicate_id(self):
        ent1 = _MyEntity()
        self._session.add(_MyEntity, ent1)
        ent2 = _MyEntity()
        self._session.add(_MyEntity, ent2)
        ent2.id = ent1.id
        self.assert_raises(ValueError, self._session.commit)

    def test_failing_add_commit_none_id(self):
        ent = _MyEntity()
        self._session.add(_MyEntity, ent)
        ent.id = None
        self.assert_raises(ValueError, self._session.commit)

    def test_failing_add_commit_remove_none_id(self):
        ent = _MyEntity()
        self._session.add(_MyEntity, ent)
        self._session.commit()
        self._session.remove(_MyEntity, ent)
        ent.id = None
        self.assert_raises(ValueError, self._session.commit)

    def test_failing_flush_duplicate_slug(self):
        ent1 = _MyEntityWithSlug()
        self._session.add(_MyEntity, ent1)
        ent2 = _MyEntityWithSlug()
        ent2.slug = None
        self._session.add(_MyEntity, ent2)
        ent2.slug = 'slug'
        self.assert_raises(ValueError, self._session.commit)

    def test_find_added_by_id(self):
        ent1 = _MyEntityWithSlug()
        self._session.add(_MyEntity, ent1)
        ent2 = self._session.get_by_id(_MyEntity, ent1.id)
        self.assert_is_not_none(ent2)
        self.assert_equal(ent1.id, ent2.id)

    def test_find_added_by_slug(self):
        ent1 = _MyEntityWithSlug()
        self._session.add(_MyEntity, ent1)
        ent2 = self._session.get_by_slug(_MyEntity, ent1.slug)
        self.assert_is_not_none(ent2)
        self.assert_equal(ent1.id, ent2.id)

    def test_find_added_with_none_slug_by_slug(self):
        ent1 = _MyEntityNoneSlug()
        self._session.add(_MyEntity, ent1)
        ent1.slug = 'testslug'
        ent2 = self._session.get_by_slug(_MyEntity, ent1.slug)
        self.assert_is_not_none(ent2)
        self.assert_equal(ent1.id, ent2.id)

    def test_replace(self):
        ent1 = _MyEntity()
        self._session.add(_MyEntity, ent1)
        ent2 = _MyEntity()
        ent2.id = ent1.id
        my_attr_value = 1
        ent2.my_attr = my_attr_value
        self._session.replace(_MyEntity, ent2)
        ent3 = self._session.get_by_id(_MyEntity, ent1.id)
        self.assert_is_not_none(ent3)
        self.assert_equal(ent3.id, ent1.id)
        self.assert_equal(ent3.my_attr, my_attr_value)


class _MyEntity(Entity):
    my_attr = None


class _MyEntityWithSlug(Entity):
    slug = 'slug'


class _MyEntityNoneSlug(Entity):
    slug = None
