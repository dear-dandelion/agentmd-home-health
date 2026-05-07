from __future__ import annotations

from typing import Any, Dict

from app.calculators.basic import _build_result, _get_float


def _get_optional_float(params: Dict[str, Any], key: str, minimum: float | None = None, maximum: float | None = None) -> float | None:
    if key not in params or params[key] in (None, ""):
        return None
    return _get_float(params, key, minimum=minimum, maximum=maximum)


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "y", "是", "有", "需要", "异常", "altered"}


def _score_from_total_or_items(
    params: Dict[str, Any],
    *,
    total_key: str = "total_score",
    item_keys: list[str] | None = None,
    minimum: float = 0,
    maximum: float = 500,
) -> float:
    if total_key in params and params[total_key] not in (None, ""):
        return _get_float(params, total_key, minimum=minimum, maximum=maximum)
    if not item_keys:
        raise KeyError(total_key)
    return sum(_get_float(params, key, minimum=0, maximum=maximum) for key in item_keys)


def _normalize_gender(value: Any) -> str:
    text = str(value).strip().lower()
    if text in {"男", "male", "m", "man"}:
        return "男"
    if text in {"女", "female", "f", "woman"}:
        return "女"
    raise ValueError("gender must be 男 or 女")


def _family_history_level(value: Any) -> str:
    text = str(value).strip().lower()
    mapping = {
        "none": "none",
        "无": "none",
        "no": "none",
        "second_degree": "second_degree",
        "二级亲属": "second_degree",
        "旁系": "second_degree",
        "first_degree": "first_degree",
        "一级亲属": "first_degree",
        "直系": "first_degree",
    }
    if text not in mapping:
        raise ValueError("family_history_diabetes must be none, second_degree, or first_degree")
    return mapping[text]


def calculate_phq9(params: Dict[str, Any]) -> Dict[str, Any]:
    score = int(round(_score_from_total_or_items(params, item_keys=[f"phq9_q{i}" for i in range(1, 10)], maximum=27)))
    if score >= 20:
        risk_level = "重度抑郁风险"
        interpretation = "分数提示重度抑郁症状，建议尽快联系精神心理专科进一步评估。"
    elif score >= 15:
        risk_level = "中重度抑郁风险"
        interpretation = "分数提示中重度抑郁症状，建议尽快接受专业评估并持续观察安全风险。"
    elif score >= 10:
        risk_level = "中度抑郁风险"
        interpretation = "分数提示中度抑郁症状，建议近期接受专业评估，并结合睡眠、食欲和功能变化综合判断。"
    elif score >= 5:
        risk_level = "轻度抑郁风险"
        interpretation = "分数提示轻度抑郁症状，可先进行生活方式调整，并持续观察症状是否加重。"
    else:
        risk_level = "低风险"
        interpretation = "当前总分较低，暂未提示明显抑郁症状。若近期情绪持续低落，仍建议继续观察。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"PHQ-9 总分为 {score} 分",
        interpretation=interpretation,
        reference="PHQ-9 常用分层：0-4 无或极轻，5-9 轻度，10-14 中度，15-19 中重度，20-27 重度。",
        details={"calculator": "phq9", "total_score": score, "input_mode": "total_or_items"},
    )


def calculate_gad7(params: Dict[str, Any]) -> Dict[str, Any]:
    score = int(round(_score_from_total_or_items(params, item_keys=[f"gad7_q{i}" for i in range(1, 8)], maximum=21)))
    if score >= 15:
        risk_level = "重度焦虑风险"
        interpretation = "分数提示重度焦虑症状，建议尽快寻求精神心理专业支持。"
    elif score >= 10:
        risk_level = "中度焦虑风险"
        interpretation = "分数提示中度焦虑症状，建议近期接受专业评估，并关注是否影响睡眠和日常功能。"
    elif score >= 5:
        risk_level = "轻度焦虑风险"
        interpretation = "分数提示轻度焦虑症状，可先进行压力管理和睡眠调整，并持续观察。"
    else:
        risk_level = "低风险"
        interpretation = "当前总分较低，暂未提示明显焦虑症状。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"GAD-7 总分为 {score} 分",
        interpretation=interpretation,
        reference="GAD-7 常用分层：0-4 无或极轻，5-9 轻度，10-14 中度，15-21 重度。",
        details={"calculator": "gad7", "total_score": score, "input_mode": "total_or_items"},
    )


def calculate_qsofa(params: Dict[str, Any]) -> Dict[str, Any]:
    rr = _get_float(params, "respiratory_rate_bpm", minimum=5, maximum=80)
    sbp = _get_float(params, "systolic_bp", minimum=50, maximum=300)
    gcs = _get_optional_float(params, "gcs_score", minimum=3, maximum=15)
    altered = _bool_value(params.get("altered_mental_status", False))
    mental_flag = altered or (gcs is not None and gcs < 15)
    score = int(rr >= 22) + int(sbp <= 100) + int(mental_flag)

    if score >= 2:
        risk_level = "高风险"
        interpretation = "qSOFA 提示感染相关不良结局风险较高，建议尽快线下就医。"
    elif score == 1:
        risk_level = "中风险"
        interpretation = "qSOFA 有 1 项异常，建议结合体温、意识状态和基础疾病继续观察，必要时就医。"
    else:
        risk_level = "低风险"
        interpretation = "当前 qSOFA 未提示明显高风险信号，但不能替代临床诊断。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"qSOFA 评分为 {score} 分",
        interpretation=interpretation,
        reference="qSOFA 由呼吸频率 >=22 次/分、收缩压 <=100 mmHg、意识状态改变三项组成，2 分及以上提示高风险。",
        details={"calculator": "qsofa", "respiratory_rate_bpm": rr, "systolic_bp": sbp, "gcs_score": gcs, "altered_mental_status": mental_flag},
    )


def calculate_news2(params: Dict[str, Any]) -> Dict[str, Any]:
    rr = _get_float(params, "respiratory_rate_bpm", minimum=5, maximum=80)
    spo2 = _get_float(params, "oxygen_saturation", minimum=50, maximum=100)
    oxygen = _bool_value(params.get("supplemental_oxygen", False))
    temp = _get_float(params, "temperature_c", minimum=30, maximum=45)
    sbp = _get_float(params, "systolic_bp", minimum=50, maximum=300)
    hr = _get_float(params, "heart_rate_bpm", minimum=20, maximum=220)
    consciousness = str(params.get("consciousness", "A")).strip().upper()

    score = 0
    score += 3 if rr <= 8 else 1 if rr <= 11 else 0 if rr <= 20 else 2 if rr <= 24 else 3
    score += 3 if spo2 <= 91 else 2 if spo2 <= 93 else 1 if spo2 <= 95 else 0
    score += 2 if oxygen else 0
    score += 3 if temp <= 35.0 else 1 if temp <= 36.0 else 0 if temp <= 38.0 else 1 if temp <= 39.0 else 2
    score += 3 if sbp <= 90 else 2 if sbp <= 100 else 1 if sbp <= 110 else 0 if sbp <= 219 else 3
    score += 3 if hr <= 40 else 1 if hr <= 50 else 0 if hr <= 90 else 1 if hr <= 110 else 2 if hr <= 130 else 3
    score += 0 if consciousness == "A" else 3

    if score >= 7:
        risk_level = "高风险"
        interpretation = "NEWS2 总分较高，提示急性恶化风险高，建议尽快就医或联系急救。"
    elif score >= 5:
        risk_level = "中高风险"
        interpretation = "NEWS2 提示病情可能恶化，建议尽快接受专业评估。"
    elif score >= 3:
        risk_level = "中风险"
        interpretation = "NEWS2 有一定异常，建议缩短复测间隔并关注症状变化。"
    else:
        risk_level = "低风险"
        interpretation = "当前 NEWS2 未提示明显高风险信号，但仍需结合症状综合判断。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"NEWS2 评分为 {score} 分",
        interpretation=interpretation,
        reference="NEWS2 依据呼吸频率、血氧饱和度、是否吸氧、体温、收缩压、心率和意识状态综合评分。",
        details={
            "calculator": "news2",
            "respiratory_rate_bpm": rr,
            "oxygen_saturation": spo2,
            "supplemental_oxygen": oxygen,
            "temperature_c": temp,
            "systolic_bp": sbp,
            "heart_rate_bpm": hr,
            "consciousness": consciousness,
        },
    )


