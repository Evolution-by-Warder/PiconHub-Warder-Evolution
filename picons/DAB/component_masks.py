"""Stable alpha-connected components for explicitly reviewed full glyph masks."""
from PIL import Image
from pathlib import Path
from collections import deque

def components(image):
 w,h=image.size;a=image.getchannel('A');mask=bytearray(a.tobytes());result=[]
 for start in range(w*h):
  if not mask[start]:continue
  mask[start]=0;todo=[start];pixels=[]
  while todo:
   q=todo.pop();pixels.append(q);x,y=q%w,q//w
   for dx,dy in ((-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)):
    nx,ny=x+dx,y+dy
    if 0<=nx<w and 0<=ny<h:
     i=ny*w+nx
     if mask[i]:mask[i]=0;todo.append(i)
  result.append(pixels)
 return result
