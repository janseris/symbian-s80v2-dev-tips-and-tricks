import struct,sys,subprocess,os
def load(fn):
    b=open(fn,'rb').read()
    if struct.unpack_from('<I',b,0x1c)[0]==0x101f7afc:
        out='/tmp/u.bin'; subprocess.run(['./unz',fn,out],capture_output=True); b=open(out,'rb').read()
    return b
def imports(b):
    imp=struct.unpack_from('<I',b,0x6c)[0]; cnt=struct.unpack_from('<i',b,0x54)[0]
    off=imp+4; r=[]
    for i in range(cnt):
        no,n=struct.unpack_from('<Ii',b,off)
        name=b[imp+no:b.index(b'\0',imp+no)].decode('latin1')
        r.append((name,struct.unpack_from('<%dI'%n,b,off+8))); off+=8+4*n
    return r
if __name__=='__main__':
    for fn in sys.argv[1:]:
        b=load(fn); open('out2/'+os.path.basename(fn)+'.u','wb').write(b)
        print('==',os.path.basename(fn), 'uid3 %x'%struct.unpack_from('<I',b,8)[0])
        for n,o in imports(b):
            if 'EUSER' in n: continue
            print('   ',n,o)