def calculate_barthel_index(params: Dict[str, Any]) -> Dict[str, Any]:
    score = int(round(_score_from_total_or_items(params, maximum=100)))
    if score == 100:
        risk_level = "独立"
        interpretation = "Barthel 指数提示日常生活能力基本独立。"
    elif score >= 91:
        risk_level = "轻度依赖"
        interpretation = "提示存在轻度日常生活依赖，建议继续维持功能训练。"
    elif score >= 61:
        risk_level = "中度依赖"
        interpretation = "提示存在中度依赖，建议结合康复训练和家庭照护支持。"
    elif score >= 21:
        risk_level = "重度依赖"
        interpretation = "提示存在重度依赖，建议加强家庭照护并接受康复评估。"
    else:
        risk_level = "完全依赖"
        interpretation = "提示日常生活高度依赖，建议尽快完善照护方案和专业评估。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"Barthel 指数为 {score} 分",
        interpretation=interpretation,
        reference="Barthel 指数常用分层：100 独立，91-99 轻度依赖，61-90 中度依赖，21-60 重度依赖，0-20 完全依赖。",
        details={"calculator": "barthel_index", "total_score": score},
    )


def calculate_pain_nrs(params: Dict[str, Any]) -> Dict[str, Any]:
    score = int(round(_score_from_total_or_items(params, maximum=10)))
    if score >= 7:
        risk_level = "重度疼痛"
        interpretation = "疼痛评分较高，建议尽快评估诱因并联系医生调整止痛方案。"
    elif score >= 4:
        risk_level = "中度疼痛"
        interpretation = "提示中度疼痛，建议记录疼痛部位、持续时间和诱因，并按需就医。"
    elif score >= 1:
        risk_level = "轻度疼痛"
        interpretation = "提示轻度疼痛，可先观察变化并避免诱发因素。"
    else:
        risk_level = "无明显疼痛"
        interpretation = "当前评分未提示明显疼痛。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"疼痛 NRS 评分为 {score} 分",
        interpretation=interpretation,
        reference="疼痛 NRS 常用分层：0 无痛，1-3 轻度，4-6 中度，7-10 重度。",
        details={"calculator": "pain_nrs", "total_score": score},
    )


def calculate_mmrc(params: Dict[str, Any]) -> Dict[str, Any]:
    grade = int(round(_get_float(params, "grade", minimum=0, maximum=4)))
    if grade >= 3:
        risk_level = "高症状负担"
        interpretation = "mMRC 分级较高，提示活动后呼吸困难明显，建议尽快评估呼吸功能。"
    elif grade >= 2:
        risk_level = "中等症状负担"
        interpretation = "提示存在中等程度呼吸困难，建议结合咳嗽、痰量和活动耐量进一步评估。"
    else:
        risk_level = "低症状负担"
        interpretation = "当前呼吸困难分级较低。"
    return _build_result(
        score=grade,
        risk_level=risk_level,
        summary=f"mMRC 呼吸困难分级为 {grade} 级",
        interpretation=interpretation,
        reference="mMRC 分级范围 0-4 级，分级越高提示呼吸困难越明显。",
        details={"calculator": "mmrc", "grade": grade},
    )


def calculate_cat(params: Dict[str, Any]) -> Dict[str, Any]:
    score = int(round(_score_from_total_or_items(params, item_keys=[f"cat_q{i}" for i in range(1, 9)], maximum=40)))
    if score >= 31:
        risk_level = "极高症状负担"
        interpretation = "CAT 评分很高，提示慢阻肺相关症状负担重，建议尽快接受专业评估。"
    elif score >= 21:
        risk_level = "高症状负担"
        interpretation = "CAT 提示症状负担较高，建议尽快完善呼吸专科评估。"
    elif score >= 10:
        risk_level = "中等症状负担"
        interpretation = "CAT 提示存在一定症状负担，建议持续记录活动耐量和夜间症状。"
    else:
        risk_level = "低症状负担"
        interpretation = "当前 CAT 评分较低。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"CAT 总分为 {score} 分",
        interpretation=interpretation,
        reference="CAT 总分范围 0-40 分，通常 10 分以上提示症状负担增高。",
        details={"calculator": "cat", "total_score": score, "input_mode": "total_or_items"},
    )


def calculate_cha2ds2_vasc(params: Dict[str, Any]) -> Dict[str, Any]:
    age = _get_float(params, "age", minimum=0, maximum=120)
    gender = _normalize_gender(params.get("gender"))
    congestive_heart_failure = _bool_value(params.get("congestive_heart_failure", False))
    hypertension = _bool_value(params.get("hypertension", False))
    diabetes = _bool_value(params.get("diabetes", False))
    prior_stroke_tia = _bool_value(params.get("prior_stroke_tia_thromboembolism", False))
    vascular_disease = _bool_value(params.get("vascular_disease", False))

    score = 0
    score += 1 if congestive_heart_failure else 0
    score += 1 if hypertension else 0
    score += 2 if age >= 75 else 1 if age >= 65 else 0
    score += 1 if diabetes else 0
    score += 2 if prior_stroke_tia else 0
    score += 1 if vascular_disease else 0
    score += 1 if gender == "女" else 0
    non_sex_score = score - (1 if gender == "女" else 0)

    if (gender == "男" and score == 0) or (gender == "女" and non_sex_score == 0):
        risk_level = "低风险"
        interpretation = "当前 CHA2DS2-VASc 评分较低，卒中风险相对较低。"
    elif (gender == "男" and score == 1) or (gender == "女" and non_sex_score == 1):
        risk_level = "中风险"
        interpretation = "当前 CHA2DS2-VASc 评分提示存在一定卒中风险，建议结合临床情况评估抗栓策略。"
    else:
        risk_level = "高风险"
        interpretation = "当前 CHA2DS2-VASc 评分较高，提示卒中风险增高，建议尽快接受专业评估。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"CHA2DS2-VASc 评分为 {score} 分",
        interpretation=interpretation,
        reference="CHA2DS2-VASc 由心衰、高血压、年龄、糖尿病、卒中/TIA、血管疾病和性别组成。",
        details={"calculator": "cha2ds2_vasc", "age": age, "gender": gender, "non_sex_score": non_sex_score},
    )


