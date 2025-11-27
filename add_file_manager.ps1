# 读取原文件
\ = Get-Content 'modules/device_web_server.py' -Raw

# 在import部分后添加file_manager导入
\ = 'import _thread'
\ = @'
import _thread

# Import file manager
try:
    from file_manager import handle_file_api
    FILE_MANAGER_ENABLED = True
except:
    FILE_MANAGER_ENABLED = False
    print('[WARN] 文件管理模块未加载')
'@

\ = \.Replace(\, \)

# 在路由处理部分添加文件管理路由
\ = 'elif path.startswith(''/api/''):'
\ = @'
elif path.startswith('/files') and FILE_MANAGER_ENABLED:
                    # 文件管理API
                    response = handle_file_api(path, query, method, request_str.split('\r\n\r\n')[1] if '\r\n\r\n' in request_str else '')
                    conn.send(response)
                elif path.startswith('/api/'):
'@

\ = \.Replace(\, \)

# 保存修改后的文件
\ | Out-File -FilePath 'modules/device_web_server.py' -Encoding UTF8 -NoNewline
Write-Host ' device_web_server.py 已更新，添加文件管理功能'
