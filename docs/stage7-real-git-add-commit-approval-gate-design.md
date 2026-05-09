# T139：real Git add/commit approval gate 设计
## 1. 设计目标
T139 的目标是设计 `real Git add/commit approval gate`，为后续 Stage 7 中受控的真实 Git 暂存与提交流程建立安全边界。
真实 `git add` 会改变 Git 暂存区，真实 `git commit` 会写入 Git 历史。相比此前的 dry-run、proposal、controlled apply 和 guarded Git backup dry-run，这一步风险更高。
因此，在系统未来允许执行真实 `git add` 和 `git commit` 之前，必须先设计清楚审批条件、文件范围限制、提交信息限制、审计记录、失败保护和后续验证流程。
本设计仍然属于 Stage 7：真实单任务自动执行。
本设计不进入 Stage 8，不涉及连续任务自动推进。
## 2. 当前边界
T139 只做设计，不实现代码。
当前仍然禁止：
- 禁止真实 `git add`
- 禁止真实 `git commit`
- 禁止真实 `git push`
- 禁止 automatic Git backup
- 禁止进入 Stage 8
- 禁止连续任务自动推进
- 禁止调用 Claude Code 做真实任务执行
- 禁止自动修改暂存区
- 禁止自动写入 Git 历史
T139 的输出应仅限于设计文档和必要任务记录。
## 3. real Git add approval gate 设计
未来系统在执行真实 `git add` 前，必须满足以下条件。
### 3.1 用户确认条件
必须存在明确的用户授权。
允许的确认方式可以包括：
- 用户显式传入 `--confirm`
- 用户确认当前任务允许进入 real git add/commit dry-run 流程
- approval record 中记录确认来源和确认时间
在 T139/T140 dry-run 阶段，即使存在确认，也不能真实执行 `git add`。
### 3.2 当前任务状态条件
必须确认：
- 当前任务存在
- 当前任务属于 Stage 7
- 当前任务状态允许进入提交准备阶段
- 当前任务不是 Stage 8 或后续阶段任务
- 当前任务不是连续自动推进任务
### 3.3 工作区检查条件
执行真实 `git add` 前必须检查：
- `git status --short`
- 当前分支
- 当前 base commit
- 当前 diff summary
- 是否存在未分类文件
- 是否存在与当前任务无关的修改
如果发现未知修改，必须停止，等待人工确认。
### 3.4 文件范围限制
只能允许 add 白名单范围内的文件。
允许范围应根据当前任务动态生成，例如：
- 当前任务相关设计文档
- 当前任务相关报告文件
- 当前任务允许修改的 docs 文件
- 当前任务允许修改的 reports 文件
- 当前任务允许修改的 memory 文件
默认禁止：
- 未分类文件
- 与当前任务无关的业务代码
- 大体积二进制文件
- 未知扩展名文件
- 临时文件
- 系统生成文件
- `.env`
- secret 文件
- token 文件
- key 文件
- credential 文件
- 私有配置文件
### 3.5 敏感文件保护
以下文件或路径必须默认拒绝：
- `.env`
- `.env.local`
- `.env.*`
- `*.pem`
- `*.key`
- `*.p12`
- `*.pfx`
- `id_rsa`
- `id_ed25519`
- 包含 `secret` 的文件
- 包含 `token` 的文件
- 包含 `credential` 的文件
- 包含 `password` 的文件
- 其他可能包含认证信息的文件
如果这些文件出现在工作区，gate 必须 fail。
### 3.6 approval record 要求
执行真实 `git add` 前必须生成 approval record。
record 至少要记录：
- planned files to add
- blocked files
- allowed scope
- current branch
- base commit
- diff summary
- dry-run 状态
- real execution 是否允许
- push 是否允许
在 T139/T140 阶段：
- `real_execution_allowed` 必须为 `false`
- `push_allowed` 必须为 `false`
### 3.7 dry-run 预览要求
在真实 add 之前，必须支持 dry-run 预览：
- 预览将被 add 的文件
- 预览被拒绝的文件
- 预览拒绝原因
- 预览 approval record
- 预览后续 commit message
dry-run 不得改变暂存区。
## 4. real Git commit approval gate 设计
未来系统在执行真实 `git commit` 前，必须满足以下条件。
### 4.1 staged files 一致性检查
commit 前必须确认 staged files 与 approval record 完全一致。
必须检查：
- 是否存在未审批 staged 文件
- 是否缺少 planned staged files
- 是否存在额外 staged 文件
- staged diff 是否与审批记录一致
如果 staged files 与 approval record 不一致，必须拒绝 commit。
### 4.2 commit message 检查
commit message 必须满足：
- 不能为空
- 必须与当前 task_id 匹配
- 必须符合项目提交信息风格
- 不能伪造其他任务编号
- 不能声明未完成的任务已经完成
- 不能包含误导性 stage 信息
例如 T140 的提交信息可以类似：
```text
docs: add T140 real git commit dry-run approval record
````
但不能在 T139/T140 阶段声明已经完成真实自动提交能力。
### 4.3 commit 前重新检查
执行真实 commit 前必须重新检查：
* `git status --short`
* `git diff --cached --stat`
* `git diff --cached`
* 当前分支
* base commit
* approval record
* staged files list
如果检查结果与 approval record 不一致，必须停止。
### 4.4 commit 失败保护
如果 commit 失败：
* 不得自动 push
* 不得自动重试无限次
* 必须记录失败原因
* 必须保留现场供人工检查
* 必须输出恢复建议
### 4.5 commit 成功后的记录
如果未来真实 commit 成功，必须记录：
* commit hash
* commit message
* committed files
* branch
* base commit
* final status
* 是否允许 push
即使 commit 成功，也不能自动 push。
push 必须由后续单独 gate 处理。
## 5. Approval record 数据结构设计
Approval record 可以使用 Markdown、YAML 或 JSON-like schema。
建议结构如下：
```yaml
task_id: T140
stage: Stage 7
operation_type: real_git_add_commit_dry_run
approval_mode: human_reviewed
approved_by: user
approval_time: null
repo: multi-agent-runner
branch: main
base_commit: null
planned_files_to_add:
  - docs/example.md