def calculate_chads2(params: Dict[str, Any]) -> Dict[str, Any]:
    age = _get_float(params, "age", minimum=0, maximum=120)
    congestive_heart_failure = _bool_value(params.get("congestive_heart_failure", False))
    hypertension = _bool_value(params.get("hypertension", False))
    diabetes = _bool_value(params.get("diabetes", False))
    prior_stroke_tia = _bool_value(params.get("prior_stroke_tia", False))

    score = 0
    score += 1 if congestive_heart_failure else 0
    score += 1 if hypertension else 0
    score += 1 if age >= 75 else 0
    score += 1 if diabetes else 0
    score += 2 if prior_stroke_tia else 0

    if score == 0:
        risk_level = "低风险"
        interpretation = "当前 CHADS2 评分较低。"
    elif score <= 2:
        risk_level = "中风险"
        interpretation = "当前 CHADS2 评分提示存在一定卒中风险，建议结合房颤管理方案进一步评估。"
    else:
        risk_level = "高风险"
        interpretation = "当前 CHADS2 评分较高，提示卒中风险明显增加。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"CHADS2 评分为 {score} 分",
        interpretation=interpretation,
        reference="CHADS2 由心衰、高血压、年龄 >=75 岁、糖尿病和卒中/TIA 史组成，其中卒中/TIA 计 2 分。",
        details={"calculator": "chads2", "age": age},
    )


def calculate_has_bled(params: Dict[str, Any]) -> Dict[str, Any]:
    age = _get_float(params, "age", minimum=0, maximum=120)
    systolic_bp = _get_optional_float(params, "systolic_bp", minimum=50, maximum=300)
    uncontrolled_hypertension = _bool_value(params.get("uncontrolled_hypertension", False)) or bool(systolic_bp and systolic_bp > 160)
    abnormal_renal_function = _bool_value(params.get("abnormal_renal_function", False))
    abnormal_liver_function = _bool_value(params.get("abnormal_liver_function", False))
    prior_stroke = _bool_value(params.get("prior_stroke", False))
    bleeding_history = _bool_value(params.get("bleeding_history", False))
    labile_inr = _bool_value(params.get("labile_inr", False))
    drugs = _bool_value(params.get("drugs_predisposing_bleeding", False))
    alcohol = _bool_value(params.get("alcohol_excess", False))

    score = 0
    score += 1 if uncontrolled_hypertension else 0
    score += 1 if abnormal_renal_function else 0
    score += 1 if abnormal_liver_function else 0
    score += 1 if prior_stroke else 0
    score += 1 if bleeding_history else 0
    score += 1 if labile_inr else 0
    score += 1 if age > 65 else 0
    score += 1 if drugs else 0
    score += 1 if alcohol else 0

    if score >= 3:
        risk_level = "高风险"
        interpretation = "HAS-BLED 评分较高，提示出血风险增高，建议抗凝前后加强评估与监测。"
    elif score == 2:
        risk_level = "中风险"
        interpretation = "HAS-BLED 提示存在一定出血风险，建议结合可逆危险因素综合管理。"
    else:
        risk_level = "低风险"
        interpretation = "当前 HAS-BLED 评分较低。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"HAS-BLED 评分为 {score} 分",
        interpretation=interpretation,
        reference="HAS-BLED 由高血压、肾功能异常、肝功能异常、卒中、出血史、INR 不稳定、年龄 >65、药物和饮酒等组成。",
        details={"calculator": "has_bled", "age": age, "systolic_bp": systolic_bp},
    )


def calculate_wells_dvt(params: Dict[str, Any]) -> Dict[str, Any]:
    score = 0.0
    score += 1 if _bool_value(params.get("active_cancer", False)) else 0
    score += 1 if _bool_value(params.get("paralysis_or_recent_cast", False)) else 0
    score += 1 if _bool_value(params.get("bedridden_or_recent_surgery", False)) else 0
    score += 1 if _bool_value(params.get("localized_tenderness", False)) else 0
    score += 1 if _bool_value(params.get("entire_leg_swollen", False)) else 0
    score += 1 if _bool_value(params.get("calf_swelling_gt_3cm", False)) else 0
    score += 1 if _bool_value(params.get("pitting_edema", False)) else 0
    score += 1 if _bool_value(params.get("collateral_superficial_veins", False)) else 0
    score += 1 if _bool_value(params.get("previous_dvt", False)) else 0
    score -= 2 if _bool_value(params.get("alternative_diagnosis_more_likely", False)) else 0

    if score >= 3:
        risk_level = "高风险"
        interpretation = "Wells DVT 评分较高，提示深静脉血栓可能性高，建议尽快完善影像学检查。"
    elif score >= 1:
        risk_level = "中风险"
        interpretation = "Wells DVT 评分提示存在一定深静脉血栓风险，建议结合 D-二聚体或超声进一步评估。"
    else:
        risk_level = "低风险"
        interpretation = "当前 Wells DVT 评分较低。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"Wells DVT 评分为 {score} 分",
        interpretation=interpretation,
        reference="Wells DVT 评分由肿瘤、制动、压痛、肿胀、既往 DVT 等临床特征组成。",
        details={"calculator": "wells_dvt"},
    )


def calculate_wells_pe(params: Dict[str, Any]) -> Dict[str, Any]:
    heart_rate = _get_optional_float(params, "heart_rate_bpm", minimum=20, maximum=220)
    score = 0.0
    score += 3 if _bool_value(params.get("clinical_signs_dvt", False)) else 0
    score += 3 if _bool_value(params.get("pe_more_likely_than_alternative", False)) else 0
    score += 1.5 if bool(heart_rate and heart_rate > 100) else 0
    score += 1.5 if _bool_value(params.get("immobilization_or_recent_surgery", False)) else 0
    score += 1.5 if _bool_value(params.get("previous_dvt_pe", False)) else 0
    score += 1 if _bool_value(params.get("hemoptysis", False)) else 0
    score += 1 if _bool_value(params.get("malignancy", False)) else 0

    if score > 6:
        risk_level = "高风险"
        interpretation = "Wells PE 评分较高，提示肺栓塞可能性高，建议尽快就医。"
    elif score >= 2:
        risk_level = "中风险"
        interpretation = "Wells PE 评分提示存在一定肺栓塞风险，建议结合 D-二聚体和影像检查进一步评估。"
    else:
        risk_level = "低风险"
        interpretation = "当前 Wells PE 评分较低。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"Wells PE 评分为 {score} 分",
        interpretation=interpretation,
        reference="Wells PE 评分由 DVT 体征、临床判断、心率、制动/手术史、既往 VTE、咯血和肿瘤等组成。",
        details={"calculator": "wells_pe", "heart_rate_bpm": heart_rate},
    )


def calculate_heart_score(params: Dict[str, Any]) -> Dict[str, Any]:
    if "total_score" in params and params["total_score"] not in (None, ""):
        score = int(round(_get_float(params, "total_score", minimum=0, maximum=10)))
    else:
        history_score = int(round(_get_float(params, "history_score", minimum=0, maximum=2)))
        ecg_score = int(round(_get_float(params, "ecg_score", minimum=0, maximum=2)))
        troponin_score = int(round(_get_float(params, "troponin_score", minimum=0, maximum=2)))
        age = _get_optional_float(params, "age", minimum=0, maximum=120)
        age_score = int(round(_get_float(params, "age_score", minimum=0, maximum=2))) if age is None else (2 if age >= 65 else 1 if age >= 45 else 0)
        risk_factor_count = int(round(_get_optional_float(params, "risk_factor_count", minimum=0, maximum=10) or 0))
        known_atherosclerotic_disease = _bool_value(params.get("known_atherosclerotic_disease", False))
        risk_factor_score = 2 if known_atherosclerotic_disease or risk_factor_count >= 3 else 1 if risk_factor_count >= 1 else 0
        score = history_score + ecg_score + troponin_score + age_score + risk_factor_score

    if score >= 7:
        risk_level = "高风险"
        interpretation = "HEART 评分较高，提示短期主要心血管不良事件风险较高，建议尽快急诊评估。"
    elif score >= 4:
        risk_level = "中风险"
        interpretation = "HEART 评分提示中等风险，建议尽快结合心电图和肌钙蛋白动态评估。"
    else:
        risk_level = "低风险"
        interpretation = "当前 HEART 评分较低。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"HEART 评分为 {score} 分",
        interpretation=interpretation,
        reference="HEART 评分由病史、心电图、年龄、危险因素和肌钙蛋白五部分组成，每项 0-2 分。",
        details={"calculator": "heart_score"},
    )


