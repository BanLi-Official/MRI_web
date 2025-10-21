#@title Autoload all modules

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import uvicorn
import numpy as np
import scipy.io as io

from dataclasses import dataclass, field
import matplotlib.pyplot as plt
import io
import csv
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib
import importlib
import os
import functools
import itertools
import torch
from losses import get_optimizer
from models.ema import ExponentialMovingAverage

import torch.nn as nn
import numpy as np
import tensorflow as tf
import tensorflow_datasets as tfds
import tensorflow_gan as tfgan
import tqdm
import io
import likelihood
import controllable_generation
from utils import restore_checkpoint
sns.set(font_scale=2)
sns.set(style="whitegrid")

import models
from models import utils as mutils
from models import ncsnv2
from models import ncsnpp
from models import ddpm as ddpm_model
from models import layerspp
from models import layers
from models import normalization
from likelihood import get_likelihood_fn
from sde_lib import VESDE, VPSDE, subVPSDE

from PIL import Image
import os

'''
sampling2_parallel_svd
sampling2_parallel_svd_仅加T1
sampling2_parallel_svd_仅加T1_DCT1
sampling2_parallel_svd_仅加T1_迭代T1
sampling2_parallel_svd_加PD_DCPD
sampling2_parallel_svd_拼接
'''
import WKGM_sampling_API as sampling_svd
'''
from sampling2_parallel_svd import (ReverseDiffusionPredictor, 
                      LangevinCorrector, 
                      EulerMaruyamaPredictor, 
                      AncestralSamplingPredictor, 
                      NoneCorrector, 
                      NonePredictor,
                      AnnealedLangevinDynamics)
'''
import datasets
import os.path as osp





import hbz_waigua
import logging
from collections import OrderedDict
import time
import scipy.io

