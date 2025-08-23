我来帮你分析这个Django博客项目。让我们逐步查看项目的结构和关键文件。

首先，让我查看一下项目的主要配置文件：


Read file: settings.py
让我看看URL配置：


Read file: urls.py
让我们看看blog应用的结构：


Ran tool
让我们查看一下模型定义：


Read file: blog/models.py
基于以上分析，我可以为你总结这个项目的主要特点：

1. **项目类型**：这是一个基于Django框架开发的博客系统，同时集成了图像处理功能。

2. **主要功能模块**：
   - 博客文章管理（Article模型）
   - 图像处理功能（ProcessedImage模型）
   - 后台管理系统（Django Admin）

3. **图像处理功能**：
   - 支持多种图像处理模型：
     - 风格迁移（style_transfer）
     - 超分辨率（super_resolution）
     - 目标检测（object_detection）
   - 图像处理流程：
     - 上传原始图片
     - 调用外部API进行处理（通过WSL环境）
     - 保存处理后的图片

4. **项目结构**：
   - `blog/` - 主应用目录
     - `models.py` - 数据模型定义
     - `views.py` - 视图函数
     - `urls.py` - URL路由配置
     - `templates/` - 模板文件
     - `forms.py` - 表单定义
     - `admin.py` - 后台管理配置
   - `media/` - 媒体文件存储目录
     - `original/` - 原始图片存储
     - `processed/` - 处理后的图片存储
   - `blog_project/` - 项目配置目录
   - `db.sqlite3` - SQLite数据库文件

5. **技术特点**：
   - 使用Django框架开发
   - 采用SQLite数据库
   - 集成了外部图像处理API
   - 支持文件上传和处理
   - 包含完整的后台管理系统

6. **文件存储**：
   - 使用Django的媒体文件系统
   - 分别存储原始图片和处理后的图片
   - 支持图片处理状态跟踪

这个项目看起来是一个结合了博客功能和图像处理功能的综合应用。它不仅提供了基本的博客功能，还集成了高级的图像处理能力，可以通过外部API进行图像处理。项目结构清晰，功能模块划分合理，适合作为学习和开发的基础。

如果你想了解更具体的某个部分，我可以为你深入分析特定的功能模块。




环境：
conda create -n web python=3.10
pip install -r requirements.txt

运行：
python manage.py runserver

创建账号：
python manage.py createsuperuser


服务器端：
环境
pip install fastapi uvicorn python-multipart pillow

运行
bash test_ori_forAPI.sh
新开一个客户端运行：./ngrok http 8001  
报错因为没有登录配置token

<!-- 这个错误是因为您需要先注册 ngrok 账号并配置 authtoken。让我帮您完成这个设置：
注册 ngrok 账号：
访问 https://dashboard.ngrok.com/signup
使用邮箱注册一个免费账号
获取 authtoken：
登录后访问 https://dashboard.ngrok.com/get-started/your-authtoken
您会看到一个类似这样的 token：2xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
配置 authtoken：
在终端中运行以下命令（替换 YOUR_AUTH_TOKEN 为您的实际 token）：
Apply to readme.md
Run
   ./ngrok config add-authtoken YOUR_AUTH_TOKEN
验证配置：
Apply to readme.md
Run
   ./ngrok config check
重新启动 ngrok：
Apply to readme.md
Run
   ./ngrok http 8001
现在应该就能正常启动 ngrok 了。启动后，您会看到类似这样的界面： -->


然后修改客户端的blog\models.py里的接口





#ngrock转发协议：8080端口转发docker里面的wkgm ，，8001端口转发Linux本机DFTM
配置文件地址  ：/home/mri/.config/ngrok/ngrok.yml

#docker采用桥接方式连接

#0719版本支持两个不同算法的转发，存在的问题：发送请求用时过长