def calculate_findrisc(params: Dict[str, Any]) -> Dict[str, Any]:
    age = _get_float(params, "age", minimum=0, maximum=120)
    bmi = _get_float(params, "bmi", minimum=10, maximum=80)
    waist_cm = _get_float(params, "waist_cm", minimum=30, maximum=200)
    gender = _normalize_gender(params.get("gender"))
    physically_active = _bool_value(params.get("physically_active_daily", False))
    daily_vegetables = _bool_value(params.get("daily_fruits_vegetables", False))
    antihypertensive = _bool_value(params.get("antihypertensive_medication", False))
    high_glucose = _bool_value(params.get("history_high_blood_glucose", False))
    family_history = _family_history_level(params.get("family_history_diabetes", "none"))

    score = 0
    score += 0 if age < 45 else 2 if age <= 54 else 3 if age <= 64 else 4
    score += 0 if bmi < 25 else 1 if bmi < 30 else 3
    if gender == "男":
        score += 0 if waist_cm < 94 else 3 if waist_cm <= 102 else 4
    else:
        score += 0 if waist_cm < 80 else 3 if waist_cm <= 88 else 4
    score += 0 if physically_active else 2
    score += 0 if daily_vegetables else 1
    score += 2 if antihypertensive else 0
    score += 5 if high_glucose else 0
    score += 0 if family_history == "none" else 3 if family_history == "second_degree" else 5

    if score >= 21:
        risk_level = "极高风险"
        interpretation = "FINDRISC 提示未来糖尿病风险很高，建议尽快进行专业评估和生活方式干预。"
    elif score >= 15:
        risk_level = "高风险"
        interpretation = "FINDRISC 提示未来糖尿病风险较高，建议尽快管理体重、饮食和运动。"
    elif score >= 12:
        risk_level = "中风险"
        interpretation = "FINDRISC 提示存在中等糖尿病风险，建议定期监测血糖并调整生活方式。"
    elif score >= 7:
        risk_level = "轻中度风险"
        interpretation = "FINDRISC 提示风险略增高，建议关注体重、饮食和运动。"
    else:
        risk_level = "低风险"
        interpretation = "当前 FINDRISC 评分较低。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"FINDRISC 评分为 {score} 分",
        interpretation=interpretation,
        reference="FINDRISC 由年龄、BMI、腰围、体力活动、饮食、降压药、高血糖史和家族史组成。",
        details={"calculator": "findrisc", "age": age, "bmi": bmi, "waist_cm": waist_cm, "gender": gender},
    )


def calculate_metabolic_syndrome(params: Dict[str, Any]) -> Dict[str, Any]:
    waist_cm = _get_float(params, "waist_cm", minimum=30, maximum=200)
    gender = _normalize_gender(params.get("gender"))
    systolic_bp = _get_float(params, "systolic_bp", minimum=50, maximum=300)
    diastolic_bp = _get_float(params, "diastolic_bp", minimum=30, maximum=200)
    fasting_glucose = _get_float(params, "fasting_glucose", minimum=1, maximum=50)
    triglycerides = _get_float(params, "triglycerides_mmol_l", minimum=0.1, maximum=50)
    hdl = _get_float(params, "hdl_mmol_l", minimum=0.1, maximum=10)

    central_obesity = waist_cm >= (90 if gender == "男" else 85)
    hypertension = systolic_bp >= 130 or diastolic_bp >= 85
    hyperglycemia = fasting_glucose >= 5.6
    hypertriglyceridemia = triglycerides >= 1.7
    low_hdl = hdl < (1.0 if gender == "男" else 1.3)

    criteria_met = [central_obesity, hypertension, hyperglycemia, hypertriglyceridemia, low_hdl]
    score = sum(1 for item in criteria_met if item)

    if score >= 3:
        risk_level = "符合代谢综合征"
        interpretation = "当前已满足代谢综合征常用诊断条件，建议尽快进行系统性慢病风险管理。"
    elif score == 2:
        risk_level = "接近代谢综合征"
        interpretation = "当前已满足 2 项异常，提示代谢风险明显上升，建议尽快干预。"
    else:
        risk_level = "未达到代谢综合征标准"
        interpretation = "当前未达到代谢综合征常用诊断标准。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"代谢综合征异常项数为 {score} 项",
        interpretation=interpretation,
        reference="常用代谢综合征筛查依据中心性肥胖、血压、空腹血糖、甘油三酯和 HDL 五项指标，满足 3 项及以上提示异常。",
        details={"calculator": "metabolic_syndrome", "gender": gender, "central_obesity": central_obesity, "hypertension": hypertension, "hyperglycemia": hyperglycemia, "hypertriglyceridemia": hypertriglyceridemia, "low_hdl": low_hdl},
    )


def calculate_nafld_fibrosis(params: Dict[str, Any]) -> Dict[str, Any]:
    age = _get_float(params, "age", minimum=0, maximum=120)
    bmi = _get_float(params, "bmi", minimum=10, maximum=80)
    ast = _get_float(params, "ast_u_l", minimum=1, maximum=5000)
    alt = _get_float(params, "alt_u_l", minimum=1, maximum=5000)
    platelets = _get_float(params, "platelet_10e9_l", minimum=1, maximum=2000)
    albumin = _get_float(params, "albumin_g_dl", minimum=0.5, maximum=10)
    ifg_or_diabetes = _bool_value(params.get("impaired_fasting_glucose_or_diabetes", False))
    ratio = ast / alt
    score = round(-1.675 + 0.037 * age + 0.094 * bmi + 1.13 * int(ifg_or_diabetes) + 0.99 * ratio - 0.013 * platelets - 0.66 * albumin, 3)

    if score < -1.455:
        risk_level = "低风险"
        interpretation = "NAFLD fibrosis score 较低，提示进展性纤维化可能性较低。"
    elif score <= 0.676:
        risk_level = "不确定风险"
        interpretation = "NAFLD fibrosis score 处于灰区，建议结合弹性成像或专科评估进一步判断。"
    else:
        risk_level = "高风险"
        interpretation = "NAFLD fibrosis score 较高，提示进展性纤维化风险升高，建议尽快就医。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"NAFLD fibrosis score 为 {score}",
        interpretation=interpretation,
        reference="NAFLD fibrosis score 依据年龄、BMI、糖代谢异常、AST/ALT 比值、血小板和白蛋白计算。",
        details={"calculator": "nafld_fibrosis", "age": age, "bmi": bmi, "ast_alt_ratio": round(ratio, 3), "platelet_10e9_l": platelets, "albumin_g_dl": albumin, "ifg_or_diabetes": ifg_or_diabetes},
    )


