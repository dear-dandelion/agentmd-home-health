const state = {
  users: [],
  currentUserId: null,
  currentUser: null,
  dialogState: {},
  busy: false,
  summaryCollapsed: false,
};

const chatStreamEl = document.getElementById("chat-stream");
const messageInputEl = document.getElementById("message-input");
const actionStatusEl = document.getElementById("action-status");
const summaryMetricsEl = document.getElementById("summary-metrics");
const summarySmokingEl = document.getElementById("summary-smoking");
const currentAvatarEl = document.getElementById("current-avatar");
const currentUserNameEl = document.getElementById("current-user-name");
const currentUserTagEl = document.getElementById("current-user-tag");
const overlayEl = document.getElementById("setup-overlay");
const overlayUserSelectEl = document.getElementById("overlay-user-select");
const userDropdownEl = document.getElementById("user-dropdown");
const userPickerWrapEl = document.getElementById("user-picker-wrap");
const userPickerTriggerEl = document.getElementById("user-picker-trigger");
const historyContainerEl = document.getElementById("history-container");
const detailsContainerEl = document.getElementById("details-container");
const sidebarTimeEl = document.getElementById("sidebar-time");
const todayTextEl = document.getElementById("today-text");
const sendButtonEl = document.getElementById("send-button");

document.addEventListener("DOMContentLoaded", async () => {
  renderTime();
  bindEvents();
  resetCurrentUser();
  await loadUsers();
});

function bindEvents() {
  document.getElementById("open-create-modal").addEventListener("click", () => openModal("create-modal"));
  document.getElementById("open-create-modal-overlay").addEventListener("click", () => openModal("create-modal"));
  document.getElementById("open-edit-modal").addEventListener("click", openEditModal);
  document.getElementById("show-history").addEventListener("click", openHistoryModal);
  document.getElementById("show-details").addEventListener("click", openDetailsModal);
  document.getElementById("toggle-summary").addEventListener("click", toggleSummary);

  document.querySelectorAll(".close-modal").forEach((button) => {
    button.addEventListener("click", () => closeModal(button.dataset.modal));
  });

  document.querySelectorAll(".tier-head").forEach((button) => {
    button.addEventListener("click", () => toggleTier(button));
  });

  overlayUserSelectEl.addEventListener("change", async (event) => {
    await switchUser(Number(event.target.value || 0));
  });

  userPickerTriggerEl.addEventListener("click", () => {
    userDropdownEl.classList.toggle("hidden");
  });

  document.addEventListener("click", (event) => {
    if (!userPickerWrapEl.contains(event.target)) {
      userDropdownEl.classList.add("hidden");
    }
  });

  document.getElementById("create-form").addEventListener("submit", handleCreateUser);
  document.getElementById("edit-form").addEventListener("submit", handleEditUser);
  sendButtonEl.addEventListener("click", sendMessage);

  document.querySelectorAll(".quick-chip").forEach((button) => {
    button.addEventListener("click", () => {
      messageInputEl.value = button.dataset.prompt || "";
      autoResizeTextarea();
      messageInputEl.focus();
    });
  });

  messageInputEl.addEventListener("input", autoResizeTextarea);
  messageInputEl.addEventListener("keydown", async (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      await sendMessage();
    }
  });
}

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || `请求失败: ${response.status}`);
  }
  return response.json();
}

function renderTime() {
  const now = new Date();
  const dateText = now.toLocaleDateString("zh-CN");
  todayTextEl.textContent = dateText;
  sidebarTimeEl.textContent = `系统时间: ${dateText}`;
}

async function loadUsers() {
  try {
    const payload = await apiRequest("/api/users");
    state.users = payload.users || [];
    renderOverlaySelect();
    renderUserDropdown();
    updateOverlay();
  } catch (error) {
    setStatus(error.message);
  }
}

function renderOverlaySelect() {
  overlayUserSelectEl.innerHTML = '<option value="">选择已有档案...</option>';
  state.users.forEach((user) => {
    const option = document.createElement("option");
    option.value = String(user.user_id);
    option.textContent = `${user.name}${user.age ? ` (${user.age}岁)` : ""}`;
    overlayUserSelectEl.appendChild(option);
  });
}

