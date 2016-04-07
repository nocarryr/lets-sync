from letssync.structures import base
from letssync.structures import account
from letssync.structures import renewal

def build_tree(root_path):
    return base.Directory(path=root_path)
