# TI-COFF v2 (C55x) reader: header, sections, relocations, symbols (little-endian control data)
import struct
def parse(b):
    magic,nscns,timdat,symptr,nsyms,opthdr,flags,tid=struct.unpack_from('<HHIIIHHH',b,0)
    off=22+opthdr
    strtab_off=symptr+18*nsyms
    def name8(raw):
        if raw[:4]==b'\0\0\0\0':
            o=struct.unpack_from('<I',raw,4)[0]; e=b.index(b'\0',strtab_off+o); return b[strtab_off+o:e].decode('latin1')
        return raw.rstrip(b'\0').decode('latin1')
    scns=[]
    for i in range(nscns):
        raw=b[off:off+48]
        paddr,vaddr,size,scnptr,relptr,lnnoptr,nreloc,nlnno,sflags,res,page=struct.unpack_from('<IIIIIIIIIHH',raw,8)
        sc=dict(name=name8(raw[:8]),paddr=paddr,vaddr=vaddr,size=size,scnptr=scnptr,relptr=relptr,nreloc=nreloc,flags=sflags,page=page,hdroff=off)
        sc['relocs']=[struct.unpack_from('<IIHH',b,relptr+12*k) for k in range(nreloc)]
        scns.append(sc); off+=48
    syms=[]; i=0
    while i<nsyms:
        o=symptr+18*i
        raw=b[o:o+8]; val,scnum,typ,sclass,naux=struct.unpack_from('<IhHBB',b,o+8)
        syms.append(dict(idx=i,name=name8(raw),value=val,scnum=scnum,type=typ,sclass=sclass,naux=naux,aux=b[o+18:o+18+18*naux]))
        i+=1+naux
    return dict(b=b,magic=magic,tid=tid,flags=flags,opthdr=opthdr,scns=scns,syms=syms,symptr=symptr,nsyms=nsyms)
