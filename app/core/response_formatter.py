import json
from html import escape
from typing import Any


class ResponseFormatter:
    def format_result(self, result: dict[str, Any]) -> tuple[str, str]:
        interpretation = result.get("interpretation", result.get("advice", "暂无"))
        reference = result.get("reference", result.get("guideline", "-"))
        details = result.get("details", {})
        display_name = details.get("display_name") or details.get("tool_name") or "健康评估"
        input_params = details.get("input_params", {})

        interpretation_text = str(interpretation).rstrip("。")
        reply_text = (
            f"评估完成：{result.get('summary', '已生成结果')}。"
            f" 风险等级：{result.get('risk_level', '未知')}。"
            f" 建议：{interpretation_text}。"
        )

        risk_class = self._risk_class(str(result.get("risk_level", "")))
        input_param_html = "".join(
            f"<span class='result-chip'><strong>{escape(self._param_label(str(name)))}</strong>{escape(str(value))}{escape(self._param_unit(str(name)))}</span>"
            for name, value in input_params.items()
        ) or "<span class='result-chip'>无额外参数</span>"

        card_html = f"""
        <div class="result-card">
          <div class="result-card__header">
            <div>
              <div class="result-card__eyebrow">量化评估结果</div>
              <div class="result-card__title">{escape(str(display_name))}</div>
            </div>
            <span class="risk-pill result-card__badge {risk_class}">{escape(str(result.get("risk_level", "-")))}</span>
          </div>
          <div class="result-card__score">
            <div class="result-card__score-label">评分 / 数值</div>
            <div class="result-card__score-value">{escape(str(result.get("score", "-")))}</div>
            <div class="result-card__score-summary">{escape(str(result.get("summary", "已生成评估结论")))}</div>
          </div>
          <div class="result-card__section">
            <div class="result-card__section-label">建议</div>
            <div class="result-card__section-text">{escape(str(interpretation))}</div>
          </div>
          <div class="result-card__section">
            <div class="result-card__section-label">参考说明</div>
            <div class="result-card__section-text">{escape(str(reference))}</div>
          </div>
          <div class="result-card__section">
            <div class="result-card__section-label">输入参数</div>
            <div class="result-card__chips">{input_param_html}</div>
          </div>
          <details>
            <summary>查看详细信息</summary>
            <pre>{escape(json.dumps(details, ensure_ascii=False, indent=2))}</pre>
          </details>
        </div>
        """
        return reply_text, card_html

    def format_profile_card(self, profile: dict[str, Any]) -> str:
        params = profile.get("params", {})
        param_lines = "".join(
            f"<span class='profile-chip'><strong>{escape(self._param_label(str(k)))}</strong>{escape(str(v))}{escape(self._param_unit(str(k)))}</span>"
            for k, v in params.items()
        ) or "<span class='profile-chip'>暂无已保存参数</span>"
        return f"""
        <div class="profile-card">
          <div class="profile-card__header">
            <div>
              <div class="profile-card__eyebrow">用户档案</div>
              <div class="profile-card__title">{escape(str(profile.get("name", "-")))}</div>
            </div>
            <span class="risk-pill risk-low">年龄 {escape(str(profile.get("age", "-")))}</span>
          </div>
          <div class="profile-card__section">
            <div class="profile-card__section-label">基础信息</div>
            <div class="profile-card__section-text">
              性别：{escape(str(profile.get("gender", "-")))}<br/>
              出生日期：{escape(str(profile.get("birth_date", "-")))}
            </div>
          </div>
          <div class="profile-card__section">
            <div class="profile-card__section-label">已记录参数</div>
            <div class="profile-card__chips">{param_lines}</div>
          </div>
        </div>
        """

    @staticmethod
    def _risk_class(risk_level: str) -> str:
        if "正常" in risk_level or "低" in risk_level:
            return "risk-low"
        if "中" in risk_level or "偏高" in risk_level:
            return "risk-medium"
        return "risk-high"

    @staticmethod
    def _param_label(name: str) -> str:
        return {
            "smoking_history": "吸烟史",
            "temperature_c": "体温",
            "heart_rate_bpm": "心率",
            "respiratory_rate_bpm": "呼吸频率",
            "height_cm": "身高",
            "weight_kg": "体重",
            "systolic_bp": "收缩压",
            "diastolic_bp": "舒张压",
            "sleep_quality": "睡眠质量",
            "urine_bowel_status": "尿便性状",
            "appetite_status": "食欲",
            "waist_cm": "腰围",
            "balance_ability": "平衡能力",
            "mood_cognition": "情绪与认知",
            "skin_sclera_status": "皮肤/巩膜颜色",
            "fasting_glucose": "空腹血糖",
            "blood_lipids": "血脂四项",
            "blood_routine": "血常规",
            "liver_function": "肝功能",
            "kidney_function": "肾功能",
            "vision_leg_edema": "视力/下肢水肿",
            "abdominal_ultrasound": "腹部超声",
            "ecg_report": "心电图",
            "bone_density": "骨密度",
            "cognitive_special_screening": "认知评估/专项筛查",
            "imaging_special_notes": "其他影像与专项体检结论",
            "thyroid_function": "甲状腺功能",
            "tumor_markers": "肿瘤标志物",
            "carotid_ultrasound": "颈动脉超声",
            "echo_abi": "超声心动图 / ABI",
            "specialist_notes": "专科补充说明",
            "age": "年龄",
            "gender": "性别",
        }.get(name, name)

    @staticmethod
    def _param_unit(name: str) -> str:
        return {
            "temperature_c": "℃",
            "heart_rate_bpm": "次/分",
            "respiratory_rate_bpm": "次/分",
            "height_cm": "cm",
            "weight_kg": "kg",
            "systolic_bp": "mmHg",
            "diastolic_bp": "mmHg",
            "fasting_glucose": "mmol/L",
            "waist_cm": "cm",
        }.get(name, "")
