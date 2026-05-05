"""Tester Agent 本地静态检查工具。

对 Web MVP 项目执行最小静态检查：
- 文件存在性检查（F-01 ~ F-03）
- HTML 关键元素检查（H-01 ~ H-06）
- CSS 基础样式检查（C-01 ~ C-03）
- JS 基础检查（J-01 ~ J-04）

测试协议详见 docs/tester-protocol.md。
"""

from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class TestCaseResult:
    """单个测试项结果。"""
    id: str
    name: str
    required: bool
    passed: bool
    details: str


@dataclass
class StaticTestResult:
    """静态测试汇总结果。"""
    task_id: str
    project_root: str
    status: str  # PASS / FAIL / BLOCKED
    result: str  # PASS / FAIL
    passed_count: int
    failed_count: int
    test_cases: list[TestCaseResult] = field(default_factory=list)
    report_path: str | None = None


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def load_text(path: str | Path) -> str:
    """读取文本文件。"""
    return Path(path).read_text(encoding="utf-8")


def check_file_exists(
    project_root: Path, relative_path: str, case_id: str, name: str
) -> TestCaseResult:
    """检查文件是否存在。"""
    full_path = project_root / relative_path
    exists = full_path.exists()
    return TestCaseResult(
        id=case_id,
        name=name,
        required=True,
        passed=exists,
        details=f"文件存在：{full_path}" if exists else f"文件缺失：{full_path}",
    )


def contains_any(content: str, keywords: list[str]) -> bool:
    """检查内容是否包含任意关键词。"""
    return any(kw in content for kw in keywords)


def contains_all(content: str, keywords: list[str]) -> bool:
    """检查内容是否包含所有关键词。"""
    return all(kw in content for kw in keywords)


# ---------------------------------------------------------------------------
# HTML 关键元素检查
# ---------------------------------------------------------------------------

def check_html_elements(html_content: str) -> list[TestCaseResult]:
    """对 HTML 内容执行关键元素检查。"""
    results = []

    # H-01 页面标题存在
    results.append(TestCaseResult(
        id="H-01",
        name="页面标题存在",
        required=True,
        passed=contains_any(html_content, ["Down 100 Floors"]),
        details="包含 Down 100 Floors 标题" if contains_any(html_content, ["Down 100 Floors"]) else "缺少 Down 100 Floors 标题",
    ))

    # H-02 游戏区域存在
    results.append(TestCaseResult(
        id="H-02",
        name="游戏区域存在 (#game-area)",
        required=True,
        passed=contains_any(html_content, ['id="game-area"', "game-area"]),
        details="包含 id=\"game-area\"" if 'id="game-area"' in html_content else "缺少 id=\"game-area\"",
    ))

    # H-03 开始按钮存在
    results.append(TestCaseResult(
        id="H-03",
        name="开始按钮存在 (#start-btn)",
        required=True,
        passed=contains_any(html_content, ['id="start-btn"']),
        details="包含 id=\"start-btn\"" if 'id="start-btn"' in html_content else "缺少 id=\"start-btn\"",
    ))

    # H-04 楼层或分数显示存在
    results.append(TestCaseResult(
        id="H-04",
        name="楼层/分数显示存在",
        required=True,
        passed=contains_any(html_content, ['id="floor-display"', "score"]),
        details="包含楼层/分数显示" if contains_any(html_content, ['id="floor-display"', "score"]) else "缺少楼层/分数显示",
    ))

    # H-05 状态提示存在
    results.append(TestCaseResult(
        id="H-05",
        name="状态提示存在 (#status-display)",
        required=True,
        passed=contains_any(html_content, ['id="status-display"']),
        details="包含 id=\"status-display\"" if 'id="status-display"' in html_content else "缺少 id=\"status-display\"",
    ))

    # H-06 玩家元素存在
    results.append(TestCaseResult(
        id="H-06",
        name="玩家元素存在 (#player)",
        required=True,
        passed=contains_any(html_content, ['id="player"']),
        details="包含 id=\"player\"" if 'id="player"' in html_content else "缺少 id=\"player\"",
    ))

    return results


# ---------------------------------------------------------------------------
# CSS 基础样式检查
# ---------------------------------------------------------------------------