def calculate_morse_fall_scale(params: Dict[str, Any]) -> Dict[str, Any]:
    score = int(round(_score_from_total_or_items(params, maximum=125)))
    if score >= 45:
        risk_level = "高风险"
        interpretation = "Morse 跌倒量表提示跌倒风险较高，建议尽快进行防跌倒干预。"
    elif score >= 25:
        risk_level = "中风险"
        interpretation = "Morse 跌倒量表提示存在一定跌倒风险，建议加强环境和步态安全管理。"
    else:
        risk_level = "低风险"
        interpretation = "当前 Morse 跌倒量表评分较低。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"Morse 跌倒量表评分为 {score} 分",
        interpretation=interpretation,
        reference="Morse Fall Scale 常用分层：0-24 低风险，25-44 中风险，45 分及以上高风险。",
        details={"calculator": "morse_fall_scale", "total_score": score},
    )


def calculate_braden_scale(params: Dict[str, Any]) -> Dict[str, Any]:
    score = int(round(_score_from_total_or_items(params, maximum=23)))
    if score <= 9:
        risk_level = "极高风险"
        interpretation = "Braden 评分极低，提示压疮风险极高，建议立即加强翻身减压和皮肤护理。"
    elif score <= 12:
        risk_level = "高风险"
        interpretation = "Braden 评分提示压疮高风险，建议尽快完善减压和护理方案。"
    elif score <= 14:
        risk_level = "中风险"
        interpretation = "Braden 评分提示中度压疮风险，建议持续观察皮肤完整性并加强护理。"
    elif score <= 18:
        risk_level = "轻度风险"
        interpretation = "Braden 评分提示轻度压疮风险，建议关注翻身、营养和皮肤保护。"
    else:
        risk_level = "低风险"
        interpretation = "当前 Braden 评分提示压疮风险较低。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"Braden 评分为 {score} 分",
        interpretation=interpretation,
        reference="Braden Scale 常用分层：<=9 极高风险，10-12 高风险，13-14 中风险，15-18 轻度风险，>18 低风险。",
        details={"calculator": "braden_scale", "total_score": score},
    )


def calculate_mna_sf(params: Dict[str, Any]) -> Dict[str, Any]:
    score = int(round(_score_from_total_or_items(params, maximum=14)))
    if score <= 7:
        risk_level = "营养不良"
        interpretation = "MNA-SF 提示营养不良，建议尽快进行营养评估与干预。"
    elif score <= 11:
        risk_level = "营养不良风险"
        interpretation = "MNA-SF 提示存在营养不良风险，建议尽快调整饮食并进一步评估。"
    else:
        risk_level = "营养状态正常"
        interpretation = "当前 MNA-SF 未提示明显营养风险。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"MNA-SF 评分为 {score} 分",
        interpretation=interpretation,
        reference="MNA-SF 常用分层：12-14 正常，8-11 营养不良风险，0-7 营养不良。",
        details={"calculator": "mna_sf", "total_score": score},
    )


def calculate_gds15(params: Dict[str, Any]) -> Dict[str, Any]:
    score = int(round(_score_from_total_or_items(params, maximum=15)))
    if score >= 12:
        risk_level = "重度抑郁风险"
        interpretation = "GDS-15 评分提示老年抑郁风险较高，建议尽快接受专业评估。"
    elif score >= 9:
        risk_level = "中度抑郁风险"
        interpretation = "GDS-15 评分提示中度抑郁风险，建议近期完善心理评估。"
    elif score >= 5:
        risk_level = "轻度抑郁风险"
        interpretation = "GDS-15 评分提示轻度抑郁风险，建议继续观察并评估睡眠、食欲和兴趣变化。"
    else:
        risk_level = "低风险"
        interpretation = "当前 GDS-15 评分较低。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"GDS-15 评分为 {score} 分",
        interpretation=interpretation,
        reference="GDS-15 常用分层：0-4 正常，5-8 轻度，9-11 中度，12-15 重度抑郁风险。",
        details={"calculator": "gds15", "total_score": score},
    )


def calculate_tug_test(params: Dict[str, Any]) -> Dict[str, Any]:
    seconds = _get_float(params, "time_seconds", minimum=1, maximum=300)
    if seconds >= 13.5:
        risk_level = "高跌倒风险"
        interpretation = "TUG 时间延长，提示跌倒风险升高，建议进一步评估平衡和步态。"
    elif seconds >= 10:
        risk_level = "中等跌倒风险"
        interpretation = "TUG 提示功能移动性略下降，建议关注步态和平衡训练。"
    else:
        risk_level = "低跌倒风险"
        interpretation = "当前 TUG 时间较好。"
    return _build_result(
        score=round(seconds, 1),
        risk_level=risk_level,
        summary=f"TUG 用时为 {round(seconds, 1)} 秒",
        interpretation=interpretation,
        reference="TUG 常以 13.5 秒作为跌倒风险筛查参考阈值，时间越长提示功能移动性越差。",
        details={"calculator": "tug_test", "time_seconds": seconds},
    )


def calculate_ad8(params: Dict[str, Any]) -> Dict[str, Any]:
    score = int(round(_score_from_total_or_items(params, maximum=8)))
    if score >= 2:
        risk_level = "认知异常风险"
        interpretation = "AD8 提示存在认知异常风险，建议尽快进行进一步认知评估。"
    else:
        risk_level = "低风险"
        interpretation = "当前 AD8 评分较低。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"AD8 评分为 {score} 分",
        interpretation=interpretation,
        reference="AD8 总分 0-8 分，2 分及以上常提示认知异常风险。",
        details={"calculator": "ad8", "total_score": score},
    )


def calculate_mini_cog(params: Dict[str, Any]) -> Dict[str, Any]:
    recall = int(round(_get_float(params, "recall_score", minimum=0, maximum=3)))
    clock_normal = _bool_value(params.get("clock_normal", False))
    total_score = recall + (2 if clock_normal else 0)
    impaired = recall == 0 or (recall in {1, 2} and not clock_normal)
    if impaired:
        risk_level = "认知异常风险"
        interpretation = "Mini-Cog 提示存在认知异常风险，建议进一步进行认知功能评估。"
    else:
        risk_level = "低风险"
        interpretation = "当前 Mini-Cog 未提示明显认知异常风险。"
    return _build_result(
        score=total_score,
        risk_level=risk_level,
        summary=f"Mini-Cog 评分为 {total_score} 分",
        interpretation=interpretation,
        reference="Mini-Cog 由三词回忆和画钟组成；0 个回忆词或 1-2 个回忆词且画钟异常常提示认知异常风险。",
        details={"calculator": "mini_cog", "recall_score": recall, "clock_normal": clock_normal},
    )


def calculate_fried_frailty(params: Dict[str, Any]) -> Dict[str, Any]:
    score = int(round(_score_from_total_or_items(params, maximum=5)))
    if score >= 3:
        risk_level = "衰弱"
        interpretation = "Fried 衰弱表型提示已达衰弱状态，建议尽快开展综合老年评估。"
    elif score >= 1:
        risk_level = "衰弱前期"
        interpretation = "Fried 衰弱表型提示处于衰弱前期，建议尽早进行运动和营养干预。"
    else:
        risk_level = "非衰弱"
        interpretation = "当前 Fried 衰弱表型未提示明显衰弱。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"Fried 衰弱表型评分为 {score} 分",
        interpretation=interpretation,
        reference="Fried 衰弱表型包含体重下降、乏力、活动减少、步速慢和握力弱，0 分非衰弱，1-2 分衰弱前期，3-5 分衰弱。",
        details={"calculator": "fried_frailty", "total_score": score},
    )


