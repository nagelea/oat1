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
            
            # 完整密钥统计
            complete_keys_info = self._get_complete_keys_info(raw_data)
            if complete_keys_info['total_complete_keys'] > 0:
                message_parts.append(f"  • 🔑 完整密钥: {complete_keys_info['total_complete_keys']} 个")
                if complete_keys_info['public_complete_keys'] > 0:
                    message_parts.append(f"  • ⚠️ 公开仓库中的完整密钥: {complete_keys_info['public_complete_keys']} 个")
            
            # 最新文件信息
            latest_files_info = self._get_latest_files_info(raw_data)
            if latest_files_info:
                message_parts.append(f"\n📄 最新发现文件:")
                for file_info in latest_files_info:
                    message_parts.append(f"  • {file_info}")
            
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
                if complete_keys_info['public_complete_keys'] > 0:
                    message_parts.append(f"🚨 发现 {complete_keys_info['public_complete_keys']} 个完整API密钥在公开仓库!")
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
    
    def _get_complete_keys_info(self, raw_data):
        """获取完整密钥信息"""
        try:
            results = raw_data.get('results', [])
            total_complete_keys = 0
            public_complete_keys = 0
            
            for result in results:
                file_info = result.get('file', {})
                complete_keys = file_info.get('full_keys_found', 0)
                is_public = not result.get('repository', {}).get('private', True)
                
                total_complete_keys += complete_keys
                if is_public and complete_keys > 0:
                    public_complete_keys += complete_keys
            
            return {
                'total_complete_keys': total_complete_keys,
                'public_complete_keys': public_complete_keys
            }
        except Exception as e:
            print(f"⚠️ 获取完整密钥信息失败: {e}")
            return {'total_complete_keys': 0, 'public_complete_keys': 0}
    
    def _get_latest_files_info(self, raw_data):
        """获取最新文件信息"""
        try:
            results = raw_data.get('results', [])
            if not results:
                return []
            
            # 按最后修改时间排序，获取最新的文件
            files_with_time = []
            
            for result in results:
                time_info = result.get('time_info', {})
                last_commit = time_info.get('last_commit', {})
                last_modified = last_commit.get('last_modified')
                
                if last_modified:
                    try:
                        # 解析时间
                        from dateutil import parser
                        mod_time = parser.parse(last_modified)
                        
                        # 处理时区转换
                        mod_time_beijing, time_ago = self._calculate_time_diff(mod_time)
                        
                        # 用于显示的时间字符串（北京时间）
                        display_time = mod_time_beijing.strftime('%m-%d %H:%M')
                        
                        file_info = {
                            'repo': result['repository']['full_name'],
                            'file': result['file']['path'],
                            'matches': result['file']['match_count'],
                            'last_modified': mod_time_beijing,
                            'last_modified_str': display_time,
                            'time_ago': time_ago,
                            'is_public': not result['repository']['private'],
                            'author': last_commit.get('last_author', 'Unknown')
                        }
                        files_with_time.append(file_info)
                    except Exception as e:
                        print(f"⚠️ 处理时间信息失败 {last_modified}: {e}")
                        continue
            
            # 按时间排序，最新的在前
            files_with_time.sort(key=lambda x: x['last_modified'], reverse=True)
            
            # 格式化输出，只显示前3个最新的文件
            latest_files = []
            for file_info in files_with_time[:3]:
                repo_indicator = "🌐" if file_info['is_public'] else "🔒"
                file_display = f"{repo_indicator} {file_info['repo']}/{file_info['file']}"
                time_display = f"({file_info['last_modified_str']}, {file_info['time_ago']})"
                
                # 显示匹配信息
                if file_info.get('has_complete_keys', False):
                    match_display = f"[🔑{file_info.get('full_keys_found', 0)}完整+{file_info['matches']}总计]"
                else:
                    match_display = f"[{file_info['matches']}次]"
                
                # 限制长度以适合通知
                if len(file_display) > 40:
                    parts = file_info['file'].split('/')
                    filename = parts[-1]
                    file_display = f"{repo_indicator} {file_info['repo']}/.../{filename}"
                
                latest_files.append(f"{file_display} {time_display} {match_display}")
            
            return latest_files
            
        except Exception as e:
            print(f"⚠️ 获取最新文件信息失败: {e}")
            return []
    
    def _calculate_time_diff(self, mod_time):
        """计算时间差，正确处理时区"""
        try:
            from datetime import timezone, timedelta
            
            # 北京时间是 UTC+8
            beijing_offset = timedelta(hours=8)
            beijing_tz = timezone(beijing_offset)
            
            # 获取当前北京时间
            current_beijing = datetime.now(beijing_tz)
            
            # 处理修改时间的时区
            if mod_time.tzinfo is not None:
                # 如果有时区信息，转换为北京时间
                mod_time_beijing = mod_time.astimezone(beijing_tz)
            else:
                # 如果没有时区信息，假设是UTC时间
                utc_tz = timezone.utc
                mod_time_utc = mod_time.replace(tzinfo=utc_tz)
                mod_time_beijing = mod_time_utc.astimezone(beijing_tz)
            
            # 计算时间差
            time_diff = current_beijing - mod_time_beijing
            time_ago = self._format_time_ago(time_diff)
            
            return mod_time_beijing, time_ago
            
        except Exception as e:
            print(f"⚠️ 时区转换失败: {e}")
            # 如果时区处理失败，使用简单的时间差计算
            current_time = datetime.now()
            
            # 移除时区信息进行简单比较
            if mod_time.tzinfo is not None:
                mod_time_naive = mod_time.replace(tzinfo=None)
                # 假设GitHub时间是UTC，加8小时转为北京时间
                mod_time_beijing = mod_time_naive + timedelta(hours=8)
            else:
                # 假设是UTC时间，加8小时
                mod_time_beijing = mod_time + timedelta(hours=8)
            
            time_diff = current_time - mod_time_beijing
            time_ago = self._format_time_ago(time_diff)
            
            return mod_time_beijing, time_ago
    
    def _format_time_ago(self, time_diff):
        """格式化时间差为易读的格式"""
        total_seconds = int(time_diff.total_seconds())
        
        if total_seconds < 0:
            return "刚刚"
        
        # 计算各种时间单位
        minutes = total_seconds // 60
        hours = minutes // 60
        days = hours // 24
        weeks = days // 7
        months = days // 30
        years = days // 365
        
        if years > 0:
            return f"{years}年前"
        elif months > 0:
            return f"{months}个月前"
        elif weeks > 0:
            return f"{weeks}周前"
        elif days > 0:
            return f"{days}天前"
        elif hours > 0:
            return f"{hours}小时前"
        elif minutes > 0:
            return f"{minutes}分钟前"
        else:
            return "刚刚"
    
    def send_notification(self, title, message, level="active"):
        """发送 Bark 通知"""
        try:
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
            
            # 确保服务器地址格式正确
            if self.bark_server.endswith('/'):
                self.bark_server = self.bark_server.rstrip('/')
            
            # 方法1: 使用 POST 请求 (推荐，避免 URL 长度限制)
            url = f"{self.bark_server}/{self.bark_key}"
            
            # 构建请求数据
            data = {
                'title': title,
                'body': message,
                'level': level,
                'sound': sound,
                'group': 'GitHub安全扫描',
                'icon': 'https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png'
            }
            
            print(f"📤 发送 Bark 通知...")
            print(f"🔗 URL: {url}")
            print(f"📋 数据: {{'title': '{title[:30]}...', 'level': '{level}', 'sound': '{sound}'}}")
            
            # 使用 POST 请求发送
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('code') == 200:
                        print(f"✅ Bark 通知发送成功!")
                        print(f"📱 消息: {result.get('message', 'Success')}")
                        return True
                    else:
                        print(f"❌ Bark 服务器返回错误: {result}")
                        # 尝试备用方法
                        return self._send_notification_fallback(title, message, level, sound)
                except json.JSONDecodeError:
                    # 如果响应不是 JSON，可能是成功的
                    if 'success' in response.text.lower() or response.status_code == 200:
                        print(f"✅ Bark 通知发送成功! (非JSON响应)")
                        return True
                    else:
                        print(f"❌ 响应解析失败: {response.text}")
                        return self._send_notification_fallback(title, message, level, sound)
            else:
                print(f"❌ HTTP 请求失败: {response.status_code}")
                print(f"📄 响应内容: {response.text}")
                # 尝试备用方法
                return self._send_notification_fallback(title, message, level, sound)
                
        except requests.exceptions.Timeout:
            print("❌ 请求超时，请检查网络连接")
            return False
        except requests.exceptions.RequestException as e:
            print(f"❌ 网络请求失败: {e}")
            return False
        except Exception as e:
            print(f"❌ 发送通知失败: {e}")
            return False
    
    def _send_notification_fallback(self, title, message, level, sound):
        """备用发送方法 - 使用 GET 请求简化版本"""
        try:
            print("🔄 尝试备用发送方法...")
            
            # 简化消息内容以避免 URL 过长
            short_message = self._create_short_message(title, message)
            
            # URL 编码
            from urllib.parse import quote
            encoded_title = quote(title.encode('utf-8'))
            encoded_message = quote(short_message.encode('utf-8'))
            
            # 构建简化的 GET 请求
            url = f"{self.bark_server}/{self.bark_key}/{encoded_title}/{encoded_message}"
            params = {
                'level': level,
                'sound': sound
            }
            
            print(f"🔗 备用 URL: {url[:100]}...")
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ 备用方法发送成功!")
                return True
            else:
                print(f"❌ 备用方法也失败: {response.status_code}")
                print(f"📄 响应: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 备用方法失败: {e}")
            return False
    
    def _create_short_message(self, title, message):
        """创建简化的消息内容"""
        lines = message.split('\n')
        short_lines = []
        
        # 保留重要信息
        for line in lines:
            if any(keyword in line for keyword in ['扫描时间', '风险等级', '总文件数', '公开仓库', '警告']):
                short_lines.append(line)
            elif len(short_lines) < 5:  # 限制行数
                short_lines.append(line)
        
        short_message = '\n'.join(short_lines)
        
        # 限制总长度
        if len(short_message) > 500:
            short_message = short_message[:500] + '...'
        
        return short_message
    
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
