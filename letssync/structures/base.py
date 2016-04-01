import os
import json

class Path(object):
    serialize_attrs = ['path', 'mode', 'id', 'modified']
    def __init__(self, **kwargs):
        self.children = {}
        self.path = kwargs.get('path')
        self.mode = kwargs.get('mode')
        if self.mode is None:
            self.mode = os.stat(self.path).st_mode
        self.modified = kwargs.get('modified')
        if self.modified is None:
            self.modified = os.stat(self.path).st_mtime
        self.id = kwargs.get('id', self.path)
        self.parent = kwargs.get('parent')
        self.is_serialized = kwargs.get('is_serialized', False)
        if self.is_serialized:
            self.deserialize_children(**kwargs)
        else:
            self.find_children()
        if self.parent is None:
            self.on_tree_built()
    @property
    def path(self):
        return getattr(self, '_path', None)
    @path.setter
    def path(self, value):
        if value == self.path:
            return
        self._path = value
        for child in self.children.values():
            child.update_path()
    @property
    def root(self):
        if self.parent is None:
            return self
        return self.parent.root
    @property
    def relative_path(self):
        p = getattr(self, '_relative_path', None)
        if p is None:
            if self.parent is None:
                p = ''
            else:
                p = os.path.join(self.parent.relative_path, self.id)
            self._relative_path = p
        return p
    @classmethod
    def get_serialize_attrs(cls):
        def iter_bases(_cls=None):
            if _cls is None:
                _cls = cls
            yield _cls
            for base_cls in _cls.__bases__:
                if not issubclass(base_cls, Path):
                    continue
                if base_cls is object:
                    continue
                for _cls_ in iter_bases(base_cls):
                    yield _cls_
        attrs = set()
        for _cls in iter_bases():
            if 'serialize_attrs' not in _cls.__dict__:
                continue
            attrs |= set(_cls.serialize_attrs)
        return attrs
    @classmethod
    def find_subclass(cls, name):
        def search(cls):
            if cls.__name__ == name:
                return cls
            for _cls in cls.__subclasses__():
                r = search(_cls)
                if r is not None:
                    return r
            return None
        return search(Path)
    @classmethod
    def _child_class_override(cls, child_class, **kwargs):
        def get_last_cls(_cls=None):
            if _cls is None:
                _cls = cls
            if not len(_cls.__subclasses__()):
                yield _cls
                raise StopIteration()
            for subcls in _cls.__subclasses__():
                for last_cls in get_last_cls(subcls):
                    yield last_cls
        for _cls in reversed(list(get_last_cls())):
            if '_child_class_override' not in _cls.__dict__:
                continue
            if _cls is cls:
                continue
            _child_class = _cls._child_class_override(child_class, **kwargs)
            if _child_class is not None:
                return _child_class
        return child_class
    @classmethod
    def from_json(cls, s):
        d = json.loads(s)
        _cls = cls.find_subclass(d['class_name'])
        d['is_serialized'] = True
        return _cls(**d)
    def search(self, path):
        if not isinstance(path, list):
            path = path.split(os.sep)
        key = path[0]
        try:
            path = path[1:]
        except IndexError:
            path = None
        child = self.children.get(key)
        if child is not None:
            if not path:
                return child
            else:
                return child.search(path)
        else:
            return None
    def update_path(self):
        root_path = self.root.path
        new_path = os.path.join(self.relative_path, root_path)
        self.path = new_path
    def find_children(self):
        pass
    def add_child(self, cls, **kwargs):
        kwargs.setdefault('parent', self)
        kwargs.setdefault('is_serialized', self.is_serialized)
        if not self.is_serialized:
            cls = cls._child_class_override(cls, **kwargs)
        child = cls(**kwargs)
        self.children[child.id] = child
        return child
    def to_json(self):
        d = self.root.serialize()
        return json.dumps(d, indent=2)
    def serialize(self):
        d = self._serialize()
        d['children'] = {}
        for key, val in self.children.items():
            d['children'][key] = val.serialize()
        return d
    def _serialize(self):
        attrs = self.get_serialize_attrs()
        d = {attr: getattr(self, attr) for attr in attrs}
        d['class_name'] = self.__class__.__name__
        return d
    def deserialize_children(self, **kwargs):
        children = kwargs.get('children', {})
        for key, val in children.items():
            cls = self.find_subclass(val['class_name'])
            self.add_child(cls, **val)
    def on_tree_built(self):
        for child in self.children.values():
            child.on_tree_built()
    def rebuild(self, root_path):
        root = self.root
        root._rebuild(root_path)
    def _rebuild(self, root_path):
        for child in self.children.values():
            child._rebuild(root_path)
    def copy(self, root_path=None):
        kwargs = self.serialize()
        kwargs['is_serialized'] = True
        new_obj = self.__class__(**kwargs)
        if root_path is not None:
            p = self.relative_path
            new_obj.path = os.path.join(root_path, p)
        return new_obj
    def __repr__(self):
        s = '<{0}: {1} at {2:#x}>'
        return s.format(self.__class__.__name__, self, id(self))
    def __str__(self):
        return self.path

