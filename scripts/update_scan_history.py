#!/usr/bin/env python3
"""
扫描历史更新脚本
更新扫描历史记录，用于下次比较
"""

import json
import os
import hashlib
from datetime import datetime


def calculate_results_hash(results_file='reports/raw_data.json'):
    """计算结果的哈希值"""
    try:
        with open(results_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 提取关键信息用于哈希计算
        key_data = []
        for result in data.get('results', []):
            key_info = {
                'repo': result['repository']['full_name'],
                'file': result['file']['path'],
                'matches': result['file']['match_count'],
                'last_modified': result.get('time_info', {}).get('last_commit', {}).get('last_modified', '')
            }
            key_data.append(key_info)
        
        # 按仓库和文件路径排序以确保一致性
        key_data.sort(key=lambda x: (x['repo'], x['file']))
        
        # 计算哈希
        content = json.dumps(key_data, sort_keys=True).encode()
        return hashlib.sha256(content).hexdigest()
        
    except Exception as e:
        print(f"❌ 计算哈希失败: {e}")
        return None


def update_scan_history():
    """更新扫描历史"""
    try:
        # 确保历史目录存在
        history_dir = '.github/scan_history'
        os.makedirs(history_dir, exist_ok=True)
        
        # 计算当前结果哈希
        current_hash = calculate_results_hash()
        if not current_hash:
            print("❌ 无法计算当前结果哈希")
            return False
        
        # 更新哈希文件
        hash_file = os.path.join(history_dir, 'last_scan_hash.txt')
        with open(hash_file, 'w') as f:
            f.write(current_hash)
        
        print(f"✅ 扫描哈希已更新: {current_hash[:12]}...")
        
        # 加载当前扫描数据
        try:
            with open('reports/raw_data.json', 'r', encoding='utf-8') as f:
                current_data = json.load(f)
        except:
            current_data = {}
        
        # 创建历史记录条目
        history_entry = {
            'scan_time': current_data.get('scan_time', datetime.now().isoformat()),
            'hash': current_hash,
            'total_found': current_data.get('total_found', 0),
            'analyzed_files': current_data.get('analyzed_files', 0),
            'search_pattern': current_data.get('search_pattern', ''),
            'search_scope': current_data.get('search_scope', ''),
            'file_extensions': current_data.get('file_extensions', []),
            'summary': create_scan_summary(current_data)
        }
        
        # 更新历史记录文件
        history_file = os.path.join(history_dir, 'scan_history.json')
        history_data = load_scan_history(history_file)
        
        # 添加新记录到历史
        history_data['scans'].append(history_entry)
        
        # 只保留最近50次扫描记录
        if len(history_data['scans']) > 50:
            history_data['scans'] = history_data['scans'][-50:]
        
        # 更新统计信息
        history_data['last_updated'] = datetime.now().isoformat()
        history_data['total_scans'] = len(history_data['scans'])
        
        # 保存历史记录
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)
        
        print(f"📊 扫描历史已更新，总记录数: {history_data['total_scans']}")
        
        # 生成扫描趋势报告
        generate_trend_report(history_data, history_dir)
        
        return True
        
    except Exception as e:
        print(f"❌ 更新扫描历史失败: {e}")
        return False


def load_scan_history(history_file):
    """加载扫描历史"""
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # 首次运行，创建新的历史结构
        return {
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'total_scans': 0,
            'scans': []
        }
    except Exception as e:
        print(f"⚠️ 加载历史记录失败: {e}，将创建新的历史记录")
        return {
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'total_scans': 0,
            'scans': []
        }


def create_scan_summary(current_data):
    """创建扫描摘要"""
    results = current_data.get('results', [])
    
    if not results:
        return {
            'total_files': 0,
            'public_files': 0,
            'private_files': 0,
            'total_matches': 0,
            'repositories': [],
            'risk_level': 'NONE'
        }
    
    public_files = sum(1 for r in results if not r['repository']['private'])
    private_files = len(results) - public_files
    total_matches = sum(r['file']['match_count'] for r in results)
    repositories = list(set(r['repository']['full_name'] for r in results))
    
    # 计算风险等级
    if public_files > 0:
        if total_matches > 10:
            risk_level = "CRITICAL"
        elif total_matches > 5:
            risk_level = "HIGH"
        else:
            risk_level = "MEDIUM"
    elif len(results) > 0:
        risk_level = "LOW"
    else:
        risk_level = "NONE"
    
    return {
        'total_files': len(results),
        'public_files': public_files,
        'private_files': private_files,
        'total_matches': total_matches,
        'repositories': repositories,
        'repository_count': len(repositories),
        'risk_level': risk_level
    }