function renderUserDropdown() {
  if (state.users.length === 0) {
    userDropdownEl.innerHTML = '<div class="user-option"><div class="user-option-avatar">无</div><span>暂无档案</span></div>';
    return;
  }

  userDropdownEl.innerHTML = state.users.map((user) => `
    <button class="user-option" data-user-id="${user.user_id}" type="button">
      <div class="user-option-avatar">${escapeHtml(user.name.slice(0, 1))}</div>
      <span>${escapeHtml(user.name)}${user.age ? ` (${escapeHtml(String(user.age))}岁)` : ""}</span>
    </button>
  `).join("");

  userDropdownEl.querySelectorAll("[data-user-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      await switchUser(Number(button.dataset.userId));
    });
  });
}

async function switchUser(userId) {
  if (!userId) {
    resetCurrentUser();
    return;
  }

  try {
    setBusy(true);
    closeAllModals();
    userDropdownEl.classList.add("hidden");

    const payload = await apiRequest(`/api/users/${userId}`);
    state.currentUserId = userId;
    state.currentUser = payload.user;
    state.dialogState = {};
    overlayUserSelectEl.value = String(userId);

    renderCurrentUser();
    renderProfileSummary();
    clearChat();
    appendWelcomeCard(
      `您好，${state.currentUser.name}`,
      "我已经加载了您的健康档案，如果您有任何关于身体状况、饮食建议或用药提醒的问题，随时可以问我。"
    );
    appendAssistantMessage("您可以直接告诉我血压、身高体重或空腹血糖，我会继续完成评估。");

    updateActionButtons();
    updateOverlay();
    setStatus(`已切换到 ${state.currentUser.name} 的档案。`);
  } catch (error) {
    setStatus(error.message);
  } finally {
    setBusy(false);
  }
}

function resetCurrentUser() {
  state.currentUserId = null;
  state.currentUser = null;
  state.dialogState = {};
  overlayUserSelectEl.value = "";
  closeAllModals();
  userDropdownEl.classList.add("hidden");

  currentAvatarEl.textContent = "未";
  currentUserNameEl.textContent = "未选择";
  currentUserTagEl.textContent = "请选择或新建档案";
  summaryMetricsEl.innerHTML = [
    summaryMetric("性别/年龄", "--"),
    summaryMetric("BMI指数", "--"),
    summaryMetric("身高/体重", "--"),
    summaryMetric("最近血压", "--"),
  ].join("");
  summarySmokingEl.textContent = "无";

  clearChat();
  appendWelcomeCard(
    "欢迎来到悦康守护",
    "请选择已有档案，或先创建一个新的健康档案，然后开始居家健康对话与量化评估。"
  );
  updateActionButtons();
  updateOverlay();
}

function renderCurrentUser() {
  if (!state.currentUser) {
    return;
  }

  currentAvatarEl.textContent = state.currentUser.name.slice(0, 1);
  currentUserNameEl.textContent = state.currentUser.name;
  currentUserTagEl.textContent = `${state.currentUser.age || "--"}岁 · ${state.currentUser.gender || "--"}`;
}

function renderProfileSummary() {
  const params = state.currentUser?.params || {};
  const bmi = computeBmi(params.height_cm, params.weight_kg);
  summaryMetricsEl.innerHTML = [
    summaryMetric("性别/年龄", `${state.currentUser?.gender || "--"} / ${state.currentUser?.age || "--"}岁`),
    summaryMetric("BMI指数", bmi ? bmi.toFixed(1) : "--"),
    summaryMetric("身高/体重", pairValue(params.height_cm, "cm", params.weight_kg, "kg")),
    summaryMetric("最近血压", pairValue(params.systolic_bp, "", params.diastolic_bp, "", "/")),
  ].join("");
  summarySmokingEl.textContent = params.smoking_history || "无";
}

function summaryMetric(label, value) {
  return `
    <div class="summary-metric">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(String(value))}</strong>
    </div>
  `;
}

function updateOverlay() {
  overlayEl.classList.toggle("hidden", Boolean(state.currentUserId));
}

function openModal(id) {
  document.getElementById(id).classList.remove("hidden");
}

function closeModal(id) {
  document.getElementById(id).classList.add("hidden");
}

function closeAllModals() {
  document.querySelectorAll(".modal").forEach((modal) => modal.classList.add("hidden"));
}

