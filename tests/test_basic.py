
def test_build_tree(conf_dir):
    from letssync.structures import build_tree
    r = build_tree(str(conf_dir['root_path']))

def test_copy(conf_dir):
    from letssync.structures import build_tree
    r1 = build_tree(str(conf_dir['root_path']))
    r2 = r1.copy()
    assert r1.is_equal(r2)
    assert r2.is_equal(r1)
