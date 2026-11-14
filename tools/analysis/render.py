import numpy as np
from PIL import Image
def tiles_px(t):
    """t: (n,128) uint8 -> (n,16,16) pens"""
    n=len(t); r=t.reshape(n,16,2,4)  # row, half, plane byte
    bits=np.unpackbits(r,axis=3,bitorder='big').reshape(n,16,2,4,8)  # plane byte -> 8 bits (x)
    # pen = sum plane bits; plane order: byte0..3 -> plane weight? use 1,2,4,8
    pen=(bits[:,:,:,0,:]*1+bits[:,:,:,1,:]*2+bits[:,:,:,2,:]*4+bits[:,:,:,3,:]*8)
    return pen.reshape(n,16,16)
def sheet(t, width=16, cols=8, scale=1, mask=None):
    px=tiles_px(t)
    if mask is not None: px[~mask]=15
    n=len(t); rows=(n+width-1)//width
    img=np.full((rows*16,width*16),15,np.uint8)
    for i in range(n):
        y,x=divmod(i,width); img[y*16:y*16+16,x*16:x*16+16]=px[i]
    # split into columns
    h=(rows*16+cols-1)//cols
    out=np.full((h,cols*(width*16+8)),15,np.uint8)
    for c in range(cols):
        part=img[c*h:(c+1)*h]; out[:len(part),c*(width*16+8):c*(width*16+8)+width*16]=part
    im=Image.fromarray(((15-out)*17).astype(np.uint8))
    if scale!=1: im=im.resize((int(im.width*scale),int(im.height*scale)))
    return im