function toggleSummary() {
  state.summaryCollapsed = !state.summaryCollapsed;
  document.getElementById("summary-body").classList.toggle("hidden", state.summaryCollapsed);
  document.getElementById("summary-toggle-icon").style.transform = state.summaryCollapsed ? "rotate(180deg)" : "rotate(0deg)";
}

function toggleTier(button) {
  const targetId = button.dataset.tierTarget;
  const content = document.getElementById(targetId);
  const icon = button.querySelector("iconify-icon");
  const collapsed = content.classList.toggle("hidden");
  button.classList.toggle("is-collapsed", collapsed);
  icon.setAttribute("icon", collapsed ? "solar:alt-arrow-right-linear" : "solar:alt-arrow-down-linear");
}

async function openHistoryModal() {
  if (!state.currentUserId) {
    setStatus("请先选择或创建档案。");
    return;
  }

  try {
    const payload = await apiRequest(`/api/users/${state.currentUserId}/assessments`);
    const items = payload.assessments || [];
    if (items.length === 0) {
      historyContainerEl.innerHTML = '<div class="history-empty">暂无历史健康评估</div>';
    } else {
      historyContainerEl.innerHTML = `
        <div class="timeline">
          ${items.map((item) => historyItem(item)).join("")}
        </div>
      `;
    }
    openModal("history-modal");
  } catch (error) {
    setStatus(error.message);
  }
}

function historyItem(item) {
  const riskLevel = item.result_json?.risk_level || "未知";
  const cls = riskLevel.includes("中") ? "timeline-item timeline-item--medium" : riskLevel.includes("正常") || riskLevel.includes("低")
    ? "timeline-item timeline-item--normal"
    : "timeline-item";
  const cardCls = riskLevel.includes("中") ? "timeline-card timeline-card--medium" : riskLevel.includes("正常") || riskLevel.includes("低")
    ? "timeline-card timeline-card--normal"
    : "timeline-card";
  const score = item.result_json?.score ?? "--";
  const summary = item.result_json?.summary || "暂无说明";
  return `
    <div class="${cls}">
      <div class="timeline-head">
        <strong>${escapeHtml(item.calculator_name || "健康评估")}</strong>
        <span>${escapeHtml(item.created_at || "-")}</span>
      </div>
      <div class="${cardCls}">
        <div>
          <span class="timeline-score-label">风险评分</span>
          <div class="timeline-score-value">
            <strong>${escapeHtml(String(score))}</strong>
            <span>/ 100</span>
          </div>
        </div>
        <div class="timeline-card-right">
          <span class="risk-pill ${riskClass(riskLevel)}">风险级别: ${escapeHtml(riskLevel)}</span>
          <p>${escapeHtml(summary)}</p>
        </div>
      </div>
    </div>
  `;
}

async function openDetailsModal() {
  if (!state.currentUserId) {
    setStatus("请先选择或创建档案。");
    return;
  }

  try {
    const payload = await apiRequest(`/api/users/${state.currentUserId}/snapshots`);
    const items = payload.snapshots || [];
    if (items.length === 0) {
      detailsContainerEl.innerHTML = '<div class="details-empty">暂无详细档案记录</div>';
    } else {
      detailsContainerEl.innerHTML = `<div class="details-list">${items.map((item) => detailsItem(item)).join("")}</div>`;
    }
    openModal("details-modal");
  } catch (error) {
    setStatus(error.message);
  }
}

function detailsItem(item) {
  const snapshot = item.snapshot_json || {};
  const params = snapshot.params || {};
  const rows = [
    detailRow("姓名", snapshot.name),
    detailRow("性别", snapshot.gender),
    detailRow("出生日期", snapshot.birth_date),
    ...Object.entries(params).map(([key, value]) => detailRow(profileLabel(key), `${value}${paramUnit(key)}`)),
  ].filter(Boolean).join("");

  return `
    <div class="details-card">
      <span class="details-badge">${escapeHtml(item.created_at || "-")} 更新</span>
      <div class="details-grid">${rows}</div>
    </div>
  `;
}

function detailRow(label, value) {
  if (value === undefined || value === null || value === "") {
    return "";
  }
  return `
    <div class="details-row">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(String(value))}</strong>
    </div>
  `;
}

