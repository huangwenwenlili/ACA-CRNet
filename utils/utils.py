# -*- coding: utf-8 -*-
"""
Created on May 9 10:24:49 2024

@author: Wenli Huang
"""

import cv2
import  torch as t

def save_state_dict(net,epoch,iteration,save_path):
    net_path = os.path.join(save_path,"net_epoch_{}_iteration_{}.pth".format(epoch,iteration))
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    torch.save(net.state_dict(),net_path)
"""   
#Generate Cloud and Shadow Mask
def Generate_Cluod_Mask(img,Tcl=0.2):
    toa = img.select(['B1','B2','B3','B4','B5','B6','B7','B8','B8A', 'B9','B10', 'B11','B12']) \
              .divide(10000)
    toa = toa.addBands(img.select(['QA60']))
    # ['QA60', 'B1','B2',    'B3',    'B4',   'B5','B6','B7', 'B8','  B8A', 'B9',          'B10', 'B11','B12']
    # ['QA60','cb', 'blue', 'green', 'red', 're1','re2','re3','nir', 'nir2', 'waterVapor', 'cirrus','swir1', 'swir2'])
    #Compute several metrics, get min value
    score = ee.Image(1)
    #Clouds in blue and cirrus bands are bright.
    score = score.min(rescale(toa, 'img.B2', [0.1, 0.5]))
    score = score.min(rescale(toa, 'img.B1', [0.1, 0.3]))
    score = score.min(rescale(toa, 'img.B1 + img.B10', [0.15, 0.2]))
    # Clouds are bright in visible RGB band.
    score = score.min(rescale(toa, 'img.B4 + img.B3 + img.B2', [0.2, 0.8]))
    #NDSI =
    #[Green(band3)-SW IR(band11)]/
    #[Green(band3)+SW IR(band11)] ,
    #rescaled range [0.8; 0.6]
    #normalized difference snow index=>NDSI
    ndsi = img.normalizedDifference(['B3', 'B11'])
    score=score.min(rescale(ndsi, 'img', [0.8, 0.6]))
    
    #Perform closing operation
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5,5))
    score= cv2.morphologyEx(score,cv2.MORPH_CLOSE,kernel,iterations=2)
    #mean of image
    score=Averaging(score)
    #clip
    score=np.clip(score,0,1)
    #Generate cloudmask
    score[score>Tcl]=1
    score[score<Tcl]=0
    return score
"""
def Generate_Cluod_Mask(img,Tcl=0.2):
    toa=img/10000
    _,length,width = img.shape
    score = np.ones((1,length,width),dtype=np.float32)
    #Clouds in blue and cirrus bands are bright.
    score = np.minimum(Rescale(toa[2,:,:],[0.1,0.5]),score)
    score = np.minimum(Rescale(toa[1,:,:],[0.1,0.3]),score)
    score = np.minimum(Rescale(toa[1,:,:]+toa[10,:,:],[0.15,0.2]),score)
    #Clouds are bright in visible RGB band.
    score = np.minimum(Rescale(toa[2,:,:]+toa[3,:,:]+toa[4,:,:],[0.2,0.8]),score)
    #NDSI =
    #[Green(band3)-SW IR(band11)]/
    #[Green(band3)+SW IR(band11)] ,
    #rescaled range [0.8; 0.6]
    #normalized difference snow index=>NDSI
    ndsi  = (toa[3,:,:]-toa[11,:,:])/(toa[3,:,:]+toa[11,:,:])
    score = np.minimum(Rescale(ndsi,[0.8,0.6]), score)
    #closing operation
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5,5))
    score= cv2.morphologyEx(score,cv2.MORPH_CLOSE,kernel,iterations=2)
    #filter
    score=cv2.blur(score,(7,7))
    #clip
    score=np.clip(score,0,1)
    #Generate cloudmask
    score[score>Tcl]=1
    score[score<Tcl]=0
    #Cloud_Mask
    return score