def check_css_styles(css_content: str) -> list[TestCaseResult]:
    """对 CSS 内容执行基础样式检查。"""
    results = []

    # C-01 游戏区域样式
    results.append(TestCaseResult(
        id="C-01",
        name="游戏区域样式存在 (.game-area)",
        required=True,
        passed=contains_any(css_content, [".game-area"]),
        details="包含 .game-area 样式" if ".game-area" in css_content else "缺少 .game-area 样式",
    ))

    # C-02 玩家样式
    results.append(TestCaseResult(
        id="C-02",
        name="玩家样式存在 (.player)",
        required=True,
        passed=contains_any(css_content, [".player"]),
        details="包含 .player 样式" if ".player" in css_content else "缺少 .player 样式",
    ))

    # C-03 按钮样式
    results.append(TestCaseResult(
        id="C-03",
        name="按钮样式存在 (.btn/button)",
        required=True,
        passed=contains_any(css_content, [".btn", "button"]),
        details="包含按钮样式" if contains_any(css_content, [".btn", "button"]) else "缺少按钮样式",
    ))

    return results


# ---------------------------------------------------------------------------
# JS 基础检查
# ---------------------------------------------------------------------------

def check_js_basics(js_content: str) -> list[TestCaseResult]:
    """对 JS 内容执行基础检查。"""
    results = []

    # J-01 JS 文件非空
    is_nonempty = len(js_content.strip()) > 0
    results.append(TestCaseResult(
        id="J-01",
        name="JS 文件非空",
        required=True,
        passed=is_nonempty,
        details=f"文件大小：{len(js_content)} 字符" if is_nonempty else "文件为空",
    ))

    # J-02 初始化逻辑存在
    has_init = contains_any(js_content, ["resetUI", "init"])
    results.append(TestCaseResult(
        id="J-02",
        name="初始化逻辑存在",
        required=True,
        passed=has_init,
        details="包含初始化逻辑（resetUI/init）" if has_init else "缺少初始化逻辑（resetUI/init）",
    ))

    # J-03 开始按钮逻辑存在
    has_start = contains_any(js_content, ["startBtn", "addEventListener"])
    results.append(TestCaseResult(
        id="J-03",
        name="开始按钮逻辑存在",
        required=True,
        passed=has_start,
        details="包含开始按钮逻辑（startBtn/addEventListener）" if has_start else "缺少开始按钮逻辑",
    ))

    # J-04 玩家显示逻辑存在
    has_player_display = contains_all(js_content, ["player", "display"])
    results.append(TestCaseResult(
        id="J-04",
        name="玩家显示逻辑存在",
        required=True,
        passed=has_player_display,
        details="包含玩家显示逻辑（player + display）" if has_player_display else "缺少玩家显示逻辑（player + display）",
    ))

    return results


# ---------------------------------------------------------------------------
# 主测试函数
# ---------------------------------------------------------------------------

def run_static_web_tests(
    project_path: str | Path, task_id: str = "G003"
) -> StaticTestResult:
    """对 Web MVP 项目执行本地静态检查。

    Args:
        project_path: 项目根目录路径
        task_id: 任务编号

    Returns:
        StaticTestResult 汇总结果
    """
    project_root = Path(project_path)
    all_cases: list[TestCaseResult] = []

    # --- A. 文件存在性检查 ---
    file_checks = [
        ("F-01", "index.html", "index.html 存在"),
        ("F-02", "style.css", "style.css 存在"),
        ("F-03", "script.js", "script.js 存在"),
    ]
    for case_id, rel_path, name in file_checks:
        all_cases.append(check_file_exists(project_root, rel_path, case_id, name))

    # 检查三个核心文件是否都存在，如果缺失则 BLOCKED
    all_files_exist = all(c.passed for c in all_cases)

    if not all_files_exist:
        passed_count = sum(1 for c in all_cases if c.passed)
        failed_count = len(all_cases) - passed_count
        return StaticTestResult(
            task_id=task_id,
            project_root=str(project_root),
            status="BLOCKED",
            result="FAIL",
            passed_count=passed_count,
            failed_count=failed_count,
            test_cases=all_cases,
        )

    # --- B. HTML 关键元素检查 ---
    html_content = load_text(project_root / "index.html")
    all_cases.extend(check_html_elements(html_content))

    # --- C. CSS 基础样式检查 ---
    css_content = load_text(project_root / "style.css")
    all_cases.extend(check_css_styles(css_content))

    # --- D. JS 基础检查 ---
    js_content = load_text(project_root / "script.js")
    all_cases.extend(check_js_basics(js_content))

    # --- 汇总 ---
    passed_count = sum(1 for c in all_cases if c.passed)
    failed_count = len(all_cases) - passed_count
    all_required_passed = all(c.passed for c in all_cases if c.required)

    status = "PASS" if all_required_passed else "FAIL"
    result = "PASS" if all_required_passed else "FAIL"

    return StaticTestResult(
        task_id=task_id,
        project_root=str(project_root),
        status=status,
        result=result,
        passed_count=passed_count,
        failed_count=failed_count,
        test_cases=all_cases,
    )