blocked_files: []
allowed_scope:
  - docs/
  - reports/
  - memory/
diff_summary:
  files_changed: 0
  insertions: 0
  deletions: 0
  notes: pending dry-run evaluation
staged_diff_required: true
commit_message: "docs: add T140 real git commit dry-run approval record"
dry_run: true
real_execution_allowed: false
push_allowed: false
validation_required: true
final_status: pending
notes:
  - T139/T140 阶段不得真实 git add
  - T139/T140 阶段不得真实 git commit
  - push_allowed 必须保持 false
```
关键约束：
```text
real_execution_allowed 在 T139/T140 dry-run 阶段必须保持 false
push_allowed 必须保持 false
```
## 6. Pass / fail 场景设计
### 6.1 Pass 场景
以下情况可以通过 dry-run gate：
1. 只有当前任务相关文档文件。
2. 文件范围在 allowed scope 内。
3. commit message 与 task_id 匹配。
4. approval record 字段完整。
5. dry-run 状态下不会真实 add/commit。
6. 当前分支明确且安全。
7. 没有敏感文件。
8. 没有未分类文件。
9. 没有与当前任务无关的修改。
10. push_allowed 为 false。
### 6.2 Fail 场景
以下情况必须拒绝：
1. 存在未分类文件。
2. 存在 `.env` 或 secret 类文件。
3. staged files 与 approval record 不一致。
4. commit message 为空。
5. commit message 与当前 task_id 不匹配。
6. 用户未明确确认。
7. 当前分支未知或不安全。
8. 工作区存在与当前任务无关的修改。
9. 尝试 push。
10. 尝试进入 Stage 8。
11. approval record 缺少关键字段。
12. `real_execution_allowed` 在 dry-run 阶段被设置为 true。
13. `push_allowed` 被设置为 true。
14. 检测到大体积二进制或未知文件。
15. 检测到 credential、token、key、password 等风险文件。
## 7. CLI / workflow 入口建议
T139 只做设计，不实现 CLI。
未来 T140/T141 可以考虑的命令形式：
```powershell
python runner.py git-commit-dry-run --task T140
python runner.py git-commit-dry-run --task T140 --confirm
```
建议 workflow：
1. 读取当前 task_id。
2. 检查当前 stage。
3. 检查工作区状态。
4. 生成 candidate files。
5. 应用 allowed scope validator。
6. 生成 approval record。
7. 预览 planned git add。
8. 预览 planned commit message。
9. 输出 pass/fail 结果。
10. 不执行真实 git add。
11. 不执行真实 git commit。
12. 不执行 git push。
T139 不新增真实命令，不实现 CLI，只提出 T140/T141 的实现方向。
## 8. 与前序任务的关系
T139 是 Stage 7 guarded Git backup dry-run 后的下一步设计任务。
与前序任务关系如下：
* T135：已经设计 guarded Git backup dry-run gate。
* T136：已经实现 guarded Git backup dry-run。
* T137：已经验证 guarded Git backup dry-run pass/fail 场景。
* T138：已经归档 Stage 7 Git backup dry-run 成果。
* T139：当前设计 real Git add/commit approval gate。
* T140：下一步实现 real Git add/commit dry-run with approval record。
* T141：验证 real Git add/commit dry-run pass/fail 场景。
* T142：归档 Stage 7 Git commit dry-run 成果。
T139 不替代 T140/T141/T142。
T139 只给出设计边界和实现方向。
## 9. 后续任务建议
下一步建议：
```text
NEXT_PENDING=T140
NEXT_STAGE=Stage 7
```
T140 应实现 real Git add/commit dry-run with approval record。
但 T140 仍然必须保持：
* 不能真实 `git add`
* 不能真实 `git commit`
* 不能真实 `git push`
* 不能进入 Stage 8
* 不能自动连续任务推进
T140 的重点应是把 T139 的 approval gate 设计落成 dry-run 数据结构、校验流程和报告输出，为后续真实执行继续建立安全边界。
