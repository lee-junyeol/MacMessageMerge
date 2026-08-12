class App {
  constructor() {
    this.recipients = new Map();
    this.toastTimer = null;
    this.bind();
    this.renderRecipients();
    this.updateMessageMeta();
  }

  bind() {
    document.getElementById('manualForm').addEventListener('submit', (e) => { e.preventDefault(); this.addManual(); });
    document.getElementById('csvForm').addEventListener('submit', (e) => { e.preventDefault(); this.loadCsv(); });
    document.getElementById('clearBtn').addEventListener('click', () => { this.recipients.clear(); this.renderRecipients(); });
    document.getElementById('messageInput').addEventListener('input', () => this.updateMessageMeta());
    document.getElementById('sendBtn').addEventListener('click', () => this.send());
    document.getElementById('diagnosticsBtn').addEventListener('click', () => this.diagnostics());
    document.getElementById('closeDialogBtn').addEventListener('click', () => document.getElementById('diagnosticsDialog').close());
  }

  async api(url, options = {}) {
    const response = await fetch(url, options);
    const text = await response.text();
    let data;
    try { data = text ? JSON.parse(text) : {}; }
    catch { throw new Error(`서버 응답을 읽을 수 없습니다. (${response.status})`); }
    if (!response.ok || data.success === false) throw new Error(data.message || `요청 실패 (${response.status})`);
    return data;
  }

  key(phone) { return String(phone || '').replace(/\D/g, ''); }

  addRecipient(contact, render = true) {
    const key = this.key(contact.phone);
    if (!key) return false;
    const fresh = !this.recipients.has(key);
    this.recipients.set(key, { name: String(contact.name || '').trim(), phone: String(contact.phone || '').trim() });
    if (render) this.renderRecipients();
    return fresh;
  }

  addManual() {
    const name = document.getElementById('nameInput').value.trim();
    const phone = document.getElementById('phoneInput').value.trim();
    if (!name || !phone) return this.toast('이름과 전화번호를 입력해주세요.');
    if (this.key(phone).length < 10) return this.toast('전화번호를 확인해주세요.');
    const fresh = this.addRecipient({ name, phone });
    document.getElementById('manualForm').reset();
    this.toast(fresh ? '수신자를 추가했습니다.' : '같은 번호의 수신자를 업데이트했습니다.');
  }

  async loadCsv() {
    const input = document.getElementById('csvInput');
    const file = input.files[0];
    if (!file) return this.toast('CSV 파일을 선택해주세요.');
    const button = document.getElementById('csvButton');
    const old = button.textContent;
    button.disabled = true;
    button.textContent = 'CSV 분석 중…';
    try {
      const form = new FormData();
      form.append('file', file);
      const data = await this.api('/api/parse-csv', { method: 'POST', body: form });
      let added = 0;
      data.contacts.forEach((contact) => { if (this.addRecipient(contact, false)) added += 1; });
      this.renderRecipients();
      this.toast(`${added}명 추가 · ${data.skipped || 0}행 제외`);
      input.value = '';
    } catch (error) {
      this.toast(error.message);
    } finally {
      button.disabled = false;
      button.textContent = old;
    }
  }

  renderRecipients() {
    const list = document.getElementById('recipientList');
    const items = [...this.recipients.entries()];
    document.getElementById('recipientCount').textContent = items.length;
    if (!items.length) {
      list.innerHTML = '<div class="empty">아직 수신자가 없습니다.</div>';
    } else {
      list.innerHTML = items.map(([key, item]) => `
        <div class="recipient"><div><strong>${this.escape(item.name)}</strong><div class="sub">${this.escape(item.phone)}</div></div>
        <button class="icon-button remove" type="button" data-key="${this.escape(key)}" aria-label="삭제">×</button></div>`).join('');
      list.querySelectorAll('.remove').forEach((button) => button.addEventListener('click', () => {
        this.recipients.delete(button.dataset.key); this.renderRecipients();
      }));
    }
    this.updateMessageMeta();
  }

  updateMessageMeta() {
    const input = document.getElementById('messageInput');
    document.getElementById('charCount').textContent = input.value.length;
    const first = this.recipients.values().next().value;
    const preview = document.getElementById('preview');
    if (!first) return preview.textContent = '수신자를 추가하면 미리보기가 표시됩니다.';
    if (!input.value) return preview.textContent = `${first.name || '첫 수신자'} 기준 미리보기 준비됨`;
    const rendered = input.value.replaceAll('{name}', first.name || '').replaceAll('{phone}', first.phone || '').replace(/\s+/g, ' ').trim();
    preview.textContent = `미리보기: ${rendered.slice(0, 90)}${rendered.length > 90 ? '…' : ''}`;
  }

  async diagnostics() {
    const dialog = document.getElementById('diagnosticsDialog');
    const content = document.getElementById('diagnosticsContent');
    content.innerHTML = '<div class="empty">확인 중…</div>';
    dialog.showModal();
    try {
      const d = await this.api('/api/diagnostics');
      const rows = [
        ['macOS', d.macos_version || d.platform || '확인 불가'],
        ['아키텍처', d.architecture || '확인 불가'],
        ['AppleScript 문법', d.script_compiles ? '정상' : '오류'],
        ['손쉬운 사용 권한', d.accessibility_enabled ? '허용됨' : '허용 필요'],
        ['Messages 자동화', d.messages_accessible ? '접근 가능' : '권한/설정 확인'],
        ['Messages 실행', d.messages_running ? '실행 중' : '전송 시 실행됨'],
        ['전송 방식', d.send_mode || '⌘N 새 메시지'],
      ];
      content.innerHTML = rows.map(([k,v]) => `<div class="diagnostic-row"><span>${this.escape(k)}</span><strong>${this.escape(v)}</strong></div>`).join('') +
        (d.errors?.length ? `<div class="diagnostic-errors">${d.errors.map(this.escape).join('<br>')}</div>` : '');
    } catch (error) {
      content.innerHTML = `<div class="diagnostic-errors">${this.escape(error.message)}</div>`;
    }
  }

  async send() {
    const message = document.getElementById('messageInput').value;
    const recipients = [...this.recipients.values()];
    if (!message.trim()) return this.toast('메시지 내용을 입력해주세요.');
    if (!recipients.length) return this.toast('수신자를 한 명 이상 추가해주세요.');
    if (!window.confirm(`${recipients.length}명에게 실제 메시지를 전송합니다. 계속할까요?`)) return;

    const loading = document.getElementById('loading');
    document.getElementById('loadingText').textContent = `${recipients.length}명에게 순서대로 전송합니다.`;
    loading.hidden = false;
    try {
      const data = await this.api('/api/send', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ recipients, message })
      });
      this.renderResults(data);
      this.toast(`${data.success_count}/${recipients.length}건 전송 완료`);
    } catch (error) {
      this.toast(error.message);
    } finally {
      loading.hidden = true;
    }
  }

  renderResults(data) {
    const panel = document.getElementById('resultsPanel');
    const list = document.getElementById('resultsList');
    const results = data.results || [];
    document.getElementById('resultSummary').textContent = `${data.success_count || 0}건 성공 · ${data.failure_count || 0}건 실패${data.stopped_early ? ' · 시스템 오류로 조기 중단' : ''}`;
    list.innerHTML = results.map((item) => `<div class="result"><div><strong>${this.escape(item.name || '(이름 없음)')}</strong><div class="sub">${this.escape(item.phone || '')}${item.success ? '' : ` · ${this.escape(item.message || '')}`}</div></div><span class="badge ${item.success ? 'success' : 'error'}">${item.success ? '완료' : '실패'}</span></div>`).join('');
    panel.hidden = false;
    panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  toast(message) {
    const el = document.getElementById('toast');
    el.textContent = message;
    el.hidden = false;
    clearTimeout(this.toastTimer);
    this.toastTimer = setTimeout(() => { el.hidden = true; }, 4200);
  }

  escape(value) {
    return String(value ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
  }
}

document.addEventListener('DOMContentLoaded', () => new App());
