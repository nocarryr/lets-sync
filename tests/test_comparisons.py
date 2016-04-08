import os

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

def test_diff(multi_conf_renewal_out_of_sync):
    from letssync.structures import build_tree
    base = multi_conf_renewal_out_of_sync['base']
    renewed = multi_conf_renewal_out_of_sync['renewed']
    r1 = build_tree(str(base['root_path']))
    r2 = build_tree(str(renewed['root_path']))
    r1.name = 'base'
    r2.name = 'renewed'
    diff = r1.get_diff(r2)
    keys_expected = []
    for domain in base['domains']:
        for fn in ['cert', 'chain', 'fullchain', 'privkey']:
            keys_expected.append('live/{}/{}.pem'.format(domain, fn))
            keys_expected.append('archive/{}/{}2.pem'.format(domain, fn))
        keys_expected.append('renewal/{}.conf'.format(domain))
    assert set(diff.keys()) == set(keys_expected)
    for key in keys_expected:
        val = diff[key]
        if key.startswith('live'):
            assert list(val.keys()) == ['linked_path']
        elif key.startswith('archive'):
            assert val['content']['base'] is None
            assert val['content']['renewed'] is not None

def test_multi_account(multi_conf_two_accounts):
    from letssync.structures import build_tree
    base = multi_conf_two_accounts['base']
    new_account = multi_conf_two_accounts['new_account']
    r1 = build_tree(str(base['root_path']))
    r2 = build_tree(str(new_account['root_path']))
    r1.name = 'base'
    r2.name = 'new_account'
    diff = r1.get_diff(r2)
    keys_expected = []
    for domain in new_account['domains']:
        keys_expected.append(os.path.join('live', domain))
        keys_expected.append(os.path.join('archive', domain))
        for fn in ['cert', 'chain', 'fullchain', 'privkey']:
            keys_expected.append('live/{}/{}.pem'.format(domain, fn))
            keys_expected.append('archive/{}/{}1.pem'.format(domain, fn))
        keys_expected.append('renewal/{}.conf'.format(domain))
    account_id = new_account['account_id']
    ac_path = os.path.join('accounts', 'acme-v01.api.letsencrypt.org', 'directory')
    ac_path = os.path.join(ac_path, account_id)
    keys_expected.append(ac_path)
    for fn in ['regr.json', 'private_key.json', 'meta.json']:
        keys_expected.append(os.path.join(ac_path, fn))
    assert set(diff.keys()) == set(keys_expected)
    for key in keys_expected:
        val = diff[key]
        assert val['class_name']['new_account'] is not None
        assert val['class_name']['base'] is None
