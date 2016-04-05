import os

def test_build_tree(conf_dir):
    from letssync.structures import build_tree
    r = build_tree(str(conf_dir['root_path']))

def test_copy(conf_dir):
    from letssync.structures import build_tree
    r1 = build_tree(str(conf_dir['root_path']))
    r2 = r1.copy()
    assert r1.is_equal(r2)
    assert r2.is_equal(r1)

def test_rw(conf_dir, tmpdir_factory):
    from letssync.structures import build_tree
    t = tmpdir_factory.mktemp('copy')
    r1 = build_tree(str(conf_dir['root_path']))
    r2 = r1.copy(str(t))
    r2.write(overwrite=False, recursive=True)
    r3 = build_tree(str(t))
    assert r1.is_equal(r3) and r3.is_equal(r1)
    assert r2.is_equal(r3) and r3.is_equal(r2)

def test_search(conf_dir):
    from letssync.structures import build_tree
    r1 = build_tree(str(conf_dir['root_path']))
    accounts = r1.search('accounts')
    account_id = conf_dir['account_id']
    account = accounts.accounts[account_id]
    search_account = r1.search(account.relative_path)
    assert account == search_account

def test_overwrite_protection(conf_dir, tmpdir_factory):
    from letssync.structures import build_tree
    r1 = build_tree(str(conf_dir['root_path']))
    accounts = r1.search('accounts')
    account_id = conf_dir['account_id']
    account = accounts.accounts[account_id]
    meta = account.search('meta.json')
    prev_content = meta.content
    meta.content = ''
    r1.write(overwrite=False, recursive=True)
    with open(meta.path, 'r') as f:
        s = f.read()
    assert s == prev_content
