# Command Permission Policy

## 1. 目标

建立 Claude Code 安全命令自动执行白名单，让低风险命令可以自动执行，同时保留高风险操作的人工确认边界。

## 2. 为什么需要命令权限白名单

真正自动化不能每条低风险命令都等待人工确认。但如果完全放开权限，又存在误操作风险。

权限白名单的核心思路：

- 低风险命令自动执行，减少交互摩擦
- Git 备份命令在明确备份任务中自动执行
- 文件修改和删除需要人工确认或任务显式授权
- 危险命令禁止自动执行
- `.env` 和 API Key 永远不能提交或打印

## 3. 权限分级总览

| 级别 | 说明 | 默认行为 |
|------|------|----------|
| A 类 | 低风险自动执行命令 | 自动执行，无需确认 |
| B 类 | 仅 Git 备份任务中自动执行 | 只在明确 Git 备份任务中自动执行 |
| C 类 | 需要人工确认或任务显式授权 | 默认需确认，任务明确授权时可执行 |
| D 类 | 禁止自动执行 | 任何情况下都禁止自动执行 |

## 4. A 类命令：低风险自动执行

A 类命令属于只读检查、状态查看、编译验证、文件内容查看，可以自动执行。

### Git 只读检查

```bash
git status
git status --short
git diff --stat
git log --oneline -1
git log --oneline -5
git branch --show-current
git remote -v
git check-ignore -v .env
```

### Python 编译与运行检查

```bash
python runner.py
python -m py_compile runner.py
python -m py_compile tools/full_task_runner.py
python -m py_compile tools/env_loader.py
python -m py_compile tools/project_runner.py
python -m py_compile tools/tester_runner.py
python -m py_compile tools/reviewer_runner.py
python -m py_compile tools/main_agent.py
```

### PowerShell 文件检查

```powershell
Test-Path <path>
Get-Content <path> -Encoding UTF8 -Tail <number>
Get-Content <path> -Encoding UTF8 -Head <number>
Select-String -Path <path> -Pattern "<pattern>"
```

### A 类命令用途

- 检查当前 pending 任务
- 检查 Git 工作区状态
- 检查完成证据是否存在
- 查看报告尾部内容
- 查看任务状态
- 检查 .env 是否被忽略
- 检查 Python 文件是否能编译

### A 类命令限制

- A 类命令不得打印 `.env` 内容
- A 类命令不得打印 API Key
- A 类命令不得包含删除、恢复、覆盖、重置操作

## 5. B 类命令：仅 Git 备份任务中自动执行

B 类命令会改变 Git 历史或远程仓库，只能在明确 Git 备份任务中自动执行。

### 允许命令

```bash
git add .
git commit -m "<message>"
git push
```

### 允许场景

- `Txxx.1 提交并推送...` 类任务
- `Txxx.2 提交并推送...` 类任务
- 阶段总结与 Git 备份任务
- 明确写有 `git commit` / `git push` 验收标准的任务

### 不允许场景

- 普通开发任务（Developer）
- Tester 任务
- Reviewer 任务
- Main Decision 任务
- rework prompt 生成任务
- 未明确要求 Git 备份的任务

### 执行前必须检查

```bash
git status --short          # 确认待提交内容
git check-ignore -v .env    # 确认 .env 不会被提交
```

### 执行后必须检查

```bash
git status --short          # 确认工作区 clean
git log --oneline -1        # 确认提交成功
```

## 6. C 类命令：需要人工确认或任务显式授权

C 类命令可能修改、恢复、删除、覆盖单个文件，默认需要人工确认。

### 典型命令

```bash
git restore <file>
git checkout -- <file>
Remove-Item <file>
Move-Item <source> <target>
Copy-Item <source> <target>
```

### 允许示例

- 恢复 `current_prompt.md` 临时文件
- 删除明确指定的单个失败运行日志
- 移动明确指定的报告文件

### 不允许泛化为

- 删除整个目录
- 批量删除 `reports/`
- 批量删除 `memory/`
- 批量删除 `projects/`

### 执行条件

只有当任务提示词中明确写有 "你可以自动执行以下命令" 并列出具体命令时，C 类命令才可自动执行。

## 7. D 类命令：禁止自动执行

D 类命令风险过高，任何情况下都禁止自动执行。

### Git 危险操作

```bash
git reset --hard
git clean -fd
git clean -fdx
```

### 文件系统危险操作

```bash
Remove-Item -Recurse
Remove-Item -Force -Recurse
rm -rf
del /s
rmdir /s
```

### 绝对禁止事项

