from __future__ import annotations

from typing import Any, Dict


STANDARD_RESULT_FIELDS = (
    "score",
    "risk_level",
    "summary",
    "interpretation",
    "reference",
    "details",
)


def _get_float(params: Dict[str, Any], key: str, minimum: float | None = None, maximum: float | None = None) -> float:
    value = float(params[key])
    if minimum is not None and value < minimum:
        raise ValueError(f"{key} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{key} must be <= {maximum}")
    return value


def _build_result(
    *,
    score: Any,
    risk_level: str,
    summary: str,
    interpretation: str,
    reference: str,
    details: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "score": score,
        "risk_level": risk_level,
        "summary": summary,
        "interpretation": interpretation,
        "reference": reference,
        "details": details,
        "advice": interpretation,
        "guideline": reference,
    }


def calculate_bmi(params: Dict[str, Any]) -> Dict[str, Any]:
    height_cm = _get_float(params, "height_cm", minimum=50, maximum=250)
    weight_kg = _get_float(params, "weight_kg", minimum=2, maximum=500)
    height_m = height_cm / 100
    bmi = round(weight_kg / (height_m * height_m), 1)

    if bmi < 18.5:
        risk_level = "偏低"
        interpretation = "体重偏低，建议结合饮食、近期体重变化和运动情况进一步评估。"
    elif bmi < 24:
        risk_level = "正常"
        interpretation = "BMI 处于参考范围内，建议保持当前饮食与运动习惯。"
    elif bmi < 28:
        risk_level = "超重"
        interpretation = "提示体重超标，建议控制总热量摄入并增加规律运动。"
    else:
        risk_level = "肥胖"
        interpretation = "提示肥胖风险，建议尽快开展体重管理并关注血压、血糖等指标。"

    reference = "中国成人 BMI 分类参考：18.5-23.9 为正常，24.0-27.9 为超重，>=28 为肥胖。"
    return _build_result(
        score=bmi,
        risk_level=risk_level,
        summary=f"BMI 为 {bmi}",
        interpretation=interpretation,
        reference=reference,
        details={
            "calculator": "bmi",
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "unit": "kg/m^2",
            "input_summary": f"身高 {height_cm} cm，体重 {weight_kg} kg",
            "applicable_scene": "居家基础体重管理",
        },
    )


def calculate_bp_risk(params: Dict[str, Any]) -> Dict[str, Any]:
    systolic = _get_float(params, "systolic_bp", minimum=50, maximum=300)
    diastolic = _get_float(params, "diastolic_bp", minimum=30, maximum=200)

    if systolic >= 140 or diastolic >= 90:
        risk_level = "高风险"
        interpretation = "血压明显升高，建议尽快线下就医，由专业医生进一步评估。"
    elif systolic >= 120 or diastolic >= 80:
        risk_level = "偏高"
        interpretation = "血压偏高，建议减少钠盐摄入、规律运动，并在家庭环境中重复监测。"
    else:
        risk_level = "正常"
        interpretation = "血压处于参考范围内，建议继续保持规律监测。"

    reference = "成人家庭静息血压参考：收缩压 <120 mmHg 且舒张压 <80 mmHg 为正常，>=140/90 mmHg 需进一步医学评估。"
    return _build_result(
        score=f"{int(systolic)}/{int(diastolic)} mmHg",
        risk_level=risk_level,
        summary=f"血压为 {int(systolic)}/{int(diastolic)} mmHg",
        interpretation=interpretation,
        reference=reference,
        details={
            "calculator": "blood_pressure",
            "systolic_bp": systolic,
            "diastolic_bp": diastolic,
            "unit": "mmHg",
            "input_summary": f"收缩压 {int(systolic)} mmHg，舒张压 {int(diastolic)} mmHg",
            "applicable_scene": "居家血压风险初筛",
        },
    )


