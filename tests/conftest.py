import os
import stat
import datetime
import random
import string
import json
import base64

import OpenSSL
import pytest

import certgen

PEM = OpenSSL.crypto.FILETYPE_PEM

def generate_keypair():
    key = OpenSSL.crypto.PKey()
    key.generate_key(OpenSSL.crypto.TYPE_RSA, 2048)
    priv = OpenSSL.crypto.dump_privatekey(PEM, key)
    pub = OpenSSL.crypto.dump_publickey(PEM, key)
    return dict(private=priv, public=pub, key=key)

def generate_certs(**kwargs):
    domains = kwargs.get('domains')
    d = {}
    ca_keypair = generate_keypair()
    d['ca_key'] = ca_keypair
    cakey = ca_keypair['key']
    careq = certgen.createCertRequest(cakey, CN='Certificate Authority')
    cacert = certgen.createCertificate(careq, careq, cakey, 0, 0, 60*60*24*365*5)
    d['ca_cert'] = OpenSSL.crypto.dump_certificate(PEM, cacert)
    if isinstance(d['ca_cert'], bytes):
        delim = b'\n'
    else:
        delim = '\n'
    for domain in domains:
        keypair = generate_keypair()
        req = certgen.createCertRequest(keypair['key'], CN=domain)
        cert = certgen.createCertificate(req, cacert, cakey, 1, 0, 60*60*24*365*5)
        d[domain] = {
            'keypair':keypair,
            'pkey':OpenSSL.crypto.dump_privatekey(PEM, keypair['key']),
            'cert':OpenSSL.crypto.dump_certificate(PEM, cert),
        }
        d[domain]['fullchain'] = delim.join([d[domain]['cert'], d['ca_cert']])
    return d

def generate_account_id():
    chars = string.hexdigits
    return ''.join(random.choice(chars) for i in range(32))

def build_conf_shell(**kwargs):
    dirstat = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
    root_path = kwargs.get('root_path')
    p = root_path
    domains = kwargs.get('domains')
    for dirname in ['accounts', 'acme-v01.api.letsencrypt.org', 'directory']:
        p = p.join(dirname)
        p.ensure(dir=True)
        p.chmod(dirstat)
    archive = root_path.join('archive')
    archive.ensure(dir=True)
    archive.chmod(dirstat)
    live = root_path.join('live')
    live.ensure(dir=True)
    live.chmod(dirstat)
    for domain in domains:
        p = archive.join(domain)
        p.ensure(dir=True)
        p.chmod(dirstat)
        p = live.join(domain)
        p.ensure(dir=True)
        p.chmod(dirstat)
    p = root_path.join('renewal')
    p.ensure(dir=True)
    p.chmod(dirstat)

def build_cert_files(**kwargs):
    root_path = kwargs.get('root_path')
    certs = kwargs.get('certs')
    domains = kwargs.get('domains')
    domain_indecies = kwargs.get('domain_indecies', {})
    for domain in domains:
        i = domain_indecies.get(domain, 1)
        for base_fn in ['cert', 'chain', 'fullchain', 'privkey']:
            fn = '{0}{1}.pem'.format(base_fn, i)
            lfn = '{0}.pem'.format(base_fn, i)
            f = root_path.join('archive', domain, fn)
            if 'fullchain' in fn:
                cert = certs[domain]['fullchain']
            elif 'privkey' in fn:
                cert = certs[domain]['pkey']
            else:
                cert = certs[domain]['cert']
            f.write(cert)
            lf = root_path.join('live', domain, lfn)
            if lf.exists():
                lf.remove()
            lf.mksymlinkto(f, absolute=False)

def build_renewal_conf(**kwargs):
    root_path = kwargs.get('root_path')
    account_id = kwargs.get('account_id')
    domains = kwargs.get('domains')
    with open(os.path.join('tests', 'renewal-template.conf'), 'r') as f:
        template = f.read()
    d = dict(root_path=str(root_path), account_id=account_id)
    for domain in domains:
        d['domain'] = domain
        fn = '.'.join([domain, 'conf'])
        f = root_path.join('renewal', fn)
        f.write(template.format(**d))

def build_confdir(**kwargs):
    dirstat = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
    data = kwargs.copy()
    defaults = dict(
        account_id = generate_account_id(),
        email = 'test@example.com',
        domains = ['example.com', 'www.example.com'],
        keypair = generate_keypair(),
        account_meta = {
            'creation_host':'localhost',
            'creation_dt':datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
    )
    for key, val in defaults.items():
        data.setdefault(key, val)
    data.setdefault('certs', generate_certs(**data))
    build_conf_shell(**data)
    accounts = data['root_path'].join('accounts', 'acme-v01.api.letsencrypt.org', 'directory')
    account = accounts.join(data['account_id'])
    account.ensure(dir=True)
    account.chmod(dirstat)
    f = account.join('meta.json')
    f.write(json.dumps(data['account_meta']))
    regr = {
        'body':{
            'contact':[data['email']],
            'key':{'e':'AQAB', 'kty':'RSA', 'n':str(data['keypair']['public'])},
        },
    }
    f = account.join('regr.json')
    f.write(json.dumps(regr))
    p = {'e':'AQAB', 'kty':'RSA', 'p':str(data['keypair']['private'])}
    f = account.join('private_key.json')
    f.write(json.dumps(p))
    f.chmod(stat.S_IRUSR | stat.S_IWUSR)
    build_cert_files(**data)
    build_renewal_conf(**data)
    return data

@pytest.fixture
def conf_dir(tmpdir):
    data = build_confdir(root_path=tmpdir)
    return data

@pytest.fixture
def conf_with_renewals(conf_dir):
    conf_dir['domain_indecies'] = {d: 2 for d in conf_dir['domains']}
    conf_dir['certs'] = generate_certs(**conf_dir)
    build_cert_files(**conf_dir)
    return conf_dir

@pytest.fixture
def multi_conf_renewal_out_of_sync(request, tmpdir_factory):
    tmpdir = tmpdir_factory.mktemp(request.node.name)
    p1 = tmpdir.mkdir('base')
    p2 = tmpdir.mkdir('renewed')
    base_data = build_confdir(root_path=p1)
    domain_indecies = {d: 2 for d in base_data['domains']}
    renewed_data = build_confdir(
        root_path=p2,
        account_id=base_data['account_id'],
        account_meta=base_data['account_meta'],
        keypair=base_data['keypair'],
        certs=base_data['certs'],
    )
    renewed_data['domain_indecies'] = domain_indecies
    renewed_data['certs'] = generate_certs(**renewed_data)
    build_cert_files(**renewed_data)
    return dict(base=base_data, renewed=renewed_data)

@pytest.fixture
def multi_conf_two_accounts(request, tmpdir_factory):
    tmpdir = tmpdir_factory.mktemp(request.node.name)
    p1 = tmpdir.mkdir('base')
    p2 = tmpdir.mkdir('new_account')
    base_data = build_confdir(root_path=p1)
    p1.copy(p2)
    new_account_data = build_confdir(
        root_path=p2,
        domains=['anotherexample.com', 'www.anotherexample.com'],
        email=['test@anotherexample.com'],
    )
    return dict(base=base_data, new_account=new_account_data)
