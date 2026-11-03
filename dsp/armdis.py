import struct,sys
sys.path.insert(0,'.')
from rom import hdr
from capstone import *
class Img:
    def __init__(s,fn):
        s.b=open(fn,'rb').read(); s.h=hdr(s.b); s.base=s.h['iCodeAddress']-0x64
        s.md=Cs(CS_ARCH_ARM,CS_MODE_ARM); s.md.detail=False
    def u32(s,a):
        o=a-s.base
        return struct.unpack_from('<I',s.b,o)[0] if 0<=o<=len(s.b)-4 else None
    def cstr(s,a):
        o=a-s.base
        if not(0<=o<len(s.b)): return None
        e=s.b.find(b'\0',o)
        t=s.b[o:e]
        if 3<=len(t)<120 and all(32<=c<127 for c in t): return t.decode()
        # wide?
        t=s.b[o:o+120]
        try:
            w=t.decode('utf-16-le').split('\0')[0]
            if len(w)>=3 and all(32<=ord(c)<127 for c in w): return 'L"'+w+'"'
        except: pass
        return None
    def dis(s,a,n=60,stop=True):
        out=[]
        o=a-s.base
        for ins in s.md.disasm(s.b[o:o+4*n],a):
            t='%x: %s %s'%(ins.address,ins.mnemonic,ins.op_str)
            if ins.mnemonic.startswith('ldr') and '[pc, #' in ins.op_str:
                off=int(ins.op_str.split('#')[-1].rstrip(']'),16)
                lit=s.u32(ins.address+8+off)
                if lit is not None:
                    t+='   ; =0x%x'%lit
                    st=s.cstr(lit)
                    if st: t+=' "%s"'%st
            out.append(t)
            if stop and ins.mnemonic in ('bx','pop') and ('lr' in ins.op_str or 'pc' in ins.op_str) and len(out)>3: break
        return out
