/**
 * course2brain - Popup Controller with Visual Stepper
 */

const SERVER_URL = 'http://127.0.0.1:8765';

const serverStatusBadge = document.getElementById('serverStatus');
const serverStatusText = document.getElementById('serverStatusText');
const platformNameEl = document.getElementById('platformName');
const pageTitleEl = document.getElementById('pageTitle');
const btnProcess = document.getElementById('btnProcess');
const btnText = document.getElementById('btnText');
const btnIcon = document.getElementById('btnIcon');

// Progress Stepper Elements
const progressCard = document.getElementById('progressCard');
const progressBarFill = document.getElementById('progressBarFill');

const stepExtract = document.getElementById('stepExtract');
const stepExtractDesc = document.getElementById('stepExtractDesc');

const stepSynthesize = document.getElementById('stepSynthesize');
const stepSynthesizeDesc = document.getElementById('stepSynthesizeDesc');

const stepVault = document.getElementById('stepVault');
const stepVaultDesc = document.getElementById('stepVaultDesc');

const stepGraph = document.getElementById('stepGraph');
const stepGraphDesc = document.getElementById('stepGraphDesc');

// Result Banner Elements
const resultBanner = document.getElementById('resultBanner');
const resultTitle = document.getElementById('resultTitle');
const resultDetail = document.getElementById('resultDetail');

let serverOnline = false;
let activeTab = null;

function setStep(stepEl, descEl, state, message) {
  stepEl.className = `step-item ${state}`;
  const iconEl = stepEl.querySelector('.step-icon');

  if (state === 'active') {
    iconEl.innerHTML = '<span class="spinner-sm"></span>';
  } else if (state === 'done') {
    iconEl.textContent = '✓';
  } else if (state === 'error') {
    iconEl.textContent = '✗';
  } else {
    // reset to initial step number
    if (stepEl === stepExtract) iconEl.textContent = '1';
    if (stepEl === stepSynthesize) iconEl.textContent = '2';
    if (stepEl === stepVault) iconEl.textContent = '3';
    if (stepEl === stepGraph) iconEl.textContent = '4';
  }

  if (message) {
    descEl.textContent = message;
  }
}

function showResult(title, detail, type = 'success') {
  resultBanner.className = `result-banner ${type}`;
  resultTitle.innerHTML = type === 'success' ? `<span>🎉</span> ${title}` : `<span>⚠️</span> ${title}`;
  resultDetail.textContent = detail;
}

function hideResult() {
  resultBanner.className = 'result-banner';
  resultBanner.style.display = 'none';
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
    // unreachable
  }

  serverOnline = false;
  serverStatusBadge.className = 'badge badge-offline';
  serverStatusText.textContent = 'Servidor Offline';
  return false;
}