function openEditModal() {
  if (!state.currentUser) {
    setStatus("请先选择或创建档案。");
    return;
  }

  const form = document.getElementById("edit-form");
  const params = state.currentUser.params || {};
  form.elements.name.value = state.currentUser.name || "";
  form.elements.birth_date.value = state.currentUser.birth_date || "";
  form.elements.gender.value = state.currentUser.gender || "男";
  [
    "smoking_history",
    "temperature_c",
    "heart_rate_bpm",
    "respiratory_rate_bpm",
    "height_cm",
    "weight_kg",
    "systolic_bp",
    "diastolic_bp",
    "sleep_quality",
    "urine_bowel_status",
    "appetite_status",
    "waist_cm",
    "balance_ability",
    "mood_cognition",
    "skin_sclera_status",
    "fasting_glucose",
    "blood_lipids",
    "blood_routine",
    "liver_function",
    "kidney_function",
    "vision_leg_edema",
    "abdominal_ultrasound",
    "ecg_report",
    "bone_density",
    "cognitive_special_screening",
    "imaging_special_notes",
    "thyroid_function",
    "tumor_markers",
    "carotid_ultrasound",
    "echo_abi",
    "specialist_notes",
  ].forEach((field) => {
    if (form.elements[field]) {
      form.elements[field].value = params[field] ?? "";
    }
  });
  document.getElementById("edit-form-message").textContent = "";
  openModal("edit-modal");
}

async function handleCreateUser(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const data = readForm(form);
  const validation = validateProfileForm(data);
  const messageEl = document.getElementById("create-form-message");
  messageEl.textContent = validation || "";
  if (validation) {
    return;
  }

  try {
    setBusy(true);
    const payload = await apiRequest("/api/users", {
      method: "POST",
      body: JSON.stringify({
        name: data.name,
        birth_date: data.birth_date,
        gender: data.gender,
        params: pickParams(data),
      }),
    });
    form.reset();
    closeModal("create-modal");
    await loadUsers();
    await switchUser(payload.user.user_id);
  } catch (error) {
    messageEl.textContent = error.message;
  } finally {
    setBusy(false);
  }
}

async function handleEditUser(event) {
  event.preventDefault();
  if (!state.currentUserId) {
    return;
  }

  const form = event.currentTarget;
  const data = readForm(form);
  const validation = validateProfileForm(data);
  const messageEl = document.getElementById("edit-form-message");
  messageEl.textContent = validation || "";
  if (validation) {
    return;
  }

  try {
    setBusy(true);
    const payload = await apiRequest(`/api/users/${state.currentUserId}`, {
      method: "PUT",
      body: JSON.stringify({
        name: data.name,
        birth_date: data.birth_date,
        gender: data.gender,
        params: pickParams(data),
      }),
    });
    state.currentUser = payload.user;
    renderCurrentUser();
    renderProfileSummary();
    closeModal("edit-modal");
    setStatus("档案已更新。");
  } catch (error) {
    messageEl.textContent = error.message;
  } finally {
    setBusy(false);
  }
}

async function sendMessage() {
  const message = messageInputEl.value.trim();
  if (!message || state.busy) {
    return;
  }
  if (!state.currentUserId) {
    setStatus("请先选择或创建档案。");
    return;
  }

  appendUserMessage(message);
  messageInputEl.value = "";
  autoResizeTextarea();
  const pendingReply = appendAssistantLoadingMessage();

  try {
    setBusy(true);
    setStatus("正在处理消息...");
    const payload = await apiRequest("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        user_id: state.currentUserId,
        message,
        dialog_state: state.dialogState,
      }),
    });

    state.dialogState = payload.state || {};
    state.currentUser = payload.profile || state.currentUser;

    renderCurrentUser();
    renderProfileSummary();
    replaceAssistantMessage(pendingReply, payload.reply_text, payload.card_html);
    setStatus(payload.result ? "消息已处理，评估结果已自动记录到历史中。" : "消息已处理。");
  } catch (error) {
    replaceAssistantMessage(pendingReply, `处理失败：${error.message}`);
    setStatus(error.message);
  } finally {
    setBusy(false);
  }
}

function appendWelcomeCard(title, text) {
  const row = document.createElement("div");
  row.className = "message-row ai";
  row.innerHTML = `
    <div class="welcome-card">
      <div class="welcome-card__eyebrow">YUEKANG GUARDIAN</div>
      <h3>${escapeHtml(title)}</h3>
      <p>${escapeHtml(text)}</p>
    </div>
  `;
  chatStreamEl.appendChild(row);
}