import tempfile
import scipy
import scipy.io as io
from scipy.io import loadmat , savemat

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
    #try:

                # @title Load the score-based model
        sde = 'VESDE' #@param ['VESDE', 'VPSDE', 'subVPSDE'] {"type": "string"}
        if sde.lower() == 'vesde':
          from configs.ve import SIAT_kdata_ncsnpp_test_w as configs  # 修改config
          #from configs.ve import bedroom_ncsnpp_continuous as configs  # 修改config
          #ckpt_filename = "exp/ve/cifar10_ncsnpp_continuous/checkpoint_24.pth"
          model_num = 'checkpoint.pth'
          #ckpt_filename = '/home/lqg/桌面/ncsn++/score_sde_pytorch-SIAT_MRIRec_noise1_multichannel6/exp/checkpoints/checkpoint_33.pth'  # 修改checkpoint  
          #ckpt_filename ='./exp/checkpoints/checkpoint_33(复件).pth'# 14(8ch) 33(12ch)
          ckpt_filename ='./exp/checkpoints/checkpoint_14.pth'# 14(8ch) 33(12ch)
          # ckpt_filename ='../pc_aloha/exp/checkpoints/checkpoint_43.pth'
          config = configs.get_config()  
          sde = VESDE(sigma_min=config.model.sigma_min, sigma_max=config.model.sigma_max, N=config.model.num_scales) ###################################  sde
          #sde = VESDE(sigma_min=0.01, sigma_max=10, N=100) ###################################  sde
          sampling_eps = 1e-5


        batch_size = 8 #@param {"type":"integer"}
        config.training.batch_size = batch_size
        config.eval.batch_size = batch_size

        random_seed = 0 #@param {"type": "integer"}

        sigmas = mutils.get_sigmas(config)
        scaler = datasets.get_data_scaler(config)
        inverse_scaler = datasets.get_data_inverse_scaler(config)
        score_model = mutils.create_model(config)

        optimizer = get_optimizer(config, score_model.parameters())
        ema = ExponentialMovingAverage(score_model.parameters(),
                                      decay=config.model.ema_rate)
        state = dict(step=0, optimizer=optimizer,
                    model=score_model, ema=ema)

        state = restore_checkpoint(ckpt_filename, state, config.device)
        ema.copy_to(score_model.parameters())

        #@title PC sampling
        img_size = config.data.image_size
        channels = config.data.num_channels
        shape = (batch_size, channels, img_size, img_size)
        # predictor = ReverseDiffusionPredictor #@param ["EulerMaruyamaPredictor", "AncestralSamplingPredictor", "ReverseDiffusionPredictor", "None"] {"type": "raw"}
        predictor = sampling_svd.ReverseDiffusionPredictor
        # corrector = LangevinCorrector #@param ["LangevinCorrector", "AnnealedLangevinDynamics", "None"] {"type": "raw"}
        corrector = sampling_svd.LangevinCorrector
        snr = 0.075#0.16 #@param {"type": "number"}
        n_steps =  1#@param {"type": "integer"}
        probability_flow = False #@param {"type": "boolean"}
        sampling_fn = sampling_svd.get_pc_sampler(sde, shape, predictor, corrector,
                                              inverse_scaler, snr, n_steps=n_steps,
                                              probability_flow=probability_flow,
                                              continuous=config.training.continuous,
                                              eps=sampling_eps, device=config.device)





        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            #temp_dir = './result/wkgm/xxtest'
            # 保存上传的图像文件
            print("开始上传文件")
        
            input_path = os.path.join(temp_dir, "input.mat")
            with open(input_path, "wb") as f:
                f.write(await image.read())
            
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


            # 创建保存结果的目录
            save_path = os.path.join(temp_dir, "results")
            print("savePath=",save_path)
            ensure_folder_exists(save_path)

            #获取图像
            
            hbz_waigua.setup_logger(
                "base",
                save_path,
                "test",
                level=logging.INFO,
                screen=True,
                tofile=True,
            )
            logger = logging.getLogger("base")
            T2_root = './datasets/T2_img'
            # T1_root = './datasets/T1_img'
            T1_root = './datasets/fastmri'
            PD_root = './datasets/PD_img'
            # mat_content = scipy.io.loadmat(input_path, mat_dtype=True, squeeze_me=True, struct_as_record=False)

            #  # 过滤掉 MATLAB 自带的元数据
            # valid_keys = [key for key in mat_content if not key.startswith('__')]
            # print("过滤成功")
            # # 如果有有效 key，返回第一个；否则返回空字典或抛出异常
            # if valid_keys:
            #     first_key = valid_keys[0]
            #     my_ori = mat_content[first_key]
            # else:
            #     raise ValueError("MAT 文件中没有找到有效数据变量！")
            my_ori = scipy.io.loadmat(input_path, mat_dtype=True, squeeze_me=True, struct_as_record=False)['DATA']
            my_mask= scipy.io.loadmat(mask_path, mat_dtype=True, squeeze_me=True, struct_as_record=False)['mask']

            dataset = hbz_waigua.get_dataset(T2_root, T1_root, PD_root)
            dataloader = hbz_waigua.get_dataloader(dataset)
            test_results = OrderedDict()
            test_results["psnr"] = []
            test_results["ssim"] = []
            test_results["psnr_y"] = []
            test_results["ssim_y"] = []

            test_results["psnr_zf"] = []
            test_results["ssim_zf"] = []
            test_times = []
            for i, test_data in enumerate(dataloader):
              if i == 3:
                print(f'前{i}张图测试完成')
                break
              img_path = test_data["T2_path"][0]
              img_name = os.path.splitext(os.path.basename(img_path))[0]
              tic = time.time()
              save_path  = './result/wkgm/xxtest'
              x, n = sampling_fn(score_model, test_data,img_name,save_path,my_ori,my_mask)
              toc = time.time()
              test_time = toc - tic
              test_times.append(test_time)
              max_psnr = n["psnr"]
              max_psnr_ssim = n["ssim"]
              psnr_zf = n["zf_psnr"]
              ssim_zf = n["zf_ssim"]
              
              test_results["psnr"].append(max_psnr)
              test_results["ssim"].append(max_psnr_ssim)
              test_results["psnr_zf"].append(psnr_zf)
              test_results["ssim_zf"].append(ssim_zf)


              logger.info(
                  "img:{:15s} - PSNR: {:.2f} dB; SSIM: {:.4f}  *****  零填充: PSNR: {:.2f} dB; SSIM: {:.4f} ***** time: {:.4f} s".format(
                      img_name, max_psnr, max_psnr_ssim, psnr_zf, ssim_zf, test_time
                  )
              )
            ave_psnr = sum(test_results["psnr"]) / len(test_results["psnr"])
            ave_ssim = sum(test_results["ssim"]) / len(test_results["ssim"])
            ave_psnr_zf = sum(test_results["psnr_zf"]) / len(test_results["psnr_zf"])
            ave_ssim_zf = sum(test_results["ssim_zf"]) / len(test_results["ssim_zf"])
            ave_time = np.mean(test_times)
            logger.info(
                "----Average PSNR/SSIM results----\n\tPSNR: {:.2f} dB; SSIM: {:.4f}*****  零填充: PSNR: {:.2f} dB; SSIM: {:.4f} ***** Average_time: {:.4f}s\n".format(
                    ave_psnr, ave_ssim, ave_psnr_zf, ave_ssim_zf, ave_time
                )
            )

             # 保存结果
            print("WKGM计算结束")
            result_path = os.path.join(save_path, 'result.mat')
            zeorfilled_data_sos_path = os.path.join(save_path, img_name+'Zeorfilled.png')
            #rec_Image_sos_path = os.path.join(save_path, img_name+'Rec'+'.png')
            rec_Image_sos_path = os.path.join(save_path, img_name+'Rec'+'.png')
            # 读取图像并转换为 NumPy 数组
            zeorfilled_data_sos = np.array(Image.open(zeorfilled_data_sos_path))
            rec_Image_sos = np.array(Image.open(rec_Image_sos_path))

            print("数据提取结束")

            io.savemat(result_path, {
                'zeorfilled_data_sos' : zeorfilled_data_sos,
                'rec_Image_sos': rec_Image_sos,
                'psnr': max_psnr,
                'ssim': max_psnr_ssim
            })
            print("数据打包结束")
            
            # 读取处理后的结果
            with open(result_path, 'rb') as f:
                processed_data = f.read()
            
            return Response(
                content=processed_data,
                media_type="application/octet-stream",
                headers={
                    "X-PSNR": str(max_psnr),
                    "X-SSIM": str(max_psnr_ssim)
                }
            )

            
    # except Exception as e:
    #     print(f"处理出错: {str(e)}")
    #     raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("启动 FastAPI 服务...")
    uvicorn.run(app, host="0.0.0.0", port=8080)

