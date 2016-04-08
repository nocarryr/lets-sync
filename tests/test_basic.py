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

def test_serialization(conf_dir):
    from letssync.structures import build_tree
    from letssync.structures.base import Path
    r1 = build_tree(str(conf_dir['root_path']))
    js_str = r1.to_json()
    r2 = Path.from_json(js_str)
    assert r1.is_equal(r2) and r2.is_equal(r1)

def test_renewals(multi_conf_renewal_out_of_sync):
    from letssync.structures import build_tree
    base = multi_conf_renewal_out_of_sync['base']
    renewed = multi_conf_renewal_out_of_sync['renewed']
    r1 = build_tree(str(base['root_path']))
    r2 = build_tree(str(renewed['root_path']))
    assert r1.search('accounts').is_equal(r2.search('accounts'))
    assert not r1.search('live').is_equal(r2.search('live'))
    base_arch = r1.search('archive')
    renew_arch = r2.search('archive')
    for renew_dir in renew_arch.children.values():
        base_dir = base_arch.search(renew_dir.id)
        for renew_file in renew_dir.children.values():
            base_file = base_dir.search(renew_file.id)
            if '2' in renew_file.id:
                assert base_file is None
            else:
                assert base_file == renew_file
