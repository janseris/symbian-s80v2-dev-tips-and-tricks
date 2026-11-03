# annotate XIP ROM images: exports named Dll@ord, calls resolved across the dumped images
import struct,sys,glob,os
sys.path.insert(0,'.')
from rom import hdr
from capstone import *
IM={}
for fn in sorted(glob.glob('./files/rom/*')):
    b=open(fn,'rb').read(); h=hdr(b); name=os.path.basename(fn).rsplit('_',1)[0]
    base=h['iCodeAddress']-0x64
    IM[name]=dict(b=b,h=h,base=base,name=name)
SYM={}
EU={}
for l in open('./euser_ords.txt'):
    k,v=l.rstrip('\n').split(' ',1); EU[int(k)]=v
for n,im in IM.items():
    h=im['h']
    for i in range(h['iExportDirCount']):
        o=h['iExportDir']+4*i-im['base']
        if 0<=o<=len(im['b'])-4:
            a=struct.unpack_from('<I',im['b'],o)[0]; SYM.setdefault(a,'%s@%d'%(n,i+1))
    SYM.setdefault(h['iEntryPoint'],n+'@entry')
def u32(a):
    for im in IM.values():
        o=a-im['base']
        if 0<=o<=len(im['b'])-4: return struct.unpack_from('<I',im['b'],o)[0]
    return None
def owner(a):
    for im in IM.values():
        if 0<=a-im['base']<len(im['b']): return im
# stubs: functions that are "ldr ip,[pc]; ldr pc,[ip]" or "ldr pc,[pc,#-4]" style -> target
md=Cs(CS_ARCH_ARM,CS_MODE_ARM)
def resolve(a):
    if a in SYM: return SYM[a]
    im=owner(a)
    if not im: return None
    o=a-im['base']; ins=list(md.disasm(im['b'][o:o+12],a))
    if len(ins)>=2 and ins[0].mnemonic=='ldr' and ins[0].op_str.startswith('ip, [pc') :
        off=int(ins[0].op_str.split('#')[-1].rstrip(']'),16) if '#' in ins[0].op_str else 0
        p=u32(a+8+off)
        if p is not None:
            if ins[1].op_str.startswith('pc, [ip') or ins[1].op_str.startswith('ip, [ip'):
                for nm,im2 in IM.items():
                    ed=im2['h']['iExportDir']
                    if ed<=p<ed+4*im2['h']['iExportDirCount']: return '->%s@%d'%(nm,(p-ed)//4+1)
                if 0x500e8938<=p<0x500e8938+4*2100: return '->EUser:'+EU.get((p-0x500e8938)//4+1,'@%d'%((p-0x500e8938)//4+1))
                t=u32(p); 
                if t in SYM: return '->'+SYM[t]
                return '->?%x'%(t or 0)
            if 'bx' in ins[1].mnemonic or ins[1].op_str=='pc, ip':
                return '->'+SYM.get(p,'?%x'%p)
    return None
def dis(a,n=200,stop=True):
    im=owner(a); o=a-im['base']; out=[]
    for ins in md.disasm(im['b'][o:o+4*n],a):
        t='%08x: %-6s %s'%(ins.address,ins.mnemonic,ins.op_str)
        if ins.mnemonic in ('bl','b') and '#' in ins.op_str:
            tgt=int(ins.op_str.split('#')[1],16); r=resolve(tgt)
            if r: t+='   ; '+r
        if ins.mnemonic.startswith('ldr') and '[pc, #' in ins.op_str:
            off=int(ins.op_str.split('#')[-1].rstrip(']'),16); v=u32(ins.address+8+off)
            if v is not None:
                t+='   ; =0x%x'%v
                if v in SYM: t+=' '+SYM[v]
        out.append(t)
        if stop and ins.mnemonic=='bx' and ins.op_str=='lr' and len(out)>2: break
        if stop and ins.mnemonic.startswith('pop') and 'pc' in ins.op_str: break
    return out
