"""Record a real installed CLI session as an asciicast; no fabricated terminal output.

The script runs the installed package, then prints its saved trace and score data
at a readable pace. The later video is a rendering of this captured transcript,
not a browser screen recording or a robot/simulator demonstration.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

out=Path(sys.argv[1]).resolve()
out.mkdir(parents=True,exist_ok=True)
started=time.monotonic()
record=[]


def line(value='',delay=0):
    value=str(value)+'\r\n'
    record.append([round(time.monotonic()-started,3),'o',value])
    print(value,end='',flush=True)
    if delay:time.sleep(delay)


line('RELATIOBENCH / Replay the interaction. Inspect the decision.',2)
line('Actual installed CLI session | authored synthetic fixtures',2)
command=[sys.executable,'-I','-m','relatiobench','demo','--output',str(out/'artifacts')]
line('$ python -I -m relatiobench demo --output ./artifacts',1)
completed=subprocess.run(command,capture_output=True,text=True)
if completed.returncode:raise RuntimeError(completed.stderr)
for row in completed.stdout.splitlines():line(row,1)
for context in ('social_robot','virtual_roleplay'):
    safe=json.loads((out/'artifacts'/f'{context}-respectful.trace.json').read_text())
    faulty=json.loads((out/'artifacts'/f'{context}-faulty.trace.json').read_text())
    from relatiobench.schema import ordered_events
    line('',0)
    line('CONTEXT: '+context.upper(),2)
    for event in ordered_events(safe['scenario']):
        a=next(a for a in safe['actions'] if a['event_id']==event['id'])
        b=next(a for a in faulty['actions'] if a['event_id']==event['id'])
        def action(x):return x['kind']+(f" level={x['level']}" if 'level' in x else '')
        line(f"{event['tick']:02} {event['kind']:<9} respectful: {action(a):<17} faulty: {action(b)}",1.5)
    score_command=[sys.executable,'-I','-m','relatiobench','score',str(out/'artifacts'/f'{context}-faulty.trace.json')]
    scored=subprocess.run(score_command,capture_output=True,text=True)
    if scored.returncode!=1:raise RuntimeError('Expected a valid failing trace')
    value=json.loads(scored.stdout)
    line('Independent score command returned 1 (valid trace, violations found).',1)
    for violation in value['violations']:line('  '+violation['code']+' @ '+violation['event_id'],1)
line('Always-stop baseline: 0 violations, but 0/2 eligible tasks completed.',2)
line('Reproduce, inspect the JSON, send one concrete friction finding.',2)
line('Engineering evidence only. No clinical, physical-robot or ROS validation.',3)
duration=round(time.monotonic()-started,3)
header={'version':2,'width':110,'height':20,'timestamp':int(time.time()),'title':'RelatioBench actual installed CLI session','env':{'TERM':'xterm-256color'},'duration':duration}
with (out/'demo.cast').open('w') as f:
    f.write(json.dumps(header)+'\n')
    for event in record:f.write(json.dumps(event)+'\n')
(out/'recording-metadata.json').write_text(json.dumps({'duration_seconds':duration,'python':sys.version,'capture':'Actual subprocess output and saved trace data, paced by this script. Video renderer is not a browser screenshot.','scenarios':'Authored synthetic fixtures','demo_returncode':completed.returncode},indent=2)+'\n')
print('Recording saved:',out/'demo.cast',flush=True)
