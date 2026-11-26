import subprocess,sys,json,tempfile,pathlib,hashlib,datetime
root=pathlib.Path(__file__).resolve().parents[1]
steps=[]
def run(args,cwd=root,expect=0):
    r=subprocess.run([str(a) for a in args],cwd=str(cwd),capture_output=True,text=True,encoding="utf-8",errors="replace")
    steps.append({"command":[str(a) for a in args],"exit_code":r.returncode,"stdout":r.stdout,"stderr":r.stderr})
    if r.returncode!=expect:
        raise RuntimeError("Unexpected exit: "+str(args)+" "+r.stderr)
    return r
try:
    run([sys.executable,"-m","unittest","discover","-s","tests","-v"])
    run([sys.executable,"-m","build","--outdir","dist/audit-ready"])
    distributions=sorted((root/"dist/audit-ready").glob("*"))
    run([sys.executable,"-m","twine","check",*distributions])
    run([sys.executable,"-m","relatiobench.cli","quickstart","--output","docs/chat-demo"])
    with tempfile.TemporaryDirectory(prefix="relatiobench-a2-") as td:
        work=pathlib.Path(td)
        run([sys.executable,"-m","venv",work/"venv"],cwd=work)
        python=work/"venv/Scripts/python.exe"
        wheel=next((root/"dist/audit-ready").glob("*.whl"))
        run([python,"-m","pip","install","--no-deps",wheel],cwd=work)
        run([python,"-m","relatiobench.cli","quickstart","--output",work/"demo"],cwd=work)
        run([python,"-m","relatiobench.cli","audit",work/"demo/before.chat.json","--output",work/"own"],cwd=work,expect=1)
        run([python,"-m","relatiobench.cli","compare",work/"demo/before/audit.json",work/"demo/after/audit.json"],cwd=work)
        run([python,"-m","relatiobench.cli","demo","--output",work/"legacy"],cwd=work)
        b=json.loads((work/"demo/before/audit.json").read_text())
        a=json.loads((work/"demo/after/audit.json").read_text())
        assert len(b["findings"])==2 and not a["findings"]
        assert b["score"]["metrics"]["eligible_task_completion"]==a["score"]["metrics"]["eligible_task_completion"]
    status="passed"
except Exception as exc:
    status="failed: "+str(exc)
proof={"verified_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"version":"0.1.0a2","status":status,"python":sys.version,"scope":"Maintainer Windows tests and isolated wheel install; not independent evaluation or PyPI registry installation.","steps":steps,"sha256":{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (root/"dist/audit-ready").glob("*") if f.is_file()}}
(root/"evidence/chat-audit-windows.json").write_text(json.dumps(proof,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"status":status,"steps":len(steps),"sha256":proof["sha256"]},indent=2))
sys.exit(0 if status=="passed" else 1)
