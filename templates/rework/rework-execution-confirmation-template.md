# Rework Execution Confirmation

## Task

任务编号：

## Rework Round

R1 / R2 / R3

## Trigger

Tester FAIL / Specialized Tester FAIL / Reviewer REQUEST_CHANGES / Main REQUEST_CHANGES / Other

## Failure Evidence

-

## Suggested Rework Scope

-

## Files Allowed To Modify

-

## Files Forbidden To Modify

-

## Confirmation Required

请用户明确输入以下格式之一：

```text
确认执行 <task-id>-R<round> 返工

或：

APPROVE_REWORK task=<task-id> round=<round>
```

## Not Accepted

以下表达不视为确认：

```text
继续
可以
试一下
你看着办
自动处理
好的
OK
yes
go
do it
```

## Safety Notes

- 未确认前不得执行返工
- 不得超过 3 轮返工
- 不得修改禁止文件
- 不得打印 API Key
- 不得自动无限循环
