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
    def __init__(self, **kwargs):
        self.data = kwargs.get('data')
        if self.data is not None:
            kwargs.setdefault('content', json.dumps(self.data))
        super(AccountFile, self).__init__(**kwargs)
        if self.data is None:
            self.data = json.loads(self.content)
