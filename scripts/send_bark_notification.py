#!/usr/bin/env python3
"""
Bark 通知脚本
当发现新的敏感内容时发送 Bark 通知
"""

import json
import os
import requests
from datetime import datetime
from urllib.parse import quote


class BarkNotifier:
    def __init__(self):
        self.bark_key = os.environ.get('BARK_KEY')
        self.bark_server = os.environ.get('BARK_SERVER', 'https://api.day.app')
        
        if not self.bark_key:
            raise ValueError("❌ BARK_KEY 环境变量未设置")
        
        # 确保服务器地址格式正确
        if not self.bark_server.startswith('http'):
            self.bark_server = f'https://{self.bark_server}'
        
        print(f"📱 Bark 服务器: {self.bark_server}")
        print(f"🔑 Bark Key: {self.bark_key[:8]}...")
    
    def load_findings_data(self):
        """加载发现数据"""
        try:
            with open('reports/new_findings_check.json', 'r', encoding='utf-8') as f:
                check_data = json.load(f)
            
            with open('reports/raw_data.json', 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            return check_data, raw_data
            
        except FileNotFoundError as e:
            print(f"❌ 找不到数据文件: {e}")
            return None, None
        except Exception as e:
            print(f"❌ 加载数据失败: {e}")
            return None, None
    
    def create_notification_content(self, check_data, raw_data):
        """创建通知内容"""
        analysis = check_data.get('analysis', {})
        is_first_scan = analysis.get('is_first_scan', False)
        
        # 基本信息
        total_files = analysis.get('total_files', 0)
        public_files = analysis.get('public_files', 0)
        private_files = analysis.get('private_files', 0)
        total_matches = analysis.get('total_matches', 0)
        risk_level = analysis.get('risk_level', 'UNKNOWN')
        
        # 构建标题
        if is_first_scan:
            title = "🔍 GitHub 安全扫描 - 首次扫描完成"
        elif total_files > 0:
            title = f"🚨 GitHub 安全警报 - 发现 {total_files} 个敏感文件"
        else:
            title = "✅ GitHub 安全扫描 - 无新发现"
        
        # 构建消息体
        message_parts = []
        
        # 扫描概要
        scan_time = datetime.fromisoformat(analysis.get('scan_time', '')).strftime('%Y-%m-%d %H:%M')
        message_parts.append(f"⏰ 扫描时间: {scan_time}")
        message_parts.append(f"🎯 风险等级: {risk_level}")
        
        if total_files > 0:
            message_parts.append(f"📊 发现统计:")
            message_parts.append(f"  • 总文件数: {total_files}")
            if public_files > 0:
                message_parts.append(f"  • 🌐 公开仓库: {public_files} 个")
            if private_files > 0:
                message_parts.append(f"  • 🔒 私有仓库: {private_files} 个")
            message_parts.append(f"  • 总匹配次数: {total_matches}")
            
            # 涉及的仓库
            repositories = analysis.get('repositories', [])
            if repositories:
                message_parts.append(f"\n📋 涉及仓库 ({len(repositories)}个):")
                for repo in repositories[:5]:  # 只显示前5个
                    message_parts.append(f"  • {repo}")
                if len(repositories) > 5:
                    message_parts.append(f"  • ... 还有 {len(repositories) - 5} 个仓库")
            
            # 风险提醒
            if public_files > 0:
                message_parts.append(f"\n⚠️ 警告: 在公开仓库中发现敏感内容!")
                message_parts.append(f"请立即检查并采取行动!")
        else:
            message_parts.append("✅ 本次扫描未发现新的敏感内容")
        
        # GitHub Actions 链接
        github_repo = os.environ.get('GITHUB_REPOSITORY', '')
        github_run_id = os.environ.get('GITHUB_RUN_ID', '')
        if github_repo and github_run_id:
            actions_url = f"https://github.com/{github_repo}/actions/runs/{github_run_id}"
            message_parts.append(f"\n🔗 查看详细报告: {actions_url}")
        
        message = '\n'.join(message_parts)
        
        return title, message
    
    def send_notification(self, title, message, level="active"):
        """发送 Bark 通知"""
        try:
            # 构建 Bark API URL
            # 格式: https://api.day.app/[KEY]/[标题]/[内容]?level=[级别]&sound=[声音]
            
            # URL 编码
            encoded_title = quote(title)
            encoded_message = quote(message)
            
            # 根据风险等级设置通知级别和声音
            if "CRITICAL" in message or "🚨" in title:
                level = "critical"
                sound = "alarm"
            elif "HIGH" in message or "⚠️" in title:
                level = "active"
                sound = "multiwayinvitation"
            elif "MEDIUM" in message:
                level = "active"
                sound = "newmail"
            else:
                level = "active"
                sound = "birdsong"
            
            # 构建完整URL
            if self.bark_server.endswith('/'):
                self.bark_server = self.bark_server.rstrip('/')
            
            # 方法1: 使用路径参数 (推荐)
            url = f"{self.bark_server}/{self.bark_key}/{encoded_title}/{encoded_message}"
            params = {
                'level': level,
                'sound': sound,
                'group': 'GitHub安全扫描',
                'icon': 'https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png'
            }
            
            print(f"📤 发送 Bark 通知...")
            print(f"🔗 URL: {url}")
            print(f"📋 参数: {params}")
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 200:
                    print(f"✅ Bark 通知发送成功!")
                    print(f"📱 消息: {result.get('message', 'Success')}")
                    return True
                else:
                    print(f"❌ Bark 服务器返回错误: {result}")
                    return False
            else:
                print(f"❌ HTTP 请求失败: {response.status_code}")
                print(f"📄 响应内容: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            print("❌ 请求超时，请检查网络连接")
            return False
        except requests.exceptions.RequestException as e:
            print(f"❌ 网络请求失败: {e}")
            return False
        except Exception as e:
            print(f"❌ 发送通知失败: {e}")
            return False
    
    def send_test_notification(self):
        """发送测试通知"""
        title = "🧪 GitHub 安全扫描测试"
        message = f"测试通知发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n这是一条测试消息，用于验证 Bark 通知配置是否正确。"
        
        return self.send_notification(title, message, "passive")


def main():
    """主函数"""
    try:
        print("📱 准备发送 Bark 通知...")
        
        # 检查是否强制发送通知
        force_notify = os.environ.get('INPUT_FORCE_NOTIFY', 'false').lower() == 'true'
        
        notifier = BarkNotifier()
        
        # 如果是强制通知且没有发现数据，发送测试通知
        if force_notify:
            if not os.path.exists('reports/new_findings_check.json'):
                print("🧪 发送测试通知...")
                success = notifier.send_test_notification()
                exit(0 if success else 1)
        
        # 加载数据
        check_data, raw_data = notifier.load_findings_data()
        if not check_data or not raw_data:
            print("❌ 无法加载必要数据，跳过通知")
            exit(1)
        
        # 检查是否需要发送通知
        has_new_findings = check_data.get('has_new_findings', False)
        analysis = check_data.get('analysis', {})
        total_files = analysis.get('total_files', 0)
        
        if not has_new_findings and not force_notify:
            print("ℹ️ 无新发现且未强制通知，跳过发送")
            exit(0)
        
        # 创建通知内容
        title, message = notifier.create_notification_content(check_data, raw_data)
        
        print(f"📝 通知标题: {title}")
        print(f"📄 通知内容预览: {message[:100]}...")
        
        # 发送通知
        success = notifier.send_notification(title, message)
        
        if success:
            # 记录通知发送日志
            notification_log = {
                'sent_at': datetime.now().isoformat(),
                'title': title,
                'total_files': total_files,
                'public_files': analysis.get('public_files', 0),
                'risk_level': analysis.get('risk_level', 'UNKNOWN'),
                'repositories_count': len(analysis.get('repositories', [])),
                'was_forced': force_notify
            }
            
            os.makedirs('reports', exist_ok=True)
            with open('reports/notification_log.json', 'w', encoding='utf-8') as f:
                json.dump(notification_log, f, indent=2, ensure_ascii=False)
            
            print("📊 通知日志已保存")
        
        exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ 通知脚本执行失败: {e}")
        exit(1)


if __name__ == "__main__":
    main()
