# ...
# ...
# ...

import machine
import ubinascii
import time

try:
    import ujson as json
except:
    import json

try:
    import urequests
except:
    print("警告: urequests未安装")

try:
    import esp32
except:
    print("警告: ESP32模块不可用")

# ...
FIRMWARE_VERSION = "2.0.2"
FIRMWARE_BUILD = "20251104"

# ...
class OTAManager:
    def __init__(self, cloud_api_base):
        self.cloud_api_base = cloud_api_base
        self.current_version = FIRMWARE_VERSION
        self.ota_partition = None
        self.progress_callback = None
        
    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def report_progress(self, stage, progress, message=""):
        """报告进度"""
        if self.progress_callback:
            self.progress_callback({
                'stage': stage,
                'progress': progress,
                'message': message
            })
        print("[OTA] " + stage + ": " + str(progress) + "% - " + message)
    
    # ...
    def check_for_updates(self):
        """检查云端是否有新版本"""
        try:
            self.report_progress('check', 0, '正在检查更新...')
            
            url = self.cloud_api_base + "/firmware/version?current=" + self.current_version
            response = urequests.get(url, timeout=10)
            data = response.json()
            response.close()
            
            if data.get('success') and data.get('hasUpdate'):
                self.report_progress('check', 100, '发现新版本: ' + data['newVersion'])
                return {
                    'hasUpdate': True,
                    'version': data['newVersion'],
                    'url': data['downloadUrl'],
                    'size': data['fileSize'],
                    'checksum': data['checksum'],
                    'changelog': data.get('changelog', '')
                }
            else:
                self.report_progress('check', 100, '已是最新版本')
                return {'hasUpdate': False}
                
        except Exception as e:
            self.report_progress('check', 0, '检查失败: ' + str(e))
            return None
    
    # ...
    def download_firmware(self, url, expected_size):
        """下载新固件到OTA分区"""
        try:
            # ...
            from esp32 import Partition
            running = Partition(Partition.RUNNING)
            self.ota_partition = running.get_next_update()
            
            self.report_progress('download', 0, '准备下载固件...')
            print("当前分区: " + str(running.info()))
            print("目标分区: " + str(self.ota_partition.info()))
            
            # ...
            self.report_progress('download', 5, '擦除Flash分区...')
            self.ota_partition.erase()
            
            # ...
            self.report_progress('download', 10, '开始下载固件...')
            response = urequests.get(url, stream=True)
            
            downloaded = 0
            chunk_size = 4096
            write_offset = 0
            buffer = bytearray(chunk_size)
            
            while True:
                chunk = response.raw.read(chunk_size)
                if not chunk:
                    break
                
                chunk_len = len(chunk)
                
                # ...
                # ...
                if chunk_len == chunk_size:
                    # ...
                    self.ota_partition.writeblocks(write_offset // chunk_size, chunk)
                else:
                    # ...
                    buffer[:chunk_len] = chunk
                    # ...
                    for i in range(chunk_len, chunk_size):
                        buffer[i] = 0xFF
                    self.ota_partition.writeblocks(write_offset // chunk_size, buffer)
                
                write_offset += chunk_len
                downloaded += chunk_len
                
                # ...
                progress = 10 + int((downloaded / expected_size) * 80)
                if downloaded % (64 * 1024) == 0 or downloaded == expected_size:
                    # ...
                    self.report_progress('download', progress, 
                        str(downloaded) + " / " + str(expected_size) + " bytes")
            
            response.close()
            
            self.report_progress('download', 100, '下载完成: ' + str(downloaded) + ' bytes')
            return downloaded
            
        except Exception as e:
            self.report_progress('download', 0, '下载失败: ' + str(e))
            print("错误详情: " + str(e))
            raise
    
    # ...
    def verify_firmware(self, expected_checksum, actual_size):
        """校验固件SHA256（仅校验实际写入的数据）"""
        try:
            import uhashlib
            
            self.report_progress('verify', 0, '开始校验固件...')
            
            sha256 = uhashlib.sha256()
            chunk_size = 4096
            verified = 0
            
            # ...
            while verified < actual_size:
                # ...
                read_size = min(chunk_size, actual_size - verified)
                
                # ...
                chunk = bytearray(chunk_size)
                block_num = verified // chunk_size
                self.ota_partition.readblocks(block_num, chunk)
                
                # ...
                sha256.update(chunk[:read_size])
                
                verified += read_size
                progress = int((verified / actual_size) * 100)
                if progress % 20 == 0:  # 每20%报告一次
                    self.report_progress('verify', progress, '校验中...')
            
            checksum = ubinascii.hexlify(sha256.digest()).decode()
            
            if checksum == expected_checksum:
                self.report_progress('verify', 100, '校验成功')
                return True
            else:
                self.report_progress('verify', 0, 
                    '校验失败 - 计算: ' + checksum[:16] + '... != 期望: ' + expected_checksum[:16] + '...')
                return False
                
        except Exception as e:
            self.report_progress('verify', 0, '校验错误: ' + str(e))
            print("校验错误详情: " + str(e))
            return False
    
    # ...
    def activate_and_reboot(self):
        """切换到新固件并重启"""
        try:
            self.report_progress('activate', 0, '准备切换固件...')
            
            # ...
            self.ota_partition.set_boot()
            
            self.report_progress('activate', 50, '已设置启动分区')
            
            # ...
            for i in range(3, 0, -1):
                self.report_progress('activate', 50 + (i * 10), 
                    str(i) + '秒后重启...')
                time.sleep(1)
            
            self.report_progress('activate', 100, '重启设备...')
            time.sleep(0.5)
            
            # ...
            machine.reset()
            
        except Exception as e:
            self.report_progress('activate', 0, '激活失败: ' + str(e))
            raise
    
    # ...
    def perform_ota_update(self, update_info):
        """执行完整的OTA升级流程"""
        try:
            print("\n" + "="*50)
            print("  🚀 开始OTA固件升级")
            print("  版本: " + update_info['version'])
            print("  大小: " + str(update_info['size']) + " bytes")
            print("="*50)
            
            # ...
            downloaded = self.download_firmware(
                update_info['url'], 
                update_info['size']
            )
            
            if downloaded != update_info['size']:
                raise Exception("下载大小不匹配: " + str(downloaded) + " != " + str(update_info['size']))
            
            # ...
            if not self.verify_firmware(update_info['checksum'], downloaded):
                raise Exception("固件校验失败")
            
            # ...
            self.activate_and_reboot()
            
            return True
            
        except Exception as e:
            print("❌ OTA升级失败: " + str(e))
            self.report_progress('error', 0, 'OTA失败: ' + str(e))
            return False
    
    # ...
    @staticmethod
    def verify_new_firmware():
        """验证新固件是否正常（首次启动时调用）"""
        try:
            from esp32 import Partition
            
            # ...
            running = Partition(Partition.RUNNING)
            
            # ...
            if running.info()[0] == Partition.RUNNING:
                print("✅ 新固件验证通过")
                # ...
                try:
                    # ESP-IDF v4.0+
                    running.mark_app_valid_cancel_rollback()
                except:
                    pass
                return True
            
            return False
            
        except Exception as e:
            print("⚠️  固件验证失败: " + str(e))
            # ...
            return False

# ...
def get_firmware_info():
    """获取当前固件信息"""
    try:
        from esp32 import Partition
        running = Partition(Partition.RUNNING)
        
        return {
            'version': FIRMWARE_VERSION,
            'build': FIRMWARE_BUILD,
            'partition': str(running.info()[0]),
            'size': running.info()[3]
        }
    except:
        return {
            'version': FIRMWARE_VERSION,
            'build': FIRMWARE_BUILD
        }
