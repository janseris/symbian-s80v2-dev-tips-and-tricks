import sys,re
fn=sys.argv[1]; cur=None; lines=[]
res={}
for l in open(fn):
    if l.startswith('===='): cur=l.strip('= \n'); res[cur]=[]; lines=[]; continue
    lines.append(l)
    if cur and 'Control(' in l:
        # find last "mov r1, #N" or "ldr r1" in previous 12 lines
        v='?'
        for p in reversed(lines[-14:-1]):
            m=re.search(r'(mov|mvn)\s+r1, #(0x[0-9a-f]+|\d+)',p)
            if m: v=('~' if m.group(1)=='mvn' else '')+m.group(2); break
            m=re.search(r'ldr\s+r1, .*; =(0x[0-9a-f]+)',p)
            if m: v=m.group(1); break
        res[cur].append(('Sv' if 'DoSv' in l else '')+v)
for k,v in res.items():
    if v: print(k, v)