def calculate_fasting_glucose(params: Dict[str, Any]) -> Dict[str, Any]:
    glucose = _get_float(params, "fasting_glucose", minimum=1, maximum=50)

    if glucose < 3.9:
        risk_level = "偏低"
        interpretation = "空腹血糖偏低，如伴随出汗、心慌或乏力等不适，建议及时就医。"
    elif glucose <= 6.0:
        risk_level = "正常"
        interpretation = "空腹血糖处于参考范围内，建议持续保持健康饮食与规律作息。"
    elif glucose < 7.0:
        risk_level = "偏高"
        interpretation = "提示糖代谢异常风险，建议复测并尽快进行生活方式干预。"
    else:
        risk_level = "高风险"
        interpretation = "空腹血糖明显升高，建议尽快就医进行进一步评估。"

    reference = "空腹血糖常用参考范围约为 3.9-6.0 mmol/L，>=7.0 mmol/L 需进一步医学评估。"
    return _build_result(
        score=round(glucose, 1),
        risk_level=risk_level,
        summary=f"空腹血糖为 {round(glucose, 1)} mmol/L",
        interpretation=interpretation,
        reference=reference,
        details={
            "calculator": "fasting_glucose",
            "fasting_glucose": glucose,
            "unit": "mmol/L",
            "input_summary": f"空腹血糖 {round(glucose, 1)} mmol/L",
            "applicable_scene": "居家血糖风险初筛",
        },
    )


def calculate_waist_circumference(params: Dict[str, Any]) -> Dict[str, Any]:
    waist_cm = _get_float(params, "waist_cm", minimum=30, maximum=200)
    gender = str(params.get("gender", "")).strip()
    if gender not in {"男", "女"}:
        raise ValueError("gender must be 男 or 女")

    normal_upper = 90 if gender == "男" else 85
    high_risk_lower = 100 if gender == "男" else 95

    if waist_cm >= high_risk_lower:
        risk_level = "高风险"
        interpretation = "腰围明显增高，提示中心性肥胖风险较高，建议尽快进行体重管理并关注血压、血糖。"
    elif waist_cm >= normal_upper:
        risk_level = "偏高"
        interpretation = "腰围偏高，提示腹型脂肪堆积，建议控制总热量摄入并增加规律活动。"
    else:
        risk_level = "正常"
        interpretation = "腰围处于参考范围内，建议继续保持饮食和运动习惯。"

    reference = "中国成人中心性肥胖常用参考：男性腰围 <90 cm、女性腰围 <85 cm；更高水平提示风险进一步增加。"
    return _build_result(
        score=round(waist_cm, 1),
        risk_level=risk_level,
        summary=f"腰围为 {round(waist_cm, 1)} cm",
        interpretation=interpretation,
        reference=reference,
        details={
            "calculator": "waist_circumference",
            "waist_cm": waist_cm,
            "gender": gender,
            "unit": "cm",
            "input_summary": f"{gender}性腰围 {round(waist_cm, 1)} cm",
            "applicable_scene": "居家中心性肥胖风险初筛",
        },
    )


def calculate_resting_heart_rate(params: Dict[str, Any]) -> Dict[str, Any]:
    heart_rate = _get_float(params, "heart_rate_bpm", minimum=20, maximum=220)

    if heart_rate > 120:
        risk_level = "高风险"
        interpretation = "静息心率明显偏快，如伴心慌、胸闷或头晕，建议尽快就医。"
    elif heart_rate > 100:
        risk_level = "偏高"
        interpretation = "静息心率偏快，建议休息后复测，并关注睡眠、压力和近期不适。"
    elif heart_rate >= 60:
        risk_level = "正常"
        interpretation = "静息心率处于常见参考范围，建议继续规律监测。"
    else:
        risk_level = "偏低"
        interpretation = "静息心率偏低，如伴乏力、头晕或黑蒙，建议尽快咨询医生。"

    reference = "成人静息心率常见参考范围约为 60-100 次/分；持续明显过快或过慢需结合症状进一步评估。"
    return _build_result(
        score=int(round(heart_rate)),
        risk_level=risk_level,
        summary=f"静息心率为 {int(round(heart_rate))} 次/分",
        interpretation=interpretation,
        reference=reference,
        details={
            "calculator": "resting_heart_rate",
            "heart_rate_bpm": heart_rate,
            "unit": "次/分",
            "input_summary": f"静息心率 {int(round(heart_rate))} 次/分",
            "applicable_scene": "居家静息心率初筛",
        },
    )