class Directory(Path):
    def add_subdirectory(self, fn, cls=None):
        if cls is None:
            cls = Directory
        if os.path.dirname(fn) != self.path:
            fn = os.path.join(self.path, fn)
        return self.add_child(cls, path=fn)
    def add_file(self, fn, cls=None):
        if cls is None:
            cls = FileObj
        if os.path.dirname(fn) != self.path:
            fn = os.path.join(self.path, fn)
        return self.add_child(cls, path=fn)
    def add_link(self, fn, cls=None):
        if cls is None:
            cls = Link
        if os.path.dirname(fn) != self.path:
            fn = os.path.join(self.path, fn)
        return self.add_child(cls, path=fn)
    def add_child(self, cls, **kwargs):
        kwargs.setdefault('id', os.path.basename(kwargs.get('path')))
        return super(Directory, self).add_child(cls, **kwargs)
    def find_children(self):
        for fn in os.listdir(self.path):
            p = os.path.join(self.path, fn)
            if os.path.isdir(p):
                self.add_subdirectory(p)
            elif os.path.islink(p):
                self.add_link(p)
            elif os.path.isfile(p):
                self.add_file(p)
    def _rebuild(self, root_path):
        p = os.path.join(root_path, self.relative_path)
        if not os.path.exists(p):
            os.makedirs(p)
        os.chmod(p, self.mode)
        super(Directory, self)._rebuild(root_path)

class FileObjBase(Path):
    def __init__(self, **kwargs):
        super(FileObjBase, self).__init__(**kwargs)
        self.content = kwargs.get('content')
        if self.content is None:
            with open(self.path, 'r') as f:
                self.content = f.read()

class FileObj(FileObjBase):
    serialize_attrs = ['content']
    def _rebuild(self, root_path):
        p = os.path.join(root_path, self.relative_path)
        with open(p, 'w') as f:
            f.write(self.content)
        os.chmod(p, self.mode)
        super(FileObj, self)._rebuild(root_path)

class Link(FileObjBase):
    serialize_attrs = ['linked_path']
    def __init__(self, **kwargs):
        super(Link, self).__init__(**kwargs)
        self.linked_path = kwargs.get('linked_path')
        if self.linked_path is None:
            self.linked_path = os.readlink(self.path)
    @property
    def content(self):
        obj = getattr(self, 'linked_obj', None)
        if obj is not None:
            return obj.content
        return ''
    @content.setter
    def content(self, value):
        if value is None:
            return
        obj = getattr(self, 'linked_obj', None)
        if obj is not None:
            obj.content = value
    def on_tree_built(self):
        p = self.linked_path
        obj = self.parent
        while p.startswith(os.path.pardir):
            obj = obj.parent
            p = p.lstrip(os.path.pardir).lstrip(os.sep)
        self.linked_obj = obj.search(p)
        super(Link, self).on_tree_built()
    def _rebuild(self, root_path):
        p = os.path.join(root_path, self.relative_path)
        l = os.path.join(root_path, self.linked_obj.relative_path)
        l = os.path.relpath(l, os.path.dirname(p))
        if not os.path.exists(l):
            if not os.path.exists(os.path.dirname(l)):
                os.makedirs(os.path.dirname(l))
            os.mknod(l)
        os.symlink(l, p)
        super(Link, self)._rebuild(root_path)
