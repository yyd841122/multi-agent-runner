# Rework Prompt Template

你现在是 Developer Agent。

## 当前项目

<project-root>

## 原任务

<original-task-id> <original-task-title>

## 返工任务

<rework-task-id> <rework-task-title>

## 返工目标

只修复以下失败项，不新增无关功能。

## 失败来源

### Tester

<tester-failure-summary>

### Behavior Tester

<behavior-tester-failure-summary>

### Reviewer

<reviewer-issues>

### Main Agent

<main-decision-reason>

## 允许修改文件

<allowed-files>

## 禁止修改文件

<blocked-files>

## 必须生成完成证据

<project-root>/reports/dev/<rework-task-id>-dev-report.md

## 限制要求

1. 不修改主框架文件。
2. 不修改禁止文件。
3. 不扩大任务范围。
4. 不实现无关功能。
5. 只修复失败项。
6. 修改后写清楚修复内容和验证建议。

请开始返工。
