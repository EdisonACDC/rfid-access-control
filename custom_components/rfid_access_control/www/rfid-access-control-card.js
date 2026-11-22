/*
 * RFID Access Control - card Lovelace
 * Versione 1.3.1
 *
 * La card usa solo i servizi e gli attributi del sensore dell'integrazione.
 * I PIN non restano nella pagina: si digitano su un tastierino a schermo e
 * vengono verificati dal server. Il PIN di un utente si vede solo dopo aver
 * digitato il PIN admin.
 */
const RFID_CARD_VERSION = '1.3.1';

const RFID_CARD_CSS = `
:host { display: block; }
.wrap {
  box-sizing: border-box; max-width: 480px; margin: 0 auto; padding: 14px 16px 12px;
  font-family: var(--paper-font-body1_-_font-family, Roboto, system-ui, sans-serif);
  color: var(--primary-text-color, #1b1f24);
  background: var(--ha-card-background, var(--card-background-color, #fff));
  border-radius: var(--ha-card-border-radius, 12px);
}
.top { display: flex; align-items: center; gap: 8px; min-height: 44px; margin-bottom: 8px; }
.top h1 { font-size: 20px; font-weight: 700; margin: 0; flex: 1; line-height: 1.2; }
.ib {
  min-width: 44px; min-height: 44px; border: 0; border-radius: 12px; background: transparent;
  color: inherit; cursor: pointer; display: flex; align-items: center; justify-content: center; padding: 0;
}
.ib:hover { background: rgba(127,127,127,.12); }
.sub { color: var(--secondary-text-color, #5b6470); font-size: 13px; line-height: 1.35; }
.stack { display: flex; flex-direction: column; gap: 12px; }
.row { display: flex; align-items: center; gap: 12px; }
.grow { flex: 1; min-width: 0; }
.label { font-size: 13px; font-weight: 600; color: var(--secondary-text-color, #5b6470); letter-spacing: .02em; }
.card-box {
  border: 1px solid var(--divider-color, #e0e0e0); border-radius: 16px; padding: 14px;
  background: var(--card-background-color, #fff);
}
.state { border-radius: 16px; padding: 16px; display: flex; gap: 14px; align-items: center; }
.state.ok { background: rgba(30,142,62,.12); }
.state.warn { background: rgba(227,116,0,.14); }
.state.alarm { background: rgba(197,34,31,.13); }
.state .dot { width: 48px; height: 48px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; color: #fff; }
.state.ok .dot { background: #1e8e3e; }
.state.warn .dot { background: #e37400; }
.state.alarm .dot { background: #c5221f; }
.state strong { display: block; font-size: 17px; margin-bottom: 2px; }
.stat { border: 1px solid var(--divider-color, #e0e0e0); border-radius: 14px; padding: 12px; }
.stat b { display: block; font-size: 24px; line-height: 1.1; }
.btn {
  min-height: 52px; width: 100%; box-sizing: border-box; padding: 0 16px; border: 0; border-radius: 14px;
  font: inherit; font-size: 16px; font-weight: 600; cursor: pointer; display: flex; align-items: center;
  justify-content: center; gap: 10px; background: var(--primary-color, #1557b0); color: var(--text-primary-color, #fff);
}
.btn.sec { background: var(--card-background-color, #fff); color: var(--primary-text-color, #1b1f24); border: 1px solid var(--divider-color, #d5dbe2); }
.btn.warn { background: #8a4b00; color: #fff; }
.btn.danger { background: #c5221f; color: #fff; }
.btn.small { min-height: 44px; width: auto; font-size: 14px; padding: 0 14px; }
.btn:disabled { opacity: .5; cursor: default; }
.btn-line { display: flex; flex-direction: column; align-items: flex-start; text-align: left; gap: 2px; }
.btn-line small { font-size: 13px; font-weight: 400; opacity: .85; }
.msg { border-radius: 12px; padding: 10px 12px; font-size: 14px; }
.msg.ok { background: rgba(30,142,62,.14); color: var(--primary-text-color, #1b1f24); }
.msg.err { background: rgba(197,34,31,.14); color: var(--primary-text-color, #1b1f24); }
.dots { display: flex; gap: 14px; justify-content: center; align-items: center; min-height: 20px; }
.dots span { width: 14px; height: 14px; border-radius: 50%; border: 2px solid var(--secondary-text-color, #9aa4b0); box-sizing: border-box; }
.dots span.on { background: var(--primary-color, #1557b0); border-color: var(--primary-color, #1557b0); }
.keys { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; width: 100%; max-width: 300px; margin: 0 auto; }
.key {
  min-height: 60px; border-radius: 16px; border: 1px solid var(--divider-color, #e3e7ec); background: var(--secondary-background-color, #f7f9fb);
  color: var(--primary-text-color, #1b1f24); font: inherit; font-size: 24px; font-weight: 500; cursor: pointer;
}
.key.fn { font-size: 18px; }
.key:disabled { opacity: .5; }
.center { display: flex; flex-direction: column; align-items: center; gap: 16px; text-align: center; }
.tag { font-size: 12px; font-weight: 600; padding: 3px 9px; border-radius: 999px; white-space: nowrap; }
.tag.pin { background: rgba(21,87,176,.14); color: var(--primary-color, #1557b0); }
.tag.rfid { background: rgba(101,57,176,.15); color: #7a4fc7; }
.tag.temp { background: rgba(227,116,0,.16); color: #b35a00; }
.tag.off { background: rgba(127,127,127,.18); color: var(--secondary-text-color, #5b6470); }
.avatar { width: 40px; height: 40px; border-radius: 50%; color: #fff; font-weight: 700; font-size: 15px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.user { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--divider-color, #eef1f4); min-height: 52px; }
.user .name { font-size: 15px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; background: none; border: 0; padding: 0; color: inherit; font: inherit; text-align: left; cursor: pointer; }
.user.off .name { color: var(--secondary-text-color, #5b6470); }
.tags { display: flex; gap: 6px; flex-wrap: wrap; }
.sw {
  width: 48px; height: 28px; border-radius: 999px; border: 0; padding: 3px; flex-shrink: 0; display: flex; align-items: center;
  justify-content: flex-start; background: #c3cad3; cursor: pointer;
}
.sw[aria-checked="true"] { background: #1e8e3e; justify-content: flex-end; }
.sw span { width: 22px; height: 22px; border-radius: 50%; background: #fff; box-shadow: 0 1px 2px rgba(0,0,0,.25); }
.search {
  width: 100%; box-sizing: border-box; min-height: 46px; padding: 0 14px; border-radius: 12px; border: 1px solid var(--divider-color, #d5dbe2);
  background: var(--secondary-background-color, #f4f6f8); color: inherit; font: inherit; font-size: 15px;
}
input.field, select.field {
  width: 100%; box-sizing: border-box; min-height: 48px; padding: 0 12px; border-radius: 12px; border: 1px solid var(--divider-color, #c3cad3);
  background: var(--card-background-color, #fff); color: inherit; font: inherit; font-size: 16px;
}
.steps { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
.steps button { border: 0; background: transparent; padding: 0; font: inherit; color: var(--secondary-text-color, #5b6470); text-align: left; cursor: pointer; min-height: 44px; }
.steps button i { display: block; height: 4px; border-radius: 2px; background: var(--divider-color, #e3e7ec); margin-bottom: 6px; }
.steps button.done i, .steps button.cur i { background: var(--primary-color, #1557b0); }
.steps button.cur { color: var(--primary-text-color, #1b1f24); font-weight: 700; }
.chip { min-width: 52px; height: 40px; border-radius: 10px; font: inherit; font-size: 14px; font-weight: 600; cursor: pointer; border: 1px solid var(--divider-color, #d5dbe2); background: var(--card-background-color, #fff); color: inherit; }
.chip.on { background: var(--primary-color, #1557b0); border-color: var(--primary-color, #1557b0); color: #fff; }
.act { min-height: 60px; border-radius: 14px; padding: 10px 14px; display: flex; align-items: center; gap: 12px; font: inherit; color: inherit; cursor: pointer; background: var(--card-background-color, #fff); border: 1px solid var(--divider-color, #e3e7ec); width: 100%; box-sizing: border-box; text-align: left; }
.act.on { border: 2px solid var(--primary-color, #1557b0); background: rgba(21,87,176,.08); }
.box { width: 22px; height: 22px; border-radius: 6px; flex-shrink: 0; box-sizing: border-box; border: 2px solid var(--secondary-text-color, #9aa4b0); }
.act.on .box { background: var(--primary-color, #1557b0); border-color: var(--primary-color, #1557b0); }
.dur { min-height: 44px; border-radius: 12px; font: inherit; font-size: 15px; font-weight: 600; cursor: pointer; background: var(--card-background-color, #fff); color: inherit; border: 1px solid var(--divider-color, #e8d3b5); }
.dur.on { border: 2px solid #e37400; color: var(--primary-text-color, #1b1f24); background: rgba(227,116,0,.16); }
.countdown { font-size: 30px; font-weight: 700; font-variant-numeric: tabular-nums; color: #8a4b00; }
.foot { margin-top: 14px; text-align: center; font-size: 11px; color: var(--secondary-text-color, #9aa4b0); }
.hint { font-size: 12px; color: var(--secondary-text-color, #5b6470); }
.loading { padding: 24px; text-align: center; color: var(--secondary-text-color, #5b6470); }
.actwrap { display: flex; flex-direction: column; gap: 6px; }
.kpi { color: var(--primary-color, #1557b0); display: flex; flex-shrink: 0; }
.kp-row { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 6px; padding: 0 2px 4px; }
.kp {
  min-height: 64px; border-radius: 12px; border: 1px solid var(--divider-color, #d5dbe2); background: var(--card-background-color, #fff);
  color: var(--primary-text-color, #1b1f24); font: inherit; font-size: 11px; cursor: pointer; padding: 4px 2px;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px;
}
.kp span { line-height: 1.1; text-align: center; }
.kp.on { border: 2px solid var(--primary-color, #1557b0); background: rgba(21,87,176,.14); font-weight: 700; }
.pinline { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.kp-switch { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 12px; }
.act:disabled { opacity: .55; cursor: default; }
.pinline b { font-size: 18px; letter-spacing: .12em; font-variant-numeric: tabular-nums; }
`;

