# Batch Criticality Score 使用说明

这个脚本可以并行处理多个 GitHub 仓库的 criticality score 计算。

## 功能特性

- ✅ 从 `tokens.env` 文件读取多个 GitHub tokens
- ✅ 从 CSV 文件读取仓库列表
- ✅ 基于 token 数量自动并行处理
- ✅ 线程安全的 token 轮询分配
- ✅ 实时进度显示
- ✅ 结果汇总和统计
- ✅ 超时保护（每个仓库最多 5 分钟）
- ✅ 错误处理和日志记录

## 准备工作

### 1. 创建 tokens.env 文件

复制示例文件并填入你的 GitHub tokens：

```bash
cp tokens.env.example tokens.env
```

编辑 `tokens.env`，填入你的 GitHub tokens：

```bash
# tokens.env
GITHUB_TOKEN=ghp_your_token_1_here
GITHUB_TOKEN=ghp_your_token_2_here
GITHUB_TOKEN=ghp_your_token_3_here
```

支持的格式：
- 多行格式（每行一个 token）
- 逗号分隔格式：`GITHUB_AUTH_TOKEN=token1,token2,token3`
- 混合使用不同的变量名（`GITHUB_TOKEN`, `GITHUB_AUTH_TOKEN`, `GH_TOKEN`, `GH_AUTH_TOKEN`）

### 2. 创建 repos.csv 文件

复制示例文件并填入你要分析的仓库：

```bash
cp repos.csv.example repos.csv
```

CSV 文件格式：

```csv
repo_url
https://github.com/ossf/criticality_score
https://github.com/ossf/scorecard
https://github.com/kubernetes/kubernetes
```

**注意**：
- 第一行是列名（默认为 `repo_url`，可以自定义）
- 每行一个 GitHub 仓库 URL
- 必须是完整的 HTTPS URL 格式

## 使用方法

### 基本用法

```bash
# 使用默认设置
python3 batch_criticality_score.py repos.csv
```

### 高级用法

```bash
# 指定自定义列名
python3 batch_criticality_score.py repos.csv -c url

# 指定输出文件
python3 batch_criticality_score.py repos.csv -o my_results.txt

# 指定自定义 tokens 文件
python3 batch_criticality_score.py repos.csv -t my_tokens.env

# 手动设置并行工作线程数
python3 batch_criticality_score.py repos.csv -w 5

# 组合使用多个参数
python3 batch_criticality_score.py repos.csv -c repo_url -t tokens.env -o results.txt -w 10
```

### 命令行参数说明

```
positional arguments:
  csv_file              CSV 文件路径（包含仓库 URL）

optional arguments:
  -h, --help            显示帮助信息
  -c COLUMN, --column COLUMN
                        CSV 中包含仓库 URL 的列名（默认：repo_url）
  -t TOKENS, --tokens TOKENS
                        包含 GitHub tokens 的文件（默认：tokens.env）
  -o OUTPUT, --output OUTPUT
                        结果输出文件（默认：criticality_scores.txt）
  -w WORKERS, --workers WORKERS
                        并行工作线程数（默认：token 数量）
```

## 输出结果

### 控制台输出

脚本会实时显示处理进度：

```
Loaded 3 GitHub token(s)
Loaded 10 repository URL(s) from repos.csv
Using 3 parallel worker(s)

[Worker 0] Processing: https://github.com/ossf/criticality_score
[Worker 1] Processing: https://github.com/ossf/scorecard
[Worker 2] Processing: https://github.com/kubernetes/kubernetes
[Worker 0] ✓ Success: https://github.com/ossf/criticality_score
...

Results saved to: criticality_scores.txt

================================================================================
SUMMARY
================================================================================
Total repositories: 10
Successful: 9 (90.0%)
Failed: 1 (10.0%)
================================================================================

Total time: 125.34 seconds
Average time per repo: 12.53 seconds
```

### 结果文件

结果会保存到指定的输出文件（默认：`criticality_scores.txt`）：

```
================================================================================
Repository: https://github.com/ossf/criticality_score
Status: SUCCESS
--------------------------------------------------------------------------------
repo.name: criticality_score
repo.url: https://github.com/ossf/criticality_score
repo.language: Go
legacy.created_since: 87
legacy.updated_since: 0
legacy.contributor_count: 19
default_score: 0.78234
================================================================================
```

## 性能优化建议

1. **Token 数量**：建议使用 3-10 个 tokens，可以有效避免 GitHub API 速率限制
2. **并行度**：默认使用 token 数量作为并行度，通常是最优的
3. **超时设置**：每个仓库默认超时 5 分钟，可以在脚本中修改 `timeout` 参数

## 常见问题

### Q: 如何获取 GitHub Token？

A: 访问 https://github.com/settings/tokens 创建 Personal Access Token。
   需要的权限：`public_repo` 或 `repo`（用于私有仓库）

### Q: 为什么需要多个 tokens？

A: GitHub API 有速率限制（每小时 5000 次请求）。使用多个 tokens 可以：
   - 提高并行处理速度
   - 避免触发速率限制
   - 处理更多仓库

### Q: 如果某个仓库处理失败怎么办？

A: 脚本会继续处理其他仓库，失败的仓库会在结果文件中标记为 FAILED，
   并包含错误信息。你可以查看错误信息后单独重试。

### Q: 可以处理私有仓库吗？

A: 可以，但需要确保你的 GitHub tokens 有访问私有仓库的权限。

## 示例场景

### 场景 1：处理大量仓库

```bash
# 假设你有 1000 个仓库和 5 个 tokens
python3 batch_criticality_score.py large_repos.csv -w 5 -o large_results.txt
```

### 场景 2：测试少量仓库

```bash
# 使用单个 token 测试
echo "GITHUB_TOKEN=your_token" > test_tokens.env
python3 batch_criticality_score.py test_repos.csv -t test_tokens.env -w 1
```

### 场景 3：自定义 CSV 格式

如果你的 CSV 文件列名不是 `repo_url`：

```csv
url,name,stars
https://github.com/ossf/scorecard,scorecard,1000
```

使用：

```bash
python3 batch_criticality_score.py repos.csv -c url
```

## 故障排除

### 错误：tokens.env not found

确保 `tokens.env` 文件存在于当前目录，或使用 `-t` 参数指定路径。

### 错误：No valid GitHub tokens found

检查 `tokens.env` 文件格式是否正确，确保使用支持的变量名。

### 错误：Column 'repo_url' not found in CSV

使用 `-c` 参数指定正确的列名。

### 错误：criticality_score: command not found

确保已安装 `criticality_score` 命令：

```bash
go install github.com/ossf/criticality_score/v2/cmd/criticality_score@latest
```

## 技术细节

- **并发模型**：使用 Python 的 `ThreadPoolExecutor` 实现线程池
- **Token 分配**：线程安全的轮询算法（Round-Robin）
- **超时处理**：每个仓库最多处理 5 分钟
- **错误处理**：捕获并记录所有异常，不影响其他仓库的处理

## License

Apache License 2.0
