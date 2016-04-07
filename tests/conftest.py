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

def generate_certs(domains):
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

def build_conf_shell(root_path, domains):
    dirstat = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
    p = root_path
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

def build_cert_files(root_path, certs, domains):
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

def build_renewal_conf(root_path, account_id, domains):
    with open(os.path.join('tests', 'renewal-template.conf'), 'r') as f:
        template = f.read()
    d = dict(root_path=str(root_path), account_id=account_id)
    for domain in domains:
        d['domain'] = domain
        f = root_path.join('renewal', domain)
        f.write(template.format(**d))

def build_confdir(root_path, **kwargs):
    dirstat = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
    account_id = kwargs.get('account_id', generate_account_id())
    email = kwargs.get('email', 'test@example.com')
    domains = kwargs.get('domains', ['example.com', 'www.example.com'])
    keypair = kwargs.get('keypair', generate_keypair())
    build_conf_shell(root_path, domains)
    accounts = root_path.join('accounts', 'acme-v01.api.letsencrypt.org', 'directory')
    account = accounts.mkdir(account_id)
    account.chmod(dirstat)
    meta = {
        'creation_host':'localhost',
        'creation_dt':datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
    }
    f = account.join('meta.json')
    f.write(json.dumps(meta))
    regr = {
        'body':{
            'contact':[email],
            'key':{'e':'AQAB', 'kty':'RSA', 'n':str(keypair['public'])},
        },
    }
    f = account.join('regr.json')
    f.write(json.dumps(regr))
    p = {'e':'AQAB', 'kty':'RSA', 'p':str(keypair['private'])}
    f = account.join('private_key.json')
    f.write(json.dumps(p))
    f.chmod(stat.S_IRUSR | stat.S_IWUSR)
    certs = generate_certs(domains)
    build_cert_files(root_path, certs, domains)
    build_renewal_conf(root_path, account_id, domains)
    d = dict(
        account_id=account_id,
        email=email,
        domains=domains,
        keypair=keypair,
        certs=certs,
    )
    return d

@pytest.fixture
def conf_dir(tmpdir):
    data = build_confdir(tmpdir)
    data['root_path'] = tmpdir
    return data
