"""Build and test the installed wheel outside the repository; capture real evidence."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import venv
import zipfile

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'evidence'
EVIDENCE.mkdir(exist_ok=True)


def run(args,cwd,env=None):
    completed=subprocess.run([str(x) for x in args],cwd=cwd,env=env,capture_output=True,text=True)
    record={'command':[str(x) for x in args],'cwd':str(cwd),'returncode':completed.returncode,
            'stdout':completed.stdout,'stderr':completed.stderr}
    if completed.returncode:
        print(json.dumps(record,indent=2));raise SystemExit(completed.returncode)
    return record


def main():
    records=[]
    # Build tooling is explicitly outside the package runtime dependency contract.
    records.append(run([sys.executable,'-c',"from setuptools import build_meta; build_meta.build_wheel('dist'); build_meta.build_sdist('dist')"],ROOT))
    wheel=next((ROOT/'dist').glob('*.whl'))
    with zipfile.ZipFile(wheel) as archive:
        contents=archive.namelist()
    permitted=[n for n in contents if n.startswith('relatiobench/') or n.startswith('relatiobench-0.1.0a1.dist-info/')]
    assert permitted==contents,contents
    assert not any(any(part in n.lower() for part in ('universalmind','.env','__pycache__','tests/')) for n in contents)
    with tempfile.TemporaryDirectory(prefix='relatiobench-clean-') as tmp:
        root=Path(tmp)
        assert not root.is_relative_to(ROOT)
        venv.EnvBuilder(with_pip=True).create(root/'venv')
        py=root/'venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        env=dict(os.environ)
        env.pop('PYTHONPATH',None)
        records.append(run([py,'-m','pip','install','--no-deps','--no-index',wheel],root,env))
        records.append(run([py,'-I','-m','relatiobench','demo','--output',root/'first'],root,env))
        records.append(run([py,'-I','-m','relatiobench','demo','--output',root/'second'],root,env))
        for path in (root/'first').glob('*.trace.json'):
            assert path.read_bytes()==(root/'second'/path.name).read_bytes(),path.name
        for path in (root/'first').glob('*.score.json'):
            assert path.read_bytes()==(root/'second'/path.name).read_bytes(),path.name
        # Deny sockets inside the installed interpreter and repeat the actual CLI path.
        script="import socket; socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('network denied')); from relatiobench.cli import main; raise SystemExit(main(['demo','--output','offline']))"
        records.append(run([py,'-I','-c',script],root,env))
        module=run([py,'-I','-c',"import relatiobench; print(relatiobench.__file__)"],root,env)
        records.append(module)
        assert str(ROOT/'src') not in module['stdout']
        fixture=json.loads((root/'first'/'demo-evidence.json').read_text())
        assert all(r['replay_equal'] for r in fixture['runs'])
        assert all(r['violations']==(3 if r['policy']=='faulty' else 0) for r in fixture['runs'])
    result={'platform':platform.platform(),'python':sys.version,'wheel':wheel.name,
            'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),'wheel_contents':contents,
            'clean_install_outside_source':True,'replay_and_metric_equality':True,'socket_denied_demo':True,
            'fixture_runs':fixture['runs'],'commands':records,'scope':'Engineering fixtures; no human, clinical, physical robot or ROS integration validation.'}
    name='windows' if os.name=='nt' else 'linux'
    (EVIDENCE/f'clean-install-{name}.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('commands','wheel_contents','fixture_runs')},indent=2))


if __name__=='__main__':main()
