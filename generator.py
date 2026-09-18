"""AI 生成模块：拼接 Prompt、调用 Claude、解析结果、演示兜底。"""

import json
import os
import re

from anthropic import Anthropic

from config import CURRICULUM, MODEL

# 大模型的系统提示：约束输出结构、保证课程全覆盖
SYSTEM_PROMPT = """你是一名资深全栈开发 / AI 工程导师，负责为用户生成个性化、可落地、可执行的 AI 全栈开发学习计划。

输出要求（必须严格遵守）：
1. 只输出一个合法 JSON 对象，不要输出 markdown 代码块，不要输出 JSON 之外的任何文字。
2. JSON 字段名必须与下列完全一致：
   - "适配说明"：字符串。说明如何结合用户年龄、学历、知识基础、学习习惯定制专属节奏。
   - "分阶段学习计划"：数组，固定 4 个对象，顺序为「入门阶段」「进阶阶段」「实战阶段」「就业冲刺阶段」。每个对象字段："阶段"、"目标"、"学习时长"、"学习内容"、"实操项目"、"验收标准"。
   - "全课程学习细则"：数组，恰好 8 个对象，顺序与给定课程顺序一致。每个对象字段："课程"、"学习要点"、"实操内容"、"建议时长"。
   - "每日任务"：字符串数组，给出具体可执行的每日/每周任务。
   - "阶段目标"：字符串数组。
   - "就业备考方案"：字符串数组，结合「面试指导与就业加强」课程，包含阶段性面试复盘、简历项目梳理、求职准备。
   - "个性化学习建议"：字符串数组，结合用户学习习惯（如晚间精神好则侧重晚间实操、白天理论记忆）。
3. 必须覆盖全部 8 门课程，一门都不能遗漏。
4. 0基础用户侧重入门铺垫；有基础用户侧重进阶实战与项目落地。
5. 内容要具体可落地，给出量化指标（天数、小时、项目名、验收标准），不要空话套话。"""


def build_prompt(form: dict) -> str:
    """将用户表单信息 + 固定课程拼接为完整 Prompt。"""
    curriculum_lines = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(CURRICULUM))
    return (
        "【用户信息】\n"
        f"姓名：{form.get('name', '')}\n"
        f"性别：{form.get('gender', '')}\n"
        f"年龄：{form.get('age', '')}\n"
        f"学历：{form.get('education', '')}\n"
        f"知识基础：{form.get('knowledge', '')}\n"
        f"学习习惯：{form.get('habit', '')}\n"
        "\n【固定课程体系（必须全覆盖，不得遗漏任何一门）】\n"
        f"{curriculum_lines}\n"
        "\n请根据以上信息生成完整学习计划，并严格按 JSON 输出。"
    )


