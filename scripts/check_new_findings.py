#!/usr/bin/env python3
"""
新发现检查脚本
检查是否有新的敏感内容发现
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
        
    except FileNotFoundError:
        print("❌ 结果文件不存在")
        return None
    except Exception as e:
        print(f"❌ 计算哈希失败: {e}")
        return None


def check_for_new_findings():
    """检查是否有新发现"""
    current_hash = calculate_results_hash()
    previous_hash = os.environ.get('PREVIOUS_HASH', '')
    
    if not current_hash:
        print("❌ 无法计算当前结果哈希")
        return False, {}
    
    print(f"📊 当前结果哈希: {current_hash[:12]}...")
    print(f"📊 上次结果哈希: {previous_hash[:12] if previous_hash else 'None'}...")
    
    # 如果是首次运行或哈希不同，则认为有新发现
    has_new_findings = (not previous_hash) or (current_hash != previous_hash)
    
    # 加载当前结果
    try:
        with open('reports/raw_data.json', 'r', encoding='utf-8') as f:
            current_data = json.load(f)
    except:
        current_data = {'results': []}
    
    # 分析新发现的详情
    new_findings_info = analyze_findings(current_data, has_new_findings, previous_hash)
    
    return has_new_findings, new_findings_info


def analyze_findings(current_data, has_new_findings, previous_hash):
    """分析发现的详情"""
    results = current_data.get('results', [])
    total_files = len(results)
    public_files = sum(1 for r in results if not r['repository']['private'])
    total_matches = sum(r['file']['match_count'] for r in results)
    
    # 风险等级
    if public_files > 0:
        if total_matches > 10:
            risk_level = "🚨 CRITICAL"
        elif total_matches > 5:
            risk_level = "⚠️ HIGH"
        else:
            risk_level = "🟡 MEDIUM"
    elif total_files > 0:
        risk_level = "🟢 LOW"
    else:
        risk_level = "✅ NONE"
    
    # 构建分析结果
    analysis = {
        'scan_time': current_data.get('scan_time', datetime.now().isoformat()),
        'is_first_scan': not previous_hash,
        'total_files': total_files,
        'public_files': public_files,
        'private_files': total_files - public_files,
        'total_matches': total_matches,
        'risk_level': risk_level,
        'repositories': list(set(r['repository']['full_name'] for r in results)),
        'top_repositories': get_top_repositories(results),
        'file_types': get_file_type_distribution(results)
    }
    
    return analysis


def get_top_repositories(results):
    """获取匹配最多的仓库"""
    repo_matches = {}
    for result in results:
        repo_name = result['repository']['full_name']
        matches = result['file']['match_count']
        
        if repo_name not in repo_matches:
            repo_matches[repo_name] = {
                'name': repo_name,
                'total_matches': 0,
                'file_count': 0,
                'is_private': result['repository']['private']
            }
        
        repo_matches[repo_name]['total_matches'] += matches
        repo_matches[repo_name]['file_count'] += 1
    
    # 按匹配数排序
    top_repos = sorted(repo_matches.values(), key=lambda x: x['total_matches'], reverse=True)
    return top_repos[:5]  # 返回前5个


def get_file_type_distribution(results):
    """获取文件类型分布"""
    file_types = {}
    for result in results:
        file_path = result['file']['path']
        ext = file_path.split('.')[-1].lower() if '.' in file_path else 'no_extension'
        
        if ext not in file_types:
            file_types[ext] = {
                'count': 0,
                'total_matches': 0
            }
        
        file_types[ext]['count'] += 1
        file_types[ext]['total_matches'] += result['file']['match_count']
    
    return dict(sorted(file_types.items(), key=lambda x: x[1]['count'], reverse=True))


def save_check_results(has_new_findings, analysis):
    """保存检查结果"""
    check_results = {
        'has_new_findings': has_new_findings,
        'check_time': datetime.now().isoformat(),
        'analysis': analysis
    }
    
    os.makedirs('reports', exist_ok=True)
    with open('reports/new_findings_check.json', 'w', encoding='utf-8') as f:
        json.dump(check_results, f, indent=2, ensure_ascii=False)
    
    # 设置 GitHub Actions 输出
    with open(os.environ.get('GITHUB_OUTPUT', '/dev/stdout'), 'a') as f:
        f.write(f"has_new_findings={'true' if has_new_findings else 'false'}\n")
        f.write(f"total_files={analysis['total_files']}\n")
        f.write(f"public_files={analysis['public_files']}\n")
        f.write(f"risk_level={analysis['risk_level']}\n")
    
    print(f"✅ 检查完成: {'发现新内容' if has_new_findings else '无新发现'}")
    print(f"📊 总文件数: {analysis['total_files']}")
    print(f"🌐 公开仓库文件: {analysis['public_files']}")
    print(f"🔒 私有仓库文件: {analysis['private_files']}")
    print(f"⚠️ 风险等级: {analysis['risk_level']}")


def main():
    """主函数"""
    try:
        print("🔍 检查新发现...")
        has_new_findings, analysis = check_for_new_findings()
        save_check_results(has_new_findings, analysis)
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        # 设置默认输出，避免后续步骤失败
        with open(os.environ.get('GITHUB_OUTPUT', '/dev/stdout'), 'a') as f:
            f.write("has_new_findings=false\n")
            f.write("total_files=0\n")
            f.write("public_files=0\n")
            f.write("risk_level=UNKNOWN\n")
        exit(1)


if __name__ == "__main__":
    main()
