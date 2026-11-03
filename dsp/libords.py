import subprocess,re,sys
def ords(lib):
    out=subprocess.run([__import__('os').path.expanduser('~/sym/gcc539/bin/arm-epoc-pe-nm'),lib],capture_output=True,text=True).stdout
    m={}; cur=None
    for l in out.split('\n'):
        a=re.search(r's_(\d+)\.o:$',l)
        if a: cur=int(a.group(1)); continue
        b=re.search(r'__imp_(\S+)',l)
        if b and cur is not None: m[cur]=b.group(1)
    return m
def demangle(names):
    p=subprocess.run([__import__('os').path.expanduser('~/sym/gcc539/bin/arm-epoc-pe-c++filt')],input='\n'.join(names),capture_output=True,text=True)
    return p.stdout.split('\n')
if __name__=='__main__':
    m=ords(sys.argv[1]); ks=sorted(m); d=demangle([m[k] for k in ks])
    for k,n in zip(ks,d): print(k,n)
