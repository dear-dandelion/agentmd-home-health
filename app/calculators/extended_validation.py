from __future__ import annotations

from typing import Any


def _param(
    name: str,
    label: str,
    python_type: str,
    description: str,
    *,
    required: bool = True,
    minimum: float | None = None,
    maximum: float | None = None,
    unit: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": name,
        "label": label,
        "type": python_type,
        "required": required,
        "description": description,
    }
    if minimum is not None:
        payload["min"] = minimum
    if maximum is not None:
        payload["max"] = maximum
    if unit is not None:
        payload["unit"] = unit
    return payload


def _unit_case(
    name: str,
    input_data: dict[str, Any],
    risk_level: str,
    *,
    score: Any | None = None,
    summary_contains: str | None = None,
) -> dict[str, Any]:
    expected: dict[str, Any] = {"risk_level": risk_level}
    if score is not None:
        expected["score"] = score
    if summary_contains is not None:
        expected["summary_contains"] = summary_contains
    return {"name": name, "input": input_data, "expected": expected}


def _boundary_case(name: str, input_data: dict[str, Any], expected_risk_level: str) -> dict[str, Any]:
    return {"name": name, "input": input_data, "expected_risk_level": expected_risk_level}


def _score_validation(
    field: str,
    unit_rows: list[tuple[Any, str, Any | None]],
    boundary_rows: list[tuple[Any, str]],
) -> dict[str, Any]:
    unit_cases = [
        _unit_case(
            f"{field}_case_{index + 1}",
            {field: value},
            risk_level,
            score=value if score is None else score,
        )
        for index, (value, risk_level, score) in enumerate(unit_rows)
    ]
    boundary_checks = [
        _boundary_case(f"{field}_boundary_{index + 1}", {field: value}, risk_level)
        for index, (value, risk_level) in enumerate(boundary_rows)
    ]
    return {"unit_cases": unit_cases, "boundary_checks": boundary_checks}


EXTENDED_PARAMETER_OVERRIDES: dict[str, list[dict[str, Any]]] = {
    "cha2ds2_vasc": [
        _param("age", "年龄", "float", "受评估者年龄", minimum=0, maximum=120),
        _param("gender", "性别", "str", "男或女"),
        _param("congestive_heart_failure", "充血性心衰", "bool", "是否存在充血性心力衰竭"),
        _param("hypertension", "高血压", "bool", "是否存在高血压病史"),
        _param("diabetes", "糖尿病", "bool", "是否存在糖尿病"),
        _param("prior_stroke_tia_thromboembolism", "既往卒中/TIA/血栓栓塞", "bool", "是否存在既往卒中或TIA病史"),
        _param("vascular_disease", "血管疾病", "bool", "是否存在外周血管病或冠心病等血管疾病"),
    ],
    "has_bled": [
        _param("age", "年龄", "float", "受评估者年龄", minimum=0, maximum=120),
        _param("uncontrolled_hypertension", "未控制高血压", "bool", "是否存在未控制的高血压"),
        _param("abnormal_renal_function", "肾功能异常", "bool", "是否存在肾功能异常"),
        _param("abnormal_liver_function", "肝功能异常", "bool", "是否存在肝功能异常"),
        _param("prior_stroke", "既往卒中", "bool", "是否存在既往卒中病史"),
        _param("bleeding_history", "出血史", "bool", "是否存在重要出血史"),
        _param("labile_inr", "INR不稳定", "bool", "INR 是否不稳定"),
        _param("drugs_predisposing_bleeding", "易出血药物", "bool", "是否联合使用增加出血风险的药物"),
        _param("alcohol_excess", "过量饮酒", "bool", "是否存在过量饮酒"),
    ],
    "chads2": [
        _param("age", "年龄", "float", "受评估者年龄", minimum=0, maximum=120),
        _param("congestive_heart_failure", "充血性心衰", "bool", "是否存在充血性心力衰竭"),
        _param("hypertension", "高血压", "bool", "是否存在高血压"),
        _param("diabetes", "糖尿病", "bool", "是否存在糖尿病"),
        _param("prior_stroke_tia", "既往卒中/TIA", "bool", "是否存在既往卒中或 TIA"),
    ],
    "wells_dvt": [
        _param("active_cancer", "活动性肿瘤", "bool", "是否存在活动性肿瘤"),
        _param("paralysis_or_recent_cast", "瘫痪或下肢石膏", "bool", "是否存在瘫痪或近期下肢石膏固定"),
        _param("bedridden_or_recent_surgery", "卧床或近期手术", "bool", "是否长期卧床或近期手术"),
        _param("localized_tenderness", "局部压痛", "bool", "深静脉走行区是否存在压痛"),
        _param("entire_leg_swollen", "整条腿肿胀", "bool", "是否整条下肢肿胀"),
        _param("calf_swelling_gt_3cm", "小腿围差大于3cm", "bool", "是否存在小腿围差大于 3 cm"),
        _param("pitting_edema", "凹陷性水肿", "bool", "是否存在凹陷性水肿"),
        _param("collateral_superficial_veins", "浅表侧支静脉", "bool", "是否可见浅表侧支静脉"),
        _param("previous_dvt", "既往DVT", "bool", "是否存在既往 DVT 病史"),
        _param("alternative_diagnosis_more_likely", "其他诊断更可能", "bool", "是否有其他更可能解释当前表现的诊断"),
    ],
    "wells_pe": [
        _param("clinical_signs_dvt", "DVT体征", "bool", "是否存在深静脉血栓体征"),
        _param("pe_more_likely_than_alternative", "PE更可能", "bool", "肺栓塞是否比其他诊断更可能"),
        _param("heart_rate_bpm", "心率", "float", "当前心率", minimum=20, maximum=220, unit="次/分"),
        _param("immobilization_or_recent_surgery", "制动或近期手术", "bool", "是否近期制动或手术"),
        _param("previous_dvt_pe", "既往DVT/PE", "bool", "是否存在既往 DVT 或 PE"),
        _param("hemoptysis", "咯血", "bool", "是否存在咯血"),
        _param("malignancy", "恶性肿瘤", "bool", "是否存在恶性肿瘤"),
    ],
    "findrisc": [
        _param("age", "年龄", "float", "受评估者年龄", minimum=0, maximum=120),
        _param("bmi", "BMI", "float", "体重指数", minimum=10, maximum=80),
        _param("waist_cm", "腰围", "float", "腰围", minimum=30, maximum=200, unit="cm"),
        _param("gender", "性别", "str", "男或女"),
        _param("physically_active_daily", "日常体力活动", "bool", "是否每天进行至少 30 分钟体力活动"),
        _param("daily_fruits_vegetables", "每日蔬果", "bool", "是否每天摄入蔬菜水果"),
        _param("antihypertensive_medication", "降压药", "bool", "是否正在使用降压药"),
        _param("history_high_blood_glucose", "高血糖史", "bool", "是否存在高血糖病史"),
        _param("family_history_diabetes", "糖尿病家族史", "str", "none、second_degree 或 first_degree"),
    ],
    "nafld_fibrosis": [
        _param("age", "年龄", "float", "受评估者年龄", minimum=0, maximum=120),
        _param("bmi", "BMI", "float", "体重指数", minimum=10, maximum=80),
        _param("ast_u_l", "AST", "float", "谷草转氨酶", minimum=1, maximum=1000, unit="U/L"),
        _param("alt_u_l", "ALT", "float", "谷丙转氨酶", minimum=1, maximum=1000, unit="U/L"),
        _param("platelet_10e9_l", "血小板", "float", "血小板计数", minimum=1, maximum=1000, unit="10^9/L"),
        _param("albumin_g_dl", "白蛋白", "float", "白蛋白", minimum=0.1, maximum=10, unit="g/dL"),
        _param("impaired_fasting_glucose_or_diabetes", "糖调节异常/糖尿病", "bool", "是否存在糖调节异常或糖尿病"),
    ],
    "cdrs": [
        _param("age", "年龄", "float", "受评估者年龄", minimum=20, maximum=74),
        _param("bmi", "BMI", "float", "体重指数", minimum=10, maximum=80),
        _param("waist_cm", "腰围", "float", "腰围", minimum=30, maximum=200, unit="cm"),
        _param("systolic_bp", "收缩压", "float", "收缩压", minimum=50, maximum=300, unit="mmHg"),
        _param("gender", "性别", "str", "男或女"),
        _param("family_history_diabetes", "糖尿病家族史", "bool", "是否存在糖尿病家族史"),
    ],
    "h2fpef": [
        _param("bmi", "BMI", "float", "体重指数", minimum=10, maximum=80),
        _param("antihypertensive_count", "降压药数量", "int", "正在使用的降压药数量", minimum=0, maximum=20),
        _param("atrial_fibrillation", "房颤", "bool", "是否存在房颤"),
        _param("pulmonary_artery_systolic_pressure", "肺动脉收缩压", "float", "肺动脉收缩压", minimum=1, maximum=200, unit="mmHg"),
        _param("age", "年龄", "float", "受评估者年龄", minimum=0, maximum=120),
        _param("e_over_e_prime", "E/e'", "float", "超声 E/e' 比值", minimum=0, maximum=100),
    ],
}


