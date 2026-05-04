# T027 Parse Test Output

## 测试 1：PASS + APPROVE（标准 Markdown fenced json）

**输入：**

```markdown
## Machine Readable Result

```json
{"status":"PASS","decision":"APPROVE","issues":[],"summary":"ok","next_action":"next"}
```
```

**解析结果：**

```
success=True
status='PASS'
decision='APPROVE'
issues=[]
summary='ok'
next_action='next'
```

**是否通过：** 是

---

## 测试 2：FAIL + REQUEST_CHANGES（无 json 标记的 fenced block）

**输入：**

```markdown
## Machine Readable Result

```
{"status":"FAIL","decision":"REQUEST_CHANGES","issues":["缺少开始按钮"],"summary":"部分验收标准未满足。","next_action":"请返工修复。"}
```
```

**解析结果：**

```
success=True
status='FAIL'
decision='REQUEST_CHANGES'
issues=['缺少开始按钮']
summary='部分验收标准未满足。'
next_action='请返工修复。'
```

**是否通过：** 是

---

## 测试 3：BLOCKED（整段内容是 JSON）

**输入：**

```json
{"status":"BLOCKED","decision":"BLOCKED","issues":["API 限额"],"summary":"审查被阻塞。","next_action":"等待额度恢复。"}
```

**解析结果：**

```
success=True
status='BLOCKED'
decision='BLOCKED'
issues=['API 限额']
summary='审查被阻塞。'
next_action='等待额度恢复。'
```

**是否通过：** 是

---

## 测试 4：缺少 Machine Readable Result

**输入：**

```
这是一个普通文本，没有结构化数据。
```

**解析结果：**

```
success=False
error='未找到 Machine Readable Result JSON 块'
```

**是否通过：** 是（正确报告未找到）

---

## 测试 5：非法 status 值

**输入：**

```json
{"status":"MAYBE","decision":"APPROVE","issues":[],"summary":"ok","next_action":"next"}
```

**解析结果：**

```
success=False
error='status 值不合法: MAYBE，可选: BLOCKED, FAIL, INFO, PASS, RETRY'
```

**是否通过：** 是（正确报告值不合法）

---

## 测试 6：缺少 decision 字段

**输入：**

```json
{"status":"PASS","issues":[],"summary":"ok","next_action":"next"}
```

**解析结果：**

```
success=False
error='未找到 Machine Readable Result JSON 块'
```

**是否通过：** 是（无法识别为有效的 Machine Readable Result，因为缺少 decision 字段）

---

## 总结

| 测试 | 场景 | success | 是否通过 |
|------|------|---------|----------|
| 1 | PASS + APPROVE (fenced json) | True | 是 |
| 2 | FAIL + REQUEST_CHANGES (plain fenced) | True | 是 |
| 3 | BLOCKED (纯 JSON) | True | 是 |
| 4 | 无结构化数据 | False | 是 |
| 5 | 非法 status | False | 是 |
| 6 | 缺少 decision | False | 是 |