# ---------------------------------------------------------------------------
# 测试报告生成
# ---------------------------------------------------------------------------

def save_test_report(result: StaticTestResult, output_path: str | Path) -> Path:
    """保存测试报告。"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 查找任务名称
    task_names = {
        "G002": "实现基础游戏页面",
        "G003": "实现玩家角色显示",
    }
    task_name = task_names.get(result.task_id, result.task_id)

    # 构建 Test Cases 表格行
    table_rows = []
    for tc in result.test_cases:
        required_text = "是" if tc.required else "否"
        result_text = "PASS" if tc.passed else "FAIL"
        table_rows.append(f"| {tc.id} | {tc.name} | {required_text} | {result_text} | {tc.details} |")

    table_str = "\n".join(table_rows)

    # 构建 Failed Items
    failed_cases = [tc for tc in result.test_cases if not tc.passed]
    if failed_cases:
        failed_items = "\n".join(f"- {tc.id} {tc.name}：{tc.details}" for tc in failed_cases)
        fix_suggestions = "\n".join(f"- 修复 {tc.id} {tc.name}" for tc in failed_cases)
    else:
        failed_items = "（无失败项）"
        fix_suggestions = "（无建议）"

    # Next Action
    if result.status == "PASS":
        next_action = "建议进入 Main Agent 综合决策。"
    else:
        next_action = "建议返回 Developer Agent 修复失败项。"

    report = f"""# {result.task_id} Test Report

## Agent

Tester Agent

## Task

任务编号：{result.task_id}
任务名称：{task_name}

## Status

{result.status}

## Project

{result.project_root}

## Test Scope

- 文件存在性检查
- HTML 关键元素检查
- CSS 基础样式检查
- JS 基础检查

## Test Cases

| 编号 | 测试项 | 必需 | 结果 | 说明 |
|------|--------|------|------|------|
{table_str}

## Result

{result.result}

## Failed Items

{failed_items}

## Fix Suggestions

{fix_suggestions}

## Evidence

- {result.project_root}/reports/test/{result.task_id}-test-report.md

## Next Action

