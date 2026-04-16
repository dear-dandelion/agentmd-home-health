from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any

import gradio as gr

from app.api.service import AppService


APP_CSS = """
body {
  background: #fffbf5;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
.gradio-container {
  max-width: 1560px !important;
}
.glass-shell {
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(14px);
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 28px;
  box-shadow: 0 28px 80px rgba(15, 23, 42, 0.08);
}
.panel-card {
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 24px;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.06);
}
.detail-card {
  border: 1px solid #edf2f7;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.96);
  padding: 16px;
  margin-bottom: 12px;
}
.soft-label {
  color: #94a3b8;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 700;
}
.timeline-time {
  color: #94a3b8;
  font-size: 12px;
  margin-bottom: 6px;
}
.risk-pill {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}
.risk-low {
  background: #dcfce7;
  color: #15803d;
}
.risk-medium {
  background: #fef3c7;
  color: #b45309;
}
.risk-high {
  background: #fee2e2;
  color: #b91c1c;
}
.quick-chip button {
  border-radius: 999px !important;
  border: 1px solid #e2e8f0 !important;
  background: white !important;
}
"""

PROFILE_LABELS = {
    "smoking_history": "吸烟史",
    "height_cm": "身高",
    "weight_kg": "体重",
    "systolic_bp": "收缩压",
    "diastolic_bp": "舒张压",
    "fasting_glucose": "空腹血糖",
}

PARAM_UNITS = {
    "height_cm": "cm",
    "weight_kg": "kg",
    "systolic_bp": "mmHg",
    "diastolic_bp": "mmHg",
    "fasting_glucose": "mmol/L",
}

QUICK_PROMPTS = {
    "今日血压分析": "帮我分析今日血压，我的血压是 138/86。",
    "BMI 评估": "帮我评估 BMI，我的身高 170cm，体重 65kg。",
    "空腹血糖分析": "帮我分析空腹血糖，我的空腹血糖是 6.1 mmol/L。",
    "饮食建议": "请根据我当前的健康情况给我一份今日饮食建议。",
}