#cv2.blur(img,(7,7))
#The image averaging operation is used in Generate_Cloud_Mask. A better method has been found and will be deprecated.
def Averaging(img):
    img_H,img_W,img_ch = img.shape
    retimg=np.zeros((img_H,img_W,img_ch),dtype=np.uint8)
    for dstX in range(3,img_H-3):
        for dstY in range(3,img_W-3):
            average = np.zeros((img_ch))
            for i in [-3,-2,-1,0,1,2,3]:
                for j in [-3,-2,-1,0,1,2,3]:
                    average+=img[dstX+i,dstY+j]
            retimg[dstX,dstY]=average/49
    return retimg

#The re-scaling function is used in Generate_Cluod_Mask.
def Rescale(img,thresholds):
    return (img-thresholds[0])/(thresholds[1]-thresholds[0])
"""
def rescale(img, exp, thresholds):
    return img.expression(exp, {"img": img}) \
              .subtract(thresholds[0]) \
              .divide(thresholds[1] - thresholds[0])
"""
              
#Generate shadow mask
def Generate_Shadow_Mask(img,T_csi=3/4,T_wbi=5/6):
    img=img/1000
    csi = (img[7,:,:]+img[10,:,:])/2    
    wbi =img[0,:,:] 
    # ['QA60', 'B1','B2',    'B3',    'B4',   'B5','B6','B7', 'B8','  B8A', 'B9',          'B10', 'B11','B12']
    # ['QA60','cb', 'blue', 'green', 'red', 're1','re2','re3','nir', 'nir2', 'waterVapor', 'cirrus','swir1', 'swir2']
    shadow_mask = np.zeros((img.shape[1],img.shape[2]))
    shadow_mask[csi.any()<T_csi and wbi.any()<T_wbi]=1
    return np.expand_dims(shadow_mask,0)

#Generate cloud mask and cloud shadow mask
def Generate_Cloud_and_Shadow_Mask(img):
    return np.logical_or(Generate_Cluod_Mask(img),Generate_Shadow_Mask(img)).astype(float)

def uint16to8(bands, lower_percent=0.001, higher_percent=99.999,is_bri=False):
    out = np.zeros_like(bands,dtype = np.uint8) 
    n = bands.shape[0]
    brighten_limit = 2000
    if is_bri:
        bands = np.clip(bands, 0, brighten_limit)

    for i in range(n): 
        a = 0 # np.min(band) 
        b = 255 # np.max(band) 
        c = np.percentile(bands[i, :, :], lower_percent) 
        d = np.percentile(bands[i, :, :], higher_percent) 
        
        t = a + (bands[i, :, :] - c) * (b - a) / (d - c) 
        t[t<a] = a 
        t[t>b] = b 
        out[i, :, :] = t 
    return out    

def getRGBImg(r,g,b,img_size=256):
    img=np.zeros((img_size,img_size,3),dtype=np.uint8)
    img[:,:,0]=b #r
    img[:,:,1]=g
    img[:,:,2]=r #b
    return img

def save_result_img(img, save_path):
    """Save the training or testing results to disk"""

    # save predicted image with discriminator score
    #mkdir(save_path)
    img_numpy = tensor2im(img.data)
    save_image(img_numpy, save_path)

def SaveImg(img,path):
    cv2.imwrite(path, img)
""" 
Name Rules
['QA60', 'B1','B2',    'B3',    'B4',   'B5','B6','B7', 'B8','  B8A', 'B9',          'B10', 'B11','B12']
['QA60','cb', 'blue', 'green', 'red', 're1','re2','re3','nir', 'nir2', 'waterVapor', 'cirrus','swir1', 'swir2'])
[        1,    2,      3,       4,     5,    6,    7,    8,     9,      10,            11,      12,     13]) #gdal
[        0,    1,      2,       3,     4,    5,    6,    7,     8,      9,            10,      11,     12]) #numpy
[              BB      BG       BR                       BNIR                                  BSWIR1    BSWIR2
 ge. Bands 1, 2, 3, 8, 11, and 12 were utilized as BB , BG , BR , BNIR , BSWIR1 , and BSWIR2, respectively.
 
oprations:
img_cld   torch.Size([1, 15, 256, 256]) 取RGB
img_fake  torch.Size([1, 13, 256, 256]) 取RGB
img_truth torch.Size([1, 13, 256, 256]) 取RGB
img_csm   torch.Size([1, 1, 256, 256])  转RGB
"""

