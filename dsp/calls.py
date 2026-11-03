import sys,re
fn=sys.argv[1]; cur=None; calls={}
order=[]
for l in open(fn):
    if l.startswith('===='): cur=l.strip('= \n'); order.append(cur); calls[cur]=[]; continue
    if cur and ('bl ' in l or 'b  ' in l) and '; ->' in l:
        calls[cur].append(l.split('; ->')[1].strip())
    if cur and re.search(r'ldr .*; =0x[0-9a-f]+$',l):
        v=l.split('=')[-1].strip()
        if int(v,16)<0x100000 and int(v,16)>0x40: calls[cur].append('#'+v)
for k in order: print(k, ', '.join(calls[k][:30]))
