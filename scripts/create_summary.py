#!/usr/bin/env python3
"""
GitHub Actions 摘要生成脚本
为 GitHub Actions 创建执行摘要
"""

import json
import os


def create_github_summary():
    """创建 GitHub Actions 执行摘要"""
    
    try:
        # 读取摘要数据
        with open('reports/summary.json', 'r', encoding='utf-8') as f:
            summary_data = json.load(f)
        
        summary = summary_data.get('summary', {})
        critical_findings = summary_data.get('critical_findings', [])
        recommendations = summary_data.get('recommendations', [])
        
        # 获取 GitHub Step Summary 文件路径
        github_summary_file = os.environ.get('GITHUB_STEP_SUMMARY')
        if not github_summary_file:
            print("⚠️ GITHUB_STEP_SUMMARY 环境变量未设置")
            return
        
        with open(github_summary_file, 'a', encoding='utf-8') as f:
            f.write("## 🔍 GitHub 代码搜索结果\n\n")
            
            # 基本统计
            total_found = summary_data.get('total_found', 0)
            analyzed = summary_data.get('analyzed_files', 0)
            
            f.write(f"- **总共发现**: {total_found} 个匹配项\n")
            f.write(f"- **已分析文件**: {analyzed} 个\n")
            f.write(f"- **公开仓库**: {summary.get('public_repos', 0)} 个文件\n")
            f.write(f"- **私有仓库**: {summary.get('private_repos', 0)} 个文件\n")
            f.write(f"- **总匹配次数**: {summary.get('total_matches', 0)} 次\n")
            f.write(f"- **涉及仓库数**: {summary.get('repository_count', 0)} 个\n")
            f.write(f"- **总提交次数**: {summary.get('total_commits', 0)} 次\n")
            f.write(f"- **最老文件**: {summary.get('oldest_file_days', 0)} 天前创建\n")
            f.write(f"- **最新文件**: {summary.get('newest_file_days', 0)} 天前创建\n")
            f.write(f"- **涉及作者数**: {summary.get('author_count', 0)} 人\n\n")
            
            # 风险评估
            risk_level = summary.get('risk_level', 'UNKNOWN')
            risk_emojis = {
                'CRITICAL': '🚨',
                'HIGH': '⚠️',
                'MEDIUM': '🟡',
                'LOW': '🟢',
                'NONE': '✅'
            }
            risk_emoji = risk_emojis.get(risk_level, '❓')
            
            f.write(f"### {risk_emoji} 风险等级: {risk_level}\n\n")
            
            # 安全警告
            if summary.get('public_repos', 0) > 0:
                f.write("🚨 **安全警告**: 在公开仓库中发现敏感内容!\n\n")
            
            # 关键发现
            if critical_findings:
                f.write("### 🎯 关键发现\n\n")
                for finding in critical_findings[:5]:  # 只显示前5个
                    f.write(f"- **{finding['repository']}**: {finding['file']} ({finding['matches']} 次匹配)\n")
                
                if len(critical_findings) > 5:
                    f.write(f"- ... 还有 {len(critical_findings) - 5} 个关键发现\n")
                f.write("\n")
            
            # 涉及的仓库
            repositories = summary.get('repositories', [])
            if repositories:
                f.write("### 📋 涉及的仓库\n\n")
                for repo in repositories[:10]:  # 只显示前10个
                    f.write(f"- {repo}\n")
                
                if len(repositories) > 10:
                    f.write(f"- ... 还有 {len(repositories) - 10} 个仓库\n")
                f.write("\n")
            
            # 涉及的作者
            authors = summary.get('unique_authors', [])
            if authors:
                f.write(f"### 👥 涉及的作者 (前10位)\n\n")
                for author in authors[:10]:
                    f.write(f"- {author}\n")
                if len(authors) > 10:
                    f.write(f"- ... 还有 {len(authors) - 10} 位作者\n")
                f.write("\n")
            
            # 文件类型分布
            extensions = summary.get('file_extensions', {})
            if extensions:
                f.write("### 📁 文件类型分布\n\n")
                for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"- **{ext}**: {count} 个文件\n")
                f.write("\n")
            
            # 安全建议
            if recommendations:
                f.write("### 💡 安全建议\n\n")
                for rec in recommendations:
                    f.write(f"- {rec}\n")
                f.write("\n")
            
            # 报告文件链接
            f.write("### 📊 详细报告\n\n")
            f.write("请在 Actions 的 Artifacts 中下载以下详细报告:\n")
            f.write("- `search_results.txt` - 完整文本报告\n")
            f.write("- `detailed_report.json` - 详细 JSON 数据\n")
            f.write("- `search_results.csv` - CSV 表格数据\n")
            f.write("- `search_results.md` - Markdown 格式报告\n")
            f.write("- `summary.json` - 执行摘要\n")
            
        print("✅ GitHub Actions 摘要已生成")
        
    except FileNotFoundError:
        print("❌ 找不到摘要文件，请确保先运行了报告生成脚本")
    except Exception as e:
        print(f"❌ 生成 GitHub 摘要失败: {e}")


def create_notification_data():
    """创建通知数据（用于外部集成）"""
    try:
        with open('reports/summary.json', 'r', encoding='utf-8') as f:
            summary_data = json.load(f)
        
        summary = summary_data.get('summary', {})
        
        # 创建简化的通知数据
        notification_data = {
            'timestamp': summary_data.get('scan_time'),
            'risk_level': summary.get('risk_level', 'UNKNOWN'),
            'total_files': summary_data.get('analyzed_files', 0),
            'public_repos': summary.get('public_repos', 0),
            'total_matches': summary.get('total_matches', 0),
            'repositories': summary.get('repository_count', 0),
            'needs_immediate_attention': summary.get('public_repos', 0) > 0,
            'summary_url': f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"
        }
        
        with open('reports/notification.json', 'w', encoding='utf-8') as f:
            json.dump(notification_data, f, indent=2, ensure_ascii=False)
        
        print("📱 通知数据已生成")
        
        # 如果配置了环境变量，可以发送到外部系统
        webhook_url = os.environ.get('SECURITY_WEBHOOK_URL')
        if webhook_url and notification_data['needs_immediate_attention']:
            print("🚨 检测到需要立即关注的安全问题")
            # 这里可以添加发送到 Slack、Teams 等的逻辑
            
    except Exception as e:
        print(f"❌ 生成通知数据失败: {e}")


def main():
    """主函数"""
    print("📝 生成 GitHub Actions 摘要...")
    
    create_github_summary()
    create_notification_data()
    
    print("✅ 摘要生成完成")


if __name__ == "__main__":
    main()