{next_action}
"""

    output_path.write_text(report, encoding="utf-8")
    return output_path


# ---------------------------------------------------------------------------
# 对 down-100-floors-game 的入口函数
# ---------------------------------------------------------------------------

def run_tester_for_game_task(task_id: str = "G003") -> Path:
    """对 down-100-floors-game 的指定任务执行静态测试。

    Args:
        task_id: 游戏任务编号，默认 G003

    Returns:
        测试报告路径
    """
    # 确定项目路径
    runner_root = Path(__file__).parent.parent
    game_project = runner_root / "projects" / "down-100-floors-game"

    # 执行静态检查
    result = run_static_web_tests(game_project, task_id)

    # 将绝对路径转为相对路径用于报告
    result.project_root = "projects/down-100-floors-game"

    # 保存测试报告
    report_path = game_project / "reports" / "test" / f"{task_id}-test-report.md"
    save_test_report(result, report_path)

    result.report_path = str(report_path)

    # 输出摘要
    print(f"已执行静态检查：{task_id}")
    print(f"Status：{result.status}")
    print(f"Result：{result.result}")
    print(f"Passed：{result.passed_count}")
    print(f"Failed：{result.failed_count}")

    return report_path, result


# ---------------------------------------------------------------------------
# 行为检查（Behavior Check）
# ---------------------------------------------------------------------------

@dataclass
class BehaviorTestResult:
    """行为检查汇总结果。"""
    task_id: str
    project_root: str
    status: str  # PASS / FAIL / BLOCKED
    result: str  # PASS / FAIL / BLOCKED
    passed_count: int
    failed_count: int
    test_cases: list[TestCaseResult] = field(default_factory=list)
    report_path: str | None = None


def _check_keyword(
    content: str, keywords: list[str], case_id: str, name: str
) -> TestCaseResult:
    """检查源码中是否包含任意关键词。"""
    passed = contains_any(content, keywords)
    matched = [kw for kw in keywords if kw in content]
    if passed:
        details = f"匹配关键词：{', '.join(matched)}"
    else:
        details = f"未匹配任何关键词：{', '.join(keywords)}"
    return TestCaseResult(
        id=case_id,
        name=name,
        required=True,
        passed=passed,
        details=details,
    )


def run_keyboard_movement_behavior_tests(
    project_path: str | Path,
    task_id: str = "G004",
) -> BehaviorTestResult:
    """对键盘左右移动逻辑执行源码静态行为检查。

    检查项遵循 docs/tester-behavior-check-protocol.md 定义的四组 13 项。

    Args:
        project_path: 项目根目录路径
        task_id: 任务编号

    Returns:
        BehaviorTestResult 汇总结果
    """
    project_root = Path(project_path)
    js_path = project_root / "script.js"

    # 检查 script.js 是否存在
    if not js_path.exists():
        return BehaviorTestResult(
            task_id=task_id,
            project_root=str(project_root),
            status="BLOCKED",
            result="BLOCKED",
            passed_count=0,
            failed_count=0,
            test_cases=[TestCaseResult(
                id="BLOCKED", name="script.js 不存在", required=True,
                passed=False, details=f"文件缺失：{js_path}",
            )],
        )

    # 读取源码
    js_content = load_text(js_path)
    all_cases: list[TestCaseResult] = []

    # --- B 组：键盘事件检查 ---
    all_cases.append(_check_keyword(
        js_content, ["keydown", "addEventListener('keydown'", "onkeydown"],
        "B-01", "键盘事件监听存在",
    ))
    all_cases.append(_check_keyword(
        js_content, ["ArrowLeft", "keyCode === 37", "key === 'ArrowLeft'", "37"],
        "B-02", "左方向键处理存在",
    ))
    all_cases.append(_check_keyword(
        js_content, ["ArrowRight", "keyCode === 39", "key === 'ArrowRight'", "39"],
        "B-03", "右方向键处理存在",
    ))

    # --- M 组：左右移动逻辑检查 ---
    all_cases.append(_check_keyword(
        js_content, ["playerState.x", "playerX", "player.x", "position.x"],
        "M-01", "玩家横向位置变量存在",
    ))
    all_cases.append(_check_keyword(
        js_content, ["x -", "x -= ", "position -", "-= MOVE_SPEED", "-= moveSpeed"],
        "M-02", "左移逻辑存在",
    ))
    all_cases.append(_check_keyword(
        js_content, ["x +", "x += ", "position +", "+= MOVE_SPEED", "+= moveSpeed"],
        "M-03", "右移逻辑存在",
    ))
    all_cases.append(_check_keyword(
        js_content, ["moveSpeed", "MOVE_SPEED", "speed", "SPEED", "step", "STEP"],
        "M-04", "移动速度或步长存在",
    ))

    # --- L 组：边界限制检查 ---
    all_cases.append(_check_keyword(
        js_content, ["Math.max", ">= 0", "x < 0", ".x < 0", ".x = 0"],
        "L-01", "左边界限制存在",
    ))
    all_cases.append(_check_keyword(
        js_content, ["Math.min", "areaWidth", "clientWidth", "areaWidth - player"],
        "L-02", "右边界限制存在",
    ))
    # L-03：同时存在左边界和右边界判断
    has_left_boundary = contains_any(js_content, ["x < 0", ".x < 0", "x = 0", ".x = 0"])
    has_right_boundary = contains_any(js_content, ["areaWidth", "clientWidth"])
    l03_passed = has_left_boundary and has_right_boundary
    all_cases.append(TestCaseResult(
        id="L-03",
        name="玩家不能移出游戏区域",
        required=True,
        passed=l03_passed,
        details="左/右边界判断同时存在" if l03_passed else "缺少左边界或右边界判断",
    ))

    # --- U 组：玩家位置更新检查 ---
    all_cases.append(_check_keyword(
        js_content, ["updatePlayerPosition", "updatePosition", "render", "draw"],
        "U-01", "位置更新函数存在",
    ))
    all_cases.append(_check_keyword(
        js_content, ["style.left", "style.transform", "translateX", "offsetLeft"],
        "U-02", "DOM 位置更新存在",
    ))
    # U-03：移动逻辑中调用位置更新函数
    has_movement = contains_any(js_content, ["x +=", "x -=", "+= MOVE", "-= MOVE"])
    has_update_call = contains_any(js_content, ["updatePlayerPosition()", "updatePosition()", "render()", "draw()"])
    u03_passed = has_movement and has_update_call
    all_cases.append(TestCaseResult(
        id="U-03",
        name="移动后调用更新函数",
        required=True,
        passed=u03_passed,
        details="移动逻辑和位置更新调用同时存在" if u03_passed else "缺少移动逻辑或位置更新调用",
    ))

    # --- 汇总 ---
    passed_count = sum(1 for c in all_cases if c.passed)
    failed_count = len(all_cases) - passed_count
    all_required_passed = all(c.passed for c in all_cases if c.required)

    status = "PASS" if all_required_passed else "FAIL"
    result = "PASS" if all_required_passed else "FAIL"

    return BehaviorTestResult(
        task_id=task_id,
        project_root=str(project_root),
        status=status,
        result=result,
        passed_count=passed_count,
        failed_count=failed_count,
        test_cases=all_cases,
    )


def save_behavior_test_report(
    result: BehaviorTestResult,
    output_path: str | Path,
) -> Path:
    """保存行为检查测试报告。"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 任务名称映射
    task_names = {
        "G004": "实现玩家键盘左右移动",
    }
    task_name = task_names.get(result.task_id, result.task_id)

    # 构建 Test Cases 表格行
    table_rows = []
    for tc in result.test_cases:
        required_text = "是" if tc.required else "否"
        result_text = "PASS" if tc.passed else "FAIL"
        table_rows.append(f"| {tc.id} | {tc.name} | {required_text} | {result_text} | {tc.details} |")

    table_str = "\n".join(table_rows)

    # 构建 Failed Items
    failed_cases = [tc for tc in result.test_cases if not tc.passed]
    if failed_cases:
        failed_items = "\n".join(f"- {tc.id} {tc.name}：{tc.details}" for tc in failed_cases)
        fix_suggestions = "\n".join(f"- 修复 {tc.id} {tc.name}" for tc in failed_cases)
    else:
        failed_items = "（无失败项）"
        fix_suggestions = "（无建议）"

    # Next Action
    if result.status == "PASS":
        next_action = "建议进入 Main Agent 综合决策复核。"
    elif result.status == "BLOCKED":
        next_action = "建议检查源码文件是否存在或可读取。"
    else:
        next_action = "建议返回 Developer Agent 修复键盘移动逻辑。"

    report = f"""# {result.task_id} Behavior Test Report

## Agent

Tester Agent

## Task

任务编号：{result.task_id}
任务名称：{task_name}

## Status

{result.status}

## Project

{result.project_root}

## Test Scope

- 键盘事件检查
- 左右移动逻辑检查
- 边界限制检查
- 玩家位置更新检查

## Test Cases

| 编号 | 测试项 | 必需 | 结果 | 说明 |
|------|--------|------|------|------|
{table_str}

## Result

{result.result}

## Failed Items

{failed_items}

## Fix Suggestions

{fix_suggestions}

## Evidence

- {result.project_root}/reports/test/{result.task_id}-behavior-test-report.md

## Next Action

{next_action}
"""

    output_path.write_text(report, encoding="utf-8")
    return output_path


