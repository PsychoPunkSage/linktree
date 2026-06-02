function versionPanel() {
  return {
    show: false,
    entries: [],

    async init() {
      try {
        const text = await fetch('/CHANGELOG.md').then(r => r.text());
        this.entries = text
          .split('\n')
          .map(l => l.trim())
          .filter(l => l)
          .map(l => {
            const [version, date] = l.split(/\s+/);
            return { version, date };
          });
      } catch {
        this.entries = [];
      }
    },

    toggle() {
      this.show = !this.show;
    },
  };
}

function chatApp() {
  // const API = 'https://api.psychopunksage.dev';
  const API = 'http://localhost:8000';

  return {
    input: '',
    messages: [],
    loading: false,
    history: [],
    historyIdx: -1,
    sessionId: (() => {
      const k = 'pps_sid';
      let id = sessionStorage.getItem(k);
      if (!id) { id = crypto.randomUUID(); sessionStorage.setItem(k, id); }
      return id;
    })(),

    historyUp() {
      if (!this.history.length) return;
      this.historyIdx = Math.min(this.historyIdx + 1, this.history.length - 1);
      this.input = this.history[this.historyIdx];
    },

    historyDown() {
      if (this.historyIdx <= 0) { this.historyIdx = -1; this.input = ''; return; }
      this.historyIdx--;
      this.input = this.history[this.historyIdx];
    },

    async send() {
      const q = this.input.trim();
      if (!q || this.loading) return;

      this.history.unshift(q);
      this.historyIdx = -1;
      this.messages.push({ role: 'user', content: q });
      this.input = '';
      this.loading = true;

      this.messages.push({ role: 'ai', content: '', error: false });
      const idx = this.messages.length - 1;

      try {
        const resp = await fetch(`${API}/api/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: q, session_id: this.sessionId }),
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

        const reader  = resp.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const text = decoder.decode(value, { stream: true });
          for (const line of text.split('\n')) {
            if (!line.startsWith('data: ')) continue;
            const token = line.slice(6);
            if (token === '[DONE]') break;
            this.messages[idx].content += token;
          }
        }
      } catch {
        this.messages[idx].content = 'Connection error. Try again.';
        this.messages[idx].error = true;
      } finally {
        this.loading = false;
        this.$nextTick(() => {
          if (this.$refs.messages) this.$refs.messages.scrollTop = this.$refs.messages.scrollHeight;
          this.$refs.chatInput.focus();
        });
      }
    },
  };
}