const RFID_AVATAR_COLORS = ['#1557b0', '#6a1b9a', '#00695c', '#ad1457', '#e65100', '#7a3e00', '#5b6470'];

// Tasti del Develco KEPZB-110 (action di Zigbee2MQTT) e icona di ciascuno.
const RFID_KEYPAD = [
  { value: 'disarm', icon: 'unlock', label: 'Lucchetto aperto' },
  { value: 'arm_all_zones', icon: 'lock', label: 'Lucchetto chiuso' },
  { value: 'arm_day_zones', icon: 'home', label: 'Casa' },
  { value: 'arm_night_zones', icon: 'moon', label: 'Luna' },
  { value: 'any', icon: 'star', label: 'Qualsiasi tasto' },
];

function rfidKeypad(value) {
  return RFID_KEYPAD.find((k) => k.value === value) || RFID_KEYPAD[RFID_KEYPAD.length - 1];
}

function rfidEsc(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function rfidInitials(name) {
  const parts = String(name || '?').trim().split(/\s+/);
  return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase();
}

function rfidColor(name) {
  let hash = 0;
  for (const ch of String(name || '')) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  return RFID_AVATAR_COLORS[hash % RFID_AVATAR_COLORS.length];
}

function rfidSlug(name) {
  return String(name || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '') || 'utente';
}

const RFID_ICON = {
  back: '<path d="M15 6l-6 6 6 6"/>',
  close: '<path d="M6 6l12 12M18 6L6 18"/>',
  lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  check: '<path d="M5 12l5 5L20 7"/>',
  alert: '<path d="M12 8v5M12 17h.01"/><path d="M10.3 3.9L2 18a2 2 0 0 0 1.7 3h16.6a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
  key: '<circle cx="9" cy="8" r="4"/><path d="M2 21c0-3.9 3.1-7 7-7s7 3.1 7 7"/><path d="M19 8v6M16 11h6"/>',
  tool: '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18v3h3l6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.5-.5-.5-2.5z"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  chevron: '<path d="M9 6l6 6-6 6"/>',
  card: '<rect x="5" y="2" width="14" height="20" rx="2"/><path d="M9 7h.01M12 7h.01M15 7h.01M9 11h.01M12 11h.01M15 11h.01M9 15h.01M12 15h.01M15 15h.01"/>',
  wave: '<path d="M5 12.5a7 7 0 0 1 0-1M8.5 15a10 10 0 0 1 0-6M12 17.5a14 14 0 0 1 0-11"/><rect x="15" y="5" width="6" height="14" rx="1.5"/>',
  unlock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 7.7-1.6"/>',
  home: '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/>',
  moon: '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/>',
  star: '<path d="M12 3v18M4.2 7.5l15.6 9M19.8 7.5l-15.6 9"/>',
  eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  eyeoff: '<path d="M3 3l18 18M10.6 6.1A10 10 0 0 1 12 6c6.5 0 10 6 10 6a17 17 0 0 1-3 3.6M6.6 6.6A17 17 0 0 0 2 12s3.5 7 10 7a10 10 0 0 0 5.4-1.6"/>',
};

function rfidIcon(name, size = 22) {
  return `<svg aria-hidden="true" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${RFID_ICON[name] || ''}</svg>`;
}

// MULTI-KEYPAD-HELPERS-BEGIN
// Più tastierini: ogni sensore "sensor.rfid_users_<device>" è un tastierino.
const RFID_SENSOR_PREFIX = 'sensor.rfid_users_';

function rfidDeviceFromEntity(entity) {
  const id = String(entity || '');
  return id.startsWith(RFID_SENSOR_PREFIX) ? id.slice(RFID_SENSOR_PREFIX.length) : '';
}

function rfidIsKeypadState(state) {
  const a = state && state.attributes;
  return !!a && typeof a.device_id === 'string' && Array.isArray(a.users) && 'setup_required' in a;
}

function rfidKeypadLabel(deviceId) {
  const text = String(deviceId || '').replace(/[_-]+/g, ' ').trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : '';
}

function rfidKeypadsFromStates(states) {
  return Object.keys(states || {})
    .filter((id) => id.startsWith('sensor.') && rfidIsKeypadState(states[id]))
    .sort()
    .map((id) => ({
      entity: id,
      deviceId: states[id].attributes.device_id,
      topic: states[id].attributes.mqtt_topic || '',
      label: rfidKeypadLabel(states[id].attributes.device_id),
    }));
}
// MULTI-KEYPAD-HELPERS-END

class RFIDAccessControlCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._view = 'home';
    this._unlocked = false;
    this._operatorPin = '';
    this._pin = '';
    this._pinPurpose = '';
    this._pinTarget = 'home';
    this._pinError = '';
    this._msg = null;
    this._search = '';
    this._draft = null;
    this._listening = false;
    this._listenStart = 0;
    this._listenTimer = null;
    this._lockTimer = null;
    this._tickTimer = null;
    this._snapshot = '';
    this._busy = false;
    this._instMinutes = 30;
    this._testResult = null;
    this._sos = { open: false, entity: '', service: '', name: '' };
    this._adminCurrent = '';
    this._adminNew = '';
    this._entityId = null;
    this._copyTarget = '';
    this._kpAdd = null;

    this.shadowRoot.addEventListener('click', (e) => this._onClick(e));
    this.shadowRoot.addEventListener('input', (e) => this._onInput(e));
    this.shadowRoot.addEventListener('change', (e) => this._onInput(e));
    this.shadowRoot.addEventListener('keydown', (e) => this._onKey(e));
  }

  connectedCallback() {
    this._render();
  }

  disconnectedCallback() {
    this._clearTimers();
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error('Indica "entity": il sensore dell\'integrazione RFID Access Control');
    }
    this.config = {
      entity: config.entity,
      device_id: config.device_id || null,
      title: config.title || 'Controllo Accessi',
      lock_timeout: Number(config.lock_timeout) || 5,
    };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    const snapshot = this._statusSnapshot();
    const changed = snapshot !== this._snapshot;
    this._snapshot = snapshot;

    if (this._listening) this._checkRfidEvent();
    // Ridisegna solo le schermate di stato: le altre non perdono ciò che l'utente sta scrivendo.
    if (changed && (this._view === 'home' || this._view === 'tamper')) this._render();
    else if (!this.shadowRoot.innerHTML) this._render();
  }

  getCardSize() {
    return 8;
  }

  // ---------------------------------------------------------------- dati
  // Il tastierino scelto nel selettore (o quello della configurazione).
  _entity() {
    return this._entityId || this.config.entity;
  }

  _attrs() {
    const state = this._hass && this._hass.states[this._entity()];
    return (state && state.attributes) || {};
  }

  // Dal sensore: non serve più scrivere device_id nella card.
  _deviceId() {
    return this._attrs().device_id || rfidDeviceFromEntity(this._entity()) || this.config.device_id || '';
  }

  _keypads() {
    return rfidKeypadsFromStates(this._hass ? this._hass.states : {});
  }

  _users() {
    const users = this._attrs().users;
    return Array.isArray(users) ? users : [];
  }

  _statusSnapshot() {
    const a = this._attrs();
    return [a.tamper_active, a.keypad_locked_by_tamper, a.installer_active, a.locked_out, a.setup_required, a.users?.length].join('|');
  }

  _status() {
    const a = this._attrs();
    if ((a.tamper_active || a.keypad_locked_by_tamper) && !a.installer_active) {
      const title = a.tamper_active ? 'Coperchio aperto' : 'Bloccato dopo apertura coperchio';
      return { kind: 'alarm', icon: 'alert', title, text: 'Il tastierino non accetta nessun codice.' };
    }
    if (a.installer_active) {
      return { kind: 'warn', icon: 'tool', title: 'Modalità installatore attiva', text: 'Il tastierino funziona anche con il coperchio aperto.' };
    }
    if (a.locked_out) {
      return { kind: 'warn', icon: 'alert', title: 'Troppi codici errati', text: `Riprova tra ${a.lockout_seconds_left || 60} secondi.` };
    }
    return { kind: 'ok', icon: 'check', title: 'Tutto a posto', text: 'Il tastierino accetta i codici.' };
  }

  _lastAccesses() {
    return this._users()
      .filter((u) => u.last_access)
      .sort((a, b) => (b.last_access > a.last_access ? 1 : -1))
      .slice(0, 3);
  }

  // ---------------------------------------------------------------- servizi
  _serviceData(data) {
    const device = this._deviceId();
    return device ? { device_id: device, ...data } : { ...data };
  }

  _call(service, data = {}) {
    return this._hass.callService('rfid_access_control', service, this._serviceData(data));
  }

  async _resp(service, data = {}) {
    const response = await this._hass.callWS({
      type: 'call_service',
      domain: 'rfid_access_control',
      service,
      service_data: this._serviceData(data),
      return_response: true,
    });
    return (response && response.response) || {};
  }

  _pinFailure(result, fallback) {
    if (result.locked_out) return `Troppi tentativi errati. Riprova tra ${result.seconds_left || 60} secondi.`;
    if (result.not_set) return 'PIN non ancora impostato: completa la configurazione.';
    return fallback;
  }

  // ---------------------------------------------------------------- stato della card
  _touch() {
    if (this._lockTimer) clearTimeout(this._lockTimer);
    this._lockTimer = setTimeout(() => this._lock(), this.config.lock_timeout * 60 * 1000);
  }

  _clearTimers() {
    if (this._lockTimer) clearTimeout(this._lockTimer);
    if (this._tickTimer) clearInterval(this._tickTimer);
    if (this._listenTimer) clearTimeout(this._listenTimer);
    this._lockTimer = this._tickTimer = this._listenTimer = null;
  }

  _lock() {
    this._clearTimers();
    this._unlocked = false;
    this._operatorPin = '';
    this._pin = '';
    this._pinPurpose = '';
    this._adminCurrent = '';
    this._adminNew = '';
    this._copyTarget = '';
    this._kpAdd = null;
    this._sos = { open: false, entity: '', service: '', name: '' };
    this._draft = null;
    this._listening = false;
    this._msg = null;
    this._view = 'home';
    this._render();
  }

  _go(view, extra = {}) {
    this._view = view;
    this._msg = null;
    this._pinError = '';
    Object.assign(this, extra);
    this._touch();
    this._render();
  }

  _setMsg(text, kind = 'ok') {
    this._msg = { text, kind };
  }

  // ---------------------------------------------------------------- PIN a schermo
  _startPin(purpose, target) {
    this._pin = '';
    this._pinPurpose = purpose;
    this._pinTarget = target;
    this._go('pin');
  }

  _pinTitle() {
    const titles = {
      admin: ['PIN admin', 'Per gestire gli utenti del tastierino'],
      operator: ['PIN operatore', 'Per il menu operatore'],
      unlock: ['PIN operatore', 'Per sbloccare il tastierino dopo il tamper'],
      newOperator: ['Nuovo PIN operatore', 'Da 4 a 8 cifre'],
      confirmOperator: ['Ripeti il PIN operatore', 'Per confermare'],
      setupAdmin: ['Scegli il PIN admin', 'Da 4 a 8 cifre. Non usare valori di esempio'],
      confirmAdmin: ['Ripeti il PIN admin', 'Per confermare'],
      setupOperator: ['Scegli il PIN operatore', 'Da 4 a 8 cifre, diverso dal PIN admin'],
      confirmSetupOperator: ['Ripeti il PIN operatore', 'Per confermare'],
      revealPin: ['PIN admin', 'Per vedere il PIN di questo utente'],
      changeAdminCurrent: ['PIN admin attuale', 'Per cambiarlo'],
      changeAdminNew: ['Nuovo PIN admin', 'Da 4 a 8 cifre, diverso dal PIN operatore'],
      changeAdminConfirm: ['Ripeti il nuovo PIN admin', 'Per confermare'],
      copyUser: ['PIN admin di destinazione', `Del tastierino ${this._copyTargetLabel()}`],
    };
    return titles[this._pinPurpose] || ['PIN', ''];
  }

  _pinHtml() {
    const [title, sub] = this._pinTitle();
    const n = this._pin.length;
    const dots = Math.max(4, Math.min(8, n));
    const dotHtml = Array.from({ length: dots }, (_, i) => `<span class="${i < n ? 'on' : ''}"></span>`).join('');
    const keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '', '0', 'del'].map((k) => {
      if (k === '') return '<span></span>';
      if (k === 'del') return `<button class="key fn" data-act="key-del" aria-label="Cancella" ${this._busy ? 'disabled' : ''}>⌫</button>`;
      return `<button class="key" data-act="key" data-v="${k}" aria-label="${k}" ${this._busy ? 'disabled' : ''}>${k}</button>`;
    }).join('');
    const ready = n >= 4 && !this._busy;
    return `
      ${this._topHtml(title, this._pinBack())}
      <div class="center">
        <div class="sub">${rfidEsc(sub)}</div>
        <div class="dots" aria-label="${n} cifre inserite">${dotHtml}</div>
        ${this._pinError ? `<div class="msg err" role="alert">${rfidEsc(this._pinError)}</div>` : ''}
        <div class="keys">${keys}</div>
        <button class="btn" data-act="pin-submit" ${ready ? '' : 'disabled'} style="max-width:300px;width:100%">Entra</button>
      </div>`;
  }

  _pinBack() {
    const back = {
      admin: 'home', operator: 'home', unlock: 'tamper', newOperator: 'operator', confirmOperator: 'operator',
      setupAdmin: 'home', confirmAdmin: 'home', setupOperator: 'home', confirmSetupOperator: 'home',
      revealPin: 'newuser', copyUser: 'newuser', changeAdminCurrent: 'users', changeAdminNew: 'users', changeAdminConfirm: 'users',
    };
    return back[this._pinPurpose] || 'home';
  }

  async _submitPin() {
    const pin = this._pin;
    if (pin.length < 4 || this._busy) return;
    this._busy = true;
    this._pinError = '';
    try {
      const purpose = this._pinPurpose;
      if (purpose === 'admin') {
        const r = await this._resp('verify_admin_pin', { pin });
        if (!r.valid) return this._pinFail(this._pinFailure(r, 'PIN admin non corretto'));
        this._unlocked = true;
        return this._go(this._pinTarget);
      }
      if (purpose === 'operator') {
        const r = await this._resp('verify_operator_pin', { pin });
        if (!r.valid) return this._pinFail(this._pinFailure(r, 'PIN operatore non corretto'));
        this._operatorPin = pin;
        this._unlocked = true;
        return this._go('operator', { _pin: '' });
      }
      if (purpose === 'revealPin') {
        // Il server controlla il PIN admin (conta nel blocco) e restituisce il PIN dell'utente.
        const r = await this._resp('get_user_pin', { admin_pin: pin, user_id: this._draft?.userId });
        if (!this._draft) return this._go('users');
        this._draft.shownPin = String(r.pin || '');
        this._draft.pinVisible = true;
        this._pin = '';
        return this._go('newuser');
      }
      if (purpose === 'changeAdminCurrent') {
        const r = await this._resp('verify_admin_pin', { pin });
        if (!r.valid) return this._pinFail(this._pinFailure(r, 'PIN admin non corretto'));
        this._adminCurrent = pin;
        this._pin = '';
        return this._go('pin', { _pinPurpose: 'changeAdminNew' });
      }
      if (purpose === 'changeAdminNew') {
        this._adminNew = pin;
        this._pin = '';
        return this._go('pin', { _pinPurpose: 'changeAdminConfirm' });
      }
      if (purpose === 'changeAdminConfirm') {
        if (pin !== this._adminNew) return this._pinFail('I PIN non corrispondono. Riprova.', 'changeAdminNew');
        await this._call('set_admin_pin', { new_pin: pin, current_pin: this._adminCurrent });
        this._adminCurrent = '';
        this._adminNew = '';
        this._pin = '';
        this._setMsg('PIN admin cambiato.', 'ok');
        return this._go('users');
      }
      if (purpose === 'copyUser') {
        // Il server controlla il PIN admin di destinazione e scrive la copia; il PIN dell'utente non torna qui.
        const target = this._copyTarget;
        const name = this._draft?.name || '';
        await this._call('copy_user', { user_id: this._draft?.userId, target_device_id: target, admin_pin: pin });
        this._draft = null;
        this._copyTarget = '';
        this._pin = '';
        this._setMsg(`Utente "${name}" copiato su ${rfidKeypadLabel(target)}. Controlla le sue azioni: possono essere diverse.`, 'ok');
        return this._go('users');
      }
      if (purpose === 'unlock') {
        await this._call('clear_tamper_lock', { pin });
        this._operatorPin = pin;
        this._setMsg('Tastierino sbloccato. Ora accetta di nuovo i codici.', 'ok');
        return this._go('home');
      }
      if (purpose === 'newOperator') {
        this._draft = { newOperator: pin };
        this._pin = '';
        return this._go('pin', { _pinPurpose: 'confirmOperator' });
      }
      if (purpose === 'confirmOperator') {
        if (pin !== this._draft?.newOperator) return this._pinFail('I PIN non corrispondono. Riprova.', 'newOperator');
        await this._call('set_operator_pin', { new_pin: pin, current_pin: this._operatorPin });
        this._operatorPin = pin;
        this._setMsg('PIN operatore cambiato.', 'ok');
        return this._go('operator');
      }
      if (purpose === 'setupAdmin') {
        this._draft = { setupAdmin: pin };
        this._pin = '';
        return this._go('pin', { _pinPurpose: 'confirmAdmin' });
      }
      if (purpose === 'confirmAdmin') {
        if (pin !== this._draft?.setupAdmin) return this._pinFail('I PIN non corrispondono. Riprova.', 'setupAdmin');
        await this._call('set_admin_pin', { new_pin: pin });
        this._draft = null;
        this._pin = '';
        this._setMsg('PIN admin salvato.', 'ok');
        return this._go('home');
      }
      if (purpose === 'setupOperator') {
        this._draft = { setupOperator: pin };
        this._pin = '';
        return this._go('pin', { _pinPurpose: 'confirmSetupOperator' });
      }
      if (purpose === 'confirmSetupOperator') {
        if (pin !== this._draft?.setupOperator) return this._pinFail('I PIN non corrispondono. Riprova.', 'setupOperator');
        await this._call('set_operator_pin', { new_pin: pin });
        this._draft = null;
        this._pin = '';
        this._setMsg('PIN operatore salvato. La configurazione è completa.', 'ok');
        return this._go('home');
      }
    } catch (err) {
      this._pinFail(err.message || 'Operazione non riuscita');
    } finally {
      this._busy = false;
    }
  }

  _pinFail(text, backPurpose) {
    this._pin = '';
    this._pinError = text;
    if (backPurpose) this._pinPurpose = backPurpose;
    this._busy = false;
    this._render();
  }

  // ---------------------------------------------------------------- viste
  _topHtml(title, back) {
    return `
      <div class="top">
        ${back ? `<button class="ib" data-act="go" data-v="${back}" aria-label="Indietro">${rfidIcon('back')}</button>` : ''}
        <h1>${rfidEsc(title)}</h1>
        ${this._unlocked && back !== 'home' ? `<button class="ib" data-act="lock" aria-label="Blocca e esci">${rfidIcon('lock', 20)}</button>` : ''}
      </div>`;
  }

  _msgHtml() {
    return this._msg ? `<div class="msg ${this._msg.kind === 'ok' ? 'ok' : 'err'}" role="status">${rfidEsc(this._msg.text)}</div>` : '';
  }

  _render() {
    if (!this.shadowRoot || !this.config) return;
    this._stopTick();
    let body;
    if (!this._hass) {
      body = '<div class="loading">Caricamento…</div>';
    } else if (this._view === 'pin') {
      body = this._pinHtml();
    } else if (this._view === 'tamper') {
      body = this._tamperHtml();
    } else if (this._view === 'users') {
      body = this._usersHtml();
    } else if (this._view === 'newuser') {
      body = this._newUserHtml();
    } else if (this._view === 'addkeypad') {
      body = this._addKeypadHtml();
    } else if (this._view === 'operator') {
      body = this._operatorHtml();
    } else {
      body = this._homeHtml();
    }
    this.shadowRoot.innerHTML = `
      <style>${RFID_CARD_CSS}</style>
      <div class="wrap">
        ${body}
        <div class="foot">RFID Access Control v${RFID_CARD_VERSION}</div>
      </div>`;
    if (this._view === 'operator') this._startTick();
    if (this._view === 'newuser') this._focusDraft();
  }

  _focusDraft() {
    const el = this.shadowRoot.querySelector('[data-autofocus]');
    if (el) el.focus();
  }

  // Home ---------------------------------------------------------------
  _homeHtml() {
    const a = this._attrs();
    if (a.setup_required) return this._setupHtml();
    const st = this._status();
    const users = this._users();
    const active = users.filter((u) => u.access_status === 'active').length;
    const last = this._lastAccesses();
    return `
      <div class="top"><h1>${rfidEsc(this.config.title)}</h1></div>
      ${this._keypadSwitchHtml()}
      <div class="stack">
        <div class="state ${st.kind}">
          <div class="dot">${rfidIcon(st.icon, 24)}</div>
          <div class="grow"><strong>${rfidEsc(st.title)}</strong><span class="sub">${rfidEsc(st.text)}</span></div>
        </div>
        ${st.kind === 'alarm' ? `<button class="btn warn" data-act="go" data-v="tamper">Vedi allarme</button>` : ''}
        <div class="stat" style="max-width:100%"><b>${active}</b><span class="sub">utenti attivi su ${users.length}</span></div>
        ${this._msgHtml()}
        <button class="btn" data-act="manage">${rfidIcon('key', 22)}<span class="btn-line">Gestisci utenti<small>Aggiungi, modifica, disattiva</small></span></button>
        <button class="btn sec" data-act="operator-enter">${rfidIcon('tool', 22)}<span class="btn-line">Menu operatore<small>Coperchio, installatore, prova codice</small></span></button>
        ${last.length ? `
          <div class="card-box">
            <div class="label" style="margin-bottom:6px">Ultimi accessi</div>
            ${last.map((u) => `<div class="row" style="padding:6px 0"><span class="grow">${rfidEsc(u.user_name)}</span><span class="sub">${rfidEsc(this._timeLabel(u.last_access))}</span></div>`).join('')}
          </div>` : ''}
      </div>`;
  }

  _timeLabel(iso) {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleString([], { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  }

  _setupHtml() {
    const a = this._attrs();
    const adminMissing = !a.admin_pin_set;
    return `
      <div class="top"><h1>${rfidEsc(this.config.title)}</h1></div>
      <div class="stack">
        <div class="state warn">
          <div class="dot">${rfidIcon('key', 24)}</div>
          <div class="grow"><strong>Configurazione iniziale</strong><span class="sub">Scegli ${adminMissing ? 'il PIN admin e il PIN operatore' : 'il PIN operatore'} di questo tastierino. Non usare valori di esempio.</span></div>
        </div>
        ${this._msgHtml()}
        <button class="btn" data-act="setup">Imposta ${adminMissing ? 'i PIN' : 'il PIN operatore'}</button>
      </div>`;
  }

  // Allarme coperchio -----------------------------------------------------
  _tamperHtml() {
    const a = this._attrs();
    const open = !!a.tamper_active;
    return `
      ${this._topHtml('Allarme coperchio', 'home')}
      <div class="stack">
        <div class="state alarm">
          <div class="dot">${rfidIcon('alert', 24)}</div>
          <div class="grow"><strong>${open ? 'Coperchio aperto' : 'Bloccato dopo apertura coperchio'}</strong><span class="sub">Il tastierino non accetta nessun codice.</span></div>
        </div>
        <div class="label">Per riattivarlo</div>
        <div class="card-box stack" style="gap:14px">
          <div class="row" style="align-items:flex-start">
            <span class="step-no" style="width:28px;height:28px;border-radius:50%;background:rgba(227,116,0,.22);color:var(--primary-text-color, #1b1f24);font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0">1</span>
            <div class="grow"><strong>Chiudi il coperchio</strong><div class="sub">${open ? 'Il sensore lo vede ancora aperto' : 'Il sensore vede il coperchio chiuso'}</div></div>
          </div>
          <div class="row" style="align-items:flex-start">
            <span style="width:28px;height:28px;border-radius:50%;background:rgba(127,127,127,.18);font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0">2</span>
            <div class="grow"><strong>Sblocca con il PIN operatore</strong><div class="sub">Sul tastierino: PIN operatore, poi ARMA TUTTO. Oppure da qui.</div></div>
          </div>
        </div>
        ${this._msgHtml()}
        <button class="btn" data-act="tamper-unlock">${rfidIcon('lock', 20)}Sblocca da qui</button>
      </div>`;
  }

  // Utenti ---------------------------------------------------------------
  _usersHtml() {
    const users = this._users();
    return `
      ${this._topHtml(`Utenti ${users.length}`, 'home')}
      <div class="stack">
        <input class="search" type="search" data-field="search" placeholder="Cerca per nome" aria-label="Cerca per nome" value="${rfidEsc(this._search)}">
        ${this._msgHtml()}
        <div id="ulist">${this._userRows()}</div>
        <button class="btn" data-act="new-user">${rfidIcon('plus', 20)}Nuovo utente</button>
        <button class="btn sec" data-act="change-admin">${rfidIcon('key', 20)}Cambia PIN admin</button>
      </div>`;
  }

  _userRows() {
    const q = this._search.trim().toLowerCase();
    const users = this._users().filter((u) => !q || String(u.user_name).toLowerCase().includes(q));
    if (!users.length) return `<p class="sub">${q ? 'Nessun utente con questo nome.' : 'Nessun utente. Premi "Nuovo utente".'}</p>`;
    return users.map((u) => this._userRow(u)).join('');
  }

  _userRow(u) {
    const enabled = u.enabled !== false;
    const tags = [];
    if (u.has_pin) tags.push('<span class="tag pin">PIN</span>');
    if (u.has_rfid) tags.push('<span class="tag rfid">Tessera</span>');
    if (u.valid_from || u.valid_until || u.max_uses) {
      const until = u.valid_until ? `fino al ${this._dateLabel(u.valid_until)}` : 'temporaneo';
      const uses = u.max_uses ? ` · ${u.uses || 0}/${u.max_uses}` : '';
      tags.push(`<span class="tag temp">${rfidEsc(until + uses)}</span>`);
    }
    if (!enabled) tags.push('<span class="tag off">Disattivato</span>');
    return `
      <div class="user ${enabled ? '' : 'off'}">
        <span class="avatar" style="background:${enabled ? rfidColor(u.user_name) : '#9aa4b0'}" aria-hidden="true">${rfidEsc(rfidInitials(u.user_name))}</span>
        <div class="grow" style="min-width:0">
          <button class="name" data-act="edit-user" data-id="${rfidEsc(u.user_id)}">${rfidEsc(u.user_name)}</button>
          <div class="tags" style="margin-top:4px">${tags.join('')}</div>
        </div>
        <button class="sw" role="switch" aria-checked="${enabled}" aria-label="${enabled ? 'Attivo' : 'Disattivato'}: ${rfidEsc(u.user_name)}" data-act="toggle-user" data-id="${rfidEsc(u.user_id)}"><span></span></button>
      </div>`;
  }

  _dateLabel(value) {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return value;
    return d.toLocaleString([], { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  }

  // Nuovo utente / modifica ----------------------------------------------
  _newUserHtml() {
    const d = this._draft;
    const editing = d.mode === 'edit';
    const names = ['Chi è', 'Come entra', 'Cosa succede'];
    const steps = names.map((n, i) => `
      <button data-act="step" data-v="${i + 1}" class="${i + 1 < d.step ? 'done' : ''} ${i + 1 === d.step ? 'cur' : ''}"><i></i>${i + 1}. ${n}</button>`).join('');
    let body = '';
    if (d.step === 1) {
      body = `
        <label class="label" for="rfid-name">Come si chiama?</label>
        <input id="rfid-name" class="field" type="text" data-field="name" value="${rfidEsc(d.name)}" ${d.name ? '' : 'data-autofocus'} placeholder="Es: Mario Rossi">
        <span class="hint">Il nome compare nel registro e nelle notifiche.</span>`;
    } else if (d.step === 2) {
      body = this._entryStepHtml();
    } else {
      body = this._actionsStepHtml();
    }
    return `
      ${this._topHtml(editing ? `Modifica: ${d.name || ''}` : 'Nuovo utente', 'users')}
      <div class="stack">
        <div class="steps">${steps}</div>
        ${this._msgHtml()}
        ${body}
        <div class="row" style="margin-top:4px">
          <button class="btn sec grow" data-act="step-back" ${d.step === 1 ? 'disabled' : ''}>Indietro</button>
          ${d.step < 3
            ? `<button class="btn grow" data-act="step-next">Avanti</button>`
            : `<button class="btn grow" data-act="save-user" ${this._busy ? 'disabled' : ''}>${editing ? 'Salva modifiche' : 'Crea utente'}</button>`}
        </div>
        ${editing ? this._copyHtml(d) : ''}
        ${editing ? this._deleteHtml(d) : ''}
      </div>`;
  }

  _entryStepHtml() {
    const d = this._draft;
    const editing = d.mode === 'edit';
    const n = d.pin.length;
    const dots = Math.max(4, Math.min(8, n));
    const dotHtml = Array.from({ length: dots }, (_, i) => `<span class="${i < n ? 'on' : ''}"></span>`).join('');
    const keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '', '0', 'del'].map((k) => {
      if (k === '') return '<span></span>';
      if (k === 'del') return '<button class="key fn" data-act="draft-del" aria-label="Cancella">⌫</button>';
      return `<button class="key" data-act="draft-key" data-v="${k}" aria-label="${k}">${k}</button>`;
    }).join('');
    const uses = [[1, '1'], [3, '3'], [10, '10'], [0, '∞']].map(([v, t]) =>
      `<button class="chip ${d.uses === v ? 'on' : ''}" data-act="uses" data-v="${v}" aria-pressed="${d.uses === v}">${t}</button>`).join('');
    return `
      ${editing ? this._currentPinHtml(d) : ''}
      <div class="label">PIN da digitare ${editing ? '<span class="hint">(lascia vuoto per non cambiarlo)</span>' : ''}</div>
      <div class="dots" aria-label="${n} cifre">${dotHtml}</div>
      <div class="keys">${keys}</div>
      <span class="hint">Da 4 a 8 cifre. Deve essere diverso dagli altri utenti.</span>
      <div class="label" style="margin-top:6px">Tessera o portachiavi <span class="hint">(facoltativo)</span></div>
      <div class="row">
        <button class="btn sec grow" data-act="read-rfid" style="${this._listening ? 'border-color:#6539b0;color:#6539b0' : ''}">${rfidIcon('wave', 20)}${this._listening ? 'In ascolto… avvicina la tessera' : 'Leggi tessera dal tastierino'}</button>
      </div>
      <input class="field" type="text" data-field="rfid" value="${rfidEsc(d.rfid)}" placeholder="Codice RFID (oppure leggilo)" aria-label="Codice RFID">
      <div class="card-box stack" style="gap:10px">
        <div class="row">
          <div class="grow"><strong>Accesso temporaneo</strong><div class="sub">Per ospiti, corrieri, ditte</div></div>
          <button class="sw" role="switch" aria-checked="${d.temp}" aria-label="Accesso temporaneo" data-act="toggle-temp"><span></span></button>
        </div>
        ${d.temp ? `
          <div class="row" style="align-items:stretch">
            <label class="grow hint">Dal<input class="field" type="datetime-local" data-field="from" value="${rfidEsc(d.from)}"></label>
            <label class="grow hint">Al<input class="field" type="datetime-local" data-field="until" value="${rfidEsc(d.until)}"></label>
          </div>
          <div class="row" style="justify-content:space-between;flex-wrap:wrap">
            <span>Numero di accessi</span>
            <div class="row" style="gap:6px">${uses}</div>
          </div>` : ''}
      </div>`;
  }

  _actionsStepHtml() {
    const d = this._draft;
    const rows = d.actions.map((a) => {
      const key = rfidKeypad(a.keypad_action);
      // Per le azioni scelte: quale tasto del tastierino le attiva (icona grande).
      const picker = a.selected ? `
        <div class="kp-row" role="group" aria-label="Quale tasto attiva ${rfidEsc(a.title)}">
          ${RFID_KEYPAD.map((k) => `<button class="kp ${k.value === key.value ? 'on' : ''}" data-act="kp" data-id="${rfidEsc(a.id)}" data-v="${k.value}" aria-label="${rfidEsc(k.label)}" aria-pressed="${k.value === key.value}">${rfidIcon(k.icon, 24)}<span>${rfidEsc(k.label)}</span></button>`).join('')}
        </div>` : '';
      return `
      <div class="actwrap">
        <button class="act ${a.selected ? 'on' : ''}" data-act="toggle-action" data-id="${rfidEsc(a.id)}" aria-pressed="${a.selected}">
          <span class="box">${a.selected ? '<span style="display:block;color:#fff;font-size:14px;text-align:center;line-height:18px">✓</span>' : ''}</span>
          <span class="grow" style="display:flex;flex-direction:column;gap:2px">
            <span style="font-weight:600">${rfidEsc(a.title)}</span>
            <span class="sub">${rfidEsc(a.sub)}</span>
          </span>
          <span class="kpi" title="${rfidEsc(key.label)}" aria-label="Tasto: ${rfidEsc(key.label)}">${rfidIcon(key.icon, 22)}</span>
        </button>
        ${picker}
      </div>`;
    }).join('');
    const options = Object.keys(this._entityGroups()).map((domain) => this._entityGroups()[domain].map((e) =>
      `<option value="${rfidEsc(e.id)}" ${d.custom.entity === e.id ? 'selected' : ''}>${rfidEsc(e.name)} (${rfidEsc(e.id)})</option>`).join('')).join('');
    return `
      <div class="label">Quando entra, cosa succede?</div>
      ${rows || '<p class="sub">Nessuna azione disponibile: non ci sono luci, serrature o script in Home Assistant.</p>'}
      ${d.customOpen ? `
        <div class="card-box stack" style="gap:10px">
          <label class="hint">Entità<select class="field" data-field="custom-entity"><option value="">— Scegli —</option>${options}</select></label>
          <label class="hint">Servizio<input class="field" type="text" data-field="custom-service" value="${rfidEsc(d.custom.service)}" placeholder="es: light.turn_on"></label>
          <label class="hint">Nome<input class="field" type="text" data-field="custom-name" value="${rfidEsc(d.custom.name)}" placeholder="Es: Apri il cancello"></label>
          <div class="row"><button class="btn grow" data-act="add-custom">Aggiungi</button><button class="btn sec grow" data-act="close-custom">Annulla</button></div>
        </div>` : `<button class="btn sec" data-act="open-custom">${rfidIcon('plus', 18)}Azione personalizzata</button>`}`;
  }

  // Più tastierini ------------------------------------------------------
  _keypadSwitchHtml() {
    const list = this._keypads();
    if (list.length < 2) return '';
    const current = this._entity();
    const chips = list.map((k) => `<button class="chip ${k.entity === current ? 'on' : ''}" data-act="kp-select" data-v="${rfidEsc(k.entity)}" aria-pressed="${k.entity === current}">${rfidEsc(k.label)}</button>`).join('');
    return `<div class="kp-switch" role="group" aria-label="Tastierino">${chips}</div>`;
  }

  _copyTargetLabel() {
    return rfidKeypadLabel(this._copyTarget);
  }

  _copyHtml(d) {
    const current = this._deviceId();
    const others = this._keypads().filter((k) => k.deviceId !== current);
    if (!others.length) return '';
    if (!d.copyOpen) {
      return `<button class="btn sec" data-act="copy-open">${rfidIcon('plus', 18)}Copia su altro tastierino</button>`;
    }
    const options = others.map((k) => `<option value="${rfidEsc(k.deviceId)}" ${this._copyTarget === k.deviceId ? 'selected' : ''}>${rfidEsc(k.label)}</option>`).join('');
    return `
      <div class="card-box stack" style="gap:10px">
        <strong>Copia su altro tastierino</strong>
        <span class="sub">Copia l'utente com'è salvato: nome, PIN, tessera e azioni. Controlla le azioni: le entità possono essere diverse sull'altro tastierino.</span>
        <label class="hint">Tastierino<select class="field" data-field="copy-target"><option value="">— Scegli —</option>${options}</select></label>
        <div class="row"><button class="btn grow" data-act="copy-start" ${this._copyTarget ? '' : 'disabled'}>Copia</button><button class="btn sec grow" data-act="copy-close">Annulla</button></div>
      </div>`;
  }

  _addKeypadHtml() {
    const k = this._kpAdd || { found: null, deviceId: '', topic: '', busy: false };
    const found = k.found;
    // Tastierini già configurati: compaiono ma non si possono scegliere di nuovo.
    const configured = this._keypads();
    const isAdded = (d) => configured.some((c) => (c.topic && c.topic === d.topic) || c.deviceId === rfidSlug(d.friendly_name));
    let list = '';
    if (found !== null) {
      list = found.length
        ? found.map((d, i) => {
          const added = isAdded(d);
          return `
          <button class="act ${!added && d.topic === k.topic ? 'on' : ''}" data-act="kp-pick" data-v="${i}" aria-pressed="${!added && d.topic === k.topic}" ${added ? 'disabled' : ''}>
            <span class="grow" style="display:flex;flex-direction:column;gap:2px"><span style="font-weight:600">${rfidEsc(d.friendly_name)}</span><span class="sub">${rfidEsc(d.model)} · ${rfidEsc(d.topic)}</span></span>
            ${added ? '<span class="tag off">già aggiunto</span>' : ''}
          </button>`;
        }).join('')
        : '<p class="sub">Nessun tastierino trovato. Controlla che Zigbee2MQTT sia acceso e il tastierino collegato.</p>';
    }
    return `
      ${this._topHtml('Aggiungi tastierino', 'operator')}
      <div class="stack">
        ${this._msgHtml()}
        <div class="card-box stack" style="gap:10px">
          <span class="sub">Legge l'elenco dei dispositivi da Zigbee2MQTT. Se il tastierino non compare, scrivilo a mano qui sotto.</span>
          <button class="btn" data-act="kp-discover" ${k.busy ? 'disabled' : ''}>${rfidIcon('wave', 20)}${k.busy ? 'Ricerca in corso…' : 'Cerca tastierini'}</button>
        </div>
        ${list ? `<div class="label">Trovati</div>${list}` : ''}
        <div class="card-box stack" style="gap:10px">
          <label class="hint">Nome del tastierino<input class="field" type="text" data-field="kp-device" value="${rfidEsc(k.deviceId)}" placeholder="es: tastierino_garage"></label>
          <label class="hint">Topic MQTT<input class="field" type="text" data-field="kp-topic" value="${rfidEsc(k.topic)}" placeholder="zigbee2mqtt/tastierino_garage"></label>
          <button class="btn" data-act="kp-create" ${k.busy ? 'disabled' : ''}>Aggiungi tastierino</button>
        </div>
      </div>`;
  }

  async _discoverKeypads() {
    this._kpAdd = { ...(this._kpAdd || {}), busy: true };
    this._render();
    try {
      const r = await this._resp('discover_keypads');
      this._kpAdd = { ...this._kpAdd, busy: false, found: Array.isArray(r.devices) ? r.devices : [] };
    } catch (err) {
      this._kpAdd = { ...this._kpAdd, busy: false, found: [] };
      this._setMsg(err.message || 'Ricerca non riuscita', 'err');
    }
    this._render();
  }

  _pickKeypad(index) {
    const d = ((this._kpAdd && this._kpAdd.found) || [])[Number(index)];
    if (!d) return undefined;
    const configured = this._keypads();
    if (configured.some((c) => (c.topic && c.topic === d.topic) || c.deviceId === rfidSlug(d.friendly_name))) {
      return undefined;
    }
    this._kpAdd = { ...this._kpAdd, deviceId: rfidSlug(d.friendly_name), topic: d.topic };
    return this._render();
  }

  _kpFail(text) {
    this._kpAdd = { ...(this._kpAdd || {}), busy: false };
    this._setMsg(text, 'err');
    this._render();
  }

  // Crea la voce dell'integrazione con lo stesso flusso che usa Impostazioni → Integrazioni.
  async _createKeypad() {
    const k = this._kpAdd || {};
    if (!k.deviceId) return this._kpFail('Scrivi il nome del tastierino.');
    if (!k.topic || !k.topic.includes('/')) return this._kpFail('Il topic deve avere la forma zigbee2mqtt/nome.');
    this._kpAdd = { ...k, busy: true };
    this._render();
    let flowId = '';
    try {
      const flow = await this._hass.callApi('POST', 'config/config_entries/flow', { handler: 'rfid_access_control' });
      flowId = flow.flow_id;
      const res = await this._hass.callApi('POST', `config/config_entries/flow/${flowId}`, {
        device_id: k.deviceId, mqtt_topic: k.topic,
      });
      if (res.type === 'create_entry') {
        this._kpAdd = null;
        this._setMsg(`Tastierino "${k.deviceId}" aggiunto. Compare tra i tastierini tra qualche secondo.`, 'ok');
        return this._go('operator');
      }
      const reasons = { already_configured: 'Questo tastierino è già aggiunto.' };
      let text = 'Controlla nome e topic del tastierino.';
      if (res.type === 'abort') text = reasons[res.reason] || 'Aggiunta annullata.';
      await this._hass.callApi('DELETE', `config/config_entries/flow/${flowId}`).catch(() => {});
      return this._kpFail(text);
    } catch (err) {
      if (flowId) await this._hass.callApi('DELETE', `config/config_entries/flow/${flowId}`).catch(() => {});
      return this._kpFail(err.message || 'Aggiunta non riuscita');
    }
  }

  _deleteHtml(d) {
    if (d.confirmDelete) {
      return `
        <div class="card-box stack" style="gap:10px;border:2px solid #c5221f">
          <strong>Eliminare ${rfidEsc(d.name)}?</strong>
          <span class="sub">Non si può annullare.</span>
          <div class="row">
            <button class="btn danger grow" data-act="delete-user" ${this._busy ? 'disabled' : ''}>Sì, elimina</button>
            <button class="btn sec grow" data-act="delete-cancel">Annulla</button>
          </div>
        </div>`;
    }
    return `<button class="btn danger" data-act="delete-ask">${rfidIcon('close', 20)}Elimina utente</button>`;
  }

  _currentPinHtml(d) {
    if (!d.hasPin) return '<span class="hint">Questo utente non ha un PIN.</span>';
    const shown = d.pinVisible && d.shownPin ? rfidEsc(d.shownPin) : '••••';
    return `
      <div class="pinline">
        <span class="label">PIN attuale</span>
        <span class="row" style="gap:6px"><b>${shown}</b>
          <button class="ib" data-act="reveal-pin" aria-label="${d.pinVisible ? 'Nascondi il PIN' : 'Mostra il PIN'}">${rfidIcon(d.pinVisible ? 'eyeoff' : 'eye', 22)}</button>
        </span>
      </div>`;
  }

  _revealPin() {
    const d = this._draft;
    if (!d) return undefined;
    if (d.shownPin) {
      d.pinVisible = !d.pinVisible;
      return this._render();
    }
    return this._startPin('revealPin', 'newuser');
  }

  async _deleteUser() {
    const d = this._draft;
    if (!d || this._busy) return;
    this._busy = true;
    this._render();
    try {
      await this._call('remove_user', { user_id: d.userId });
      this._draft = null;
      this._busy = false;
      this._setMsg(`Utente "${d.name}" eliminato.`, 'ok');
      this._view = 'users';
      this._render();
    } catch (err) {
      this._busy = false;
      this._fail(err.message || 'Eliminazione non riuscita');
    }
  }

  _sosHtml() {
    const list = this._attrs().sos_actions || [];
    const f = this._sos;
    const rows = list.length
      ? list.map((s) => `
        <div class="row" style="padding:6px 0">
          <span class="grow"><strong>${rfidEsc(s.action_name)}</strong><span class="sub" style="display:block">${rfidEsc(s.service)} → ${rfidEsc(s.entity_id)}</span></span>
          <button class="btn small sec" data-act="sos-remove" data-id="${rfidEsc(s.action_name)}" aria-label="Rimuovi ${rfidEsc(s.action_name)}">Rimuovi</button>
        </div>`).join('')
      : '<span class="sub">Nessuna azione SOS: il tasto SOS registra solo l\'evento.</span>';
    const options = Object.values(this._entityGroups()).flat().map((e) =>
      `<option value="${rfidEsc(e.id)}" ${f.entity === e.id ? 'selected' : ''}>${rfidEsc(e.name)} (${rfidEsc(e.id)})</option>`).join('');
    return `
      <div class="card-box stack" style="gap:10px">
        <div class="row">${rfidIcon('alert', 22)}<div class="grow"><strong>Tasto SOS</strong><div class="sub">Azioni globali: partono con il tasto SOS, per tutti, anche senza codice.</div></div></div>
        ${rows}
        ${f.open ? `
          <div class="card-box stack" style="gap:10px">
            <label class="hint">Entità<select class="field" data-field="sos-entity"><option value="">— Scegli —</option>${options}</select></label>
            <label class="hint">Servizio<input class="field" type="text" data-field="sos-service" value="${rfidEsc(f.service)}" placeholder="es: siren.turn_on"></label>
            <label class="hint">Nome<input class="field" type="text" data-field="sos-name" value="${rfidEsc(f.name)}" placeholder="Es: Sirena cortile"></label>
            <div class="row"><button class="btn grow" data-act="sos-add">Aggiungi</button><button class="btn sec grow" data-act="sos-close">Annulla</button></div>
          </div>` : `<button class="btn sec" data-act="sos-open">${rfidIcon('plus', 18)}Aggiungi azione SOS</button>`}
      </div>`;
  }

  async _addSos() {
    const f = this._sos;
    if (!f.entity) return this._sosMsg('Scegli un\'entità.', 'err');
    if (!f.service || !f.service.includes('.')) return this._sosMsg('Scrivi il servizio nella forma dominio.servizio.', 'err');
    const name = f.name.trim() || `SOS ${f.entity}`;
    try {
      await this._call('add_sos_action', { action_name: name, action_entity: f.entity, action_service: f.service });
      this._sos = { open: false, entity: '', service: '', name: '' };
      return this._sosMsg('Azione SOS aggiunta.', 'ok');
    } catch (err) {
      return this._sosMsg(err.message || 'Operazione non riuscita', 'err');
    }
  }

  async _removeSos(name) {
    try {
      await this._call('remove_sos_action', { action_name: name });
      return this._sosMsg('Azione SOS rimossa.', 'ok');
    } catch (err) {
      return this._sosMsg(err.message || 'Operazione non riuscita', 'err');
    }
  }

  _sosMsg(text, kind) {
    this._setMsg(text, kind);
    this._render();
  }

  _entityGroups() {
    const wanted = ['lock', 'light', 'switch', 'script', 'cover'];
    const groups = {};
    const states = this._hass ? this._hass.states : {};
    Object.keys(states).sort().forEach((id) => {
      const domain = id.split('.')[0];
      if (!wanted.includes(domain)) return;
      const name = states[id].attributes?.friendly_name || id;
      (groups[domain] = groups[domain] || []).push({ id, name, service: this._defaultService(domain) });
    });
    return groups;
  }

  _defaultService(domain) {
    return { lock: 'lock.unlock', light: 'light.turn_on', switch: 'switch.turn_on', script: 'script.turn_on', cover: 'cover.open_cover' }[domain] || '';
  }

  _presetActions() {
    const groups = this._entityGroups();
    const list = [];
    Object.keys(groups).forEach((domain) => groups[domain].slice(0, 6).forEach((e) => {
      const verb = { lock: 'Apri', light: 'Accendi', switch: 'Attiva', script: 'Avvia', cover: 'Apri' }[domain];
      list.push({ id: `p:${e.id}`, title: `${verb} ${e.name}`, sub: e.id, entity_id: e.id, service: e.service, keypad_action: domain === 'lock' ? 'disarm' : 'any', action_name: `${verb} ${e.name}`, existing: false, selected: false });
    }));
    return list;
  }

  // Menu operatore ----------------------------------------------------------
  _operatorHtml() {
    const a = this._attrs();
    const inst = this._installerRemaining();
    const durations = [15, 30, 60].map((m) => `<button class="dur ${this._instMinutes === m ? 'on' : ''}" data-act="inst-pick" data-v="${m}" aria-pressed="${this._instMinutes === m}">${m} min</button>`).join('');
    const test = this._testResult;
    return `
      ${this._topHtml('Menu operatore', 'home')}
      <div class="stack">
        ${this._msgHtml()}
        <div class="label">Stato</div>
        <div class="card-box stack" style="gap:8px">
          <div class="row"><span class="grow">Coperchio</span><strong>${a.tamper_active ? 'Aperto' : 'Chiuso'}</strong></div>
          <div class="row"><span class="grow">Blocco anti-manomissione</span><strong>${a.keypad_locked_by_tamper ? 'Attivo' : 'Nessuno'}</strong></div>
        </div>
        <div class="card-box stack" style="gap:10px;${inst ? 'border:2px solid #8a4b00' : ''}">
          <div class="row">${rfidIcon('tool', 22)}<div class="grow"><strong>Modalità installatore</strong><div class="sub">Il tastierino funziona anche con il coperchio aperto.</div></div></div>
          ${inst ? `
            <div class="row"><span class="countdown" id="countdown">${this._fmtRemaining(inst)}</span><span class="sub">rimasti</span></div>
            <button class="btn sec" data-act="inst-stop">Termina ora</button>` : `
            <div class="row" style="gap:8px">${durations}</div>
            <button class="btn warn" data-act="inst-start">Attiva per ${this._instMinutes} minuti</button>`}
        </div>
        ${this._sosHtml()}
        <button class="btn sec" data-act="kp-add">${rfidIcon('plus', 18)}<span class="btn-line">Aggiungi tastierino<small>Cerca i tastierini in Zigbee2MQTT</small></span></button>
        <div class="card-box stack" style="gap:10px">
          <strong>Prova un codice</strong>
          <span class="sub">Dice di chi è, senza aprire niente.</span>
          <div class="row" style="gap:8px">
            <input class="field" type="password" inputmode="numeric" autocomplete="off" data-field="test-code" aria-label="Codice da provare">
            <button class="btn small" data-act="test-code">Prova</button>
          </div>
          ${test ? `<div class="msg ${test.found ? 'ok' : 'err'}">${test.found ? `<b>${rfidEsc(test.user_name)}</b> · utente ${test.block_reason ? 'non valido adesso' : 'attivo'}` : 'Nessun utente con questo codice'}</div>` : ''}
        </div>
        <button class="btn sec" data-act="change-operator">${rfidIcon('key', 20)}Cambia PIN operatore</button>
      </div>`;
  }

  _installerRemaining() {
    const until = this._attrs().installer_until;
    if (!this._attrs().installer_active || !until) return 0;
    return Math.max(0, Math.round((Date.parse(until) - Date.now()) / 1000));
  }

  _fmtRemaining(seconds) {
    const m = Math.floor(seconds / 60);
    const s = String(seconds % 60).padStart(2, '0');
    return `${m}:${s}`;
  }

  _startTick() {
    this._tickTimer = setInterval(() => {
      const el = this.shadowRoot.getElementById('countdown');
      const left = this._installerRemaining();
      if (el && left > 0) el.textContent = this._fmtRemaining(left);
      else if (left === 0 && this._attrs().installer_active) this._render();
    }, 1000);
  }

  _stopTick() {
    if (this._tickTimer) clearInterval(this._tickTimer);
    this._tickTimer = null;
  }

  // ---------------------------------------------------------------- eventi
  _onClick(e) {
    const el = e.target.closest ? e.target.closest('[data-act]') : null;
    if (!el) return;
    this._touch();
    this._act(el.dataset.act, el);
  }

  _onInput(e) {
    const field = e.target.dataset ? e.target.dataset.field : null;
    if (!field) return;
    if (field === 'search') {
      this._search = e.target.value;
      const list = this.shadowRoot.getElementById('ulist');
      if (list) list.innerHTML = this._userRows();
      return;
    }
    if (field === 'test-code') return;
    if (field === 'copy-target') {
      this._copyTarget = e.target.value;
      return this._render();
    }
    if (field === 'kp-device' || field === 'kp-topic') {
      const key = field === 'kp-device' ? 'deviceId' : 'topic';
      this._kpAdd = { ...(this._kpAdd || { found: null, busy: false }), [key]: e.target.value.trim() };
      return undefined;
    }
    if (field === 'sos-entity') {
      this._sos.entity = e.target.value;
      this._sos.service = this._defaultService(e.target.value.split('.')[0]);
      return this._render();
    }
    if (field === 'sos-service') return void (this._sos.service = e.target.value.trim());
    if (field === 'sos-name') return void (this._sos.name = e.target.value);
    if (!this._draft) return;
    const d = this._draft;
    if (field === 'name') d.name = e.target.value;
    if (field === 'rfid') d.rfid = e.target.value.trim().toUpperCase();
    if (field === 'from') d.from = e.target.value;
    if (field === 'until') d.until = e.target.value;
    if (field === 'custom-entity') {
      d.custom.entity = e.target.value;
      const domain = e.target.value.split('.')[0];
      d.custom.service = this._defaultService(domain);
      this._render();
    }
    if (field === 'custom-service') d.custom.service = e.target.value.trim();
    if (field === 'custom-name') d.custom.name = e.target.value;
  }

  _onKey(e) {
    if (this._view !== 'pin') return;
    if (/^\d$/.test(e.key)) {
      e.preventDefault();
      this._pushDigit(e.key);
    } else if (e.key === 'Backspace') {
      e.preventDefault();
      this._pin = this._pin.slice(0, -1);
      this._render();
    } else if (e.key === 'Enter') {
      e.preventDefault();
      this._submitPin();
    }
  }

  _pushDigit(digit) {
    if (this._pin.length >= 8) return;
    this._pin += digit;
    this._pinError = '';
    this._render();
  }

  _act(name, el) {
    switch (name) {
      case 'go':
        return this._go(el.dataset.v);
      case 'lock':
        return this._lock();
      case 'manage':
        if (this._unlocked) return this._go('users');
        return this._startPin('admin', 'users');
      case 'operator-enter':
        if (this._operatorPin) return this._go('operator');
        return this._startPin('operator', 'operator');
      case 'tamper-unlock':
        return this._startPin('unlock', 'tamper');
      case 'setup': {
        const a = this._attrs();
        return this._startPin(a.admin_pin_set ? 'setupOperator' : 'setupAdmin', 'home');
      }
      case 'key':
        return this._pushDigit(el.dataset.v);
      case 'key-del':
        this._pin = this._pin.slice(0, -1);
        this._pinError = '';
        return this._render();
      case 'pin-submit':
        return this._submitPin();
      case 'edit-user':
        return this._editUser(el.dataset.id);
      case 'new-user':
        return this._newUser();
      case 'toggle-user':
        return this._toggleUser(el.dataset.id);
      case 'step':
        return this._goStep(Number(el.dataset.v));
      case 'step-back':
        return this._goStep(this._draft.step - 1);
      case 'step-next':
        return this._nextStep();
      case 'save-user':
        return this._saveUser();
      case 'draft-key':
        if (this._draft.pin.length < 8) this._draft.pin += el.dataset.v;
        return this._render();
      case 'draft-del':
        this._draft.pin = this._draft.pin.slice(0, -1);
        return this._render();
      case 'read-rfid':
        return this._toggleListen();
      case 'toggle-temp':
        this._draft.temp = !this._draft.temp;
        if (this._draft.temp && !this._draft.from) this._draft.from = this._nowLocal();
        return this._render();
      case 'uses':
        this._draft.uses = Number(el.dataset.v);
        return this._render();
      case 'toggle-action': {
        const item = this._draft.actions.find((a) => a.id === el.dataset.id);
        if (item) item.selected = !item.selected;
        return this._render();
      }
      case 'open-custom':
        this._draft.customOpen = true;
        return this._render();
      case 'close-custom':
        this._draft.customOpen = false;
        return this._render();
      case 'add-custom':
        return this._addCustom();
      case 'inst-pick':
        this._instMinutes = Number(el.dataset.v);
        return this._render();
      case 'inst-start':
        return this._setInstaller(this._instMinutes || 15);
      case 'inst-stop':
        return this._setInstaller(0);
      case 'test-code':
        return this._testCode();
      case 'change-operator':
        return this._startPin('newOperator', 'operator');
      case 'change-admin':
        return this._startPin('changeAdminCurrent', 'users');
      case 'kp':
        if (this._draft) {
          const item = this._draft.actions.find((a) => a.id === el.dataset.id);
          if (item) item.keypad_action = el.dataset.v;
        }
        return this._render();
      case 'reveal-pin':
        return this._revealPin();
      case 'delete-ask':
        this._draft.confirmDelete = true;
        return this._render();
      case 'delete-cancel':
        this._draft.confirmDelete = false;
        return this._render();
      case 'delete-user':
        return this._deleteUser();
      case 'kp-select':
        this._entityId = el.dataset.v;
        this._msg = null;
        return this._render();
      case 'kp-add':
        this._kpAdd = { found: null, deviceId: '', topic: '', busy: false };
        return this._go('addkeypad');
      case 'kp-discover':
        return this._discoverKeypads();
      case 'kp-pick':
        return this._pickKeypad(el.dataset.v);
      case 'kp-create':
        return this._createKeypad();
      case 'copy-open':
        this._draft.copyOpen = true;
        this._copyTarget = '';
        return this._render();
      case 'copy-close':
        this._draft.copyOpen = false;
        this._copyTarget = '';
        return this._render();
      case 'copy-start':
        return this._startPin('copyUser', 'newuser');
      case 'sos-open':
        this._sos.open = true;
        return this._render();
      case 'sos-close':
        this._sos = { open: false, entity: '', service: '', name: '' };
        return this._render();
      case 'sos-add':
        return this._addSos();
      case 'sos-remove':
        return this._removeSos(el.dataset.id);
      default:
        return undefined;
    }
  }

  _nowLocal() {
    const d = new Date();
    d.setSeconds(0, 0);
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  _newUser() {
    this._search = '';
    this._draft = {
      mode: 'new', userId: '', name: '', pin: '', rfid: '', temp: false, from: '', until: '', uses: 1,
      hasPin: false, shownPin: '', pinVisible: false, confirmDelete: false,
      step: 1, customOpen: false, custom: { entity: '', service: '', name: '' }, actions: this._presetActions(),
    };
    this._msg = null;
    this._view = 'newuser';
    this._touch();
    this._render();
  }

  _editUser(id) {
    const u = this._users().find((x) => x.user_id === id);
    if (!u) return;
    const existing = (u.actions || []).map((a) => ({
      id: `e:${a.action_name}`, title: a.action_name || a.service, sub: `${a.service} → ${a.entity_id}`,
      entity_id: a.entity_id, service: a.service, keypad_action: a.keypad_action || 'any',
      orig_keypad: a.keypad_action || 'any',
      action_name: a.action_name, existing: true, selected: true,
    }));
    const presets = this._presetActions().filter((p) => !existing.some((e) => e.entity_id === p.entity_id));
    this._draft = {
      mode: 'edit', userId: u.user_id, name: u.user_name, pin: '', rfid: u.rfid || '',
      hasPin: !!u.has_pin, shownPin: '', pinVisible: false, confirmDelete: false,
      temp: !!(u.valid_from || u.valid_until || u.max_uses), from: u.valid_from || '', until: u.valid_until || '',
      uses: u.max_uses || 0, step: 1, customOpen: false, custom: { entity: '', service: '', name: '' },
      actions: [...existing, ...presets],
    };
    this._msg = null;
    this._view = 'newuser';
    this._touch();
    this._render();
  }

  _goStep(step) {
    if (!this._draft || step < 1 || step > 3) return;
    if (step > this._draft.step && !this._validateStep(this._draft.step)) return;
    this._draft.step = step;
    this._msg = null;
    this._render();
  }

  _nextStep() {
    this._goStep(this._draft.step + 1);
  }

  _validateStep(step) {
    const d = this._draft;
    this._msg = null;
    if (step === 1 && !d.name.trim()) return this._fail('Inserisci il nome.');
    if (step === 2) {
      if (d.mode === 'new' && !d.pin && !d.rfid) return this._fail('Inserisci un PIN o leggi una tessera.');
      if (d.pin && (d.pin.length < 4 || d.pin.length > 8)) return this._fail('Il PIN deve avere da 4 a 8 cifre.');
      if (d.temp && d.from && d.until && d.until <= d.from) return this._fail('La data di fine deve essere dopo quella di inizio.');
    }
    return true;
  }

  _fail(text) {
    this._setMsg(text, 'err');
    this._render();
    return false;
  }

  _addCustom() {
    const d = this._draft;
    const c = d.custom;
    if (!c.entity) return this._fail('Scegli un\'entità.');
    if (!c.service || !c.service.includes('.')) return this._fail('Scrivi il servizio nella forma dominio.servizio.');
    const title = c.name.trim() || `${c.service} su ${c.entity}`;
    d.actions.push({ id: `c:${Date.now().toString(36)}`, title, sub: `${c.service} → ${c.entity}`, entity_id: c.entity, service: c.service, keypad_action: 'any', action_name: title, existing: false, selected: true });
    d.custom = { entity: '', service: '', name: '' };
    d.customOpen = false;
    this._render();
  }

  _toggleListen() {
    if (this._listening) {
      this._stopListen();
      return this._render();
    }
    this._listening = true;
    this._listenStart = Date.now() / 1000;
    this._listenTimer = setTimeout(() => { this._stopListen(); this._render(); }, 30000);
    this._render();
  }

  _stopListen() {
    this._listening = false;
    if (this._listenTimer) clearTimeout(this._listenTimer);
    this._listenTimer = null;
  }

  _checkRfidEvent() {
    const a = this._attrs();
    if (a.last_code && a.last_code_time && a.last_code_time > this._listenStart && this._draft) {
      this._draft.rfid = String(a.last_code).toUpperCase();
      this._stopListen();
      this._render();
    }
  }

  async _saveUser() {
    const d = this._draft;
    if (this._busy || !this._validateStep(1) || !this._validateStep(2)) return;
    this._busy = true;
    this._render();
    const timing = d.temp
      ? { valid_from: d.from || '', valid_until: d.until || '', max_uses: d.uses || 0 }
      : { valid_from: '', valid_until: '', max_uses: 0 };
    try {
      if (d.mode === 'new') {
        const userId = `${rfidSlug(d.name)}_${Date.now().toString(36)}`;
        await this._call('add_user', { user_id: userId, user_name: d.name.trim(), user_pin: d.pin, user_rfid: d.rfid, ...timing });
        for (const a of d.actions.filter((x) => x.selected)) {
          await this._call('add_action', {
            user_id: userId, action_name: a.action_name, action_entity: a.entity_id, action_service: a.service,
            keypad_action: a.keypad_action,
          });
        }
        this._setMsg(`Utente "${d.name.trim()}" creato.`, 'ok');
      } else {
        await this._call('update_user', { user_id: d.userId, user_name: d.name.trim(), user_pin: d.pin, user_rfid: d.rfid, ...timing });
        // Si toglie e si rimette l'azione anche quando cambia solo il tasto del tastierino.
        for (const a of d.actions.filter((x) => x.existing && (!x.selected || x.keypad_action !== x.orig_keypad))) {
          await this._call('remove_action', { user_id: d.userId, action_name: a.action_name });
        }
        for (const a of d.actions.filter((x) => x.selected && (!x.existing || x.keypad_action !== x.orig_keypad))) {
          await this._call('add_action', {
            user_id: d.userId, action_name: a.action_name, action_entity: a.entity_id, action_service: a.service,
            keypad_action: a.keypad_action,
          });
        }
        this._setMsg('Modifiche salvate.', 'ok');
      }
      this._draft = null;
      this._busy = false;
      this._view = 'users';
      this._render();
    } catch (err) {
      this._busy = false;
      this._fail(err.message || 'Salvataggio non riuscito');
    }
  }

  async _toggleUser(id) {
    const u = this._users().find((x) => x.user_id === id);
    if (!u) return;
    try {
      await this._call('update_user', { user_id: id, enabled: u.enabled === false });
      this._render();
    } catch (err) {
      this._setMsg(err.message || 'Operazione non riuscita', 'err');
      this._render();
    }
  }

  async _setInstaller(minutes) {
    if (!this._operatorPin) return this._go('operator');
    try {
      await this._call('set_installer_mode', { pin: this._operatorPin, minutes });
      this._setMsg(minutes ? `Modalità installatore attiva per ${minutes} minuti.` : 'Modalità installatore spenta.', 'ok');
    } catch (err) {
      this._setMsg(err.message || 'Operazione non riuscita', 'err');
    }
    this._render();
  }

  async _testCode() {
    const input = this.shadowRoot.querySelector('[data-field="test-code"]');
    const code = (input?.value || '').trim();
    if (!code) return;
    if (input) input.value = '';
    try {
      const r = await this._resp('test_access_code', { operator_pin: this._operatorPin, code });
      this._testResult = r;
    } catch (err) {
      this._testResult = null;
      this._setMsg(err.message || 'Prova non riuscita', 'err');
    }
    this._render();
  }
}

if (!customElements.get('rfid-access-control-card')) {
  customElements.define('rfid-access-control-card', RFIDAccessControlCard);
}
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === 'rfid-access-control-card')) {
  window.customCards.push({
    type: 'rfid-access-control-card',
    name: 'RFID Access Control',
    description: 'Controllo accessi con tastierino Zigbee: utenti, tamper, installatore.',
  });
}
