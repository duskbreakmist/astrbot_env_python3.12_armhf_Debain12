import importlib.metadata as md, json, sys, platform, urllib.request, sqlite3, subprocess, re
from pathlib import Path
venv=Path(sys.prefix)
assert venv==Path("/opt/py3_12"),sys.prefix
assert sys.version_info[:2]==(3,12)
assert not any("python3.11" in p or "dist-packages" in p for p in sys.path)
assert "include-system-site-packages = false" in (venv/"pyvenv.cfg").read_text()
packages={d.metadata["Name"].lower().replace("_","-"):d.version for d in md.distributions()}
assert packages["astrbot"]=="4.29.3" and packages["faiss-cpu"]=="1.14.3"
for name in ("numpy","pyotp","docx","reportlab","opentelemetry.sdk"):
    module=__import__(name,fromlist=["__name__"])
    loc=getattr(module,"__file__",None)
    if loc: assert str(venv) in loc,(name,loc)
versions={}
for endpoint in ("/", "/api/stat/versions", "/api/v1/stats/versions"):
    with urllib.request.urlopen("http://127.0.0.1:6185"+endpoint,timeout=20) as res:
        assert res.status==200
        data=res.read()
        if endpoint!="/":
            obj=json.loads(data)["data"];assert obj["astrbot_version"]=="4.29.3";assert obj["webui_version"]=="v4.29.3";versions[endpoint]=obj
work=Path("/home/ray/astrbot_workplace/data")
db_status={}
for name in ("data_v4.db","knowledge_base/kb.db"):
    conn=sqlite3.connect("file:"+str(work/name)+"?mode=ro",uri=True)
    status=conn.execute("pragma quick_check").fetchone()[0];conn.close();assert status=="ok";db_status[name]=status
service=dict(x.split("=",1) for x in subprocess.check_output(["systemctl","show","astrbot","-p","ActiveState","-p","SubState","-p","NRestarts"],text=True).splitlines())
assert service["ActiveState"]=="active" and service["SubState"]=="running" and service["NRestarts"]=="0"
invocation=subprocess.check_output(["systemctl","show","astrbot","-p","InvocationID","--value"],text=True).strip()
logs=subprocess.check_output(["journalctl","_SYSTEMD_INVOCATION_ID="+invocation,"--no-pager","-o","cat"],text=True)
logs=re.sub(r"\x1b\[[0-9;]*m","",logs)
# Keep only the most recent new-version boot, never export raw operational logs.
recent=logs
errors=[line for line in recent.splitlines() if "[ERROR]" in line or "Traceback (most recent call last)" in line]
assert not errors,"Errors present in latest startup; inspect private journal locally"
plugins=len(re.findall(r"Plugin .+? by ",recent))
adapters=len(re.findall(r"Loading IM platform adapter qq_official",recent))
result=dict(status="PASS",python=platform.python_version(),machine=platform.machine(),kernel=platform.release(),executable=sys.executable,system_site_packages=False,python311_paths=False,packages=packages,package_count=len(packages),http_versions=versions,database_checks=db_status,service=service,loaded_plugin_count=plugins,loaded_qq_official_adapters=adapters,latest_startup_errors=len(errors),limits=["No outgoing IM message or paid model call was sent", "No populated FAISS index existed in the knowledge-base directory", "Existing SILK backend and stdlib _lzma omissions were not fixed by this package upgrade"])
print(json.dumps(result,indent=2))
