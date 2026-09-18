"""Excel 导出模块：生成固定文件名「学习计划.xlsx」。"""

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# 样式常量
TITLE_FONT = Font(name="微软雅黑", size=16, bold=True, color="FFFFFF")
SECTION_FONT = Font(name="微软雅黑", size=12, bold=True, color="FFFFFF")
HEADER_FONT = Font(name="微软雅黑", size=10, bold=True, color="333333")
BODY_FONT = Font(name="微软雅黑", size=10, color="333333")

TITLE_FILL = PatternFill("solid", fgColor="2F5496")
SECTION_FILL = PatternFill("solid", fgColor="4472C4")
HEADER_FILL = PatternFill("solid", fgColor="D9E2F3")

THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

WRAP = Alignment(horizontal="left", vertical="top", wrap_text=True)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)

# 整表列宽（A~F）
COL_WIDTHS = [14, 26, 32, 32, 18, 30]
TOTAL_WIDTH = sum(COL_WIDTHS)


def _disp_width(text):
    """估算显示宽度：CJK 按 2 个字符宽计。"""
    return sum(2 if ord(ch) > 127 else 1 for ch in str(text or ""))


def _row_height(texts, widths):
    """按内容长度估算行高，保证换行后能完整显示。"""
    max_lines = 1
    for t, w in zip(texts, widths):
        per_line = max(w - 2, 4)
        lines = max(1, -(-_disp_width(t) // per_line))
        max_lines = max(max_lines, lines)
    return max(16, 16 * max_lines + 6)


def _section_title(ws, row, text):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    c = ws.cell(row=row, column=1, value=text)
    c.font = SECTION_FONT
    c.fill = SECTION_FILL
    c.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[row].height = 24
    return row + 1


def _kv_row(ws, row, key, value):
    ck = ws.cell(row=row, column=1, value=key)
    ck.font = HEADER_FONT
    ck.fill = HEADER_FILL
    ck.alignment = CENTER
    ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=6)
    cv = ws.cell(row=row, column=2, value=value or "")
    cv.font = BODY_FONT
    cv.alignment = WRAP
    for col in range(1, 7):
        ws.cell(row=row, column=col).border = BORDER
    ws.row_dimensions[row].height = _row_height(
        [key, value], [COL_WIDTHS[0], TOTAL_WIDTH - COL_WIDTHS[0]]
    )
    return row + 1


def _paragraph(ws, row, text):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    c = ws.cell(row=row, column=1, value=text or "")
    c.font = BODY_FONT
    c.alignment = WRAP
    for col in range(1, 7):
        ws.cell(row=row, column=col).border = BORDER
    ws.row_dimensions[row].height = _row_height([text], [TOTAL_WIDTH])
    return row + 1


def _table_header(ws, row, headers):
    for col, h in enumerate(headers, start=1):
        c = ws.cell(row=row, column=col, value=h)
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = CENTER
        c.border = BORDER
    ws.row_dimensions[row].height = 24
    return row + 1


def _table_row(ws, row, values, widths):
    for col, v in enumerate(values, start=1):
        c = ws.cell(row=row, column=col, value=v if v is not None else "")
        c.font = BODY_FONT
        c.alignment = WRAP if col > 1 else CENTER
        c.border = BORDER
    ws.row_dimensions[row].height = _row_height(values, widths)
    return row + 1


def _list_row(ws, row, index, text):
    content = f"{index}. {text}"
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    c = ws.cell(row=row, column=1, value=content)
    c.font = BODY_FONT
    c.alignment = WRAP
    for col in range(1, 7):
        ws.cell(row=row, column=col).border = BORDER
    ws.row_dimensions[row].height = _row_height([content], [TOTAL_WIDTH])
    return row + 1


def _set_widths(ws):
    for i, w in enumerate(COL_WIDTHS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def write_plan(form: dict, plan: dict, path: str) -> None:
    """把用户信息 + 计划写入 Excel 文件。"""
    wb = Workbook()
    ws = wb.active
    ws.title = "学习计划"
    _set_widths(ws)

    row = 1
    # 标题
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    c = ws.cell(row=row, column=1, value="AI 全栈开发学习计划")
    c.font = TITLE_FONT
    c.fill = TITLE_FILL
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[row].height = 34
    row += 2

    # 一、用户基础信息
    row = _section_title(ws, row, "一、用户基础信息")
    info = [
        ("姓名", form.get("name", "")),
        ("性别", form.get("gender", "")),
        ("年龄", form.get("age", "")),
        ("学历", form.get("education", "")),
        ("知识基础", form.get("knowledge", "")),
        ("学习习惯", form.get("habit", "")),
    ]
    for k, v in info:
        row = _kv_row(ws, row, k, v)
    row += 1

    # 二、适配说明
    row = _section_title(ws, row, "二、适配说明")
    row = _paragraph(ws, row, plan.get("适配说明", ""))
    row += 1

    # 三、分阶段学习计划
    row = _section_title(ws, row, "三、分阶段学习计划")
    stage_headers = ["阶段", "目标", "学习时长", "学习内容", "实操项目", "验收标准"]
    row = _table_header(ws, row, stage_headers)
    for s in plan.get("分阶段学习计划", []):
        values = [
            s.get("阶段", ""),
            s.get("目标", ""),
            s.get("学习时长", ""),
            s.get("学习内容", ""),
            s.get("实操项目", ""),
            s.get("验收标准", ""),
        ]
        row = _table_row(ws, row, values, COL_WIDTHS)
    row += 1

    # 四、全课程学习细则
    row = _section_title(ws, row, "四、全课程学习细则")
    course_headers = ["序号", "课程", "学习要点", "实操内容", "建议时长"]
    course_widths = [6, 26, 40, 40, 12]
    row = _table_header(ws, row, course_headers)
    for i, c_item in enumerate(plan.get("全课程学习细则", []), start=1):
        values = [
            i,
            c_item.get("课程", ""),
            c_item.get("学习要点", ""),
            c_item.get("实操内容", ""),
            c_item.get("建议时长", ""),
        ]
        row = _table_row(ws, row, values, course_widths)
    row += 1

    # 五~八、列表类内容
    for title, key in [
        ("五、每日任务", "每日任务"),
        ("六、阶段目标", "阶段目标"),
        ("七、就业备考方案", "就业备考方案"),
        ("八、个性化学习建议", "个性化学习建议"),
    ]:
        row = _section_title(ws, row, title)
        items = plan.get(key, [])
        if items:
            for i, item in enumerate(items, start=1):
                row = _list_row(ws, row, i, item)
        else:
            row = _paragraph(ws, row, "（暂无）")
        row += 1

    wb.save(path)
