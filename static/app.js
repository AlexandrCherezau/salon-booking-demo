"use strict";

const WEEKDAYS = ["вс", "пн", "вт", "ср", "чт", "пт", "сб"];
const MONTHS_GEN = ["января", "февраля", "марта", "апреля", "мая", "июня",
  "июля", "августа", "сентября", "октября", "ноября", "декабря"];
const AVATAR_COLORS = ["#b0674a", "#56634f", "#7d8fb0", "#a98a5c"];
const DAYS_SHOWN = 14;

const state = { catalog: null, serviceId: null, masterId: null, day: null, time: null };
const $ = (id) => document.getElementById(id);

function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  Object.entries(props).forEach(([key, value]) => {
    if (key === "text") node.textContent = value;
    else if (key === "class") node.className = value;
    else node.setAttribute(key, value);
  });
  children.forEach((child) => node.append(child));
  return node;
}

const rub = (n) => `${n.toLocaleString("ru-RU")} ₽`;
const isoDay = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const humanDay = (iso) => {
  const d = new Date(`${iso}T00:00:00`);
  return `${d.getDate()} ${MONTHS_GEN[d.getMonth()]}, ${WEEKDAYS[d.getDay()]}`;
};
const hoursLabel = (h) => (h === 1 ? "1 час" : `${h} часа`);
const service = () => state.catalog.services.find((s) => s.id === state.serviceId);
const master = () => state.catalog.masters.find((m) => m.id === state.masterId);

async function api(path, options) {
  const res = await fetch(path, options);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(body.detail)
      ? body.detail.map((d) => d.msg.replace(/^Value error, /, "")).join("; ")
      : body.detail;
    throw new Error(detail || `Ошибка сервера (${res.status})`);
  }
  return body;
}

/* ---------- landing ---------- */

function renderPrices() {
  const grid = $("price-grid");
  const categories = [...new Set(state.catalog.services.map((s) => s.category))];
  categories.forEach((cat) => {
    const rows = state.catalog.services.filter((s) => s.category === cat).map((s) =>
      el("div", { class: "price-row" }, [
        el("div", {}, [el("span", { class: "t", text: s.title }), el("span", { class: "n", text: s.note })]),
        el("span", { class: "d", text: hoursLabel(s.hours) }),
        el("span", { class: "p", text: rub(s.price) }),
      ]));
    grid.append(el("div", { class: "price-col" }, [el("h3", { text: cat }), ...rows]));
  });
}

function renderMasters() {
  const list = $("masters-list");
  state.catalog.masters.forEach((m, i) => {
    const initials = m.name.split(" ").map((p) => p[0]).join("");
    list.append(el("article", { class: "master" }, [
      el("div", { class: "avatar", style: `background:${AVATAR_COLORS[i % AVATAR_COLORS.length]}`, text: initials }),
      el("h3", { text: m.name }),
      el("span", { class: "role", text: m.role }),
      el("p", { text: m.bio }),
      el("span", { class: "exp", text: `Стаж ${m.years} лет` }),
    ]));
  });
}

async function findNearest() {
  const today = new Date();
  for (let offset = 0; offset < 3; offset += 1) {
    const day = isoDay(new Date(today.getFullYear(), today.getMonth(), today.getDate() + offset));
    const results = await Promise.all(state.catalog.masters.map((m) =>
      api(`/api/slots?service_id=${m.services[0]}&master_id=${m.id}&day=${day}`)
        .then((r) => r.slots.map((t) => ({ t, m }))).catch(() => [])));
    const all = results.flat().sort((a, b) => a.t.localeCompare(b.t));
    if (all.length) {
      const label = offset === 0 ? "сегодня" : offset === 1 ? "завтра" : humanDay(day);
      return `${label} в ${all[0].t} · ${all[0].m.name.split(" ")[0]}`;
    }
  }
  return "на ближайшие дни всё занято";
}

/* ---------- booking form ---------- */

function chip(label, sub, checked, onClick) {
  const btn = el("button", { type: "button", class: "chip-btn", role: "radio", "aria-checked": String(checked) },
    [label instanceof Node ? label : document.createTextNode(label)]);
  if (sub) btn.append(el("small", { text: sub }));
  btn.addEventListener("click", onClick);
  return btn;
}

function renderServiceSelect() {
  const select = $("service");
  state.catalog.services.forEach((s) => {
    select.append(el("option", { value: s.id, text: `${s.title} — ${rub(s.price)} · ${hoursLabel(s.hours)}` }));
  });
  state.serviceId = select.value;
  select.addEventListener("change", () => {
    state.serviceId = select.value;
    if (!master()?.services.includes(state.serviceId)) state.masterId = null;
    state.time = null;
    renderMasterPick();
    loadSlots();
  });
}

function renderMasterPick() {
  const box = $("master-pick");
  box.replaceChildren();
  const suitable = state.catalog.masters.filter((m) => m.services.includes(state.serviceId));
  if (suitable.length === 1) state.masterId = suitable[0].id;
  suitable.forEach((m) => box.append(chip(m.name, m.role, m.id === state.masterId, () => {
    state.masterId = m.id;
    state.time = null;
    renderMasterPick();
    loadSlots();
  })));
}