def generate_trend_report(history_data, history_dir):
    """生成趋势报告"""
    try:
        scans = history_data.get('scans', [])
        if len(scans) < 2:
            print("📈 扫描记录不足，跳过趋势分析")
            return
        
        # 最近7天的数据
        recent_scans = scans[-7:] if len(scans) >= 7 else scans
        
        # 计算趋势
        trend_data = {
            'period': f"最近 {len(recent_scans)} 次扫描",
            'first_scan': recent_scans[0]['scan_time'],
            'last_scan': recent_scans[-1]['scan_time'],
            'trends': {
                'total_files': [scan['summary']['total_files'] for scan in recent_scans],
                'public_files': [scan['summary']['public_files'] for scan in recent_scans],
                'total_matches': [scan['summary']['total_matches'] for scan in recent_scans],
                'risk_levels': [scan['summary']['risk_level'] for scan in recent_scans]
            },
            'statistics': {}
        }
        
        # 计算统计信息
        total_files_trend = trend_data['trends']['total_files']
        public_files_trend = trend_data['trends']['public_files']
        matches_trend = trend_data['trends']['total_matches']
        
        if len(total_files_trend) >= 2:
            trend_data['statistics'] = {
                'avg_total_files': sum(total_files_trend) / len(total_files_trend),
                'max_total_files': max(total_files_trend),
                'min_total_files': min(total_files_trend),
                'avg_public_files': sum(public_files_trend) / len(public_files_trend),
                'max_public_files': max(public_files_trend),
                'avg_matches': sum(matches_trend) / len(matches_trend),
                'max_matches': max(matches_trend),
                'latest_vs_previous': {
                    'total_files_change': total_files_trend[-1] - total_files_trend[-2],
                    'public_files_change': public_files_trend[-1] - public_files_trend[-2],
                    'matches_change': matches_trend[-1] - matches_trend[-2]
                }
            }
        
        # 风险等级分布
        risk_distribution = {}
        for risk in trend_data['trends']['risk_levels']:
            risk_distribution[risk] = risk_distribution.get(risk, 0) + 1
        
        trend_data['risk_distribution'] = risk_distribution
        
        # 保存趋势报告
        trend_file = os.path.join(history_dir, 'trend_report.json')
        with open(trend_file, 'w', encoding='utf-8') as f:
            json.dump(trend_data, f, indent=2, ensure_ascii=False)
        
        print("📈 趋势报告已生成")
        
        # 打印简要趋势信息
        if trend_data['statistics']:
            stats = trend_data['statistics']
            latest_change = stats['latest_vs_previous']
            
            print(f"📊 趋势摘要:")
            print(f"  • 平均文件数: {stats['avg_total_files']:.1f}")
            print(f"  • 平均公开文件: {stats['avg_public_files']:.1f}")
            print(f"  • 平均匹配数: {stats['avg_matches']:.1f}")
            
            if latest_change['total_files_change'] != 0:
                change_symbol = "📈" if latest_change['total_files_change'] > 0 else "📉"
                print(f"  • 文件数变化: {change_symbol} {latest_change['total_files_change']:+d}")
            
            if latest_change['public_files_change'] != 0:
                change_symbol = "⚠️" if latest_change['public_files_change'] > 0 else "✅"
                print(f"  • 公开文件变化: {change_symbol} {latest_change['public_files_change']:+d}")
        
    except Exception as e:
        print(f"⚠️ 生成趋势报告失败: {e}")


def cleanup_old_files(history_dir):
    """清理旧文件"""
    try:
        # 清理超过30天的临时文件
        import glob
        import time
        
        temp_pattern = os.path.join(history_dir, '*.tmp')
        current_time = time.time()
        
        for temp_file in glob.glob(temp_pattern):
            file_age = current_time - os.path.getmtime(temp_file)
            if file_age > 30 * 24 * 3600:  # 30天
                os.remove(temp_file)
                print(f"🗑️ 清理旧文件: {temp_file}")
                
    except Exception as e:
        print(f"⚠️ 清理旧文件失败: {e}")


def main():
    """主函数"""
    try:
        print("📝 更新扫描历史...")
        
        success = update_scan_history()
        
        if success:
            # 清理旧文件
            cleanup_old_files('.github/scan_history')
            print("✅ 扫描历史更新完成")
        else:
            print("❌ 扫描历史更新失败")
            exit(1)
            
    except Exception as e:
        print(f"❌ 脚本执行失败: {e}")
        exit(1)


if __name__ == "__main__":
    main()