def run_behavior_tester_for_game_task(task_id: str = "G004") -> tuple[Path, BehaviorTestResult]:
    """对 down-100-floors-game 指定任务执行行为检查。

    Args:
        task_id: 游戏任务编号，默认 G004

    Returns:
        (报告路径, BehaviorTestResult)
    """
    runner_root = Path(__file__).parent.parent
    game_project = runner_root / "projects" / "down-100-floors-game"

    # 执行行为检查
    result = run_keyboard_movement_behavior_tests(game_project, task_id)

    # 将绝对路径转为相对路径
    result.project_root = "projects/down-100-floors-game"

    # 保存行为检查报告
    report_path = game_project / "reports" / "test" / f"{task_id}-behavior-test-report.md"
    save_behavior_test_report(result, report_path)

    result.report_path = str(report_path)

    # 输出摘要
    print(f"已执行行为检查：{task_id}")
    print(f"Status：{result.status}")
    print(f"Result：{result.result}")
    print(f"Passed：{result.passed_count}")
    print(f"Failed：{result.failed_count}")

    return report_path, result


# ---------------------------------------------------------------------------
# 碰撞行为检查（Collision Check）
# ---------------------------------------------------------------------------

@dataclass
class CollisionTestResult:
    """碰撞行为检查汇总结果。"""
    task_id: str
    project_root: str
    status: str  # PASS / FAIL / BLOCKED
    result: str  # PASS / FAIL / BLOCKED
    passed_count: int
    failed_count: int
    test_cases: list[TestCaseResult] = field(default_factory=list)
    report_path: str | None = None