async function init() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tabs || tabs.length === 0) {
    showResult('Aba Não Encontrada', 'Nenhuma aba ativa identificada no navegador.', 'error');
    return;
  }

  activeTab = tabs[0];
  pageTitleEl.textContent = activeTab.title || 'Sem título';

  const isHealthy = await checkServerHealth();

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
        showResult('Servidor Desconectado', 'Inicie o servidor no terminal com "c2b serve" para habilitar o processamento.', 'error');
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
  if (!activeTab || !serverOnline) return;

  btnProcess.disabled = true;
  btnIcon.innerHTML = '<span class="spinner-sm"></span>';
  btnText.textContent = 'Processando Aula...';

  hideResult();
  progressCard.style.display = 'block';

  // Reset steps
  setStep(stepExtract, stepExtractDesc, 'active', 'Extraindo título, notas, legendas e links...');
  setStep(stepSynthesize, stepSynthesizeDesc, 'pending', 'Aguardando extração...');
  setStep(stepVault, stepVaultDesc, 'pending', 'Aguardando síntese...');
  setStep(stepGraph, stepGraphDesc, 'pending', 'Aguardando gravação...');
  progressBarFill.style.width = '15%';

  try {
    // 1. Extração do Conteúdo da Página
    chrome.tabs.sendMessage(activeTab.id, { action: 'extract_lesson' }, async (payload) => {
      if (chrome.runtime.lastError) {
        setStep(stepExtract, stepExtractDesc, 'error', 'Falha ao comunicar com a aba.');
        showResult('Erro de Conexão', 'Recarregue a página da aula e abra a extensão novamente.', 'error');
        btnProcess.disabled = false;
        btnIcon.textContent = '⚠️';
        btnText.textContent = 'Tentar Novamente';
        return;
      }

      if (!payload || payload.error) {
        setStep(stepExtract, stepExtractDesc, 'error', payload?.error || 'Erro na extração');
        showResult('Falha na Extração', payload?.error || 'Não foi possível ler o conteúdo desta página.', 'error');
        btnProcess.disabled = false;
        btnIcon.textContent = '⚠️';
        btnText.textContent = 'Tentar Novamente';
        return;
      }

      const hasCaptions = payload.captions_text && payload.captions_text.length > 50;
      const hasNotes = payload.notes_text && payload.notes_text.length > 30;
      const countLinks = (payload.links || []).length;

      setStep(
        stepExtract,
        stepExtractDesc,
        'done',
        `Capturado: ${hasCaptions ? 'Legendas OK' : 'Sem legendas'} | ${hasNotes ? 'Notas OK' : 'Sem notas'} | ${countLinks} links.`
      );
      progressBarFill.style.width = '35%';

      // 2. Síntese com Gemini
      setStep(stepSynthesize, stepSynthesizeDesc, 'active', 'Estruturando Resumo, Conceitos e Active Recall com IA...');
      progressBarFill.style.width = '55%';

      const synthesizeTimer = setTimeout(() => {
        setStep(stepSynthesize, stepSynthesizeDesc, 'active', 'Analisando trade-offs e gerando perguntas de fixação...');
        progressBarFill.style.width = '70%';
      }, 2500);

      try {
        const resp = await fetch(`${SERVER_URL}/api/process`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        clearTimeout(synthesizeTimer);
        const data = await resp.json();

        if (resp.ok && data.success) {
          // Síntese concluída
          setStep(stepSynthesize, stepSynthesizeDesc, 'done', 'Síntese Second Brain gerada com sucesso!');
          progressBarFill.style.width = '85%';

          // 3. Vault
          setStep(stepVault, stepVaultDesc, 'done', `Nota salva em: ${data.note_file}`);
          progressBarFill.style.width = '95%';

          // 4. Grafo & Interlink
          const linksCount = data.interlinks_count || 0;
          if (linksCount > 0) {
            setStep(stepGraph, stepGraphDesc, 'done', `${linksCount} conexão(ões) semântica(s) injetada(s) no Grafo!`);
          } else {
            setStep(stepGraph, stepGraphDesc, 'done', 'Indexado com sucesso no grafo.');
          }
          progressBarFill.style.width = '100%';

          btnIcon.textContent = '✓';
          btnText.textContent = 'Concluído com Sucesso!';

          showResult(
            'Aula Processada com Sucesso!',
            `Sua nota foi estruturada e salva no cofre Obsidian.\nPressione Cmd+G (ou Ctrl+G) no Obsidian para ver o nó no Graph View!`
          );
        } else {
          throw new Error(data.detail || data.error || 'Erro durante processamento no servidor');
        }
      } catch (err) {
        clearTimeout(synthesizeTimer);
        setStep(stepSynthesize, stepSynthesizeDesc, 'error', 'Falha na comunicação com o servidor');
        showResult('Erro no Servidor Local', err.message, 'error');
        btnProcess.disabled = false;
        btnIcon.textContent = '⚠️';
        btnText.textContent = 'Tentar Novamente';
      }
    });
  } catch (err) {
    setStep(stepExtract, stepExtractDesc, 'error', err.message);
    showResult('Erro Inesperado', err.message, 'error');
    btnProcess.disabled = false;
    btnIcon.textContent = '⚠️';
    btnText.textContent = 'Tentar Novamente';
  }
});

document.addEventListener('DOMContentLoaded', init);