def build_app() -> gr.Blocks:
    service = AppService()

    def refresh_user_choices(selected_user_id: int | None = None) -> gr.Dropdown:
        users = service.user_manager.list_all()
        choices = [f"{user['user_id']} - {user['name']}" for user in users]
        value = choices[0] if choices else None
        if selected_user_id is not None:
            for choice in choices:
                if choice.startswith(f"{selected_user_id} - "):
                    value = choice
                    break
        return gr.update(choices=choices, value=value)

    def validate_create_form(name: str, birth_date: str, gender: str, height_cm: float | None, weight_kg: float | None) -> str:
        return _validate_profile_form(name, birth_date, gender, height_cm, weight_kg, None, None, None, require_basic=False)

    def validate_edit_form(
        name: str,
        birth_date: str,
        gender: str,
        height_cm: float | None,
        weight_kg: float | None,
        systolic_bp: float | None,
        diastolic_bp: float | None,
        fasting_glucose: float | None,
    ) -> str:
        return _validate_profile_form(name, birth_date, gender, height_cm, weight_kg, systolic_bp, diastolic_bp, fasting_glucose, require_basic=False)

    def load_user_context(user_label: str | None, detail_view: str) -> tuple[str, str, str, list[dict[str, str]], dict[str, Any], dict[str, Any] | None, str, str]:
        user_id = _parse_user_id(user_label)
        if user_id is None:
            empty = "<div class='detail-card'>请先创建或选择用户档案。</div>"
            return "当前管理档案：未选择", empty, empty, [], {}, None, "", ""
        profile = service.user_manager.get(user_id)
        return (
            f"当前管理档案：**{profile['name']}**",
            _render_profile_summary(profile),
            _render_detail_panel(service, user_id, detail_view),
            [],
            {},
            None,
            "",
            "",
        )

    def create_user(
        name: str,
        birth_date: str,
        gender: str,
        smoking_history: str,
        height_cm: float | None,
        weight_kg: float | None,
        validation_message: str,
    ) -> tuple[str, gr.Dropdown, str, str, str, None, None]:
        validation_message = validation_message or validate_create_form(name, birth_date, gender, height_cm, weight_kg)
        if validation_message and validation_message != "输入范围校验通过。":
            return validation_message, refresh_user_choices(), name, birth_date, gender, height_cm, weight_kg
        if not name.strip() or not birth_date.strip() or not gender.strip():
            return "姓名、出生日期、性别为必填项。", refresh_user_choices(), name, birth_date, gender, height_cm, weight_kg

        profile = service.user_manager.create(name=name.strip(), birth_date=birth_date.strip(), gender=gender.strip())
        params = _collect_optional_profile_params(smoking_history, height_cm, weight_kg, None, None, None)
        if params:
            service.data_access.upsert_params(profile["user_id"], params, source="create_form")
        return f"已创建档案：{profile['name']}。", refresh_user_choices(profile["user_id"]), "", "", "", None, None

    def open_edit_profile(user_label: str | None) -> tuple[gr.Group, str, str, str, str, float | None, float | None, float | None, float | None, float | None, str]:
        user_id = _parse_user_id(user_label)
        if user_id is None:
            return gr.update(visible=False), "", "", "", "", None, None, None, None, None, "请先选择用户档案。"
        profile = service.user_manager.get(user_id)
        params = profile.get("params", {})
        return (
            gr.update(visible=True),
            profile.get("name", ""),
            profile.get("birth_date", ""),
            profile.get("gender", ""),
            str(params.get("smoking_history", "")),
            _to_float_or_none(params.get("height_cm")),
            _to_float_or_none(params.get("weight_kg")),
            _to_float_or_none(params.get("systolic_bp")),
            _to_float_or_none(params.get("diastolic_bp")),
            _to_float_or_none(params.get("fasting_glucose")),
            "已载入当前档案信息。",
        )

    def cancel_edit_profile() -> tuple[gr.Group, str, str]:
        return gr.update(visible=False), "", ""

    def save_edit_profile(
        user_label: str | None,
        name: str,
        birth_date: str,
        gender: str,
        smoking_history: str,
        height_cm: float | None,
        weight_kg: float | None,
        systolic_bp: float | None,
        diastolic_bp: float | None,
        fasting_glucose: float | None,
        validation_message: str,
    ) -> tuple[str, gr.Dropdown, gr.Group, str]:
        user_id = _parse_user_id(user_label)
        if user_id is None:
            return "请先选择用户档案。", refresh_user_choices(), gr.update(visible=False), ""
        validation_message = validation_message or validate_edit_form(name, birth_date, gender, height_cm, weight_kg, systolic_bp, diastolic_bp, fasting_glucose)
        if validation_message and validation_message != "输入范围校验通过。":
            return validation_message, refresh_user_choices(user_id), gr.update(visible=True), validation_message

        service.user_manager.update(user_id, name=name.strip(), birth_date=birth_date.strip(), gender=gender.strip())
        params = _collect_optional_profile_params(smoking_history, height_cm, weight_kg, systolic_bp, diastolic_bp, fasting_glucose)
        if params:
            service.data_access.upsert_params(user_id, params, source="edit_profile")
        return "档案已更新。若修改了评估关键参数，建议重新评估。", refresh_user_choices(user_id), gr.update(visible=False), ""

    def show_history_panel(user_label: str | None) -> tuple[str, str]:
        return _render_detail_panel(service, _parse_user_id(user_label), "history"), "history"

    def show_detail_panel(user_label: str | None) -> tuple[str, str]:
        return _render_detail_panel(service, _parse_user_id(user_label), "details"), "details"

    def send_message(
        user_label: str | None,
        message: str,
        chat_history: list[dict[str, str]] | None,
        dialog_state: dict[str, Any] | None,
    ) -> tuple[list[dict[str, str]], dict[str, Any], str, dict[str, Any] | None, str, str, str]:
        history = list(chat_history or [])
        if not message.strip():
            return history, dialog_state or {}, "", None, "", "请输入消息内容。", gr.update()
        user_id = _parse_user_id(user_label)
        if user_id is None:
            history.append({"role": "assistant", "content": "请先创建或选择一个用户档案。"})
            return history, dialog_state or {}, "", None, "", "尚未选择用户档案。", _render_empty_profile()

        result = service.message_processor.process(user_id=user_id, text=message, dialog_state=dialog_state)
        assistant_content = result.reply_text
        if result.card_html:
            assistant_content += "\n\n" + result.card_html
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": assistant_content})
        next_state = {
            "state": result.state.state,
            "pending_tool": result.state.pending_tool,
            "pending_intent": result.state.pending_intent,
            "required_params": result.state.required_params,
            "collected_params": result.state.collected_params,
            "last_active_at": result.state.last_active_at.isoformat() if result.state.last_active_at else None,
        }
        latest_result = None
        if result.result:
            latest_result = {
                "tool_name": result.result.get("details", {}).get("tool_name"),
                "input_params": result.result.get("details", {}).get("input_params", {}),
                "result": result.result,
                "saved": False,
            }
        return history, next_state, "", latest_result, "", "", _render_profile_summary(service.user_manager.get(user_id))

    def save_latest_result(user_label: str | None, latest_result: dict[str, Any] | None, detail_view: str) -> tuple[str, dict[str, Any] | None, str]:
        user_id = _parse_user_id(user_label)
        if user_id is None:
            return "请先选择用户档案。", latest_result, "<div class='detail-card'>请先创建或选择用户档案。</div>"
        if not latest_result:
            return "当前没有可保存的评估结果。", latest_result, _render_detail_panel(service, user_id, detail_view)
        if latest_result.get("saved"):
            return "本次评估结果已保存到档案。", latest_result, _render_detail_panel(service, user_id, detail_view)
        service.data_access.create_assessment(
            user_id=user_id,
            calculator_name=str(latest_result.get("tool_name", "")),
            input_params=dict(latest_result.get("input_params", {})),
            result=dict(latest_result.get("result", {})),
        )
        latest_result["saved"] = True
        return "本次评估结果已保存到历史记录。", latest_result, _render_detail_panel(service, user_id, detail_view)

    def share_latest_result(latest_result: dict[str, Any] | None) -> tuple[str, str]:
        if not latest_result:
            return "", "当前没有可分享的评估结果。"
        result = latest_result.get("result", {})
        details = result.get("details", {})
        params = latest_result.get("input_params", {})
        params_text = "，".join(f"{PROFILE_LABELS.get(key, key)}={value}{PARAM_UNITS.get(key, '')}" for key, value in params.items())
        share_text = (
            f"评估类型：{details.get('display_name', details.get('tool_name', '未知评估'))}\n"
            f"结果摘要：{result.get('summary', '-')}\n"
            f"风险等级：{result.get('risk_level', '-')}\n"
            f"建议：{result.get('interpretation', result.get('advice', '-'))}\n"
            f"输入参数：{params_text or '无'}"
        )
        return share_text, "已生成可分享摘要。"

    with gr.Blocks(title="悦康守护 - 居家健康智能对话系统", theme=gr.themes.Soft(), css=APP_CSS) as demo:
        dialog_state = gr.State({})
        latest_result_state = gr.State(None)
        detail_view_state = gr.State("history")

        with gr.Row(elem_classes=["glass-shell"]):
            with gr.Column(scale=1, min_width=360, elem_classes=["panel-card"]):
                gr.Markdown("### 悦康守护")
                current_user = gr.Markdown("当前管理档案：未选择")
                user_selector = gr.Dropdown(label="切换档案", choices=[])
                with gr.Row():
                    refresh_btn = gr.Button("刷新列表")
                    edit_btn = gr.Button("编辑档案")

                with gr.Accordion("新建档案", open=False):
                    create_name = gr.Textbox(label="姓名")
                    create_birth = gr.Textbox(label="出生日期", placeholder="YYYY-MM-DD")
                    create_gender = gr.Dropdown(label="性别", choices=["男", "女"])
                    create_smoking = gr.Dropdown(label="吸烟史", choices=["", "从不吸烟", "当前吸烟", "已戒烟"], value="")
                    with gr.Row():
                        create_height = gr.Number(label="身高（cm）", precision=1)
                        create_weight = gr.Number(label="体重（kg）", precision=1)
                    create_validation = gr.Markdown()
                    create_btn = gr.Button("创建档案", variant="primary")
                    create_status = gr.Markdown()

                profile_summary = gr.HTML(_render_empty_profile())
                with gr.Row():
                    history_btn = gr.Button("历史评估")
                    detail_btn = gr.Button("档案详情")
                detail_panel = gr.HTML("<div class='detail-card'>请选择用户后查看详情。</div>")

                with gr.Group(visible=False) as edit_panel:
                    gr.Markdown("#### 编辑档案")
                    edit_name = gr.Textbox(label="姓名")
                    edit_birth = gr.Textbox(label="出生日期", placeholder="YYYY-MM-DD")
                    edit_gender = gr.Dropdown(label="性别", choices=["男", "女"])
                    edit_smoking = gr.Dropdown(label="吸烟史", choices=["", "从不吸烟", "当前吸烟", "已戒烟"], value="")
                    with gr.Row():
                        edit_height = gr.Number(label="身高（cm）", precision=1)
                        edit_weight = gr.Number(label="体重（kg）", precision=1)
                    with gr.Row():
                        edit_sys = gr.Number(label="收缩压（mmHg）", precision=0)
                        edit_dia = gr.Number(label="舒张压（mmHg）", precision=0)
                    edit_glucose = gr.Number(label="空腹血糖（mmol/L）", precision=1)
                    edit_validation = gr.Markdown()
                    edit_status = gr.Markdown()
                    with gr.Row():
                        save_edit_btn = gr.Button("保存修改", variant="primary")
                        cancel_edit_btn = gr.Button("取消")

            with gr.Column(scale=2, min_width=620, elem_classes=["panel-card"]):
                gr.Markdown("### 智能健康助手")
                chatbot = gr.Chatbot(label="对话历史", type="messages", height=560, show_copy_button=True)
                with gr.Row():
                    quick_bp = gr.Button("今日血压分析", elem_classes=["quick-chip"])
                    quick_bmi = gr.Button("BMI 评估", elem_classes=["quick-chip"])
                    quick_glucose = gr.Button("空腹血糖分析", elem_classes=["quick-chip"])
                    quick_diet = gr.Button("饮食建议", elem_classes=["quick-chip"])
                message = gr.Textbox(label="输入消息", lines=3, placeholder="例如：帮我分析今日血压，或帮我评估 BMI。")
                send_btn = gr.Button("发送", variant="primary")
                action_status = gr.Markdown()
                with gr.Row():
                    save_result_btn = gr.Button("保存到档案")
                    share_result_btn = gr.Button("分享结果")
                share_box = gr.Textbox(label="分享摘要", lines=5, interactive=False)

        for component in [create_name, create_birth, create_gender, create_height, create_weight]:
            component.change(validate_create_form, inputs=[create_name, create_birth, create_gender, create_height, create_weight], outputs=create_validation)

        create_btn.click(
            create_user,
            inputs=[create_name, create_birth, create_gender, create_smoking, create_height, create_weight, create_validation],
            outputs=[create_status, user_selector, create_name, create_birth, create_gender, create_height, create_weight],
        ).then(
            load_user_context,
            inputs=[user_selector, detail_view_state],
            outputs=[current_user, profile_summary, detail_panel, chatbot, dialog_state, latest_result_state, share_box, action_status],
        )

        refresh_btn.click(refresh_user_choices, outputs=user_selector).then(
            load_user_context,
            inputs=[user_selector, detail_view_state],
            outputs=[current_user, profile_summary, detail_panel, chatbot, dialog_state, latest_result_state, share_box, action_status],
        )
        user_selector.change(
            load_user_context,
            inputs=[user_selector, detail_view_state],
            outputs=[current_user, profile_summary, detail_panel, chatbot, dialog_state, latest_result_state, share_box, action_status],
        )

        edit_btn.click(
            open_edit_profile,
            inputs=user_selector,
            outputs=[edit_panel, edit_name, edit_birth, edit_gender, edit_smoking, edit_height, edit_weight, edit_sys, edit_dia, edit_glucose, edit_status],
        )
        cancel_edit_btn.click(cancel_edit_profile, outputs=[edit_panel, edit_status, edit_validation])

        for component in [edit_name, edit_birth, edit_gender, edit_height, edit_weight, edit_sys, edit_dia, edit_glucose]:
            component.change(
                validate_edit_form,
                inputs=[edit_name, edit_birth, edit_gender, edit_height, edit_weight, edit_sys, edit_dia, edit_glucose],
                outputs=edit_validation,
            )

        save_edit_btn.click(
            save_edit_profile,
            inputs=[user_selector, edit_name, edit_birth, edit_gender, edit_smoking, edit_height, edit_weight, edit_sys, edit_dia, edit_glucose, edit_validation],
            outputs=[edit_status, user_selector, edit_panel, edit_validation],
        ).then(
            load_user_context,
            inputs=[user_selector, detail_view_state],
            outputs=[current_user, profile_summary, detail_panel, chatbot, dialog_state, latest_result_state, share_box, action_status],
        )

        history_btn.click(show_history_panel, inputs=user_selector, outputs=[detail_panel, detail_view_state])
        detail_btn.click(show_detail_panel, inputs=user_selector, outputs=[detail_panel, detail_view_state])

        send_btn.click(
            send_message,
            inputs=[user_selector, message, chatbot, dialog_state],
            outputs=[chatbot, dialog_state, message, latest_result_state, share_box, action_status, profile_summary],
        )
        message.submit(
            send_message,
            inputs=[user_selector, message, chatbot, dialog_state],
            outputs=[chatbot, dialog_state, message, latest_result_state, share_box, action_status, profile_summary],
        )

        save_result_btn.click(
            save_latest_result,
            inputs=[user_selector, latest_result_state, detail_view_state],
            outputs=[action_status, latest_result_state, detail_panel],
        )
        share_result_btn.click(share_latest_result, inputs=latest_result_state, outputs=[share_box, action_status])

        quick_bp.click(lambda: QUICK_PROMPTS["今日血压分析"], outputs=message).then(
            send_message,
            inputs=[user_selector, message, chatbot, dialog_state],
            outputs=[chatbot, dialog_state, message, latest_result_state, share_box, action_status, profile_summary],
        )
        quick_bmi.click(lambda: QUICK_PROMPTS["BMI 评估"], outputs=message).then(
            send_message,
            inputs=[user_selector, message, chatbot, dialog_state],
            outputs=[chatbot, dialog_state, message, latest_result_state, share_box, action_status, profile_summary],
        )
        quick_glucose.click(lambda: QUICK_PROMPTS["空腹血糖分析"], outputs=message).then(
            send_message,
            inputs=[user_selector, message, chatbot, dialog_state],
            outputs=[chatbot, dialog_state, message, latest_result_state, share_box, action_status, profile_summary],
        )
        quick_diet.click(lambda: QUICK_PROMPTS["饮食建议"], outputs=message).then(
            send_message,
            inputs=[user_selector, message, chatbot, dialog_state],
            outputs=[chatbot, dialog_state, message, latest_result_state, share_box, action_status, profile_summary],
        )

        demo.load(refresh_user_choices, outputs=user_selector).then(
            load_user_context,
            inputs=[user_selector, detail_view_state],
            outputs=[current_user, profile_summary, detail_panel, chatbot, dialog_state, latest_result_state, share_box, action_status],
        )

    return demo