- 删除 `.git/`
- 删除 `reports/`
- 删除 `memory/`
- 删除 `projects/`
- 删除 `docs/`
- 删除 `workflows/`
- 打印 `.env` 内容
- 打印 API Key
- 修改 API Key
- 提交 `.env`
- 提交 secrets
- 批量覆盖未知文件

## 8. Claude Code /permissions 配置建议

可以在 Claude Code 中使用 `/permissions` 命令管理权限。

### 建议优先允许的 A 类模式

```
Bash(git status*)
Bash(git diff --stat*)
Bash(git log --oneline*)
Bash(git branch --show-current*)
Bash(git remote -v*)
Bash(git check-ignore*)
Bash(python runner.py*)
Bash(python -m py_compile*)
Bash(Test-Path*)
Bash(Get-Content*)
Bash(Select-String*)
```

### Git 备份命令的配置建议

不建议全局长期放开 Git 备份命令权限。建议在明确 Git 备份任务中临时允许：

```
Bash(git add .)
Bash(git commit*)
Bash(git push*)
```

如果确实要长期允许，也必须遵守本项目规则：

- 只能在 Git 备份任务中使用
- 执行前检查 `git status`
- 不允许提交 `.env`
- 执行后确认工作区 clean

## 9. full task loop 中的命令执行规则

`run-project-task-full` 可以自动执行：

- 状态检查
- 完成证据检查
- Python 编译检查
- Basic Tester
- Specialized Tester
- Reviewer
- Main Decision
- full-loop-report 生成

### 必须停止的情况

- Claude Code 超时
- Reviewer API 失败
- DeepSeek API 429
- 缺少 API Key
- Tester BLOCKED
- Main Agent BLOCKED
- 任务状态和完成证据冲突且无法判断
- 需要删除或恢复文件
- 需要执行 D 类命令

## 10. Git 备份任务中的命令执行规则

在明确 Git 备份任务中，Claude Code 可以自动执行：

```bash
git status --short          # 检查待提交内容
git check-ignore -v .env    # 确认 .env 不被提交
git diff --stat             # 查看变更统计
python runner.py            # 确认下一个 pending
git add .                   # 暂存所有变更
git commit -m "<message>"   # 提交
git push                    # 推送
git status --short          # 确认 clean
git log --oneline -1        # 确认提交
```

### 必须遵守

- 不提交 `.env`
- 不打印 API Key
- 不修改 `.env`
- 不执行 `git reset --hard`
- 不执行 `git clean -fd`
- 不删除任何目录

## 11. API Key 与 .env 安全规则

| 规则 | 说明 |
|------|------|
| `.env` 可以存在于本地 | 用于存储 API Key 等敏感配置 |
| `.env` 必须被 `.gitignore` 忽略 | 防止意外提交 |
| `.env.example` 可以提交 | 安全示例文件，不含真实 Key |
| 不得打印 `.env` 内容 | 包括 `cat .env`、`Get-Content .env` 等 |
| 不得打印 `DEEPSEEK_API_KEY` | 任何输出中不得出现真实 Key |
| 不得将 API Key 写入 reports | 报告中不得包含真实 Key |
| 不得将 API Key 写入 memory | 经验记录中不得包含真实 Key |
| 不得将 API Key 写入 docs | 文档中不得包含真实 Key |
| 不得将 API Key 写入代码 | 源码中不得硬编码 Key |
| 不得将 API Key 写入 git commit | 提交信息和差异中不得出现 Key |

## 12. 风险场景示例

### 场景 1：误提交 .env

- 风险：API Key 泄露到远程仓库
- 防护：`.gitignore` 忽略 + 提交前 `git check-ignore -v .env`
- 策略：B 类命令执行前必须检查

### 场景 2：误执行 git reset --hard

- 风险：丢失所有未提交的工作
- 防护：D 类命令禁止自动执行
- 策略：任何情况下都不自动执行

### 场景 3：误删除项目目录

- 风险：丢失项目代码和报告
- 防护：D 类命令禁止自动执行
- 策略：删除命令不在白名单中

### 场景 4：API Key 出现在报告输出

- 风险：Key 泄露到日志或终端
- 防护：所有输出过滤 + 权限策略明确禁止
- 策略：A/B/C/D 四级都禁止打印 Key

## 13. 后续优化方向

- 将本策略固化到 runner 的权限检查模块中
- 让自动化命令在执行前进行安全分类
- 支持任务级别权限声明（任务提示词中声明允许的命令）
- 支持权限审计日志
- 支持权限策略版本管理