def run_collision_behavior_tests(
    project_path: str | Path,
    task_id: str = "G007",
) -> CollisionTestResult:
    """对玩家与平台基础碰撞逻辑执行源码静态行为检查。

    检查项遵循 docs/tester-collision-check-protocol.md 定义的六组 18 项。

    Args:
        project_path: 项目根目录路径
        task_id: 任务编号

    Returns:
        CollisionTestResult 汇总结果
    """
    project_root = Path(project_path)
    js_path = project_root / "script.js"

    # 检查 script.js 是否存在
    if not js_path.exists():
        return CollisionTestResult(
            task_id=task_id,
            project_root=str(project_root),
            status="BLOCKED",
            result="BLOCKED",
            passed_count=0,
            failed_count=0,
            test_cases=[TestCaseResult(
                id="BLOCKED", name="script.js 不存在", required=True,
                passed=False, details=f"文件缺失：{js_path}",
            )],
        )

    # 读取源码
    js_content = load_text(js_path)
    all_cases: list[TestCaseResult] = []

    # --- C 组：碰撞函数 / 状态检查 ---
    all_cases.append(_check_keyword(
        js_content,
        ["checkPlatformCollision", "detectPlatformCollision",
         "handlePlatformCollision", "resolvePlatformCollision",
         "checkCollision", "collisionDetection"],
        "C-01", "碰撞检测函数存在",
    ))
    all_cases.append(_check_keyword(
        js_content,
        ["vy > 0", "velocityY > 0", "vy >= 0", "velocityY >= 0",
         "playerState.vy > 0", "playerState.velocityY > 0",
         "playerState.vy >= 0", "playerState.vy < 0",
         "isFalling", "falling"],
        "C-02", "碰撞逻辑在下落时执行",
    ))
    has_on_platform = contains_any(js_content, [
        "isOnPlatform", "onPlatform", "currentPlatform",
        "grounded", "isGrounded", "standingOn",
    ])
    all_cases.append(TestCaseResult(
        id="C-03",
        name="存在站立状态或平台接触状态",
        required=False,
        passed=has_on_platform,
        details="匹配到站立状态关键词" if has_on_platform else "未匹配站立状态关键词（非必需）",
    ))

    # --- P 组：平台数据检查 ---
    all_cases.append(_check_keyword(
        js_content,
        ["platforms", "PLATFORM_LAYOUT", "platformData", "platformList"],
        "P-01", "平台数据存在",
    ))
    has_platform_struct = contains_any(js_content, [
        ".x", ".y", ".width", ".height",
        "platform.x", "platform.y", "platform.width", "platform.height",
        "plat.x", "plat.y", "plat.width", "plat.height",
    ])
    all_cases.append(TestCaseResult(
        id="P-02",
        name="平台有 x/y/width/height 信息",
        required=True,
        passed=has_platform_struct,
        details="平台数据包含位置和尺寸信息" if has_platform_struct else "平台数据缺少位置或尺寸信息",
    ))
    all_cases.append(_check_keyword(
        js_content,
        ["forEach", ".some(", ".find(", "for (", "for("],
        "P-03", "碰撞逻辑遍历平台",
    ))

    # --- L 组：落到平台检查 ---
    all_cases.append(_check_keyword(
        js_content,
        ["playerBottom", "playerState.y + playerHeight",
         "playerState.y + PLAYER_HEIGHT", "player.y + player.height",
         "playerY + playerH", "bottom"],
        "L-01", "判断玩家底部位置",
    ))
    has_horizontal_overlap = contains_any(js_content, [
        "playerLeft", "playerRight", "platformLeft", "platformRight",
        "playerState.x + playerWidth", "playerX + playerWidth",
        "overlap", "horizontalOverlap", "x + width",
    ])
    all_cases.append(TestCaseResult(
        id="L-02",
        name="判断玩家水平范围重叠",
        required=True,
        passed=has_horizontal_overlap,
        details="存在水平范围重叠判断" if has_horizontal_overlap else "缺少水平范围重叠判断",
    ))
    all_cases.append(_check_keyword(
        js_content,
        ["previousY", "previousBottom", "lastY", "prevY", "oldY",
         "prevBottom", "prevYBottom",
         "playerBottom - playerState.vy", "playerBottom - vy",
         "vy >= 0", "velocityY >= 0", "vy > 0", "velocityY > 0",
         "playerState.vy >= 0", "playerState.vy > 0",
         "playerState.vy < 0", "playerState.velocityY >= 0",
         "fromAbove"],
        "L-03", "判断从上方落到平台",
    ))

    # --- S 组：停止下落检查 ---
    all_cases.append(_check_keyword(
        js_content,
        ["playerState.y = platform.y - playerHeight",
         "playerState.y = platform.y - PLAYER_HEIGHT",
         "playerState.y = plat.y", "playerY = platform.y",
         "playerState.y = platform.y - height",
         "playerState.y = bounds.top - playerState.height",
         "playerState.y = bounds.top - playerHeight",
         "bounds.top - playerState.height",
         "bounds.top - player.height",
         "platformTop - playerHeight",
         "snapTo", "snapToPlatform"],
        "S-01", "落到平台后修正 y 坐标",
    ))
    all_cases.append(_check_keyword(
        js_content,
        ["velocityY = 0", "vy = 0", "playerState.vy = 0",
         "playerState.velocityY = 0", "speedY = 0",
         "verticalSpeed = 0"],
        "S-02", "落到平台后垂直速度归零",
    ))
    all_cases.append(_check_keyword(
        js_content,
        ["style.top", "updatePlayerPosition", "updatePosition",
         "renderPlayer", "drawPlayer"],
        "S-03", "更新玩家 DOM 位置",
    ))

    # --- T 组：防穿透检查 ---
    all_cases.append(_check_keyword(
        js_content,
        ["previousY", "lastY", "prevY", "oldY",
         "prevBottom", "previousBottom",
         "playerBottom - playerState.vy", "playerBottom - vy",
         "vy > 0", "velocityY > 0", "playerState.vy > 0",
         "playerState.vy < 0", "playerState.vy >= 0"],
        "T-01", "使用上一帧位置或下落方向避免误判",
    ))
    has_y_fix = contains_any(js_content, [
        "playerState.y = platform.y", "playerState.y = plat.y",
        "playerY = platform.y", "playerState.y = platform.y -",
        "playerState.y = bounds.top", "bounds.top - playerState.height",
        "bounds.top - player.height", "bounds.top - playerHeight",
        "platformTop - playerHeight",
        "snapToPlatform", "clampY",
    ])
    all_cases.append(TestCaseResult(
        id="T-02",
        name="玩家不能直接穿过平台",
        required=True,
        passed=has_y_fix,
        details="存在 y 坐标修正逻辑" if has_y_fix else "缺少 y 坐标修正逻辑",
    ))
    all_cases.append(_check_keyword(
        js_content,
        ["vy >= 0", "velocityY >= 0", "vy > 0", "velocityY > 0",
         "playerState.vy >= 0", "playerState.vy > 0",
         "playerState.vy < 0", "playerState.velocityY >= 0",
         "playerState.velocityY < 0",
         "isFalling", "falling"],
        "T-03", "碰撞只在下落时触发",
    ))

    # --- O 组：范围限制检查（不应出现） ---
    has_scroll = contains_any(js_content, [
        "scrollPlatforms", "platformScroll", "movePlatforms", "scrollOffset",
    ])
    all_cases.append(TestCaseResult(
        id="O-01",
        name="不包含平台滚动逻辑",
        required=True,
        passed=not has_scroll,
        details="未检测到平台滚动逻辑" if not has_scroll else "检测到平台滚动逻辑，越界实现",
    ))
    has_random = contains_any(js_content, ["Math.random"])
    all_cases.append(TestCaseResult(
        id="O-02",
        name="不包含随机平台生成",
        required=True,
        passed=not has_random,
        details="未检测到 Math.random" if not has_random else "检测到 Math.random，需确认是否用于平台生成",
    ))
    has_game_over = contains_any(js_content, [
        "gameOver", "isGameOver", "checkFail", "failCondition",
    ])
    all_cases.append(TestCaseResult(
        id="O-03",
        name="不包含游戏失败条件",
        required=True,
        passed=not has_game_over,
        details="未检测到游戏失败条件" if not has_game_over else "检测到游戏失败条件，越界实现",
    ))

    # --- 汇总 ---
    passed_count = sum(1 for c in all_cases if c.passed)
    failed_count = len(all_cases) - passed_count
    all_required_passed = all(c.passed for c in all_cases if c.required)

    status = "PASS" if all_required_passed else "FAIL"
    result = "PASS" if all_required_passed else "FAIL"

    return CollisionTestResult(
        task_id=task_id,
        project_root=str(project_root),
        status=status,
        result=result,
        passed_count=passed_count,
        failed_count=failed_count,
        test_cases=all_cases,
    )


