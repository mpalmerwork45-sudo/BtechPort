"""Supply original town-loader file boundaries to the bounded CPU oracle."""
import struct
from combat_oracle import ROOT
from make_city_edge_vectors import span


def load_town(m, town):
    raw=(ROOT/f'Original DOS/MAP{town}.MTP').read_bytes()
    m.reset();m.write(m.ds+0x4fc0,(0x020304).to_bytes(3,'little'))
    noise=bytes(m.call(0x187f,0xbc0)&255 for _ in range(256))
    width,height=raw[3:5];rx=struct.unpack_from('<H',raw,389)[0]>>8;ry=struct.unpack_from('<H',raw,421)[0]>>12
    m.write(m.buffer+0x9fb,noise);m.call(0x187f,0x104e,16*ry+rx)
    m.write(m.buffer+0x101d,raw[541:])
    span(m,0,0x3050,0x30bb,m.ds//16,{6:4,-12:0,-8:0,-2:width//8,-10:height//8})
    span(m,0x187f,0x1886,0x18d7,m.buffer//16)
    # These are the loader's file-derived tables, not executable changes.
    m.write(m.state+0x4564,raw[389:421]);m.write(m.state+0x4596,raw[421:453])
    m.write(m.buffer+0xa561,raw[133:389]);m.write(m.state+0xd346,[0]);m.word(m.ds+0x150,85)
    return raw,rx*128,ry*128


def cursor(m,x,y):
    px=(x//128<<8)|(x&127);py=(y//128<<12)|(y&127)
    # A controlled caller position is not a walk across all intervening
    # sectors. Supply it directly, then execute the actual viewport builders.
    m.word(m.buffer+0xa44b,px);m.word(m.buffer+0xa44d,py)
    m.call(0x187f,0x1314,px,py);m.call(0x187f,0x1df8)
    return px,py
