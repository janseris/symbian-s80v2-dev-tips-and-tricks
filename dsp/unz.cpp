#include <cstdio>
#include <cstdlib>
#include <cstring>
void InflateUnCompress(unsigned char* source, int sourcesize,unsigned char* dest, int destsize);
int main(int c,char**v){
 FILE*f=fopen(v[1],"rb"); fseek(f,0,2); long n=ftell(f); fseek(f,0,0);
 unsigned char*b=(unsigned char*)malloc(n); fread(b,1,n,f); fclose(f);
 unsigned int un=*(unsigned int*)(b+0x7c);
 unsigned char*o=(unsigned char*)calloc(1,0x7c+un);
 memcpy(o,b,0x7c);
 InflateUnCompress(b+0x80,n-0x80,o+0x7c,un);
 f=fopen(v[2],"wb"); fwrite(o,1,0x7c+un,f); fclose(f);
 printf("%s: %u bytes\n",v[2],0x7c+un); return 0;}
