import struct,sys
F=['iUid1','iUid2','iUid3','iCheck','iEntryPoint','iCodeAddress','iDataAddress','iCodeSize','iTextSize','iDataSize','iBssSize','iHeapMin','iHeapMax','iStack','iDllRefTable','iExportDirCount','iExportDir','iCheckSumCode','iFormat','iVersion','iFlags','iPriority','iDataBssLinearBase','iNextExtension','iHwVariant']
def hdr(b):
    v=struct.unpack_from('<25I',b,0); return dict(zip(F,v))
if __name__=='__main__':
    for fn in sys.argv[1:]:
        b=open(fn,'rb').read(); h=hdr(b)
        print(fn, {k:hex(v) for k,v in h.items()})