function renderDays() {
  const box = $("days");
  box.replaceChildren();
  const now = new Date();
  for (let i = 0; i < DAYS_SHOWN; i += 1) {
    const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() + i);
    const iso = isoDay(d);
    if (!state.day) state.day = iso;
    const label = el("b", { text: String(d.getDate()) });
    box.append(chip(label, i === 0 ? "сег" : WEEKDAYS[d.getDay()], iso === state.day, () => {
      state.day = iso;
      state.time = null;
      renderDays();
      loadSlots();
    }));
  }
}

let slotsRequest = 0;
async function loadSlots() {
  const box = $("slots");
  updateSummary();
  if (!state.masterId) {
    box.replaceChildren(el("p", { class: "muted small", text: "Выберите мастера" }));
    return;
  }
  const requestId = ++slotsRequest;
  box.replaceChildren(el("p", { class: "muted small", text: "Загружаем свободное время…" }));
  try {
    const data = await api(`/api/slots?service_id=${state.serviceId}&master_id=${state.masterId}&day=${state.day}`);
    if (requestId !== slotsRequest) return;
    if (!data.slots.includes(state.time)) state.time = null;
    if (!data.slots.length) {
      box.replaceChildren(el("p", { class: "muted small", text: "На этот день свободных окон нет — выберите другой" }));
    } else {
      box.replaceChildren(...data.slots.map((t) => chip(t, null, t === state.time, () => {
        state.time = t;
        box.querySelectorAll(".chip-btn").forEach((b) => b.setAttribute("aria-checked", String(b.textContent === t)));
        updateSummary();
      })));
    }
  } catch (err) {
    if (requestId === slotsRequest) box.replaceChildren(el("p", { class: "form-error", text: err.message }));
  }
  updateSummary();
}

function updateSummary() {
  const box = $("summary");
  const s = service();
  const m = master();
  if (!s || !m || !state.time) { box.classList.remove("on"); return; }
  box.replaceChildren(
    el("b", { text: `${s.title}` }), document.createTextNode(` у ${m.name}`), el("br"),
    document.createTextNode(`${humanDay(state.day)}, ${state.time} · ${hoursLabel(s.hours)} · ${rub(s.price)}`));
  box.classList.add("on");
}

function formatPhone(input) {
  const raw = input.value.trim();
  let digits = raw.replace(/\D/g, "");
  if (raw.startsWith("+7")) digits = digits.slice(1);           // our own prefix
  else if (/^[78]/.test(digits) && (digits.length === 1 || digits.length === 11)) digits = digits.slice(1);
  if (!digits && /^(\+7|[78])$/.test(raw)) { input.value = "+7 "; return; }
  digits = digits.slice(0, 10);
  if (!digits) { input.value = ""; return; }
  const parts = [digits.slice(0, 3), digits.slice(3, 6), digits.slice(6, 8), digits.slice(8, 10)];
  input.value = `+7 ${parts[0]}${parts[1] ? ` ${parts[1]}` : ""}${parts[2] ? `-${parts[2]}` : ""}${parts[3] ? `-${parts[3]}` : ""}`;
}

function validate() {
  const name = $("name");
  const phone = $("phone");
  const nameOk = name.value.trim().length >= 2;
  const phoneOk = phone.value.replace(/\D/g, "").length === 11;
  name.setAttribute("aria-invalid", String(!nameOk));
  phone.setAttribute("aria-invalid", String(!phoneOk));
  if (!state.masterId) return "Выберите мастера";
  if (!state.time) return "Выберите время";
  if (!nameOk) return "Укажите имя";
  if (!phoneOk) return "Укажите телефон полностью";
  return null;
}

async function submit(event) {
  event.preventDefault();
  const error = $("form-error");
  const problem = validate();
  error.textContent = problem || "";
  if (problem) return;
  const btn = $("submit");
  btn.disabled = true;
  btn.textContent = "Отправляем…";
  try {
    const booking = await api("/api/bookings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        service_id: state.serviceId, master_id: state.masterId, day: state.day,
        hour: Number(state.time.slice(0, 2)), name: $("name").value,
        phone: $("phone").value, comment: $("comment").value,
      }),
    });
    $("success-text").textContent =
      `${booking.service} у мастера ${booking.master} — ${humanDay(booking.day).replace(" ", "\u00a0")}, в ${booking.time}. ` +
      `Стоимость ${rub(booking.price)}. Номер записи\u00a0#${booking.id}.`;
    $("booking-form").hidden = true;
    $("success").hidden = false;
  } catch (err) {
    error.textContent = err.message;
    loadSlots();
  } finally {
    btn.disabled = false;
    btn.textContent = "Записаться";
  }
}

function resetForm() {
  $("booking-form").reset();
  state.time = null;
  $("service").value = state.serviceId;
  $("success").hidden = true;
  $("booking-form").hidden = false;
  loadSlots();
}

async function init() {
  try {
    state.catalog = await api("/api/catalog");
  } catch (err) {
    $("form-error").textContent = "Не удалось загрузить данные: запустите сервер (см. README)";
    return;
  }
  renderPrices();
  renderMasters();
  renderServiceSelect();
  renderMasterPick();
  renderDays();
  loadSlots();
  $("phone").addEventListener("input", (e) => formatPhone(e.target));
  $("booking-form").addEventListener("submit", submit);
  $("again").addEventListener("click", resetForm);
  findNearest().then((text) => { $("nearest").textContent = text; });
}

init();
