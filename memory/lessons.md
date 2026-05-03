# Lessons

## 第一阶段经验总结

1. **自动化流程必须从最小闭环开始。** 先跑通"读任务 → 生成 prompt → 调用 Claude Code → 判断结果 → 更新状态"，再逐步增加能力。

2. **任务状态必须可机器读写。** `docs/tasks.md` 用固定格式（`状态：pending / in_progress / done`），runner.py 通过正则解析和更新，不需要数据库。

3. **生成 prompt、执行 prompt、判断结果、更新状态要拆成独立能力。** 每个能力独立函数，通过命令行组合，方便调试和复用。

4. **returncode=0 只能说明 Claude Code 进程成功，不代表任务完成。** Claude Code 可能只输出了建议代码而没有实际修改文件。

5. **必须检查完成证据。** 以 `reports/dev/<任务编号>-dev-report.md` 是否存在作为最小完成证据。没有证据不标记 done。

6. **retry-current 是处理 in_progress 卡住任务的必要能力。** 任务执行不完整时，可以重新生成 prompt 并重新调用 Claude Code，不需要手动干预。

7. **Claude Code 非交互执行必须允许自动编辑文件。** 调用时需要 `--permission-mode acceptEdits`，否则 Claude Code 只会输出建议代码而不是实际修改文件。

8. **runner.py 应作为最外层调度器。** Claude Code 是被调用的执行器，不应在 Claude Code 执行过程中嵌套调用 runner.py 的自动执行命令。

## T020.1 第一次子项目自动执行成功经验

### 成果

`multi-agent-runner` 已经第一次成功驱动 `projects/down-100-floors-game` 自动完成真实开发任务 G002。

### 成功链路

1. `runner.py run-game-next` 读取子项目任务文件。
2. 自动找到 G002 pending。
3. 自动将 G002 标记为 in_progress。
4. 自动生成 G002 执行提示词。
5. 自动调用 Claude Code。
6. Claude Code 自动修改子项目文件。
7. Claude Code 自动生成 `projects/down-100-floors-game/reports/dev/G002-dev-report.md`。
8. runner 检查完成证据。
9. G002 自动标记为 done。
10. index.html 可以在浏览器打开。

### 关键经验

- 子项目任务清单可以独立于主项目任务清单。
- 主框架可以通过专用命令驱动子项目任务。
- 完成证据检查对自动化判断非常关键。
- 验证项目应先从最小页面开始，不要一开始实现复杂玩法。
- 真实项目验证中发现的问题，应回写主框架。
