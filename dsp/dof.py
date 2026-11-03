import struct,sys
def parse(fn):
    b=open(fn,'rb').read()
    strsz,entry,resh,scnnamesz,nsyms,nscns0,nscns,ver,tid,flags,esec=struct.unpack_from('<IIIIHHHHHHi',b,0)
    off=36+20
    strtab=b[off:off+strsz]; off+=strsz
    def s(o):
        if o<0 or o>=len(strtab): return '#%d'%o
        e=strtab.index(b'\0',o); return strtab[o:e].decode('latin1')
    scns=[]
    for i in range(nscns):
        so,pa,va,sz,page,fl,pkt,npk=struct.unpack_from('<iiiiHHIi',b,off); off+=28
        scns.append(dict(name=s(so),paddr=pa,vaddr=va,size=sz,page=page,flags=fl,pkt=pkt,npk=npk))
    syms=[]
    for i in range(nsyms):
        no,val,sc,cl=struct.unpack_from('<iihh',b,off); off+=12
        syms.append((s(no) if 0<=no<len(strtab) else '?',val,sc,cl))
    return dict(b=b,entry=entry,ver=ver,tid=tid,flags=flags,scns=scns,syms=syms,fname=s(0),strtab=strtab)
def sectiondata(d,sc):
    b=d['b']; off=sc['pkt']; out=b''
    for i in range(sc['npk']):
        nrel,psz,ck=struct.unpack_from('<iiI',b,off); off+=12
        out+=b[off:off+psz]; off+=psz+nrel*12  # reloc size guess
    return out
if __name__=='__main__':
    d=parse(sys.argv[1])
    print('file',d['fname'],'ver',d['ver'],'target',hex(d['tid']),'flags',hex(d['flags']),'entry',hex(d['entry']))
    for sc in d['scns']: print('  scn %-40s paddr %8x vaddr %8x size %6x page %d flags %x pk %d'%(sc['name'],sc['paddr'],sc['vaddr'],sc['size'],sc['page'],sc['flags'],sc['npk']))
    print('  syms',len(d['syms']))
