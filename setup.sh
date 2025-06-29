#!/bin/bash
# setup.sh - GitHub 敏感内容搜索项目设置脚本

set -e

echo "🚀 设置 GitHub 敏感内容搜索项目..."

# 创建目录结构
echo "📁 创建目录结构..."
mkdir -p .github/workflows
mkdir -p scripts
mkdir -p config
mkdir -p reports
mkdir -p docs

# 创建脚本文件
echo "📝 创建 Python 脚本文件..."

# 创建主搜索脚本
cat > scripts/github_search.py << 'EOF'
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

# [这里会包含完整的 GitHubSearcher 类代码]
# 由于空间限制，实际使用时需要复制完整的脚本内容

if __name__ == "__main__":
    main()
EOF

# 创建报告生成脚本
cat > scripts/generate_reports.py << 'EOF'
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

# [这里会包含完整的 ReportGenerator 类代码]
# 由于空间限制，实际使用时需要复制完整