def calculate_lawton_iadl(params: Dict[str, Any]) -> Dict[str, Any]:
    score = int(round(_score_from_total_or_items(params, maximum=8)))
    if score >= 8:
        risk_level = "独立"
        interpretation = "Lawton IADL 提示工具性日常生活能力基本独立。"
    elif score >= 6:
        risk_level = "轻度依赖"
        interpretation = "Lawton IADL 提示存在轻度工具性日常生活依赖。"
    elif score >= 3:
        risk_level = "中度依赖"
        interpretation = "Lawton IADL 提示存在中度依赖，建议结合照护需求进一步评估。"
    else:
        risk_level = "重度依赖"
        interpretation = "Lawton IADL 提示工具性日常生活能力受限明显，建议尽快完善照护支持。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"Lawton IADL 评分为 {score} 分",
        interpretation=interpretation,
        reference="Lawton IADL 常用总分 0-8 分，分数越低提示工具性日常生活能力依赖越明显。",
        details={"calculator": "lawton_iadl", "total_score": score},
    )


def calculate_sarc_f(params: Dict[str, Any]) -> Dict[str, Any]:
    score = int(round(_score_from_total_or_items(params, maximum=10)))
    if score >= 4:
        risk_level = "肌少症风险"
        interpretation = "SARC-F 提示肌少症风险升高，建议进一步进行肌力和肌量评估。"
    else:
        risk_level = "低风险"
        interpretation = "当前 SARC-F 评分较低。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"SARC-F 评分为 {score} 分",
        interpretation=interpretation,
        reference="SARC-F 总分 0-10 分，4 分及以上常提示肌少症风险升高。",
        details={"calculator": "sarc_f", "total_score": score},
    )


def calculate_rockwood_cfs(params: Dict[str, Any]) -> Dict[str, Any]:
    score = int(round(_get_float(params, "grade", minimum=1, maximum=9)))
    if score >= 7:
        risk_level = "重度衰弱"
        interpretation = "Clinical Frailty Scale 提示重度衰弱，建议尽快完善综合照护与风险管理。"
    elif score >= 5:
        risk_level = "衰弱"
        interpretation = "Clinical Frailty Scale 提示已进入衰弱状态，建议加强功能和营养干预。"
    elif score == 4:
        risk_level = "脆弱"
        interpretation = "Clinical Frailty Scale 提示处于脆弱阶段，建议尽早干预以延缓功能下降。"
    else:
        risk_level = "较稳定"
        interpretation = "当前 Clinical Frailty Scale 提示总体功能状态相对稳定。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"Clinical Frailty Scale 评分为 {score} 级",
        interpretation=interpretation,
        reference="Clinical Frailty Scale 为 1-9 级量表，分值越高提示衰弱程度越重。",
        details={"calculator": "rockwood_cfs", "grade": score},
    )


def calculate_karnofsky_ps(params: Dict[str, Any]) -> Dict[str, Any]:
    score = int(round(_get_float(params, "total_score", minimum=0, maximum=100)))
    if score >= 80:
        risk_level = "功能状态较好"
        interpretation = "Karnofsky 评分提示日常功能状态较好。"
    elif score >= 50:
        risk_level = "中度功能受限"
        interpretation = "Karnofsky 评分提示存在一定功能受限，建议关注照护和康复需求。"
    else:
        risk_level = "重度功能受限"
        interpretation = "Karnofsky 评分较低，提示依赖程度较高，建议尽快完善支持性照护。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"Karnofsky 评分为 {score} 分",
        interpretation=interpretation,
        reference="Karnofsky Performance Status 评分范围 0-100 分，分数越高表示功能状态越好。",
        details={"calculator": "karnofsky_ps", "total_score": score},
    )


def calculate_cdrs(params: Dict[str, Any]) -> Dict[str, Any]:
    age = _get_float(params, "age", minimum=20, maximum=74)
    bmi = _get_float(params, "bmi", minimum=10, maximum=80)
    waist_cm = _get_float(params, "waist_cm", minimum=30, maximum=200)
    systolic_bp = _get_float(params, "systolic_bp", minimum=50, maximum=300)
    gender = _normalize_gender(params.get("gender"))
    family_history = _bool_value(params.get("family_history_diabetes", False))

    if age < 25:
        age_score = 0
    elif age < 35:
        age_score = 4
    elif age < 40:
        age_score = 8
    elif age < 45:
        age_score = 11
    elif age < 50:
        age_score = 12
    elif age < 55:
        age_score = 13
    elif age < 60:
        age_score = 15
    elif age < 65:
        age_score = 16
    else:
        age_score = 18

    bmi_score = 0 if bmi < 22 else 1 if bmi < 24 else 3 if bmi < 30 else 5

    if gender == "男":
        waist_score = 0 if waist_cm < 75 else 3 if waist_cm < 80 else 5 if waist_cm < 85 else 7 if waist_cm < 90 else 8 if waist_cm < 95 else 10
    else:
        waist_score = 0 if waist_cm < 70 else 3 if waist_cm < 75 else 5 if waist_cm < 80 else 7 if waist_cm < 85 else 8 if waist_cm < 90 else 10

    sbp_score = 0 if systolic_bp < 110 else 1 if systolic_bp < 120 else 3 if systolic_bp < 130 else 6 if systolic_bp < 140 else 7 if systolic_bp < 150 else 8 if systolic_bp < 160 else 10
    family_score = 6 if family_history else 0
    gender_score = 2 if gender == "男" else 0
    score = age_score + bmi_score + waist_score + sbp_score + family_score + gender_score

    if score >= 25:
        risk_level = "高风险"
        interpretation = "CDRS 提示已达到中国糖尿病高危人群常用筛查阈值，建议进一步进行 OGTT 或规范血糖检查。"
    elif score >= 20:
        risk_level = "中风险"
        interpretation = "CDRS 提示糖尿病风险升高，建议加强体重、腰围和血压管理，并定期筛查。"
    else:
        risk_level = "低风险"
        interpretation = "当前 CDRS 评分相对较低。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"CDRS 评分为 {score} 分",
        interpretation=interpretation,
        reference="中国糖尿病风险评分表常以总分 >=25 分作为高危筛查阈值。",
        details={"calculator": "cdrs", "age": age, "bmi": bmi, "waist_cm": waist_cm, "systolic_bp": systolic_bp, "gender": gender},
    )


def calculate_nihss(params: Dict[str, Any]) -> Dict[str, Any]:
    score = int(round(_score_from_total_or_items(params, maximum=42)))
    if score >= 21:
        risk_level = "重度神经功能缺损"
        interpretation = "NIHSS 提示重度神经功能缺损，建议立即就医并接受卒中专科评估。"
    elif score >= 16:
        risk_level = "中重度神经功能缺损"
        interpretation = "NIHSS 提示中重度神经功能缺损，建议尽快完善神经专科评估。"
    elif score >= 5:
        risk_level = "中度神经功能缺损"
        interpretation = "NIHSS 提示存在中度神经功能缺损。"
    elif score >= 1:
        risk_level = "轻度神经功能缺损"
        interpretation = "NIHSS 提示轻度神经功能缺损。"
    else:
        risk_level = "无明显缺损"
        interpretation = "当前 NIHSS 评分未提示明显神经功能缺损。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"NIHSS 评分为 {score} 分",
        interpretation=interpretation,
        reference="NIHSS 总分范围 0-42 分，分数越高提示神经功能缺损越重。",
        details={"calculator": "nihss", "total_score": score},
    )


