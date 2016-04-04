
def test_build_tree(conf_dir):
    from letssync.structures import build_tree
    r = build_tree(str(conf_dir['root_path']))