def GetQuadrupletsImg(img_cld,img_fake,img_truth,img_csm,img_size=256,scale=2000):
    #print(img_cld.shape,img_fake.shape,img_truth.shape)
    output_img=np.zeros((img_size,5*img_size,3),dtype=np.uint8)
    
    # Compress dimensions, convert to NUMPY, convert dimensions, multiply by the scaling ratio, and then convert to int8
    # After the transformation, the dimensions are 256*256*15   256*256*15  256*256*15  256*256*1

    img_sar = uint16to8((t.squeeze(img_cld).cpu().numpy() * scale).astype("uint16")).transpose(1, 2, 0)
    img_cld_nobright = uint16to8((t.squeeze(img_cld).cpu().numpy() * scale).astype("uint16")).transpose(1, 2, 0)

    img_cld=  uint16to8((t.squeeze(img_cld  ).cpu().numpy()*scale).astype("uint16"),is_bri=True).transpose(1,2,0)
    img_fake= uint16to8((t.squeeze(img_fake ).cpu().numpy()*scale).astype("uint16")).transpose(1,2,0)
    img_truth=uint16to8((t.squeeze(img_truth).cpu().numpy()*scale).astype("uint16")).transpose(1,2,0)
    
    img_csm=t.squeeze(img_csm,dim=0).cpu().numpy().transpose(1,2,0)
    #print(img_cld.shape,img_fake.shape,img_truth.shape)
    #get RGB
    img_sar_RGB = getRGBImg(np.zeros_like(img_sar[:,:,0]),img_sar[:,:,0], img_sar[:,:,1], img_size)
    img_cld_nobright_RGB = getRGBImg(img_cld_nobright[:, :, 5], img_cld_nobright[:, :, 4], img_cld_nobright[:, :, 3], img_size)
    img_cld_RGB=getRGBImg(img_cld[:,:,5], img_cld[:,:,4], img_cld[:,:,3], img_size)
    img_fake_RGB=getRGBImg(img_fake[:,:,3], img_fake[:,:,2], img_fake[:,:,1], img_size)
    img_truth_RGB=getRGBImg(img_truth[:,:,3], img_truth[:,:,2], img_truth[:,:,1], img_size)
    #print(img_cld_RGB,img_fake_RGB,img_truth_RGB)
    #convert CSM to RGB
    img_csm_RGB=np.concatenate((img_csm, img_csm, img_csm),axis=-1)*255
    
    #merge
    output_img[:,0*img_size:1*img_size,:]=img_cld_nobright_RGB
    output_img[:,1*img_size:2*img_size,:]=img_fake_RGB
    output_img[:,2*img_size:3*img_size,:]=img_truth_RGB
    output_img[:,3*img_size:4*img_size,:]=img_csm_RGB
    output_img[:, 4 * img_size:5 * img_size, :] = img_sar_RGB
    return output_img,img_cld_RGB,img_fake_RGB,img_truth_RGB,img_csm_RGB,img_sar_RGB,img_cld_nobright_RGB

import numpy as np
import os
import imageio
import torch


# convert a tensor into a numpy array
def tensor2im(image_tensor, bytes=255.0, imtype=np.uint8):
    if image_tensor.dim() == 3:
        image_numpy = image_tensor.cpu().float().numpy()
    else:
        image_numpy = image_tensor[0].cpu().float().numpy()
    image_numpy = (np.transpose(image_numpy, (1, 2, 0)) + 1) / 2.0 * bytes

    return image_numpy.astype(imtype)

# conver a tensor into a numpy array
def tensor2array(value_tensor):
    if value_tensor.dim() == 3:
        numpy = value_tensor.view(-1).cpu().float().numpy()
    else:
        numpy = value_tensor[0].view(-1).cpu().float().numpy()
    return numpy

def save_image(image_numpy, image_path):
    if image_numpy.shape[2] == 1:
        image_numpy = image_numpy.reshape(image_numpy.shape[0], image_numpy.shape[1])

    imageio.imwrite(image_path, image_numpy)

def mkdirs(paths):
    if isinstance(paths, list) and not isinstance(paths, str):
        for path in paths:
            mkdir(path)
    else:
        mkdir(paths)

def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)