def calculate_glasgow_coma_scale(params: Dict[str, Any]) -> Dict[str, Any]:
    score = int(round(_score_from_total_or_items(params, total_key="gcs_score", maximum=15, item_keys=["eye_score", "verbal_score", "motor_score"])))
    if score <= 8:
        risk_level = "重度意识障碍"
        interpretation = "GCS 提示重度意识障碍，建议立即就医。"
    elif score <= 12:
        risk_level = "中度意识障碍"
        interpretation = "GCS 提示中度意识障碍，建议尽快接受专业评估。"
    else:
        risk_level = "轻度或无明显意识障碍"
        interpretation = "当前 GCS 提示意识状态相对较稳定。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"GCS 评分为 {score} 分",
        interpretation=interpretation,
        reference="Glasgow Coma Scale 常用分层：13-15 轻度，9-12 中度，3-8 重度意识障碍。",
        details={"calculator": "glasgow_coma_scale", "gcs_score": score},
    )


def calculate_must(params: Dict[str, Any]) -> Dict[str, Any]:
    if "total_score" in params and params["total_score"] not in (None, ""):
        score = int(round(_get_float(params, "total_score", minimum=0, maximum=10)))
    else:
        bmi = _get_float(params, "bmi", minimum=10, maximum=80)
        weight_loss_percent = _get_float(params, "weight_loss_percent", minimum=0, maximum=100)
        acute_disease_effect = _bool_value(params.get("acute_disease_effect", False))
        score = 0
        score += 0 if bmi > 20 else 1 if bmi >= 18.5 else 2
        score += 0 if weight_loss_percent < 5 else 1 if weight_loss_percent <= 10 else 2
        score += 2 if acute_disease_effect else 0

    if score >= 2:
        risk_level = "高营养风险"
        interpretation = "MUST 提示营养风险较高，建议尽快进行营养评估与干预。"
    elif score == 1:
        risk_level = "中营养风险"
        interpretation = "MUST 提示中等营养风险，建议密切随访体重和进食情况。"
    else:
        risk_level = "低营养风险"
        interpretation = "当前 MUST 评分较低。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"MUST 评分为 {score} 分",
        interpretation=interpretation,
        reference="MUST 由 BMI、近期体重下降和急性疾病效应组成，0 分低风险，1 分中风险，>=2 分高风险。",
        details={"calculator": "must", "total_score": score},
    )


def calculate_caprini_vte(params: Dict[str, Any]) -> Dict[str, Any]:
    score = int(round(_score_from_total_or_items(params, maximum=40)))
    if score >= 5:
        risk_level = "极高风险"
        interpretation = "Caprini 评分较高，提示静脉血栓栓塞风险高，建议尽快进行专业评估。"
    elif score >= 3:
        risk_level = "高风险"
        interpretation = "Caprini 评分提示血栓风险较高，建议结合手术、卧床和基础病情况管理。"
    elif score == 2:
        risk_level = "中风险"
        interpretation = "Caprini 评分提示中等血栓风险。"
    else:
        risk_level = "低风险"
        interpretation = "当前 Caprini 评分较低。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"Caprini 评分为 {score} 分",
        interpretation=interpretation,
        reference="Caprini 评分分数越高提示静脉血栓栓塞风险越高，常以 5 分及以上视为高危。",
        details={"calculator": "caprini_vte", "total_score": score},
    )


def calculate_mews(params: Dict[str, Any]) -> Dict[str, Any]:
    if "total_score" in params and params["total_score"] not in (None, ""):
        score = int(round(_get_float(params, "total_score", minimum=0, maximum=20)))
    else:
        rr = _get_float(params, "respiratory_rate_bpm", minimum=5, maximum=80)
        temp = _get_float(params, "temperature_c", minimum=30, maximum=45)
        sbp = _get_float(params, "systolic_bp", minimum=50, maximum=300)
        hr = _get_float(params, "heart_rate_bpm", minimum=20, maximum=220)
        consciousness = str(params.get("consciousness", "A")).strip().upper()

        score = 0
        score += 2 if rr < 9 else 0 if rr <= 14 else 1 if rr <= 20 else 2 if rr <= 29 else 3
        score += 2 if temp < 35 else 0 if temp <= 38.4 else 2
        score += 3 if sbp <= 70 else 2 if sbp <= 80 else 1 if sbp <= 100 else 0 if sbp <= 199 else 2
        score += 2 if hr <= 40 else 1 if hr <= 50 else 0 if hr <= 100 else 1 if hr <= 110 else 2 if hr < 130 else 3
        score += 0 if consciousness == "A" else 3

    if score >= 5:
        risk_level = "高风险"
        interpretation = "MEWS 提示病情恶化风险较高，建议尽快就医或接受专业评估。"
    elif score >= 3:
        risk_level = "中风险"
        interpretation = "MEWS 提示存在一定病情恶化风险，建议缩短观察间隔。"
    else:
        risk_level = "低风险"
        interpretation = "当前 MEWS 评分较低。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"MEWS 评分为 {score} 分",
        interpretation=interpretation,
        reference="MEWS 常依据呼吸频率、体温、收缩压、心率和意识状态综合评分。",
        details={"calculator": "mews", "total_score": score},
    )


def calculate_charlson_cci(params: Dict[str, Any]) -> Dict[str, Any]:
    score = int(round(_score_from_total_or_items(params, maximum=50)))
    if score >= 5:
        risk_level = "高合并症负担"
        interpretation = "Charlson 合并症指数较高，提示基础病负担较重，建议综合管理。"
    elif score >= 3:
        risk_level = "中等合并症负担"
        interpretation = "Charlson 合并症指数提示存在一定基础病负担。"
    else:
        risk_level = "低合并症负担"
        interpretation = "当前 Charlson 合并症指数较低。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"Charlson 合并症指数为 {score} 分",
        interpretation=interpretation,
        reference="Charlson Comorbidity Index 分数越高提示合并症负担越重。",
        details={"calculator": "charlson_cci", "total_score": score},
    )


def calculate_norton_scale(params: Dict[str, Any]) -> Dict[str, Any]:
    score = int(round(_score_from_total_or_items(params, maximum=20)))
    if score <= 12:
        risk_level = "高压疮风险"
        interpretation = "Norton 评分较低，提示压疮风险较高，建议加强减压和皮肤护理。"
    elif score <= 14:
        risk_level = "中风险"
        interpretation = "Norton 评分提示存在一定压疮风险。"
    else:
        risk_level = "低风险"
        interpretation = "当前 Norton 评分提示压疮风险较低。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"Norton 评分为 {score} 分",
        interpretation=interpretation,
        reference="Norton Scale 分数越低提示压疮风险越高，常以 <=14 分作为警示阈值。",
        details={"calculator": "norton_scale", "total_score": score},
    )


