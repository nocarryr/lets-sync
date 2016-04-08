import sys
import os
import io

from configobj import ConfigObj

from letssync.structures.base import Directory, FileObj

PY2 = sys.version_info.major == 2

class Renewals(Directory):
    """A directory containing renewal configuration

    Attributes:
        domains (dict): A dictionary containing discovered domain names as keys
            with their associated :class:`RenewalConf` objects as values
        accounts (dict): A dictionary mapping account_id's discovered from
            the configuration files as keys to the domains they are associated
            with as values (a :class:`list` of strings)
    """
    def __init__(self, **kwargs):
        self.domains = {}
        self.accounts = {}
        super(Renewals, self).__init__(**kwargs)
    @classmethod
    def _child_class_override(cls, child_class, **kwargs):
        parent = kwargs.get('parent')
        if kwargs.get('id') == 'renewal' and parent.parent is None:
            return Renewals
    def add_child(self, cls, **kwargs):
        cls = RenewalConf
        obj = super(Renewals, self).add_child(cls, **kwargs)
        self.domains[obj.domain] = obj
        if obj.account_id not in self.accounts:
            self.accounts[obj.account_id] = {}
        self.accounts[obj.account_id][obj.domain] = obj
        return obj


class RenewalConf(FileObj):
    """A renewal configuration file

    Attributes:
        account_id (str): The account_id contained in the config file
        domain (str): The domain name (discovered from the filename itself)
    """
    serialize_attrs = ['account_id', 'domain']
    def read(self, **kwargs):
        super(RenewalConf, self).read(**kwargs)
        if PY2 and not isinstance(self.content, unicode):
            b = io.BytesIO(self.content)
        else:
            b = io.StringIO(self.content)
        self.config = ConfigObj(b)
        self.account_id = kwargs.get('account_id')
        if self.account_id is None:
            try:
                self.account_id = self.config['renewalparams']['account']
            except TypeError:
                print(self.config['renewalparams'], type(self.config['renewalparams']))
                raise
        self.domain = kwargs.get('domain')
        if self.domain is None:
            self.domain = self.id.rstrip('.conf')
    def on_tree_built(self):
        accounts = self.root.children['accounts']
        self.account = accounts.accounts.get(self.account_id)
    def _write(self, overwrite=False):
        p = self.path
        if os.path.exists(p) and overwrite is False:
            return
        with open(self.path, 'wb') as f:
            self.config.write(f)
    def __eq__(self, other):
        return self.config.dict() == other.config.dict()
