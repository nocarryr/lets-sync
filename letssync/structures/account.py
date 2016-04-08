import os
import json

from letssync.structures.base import Directory, FileObjBase


class Accounts(Directory):
    """A directory that keeps track of account information

    Attributes:
        accounts (dict): A dictionary containing all discovered accounts.
            Only one instance of :class:`Accounts` will hold the :class:`dict`
            object, all others will reference it indirectly.
    """
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
    """Holds data stored with an account with its associated
    :attr:`~letssync.structures.base.Path.id`
    Data is read from the files within the account directory:
    'meta.json', 'private_key.json' and 'regr.json'
    """
    serialize_attrs = ['meta', 'private_key', 'regr', 'domains']
    @classmethod
    def _child_class_override(cls, child_class, **kwargs):
        parent = kwargs.get('parent')
        if parent.id == 'directory' and parent.__class__ is Accounts:
            return Account
    def read(self, **kwargs):
        super(Account, self).read(**kwargs)
        self.domains = kwargs.get('domains', [])
    def add_child(self, cls, **kwargs):
        cls = AccountFile
        obj = super(Account, self).add_child(cls, **kwargs)
        attr = os.path.splitext(obj.id)[0]
        setattr(self, attr, obj.data)
        return obj
    def on_tree_built(self):
        renewal = self.root.children['renewal']
        for key in renewal.accounts[self.id].keys():
            if key in self.domains:
                continue
            self.domains.append(key)
    def __eq__(self, other):
        r = super(Account, self).__eq__(other)
        if not r:
            return False
        return set(self.domains) == set(other.domains)

class AccountFile(FileObjBase):
    """A file used to read and store data used in :class:`Account`
    """
    serialize_attrs = ['data']
    def read(self, **kwargs):
        self.data = kwargs.get('data')
        if self.data is not None:
            kwargs.setdefault('content', json.dumps(self.data))
        super(AccountFile, self).read(**kwargs)
        if self.data is None:
            self.data = json.loads(self.content)
    def _get_diff(self, other, other_name):
        d = super(AccountFile, self)._get_diff(other, other_name)
        if other is None:
            return d
        if self.data != other.data:
            d['data'] = {self.name:self.data, other_name:other.data}
        return d
    def __eq__(self, other):
        if not isinstance(other, AccountFile):
            return False
        return other.data == self.data
