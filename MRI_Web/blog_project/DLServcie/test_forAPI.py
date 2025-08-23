import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))  

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import uvicorn
import numpy as np
import scipy.io as io

import tempfile
import cv2
from skimage.metrics import structural_similarity as compare_ssim
from skimage.metrics import peak_signal_noise_ratio as compare_psnr
from skimage.metrics import mean_squared_error as compare_mse
#from basicsr.testImage import test_Image
import matplotlib.pyplot as plt
import time

# flake8: noqa
import os.path as osp
from basicsr.test import test_pipeline

import DiffIR.archs
import DiffIR.data
import DiffIR.models
import os
import os.path as osp  
import numpy as np

import scipy
import scipy.io as io
from scipy.io import loadmat , savemat

import PIL.Image as Image
import matplotlib.pyplot as plt  

import cv2
from skimage.metrics import structural_similarity as compare_ssim
from skimage.metrics import peak_signal_noise_ratio as compare_psnr
from skimage.metrics import mean_squared_error as compare_mse



from basicsr.testImage import test_Image  
from basicsr.test import test_pipeline  



app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def write_images(x, image_save_path):
    x = np.clip(x * 255, 0, 255).astype(np.uint8)
    cv2.imwrite(image_save_path, x)

def ensure_folder_exists(save_path):
    if not os.path.exists(save_path):
        os.makedirs(save_path)

@app.post("/process/")
async def process_image(
    image: UploadFile = File(...),
    mask: UploadFile = File(None),
    model_type: str = Form(...)
):
    try:
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 保存上传的图像文件
            input_path = os.path.join(temp_dir, "input.mat")
            with open(input_path, "wb") as f:
                f.write(await image.read())
            
            # 创建保存结果的目录
            save_path = os.path.join(temp_dir, "results")
            ensure_folder_exists(save_path)
            
            # 读取输入数据
            coil = 1
            ori_input = np.zeros([256, 256, coil], dtype=np.complex64)
            ori_input[:,:,0] = io.loadmat(input_path)['resESPIRiT_sos']
            
            print("ori_input.shape=", ori_input.shape)
            ori_input = ori_input / np.max(abs(ori_input))
            ori_data_sos = np.sqrt(np.sum(np.square(np.abs(ori_input)), axis=2))
            write_images(abs(ori_data_sos), os.path.join(save_path, 'ori.png'))
            
            # 读取mask
            mask_array = np.zeros((coil, 256, 256))
            if mask:
                # 保存上传的mask文件
                mask_path = os.path.join(temp_dir, "mask.mat")
                with open(mask_path, "wb") as f:
                    f.write(await mask.read())
                mask_item = io.loadmat(mask_path)['mask']
            else:
                # 使用默认mask
                mask_path = '/media/mri/data/xx/DFTM/测试数据包/mask/poisson/6.mat'
                mask_item = io.loadmat(mask_path)['mask']
            
            for i in range(coil):
                mask_array[i,:,:] = mask_item
            
            mask2 = mask_array
            mask2_img = np.sqrt(np.sum(np.square(np.abs(mask2)), axis=0))
            mask2_img = mask2_img/np.max(np.abs(mask2_img))
            
            # 欠采样处理
            Kdata = np.zeros((coil, 256, 256), dtype=np.complex64)
            Ksample = np.zeros((coil, 256, 256), dtype=np.complex64)
            zeorfilled_data = np.zeros((coil, 256, 256), dtype=np.complex64)
            
            for i in range(coil):
                Kdata[i, :, :] = np.fft.fft2(ori_input[:, :, i])
                Kdata[i, :, :] = np.fft.fftshift(Kdata[i, :, :])
                Ksample[i,:,:] = np.multiply(mask_array[i,:,:], Kdata[i,:,:])
                zeorfilled_data[i,:,:] = np.fft.ifft2(Ksample[i,:,:])
            
            # 制作 sos 的零填充图像
            zeorfilled_data_sos = np.sqrt(np.sum(np.square(np.abs(zeorfilled_data)), axis=0))
            ori_data_sos = ori_data_sos/np.max(np.abs(ori_data_sos))
            zeorfilled_data_sos = zeorfilled_data_sos/np.max(np.abs(zeorfilled_data_sos))
            
            # 准备输入数据
            Lq = np.tile(zeorfilled_data_sos, (1, 3, 1, 1))
            hq = np.tile(ori_data_sos, (1, 3, 1, 1))
            
            # 重建
            save_image = np.zeros((256, 256, 3), dtype=np.uint8)
            root_path = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir))
            save_image = test_Image(Lq, hq, save_image, root_path)
            save_image_sos = save_image[:,:,0]
            
            # CD 处理
            save_image_sos = save_image_sos/np.max(np.abs(save_image_sos))
            recKdata = np.fft.fft2(save_image_sos)
            recKdata = np.fft.fftshift(recKdata)
            Ksample = Ksample/np.max(np.abs(Ksample))
            recKdata = recKdata/np.max(np.abs(recKdata))
            
            DC_Image = np.zeros((coil,256,256), dtype=np.complex64)
            k_complex2 = np.zeros((coil,256,256), dtype=np.complex64)
            
            for i in range(coil):
                k_complex2[i,:,:] = Ksample[i,:,:] + recKdata*(1-mask2[i,:,:])
                DC_Image[i,:,:] = np.fft.ifft2(k_complex2[i,:,:])
            
            rec_Image_sos = np.sqrt(np.sum(np.square(np.abs(DC_Image)), axis=0))
            rec_Image_sos = rec_Image_sos/np.max(np.abs(rec_Image_sos))
            
            # 计算指标
            psnr = compare_psnr(255*abs(rec_Image_sos), 255*abs(ori_data_sos), data_range=255)
            ssim = compare_ssim(abs(rec_Image_sos), abs(ori_data_sos), data_range=1)
            
            # 保存结果
            result_path = os.path.join(save_path, 'result.mat')
            io.savemat(result_path, {
                'zeorfilled_data_sos' : zeorfilled_data_sos,
                'rec_Image_sos': rec_Image_sos,
                'psnr': psnr,
                'ssim': ssim
            })
            
            # 读取处理后的结果
            with open(result_path, 'rb') as f:
                processed_data = f.read()
            
            return Response(
                content=processed_data,
                media_type="application/octet-stream",
                headers={
                    "X-PSNR": str(psnr),
                    "X-SSIM": str(ssim)
                }
            )
            
    except Exception as e:
        print(f"处理出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("启动 FastAPI 服务...")
    uvicorn.run(app, host="0.0.0.0", port=8080)