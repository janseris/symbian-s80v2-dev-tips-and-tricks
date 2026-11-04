#!/bin/sh
# Sets up TI's C5500 code generation tools (4.4.1, 32-bit static Linux binaries) where 32-bit
# programs can't run natively (Cowork's Linux VM: "Bad system call"): through qemu-i386-static
# (user mode, no root). The drivers (cl55, masm55) start their siblings from their own folder, so
# each tool gets a folder of its own (w/<tool>/) beside wrappers for all the others.
#   setup_cgt55.sh <cgt55 tarball or install dir> [qemu-user-static .deb] [target dir, ~/ti55]
# The tarball: the installer's tree (ti_cgt_c5500_4.4.1_setup_linux_x86.bin --mode silent
# --prefix <dir>, on a Linux with libc6:i386), tar'ed. TI's files: never commit them.
# Then: ~/ti55/cgt55/bin/cl55 -v5510 --memory_model=large -O2 -c x.c
set -e
SRC=$1; DEB=$2; T=${3:-$HOME/ti55}
mkdir -p "$T"
if [ -d "$SRC" ]; then cp -r "$SRC" "$T/cgt55"; else tar -xJf "$SRC" -C "$T"; fi
if [ -z "$DEB" ]; then (cd "$T" && apt-get download qemu-user-static); DEB=$(ls "$T"/qemu-user-static*.deb | head -1); fi
mkdir -p "$T/qx" && dpkg-deb -x "$DEB" "$T/qx"
Q=$T/qx/usr/bin/qemu-i386-static
B=$T/cgt55/bin
cd "$B"
mkdir -p w
for f in *; do
    [ -f "$f" ] && file "$f" | grep -q "ELF 32-bit" || continue
    mkdir -p "w/$f" && mv "$f" "w/$f/$f"
done
for t in $(ls w); do
    for o in $(ls w); do
        [ "$o" = "$t" ] && continue
        printf '#!/bin/sh\nexec %s "%s/w/%s/%s" "$@"\n' "$Q" "$B" "$o" "$o" > "w/$t/$o"; chmod +x "w/$t/$o"
    done
    printf '#!/bin/sh\nexec %s "%s/w/%s/%s" "$@"\n' "$Q" "$B" "$t" "$t" > "$t"; chmod +x "$t"
done
echo "cl55: $B/cl55"
