/* SPDX-License-Identifier: GPL-2.0-or-later
 * Test-only bounded HBPL1 decoder, adapted from Dave Coffin's HBPL1 portion
 * of hbpldecode.c (see vendor/foo2zjs). Never installed as a printer filter.
 * Decoding follows the upstream decoder, independently of the encoder. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void die(const char *s) { fprintf(stderr,"decode: %s\n",s); exit(1); }
static void read_exact(FILE *f, void *p, size_t n) { if (fread(p,1,n,f)!=n) die("truncated input"); }
static uint32_t le(const unsigned char *p) { return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24); }
typedef struct { const unsigned char *p; size_t size, bit; } Bits;
static unsigned bits(Bits *s, unsigned n)
{
    if (n>24 || s->bit+n > s->size*8) die("truncated bitstream");
    unsigned v=0;
    for (unsigned i=0;i<n;i++,s->bit++) v=(v<<1)|((s->p[s->bit/8]>>(7-s->bit%8))&1);
    return v;
}
static unsigned length(Bits *s)
{
    const unsigned sizes[]={3,3,3,4,5,6,9,14}, base[]={26,34,42,50,66,98,162,674};
    switch(bits(s,3)) {
    case 0: case 1: s->bit--; return 1;
    case 2: return 2; case 3: return 3;
    case 4: return 4+bits(s,1); case 5: return 6+bits(s,2); case 6: return 10+bits(s,4);
    }
    unsigned i=bits(s,3); return base[i]+bits(s,sizes[i]);
}
static int difference(Bits *s)
{
    const unsigned code[]={1,2,3,5,5,6,2,4,8,16,48,80};
    unsigned i=bits(s,3);
    if(i==0) return 0; if(i==1) return 1; if(i==2) return -1;
    if(i==7) i+=bits(s,1);
    unsigned sign=bits(s,1), v=code[i+3]+bits(s,code[i-3]);
    return sign ? -(int)v : (int)v;
}
static unsigned token(Bits *s, int table)
{
    /* Prefix tree from the upstream decoder's expanded Huffman table. */
    if (!bits(s,1)) return table ? 5 : 0;
    if (!bits(s,1)) return table ? 0 : 5;
    if (!bits(s,1)) return 1;
    unsigned tail=bits(s,2);
    if(tail==3) { if(bits(s,1)) die("invalid table-switch token"); return 6; }
    return tail+2;
}
static void decode(FILE *f, const char *prefix, const unsigned char *h, uint32_t size)
{
    unsigned w=le(h+39), height=le(h+43), page=le(h+33);
    int color=h[55]==139, depth=color?4:1;
    if((h[55]!=9 && !color)||!w||!height||w>5200||height>7100||size<48||size>256u*1024*1024)
        die("invalid page header");
    unsigned char *in=malloc(size);
    size_t pixels=(size_t)w*height;
    unsigned char *storage=malloc((pixels+w+1)*4);
    if(!in||!storage) die("out of memory");
    memset(storage,color?255:0,(pixels+w+1)*4);
    unsigned char *out=storage+(w+1)*4;
    read_exact(f,in,size);
    Bits stream[5]={0}; size_t pos=48;
    for(int i=0;i<=depth;i++) {
        uint32_t n=le(in+32+i*4);
        /* The fifth size overlaps the first stream; infer its final length. */
        if(i==4) n=(uint32_t)(size-pos);
        if(n>size-pos) die("invalid stream size");
        stream[i]=(Bits){in+pos,n,0}; pos+=n;
    }
    if(pos!=size) die("unconsumed page data");
    int rotor[]={0,1,2,3,4}, dirs[]={-1,-(int)w,-(int)w-1,1-(int)w,color?2-(int)w:-8};
    size_t off=0; int table=0, bit=0;
    while(off<pixels) {
        unsigned t=token(stream,table);
        if(t==6) {table=!table;continue;}
        if(t==5) {
            for(int c=0;c<depth;c++) out[off*4+c]=(unsigned char)(out[((ptrdiff_t)off-1)*4+c]+difference(stream+1+c));
            off++;bit=0;continue;
        }
        unsigned run=length(stream), raw=t+bit;
        if(raw>4||run>pixels-off) die("invalid run");
        int dir=dirs[rotor[raw]];bit=run<17057;
        while(run--) {
            ptrdiff_t from=(ptrdiff_t)off+dir;
            if(from<-(ptrdiff_t)(w+1)||from>=(ptrdiff_t)off) die("invalid reference");
            memcpy(out+off*4,out+from*4,4);off++;
        }
        if(raw) {int r=rotor[raw];for(unsigned j=raw;j;j--)rotor[j]=rotor[j-1];rotor[0]=r;}
    }
    char name[1024];snprintf(name,sizeof(name),"%s-%u.%s",prefix,page,color?"ppm":"pgm");
    FILE *dest=fopen(name,"wb");if(!dest)die("cannot write image");
    fprintf(dest,"P%d\n%u %u\n255\n",color?6:5,w,height);
    unsigned char *row=malloc(w*3);if(!row)die("out of memory");
    for(unsigned y=0;y<height;y++) {
        for(unsigned x=0;x<w;x++) {
            unsigned char *p=out+((size_t)y*w+x)*4;
            if(color)for(int c=0;c<3;c++)row[x*3+c]=(255-p[0])*(255-p[c+1])/255;
            else row[x]=255-p[0];
        }
        if(fwrite(row,1,w*(color?3:1),dest)!=w*(unsigned)(color?3:1))die("write failed");
    }
    free(row);fclose(dest);free(storage);free(in);
    printf("page=%u width=%u height=%u color=%d paper=%u\n",page,w,height,color,h[12]);
}
int main(int argc,char **argv)
{
    if(argc!=3)die("usage: decode-hbpl1 input.hbpl output-prefix");
    FILE *f=fopen(argv[1],"rb");if(!f)die("cannot open input");
    char line[1024];int found=0;
    while(fgets(line,sizeof(line),f))if(!strcmp(line,"@PJL ENTER LANGUAGE=HBPL\n")){found=1;break;}
    if(!found)die("missing HBPL preamble");
    unsigned char start[12];read_exact(f,start,12);
    if(start[0]!='A')die("missing job header");
    unsigned pages=0;
    for(;;) {
        int c=fgetc(f);if(c=='B')break;if(c!='C')die("missing page header");
        unsigned char h[90]={0};h[0]='C';read_exact(f,h+1,85);
        unsigned n=h[85]==0xa2?2:h[85]==0xa4?4:0;if(!n)die("invalid size tag");
        read_exact(f,h+86,n);
        uint32_t size=n==2 ? h[86]+((unsigned)h[87]<<8) : le(h+86);
        decode(f,argv[2],h,size);pages++;
        if(fgetc(f)!='S'||fgetc(f)!='D')die("missing page trailer");
    }
    char end[64];if(!fgets(end,sizeof(end),f)||strcmp(end,"\033%-12345X@PJL EOJ\n")||fgetc(f)!=EOF)die("invalid job trailer");
    fclose(f);return pages?0:1;
}