function appendAssistantMessage(text, cardHtml = "") {
  appendMessageRow("ai", `<div>${escapeHtml(text).replace(/\n/g, "<br/>")}</div>${cardHtml ? `<div style="margin-top:12px">${cardHtml}</div>` : ""}`, true);
}

function appendUserMessage(text) {
  appendMessageRow("user", escapeHtml(text), true);
}

function appendAssistantLoadingMessage() {
  return appendMessageRow(
    "ai",
    `
      <div class="thinking-indicator">
        <span class="thinking-indicator__label">正在分析</span>
        <span class="thinking-dots" aria-hidden="true">
          <span></span><span></span><span></span>
        </span>
      </div>
    `,
    true,
    { loading: true, metaText: "处理中..." },
  );
}

function replaceAssistantMessage(messageRef, text, cardHtml = "") {
  if (!messageRef) {
    appendAssistantMessage(text, cardHtml);
    return;
  }

  messageRef.bubble.className = "message-bubble";
  messageRef.bubble.innerHTML = `<div>${escapeHtml(text).replace(/\n/g, "<br/>")}</div>${cardHtml ? `<div style="margin-top:12px">${cardHtml}</div>` : ""}`;
  messageRef.meta.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  chatStreamEl.scrollTop = chatStreamEl.scrollHeight;
}

