import sys,struct,glob,os; sys.path.insert(0,'.')
import dof
def txt(raw): return raw.decode('utf-16-be',errors='replace').replace('\x00','|').strip('|')
for fn in sorted(glob.glob('./files/*55l.bin'))+['./files/Dsp_image_dof.bin']:
    d=dof.parse(fn); b=d['b']
    print('=====',os.path.basename(fn), d['fname'])
    for sc in d['scns']:
        n=sc['name']
        if n in ('.vers','.dcd_register') or (n.startswith('.') and len(n)==37 and n[9]=='_'):
            o=sc['pkt']; nrel,psz,ck=struct.unpack_from('<iiI',b,o)
            print('  %s: %s'%(n, txt(b[o+12:o+12+psz])))
