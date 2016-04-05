import os
import json

from letssync.structures.base import Directory, FileObjBase


class Accounts(Directory):
    @property
    def accounts(self):
        a = getattr(self, '_accounts', None)
        if a is None:
            p = self.parent
            if not isinstance(p, Accounts):
                a = self._accounts = {}
            else:
                a = p.accounts
        return a
    @classmethod
    def _child_class_override(cls, child_class, **kwargs):
        parent = kwargs.get('parent')
        if kwargs.get('id') == 'accounts' and parent.parent is None:
            return Accounts
        elif parent.__class__ is Accounts and child_class is Directory:
            return Accounts
    def add_child(self, cls, **kwargs):
        child = super(Accounts, self).add_child(cls, **kwargs)
        if isinstance(child, Account):
            self.add_account(child)
        return child
    def add_account(self, obj):
        if obj.id not in self.accounts:
            self.accounts[obj.id] = obj
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if other.relative_path != self.relative_path:
            return False
        return set(self.accounts.keys()) == set(other.accounts.keys())

class Account(Directory):
    serialize_attrs = ['meta', 'private_key', 'regr']
    @classmethod
    def _child_class_override(cls, child_class, **kwargs):
        parent = kwargs.get('parent')
        if parent.id == 'directory' and parent.__class__ is Accounts:
            return Account
    def add_child(self, cls, **kwargs):
        cls = AccountFile
        obj = super(Account, self).add_child(cls, **kwargs)
        attr = os.path.splitext(obj.id)[0]
        setattr(self, attr, obj.data)
        return obj


class AccountFile(FileObjBase):
    serialize_attrs = ['data']
    def read(self, **kwargs):
        self.data = kwargs.get('data')
        if self.data is not None:
            kwargs.setdefault('content', json.dumps(self.data))
        super(AccountFile, self).read(**kwargs)
        if self.data is None:
            self.data = json.loads(self.content)
    def _get_diff(self, other, reverse=False):
        d = super(AccountFile, self)._get_diff(other, reverse)
        if other is None:
            return d
        selfkey = 'self'
        othkey = 'other'
        if reverse:
            selfkey = 'other'
            othkey = 'self'
        if self.data != other.data:
            d['data'] = {selfkey:self.data, othkey:other.data}
        return d
    def __eq__(self, other):
        if not isinstance(other, AccountFile):
            return False
        return other.data == self.data