function appendMessageRow(role, html, trusted, options = {}) {
  const row = document.createElement("div");
  row.className = `message-row ${role}`;

  const wrap = document.createElement("div");
  wrap.className = `message-wrap ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.innerHTML = role === "ai"
    ? '<iconify-icon icon="solar:user-rounded-bold"></iconify-icon>'
    : escapeHtml(state.currentUser?.name?.slice(0, 1) || "我");

  const stack = document.createElement("div");
  stack.className = "message-stack";

  const bubble = document.createElement("div");
  bubble.className = `message-bubble${options.loading ? " message-bubble--loading" : ""}`;
  if (trusted) {
    bubble.innerHTML = html;
  } else {
    bubble.textContent = html;
  }

  const meta = document.createElement("span");
  meta.className = "message-meta";
  meta.textContent = options.metaText || new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  stack.appendChild(bubble);
  stack.appendChild(meta);
  wrap.appendChild(avatar);
  wrap.appendChild(stack);
  row.appendChild(wrap);
  chatStreamEl.appendChild(row);
  chatStreamEl.scrollTop = chatStreamEl.scrollHeight;
  return { row, bubble, meta };
}

function clearChat() {
  chatStreamEl.innerHTML = "";
}

function setBusy(flag) {
  state.busy = flag;
  sendButtonEl.disabled = flag || !state.currentUserId;
}

function updateActionButtons() {
  setBusy(state.busy);
}

function setStatus(text) {
  actionStatusEl.textContent = text;
}

function autoResizeTextarea() {
  messageInputEl.style.height = "auto";
  messageInputEl.style.height = `${Math.min(messageInputEl.scrollHeight, 132)}px`;
}

function readForm(form) {
  const formData = new FormData(form);
  return Object.fromEntries(formData.entries());
}

function validateProfileForm(data) {
  if (!data.name || !data.birth_date || !data.gender) {
    return "姓名、出生日期、性别为必填项。";
  }
  if (ageFromBirthDate(data.birth_date) === null) {
    return "出生日期格式无效。";
  }

  const rules = [
    ["temperature_c", 30, 45],
    ["heart_rate_bpm", 20, 220],
    ["respiratory_rate_bpm", 5, 60],
    ["height_cm", 50, 250],
    ["weight_kg", 30, 200],
    ["systolic_bp", 50, 300],
    ["diastolic_bp", 30, 200],
    ["fasting_glucose", 1, 50],
    ["waist_cm", 30, 200],
  ];

  for (const [field, min, max] of rules) {
    const value = data[field];
    if (!value) {
      continue;
    }
    const numeric = Number(value);
    if (Number.isNaN(numeric) || numeric < min || numeric > max) {
      return `${profileLabel(field)}需要在 ${min} 到 ${max} 之间。`;
    }
  }
  return "";
}

function pickParams(data) {
  const params = {};
  [
    "smoking_history",
    "temperature_c",
    "heart_rate_bpm",
    "respiratory_rate_bpm",
    "height_cm",
    "weight_kg",
    "systolic_bp",
    "diastolic_bp",
    "sleep_quality",
    "urine_bowel_status",
    "appetite_status",
    "waist_cm",
    "balance_ability",
    "mood_cognition",
    "skin_sclera_status",
    "fasting_glucose",
    "blood_lipids",
    "blood_routine",
    "liver_function",
    "kidney_function",
    "vision_leg_edema",
    "abdominal_ultrasound",
    "ecg_report",
    "bone_density",
    "cognitive_special_screening",
    "imaging_special_notes",
    "thyroid_function",
    "tumor_markers",
    "carotid_ultrasound",
    "echo_abi",
    "specialist_notes",
  ].forEach((field) => {
    const value = data[field];
    if (value === undefined || value === null || value === "") {
      return;
    }
    params[field] = [
      "temperature_c",
      "heart_rate_bpm",
      "respiratory_rate_bpm",
      "height_cm",
      "weight_kg",
      "systolic_bp",
      "diastolic_bp",
      "fasting_glucose",
      "waist_cm",
    ].includes(field)
      ? Number(value)
      : value;
  });
  return params;
}

function ageFromBirthDate(text) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text);
  if (!match) {
    return null;
  }
  const date = new Date(text);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  const now = new Date();
  let age = now.getFullYear() - date.getFullYear();
  if (now.getMonth() < date.getMonth() || (now.getMonth() === date.getMonth() && now.getDate() < date.getDate())) {
    age -= 1;
  }
  return age;
}

function computeBmi(heightCm, weightKg) {
  const height = Number(heightCm);
  const weight = Number(weightKg);
  if (!height || !weight) {
    return null;
  }
  return weight / ((height / 100) ** 2);
}

function pairValue(left, leftUnit, right, rightUnit, sep = " / ") {
  if ((left === undefined || left === null || left === "") && (right === undefined || right === null || right === "")) {
    return "--";
  }
  const leftText = left === undefined || left === null || left === "" ? "--" : `${left}${leftUnit}`;
  const rightText = right === undefined || right === null || right === "" ? "--" : `${right}${rightUnit}`;
  return `${leftText}${sep}${rightText}`;
}

function riskClass(text) {
  if (text.includes("正常") || text.includes("低")) {
    return "risk-low";
  }
  if (text.includes("中") || text.includes("偏高")) {
    return "risk-medium";
  }
  return "risk-high";
}

function profileLabel(key) {
  return {
    smoking_history: "吸烟史",
    temperature_c: "体温",
    heart_rate_bpm: "心率",
    respiratory_rate_bpm: "呼吸频率",
    height_cm: "身高",
    weight_kg: "体重",
    systolic_bp: "收缩压",
    diastolic_bp: "舒张压",
    sleep_quality: "睡眠质量",
    urine_bowel_status: "尿便性状",
    appetite_status: "食欲",
    waist_cm: "腰围",
    balance_ability: "平衡能力",
    mood_cognition: "情绪与认知",
    skin_sclera_status: "皮肤/巩膜颜色",
    fasting_glucose: "空腹血糖",
    blood_lipids: "血脂四项",
    blood_routine: "血常规",
    liver_function: "肝功能",
    kidney_function: "肾功能",
    vision_leg_edema: "视力/下肢水肿",
    abdominal_ultrasound: "腹部超声",
    ecg_report: "心电图",
    bone_density: "骨密度",
    cognitive_special_screening: "认知评估/专项筛查",
    imaging_special_notes: "其他影像与专项体检结论",
    thyroid_function: "甲状腺功能",
    tumor_markers: "肿瘤标志物",
    carotid_ultrasound: "颈动脉超声",
    echo_abi: "超声心动图 / ABI",
    specialist_notes: "专科补充说明",
  }[key] || key;
}

function paramUnit(key) {
  return {
    temperature_c: "℃",
    heart_rate_bpm: "次/分",
    respiratory_rate_bpm: "次/分",
    height_cm: "cm",
    weight_kg: "kg",
    systolic_bp: "mmHg",
    diastolic_bp: "mmHg",
    fasting_glucose: "mmol/L",
    waist_cm: "cm",
  }[key] || "";
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
