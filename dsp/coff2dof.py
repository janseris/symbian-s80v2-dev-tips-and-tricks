#!/usr/bin/env python3
# coff2dof.py: a TI-COFF object from cl55 (C55x, large model) -> a DSP/BIOS Bridge dynamic node
# file (DOF) for the Nokia 9300's DSP, modelled byte for byte on the ROM's nodes (Prodtest, Raw):
# .text (code, as is, 1024-byte packets, the COFF relocations as they are: offsets made
# packet-relative, symbols renumbered), then the bridge's information sections: .dspbridge_symbols,
# .vers, .dcd_register ("UUID:0,") and .<UUID> (the node's DCD properties), all UTF-16BE.
# Only .text: data sections (.const, .bss, .data, .switch, .cinit) are refused, so are relocations
# against our own sections (the code's own symbols at load address 0x100, as TI's tool does).
#   coff2dof.py in.obj out.dof55l --uuid 4D415053-3933-3030-8000-000000000001 --name ECHO_MAPS
#       [--create ECHO_MAPS_create --execute ... --delete ...] [--stack 0x800] [--msgdepth 3]
import sys,struct,argparse,time,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import coff,dofw
KTEXT_ADDR=0     # .text where cl55's object has it: our own relocations (function addresses) stay right
BRIDGE_SYMS='_RMS_queryServer,_RMS_configureServer,_RMS_createNode,_RMS_executeNode,_RMS_deleteNode,_RMS_changeNodePriority,_RMS_readMemory,_RMS_writeMemory,_RMS_copy,_STRM_ATTRS,_SHM_BEG,_SHM_END,_SHM0_RSVDSTRT,_SHM0_BEG,_SHM0_END,_MSG_BEG,_MSG_END,_EXT_BEG,_EXT_END,_DYNEXT_BEG,_DYNEXT_END,_SRAM_BEG,_SRAM_END,_SYS_PUTCBEG,_SYS_PUTCEND,'
def u16be(s): return s.encode('utf-16-be')
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('obj'); ap.add_argument('out')
    ap.add_argument('--uuid',required=True); ap.add_argument('--name',required=True)
    ap.add_argument('--create'); ap.add_argument('--execute'); ap.add_argument('--delete')
    ap.add_argument('--stack',default='0800H'); ap.add_argument('--sysstack',default='0100H')
    ap.add_argument('--msgdepth',default='03H'); ap.add_argument('--prio',default='0aH')
    ap.add_argument('--fname',default=None)
    a=ap.parse_args()
    cr=a.create or a.name+'_create'; ex=a.execute or a.name+'_execute'; de=a.delete or a.name+'_delete'
    c=coff.parse(open(a.obj,'rb').read())
    assert c['magic']==0xc2 and c['tid']==0x9c, 'not a C55x TI-COFF'
    bad=[s for s in c['scns'] if s['size'] and s['name'] in ('.const','.data','.bss','.switch','.cinit','.sysmem','.far','.fardata','.cio')]
    if bad: sys.exit('data sections not supported yet: %s'%[s['name'] for s in bad])
    texts=[s for s in c['scns'] if s['name']=='.text']
    assert len(texts)==1
    t=texts[0]; tidx=c['scns'].index(t)+1     # COFF section numbers are 1-based
    code=c['b'][t['scnptr']:t['scnptr']+t['size']]
    # symbols: our three functions, then '_c_int00' and the node's name (as TI's), then the externals used
    csym={s['idx']:s for s in c['syms']}
    defs={s['name']:s for s in c['syms'] if s['scnum']==tidx and s['sclass']==2}
    for f in (cr,ex,de):
        assert '_'+f in defs, 'no _%s in the object'%f
    syms=[dict(name='_'+f,value=KTEXT_ADDR+defs['_'+f]['value'],scnum=1,sclass=2) for f in (cr,de,ex)]
    syms.append(dict(name='_c_int00',value=0,scnum=0,sclass=2))
    syms.append(dict(name=a.name,value=0,scnum=5,sclass=2))     # the .<UUID> section (Prodtest: 6, after its .const)
    # relocations: the symbol ones (R_REL24 5, R_LD3_REL23 124, RE_PUSH 0x4011, RE_PUSHSV 0xC011) get
    # their symbol renumbered: an external is added as undefined, one of ours (a function whose
    # address the code takes) as defined in section 1; -1 (this section) and the expression
    # operators' constants (RE_PUSHUK, the field stores) stay as they are
    SYMTYPES=(5,124,0x4011,0xC011)
    index={}
    def symidx(r):
        if r[3] not in SYMTYPES or r[1]==0xffffffff: return r[1]
        s=csym[r[1]]
        key=(s['name'],s['scnum'])
        if key not in index:
            if s['scnum']==0: index[key]=len(syms); syms.append(dict(name=s['name'],value=0,scnum=0,sclass=2))
            elif s['scnum']==tidx:
                found=[k for k,x in enumerate(syms) if x['name']==s['name'] and x['scnum']==1]
                if found: index[key]=found[0]
                else: index[key]=len(syms); syms.append(dict(name=s['name'] if s['sclass']==2 else None,noff=-1,value=KTEXT_ADDR+s['value'],scnum=1,sclass=s['sclass']))
            else: sys.exit('relocation against %s in section %d: only .text is supported'%(s['name'],s['scnum']))
        return index[key]
    rels=[(r[0],symidx(r),r[2],r[3]) for r in t['relocs']]
    # .text packets of up to 1024 bytes, cut so that no relocated field (up to 4 bytes) crosses one
    pk=[]; o=0
    while o<len(code):
        end=min(o+1024,len(code))
        if end<len(code):
            for r in rels:
                if end-4<r[0]<end: end=min(end,r[0])
        pk.append(dict(data=code[o:end],relocs=[(r[0]-o,r[1],r[2],r[3]) for r in rels if o<=r[0]<end]))
        o=end
    U=a.uuid.upper().replace('-','_')
    assert len(U)==36
    props=('1024,%s,%s,01H,00H,1024,0200H,080H,0c00H,05H,03H,03e8H,064H,0aH,%s,%s,%s,00H,%s,00H,00H,0ffffffffH,'
           '%s,%s,%s,00H,08000H,iAlgName,1,0ff3f3f00H,0ff3f3f82H,')%(U,a.name,a.prio,a.stack,a.sysstack,a.msgdepth,cr,ex,de)
    ts=time.strftime('%a %b %d %H:%M:%S %Y',time.gmtime())
    vers=ts+'\0'+(a.fname or os.path.basename(a.out))+'\0@(#)*** maps9300\0;;;\0'
    info=[('.dspbridge_symbols',BRIDGE_SYMS+'%s,%s,%s,'%(cr,ex,de)),('.vers',vers),('.dcd_register',U+':0,'),('.'+U,props)]
    scns=[dict(name='.text',paddr=KTEXT_ADDR,vaddr=KTEXT_ADDR,size=len(code),page=0,flags=0x230,packets=pk)]
    for n,txt in info:
        b=u16be(txt); scns.append(dict(name=n,paddr=0,vaddr=0,size=len(b),page=0,flags=0x101,packets=[dict(data=b,relocs=[])]))
    d=dict(fname=(a.fname or os.path.splitext(os.path.basename(a.out))[0]+'.out'),entry=0,resh=0x10203,w4h=0x26,w5h=2,w6=0x9c0000,w7=0x12e0,
           timdat=int(time.time()),scns=scns,syms=syms)
    out=dofw.build(d)
    open(a.out,'wb').write(out)
    # read it back
    r=dofw.parse(out)
    print('%s: %d bytes, .text %d bytes, %d symbols, %d relocations'%(a.out,len(out),len(code),len(syms),sum(len(p['relocs']) for p in pk)))
    for s in r['syms']: print('  sym %-22s %6x scn %d class %d'%(s['name'],s['value'],s['scnum'],s['sclass']))
main()
