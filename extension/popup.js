/**
 * course2brain - Popup Controller
 */

const SERVER_URL = 'http://127.0.0.1:8765';

const serverStatusBadge = document.getElementById('serverStatus');
const serverStatusText = document.getElementById('serverStatusText');
const platformNameEl = document.getElementById('platformName');
const pageTitleEl = document.getElementById('pageTitle');
const btnProcess = document.getElementById('btnProcess');
const btnText = document.getElementById('btnText');
const btnIcon = document.getElementById('btnIcon');
const statusBox = document.getElementById('statusBox');

let serverOnline = false;
let activeTab = null;

function showStatus(message, type = 'info') {
  statusBox.className = `status-box ${type}`;
  statusBox.textContent = message;
}

function hideStatus() {
  statusBox.className = 'status-box';
  statusBox.textContent = '';
}

async function checkServerHealth() {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000);
    const resp = await fetch(`${SERVER_URL}/api/health`, {
      method: 'GET',
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (resp.ok) {
      serverOnline = true;
      serverStatusBadge.className = 'badge badge-online';
      serverStatusText.textContent = 'Servidor Ativo';
      return true;
    }
  } catch (e) {
    // server unreachable
  }

  serverOnline = false;
  serverStatusBadge.className = 'badge badge-offline';
  serverStatusText.textContent = 'Servidor Offline';
  return false;
}

async function init() {
  // 1. Get active tab
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tabs || tabs.length === 0) {
    showStatus('Nenhuma aba ativa encontrada.', 'error');
    return;
  }

  activeTab = tabs[0];
  pageTitleEl.textContent = activeTab.title || 'Sem título';

  // 2. Check server
  const isHealthy = await checkServerHealth();

  // 3. Ask content script for platform info
  try {
    chrome.tabs.sendMessage(activeTab.id, { action: 'check_platform' }, (resp) => {
      if (chrome.runtime.lastError || !resp) {
        platformNameEl.textContent = 'Página Web Genérica';
      } else {
        platformNameEl.textContent = resp.platformName || resp.platformId;
      }

      if (isHealthy) {
        btnProcess.disabled = false;
      } else {
        showStatus('Inicie o servidor local no terminal com: c2b serve', 'error');
      }
    });
  } catch (err) {
    platformNameEl.textContent = 'Não detectado';
    if (isHealthy) {
      btnProcess.disabled = false;
    }
  }
}

btnProcess.addEventListener('click', async () => {
  if (!activeTab) return;

  btnProcess.disabled = true;
  btnIcon.innerHTML = '<span class="spinner"></span>';
  btnText.textContent = 'Extraindo conteúdo...';
  showStatus('Extraindo legendas, notas e estrutura da aula...', 'info');

  try {
    // 1. Extract from page
    chrome.tabs.sendMessage(activeTab.id, { action: 'extract_lesson' }, async (payload) => {
      if (chrome.runtime.lastError) {
        btnIcon.textContent = '⚠️';
        btnText.textContent = 'Erro de Conexão';
        showStatus('Recarregue a página da aula e tente novamente.', 'error');
        btnProcess.disabled = false;
        return;
      }

      if (!payload || payload.error) {
        btnIcon.textContent = '⚠️';
        btnText.textContent = 'Falha na Extração';
        showStatus(payload?.error || 'Não foi possível extrair dados da aula.', 'error');
        btnProcess.disabled = false;
        return;
      }

      // 2. Send to c2b serve
      btnText.textContent = 'Sintetizando & Salvando...';
      showStatus('Sintetizando com Gemini e atualizando grafo Obsidian...', 'info');

      try {
        const resp = await fetch(`${SERVER_URL}/api/process`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        const data = await resp.json();

        if (resp.ok && data.success) {
          btnIcon.textContent = '✓';
          btnText.textContent = 'Concluído com Sucesso!';
          const linksCount = data.interlinks_count || 0;
          showStatus(
            `Nota salva em "${data.note_file}"!\n${linksCount} conexões de grafo injetadas.`,
            'success'
          );
        } else {
          throw new Error(data.detail || data.error || 'Erro no processamento');
        }
      } catch (err) {
        btnIcon.textContent = '⚠️';
        btnText.textContent = 'Erro ao Salvar';
        showStatus(`Falha no servidor local: ${err.message}`, 'error');
        btnProcess.disabled = false;
      }
    });
  } catch (err) {
    btnIcon.textContent = '⚠️';
    btnText.textContent = 'Erro';
    showStatus(err.message, 'error');
    btnProcess.disabled = false;
  }
});

document.addEventListener('DOMContentLoaded', init);
