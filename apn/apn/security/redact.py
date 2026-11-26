from __future__ import annotations
import cv2
import numpy as np


def mask_person(image:np.ndarray,bbox:tuple[float,float,float,float],mode:str="masked")->np.ndarray:
    result=image.copy()
    if mode=="raw":return result
    x1,y1,x2,y2=map(int,bbox);x1=max(0,x1);y1=max(0,y1);x2=min(result.shape[1],x2);y2=min(result.shape[0],y2)
    if mode=="metadata_only":
        result[:]=0;cv2.rectangle(result,(x1,y1),(x2,y2),(42,210,190),-1);return result
    head_end=min(y2,y1+max(1,int((y2-y1)*.22)));region=result[y1:head_end,x1:x2]
    if region.size:
        kernel=max(3,(min(region.shape[:2])//3)|1);result[y1:head_end,x1:x2]=cv2.GaussianBlur(region,(kernel,kernel),0)
    return result
