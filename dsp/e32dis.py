import struct,sys
sys.path.insert(0,'.')
from imports import imports
from capstone import *
def load(fn):
    b=open(fn,'rb').read()
    cb=struct.unpack_from('<I',b,0x4c)[0]; text=struct.unpack_from('<I',b,0x60)[0]; co=struct.unpack_from('<I',b,0x64)[0]
    csz=struct.unpack_from('<I',b,0x30)[0]; entry=struct.unpack_from('<I',b,0x48)[0]
    exo=struct.unpack_from('<I',b,0x58)[0]; exn=struct.unpack_from('<i',b,0x5c)[0]
    iat={}; k=0
    for n,ords in imports(b):
        short=n.split('[')[0]
        for o in ords: iat[cb+text+4*k]='%s@%d'%(short,o); k+=1
    code=b[co:co+csz]
    exports=[struct.unpack_from('<I',b,exo+4*i)[0] for i in range(exn)]
    return dict(b=b,cb=cb,text=text,code=code,iat=iat,exports=exports,entry=entry)
def dis(img,start=None,end=None):
    md=Cs(CS_ARCH_ARM,CS_MODE_ARM)
    cb=img['cb']; code=img['code']
    s=start or cb; e=end or cb+img['text']
    lit={}
    out=[]
    for ins in md.disasm(code[s-cb:e-cb],s):
        t='%08x: %-6s %s'%(ins.address,ins.mnemonic,ins.op_str)
        if ins.mnemonic.startswith('ldr') and '[pc, #' in ins.op_str:
            off=int(ins.op_str.split('#')[-1].rstrip(']'),16); a=ins.address+8+off
            if cb<=a<cb+len(code)-3:
                v=struct.unpack_from('<I',code,a-cb)[0]; t+='   ; =0x%x'%v
                if v in img['iat']: t+=' -> '+img['iat'][v]
        out.append(t)
    return out
if __name__=='__main__':
    img=load(sys.argv[1])
    print('codebase %x text %x exports %s'%(img['cb'],img['text'],[hex(x) for x in img['exports']]))
    for l in dis(img): print(l)