def _parse_user_id(user_label: str | None) -> int | None:
    if not user_label:
        return None
    try:
        return int(str(user_label).split(" - ", maxsplit=1)[0])
    except (TypeError, ValueError):
        return None


def _validate_profile_form(
    name: str,
    birth_date: str,
    gender: str,
    height_cm: float | None,
    weight_kg: float | None,
    systolic_bp: float | None,
    diastolic_bp: float | None,
    fasting_glucose: float | None,
    require_basic: bool,
) -> str:
    issues: list[str] = []
    if require_basic and (not name.strip() or not birth_date.strip() or not gender.strip()):
        issues.append("姓名、出生日期、性别为必填项。")
    if birth_date:
        age = _age_from_birth_date(birth_date)
        if age is None:
            issues.append("出生日期格式应为 YYYY-MM-DD。")
        elif not 0 <= age <= 120:
            issues.append("出生日期对应的年龄需要在 0 到 120 岁之间。")
    for field_name, value, minimum, maximum in (
        ("height_cm", height_cm, 50, 250),
        ("weight_kg", weight_kg, 30, 200),
        ("systolic_bp", systolic_bp, 50, 300),
        ("diastolic_bp", diastolic_bp, 30, 200),
        ("fasting_glucose", fasting_glucose, 1, 50),
    ):
        if value is not None and not minimum <= float(value) <= maximum:
            issues.append(f"{PROFILE_LABELS.get(field_name, field_name)}需要在 {minimum} 到 {maximum} 之间。")
    if not issues and any(item not in (None, "") for item in [name, birth_date, gender, height_cm, weight_kg, systolic_bp, diastolic_bp, fasting_glucose]):
        return "输入范围校验通过。"
    return " ".join(issues)