def calculate_waterlow_score(params: Dict[str, Any]) -> Dict[str, Any]:
    score = int(round(_score_from_total_or_items(params, maximum=100)))
    if score >= 20:
        risk_level = "极高压疮风险"
        interpretation = "Waterlow 评分提示极高压疮风险，建议立即加强护理干预。"
    elif score >= 15:
        risk_level = "高压疮风险"
        interpretation = "Waterlow 评分提示高压疮风险，建议尽快进行减压和护理。"
    elif score >= 10:
        risk_level = "有压疮风险"
        interpretation = "Waterlow 评分提示存在压疮风险，建议加强皮肤观察和保护。"
    else:
        risk_level = "低风险"
        interpretation = "当前 Waterlow 评分较低。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"Waterlow 评分为 {score} 分",
        interpretation=interpretation,
        reference="Waterlow 常用分层：10-14 有风险，15-19 高风险，20 分及以上极高风险。",
        details={"calculator": "waterlow_score", "total_score": score},
    )


def calculate_ascvd_10y(params: Dict[str, Any]) -> Dict[str, Any]:
    risk_percent = _get_float(params, "risk_percent", minimum=0, maximum=100)
    if risk_percent >= 20:
        risk_level = "高风险"
        interpretation = "ASCVD 十年风险较高，建议尽快进行综合危险因素干预。"
    elif risk_percent >= 7.5:
        risk_level = "中等风险"
        interpretation = "ASCVD 十年风险处于中间水平，建议结合血脂、血压和吸烟状况综合管理。"
    elif risk_percent >= 5:
        risk_level = "边缘升高"
        interpretation = "ASCVD 十年风险略有升高，建议加强生活方式管理。"
    else:
        risk_level = "低风险"
        interpretation = "当前 ASCVD 十年风险较低。"
    return _build_result(
        score=round(risk_percent, 1),
        risk_level=risk_level,
        summary=f"ASCVD 十年风险为 {round(risk_percent, 1)}%",
        interpretation=interpretation,
        reference="ASCVD 十年风险常用分层：<5% 低风险，5%-7.4% 边缘升高，7.5%-19.9% 中等风险，>=20% 高风险。",
        details={"calculator": "ascvd_10y", "risk_percent": risk_percent, "mode": "risk_percent_interpreter"},
    )


def calculate_timi(params: Dict[str, Any]) -> Dict[str, Any]:
    score = int(round(_score_from_total_or_items(params, maximum=14)))
    if score >= 5:
        risk_level = "高风险"
        interpretation = "TIMI 评分较高，提示急性冠脉事件风险升高，建议尽快接受专业评估。"
    elif score >= 3:
        risk_level = "中风险"
        interpretation = "TIMI 评分提示存在一定急性冠脉风险。"
    else:
        risk_level = "低风险"
        interpretation = "当前 TIMI 评分较低。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"TIMI 评分为 {score} 分",
        interpretation=interpretation,
        reference="TIMI 分数越高提示急性冠脉综合征近期不良事件风险越高。",
        details={"calculator": "timi", "total_score": score},
    )


def calculate_grace(params: Dict[str, Any]) -> Dict[str, Any]:
    if "risk_percent" in params and params["risk_percent"] not in (None, ""):
        risk_percent = _get_float(params, "risk_percent", minimum=0, maximum=100)
        if risk_percent >= 10:
            risk_level = "高风险"
            interpretation = "GRACE 风险较高，提示急性冠脉综合征预后风险升高。"
        elif risk_percent >= 3:
            risk_level = "中风险"
            interpretation = "GRACE 风险处于中间水平，建议尽快完善专科评估。"
        else:
            risk_level = "低风险"
            interpretation = "当前 GRACE 风险较低。"
        return _build_result(
            score=round(risk_percent, 1),
            risk_level=risk_level,
            summary=f"GRACE 风险为 {round(risk_percent, 1)}%",
            interpretation=interpretation,
            reference="GRACE 风险百分比越高提示急性冠脉综合征不良结局风险越高。",
            details={"calculator": "grace", "risk_percent": risk_percent, "mode": "risk_percent_interpreter"},
        )

    score = int(round(_get_float(params, "total_score", minimum=0, maximum=400)))
    if score > 140:
        risk_level = "高风险"
        interpretation = "GRACE 总分较高，提示急性冠脉综合征预后风险升高。"
    elif score >= 109:
        risk_level = "中风险"
        interpretation = "GRACE 总分提示中等风险，建议尽快完善评估。"
    else:
        risk_level = "低风险"
        interpretation = "当前 GRACE 总分较低。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"GRACE 总分为 {score} 分",
        interpretation=interpretation,
        reference="GRACE 常以 <109、109-140、>140 作为低中高风险参考分层。",
        details={"calculator": "grace", "total_score": score, "mode": "score_interpreter"},
    )


def calculate_qrisk3(params: Dict[str, Any]) -> Dict[str, Any]:
    risk_percent = _get_float(params, "risk_percent", minimum=0, maximum=100)
    if risk_percent >= 20:
        risk_level = "很高风险"
        interpretation = "QRISK3 风险百分比较高，提示未来心血管事件风险明显升高。"
    elif risk_percent >= 10:
        risk_level = "高风险"
        interpretation = "QRISK3 达到常用干预阈值，建议尽快评估综合危险因素管理。"
    else:
        risk_level = "低风险"
        interpretation = "当前 QRISK3 风险百分比较低。"
    return _build_result(
        score=round(risk_percent, 1),
        risk_level=risk_level,
        summary=f"QRISK3 十年风险为 {round(risk_percent, 1)}%",
        interpretation=interpretation,
        reference="QRISK3 常以 >=10% 作为干预参考阈值；本实现用于解释已获得的风险百分比。",
        details={"calculator": "qrisk3", "risk_percent": risk_percent, "mode": "risk_percent_interpreter"},
    )


def calculate_h2fpef(params: Dict[str, Any]) -> Dict[str, Any]:
    bmi = _get_float(params, "bmi", minimum=10, maximum=80)
    antihypertensive_count = int(round(_get_float(params, "antihypertensive_count", minimum=0, maximum=20)))
    atrial_fibrillation = _bool_value(params.get("atrial_fibrillation", False))
    pulmonary_artery_systolic_pressure = _get_float(params, "pulmonary_artery_systolic_pressure", minimum=1, maximum=200)
    age = _get_float(params, "age", minimum=0, maximum=120)
    e_over_e_prime = _get_float(params, "e_over_e_prime", minimum=0, maximum=100)

    score = 0
    score += 2 if bmi > 30 else 0
    score += 1 if antihypertensive_count >= 2 else 0
    score += 3 if atrial_fibrillation else 0
    score += 1 if pulmonary_artery_systolic_pressure > 35 else 0
    score += 1 if age > 60 else 0
    score += 1 if e_over_e_prime > 9 else 0

    if score >= 6:
        risk_level = "高概率"
        interpretation = "H2FPEF 评分提示 HFpEF 概率较高，建议尽快进行心脏专科评估。"
    elif score >= 2:
        risk_level = "中间概率"
        interpretation = "H2FPEF 评分处于中间区间，建议结合超声和临床表现进一步判断。"
    else:
        risk_level = "低概率"
        interpretation = "当前 H2FPEF 评分较低。"
    return _build_result(
        score=score,
        risk_level=risk_level,
        summary=f"H2FPEF 评分为 {score} 分",
        interpretation=interpretation,
        reference="H2FPEF 由肥胖、降压药数量、房颤、肺动脉压、年龄和 E/e' 组成，0-1 低概率，2-5 中间概率，6-9 高概率。",
        details={"calculator": "h2fpef", "bmi": bmi, "antihypertensive_count": antihypertensive_count, "atrial_fibrillation": atrial_fibrillation, "pulmonary_artery_systolic_pressure": pulmonary_artery_systolic_pressure, "age": age, "e_over_e_prime": e_over_e_prime},
    )
