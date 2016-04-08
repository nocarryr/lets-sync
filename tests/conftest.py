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
    for domain in domains:
        keypair = generate_keypair()
        req = certgen.createCertRequest(keypair['key'], CN=domain)
        cert = certgen.createCertificate(req, cacert, cakey, 1, 0, 60*60*24*365*5)
        d[domain] = {
            'keypair':keypair,
            'pkey':OpenSSL.crypto.dump_privatekey(PEM, keypair['key']),
            'cert':OpenSSL.crypto.dump_certificate(PEM, cert),
        }
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
        p = p.mkdir(dirname)
        p.chmod(dirstat)
    archive = root_path.mkdir('archive')
    archive.chmod(dirstat)
    live = root_path.mkdir('live')
    live.chmod(dirstat)
    for domain in domains:
        p = archive.mkdir(domain)
        p.chmod(dirstat)
        p = live.mkdir(domain)
        p.chmod(dirstat)
    p = root_path.mkdir('renewal')
    p.chmod(dirstat)

def build_cert_files(**kwargs):
    root_path = kwargs.get('root_path')
    certs = kwargs.get('certs')
    domains = kwargs.get('domains')
    for domain in domains:
        for fn, lfn in [['cert1.pem', 'cert.pem'], ['chain1.pem', 'chain.pem']]:
            f = root_path.join('archive', domain, fn)
            f.write(certs[domain]['cert'])
            lf = root_path.join('live', domain, lfn)
            lf.mksymlinkto(f, absolute=False)
        f = root_path.join('archive', domain, 'fullchain1.pem')
        f.write('\n'.join([str(certs[domain]['cert']), str(certs['ca_cert'])]))
        lf = root_path.join('live', domain, 'fullchain.pem')
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
    )
    for key, val in defaults.items():
        data.setdefault(key, val)
    data.setdefault('certs', generate_certs(**data))
    build_conf_shell(**data)
    accounts = data['root_path'].join('accounts', 'acme-v01.api.letsencrypt.org', 'directory')
    account = accounts.mkdir(data['account_id'])
    account.chmod(dirstat)
    meta = {
        'creation_host':'localhost',
        'creation_dt':datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
    }
    f = account.join('meta.json')
    f.write(json.dumps(meta))
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
