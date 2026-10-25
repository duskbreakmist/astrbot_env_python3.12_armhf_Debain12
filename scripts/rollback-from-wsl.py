#!/usr/bin/env python3
"""Verify private pre-upgrade snapshots; restore only with explicit --apply."""
import argparse, hashlib, os, pathlib, subprocess, tarfile
p=argparse.ArgumentParser()
p.add_argument("backup_dir",type=pathlib.Path)
p.add_argument("--host",default="hi3798_37_10")
p.add_argument("--expected-hostname",default="HI3798moe26")
p.add_argument("--apply",action="store_true")
a=p.parse_args()
required=("python-venv-systemd-before.tar.gz","astrbot-data-before.tar.gz")
sums={}
for line in (a.backup_dir/"SHA256SUMS.private").read_text().splitlines():
    digest,name=line.split(None,1);sums[name.strip().lstrip("*")]=digest
for name in required:
    f=a.backup_dir/name
    with f.open("rb") as src: digest=hashlib.file_digest(src,"sha256").hexdigest()
    assert digest==sums[name],"Backup checksum mismatch: "+name
    with tarfile.open(f) as t:
        for m in t.getmembers():
            path=pathlib.PurePosixPath(m.name)
            assert not path.is_absolute() and ".." not in path.parts
            assert m.name.startswith(("opt/py3_12","opt/python3.12-standalone","etc/systemd/system/astrbot.service","home/ray/astrbot_workplace"))
sshbin="/mnt/c/Windows/System32/OpenSSH/ssh.exe"
if not pathlib.Path(sshbin).exists(): sshbin="ssh"
ssh=[sshbin,"-o","BatchMode=yes","-o","UpdateHostKeys=no","-o","User=root",a.host]
hostname=subprocess.check_output(ssh+["hostname"],text=True).strip()
assert hostname==a.expected_hostname,(hostname,a.expected_hostname)
print("Verified both private backups and target host:",hostname)
if not a.apply:
    print("Dry run only. --apply restores the pre-upgrade venv AND business data.")
    raise SystemExit(0)
subprocess.run(ssh+["systemctl stop astrbot"],check=True)
# Fixed explicit destinations only; reject symlinks before removing newer files.
cleanup="import os,shutil; paths=['/opt/py3_12','/home/ray/astrbot_workplace']; assert all(os.path.realpath(x)==x for x in paths); [shutil.rmtree(x) for x in paths if os.path.isdir(x)]"
import shlex
subprocess.run(ssh+["/opt/python3.12-standalone/bin/python3.12 -B -c "+shlex.quote(cleanup)],check=True)
for name in required:
    with (a.backup_dir/name).open("rb") as src:
        subprocess.run(ssh+["tar -xzpf - -C /"],stdin=src,check=True)
subprocess.run(ssh+["systemctl daemon-reload && systemctl start astrbot && systemctl is-active astrbot"],check=True)
print("Pre-upgrade snapshot restored. Verify version, WebUI and platform state.")
