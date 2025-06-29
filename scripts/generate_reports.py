#!/usr/bin/env python3
"""
报告生成脚本
生成多种格式的安全扫描报告
"""

import json
import os
from datetime import datetime
from typing import Dict, List
import csv


class ReportGenerator:
    def __init__(self):
        self.raw_data_file = 'reports/raw_data.json'
        self.reports_dir = 'reports'
        
        # 确保报告目录存在
        os.makedirs(self.reports_dir, exist_ok=True)
        
        # 加载原始数据
        self.data = self._load_raw_data()
    
    def _load_raw_data(self) -> Dict:
        """加载原始数据"""
        try:
            with open(self.raw_data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print("❌ 原始数据文件不存在，请先运行搜索脚本")
            exit(1)
        except Exception as e:
            print(f"❌ 加载原始数据失败: {e}")
            exit(1)
    
    def generate_all_reports(self):
        """生成所有格式的报告"""
        print("📝 开始生成报告...")
        
        self.generate_text_report()
        self.generate_detailed_json_report()
        self.generate_csv_report()
        self.generate_markdown_report()
        self.generate_summary_report()
        
        print("✅ 所有报告已生成完成！")
    
    def generate_text_report(self):
        """生成文本格式报告"""
        print("📄 生成文本报告...")
        
        results = self.data.get('results', [])
        total_found = self.data.get('total_found', 0)
        
        with open(f'{self.reports_dir}/search_results.txt', 'w', encoding='utf-8') as f:
            f.write(f"GitHub 代码搜索结果报告\n")
            f.write("=" * 80 + "\n")
            f.write(f"扫描时间: {self.data.get('scan_time', 'N/A')}\n")
            f.write(f"搜索查询: {self.data.get('search_query', 'N/A')}\n")
            f.write(f"搜索模式: {self.data.get('search_pattern', 'N/A')}\n")
            f.write(f"文件类型: {', '.join(self.data.get('file_extensions', []))}\n")
            f.write(f"搜索范围: {self.data.get('search_scope', '全部公开仓库')}\n")
            f.write(f"总共找到: {total_found} 个结果\n")
            f.write(f"已分析: {len(results)} 个文件\n\n")
            
            if not results:
                f.write("✅ 未发现包含敏感内容的文件\n")
                return
            
            f.write("⚠️  发现以下文件包含敏感内容:\n\n")
            
            for i, result in enumerate(results, 1):
                self._write_file_details(f, i, result)
    
    def _write_file_details(self, f, index: int, result: Dict):
        """写入文件详细信息"""
        repo = result['repository']
        file_info = result['file']
        time_info = result.get('time_info', {})
        first_commit = time_info.get('first_commit', {})
        last_commit = time_info.get('last_commit', {})
        change_info = result.get('change_info', {})
        
        f.write(f"{index}. 仓库: {repo['full_name']}\n")
        f.write(f"   文件: {file_info['path']}\n")
        f.write(f"   URL: {file_info['html_url']}\n")
        f.write(f"   仓库类型: {'私有' if repo['private'] else '公开'}\n")
        f.write(f"   文件大小: {file_info['size']} bytes\n")
        f.write(f"   匹配次数: {file_info['match_count']}\n")
        
        # 详细时间信息
        f.write(f"\n   📅 时间信息:\n")
        if first_commit:
            f.write(f"   ├─ 首次创建: {first_commit.get('first_created', 'N/A')}\n")
            f.write(f"   ├─ 创建作者: {first_commit.get('first_author', 'N/A')}\n")
            f.write(f"   ├─ 创建提交: {first_commit.get('first_commit_sha', 'N/A')[:8]}\n")
            f.write(f"   ├─ 创建消息: {first_commit.get('first_commit_message', 'N/A')}\n")
        
        if last_commit:
            f.write(f"   ├─ 最后修改: {last_commit.get('last_modified', 'N/A')}\n")
            f.write(f"   ├─ 修改作者: {last_commit.get('last_author', 'N/A')}\n")
            f.write(f"   ├─ 最新提交: {last_commit.get('last_commit_sha', 'N/A')[:8]}\n")
            f.write(f"   ├─ 提交消息: {last_commit.get('last_commit_message', 'N/A')}\n")
        
        file_age = time_info.get('file_age_days')
        if file_age is not None:
            f.write(f"   ├─ 文件年龄: {file_age} 天\n")
        
        total_commits = time_info.get('total_commits', 0)
        f.write(f"   └─ 总提交数: {total_commits}\n")
        
        # 变更信息
        if change_info:
            f.write(f"\n   📊 最近变更:\n")
            f.write(f"   ├─ 状态: {change_info.get('status', 'N/A')}\n")
            f.write(f"   ├─ 新增行数: {change_info.get('additions', 0)}\n")
            f.write(f"   ├─ 删除行数: {change_info.get('deletions', 0)}\n")
            f.write(f"   └─ 总变更行数: {change_info.get('changes', 0)}\n")
            if change_info.get('previous_filename'):
                f.write(f"   └─ 原文件名: {change_info['previous_filename']}\n")
        
        # 修改历史
        commit_history = time_info.get('commit_history', [])
        if commit_history:
            f.write(f"\n   📝 最近修改历史:\n")
            for j, commit in enumerate(commit_history[:5], 1):
                f.write(f"   {j}. {commit['date'][:10]} - {commit['author']} - {commit['message']}\n")
        
        f.write(f"\n   🏢 仓库信息:\n")
        f.write(f"   ├─ 描述: {repo['description']}\n")
        f.write(f"   ├─ 主要语言: {repo['language']}\n")
        f.write(f"   ├─ 创建时间: {repo.get('created_at', 'N/A')}\n")
        f.write(f"   └─ Stars: {repo['stars']}, Forks: {repo['forks']}\n")
        
        f.write("\n" + "=" * 80 + "\n\n")
    
    def generate_detailed_json_report(self):
        """生成详细的 JSON 报告"""
        print("📄 生成详细 JSON 报告...")
        
        results = self.data.get('results', [])
        
        # 计算统计信息
        summary = self._calculate_summary(results)
        
        report_data = {
            **self.data,  # 包含原始数据
            'summary': summary,
            'report_generated_at': datetime.now().isoformat()
        }
        
        with open(f'{self.reports_dir}/detailed_report.json', 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    def _calculate_summary(self, results: List[Dict]) -> Dict:
        """计算统计摘要"""
        if not results:
            return {}
        
        # 基本统计
        public_repos = sum(1 for r in results if not r['repository']['private'])
        private_repos = sum(1 for r in results if r['repository']['private'])
        total_matches = sum(r['file']['match_count'] for r in results)
        repositories = list(set(r['repository']['full_name'] for r in results))
        
        # 时间统计
        file_ages = [r.get('time_info', {}).get('file_age_days') for r in results]
        file_ages = [age for age in file_ages if age is not None]
        
        oldest_file_days = max(file_ages) if file_ages else 0
        newest_file_days = min(file_ages) if file_ages else 0
        avg_file_age = sum(file_ages) / len(file_ages) if file_ages else 0
        
        # 作者统计
        authors = set()
        for r in results:
            time_info = r.get('time_info', {})
            first_author = time_info.get('first_commit', {}).get('first_author')
            last_author = time_info.get('last_commit', {}).get('last_author')
            if first_author:
                authors.add(first_author)
            if last_author:
                authors.add(last_author)
        
        # 提交统计
        total_commits = sum(r.get('time_info', {}).get('total_commits', 0) for r in results)
        
        # 文件扩展名统计
        extensions = {}
        for r in results:
            file_path = r['file']['path']
            ext = file_path.split('.')[-1].lower() if '.' in file_path else 'no_extension'
            extensions[ext] = extensions.get(ext, 0) + 1
        
        # 仓库语言统计
        languages = {}
        for r in results:
            lang = r['repository']['language'] or 'Unknown'
            languages[lang] = languages.get(lang, 0) + 1
        
        return {
            'public_repos': public_repos,
            'private_repos': private_repos,
            'total_matches': total_matches,
            'repositories': repositories,
            'repository_count': len(repositories),
            'oldest_file_days': oldest_file_days,
            'newest_file_days': newest_file_days,
            'avg_file_age_days': round(avg_file_age, 1),
            'total_commits': total_commits,
            'unique_authors': list(authors),
            'author_count': len(authors),
            'file_extensions': extensions,
            'repository_languages': languages,
            'risk_level': self._calculate_risk_level(public_repos, total_matches)
        }
    
    def _calculate_risk_level(self, public_repos: int, total_matches: int) -> str:
        """计算风险等级"""
        if public_repos > 0:
            if total_matches > 10:
                return "CRITICAL"
            elif total_matches > 5:
                return "HIGH"
            else:
                return "MEDIUM"
        elif total_matches > 0:
            return "LOW"
        else:
            return "NONE"
    
    def generate_csv_report(self):
        """生成 CSV 格式报告"""
        print("📄 生成 CSV 报告...")
        
        results = self.data.get('results', [])
        
        with open(f'{self.reports_dir}/search_results.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'repository_name', 'repository_owner', 'repository_private', 'repository_url',
                'file_path', 'file_name', 'file_url', 'file_size', 'match_count',
                'first_created', 'first_author', 'last_modified', 'last_author',
                'file_age_days', 'total_commits', 'last_commit_sha', 'change_status',
                'additions', 'deletions', 'repo_stars', 'repo_forks', 'repo_language'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                repo = result['repository']
                file_info = result['file']
                time_info = result.get('time_info', {})
                first_commit = time_info.get('first_commit', {})
                last_commit = time_info.get('last_commit', {})
                change_info = result.get('change_info', {})
                
                writer.writerow({
                    'repository_name': repo['full_name'],
                    'repository_owner': repo['owner'],
                    'repository_private': repo['private'],
                    'repository_url': repo['html_url'],
                    'file_path': file_info['path'],
                    'file_name': file_info['name'],
                    'file_url': file_info['html_url'],
                    'file_size': file_info['size'],
                    'match_count': file_info['match_count'],
                    'first_created': first_commit.get('first_created', ''),
                    'first_author': first_commit.get('first_author', ''),
                    'last_modified': last_commit.get('last_modified', ''),
                    'last_author': last_commit.get('last_author', ''),
                    'file_age_days': time_info.get('file_age_days', ''),
                    'total_commits': time_info.get('total_commits', 0),
                    'last_commit_sha': last_commit.get('last_commit_sha', ''),
                    'change_status': change_info.get('status', ''),
                    'additions': change_info.get('additions', 0),
                    'deletions': change_info.get('deletions', 0),
                    'repo_stars': repo['stars'],
                    'repo_forks': repo['forks'],
                    'repo_language': repo['language']
                })
    
    def generate_markdown_report(self):
        """生成 Markdown 格式报告"""
        print("📄 生成 Markdown 报告...")
        
        results = self.data.get('results', [])
        summary = self._calculate_summary(results)
        
        with open(f'{self.reports_dir}/search_results.md', 'w', encoding='utf-8') as f:
            f.write("# GitHub 敏感内容搜索报告\n\n")
            
            # 概览
            f.write("## 📊 扫描概览\n\n")
            f.write(f"- **扫描时间**: {self.data.get('scan_time', 'N/A')}\n")
            f.write(f"- **搜索模式**: `{self.data.get('search_pattern', 'N/A')}`\n")
            f.write(f"- **文件类型**: {', '.join(self.data.get('file_extensions', []))}\n")
            f.write(f"- **搜索范围**: {self.data.get('search_scope', '全部公开仓库')}\n")
            f.write(f"- **总共找到**: {self.data.get('total_found', 0)} 个结果\n")
            f.write(f"- **已分析**: {len(results)} 个文件\n\n")
            
            if summary:
                # 风险评估
                risk_level = summary.get('risk_level', 'UNKNOWN')
                risk_emoji = {'CRITICAL': '🚨', 'HIGH': '⚠️', 'MEDIUM': '🟡', 'LOW': '🟢', 'NONE': '✅'}.get(risk_level, '❓')
                f.write(f"## {risk_emoji} 风险评估: {risk_level}\n\n")
                
                # 统计摘要
                f.write("## 📈 统计摘要\n\n")
                f.write(f"- **公开仓库文件**: {summary.get('public_repos', 0)} 个\n")
                f.write(f"- **私有仓库文件**: {summary.get('private_repos', 0)} 个\n")
                f.write(f"- **总匹配次数**: {summary.get('total_matches', 0)} 次\n")
                f.write(f"- **涉及仓库数**: {summary.get('repository_count', 0)} 个\n")
                f.write(f"- **涉及作者数**: {summary.get('author_count', 0)} 人\n")
                f.write(f"- **平均文件年龄**: {summary.get('avg_file_age_days', 0)} 天\n")
                f.write(f"- **总提交次数**: {summary.get('total_commits', 0)} 次\n\n")
                
                # 文件扩展名分布
                extensions = summary.get('file_extensions', {})
                if extensions:
                    f.write("### 📁 文件类型分布\n\n")
                    for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True):
                        f.write(f"- **{ext}**: {count} 个文件\n")
                    f.write("\n")
                
                # 仓库语言分布
                languages = summary.get('repository_languages', {})
                if languages:
                    f.write("### 💻 仓库语言分布\n\n")
                    for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
                        f.write(f"- **{lang}**: {count} 个仓库\n")
                    f.write("\n")
            
            if not results:
                f.write("## ✅ 扫描结果\n\n")
                f.write("未发现包含敏感内容的文件。\n\n")
                return
            
            # 详细结果
            f.write("## 📋 详细发现\n\n")
            
            for i, result in enumerate(results, 1):
                repo = result['repository']
                file_info = result['file']
                time_info = result.get('time_info', {})
                
                f.write(f"### {i}. {repo['full_name']}\n\n")
                
                # 基本信息表格
                f.write("| 属性 | 值 |\n")
                f.write("|------|----|\n")
                f.write(f"| 文件路径 | [`{file_info['path']}`]({file_info['html_url']}) |\n")
                f.write(f"| 仓库类型 | {'🔒 私有' if repo['private'] else '🌐 公开'} |\n")
                f.write(f"| 文件大小 | {file_info['size']} bytes |\n")
                f.write(f"| 匹配次数 | {file_info['match_count']} |\n")
                
                first_commit = time_info.get('first_commit', {})
                last_commit = time_info.get('last_commit', {})
                
                if first_commit:
                    f.write(f"| 首次创建 | {first_commit.get('first_created', 'N/A')[:10]} |\n")
                    f.write(f"| 创建作者 | {first_commit.get('first_author', 'N/A')} |\n")
                
                if last_commit:
                    f.write(f"| 最后修改 | {last_commit.get('last_modified', 'N/A')[:10]} |\n")
                    f.write(f"| 修改作者 | {last_commit.get('last_author', 'N/A')} |\n")
                
                file_age = time_info.get('file_age_days')
                if file_age is not None:
                    f.write(f"| 文件年龄 | {file_age} 天 |\n")
                
                f.write(f"| 总提交数 | {time_info.get('total_commits', 0)} |\n")
                f.write(f"| Stars | {repo['stars']} |\n")
                f.write(f"| Forks | {repo['forks']} |\n")
                f.write("\n")
                
                # 仓库描述
                if repo.get('description'):
                    f.write(f"**描述**: {repo['description']}\n\n")
                
                f.write("---\n\n")
    
    def generate_summary_report(self):
        """生成简要摘要报告"""
        print("📄 生成摘要报告...")
        
        results = self.data.get('results', [])
        summary = self._calculate_summary(results)
        
        summary_data = {
            'scan_time': self.data.get('scan_time'),
            'search_pattern': self.data.get('search_pattern'),
            'total_found': self.data.get('total_found', 0),
            'analyzed_files': len(results),
            'summary': summary,
            'critical_findings': self._get_critical_findings(results),
            'recommendations': self._get_recommendations(summary)
        }
        
        with open(f'{self.reports_dir}/summary.json', 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
    
    def _get_critical_findings(self, results: List[Dict]) -> List[Dict]:
        """获取关键发现"""
        critical = []
        
        for result in results:
            if not result['repository']['private']:  # 公开仓库
                critical.append({
                    'repository': result['repository']['full_name'],
                    'file': result['file']['path'],
                    'matches': result['file']['match_count'],
                    'url': result['file']['html_url'],
                    'reason': 'Public repository exposure'
                })
        
        # 按匹配次数排序
        critical.sort(key=lambda x: x['matches'], reverse=True)
        return critical[:10]  # 只返回前10个
    
    def _get_recommendations(self, summary: Dict) -> List[str]:
        """获取安全建议"""
        recommendations = []
        
        risk_level = summary.get('risk_level', 'NONE')
        public_repos = summary.get('public_repos', 0)
        
        if risk_level in ['CRITICAL', 'HIGH']:
            recommendations.append("🚨 立即更换所有相关的 API 密钥")
            recommendations.append("📞 联系相关仓库所有者删除敏感内容")
            
        if public_repos > 0:
            recommendations.append("🔒 将包含敏感信息的仓库设为私有")
            recommendations.append("🧹 使用 BFG Repo-Cleaner 清理 Git 历史")
            
        recommendations.extend([
            "🛡️ 启用 GitHub Secret Scanning",
            "🔧 配置 pre-commit hooks 防止未来泄露",
            "📋 建立敏感信息管理流程",
            "🔄 定期运行安全扫描"
        ])
        
        return recommendations


def main():
    """主函数"""
    try:
        generator = ReportGenerator()
        generator.generate_all_reports()
        
        print(f"\n📁 报告文件位置:")
        print(f"├── reports/search_results.txt     (文本格式)")
        print(f"├── reports/detailed_report.json  (详细 JSON)")
        print(f"├── reports/search_results.csv    (CSV 表格)")
        print(f"├── reports/search_results.md     (Markdown)")
        print(f"├── reports/summary.json          (摘要)")
        print(f"└── reports/raw_data.json         (原始数据)")
        
    except Exception as e:
        print(f"❌ 报告生成失败: {e}")
        exit(1)


if __name__ == "__main__":
    main()