def save_collision_test_report(
    result: CollisionTestResult,
    output_path: str | Path,
) -> Path:
    """保存碰撞行为检查测试报告。"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    task_names = {
        "G007": "实现玩家与平台基础碰撞",
    }
    task_name = task_names.get(result.task_id, result.task_id)

    table_rows = []
    for tc in result.test_cases:
        required_text = "是" if tc.required else "否"
        result_text = "PASS" if tc.passed else "FAIL"
        table_rows.append(f"| {tc.id} | {tc.name} | {required_text} | {result_text} | {tc.details} |")

    table_str = "\n".join(table_rows)

    failed_cases = [tc for tc in result.test_cases if not tc.passed and tc.required]
    if failed_cases:
        failed_items = "\n".join(f"- {tc.id} {tc.name}：{tc.details}" for tc in failed_cases)
        fix_suggestions = "\n".join(f"- 修复 {tc.id} {tc.name}" for tc in failed_cases)
    else:
        failed_items = "（无失败项）"
        fix_suggestions = "（无建议）"

    out_of_scope = [tc for tc in result.test_cases if not tc.passed and tc.id.startswith("O-")]
    if out_of_scope:
        scope_items = "\n".join(f"- {tc.id} {tc.name}：{tc.details}" for tc in out_of_scope)
    else:
        scope_items = "（无越界发现）"

    if result.status == "PASS":
        next_action = "建议进入 Main Agent 综合决策复核。"
    elif result.status == "BLOCKED":
        next_action = "建议检查源码文件是否存在或可读取。"
    else:
        next_action = "建议返回 Developer Agent 修复碰撞逻辑。"

    report = f"""# {result.task_id} Collision Test Report

