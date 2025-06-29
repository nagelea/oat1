#!/usr/bin/env python3
"""
GitHub Code Search Script
搜索 GitHub 仓库中的敏感内容
"""

import requests
import json
import os
import time
from datetime import datetime
from dateutil import parser
import base64
from typing import List, Dict, Optional


class GitHubSearcher:
    def __init__(self):
        self.token = os.environ.get('GITHUB_TOKEN')
        self.search_scope = os.environ.get('SEARCH_SCOPE', '')
        self.max_results = int(os.environ.get('MAX_RESULTS', '100'))
        self.search_pattern = os.environ.get('SEARCH_PATTERN', 'sk-ant-oat01-')
        self.file_extensions = os.environ.get('FILE_EXTENSIONS', 'json').split(',')
        
        if not self.token:
            raise ValueError("❌ GITHUB_TOKEN 未设置")
            
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }
        
        # 确保报告目录存在
        os.makedirs('reports', exist_ok=True)
    
    def build_search_query(self) -> str:
        """构建搜索查询"""
        # 构建语言查询
        if len(self.file_extensions) == 1:
            language_query = f'language:{self.file_extensions[0]}'
        else:
            # 多个扩展名用 OR 连接
            ext_queries = [f'extension:{ext.strip()}' for ext in self.file_extensions]
            language_query = ' OR '.join(ext_queries)
            if len(ext_queries) > 1:
                language_query = f'({language_query})'
        
        base_query = f'{self.search_pattern} {language_query}'
        
        if self.search_scope:
            query = f'{base_query} {self.search_scope}'
        else:
            query = base_query
            
        return query
    
    def search_github_code(self) -> tuple[List[Dict], int]:
        """执行 GitHub 代码搜索"""
        query = self.build_search_query()
        print(f"🔍 搜索查询: {query}")
        print("=" * 80)
        
        results = []
        page = 1
        per_page = 30  # GitHub API 限制
        total_found = 0
        
        while len(results) < self.max_results:
            try:
                print(f"📄 正在搜索第 {page} 页...")
                
                # GitHub Code Search API
                search_url = 'https://api.github.com/search/code'
                params = {
                    'q': query,
                    'page': page,
                    'per_page': min(per_page, self.max_results - len(results))
                }
                
                response = requests.get(search_url, headers=self.headers, params=params)
                
                if response.status_code == 403:
                    print("⚠️  API 速率限制，等待 60 秒...")
                    time.sleep(60)
                    continue
                elif response.status_code != 200:
                    print(f"❌ API 请求失败: {response.status_code}")
                    print(f"响应: {response.text}")
                    break
                
                data = response.json()
                total_found = data.get('total_count', 0)
                items = data.get('items', [])
                
                if not items:
                    print("✅ 没有更多结果")
                    break
                
                for item in items:
                    file_info = self.get_file_details(item)
                    if file_info:
                        results.append(file_info)
                
                page += 1
                time.sleep(1)  # 避免 API 速率限制
                
            except Exception as e:
                print(f"❌ 搜索错误: {e}")
                break
        
        print(f"\n📊 搜索完成:")
        print(f"总共找到: {total_found} 个结果")
        print(f"已处理: {len(results)} 个文件")
        
        return results, total_found
    
    def get_file_details(self, item: Dict) -> Optional[Dict]:
        """获取文件的详细信息"""
        try:
            repo_info = item['repository']
            file_path = item['path']
            
            print(f"  📅 获取文件信息: {repo_info['full_name']}/{file_path}")
            
            # 获取时间和提交信息
            time_info = self._get_time_info(repo_info['full_name'], file_path)
            
            # 获取文件内容信息
            content_info = self._get_content_info(item)
            
            # 获取变更信息
            change_info = self._get_change_info(repo_info['full_name'], file_path, time_info)
            
            return {
                'repository': {
                    'name': repo_info['name'],
                    'full_name': repo_info['full_name'],
                    'owner': repo_info['owner']['login'],
                    'html_url': repo_info['html_url'],
                    'private': repo_info['private'],
                    'description': repo_info.get('description', ''),
                    'language': repo_info.get('language', ''),
                    'stars': repo_info.get('stargazers_count', 0),
                    'forks': repo_info.get('forks_count', 0),
                    'created_at': repo_info.get('created_at'),
                    'updated_at': repo_info.get('updated_at')
                },
                'file': {
                    'path': file_path,
                    'name': item['name'],
                    'html_url': item['html_url'],
                    'size': content_info.get('size', 0),
                    'match_count': content_info.get('match_count', 0)
                },
                'time_info': time_info,
                'change_info': change_info,
                'found_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"⚠️  获取文件详情失败 {item.get('path', 'unknown')}: {e}")
            return None
    
    def _get_time_info(self, repo_full_name: str, file_path: str) -> Dict:
        """获取文件的时间信息"""
        time_info = {
            'first_commit': {},
            'last_commit': {},
            'commit_history': [],
            'total_commits': 0,
            'file_age_days': None
        }
        
        try:
            # 获取所有提交记录
            commits_url = f"https://api.github.com/repos/{repo_full_name}/commits"
            params = {'path': file_path, 'per_page': 100}
            
            response = requests.get(commits_url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                commits_data = response.json()
                
                if commits_data:
                    # 最新提交
                    latest_commit = commits_data[0]
                    time_info['last_commit'] = {
                        'last_modified': latest_commit['commit']['committer']['date'],
                        'last_commit_sha': latest_commit['sha'],
                        'last_commit_message': self._truncate_message(latest_commit['commit']['message']),
                        'last_author': latest_commit['commit']['author']['name'],
                        'last_author_email': latest_commit['commit']['author']['email'],
                        'last_committer': latest_commit['commit']['committer']['name'],
                        'last_committer_date': latest_commit['commit']['committer']['date']
                    }
                    
                    # 最早提交
                    oldest_commit = commits_data[-1]
                    time_info['first_commit'] = {
                        'first_created': oldest_commit['commit']['author']['date'],
                        'first_commit_sha': oldest_commit['sha'],
                        'first_commit_message': self._truncate_message(oldest_commit['commit']['message']),
                        'first_author': oldest_commit['commit']['author']['name'],
                        'first_author_email': oldest_commit['commit']['author']['email'],
                        'creation_committer': oldest_commit['commit']['committer']['name'],
                        'creation_committer_date': oldest_commit['commit']['committer']['date']
                    }
                    
                    # 计算文件年龄
                    try:
                        created_date = parser.parse(oldest_commit['commit']['author']['date'])
                        file_age = (datetime.now(created_date.tzinfo) - created_date).days
                        time_info['file_age_days'] = file_age
                    except:
                        pass
                    
                    # 提交历史
                    time_info['total_commits'] = len(commits_data)
                    for commit in commits_data[:10]:  # 前10次提交
                        time_info['commit_history'].append({
                            'sha': commit['sha'][:8],
                            'date': commit['commit']['author']['date'],
                            'author': commit['commit']['author']['name'],
                            'message': self._truncate_message(commit['commit']['message'], 50),
                            'committer_date': commit['commit']['committer']['date']
                        })
        
        except Exception as e:
            print(f"    ⚠️ 获取时间信息失败: {e}")
        
        return time_info
    
    def _get_content_info(self, item: Dict) -> Dict:
        """获取文件内容信息"""
        content_info = {'size': 0, 'match_count': 0}
        
        try:
            content_url = item['url']
            response = requests.get(content_url, headers=self.headers)
            
            if response.status_code == 200:
                content_data = response.json()
                content_info['size'] = content_data.get('size', 0)
                
                if content_data.get('content'):
                    try:
                        decoded_content = base64.b64decode(content_data['content']).decode('utf-8')
                        content_info['match_count'] = decoded_content.count(self.search_pattern)
                    except:
                        pass
        
        except Exception as e:
            print(f"    ⚠️ 获取内容信息失败: {e}")
        
        return content_info
    
    def _get_change_info(self, repo_full_name: str, file_path: str, time_info: Dict) -> Dict:
        """获取文件变更信息"""
        change_info = {}
        
        try:
            last_commit_sha = time_info.get('last_commit', {}).get('last_commit_sha')
            if last_commit_sha:
                commit_url = f"https://api.github.com/repos/{repo_full_name}/commits/{last_commit_sha}"
                response = requests.get(commit_url, headers=self.headers)
                
                if response.status_code == 200:
                    commit_detail = response.json()
                    files_changed = commit_detail.get('files', [])
                    
                    for file_change in files_changed:
                        if file_change.get('filename') == file_path:
                            change_info = {
                                'additions': file_change.get('additions', 0),
                                'deletions': file_change.get('deletions', 0),
                                'changes': file_change.get('changes', 0),
                                'status': file_change.get('status', 'unknown'),
                                'previous_filename': file_change.get('previous_filename')
                            }
                            break
        
        except Exception as e:
            print(f"    ⚠️ 获取变更信息失败: {e}")
        
        return change_info
    
    def _truncate_message(self, message: str, max_length: int = 100) -> str:
        """截断提交消息"""
        if len(message) > max_length:
            return message[:max_length] + '...'
        return message
    
    def save_raw_data(self, results: List[Dict], total_found: int):
        """保存原始数据"""
        raw_data = {
            'scan_time': datetime.now().isoformat(),
            'search_query': self.build_search_query(),
            'search_pattern': self.search_pattern,
            'file_extensions': self.file_extensions,
            'search_scope': self.search_scope,
            'total_found': total_found,
            'analyzed_files': len(results),
            'results': results
        }
        
        with open('reports/raw_data.json', 'w', encoding='utf-8') as f:
            json.dump(raw_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 原始数据已保存到 reports/raw_data.json")


def main():
    """主函数"""
    try:
        print("🚀 开始 GitHub 代码搜索...")
        
        searcher = GitHubSearcher()
        results, total_found = searcher.search_github_code()
        
        print(f"\n💾 保存原始数据...")
        searcher.save_raw_data(results, total_found)
        
        print(f"\n✅ 搜索完成！")
        if results:
            print(f"⚠️  发现 {len(results)} 个文件包含敏感内容")
            print(f"🔍 涉及 {len(set(r['repository']['full_name'] for r in results))} 个仓库")
            public_count = sum(1 for r in results if not r['repository']['private'])
            if public_count > 0:
                print(f"🚨 警告: {public_count} 个文件在公开仓库中!")
        else:
            print("✅ 未发现敏感内容")
            
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
        exit(1)


if __name__ == "__main__":
    main()