EXTENDED_VALIDATION_OVERRIDES: dict[str, dict[str, Any]] = {
    "phq9": _score_validation(
        "total_score",
        [(0, "低风险", 0), (5, "轻度抑郁风险", 5), (10, "中度抑郁风险", 10), (20, "重度抑郁风险", 20)],
        [(4, "低风险"), (5, "轻度抑郁风险"), (14, "中度抑郁风险"), (15, "中重度抑郁风险"), (19, "中重度抑郁风险"), (20, "重度抑郁风险")],
    ),
    "gad7": _score_validation(
        "total_score",
        [(0, "低风险", 0), (5, "轻度焦虑风险", 5), (10, "中度焦虑风险", 10), (15, "重度焦虑风险", 15)],
        [(4, "低风险"), (5, "轻度焦虑风险"), (9, "轻度焦虑风险"), (10, "中度焦虑风险"), (14, "中度焦虑风险"), (15, "重度焦虑风险")],
    ),
    "qsofa": {
        "unit_cases": [
            _unit_case("baseline_low", {"respiratory_rate_bpm": 18, "systolic_bp": 120, "altered_mental_status": False}, "低风险", score=0),
            _unit_case("tachypnea_only", {"respiratory_rate_bpm": 24, "systolic_bp": 120, "altered_mental_status": False}, "中风险", score=1),
            _unit_case("tachypnea_and_hypotension", {"respiratory_rate_bpm": 24, "systolic_bp": 95, "altered_mental_status": False}, "高风险", score=2),
            _unit_case("all_three_positive", {"respiratory_rate_bpm": 24, "systolic_bp": 95, "altered_mental_status": True}, "高风险", score=3),
        ],
        "boundary_checks": [
            _boundary_case("resp_boundary_below", {"respiratory_rate_bpm": 21, "systolic_bp": 101, "altered_mental_status": False}, "低风险"),
            _boundary_case("resp_boundary_at", {"respiratory_rate_bpm": 22, "systolic_bp": 101, "altered_mental_status": False}, "中风险"),
            _boundary_case("bp_boundary_at", {"respiratory_rate_bpm": 22, "systolic_bp": 100, "altered_mental_status": False}, "高风险"),
            _boundary_case("mental_status_boundary", {"respiratory_rate_bpm": 21, "systolic_bp": 101, "altered_mental_status": True}, "中风险"),
        ],
    },
    "news2": {
        "unit_cases": [
            _unit_case("stable_case", {"respiratory_rate_bpm": 16, "oxygen_saturation": 97, "temperature_c": 36.8, "systolic_bp": 120, "heart_rate_bpm": 80, "consciousness": "A"}, "低风险", score=0),
            _unit_case("moderate_case", {"respiratory_rate_bpm": 22, "oxygen_saturation": 95, "temperature_c": 37.8, "systolic_bp": 108, "heart_rate_bpm": 105, "consciousness": "A"}, "中高风险", score=5),
            _unit_case("high_case", {"respiratory_rate_bpm": 24, "oxygen_saturation": 93, "temperature_c": 38.4, "systolic_bp": 96, "heart_rate_bpm": 118, "consciousness": "A"}, "高风险", score=9),
            _unit_case("critical_case", {"respiratory_rate_bpm": 25, "oxygen_saturation": 91, "supplemental_oxygen": True, "temperature_c": 38.5, "systolic_bp": 90, "heart_rate_bpm": 132, "consciousness": "V"}, "高风险", score=18),
        ],
        "boundary_checks": [
            _boundary_case("normal_case", {"respiratory_rate_bpm": 16, "oxygen_saturation": 97, "temperature_c": 36.8, "systolic_bp": 120, "heart_rate_bpm": 80, "consciousness": "A"}, "低风险"),
            _boundary_case("escalation_case", {"respiratory_rate_bpm": 22, "oxygen_saturation": 95, "temperature_c": 37.8, "systolic_bp": 108, "heart_rate_bpm": 105, "consciousness": "A"}, "中高风险"),
            _boundary_case("high_case", {"respiratory_rate_bpm": 24, "oxygen_saturation": 93, "temperature_c": 38.4, "systolic_bp": 96, "heart_rate_bpm": 118, "consciousness": "A"}, "高风险"),
        ],
    },
    "barthel_index": _score_validation(
        "total_score",
        [(10, "完全依赖", 10), (30, "重度依赖", 30), (70, "中度依赖", 70), (100, "独立", 100)],
        [(20, "完全依赖"), (21, "重度依赖"), (60, "重度依赖"), (61, "中度依赖"), (90, "中度依赖"), (91, "轻度依赖"), (99, "轻度依赖"), (100, "独立")],
    ),
    "pain_nrs": _score_validation(
        "total_score",
        [(0, "无明显疼痛", 0), (2, "轻度疼痛", 2), (5, "中度疼痛", 5), (8, "重度疼痛", 8)],
        [(0, "无明显疼痛"), (1, "轻度疼痛"), (3, "轻度疼痛"), (4, "中度疼痛"), (6, "中度疼痛"), (7, "重度疼痛")],
    ),
    "mmrc": _score_validation(
        "grade",
        [(0, "低症状负担", 0), (2, "中等症状负担", 2), (3, "高症状负担", 3), (4, "高症状负担", 4)],
        [(1, "低症状负担"), (2, "中等症状负担"), (3, "高症状负担")],
    ),
    "cat": _score_validation(
        "total_score",
        [(5, "低症状负担", 5), (15, "中等症状负担", 15), (25, "高症状负担", 25), (35, "极高症状负担", 35)],
        [(9, "低症状负担"), (10, "中等症状负担"), (20, "中等症状负担"), (21, "高症状负担"), (30, "高症状负担"), (31, "极高症状负担")],
    ),
    "cha2ds2_vasc": {
        "unit_cases": [
            _unit_case("male_zero", {"age": 50, "gender": "male", "congestive_heart_failure": False, "hypertension": False, "diabetes": False, "prior_stroke_tia_thromboembolism": False, "vascular_disease": False}, "低风险", score=0),
            _unit_case("male_age_65", {"age": 66, "gender": "male", "congestive_heart_failure": False, "hypertension": False, "diabetes": False, "prior_stroke_tia_thromboembolism": False, "vascular_disease": False}, "中风险", score=1),
            _unit_case("multiple_factors", {"age": 76, "gender": "male", "congestive_heart_failure": True, "hypertension": True, "diabetes": False, "prior_stroke_tia_thromboembolism": False, "vascular_disease": False}, "高风险", score=4),
            _unit_case("female_very_high", {"age": 78, "gender": "female", "congestive_heart_failure": True, "hypertension": True, "diabetes": True, "prior_stroke_tia_thromboembolism": True, "vascular_disease": True}, "高风险", score=9),
        ],
        "boundary_checks": [
            _boundary_case("female_sex_only", {"age": 40, "gender": "female", "congestive_heart_failure": False, "hypertension": False, "diabetes": False, "prior_stroke_tia_thromboembolism": False, "vascular_disease": False}, "低风险"),
            _boundary_case("age_65_boundary", {"age": 65, "gender": "male", "congestive_heart_failure": False, "hypertension": False, "diabetes": False, "prior_stroke_tia_thromboembolism": False, "vascular_disease": False}, "中风险"),
            _boundary_case("age_75_boundary", {"age": 75, "gender": "male", "congestive_heart_failure": False, "hypertension": False, "diabetes": False, "prior_stroke_tia_thromboembolism": False, "vascular_disease": False}, "高风险"),
        ],
    },
    "has_bled": {
        "unit_cases": [
            _unit_case("all_negative", {"age": 50, "uncontrolled_hypertension": False, "abnormal_renal_function": False, "abnormal_liver_function": False, "prior_stroke": False, "bleeding_history": False, "labile_inr": False, "drugs_predisposing_bleeding": False, "alcohol_excess": False}, "低风险", score=0),
            _unit_case("moderate_case", {"age": 70, "uncontrolled_hypertension": True, "abnormal_renal_function": False, "abnormal_liver_function": False, "prior_stroke": False, "bleeding_history": False, "labile_inr": False, "drugs_predisposing_bleeding": False, "alcohol_excess": False}, "中风险", score=2),
            _unit_case("high_case", {"age": 72, "uncontrolled_hypertension": True, "abnormal_renal_function": True, "abnormal_liver_function": False, "prior_stroke": True, "bleeding_history": False, "labile_inr": False, "drugs_predisposing_bleeding": False, "alcohol_excess": False}, "高风险", score=4),
            _unit_case("maximal_case", {"age": 80, "uncontrolled_hypertension": True, "abnormal_renal_function": True, "abnormal_liver_function": True, "prior_stroke": True, "bleeding_history": True, "labile_inr": True, "drugs_predisposing_bleeding": True, "alcohol_excess": True}, "高风险", score=9),
        ],
        "boundary_checks": [
            _boundary_case("low_case", {"age": 50, "uncontrolled_hypertension": False, "abnormal_renal_function": False, "abnormal_liver_function": False, "prior_stroke": False, "bleeding_history": False, "labile_inr": False, "drugs_predisposing_bleeding": False, "alcohol_excess": False}, "低风险"),
            _boundary_case("medium_case", {"age": 70, "uncontrolled_hypertension": True, "abnormal_renal_function": False, "abnormal_liver_function": False, "prior_stroke": False, "bleeding_history": False, "labile_inr": False, "drugs_predisposing_bleeding": False, "alcohol_excess": False}, "中风险"),
            _boundary_case("high_case", {"age": 72, "uncontrolled_hypertension": True, "abnormal_renal_function": True, "abnormal_liver_function": False, "prior_stroke": True, "bleeding_history": False, "labile_inr": False, "drugs_predisposing_bleeding": False, "alcohol_excess": False}, "高风险"),
        ],
    },
    "chads2": {
        "unit_cases": [
            _unit_case("zero_score", {"age": 50, "congestive_heart_failure": False, "hypertension": False, "diabetes": False, "prior_stroke_tia": False}, "低风险", score=0),
            _unit_case("age_only", {"age": 76, "congestive_heart_failure": False, "hypertension": False, "diabetes": False, "prior_stroke_tia": False}, "中风险", score=1),
            _unit_case("three_points", {"age": 76, "congestive_heart_failure": False, "hypertension": True, "diabetes": True, "prior_stroke_tia": False}, "高风险", score=3),
            _unit_case("max_case", {"age": 76, "congestive_heart_failure": True, "hypertension": True, "diabetes": True, "prior_stroke_tia": True}, "高风险", score=6),
        ],
        "boundary_checks": [
            _boundary_case("age_74", {"age": 74, "congestive_heart_failure": False, "hypertension": False, "diabetes": False, "prior_stroke_tia": False}, "低风险"),
            _boundary_case("age_75", {"age": 75, "congestive_heart_failure": False, "hypertension": False, "diabetes": False, "prior_stroke_tia": False}, "中风险"),
            _boundary_case("high_risk_case", {"age": 76, "congestive_heart_failure": False, "hypertension": True, "diabetes": True, "prior_stroke_tia": False}, "高风险"),
        ],
    },
    "wells_dvt": {
        "unit_cases": [
            _unit_case("alternative_more_likely", {"active_cancer": False, "paralysis_or_recent_cast": False, "bedridden_or_recent_surgery": False, "localized_tenderness": False, "entire_leg_swollen": False, "calf_swelling_gt_3cm": False, "pitting_edema": False, "collateral_superficial_veins": False, "previous_dvt": False, "alternative_diagnosis_more_likely": True}, "低风险", score=-2.0),
            _unit_case("intermediate_case", {"active_cancer": False, "paralysis_or_recent_cast": False, "bedridden_or_recent_surgery": True, "localized_tenderness": True, "entire_leg_swollen": False, "calf_swelling_gt_3cm": False, "pitting_edema": False, "collateral_superficial_veins": False, "previous_dvt": False, "alternative_diagnosis_more_likely": False}, "中风险", score=2.0),
            _unit_case("high_case", {"active_cancer": False, "paralysis_or_recent_cast": False, "bedridden_or_recent_surgery": True, "localized_tenderness": True, "entire_leg_swollen": True, "calf_swelling_gt_3cm": True, "pitting_edema": True, "collateral_superficial_veins": False, "previous_dvt": False, "alternative_diagnosis_more_likely": False}, "高风险", score=5.0),
            _unit_case("very_high_case", {"active_cancer": True, "paralysis_or_recent_cast": True, "bedridden_or_recent_surgery": True, "localized_tenderness": True, "entire_leg_swollen": True, "calf_swelling_gt_3cm": True, "pitting_edema": True, "collateral_superficial_veins": True, "previous_dvt": True, "alternative_diagnosis_more_likely": False}, "高风险", score=9.0),
        ],
        "boundary_checks": [
            _boundary_case("score_below_zero", {"active_cancer": False, "paralysis_or_recent_cast": False, "bedridden_or_recent_surgery": False, "localized_tenderness": False, "entire_leg_swollen": False, "calf_swelling_gt_3cm": False, "pitting_edema": False, "collateral_superficial_veins": False, "previous_dvt": False, "alternative_diagnosis_more_likely": True}, "低风险"),
            _boundary_case("score_two", {"active_cancer": False, "paralysis_or_recent_cast": False, "bedridden_or_recent_surgery": True, "localized_tenderness": True, "entire_leg_swollen": False, "calf_swelling_gt_3cm": False, "pitting_edema": False, "collateral_superficial_veins": False, "previous_dvt": False, "alternative_diagnosis_more_likely": False}, "中风险"),
            _boundary_case("score_five", {"active_cancer": False, "paralysis_or_recent_cast": False, "bedridden_or_recent_surgery": True, "localized_tenderness": True, "entire_leg_swollen": True, "calf_swelling_gt_3cm": True, "pitting_edema": True, "collateral_superficial_veins": False, "previous_dvt": False, "alternative_diagnosis_more_likely": False}, "高风险"),
        ],
    },
    "wells_pe": {
        "unit_cases": [
            _unit_case("zero_score", {"clinical_signs_dvt": False, "pe_more_likely_than_alternative": False, "heart_rate_bpm": 80, "immobilization_or_recent_surgery": False, "previous_dvt_pe": False, "hemoptysis": False, "malignancy": False}, "低风险", score=0.0),
            _unit_case("intermediate_case", {"clinical_signs_dvt": True, "pe_more_likely_than_alternative": False, "heart_rate_bpm": 105, "immobilization_or_recent_surgery": False, "previous_dvt_pe": False, "hemoptysis": False, "malignancy": False}, "中风险", score=4.5),
            _unit_case("high_case", {"clinical_signs_dvt": True, "pe_more_likely_than_alternative": True, "heart_rate_bpm": 118, "immobilization_or_recent_surgery": False, "previous_dvt_pe": False, "hemoptysis": False, "malignancy": False}, "高风险", score=7.5),
            _unit_case("very_high_case", {"clinical_signs_dvt": True, "pe_more_likely_than_alternative": True, "heart_rate_bpm": 118, "immobilization_or_recent_surgery": True, "previous_dvt_pe": True, "hemoptysis": True, "malignancy": True}, "高风险", score=12.5),
        ],
        "boundary_checks": [
            _boundary_case("low_case", {"clinical_signs_dvt": False, "pe_more_likely_than_alternative": False, "heart_rate_bpm": 80, "immobilization_or_recent_surgery": False, "previous_dvt_pe": False, "hemoptysis": False, "malignancy": False}, "低风险"),
            _boundary_case("intermediate_case", {"clinical_signs_dvt": True, "pe_more_likely_than_alternative": False, "heart_rate_bpm": 105, "immobilization_or_recent_surgery": False, "previous_dvt_pe": False, "hemoptysis": False, "malignancy": False}, "中风险"),
            _boundary_case("high_case", {"clinical_signs_dvt": True, "pe_more_likely_than_alternative": True, "heart_rate_bpm": 118, "immobilization_or_recent_surgery": False, "previous_dvt_pe": False, "hemoptysis": False, "malignancy": False}, "高风险"),
        ],
    },
    "heart_score": {
        "unit_cases": [
            _unit_case("formula_low", {"history_score": 0, "ecg_score": 0, "troponin_score": 0, "age": 35, "risk_factor_count": 0}, "低风险", score=0),
            _unit_case("middle_total_score", {"total_score": 5}, "中风险", score=5),
            _unit_case("formula_high", {"history_score": 2, "ecg_score": 1, "troponin_score": 1, "age": 67, "risk_factor_count": 3}, "高风险", score=8),
            _unit_case("very_high_total_score", {"total_score": 7}, "高风险", score=7),
        ],
        "boundary_checks": [
            _boundary_case("score_three", {"total_score": 3}, "低风险"),
            _boundary_case("score_four", {"total_score": 4}, "中风险"),
            _boundary_case("score_six", {"total_score": 6}, "中风险"),
            _boundary_case("score_seven", {"total_score": 7}, "高风险"),
        ],
    },
    "findrisc": {
        "unit_cases": [
            _unit_case("low_case", {"age": 45, "bmi": 24, "waist_cm": 90, "gender": "male", "physically_active_daily": True, "daily_fruits_vegetables": True, "antihypertensive_medication": False, "history_high_blood_glucose": False, "family_history_diabetes": "none"}, "低风险", score=2),
            _unit_case("mild_case", {"age": 45, "bmi": 24, "waist_cm": 90, "gender": "male", "physically_active_daily": True, "daily_fruits_vegetables": True, "antihypertensive_medication": False, "history_high_blood_glucose": False, "family_history_diabetes": "first_degree"}, "轻中度风险", score=7),
            _unit_case("medium_case", {"age": 45, "bmi": 24, "waist_cm": 90, "gender": "male", "physically_active_daily": True, "daily_fruits_vegetables": True, "antihypertensive_medication": False, "history_high_blood_glucose": True, "family_history_diabetes": "first_degree"}, "中风险", score=12),
            _unit_case("high_case", {"age": 45, "bmi": 24, "waist_cm": 90, "gender": "male", "physically_active_daily": True, "daily_fruits_vegetables": False, "antihypertensive_medication": True, "history_high_blood_glucose": True, "family_history_diabetes": "first_degree"}, "高风险", score=15),
        ],
        "boundary_checks": [
            _boundary_case("score_two", {"age": 45, "bmi": 24, "waist_cm": 90, "gender": "male", "physically_active_daily": True, "daily_fruits_vegetables": True, "antihypertensive_medication": False, "history_high_blood_glucose": False, "family_history_diabetes": "none"}, "低风险"),
            _boundary_case("score_seven", {"age": 45, "bmi": 24, "waist_cm": 90, "gender": "male", "physically_active_daily": True, "daily_fruits_vegetables": True, "antihypertensive_medication": False, "history_high_blood_glucose": False, "family_history_diabetes": "first_degree"}, "轻中度风险"),
            _boundary_case("score_twelve", {"age": 45, "bmi": 24, "waist_cm": 90, "gender": "male", "physically_active_daily": True, "daily_fruits_vegetables": True, "antihypertensive_medication": False, "history_high_blood_glucose": True, "family_history_diabetes": "first_degree"}, "中风险"),
            _boundary_case("score_fifteen", {"age": 45, "bmi": 24, "waist_cm": 90, "gender": "male", "physically_active_daily": True, "daily_fruits_vegetables": False, "antihypertensive_medication": True, "history_high_blood_glucose": True, "family_history_diabetes": "first_degree"}, "高风险"),
        ],
    },
    "metabolic_syndrome": {
        "unit_cases": [
            _unit_case("all_normal", {"waist_cm": 80, "gender": "female", "systolic_bp": 118, "diastolic_bp": 76, "fasting_glucose": 5.0, "triglycerides_mmol_l": 1.0, "hdl_mmol_l": 1.5}, "未达到代谢综合征标准", score=0),
            _unit_case("central_obesity_only", {"waist_cm": 86, "gender": "female", "systolic_bp": 118, "diastolic_bp": 76, "fasting_glucose": 5.0, "triglycerides_mmol_l": 1.0, "hdl_mmol_l": 1.5}, "未达到代谢综合征标准", score=1),
            _unit_case("meets_criteria", {"waist_cm": 86, "gender": "female", "systolic_bp": 135, "diastolic_bp": 86, "fasting_glucose": 5.8, "triglycerides_mmol_l": 1.8, "hdl_mmol_l": 1.0}, "符合代谢综合征", score=5),
            _unit_case("severe_case", {"waist_cm": 98, "gender": "male", "systolic_bp": 142, "diastolic_bp": 92, "fasting_glucose": 7.2, "triglycerides_mmol_l": 2.6, "hdl_mmol_l": 0.8}, "符合代谢综合征", score=5),
        ],
        "boundary_checks": [
            _boundary_case("central_obesity_boundary", {"waist_cm": 85, "gender": "female", "systolic_bp": 118, "diastolic_bp": 76, "fasting_glucose": 5.0, "triglycerides_mmol_l": 1.0, "hdl_mmol_l": 1.5}, "未达到代谢综合征标准"),
            _boundary_case("central_obesity_cross", {"waist_cm": 86, "gender": "female", "systolic_bp": 118, "diastolic_bp": 76, "fasting_glucose": 5.0, "triglycerides_mmol_l": 1.0, "hdl_mmol_l": 1.5}, "未达到代谢综合征标准"),
            _boundary_case("diagnostic_case", {"waist_cm": 86, "gender": "female", "systolic_bp": 135, "diastolic_bp": 86, "fasting_glucose": 5.8, "triglycerides_mmol_l": 1.8, "hdl_mmol_l": 1.0}, "符合代谢综合征"),
        ],
    },
    "nafld_fibrosis": {
        "unit_cases": [
            _unit_case("low_case", {"age": 35, "bmi": 22, "ast_u_l": 20, "alt_u_l": 30, "platelet_10e9_l": 300, "albumin_g_dl": 4.5, "impaired_fasting_glucose_or_diabetes": False}, "低风险", score=-4.522),
            _unit_case("uncertain_case", {"age": 55, "bmi": 29, "ast_u_l": 30, "alt_u_l": 35, "platelet_10e9_l": 200, "albumin_g_dl": 4.1, "impaired_fasting_glucose_or_diabetes": False}, "不确定风险", score=-1.371),
            _unit_case("high_case", {"age": 58, "bmi": 31.2, "ast_u_l": 42, "alt_u_l": 35, "platelet_10e9_l": 180, "albumin_g_dl": 4.0, "impaired_fasting_glucose_or_diabetes": True}, "高风险", score=0.742),
            _unit_case("very_high_case", {"age": 70, "bmi": 34, "ast_u_l": 80, "alt_u_l": 45, "platelet_10e9_l": 110, "albumin_g_dl": 3.2, "impaired_fasting_glucose_or_diabetes": True}, "高风险", score=3.459),
        ],
        "boundary_checks": [
            _boundary_case("low_case", {"age": 35, "bmi": 22, "ast_u_l": 20, "alt_u_l": 30, "platelet_10e9_l": 300, "albumin_g_dl": 4.5, "impaired_fasting_glucose_or_diabetes": False}, "低风险"),
            _boundary_case("uncertain_case", {"age": 55, "bmi": 29, "ast_u_l": 30, "alt_u_l": 35, "platelet_10e9_l": 200, "albumin_g_dl": 4.1, "impaired_fasting_glucose_or_diabetes": False}, "不确定风险"),
            _boundary_case("high_case", {"age": 58, "bmi": 31.2, "ast_u_l": 42, "alt_u_l": 35, "platelet_10e9_l": 180, "albumin_g_dl": 4.0, "impaired_fasting_glucose_or_diabetes": True}, "高风险"),
        ],
    },
    "morse_fall_scale": _score_validation(
        "total_score",
        [(10, "低风险", 10), (30, "中风险", 30), (50, "高风险", 50), (70, "高风险", 70)],
        [(24, "低风险"), (25, "中风险"), (44, "中风险"), (45, "高风险")],
    ),
    "braden_scale": _score_validation(
        "total_score",
        [(20, "低风险", 20), (17, "轻度风险", 17), (12, "高风险", 12), (9, "极高风险", 9)],
        [(18, "轻度风险"), (19, "低风险"), (14, "中风险"), (15, "轻度风险"), (12, "高风险"), (13, "中风险"), (9, "极高风险"), (10, "高风险")],
    ),
    "mna_sf": _score_validation(
        "total_score",
        [(13, "营养状态正常", 13), (11, "营养不良风险", 11), (9, "营养不良风险", 9), (7, "营养不良", 7)],
        [(7, "营养不良"), (8, "营养不良风险"), (11, "营养不良风险"), (12, "营养状态正常")],
    ),
    "gds15": _score_validation(
        "total_score",
        [(2, "低风险", 2), (7, "轻度抑郁风险", 7), (10, "中度抑郁风险", 10), (13, "重度抑郁风险", 13)],
        [(4, "低风险"), (5, "轻度抑郁风险"), (8, "轻度抑郁风险"), (9, "中度抑郁风险"), (11, "中度抑郁风险"), (12, "重度抑郁风险")],
    ),
    "tug_test": _score_validation(
        "time_seconds",
        [(9.0, "低跌倒风险", 9.0), (11.0, "中等跌倒风险", 11.0), (14.0, "高跌倒风险", 14.0), (20.0, "高跌倒风险", 20.0)],
        [(9.9, "低跌倒风险"), (10.0, "中等跌倒风险"), (13.4, "中等跌倒风险"), (13.5, "高跌倒风险")],
    ),
    "ad8": _score_validation(
        "total_score",
        [(1, "低风险", 1), (2, "认知异常风险", 2), (4, "认知异常风险", 4), (6, "认知异常风险", 6)],
        [(1, "低风险"), (2, "认知异常风险")],
    ),
    "mini_cog": {
        "unit_cases": [
            _unit_case("recall3_clock_ok", {"recall_score": 3, "clock_normal": True}, "低风险", score=5),
            _unit_case("recall2_clock_ok", {"recall_score": 2, "clock_normal": True}, "低风险", score=4),
            _unit_case("recall2_clock_bad", {"recall_score": 2, "clock_normal": False}, "认知异常风险", score=2),
            _unit_case("recall0_clock_bad", {"recall_score": 0, "clock_normal": False}, "认知异常风险", score=0),
        ],
        "boundary_checks": [
            _boundary_case("clock_changes_result", {"recall_score": 2, "clock_normal": True}, "低风险"),
            _boundary_case("clock_abnormal", {"recall_score": 2, "clock_normal": False}, "认知异常风险"),
            _boundary_case("zero_recall", {"recall_score": 0, "clock_normal": True}, "认知异常风险"),
        ],
    },
    "fried_frailty": _score_validation(
        "total_score",
        [(0, "非衰弱", 0), (1, "衰弱前期", 1), (2, "衰弱前期", 2), (3, "衰弱", 3)],
        [(0, "非衰弱"), (1, "衰弱前期"), (2, "衰弱前期"), (3, "衰弱")],
    ),
    "lawton_iadl": _score_validation(
        "total_score",
        [(8, "独立", 8), (6, "轻度依赖", 6), (4, "中度依赖", 4), (2, "重度依赖", 2)],
        [(2, "重度依赖"), (3, "中度依赖"), (5, "中度依赖"), (6, "轻度依赖"), (7, "轻度依赖"), (8, "独立")],
    ),
    "sarc_f": _score_validation(
        "total_score",
        [(2, "低风险", 2), (3, "低风险", 3), (4, "肌少症风险", 4), (8, "肌少症风险", 8)],
        [(3, "低风险"), (4, "肌少症风险")],
    ),
    "rockwood_cfs": _score_validation(
        "grade",
        [(2, "较稳定", 2), (4, "脆弱", 4), (5, "衰弱", 5), (7, "重度衰弱", 7)],
        [(3, "较稳定"), (4, "脆弱"), (5, "衰弱"), (6, "衰弱"), (7, "重度衰弱")],
    ),
    "karnofsky_ps": _score_validation(
        "total_score",
        [(90, "功能状态较好", 90), (70, "中度功能受限", 70), (50, "中度功能受限", 50), (20, "重度功能受限", 20)],
        [(49, "重度功能受限"), (50, "中度功能受限"), (79, "中度功能受限"), (80, "功能状态较好")],
    ),
    "cdrs": {
        "unit_cases": [
            _unit_case("low_case", {"age": 25, "bmi": 21, "waist_cm": 74, "systolic_bp": 108, "gender": "male", "family_history_diabetes": False}, "低风险", score=6),
            _unit_case("middle_case", {"age": 25, "bmi": 21, "waist_cm": 78, "systolic_bp": 138, "gender": "male", "family_history_diabetes": True}, "中风险", score=21),
            _unit_case("high_boundary_case", {"age": 25, "bmi": 21, "waist_cm": 86, "systolic_bp": 138, "gender": "male", "family_history_diabetes": True}, "高风险", score=25),
            _unit_case("high_case", {"age": 58, "bmi": 28, "waist_cm": 92, "systolic_bp": 142, "gender": "male", "family_history_diabetes": True}, "高风险", score=41),
        ],
        "boundary_checks": [
            _boundary_case("score_19_low", {"age": 25, "bmi": 21, "waist_cm": 74, "systolic_bp": 138, "gender": "male", "family_history_diabetes": True}, "低风险"),
            _boundary_case("score_21_middle", {"age": 25, "bmi": 21, "waist_cm": 78, "systolic_bp": 138, "gender": "male", "family_history_diabetes": True}, "中风险"),
            _boundary_case("score_25_high", {"age": 25, "bmi": 21, "waist_cm": 86, "systolic_bp": 138, "gender": "male", "family_history_diabetes": True}, "高风险"),
        ],
    },
    "nihss": _score_validation(
        "total_score",
        [(0, "无明显缺损", 0), (2, "轻度神经功能缺损", 2), (8, "中度神经功能缺损", 8), (18, "中重度神经功能缺损", 18)],
        [(0, "无明显缺损"), (1, "轻度神经功能缺损"), (4, "轻度神经功能缺损"), (5, "中度神经功能缺损"), (15, "中度神经功能缺损"), (16, "中重度神经功能缺损"), (20, "中重度神经功能缺损"), (21, "重度神经功能缺损")],
    ),
    "glasgow_coma_scale": _score_validation(
        "gcs_score",
        [(15, "轻度或无明显意识障碍", 15), (12, "中度意识障碍", 12), (8, "重度意识障碍", 8), (7, "重度意识障碍", 7)],
        [(8, "重度意识障碍"), (9, "中度意识障碍"), (12, "中度意识障碍"), (13, "轻度或无明显意识障碍")],
    ),
    "must": {
        "unit_cases": [
            _unit_case("score_zero", {"total_score": 0}, "低营养风险", score=0),
            _unit_case("score_one", {"total_score": 1}, "中营养风险", score=1),
            _unit_case("score_two", {"total_score": 2}, "高营养风险", score=2),
            _unit_case("derived_case", {"bmi": 17.8, "weight_loss_percent": 12, "acute_disease_effect": True}, "高营养风险", score=6),
        ],
        "boundary_checks": [
            _boundary_case("score_zero", {"total_score": 0}, "低营养风险"),
            _boundary_case("score_one", {"total_score": 1}, "中营养风险"),
            _boundary_case("score_two", {"total_score": 2}, "高营养风险"),
            _boundary_case("derived_case", {"bmi": 17.8, "weight_loss_percent": 12, "acute_disease_effect": True}, "高营养风险"),
        ],
    },
    "caprini_vte": _score_validation(
        "total_score",
        [(1, "低风险", 1), (2, "中风险", 2), (3, "高风险", 3), (5, "极高风险", 5)],
        [(1, "低风险"), (2, "中风险"), (3, "高风险"), (4, "高风险"), (5, "极高风险")],
    ),
    "mews": {
        "unit_cases": [
            _unit_case("score_one", {"total_score": 1}, "低风险", score=1),
            _unit_case("score_three", {"total_score": 3}, "中风险", score=3),
            _unit_case("score_five", {"total_score": 5}, "高风险", score=5),
            _unit_case("derived_case", {"respiratory_rate_bpm": 32, "temperature_c": 39.1, "systolic_bp": 78, "heart_rate_bpm": 138, "consciousness": "V"}, "高风险", score=13),
        ],
        "boundary_checks": [
            _boundary_case("score_two", {"total_score": 2}, "低风险"),
            _boundary_case("score_three", {"total_score": 3}, "中风险"),
            _boundary_case("score_four", {"total_score": 4}, "中风险"),
            _boundary_case("score_five", {"total_score": 5}, "高风险"),
        ],
    },
    "charlson_cci": _score_validation(
        "total_score",
        [(1, "低合并症负担", 1), (3, "中等合并症负担", 3), (5, "高合并症负担", 5), (8, "高合并症负担", 8)],
        [(2, "低合并症负担"), (3, "中等合并症负担"), (4, "中等合并症负担"), (5, "高合并症负担")],
    ),
    "norton_scale": _score_validation(
        "total_score",
        [(18, "低风险", 18), (14, "中风险", 14), (12, "高压疮风险", 12), (9, "高压疮风险", 9)],
        [(12, "高压疮风险"), (13, "中风险"), (14, "中风险"), (15, "低风险")],
    ),
    "waterlow_score": _score_validation(
        "total_score",
        [(8, "低风险", 8), (12, "有压疮风险", 12), (16, "高压疮风险", 16), (22, "极高压疮风险", 22)],
        [(9, "低风险"), (10, "有压疮风险"), (14, "有压疮风险"), (15, "高压疮风险"), (19, "高压疮风险"), (20, "极高压疮风险")],
    ),
    "ascvd_10y": _score_validation(
        "risk_percent",
        [(3.0, "低风险", 3.0), (5.0, "边缘升高", 5.0), (7.5, "中等风险", 7.5), (20.0, "高风险", 20.0)],
        [(4.9, "低风险"), (5.0, "边缘升高"), (7.4, "边缘升高"), (7.5, "中等风险"), (19.9, "中等风险"), (20.0, "高风险")],
    ),
    "timi": _score_validation(
        "total_score",
        [(1, "低风险", 1), (3, "中风险", 3), (5, "高风险", 5), (7, "高风险", 7)],
        [(2, "低风险"), (3, "中风险"), (4, "中风险"), (5, "高风险")],
    ),
    "grace": {
        "unit_cases": [
            _unit_case("score_low", {"total_score": 80}, "低风险", score=80),
            _unit_case("score_middle", {"total_score": 109}, "中风险", score=109),
            _unit_case("score_high", {"total_score": 150}, "高风险", score=150),
            _unit_case("percent_high", {"risk_percent": 10.0}, "高风险", score=10.0),
        ],
        "boundary_checks": [
            _boundary_case("score_108", {"total_score": 108}, "低风险"),
            _boundary_case("score_109", {"total_score": 109}, "中风险"),
            _boundary_case("score_140", {"total_score": 140}, "中风险"),
            _boundary_case("score_141", {"total_score": 141}, "高风险"),
            _boundary_case("percent_2_9", {"risk_percent": 2.9}, "低风险"),
            _boundary_case("percent_3_0", {"risk_percent": 3.0}, "中风险"),
            _boundary_case("percent_10_0", {"risk_percent": 10.0}, "高风险"),
        ],
    },
    "qrisk3": _score_validation(
        "risk_percent",
        [(5.0, "低风险", 5.0), (10.0, "高风险", 10.0), (11.2, "高风险", 11.2), (20.0, "很高风险", 20.0)],
        [(9.9, "低风险"), (10.0, "高风险"), (19.9, "高风险"), (20.0, "很高风险")],
    ),
    "h2fpef": {
        "unit_cases": [
            _unit_case("low_case", {"bmi": 24, "antihypertensive_count": 0, "atrial_fibrillation": False, "pulmonary_artery_systolic_pressure": 28, "age": 50, "e_over_e_prime": 8}, "低概率", score=0),
            _unit_case("middle_case", {"bmi": 31, "antihypertensive_count": 1, "atrial_fibrillation": False, "pulmonary_artery_systolic_pressure": 36, "age": 62, "e_over_e_prime": 10}, "中间概率", score=5),
            _unit_case("high_case", {"bmi": 32.1, "antihypertensive_count": 2, "atrial_fibrillation": True, "pulmonary_artery_systolic_pressure": 42, "age": 68, "e_over_e_prime": 12}, "高概率", score=9),
            _unit_case("very_high_case", {"bmi": 36, "antihypertensive_count": 3, "atrial_fibrillation": True, "pulmonary_artery_systolic_pressure": 55, "age": 78, "e_over_e_prime": 18}, "高概率", score=9),
        ],
        "boundary_checks": [
            _boundary_case("score_zero", {"bmi": 24, "antihypertensive_count": 0, "atrial_fibrillation": False, "pulmonary_artery_systolic_pressure": 28, "age": 50, "e_over_e_prime": 8}, "低概率"),
            _boundary_case("score_five", {"bmi": 31, "antihypertensive_count": 1, "atrial_fibrillation": False, "pulmonary_artery_systolic_pressure": 36, "age": 62, "e_over_e_prime": 10}, "中间概率"),
            _boundary_case("score_six_plus", {"bmi": 32.1, "antihypertensive_count": 2, "atrial_fibrillation": True, "pulmonary_artery_systolic_pressure": 42, "age": 68, "e_over_e_prime": 12}, "高概率"),
        ],
    },
}