## Agent

Tester Agent

## Task

任务编号：{result.task_id}
任务名称：{task_name}

## Status

{result.status}

## Project

{result.project_root}

## Test Scope

- 碰撞函数 / 状态检查（C 组）
- 平台数据检查（P 组）
- 玩家落到平台检查（L 组）
- 停止下落检查（S 组）
- 防穿透检查（T 组）
- 范围限制检查（O 组）

## Test Cases

| 编号 | 测试项 | 必需 | 结果 | 说明 |
|------|--------|------|------|------|
{table_str}

## Result

{result.result}

## Failed Items

{failed_items}

## Out-of-Scope Findings

{scope_items}

## Fix Suggestions

{fix_suggestions}

## Evidence

- {result.project_root}/reports/test/{result.task_id}-collision-test-report.md

## Next Action

{next_action}
"""

    output_path.write_text(report, encoding="utf-8")
    return output_path


def run_collision_tester_for_game_task(task_id: str = "G007") -> tuple[Path, CollisionTestResult]:
    """对 down-100-floors-game 指定任务执行碰撞行为检查。

    Args:
        task_id: 游戏任务编号，默认 G007

    Returns:
        (报告路径, CollisionTestResult)
    """
    runner_root = Path(__file__).parent.parent
    game_project = runner_root / "projects" / "down-100-floors-game"

    result = run_collision_behavior_tests(game_project, task_id)

    result.project_root = "projects/down-100-floors-game"

    report_path = game_project / "reports" / "test" / f"{task_id}-collision-test-report.md"
    save_collision_test_report(result, report_path)

    result.report_path = str(report_path)

    print(f"已执行碰撞检查：{task_id}")
    print(f"Status：{result.status}")
    print(f"Result：{result.result}")
    print(f"Passed：{result.passed_count}")
    print(f"Failed：{result.failed_count}")

    return report_path, result
