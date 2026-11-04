# TI DOF (DSP/BIOS Bridge "dynamic object file", DOFF v2, C55x) reader/writer.
# (doff.h in Linux's drivers/staging/tidspbridge/dynload has the structures.)
# Layout: header 36 B {string table size, entry, 0x00010203, size up to the last section name,
# symbols u16, longest string u16, sections u16, sections to allocate u16, version 0 u16, target 0x9C u16,
# flags u16 (0x12E0), entry section s16, checksum: the 9 words sum to 0xFFFFFFFF}, verify record
# 20 B {time, ~sum(section headers), ~sum(string table), ~sum(symbols), ~sum(the 4 before)},
# string table (file name, section names, then symbol names), section headers 28 B
# {name offset, run addr, load addr, size, page u16, flags u16, first packet offset, packets},
# symbols 12 B {name offset, value, section s16, class s16}, then each section's packets
# {relocs, size, checksum: the whole packet sums to 0xFFFFFFFF} + data (padded to 4) + relocs 12 B
# {offset in the packet, symbol, disp u16, type u16}. All little-endian.
import struct
M=0xffffffff
def s32(d):
    d=bytes(d)+b'\0'*((-len(d))%4); return sum(struct.unpack('<%dI'%(len(d)//4),d))&M
def parse(b):
    strsz,entry,resh,scnnamesz,nsyms,w4h,nscns,w5h,w6,w7,hck=struct.unpack_from('<IIIIHHHHIII',b,0)
    timdat,cs,cst,csy,cv=struct.unpack_from('<5I',b,36)
    st=b[56:56+strsz]
    def s(o):
        e=st.index(b'\0',o); return st[o:e].decode('latin1')
    off=56+strsz; scns=[]
    for i in range(nscns):
        so,pa,va,sz,page,fl,pkt,npk=struct.unpack_from('<iiiiHHIi',b,off+28*i)
        pk=[]; o=pkt
        for k in range(npk):
            nrel,psz,ck=struct.unpack_from('<iiI',b,o); dl=(psz+3)&~3
            data=b[o+12:o+12+psz]; rel=[struct.unpack_from('<iIHH',b,o+12+dl+12*r) for r in range(nrel)]
            pk.append(dict(data=data,relocs=rel)); o+=12+dl+12*nrel
        scns.append(dict(name=s(so),paddr=pa,vaddr=va,size=sz,page=page,flags=fl,packets=pk))
    off+=28*nscns; syms=[]
    for i in range(nsyms):
        no,val,sc,cl=struct.unpack_from('<iihh',b,off+12*i)
        syms.append(dict(name=s(no) if 0<=no<strsz else None,noff=no,value=val,scnum=sc,sclass=cl))
    return dict(keep_counts=True,fname=s(0),entry=entry,resh=resh,w4h=w4h,w5h=w5h,w6=w6,w7=w7,timdat=timdat,scns=scns,syms=syms,strtab=st,scnnamesz=scnnamesz)
def build(d):
    # string table: file name, section names, symbol names (in that order, as TI's tool does)
    st=bytearray(); offs={}
    def add(n):
        o=len(st); st.extend(n.encode('latin1')+b'\0'); return o
    add(d['fname'])
    scnoff=[add(sc['name']) for sc in d['scns']]
    scnnamesz=len(st)
    symoff=[]
    for sy in d['syms']:
        if sy.get('name') is None: symoff.append(sy.get('noff',-1))
        else: symoff.append(add(sy['name']))
    while len(st)%4: st.append(0)
    nsc=len(d['scns']); nsy=len(d['syms'])
    pktstart=56+len(st)+28*nsc+12*nsy
    # packets
    body=bytearray(); hdrs=bytearray()
    for i,sc in enumerate(d['scns']):
        first=pktstart+len(body) if sc['packets'] else 0
        for p in sc['packets']:
            data=bytes(p['data']); dl=(len(data)+3)&~3
            pkt=bytearray(struct.pack('<iiI',len(p['relocs']),len(data),0)+data+b'\0'*(dl-len(data)))
            for r in p['relocs']: pkt+=struct.pack('<iIHH',*r)
            struct.pack_into('<I',pkt,8,(M-s32(pkt))&M)
            body+=pkt
        hdrs+=struct.pack('<iiiiHHIi',scnoff[i],sc['paddr'],sc['vaddr'],sc['size'],sc['page'],sc['flags'],first,len(sc['packets']))
    syb=bytearray()
    for sy,o in zip(d['syms'],symoff): syb+=struct.pack('<iihh',o,sy['value'],sy['scnum'],sy['sclass'])
    # df_max_str_len: the longest string (not the file name) with its NUL; df_target_scns: the sections to allocate
    maxstr=d.get('w4h') if d.get('keep_counts') else max(len(x) for x in bytes(st).split(b'\0')[1:])+1
    tgt=d.get('w5h') if d.get('keep_counts') else sum(1 for sc in d['scns'] if sc['flags']&0x10)
    hdr=bytearray(struct.pack('<IIIIHHHHIII',len(st),d['entry'],d.get('resh',0x10203),scnnamesz,nsy,maxstr,nsc,tgt,d.get('w6',0x9c0000),d.get('w7',0x12e0),0))
    struct.pack_into('<I',hdr,32,(M-s32(hdr))&M)
    v=[d.get('timdat',0),(M-s32(hdrs))&M,(M-s32(st))&M,(M-s32(syb))&M]
    v.append((M-(sum(v)&M))&M)
    return bytes(hdr+struct.pack('<5I',*v)+st+hdrs+syb+body)