def _age_from_birth_date(birth_date: str) -> int | None:
    try:
        birth = datetime.strptime(birth_date, "%Y-%m-%d").date()
    except ValueError:
        return None
    today = datetime.now().date()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def _collect_optional_profile_params(
    smoking_history: str,
    height_cm: float | None,
    weight_kg: float | None,
    systolic_bp: float | None,
    diastolic_bp: float | None,
    fasting_glucose: float | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if smoking_history:
        params["smoking_history"] = smoking_history
    if height_cm is not None:
        params["height_cm"] = int(height_cm) if float(height_cm).is_integer() else round(float(height_cm), 1)
    if weight_kg is not None:
        params["weight_kg"] = int(weight_kg) if float(weight_kg).is_integer() else round(float(weight_kg), 1)
    if systolic_bp is not None:
        params["systolic_bp"] = int(systolic_bp)
    if diastolic_bp is not None:
        params["diastolic_bp"] = int(diastolic_bp)
    if fasting_glucose is not None:
        params["fasting_glucose"] = int(fasting_glucose) if float(fasting_glucose).is_integer() else round(float(fasting_glucose), 1)
    return params


def _render_profile_summary(profile: dict[str, Any]) -> str:
    params = profile.get("params", {})
    age = profile.get("age") if profile.get("age") is not None else "-"
    bmi_text = "--"
    try:
        height = float(params.get("height_cm"))
        weight = float(params.get("weight_kg"))
        bmi_text = f"{weight / ((height / 100) ** 2):.1f}"
    except (TypeError, ValueError):
        pass
    metrics = [
        ("性别/年龄", f"{profile.get('gender', '-') or '-'} / {age}岁"),
        ("BMI 指数", bmi_text),
        ("身高/体重", _pair_value(params.get("height_cm"), "cm", params.get("weight_kg"), "kg")),
        ("最近血压", _pair_value(params.get("systolic_bp"), "", params.get("diastolic_bp"), "", sep="/")),
        ("吸烟史", str(params.get("smoking_history", "未记录"))),
    ]
    cards = "".join(
        f"<div style='background:#f8fafc;border-radius:14px;padding:12px;'><div class='soft-label'>{escape(label)}</div><div style='margin-top:4px;font-weight:700;color:#334155;'>{escape(value)}</div></div>"
        for label, value in metrics
    )
    return f"<div class='detail-card'><div style='font-weight:800;color:#1e293b;margin-bottom:12px;'>档案摘要</div><div style='display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;'>{cards}</div><div style='margin-top:12px;color:#94a3b8;font-size:12px;'>最近更新时间：{escape(str(profile.get('updated_at', '-')))}</div></div>"


def _render_detail_panel(service: AppService, user_id: int | None, detail_view: str) -> str:
    if user_id is None:
        return "<div class='detail-card'>请先创建或选择用户档案。</div>"
    if detail_view == "details":
        return _render_profile_snapshots(service.data_access.list_profile_snapshots(user_id))
    return _render_assessment_history(service.data_access.list_assessments(user_id))


def _render_assessment_history(assessments: list[dict[str, Any]]) -> str:
    if not assessments:
        return "<div class='detail-card'>暂无历史评估记录。点击右侧“保存到档案”后会显示在这里。</div>"
    return "".join(
        f"""
        <div class="detail-card">
          <div class="timeline-time">{escape(str(item.get('created_at', '-')))}</div>
          <div style="font-size:16px;font-weight:700;color:#1e293b;">{escape(str(item.get('calculator_name', '-')))}</div>
          <div style="margin-top:6px;color:#475569;">{escape(str(item.get('result_json', {}).get('summary', '-')))}</div>
          <div style="margin-top:8px;"><span class="risk-pill {_risk_class(str(item.get('result_json', {}).get('risk_level', '未知')))}">{escape(str(item.get('result_json', {}).get('risk_level', '未知')))}</span></div>
        </div>
        """
        for item in assessments
    )


def _render_profile_snapshots(snapshots: list[dict[str, Any]]) -> str:
    if not snapshots:
        return "<div class='detail-card'>暂无档案变更记录。</div>"
    items = []
    for snapshot in snapshots:
        profile = snapshot.get("snapshot_json", {})
        params = profile.get("params", {})
        param_lines = "".join(
            f"<li><strong>{escape(PROFILE_LABELS.get(key, key))}</strong>：{escape(str(value))}{PARAM_UNITS.get(key, '')}</li>"
            for key, value in params.items()
        ) or "<li>暂无参数</li>"
        items.append(
            f"""
            <div class="detail-card">
              <div class="timeline-time">{escape(str(snapshot.get('created_at', '-')))} · {escape(str(snapshot.get('source', '-')))}</div>
              <div style="font-size:16px;font-weight:700;color:#1e293b;">{escape(str(profile.get('name', '-')))}</div>
              <div style="margin-top:4px;color:#64748b;">性别：{escape(str(profile.get('gender', '-')))} · 出生日期：{escape(str(profile.get('birth_date', '-')))}</div>
              <ul style="margin-top:10px;padding-left:18px;color:#475569;">{param_lines}</ul>
            </div>
            """
        )
    return "".join(items)


def _render_empty_profile() -> str:
    return "<div class='detail-card'>请选择用户后查看档案摘要。</div>"


def _risk_class(risk_level: str) -> str:
    if any(word in risk_level for word in ["正常", "偏低", "低"]):
        return "risk-low"
    if any(word in risk_level for word in ["偏高", "中"]):
        return "risk-medium"
    return "risk-high"


def _pair_value(left: Any, left_unit: str, right: Any, right_unit: str, sep: str = " / ") -> str:
    if left in (None, "") and right in (None, ""):
        return "--"
    left_text = f"{left}{left_unit}" if left not in (None, "") else "--"
    right_text = f"{right}{right_unit}" if right not in (None, "") else "--"
    return f"{left_text}{sep}{right_text}"


def _to_float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
