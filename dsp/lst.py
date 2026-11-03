import sys; sys.path.insert(0,'.')
import xan
n=sys.argv[1]; im=xan.IM[n]; h=im['h']; ed=h['iExportDir']
ex=[xan.u32(ed+4*i) for i in range(h['iExportDirCount'])]
lab={a:'%s@%d'%(n,i+1) for i,a in enumerate(ex)}
for l in xan.dis(h['iCodeAddress'], h['iTextSize']//4, stop=False):
    a=int(l.split(':')[0],16)
    if a in lab: print('\n==== '+lab[a])
    print(l)