def generate_plan(form: dict):
    """真实调用 Claude 生成计划；无 Key 或调用失败时回退到演示方案。

    返回 (plan_dict, source)，source 为 "claude" 或 "demo"。
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        try:
            text = _call_claude_real(build_prompt(form))
            plan = parse_plan_json(text)
            if plan:
                return merge_courses(plan, form), "claude"
        except Exception:
            # 调用失败或解析失败，走演示兜底，保证闭环可用
            pass
    return merge_courses(demo_plan(form), form), "demo"


def _call_claude_real(prompt: str) -> str:
    """通过 anthropic SDK 流式调用 Claude，返回文本内容。"""
    client = Anthropic()
    with client.messages.stream(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        message = stream.get_final_message()

    if getattr(message, "stop_reason", None) == "refusal":
        raise RuntimeError("model refused the request")

    parts = [block.text for block in message.content if getattr(block, "type", None) == "text"]
    return "".join(parts)


def parse_plan_json(text: str):
    """将模型返回文本解析为 dict；解析失败返回 None。"""
    if not text:
        return None
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None


def merge_courses(plan: dict, form: dict) -> dict:
    """确保「全课程学习细则」覆盖全部 8 门固定课程，缺失的自动补齐。"""
    plan = plan or {}
    detail = plan.get("全课程学习细则") or []
    by_name = {}
    for item in detail:
        if isinstance(item, dict):
            by_name[(item.get("课程") or "").strip()] = item

    merged = []
    for name in CURRICULUM:
        if name in by_name:
            item = dict(by_name[name])
        else:
            item = {
                "课程": name,
                "学习要点": "掌握本课程核心概念、关键技术与典型应用场景，完成对应实操练习。",
                "实操内容": "完成课程配套实战项目并输出可演示成果。",
                "建议时长": "2 周",
            }
        item["课程"] = name
        merged.append(item)

    plan["全课程学习细则"] = merged
    return plan


def demo_plan(form: dict) -> dict:
    """演示兜底方案：无 Key 或调用失败时，用固定逻辑生成一份可用的计划。"""
    knowledge = (form.get("knowledge") or "").strip()
    habit = (form.get("habit") or "").strip()

    is_zero = (
        not knowledge
        or "0基础" in knowledge
        or "零基础" in knowledge
        or "无基础" in knowledge
    )
    evening = ("晚" in habit and ("精神" in habit or "清醒" in habit or "好" in habit))

    base_desc = (
        "你目前为 0 基础，计划先从计算机与编程入门开始铺垫，前两门课程放慢节奏、夯实地基，再逐步进入 AI 全栈开发实战。"
        if is_zero
        else f"你已具备「{knowledge}」基础，计划跳过纯入门铺垫，直接侧重进阶实战与项目落地，用真实项目驱动学习。"
    )
    habit_desc = (
        "根据你的学习习惯，晚间状态更佳，因此把高强度的实操编码安排在晚间，白天用于理论记忆、看课与复盘。"
        if evening
        else "根据你的作息，白天安排理论学习，实操与复习固定在你精力最集中的时段，保持节奏稳定。"
    )

    stages = [
        {
            "阶段": "入门阶段",
            "目标": "打牢计算机与编程基础，跑通第一个 AI 应用小项目，建立学习正反馈。",
            "学习时长": "4 周",
            "学习内容": "计算机基础、Python 基础语法、Git 与命令行、AI 应用全栈开发基础（前端入门 + 接口调用）。",
            "实操项目": "用 Python 写一个命令行小工具；调用大模型 API 做一个「AI 问答小助手」网页。",
            "验收标准": "独立完成命令行工具与 AI 问答助手，能讲清楚代码流程。",
        },
        {
            "阶段": "进阶阶段",
            "目标": "掌握全栈开发与 RAG 智能体，能独立搭建带知识库的 AI 应用。",
            "学习时长": "6 周",
            "学习内容": "vibecoding 项目开发、AI 应用全栈开发基础（前后端打通）、RAG 智能体开发（向量检索 + 提示工程）。",
            "实操项目": "做一个「个人知识库问答机器人」，接入向量数据库并优化检索效果。",
            "验收标准": "知识库机器人可稳定回答指定文档内容，检索准确率达到自测标准。",
        },
        {
            "阶段": "实战阶段",
            "目标": "补齐企业工程化与 Java 微服务能力，完成可上简历的完整项目。",
            "学习时长": "8 周",
            "学习内容": "企业工程化能力（Java）、AI 工程化 - 微服务智能体实战、传统项目的智能化升级、AI 应用评估与模型调优。",
            "实操项目": "将已有项目智能化升级：接入 AI 能力、拆分微服务、做模型评估与调优，沉淀成完整 GitHub 项目。",
            "验收标准": "项目可部署运行，具备完整 README、测试与调优记录，能应对面试追问。",
        },
        {
            "阶段": "就业冲刺阶段",
            "目标": "打磨简历与面试，持续复盘，拿到 AI 开发方向 Offer。",
            "学习时长": "4 周",
            "学习内容": "面试指导与就业加强：简历项目梳理、八股与算法、模拟面试、阶段复盘。",
            "实操项目": "整理 2~3 个可深挖的项目 STAR 案例，完成 3 轮模拟面试并复盘。",
            "验收标准": "简历投递转化达标，能流畅讲清项目难点与解决方案。",
        },
    ]

    courses = [
        {"课程": CURRICULUM[0], "学习要点": "用 AI 辅助快速搭建应用，掌握提示驱动的开发流程。", "实操内容": "完成 2~3 个 vibecoding 小项目。", "建议时长": "2 周"},
        {"课程": CURRICULUM[1], "学习要点": "掌握前端 + 后端 + 大模型 API 的全栈闭环。", "实操内容": "搭建全栈 AI 应用并上线。", "建议时长": "3 周"},
        {"课程": CURRICULUM[2], "学习要点": "向量检索、提示工程、Agent 编排。", "实操内容": "构建 RAG 知识库问答系统。", "建议时长": "3 周"},
        {"课程": CURRICULUM[3], "学习要点": "Java 工程化、Spring、代码规范与测试。", "实操内容": "用 Java 重写/搭建一个后端服务。", "建议时长": "4 周"},
        {"课程": CURRICULUM[4], "学习要点": "微服务架构、智能体服务化、网关与治理。", "实操内容": "将智能体拆分为微服务并部署。", "建议时长": "4 周"},
        {"课程": CURRICULUM[5], "学习要点": "如何为存量传统系统接入 AI 能力。", "实操内容": "选一个传统项目做智能化升级改造。", "建议时长": "3 周"},
        {"课程": CURRICULUM[6], "学习要点": "模型评测、prompt 调优、成本与效果平衡。", "实操内容": "建立评估集并持续调优一个应用。", "建议时长": "2 周"},
        {"课程": CURRICULUM[7], "学习要点": "面试八股、项目复盘、简历与求职策略。", "实操内容": "模拟面试、简历打磨、岗位投递。", "建议时长": "贯穿全程"},
    ]

    daily = [
        ("每天固定 2~3 小时：白天 1 小时理论/看课 + 晚间 1~2 小时实操编码"
         if evening else "每天固定 2~3 小时：上午理论看课 + 下午/晚上实操编码"),
        "每天完成 1 个代码练习，并在本地 git 提交记录",
        "每周末用 2 小时复盘本周内容，整理成笔记或博客",
        "每周推进当前阶段的项目至少 3 次，保持项目主线不断",
    ]

    stage_goals = [
        "入门阶段结束：能独立调用大模型 API 完成一个小应用",
        "进阶阶段结束：能独立搭建 RAG 知识库问答系统",
        "实战阶段结束：拥有 1~2 个可上简历的完整项目",
        "就业冲刺阶段结束：简历、面试、项目案例全部就绪",
    ]

    employment = [
        "简历项目梳理：用 STAR 法则包装每个项目的背景、难点、方案、结果",
        "阶段性面试复盘：每两周一次模拟面试，记录薄弱点并针对性补强",
        "求职准备：整理目标岗位 JD，拆解技能点，查漏补缺",
        "面试指导：准备 AI 全栈常见面试题（RAG、微服务、模型调优等）",
    ]

    advice = [
        habit_desc,
        ("0基础阶段不要跳步，先把基础语法和第一个小项目跑通，建立信心"
         if is_zero else "有基础可直接以项目驱动，遇到不懂的再回头补理论，效率更高"),
        "把每个阶段的产出沉淀为 GitHub 仓库，形成可展示的学习轨迹",
        "遇到卡点当天解决，不要积压；坚持每天固定投入比周末突击更有效",
    ]

    return {
        "适配说明": base_desc + habit_desc,
        "分阶段学习计划": stages,
        "全课程学习细则": courses,
        "每日任务": daily,
        "阶段目标": stage_goals,
        "就业备考方案": employment,
        "个性化学习建议": advice,
    }
