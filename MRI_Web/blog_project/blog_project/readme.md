要启动的东西：wsl的ngrok，test_ori_forAPI.sh   （打开ngrok后修改客户端这边的models中的链接）
            api_url = 'https://7eca-220-175-48-224.ngrok-free.app/process_image/super_resolution'

服务器端：
        conda activate DiffiR_srGan
        ./ngrok http 8001    
        bash test_ori_forAPI.sh 



客户端启动：python manage.py runserver