def calculate_body_temperature(params: Dict[str, Any]) -> Dict[str, Any]:
    temperature = _get_float(params, "temperature_c", minimum=30, maximum=45)

    if temperature >= 38.0:
        risk_level = "高风险"
        interpretation = "体温明显升高，提示发热风险较高，建议结合伴随症状尽快就医。"
    elif temperature >= 37.3:
        risk_level = "偏高"
        interpretation = "体温偏高，建议休息、补充水分并短时间内复测体温。"
    elif temperature >= 36.1:
        risk_level = "正常"
        interpretation = "体温处于常见参考范围内，建议继续观察。"
    elif temperature >= 35.0:
        risk_level = "偏低"
        interpretation = "体温偏低，建议注意保暖并复测，如持续偏低应进一步评估。"
    else:
        risk_level = "高风险"
        interpretation = "体温明显偏低，建议尽快寻求医疗帮助。"

    reference = "成人体温常见参考范围约为 36.1-37.2 ℃；>=37.3 ℃ 提示发热风险，明显偏低也需警惕。"
    return _build_result(
        score=round(temperature, 1),
        risk_level=risk_level,
        summary=f"体温为 {round(temperature, 1)} ℃",
        interpretation=interpretation,
        reference=reference,
        details={
            "calculator": "body_temperature",
            "temperature_c": temperature,
            "unit": "℃",
            "input_summary": f"体温 {round(temperature, 1)} ℃",
            "applicable_scene": "居家体温异常初筛",
        },
    )


def calculate_fall_risk(params: Dict[str, Any]) -> Dict[str, Any]:
    age = int(_get_float(params, "age", minimum=0, maximum=120))
    balance_raw = str(params.get("balance_ability", "")).strip()
    balance_level = _normalize_balance_level(balance_raw)

    age_score = 0 if age < 65 else 1 if age < 75 else 2
    balance_score = {"良好": 0, "一般": 1, "较差": 2}[balance_level]
    total_score = age_score + balance_score

    if total_score >= 4:
        risk_level = "高风险"
        interpretation = "跌倒风险较高，建议尽快进行步态与环境安全评估，并减少独自高风险活动。"
    elif total_score >= 2:
        risk_level = "中风险"
        interpretation = "存在一定跌倒风险，建议加强平衡训练并关注居家防滑、防绊倒措施。"
    else:
        risk_level = "低风险"
        interpretation = "当前跌倒风险较低，建议继续保持活动能力并定期观察平衡状态。"

    reference = "老年人居家跌倒风险常结合年龄、平衡能力与步态稳定性进行分层，本结果仅用于初步提示。"
    return _build_result(
        score=total_score,
        risk_level=risk_level,
        summary=f"跌倒风险评分为 {total_score} 分",
        interpretation=interpretation,
        reference=reference,
        details={
            "calculator": "fall_risk",
            "age": age,
            "balance_ability": balance_level,
            "input_summary": f"年龄 {age} 岁，平衡能力 {balance_level}",
            "applicable_scene": "居家老年跌倒风险初筛",
        },
    )


def _normalize_balance_level(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("balance_ability is required")

    low_risk_terms = ("良好", "稳定", "正常", "平稳", "步态稳定", "无跌倒")
    medium_terms = ("一般", "尚可", "偶有不稳", "稍差")
    high_risk_terms = ("较差", "差", "不稳", "站不稳", "需搀扶", "步态不稳", "易跌倒", "曾跌倒")

    if any(term in cleaned for term in high_risk_terms):
        return "较差"
    if any(term in cleaned for term in medium_terms):
        return "一般"
    if any(term in cleaned for term in low_risk_terms):
        return "良好"

    if cleaned in {"良好", "一般", "较差"}:
        return cleaned
    return "一般"
