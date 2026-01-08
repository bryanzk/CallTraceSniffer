let currentTab = 'single';
let singleResultData = null;
let batchResultData = null;
let simulationResultData = null;
let compareResultA = null;
let compareResultB = null;
let mermaidInitialized = false;
let singleMermaidText = null;
let isSyncingScroll = false;

function switchTab(tab) {
    currentTab = tab;
    
    // 更新标签按钮
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // 更新内容区域
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tab}-tab`).classList.add('active');
    
    // 隐藏结果
    document.getElementById('single-result').style.display = 'none';
    document.getElementById('simulation-result').style.display = 'none';
    document.getElementById('batch-result').style.display = 'none';
    const compareResult = document.getElementById('compare-result');
    if (compareResult) {
        compareResult.style.display = 'none';
    }
}

// 单个交易分析
async function analyzeSingle() {
    const rawInput = document.getElementById('tx-hash').value.trim();
    const txHash = normalizeTxInput(rawInput);

    if (!rawInput) {
        showError('请输入交易哈希');
        return;
    }
    if (!txHash) {
        showError('无效的交易哈希或URL');
        return;
    }
    
    showLoading();
    hideError();
    
    try {
        const data = await fetchAnalyzeWithRetry('/api/analyze', { tx_hash: txHash }, 'single');
        
        hideLoading();
        
        if (data.success) {
            singleResultData = data;
            displaySingleResult(data);
        } else {
            showError(data.error || '分析失败');
        }
    } catch (error) {
        hideLoading();
        showError('请求失败: ' + error.message);
    }
}

async function analyzeCompare(side) {
    const mode = getCompareMode(side);
    const rawInput = getCompareInputValue(side).trim();

    if (!rawInput) {
        showCompareStatus(side, '请输入交易哈希/URL或IR JSON', 'error');
        return;
    }

    showCompareStatus(side, '分析中...', 'loading');

    try {
        if (mode === 'ir') {
            let irObj;
            try {
                irObj = JSON.parse(rawInput);
            } catch (error) {
                showCompareStatus(side, 'IR JSON解析失败', 'error');
                return;
            }
            const built = await buildCompareResultFromIr(side, irObj);
            if (!built.success) {
                showCompareStatus(side, built.error || 'IR解析失败', 'error');
                return;
            }
            if (side === 'A') {
                compareResultA = built;
            } else {
                compareResultB = built;
            }
            showCompareStatus(side, '', 'clear');
            displayCompareResult();
            return;
        }

        const parsed = parseBlocksecInput(rawInput);
        if (parsed.isSimulation) {
            const data = await fetchAnalyzeWithRetry(
                '/api/analyze-simulation',
                { simulation_url: parsed.simulationUrl },
                side
            );
            if (data.success) {
                if (side === 'A') {
                    compareResultA = data;
                } else {
                    compareResultB = data;
                }
                showCompareStatus(side, '', 'clear');
                displayCompareResult();
            } else {
                showCompareStatus(side, data.error || '分析失败', 'error');
            }
            return;
        }

        if (!parsed.txHash) {
            showCompareStatus(side, '无效的交易哈希或URL', 'error');
            return;
        }

        const data = await fetchAnalyzeWithRetry(
            '/api/analyze',
            { tx_hash: parsed.txHash },
            side
        );

        if (data.success) {
            if (side === 'A') {
                compareResultA = data;
            } else {
                compareResultB = data;
            }
            showCompareStatus(side, '', 'clear');
            displayCompareResult();
        } else {
            showCompareStatus(side, data.error || '分析失败', 'error');
        }
    } catch (error) {
        showCompareStatus(side, '请求失败: ' + error.message, 'error');
    }
}

function swapCompareInputs() {
    const urlA = document.getElementById('compare-url-a');
    const urlB = document.getElementById('compare-url-b');
    const irA = document.getElementById('compare-ir-a-input');
    const irB = document.getElementById('compare-ir-b-input');
    const modeA = getCompareMode('A');
    const modeB = getCompareMode('B');
    setCompareMode('A', modeB);
    setCompareMode('B', modeA);
    if (urlA && urlB) {
        const tmpUrl = urlA.value;
        urlA.value = urlB.value;
        urlB.value = tmpUrl;
    }
    if (irA && irB) {
        const tmpIr = irA.value;
        irA.value = irB.value;
        irB.value = tmpIr;
    }
}

function showCompareStatus(side, message, type) {
    const statusId = side === 'A' ? 'compare-status-a' : 'compare-status-b';
    const statusEl = document.getElementById(statusId);
    if (!statusEl) {
        return;
    }
    statusEl.textContent = message;
    statusEl.classList.remove('error', 'loading');
    if (type === 'error') {
        statusEl.classList.add('error');
    } else if (type === 'loading') {
        statusEl.classList.add('loading');
    }
}

const dagViewer = document.getElementById('dag-viewer');
if (dagViewer) {
    dagViewer.addEventListener('click', function(e) {
        if (e.target === dagViewer) {
            closeDagViewer();
        }
    });
}

function getCompareMode(side) {
    const key = side === 'A' ? 'a' : 'b';
    const selected = document.querySelector(`input[name="compare-mode-${key}"]:checked`);
    return selected ? selected.value : 'url';
}

function setCompareMode(side, mode) {
    const key = side === 'A' ? 'a' : 'b';
    const radio = document.querySelector(`input[name="compare-mode-${key}"][value="${mode}"]`);
    if (radio) {
        radio.checked = true;
    }
    toggleCompareMode(side);
}

function toggleCompareMode(side) {
    const key = side === 'A' ? 'a' : 'b';
    const mode = getCompareMode(side);
    const urlBlock = document.getElementById(`compare-input-url-${key}`);
    const irBlock = document.getElementById(`compare-input-ir-${key}`);
    if (!urlBlock || !irBlock) {
        return;
    }
    if (mode === 'ir') {
        urlBlock.style.display = 'none';
        irBlock.style.display = 'block';
    } else {
        urlBlock.style.display = 'block';
        irBlock.style.display = 'none';
    }
}

function getCompareInputValue(side) {
    const key = side === 'A' ? 'a' : 'b';
    const mode = getCompareMode(side);
    if (mode === 'ir') {
        const el = document.getElementById(`compare-ir-${key}-input`);
        return el ? el.value : '';
    }
    const el = document.getElementById(`compare-url-${key}`);
    return el ? el.value : '';
}

function parseBlocksecInput(input) {
    const result = {
        txHash: '',
        isSimulation: false,
        simulationUrl: ''
    };
    if (!input) {
        return result;
    }
    if (input.startsWith('0x') && input.length === 66) {
        result.txHash = input;
        return result;
    }
    if (input.includes('blocksec.com') && input.includes('/explorer/tx/eth/')) {
        const match = input.match(/\/explorer\/tx\/eth\/(0x[a-fA-F0-9]{64})/);
        if (match) {
            result.txHash = match[1];
            result.isSimulation = /[?&]event=simulation/.test(input);
            result.simulationUrl = input;
        }
    }
    return result;
}

function isRetryableTraceError(errorText) {
    if (!errorText) {
        return false;
    }
    return errorText.includes('未找到trace数据') || errorText.includes('未找到simulation trace数据');
}

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function jitterDelay(baseMs, jitterMs = 400) {
    return baseMs + Math.floor(Math.random() * (jitterMs + 1));
}

async function fetchAnalyzeWithRetry(url, payload, side, maxRetries = 3) {
    const request = async () => {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        });
        return response.json();
    };

    let data = await request();
    let attempt = 0;
    while (!data.success && isRetryableTraceError(data.error) && attempt < maxRetries) {
        attempt += 1;
        if (side === 'single') {
            showError(`未找到trace数据，自动重试 (${attempt}/${maxRetries})...`);
        } else {
            showCompareStatus(side, `未找到trace数据，自动重试 (${attempt}/${maxRetries})...`, 'loading');
        }
        await sleep(jitterDelay(800, 400));
        data = await request();
    }
    if (!data.success && isRetryableTraceError(data.error) && attempt > 0) {
        data.error = `${data.error}（已重试${attempt}次）`;
    }
    return data;
}

function countIrNodes(node) {
    if (!node || typeof node !== 'object') {
        return { swaps: 0, transfers: 0 };
    }
    let swaps = node.type === 'swap' ? 1 : 0;
    let transfers = node.type === 'transfer' ? 1 : 0;
    const children = node.callback || [];
    for (const child of children) {
        const childCounts = countIrNodes(child);
        swaps += childCounts.swaps;
        transfers += childCounts.transfers;
    }
    return { swaps, transfers };
}

async function buildCompareResultFromIr(side, irObj) {
    let mermaidDag = null;
    try {
        const response = await fetch('/api/ir-to-mermaid', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ ir_v1: irObj })
        });
        const data = await response.json();
        if (data.success) {
            mermaidDag = data.mermaid_dag;
        } else {
            return { success: false, error: data.error || 'Mermaid生成失败' };
        }
    } catch (error) {
        return { success: false, error: error.message };
    }

    const counts = countIrNodes(irObj.rootTrace || {});
    const txHash = irObj.tx_hash || `custom_${side.toLowerCase()}`;
    return {
        success: true,
        tx_hash: txHash,
        ir_v1: irObj,
        ir_v1_json: JSON.stringify(irObj, null, 2),
        mermaid_dag: mermaidDag,
        stats: {
            swaps_count: counts.swaps,
            transfers_count: counts.transfers,
            total_gas: null
        }
    };
}
function normalizeTxInput(input) {
    if (!input) {
        return '';
    }
    if (input.startsWith('0x') && input.length === 66) {
        return input;
    }
    if (input.includes('blocksec.com') && input.includes('/explorer/tx/eth/')) {
        const match = input.match(/\/explorer\/tx\/eth\/(0x[a-fA-F0-9]{64})/);
        if (match) {
            return match[1];
        }
    }
    return '';
}

function displaySingleResult(data) {
    const resultSection = document.getElementById('single-result');
    const statsDiv = document.getElementById('single-stats');
    const irDiv = document.getElementById('single-ir');
    
    // 显示统计信息
    statsDiv.innerHTML = `
        <div class="stat-card">
            <h3>${data.stats.swaps_count}</h3>
            <p>Swaps</p>
        </div>
        <div class="stat-card">
            <h3>${data.stats.transfers_count}</h3>
            <p>Transfers</p>
        </div>
        <div class="stat-card">
            <h3>${data.stats.router_count}</h3>
            <p>Router</p>
        </div>
        <div class="stat-card">
            <h3>${data.stats.direct_count}</h3>
            <p>Direct</p>
        </div>
        <div class="stat-card">
            <h3>${data.stats.virtual_count}</h3>
            <p>Virtual</p>
        </div>
        <div class="stat-card">
            <h3>${data.stats.total_gas.toLocaleString()}</h3>
            <p>Total Gas</p>
        </div>
    `;
    
    irDiv.textContent = data.ir_v1_json || formatJson(data.ir_v1);
    singleMermaidText = data.mermaid_dag || null;
    renderMermaid('single-mermaid', data.mermaid_dag);

    resultSection.style.display = 'block';
    resultSection.scrollIntoView({ behavior: 'smooth' });
}

function displayCompareResult() {
    const resultSection = document.getElementById('compare-result');
    if (!resultSection || !compareResultA || !compareResultB) {
        return;
    }

    const summary = document.getElementById('compare-summary');
    summary.innerHTML = buildCompareSummary(compareResultA, compareResultB);

    const irA = document.getElementById('compare-ir-a');
    const irB = document.getElementById('compare-ir-b');
    const irTextA = compareResultA.ir_v1_json || formatJson(compareResultA.ir_v1);
    const irTextB = compareResultB.ir_v1_json || formatJson(compareResultB.ir_v1);
    const diffHtml = buildDiffHtml(irTextA, irTextB);
    irA.innerHTML = diffHtml.left;
    irB.innerHTML = diffHtml.right;

    renderMermaid('compare-mermaid-a', compareResultA.mermaid_dag);
    renderMermaid('compare-mermaid-b', compareResultB.mermaid_dag);

    resultSection.style.display = 'block';
    resultSection.scrollIntoView({ behavior: 'smooth' });

    setupCompareSync();
}

function buildCompareSummary(a, b) {
    const aStats = a.stats || {};
    const bStats = b.stats || {};
    const aPath = getRootPath(a.ir_v1);
    const bPath = getRootPath(b.ir_v1);

    return `
        <div class="compare-card">
            <h4>Swaps</h4>
            <div class="compare-values">
                <div>A: ${aStats.swaps_count ?? 'N/A'}</div>
                <div>B: ${bStats.swaps_count ?? 'N/A'}</div>
            </div>
        </div>
        <div class="compare-card">
            <h4>Transfers</h4>
            <div class="compare-values">
                <div>A: ${aStats.transfers_count ?? 'N/A'}</div>
                <div>B: ${bStats.transfers_count ?? 'N/A'}</div>
            </div>
        </div>
        <div class="compare-card">
            <h4>Total Gas</h4>
            <div class="compare-values">
                <div>A: ${formatGas(aStats.total_gas)}</div>
                <div>B: ${formatGas(bStats.total_gas)}</div>
            </div>
        </div>
        <div class="compare-card">
            <h4>Root Path</h4>
            <div class="compare-values">
                <div>A: ${aPath}</div>
                <div>B: ${bPath}</div>
            </div>
        </div>
    `;
}

function buildDiffHtml(textA, textB) {
    const linesA = (textA || '').split('\n');
    const linesB = (textB || '').split('\n');
    const maxLines = Math.max(linesA.length, linesB.length);
    const left = [];
    const right = [];

    for (let i = 0; i < maxLines; i++) {
        const lineA = linesA[i] ?? '';
        const lineB = linesB[i] ?? '';
        const isChanged = lineA !== lineB;
        const leftClass = isChanged ? 'diff-line diff-changed' : 'diff-line';
        const rightClass = isChanged ? 'diff-line diff-changed' : 'diff-line';
        left.push(`<span class="${leftClass}">${escapeHtml(lineA)}</span>`);
        right.push(`<span class="${rightClass}">${escapeHtml(lineB)}</span>`);
    }

    return {
        left: `<div class="compare-diff">${left.join('')}</div>`,
        right: `<div class="compare-diff">${right.join('')}</div>`
    };
}

function setupCompareSync() {
    const irA = document.getElementById('compare-ir-a');
    const irB = document.getElementById('compare-ir-b');
    const dagA = document.getElementById('compare-mermaid-a');
    const dagB = document.getElementById('compare-mermaid-b');
    const syncIr = document.getElementById('compare-sync-ir');
    const syncDag = document.getElementById('compare-sync-dag');

    if (!irA || !irB || !dagA || !dagB || !syncIr || !syncDag) {
        return;
    }

    const syncScroll = (source, target) => {
        if (isSyncingScroll) {
            return;
        }
        isSyncingScroll = true;
        target.scrollTop = source.scrollTop;
        target.scrollLeft = source.scrollLeft;
        isSyncingScroll = false;
    };

    irA.onscroll = () => {
        if (syncIr.checked) {
            syncScroll(irA, irB);
        }
    };
    irB.onscroll = () => {
        if (syncIr.checked) {
            syncScroll(irB, irA);
        }
    };
    dagA.onscroll = () => {
        if (syncDag.checked) {
            syncScroll(dagA, dagB);
        }
    };
    dagB.onscroll = () => {
        if (syncDag.checked) {
            syncScroll(dagB, dagA);
        }
    };
}

function getRootPath(ir) {
    if (!ir || !ir.rootTrace || !ir.rootTrace.swap || !ir.rootTrace.swap.swapIntent) {
        return 'N/A';
    }
    const intent = ir.rootTrace.swap.swapIntent;
    if (!intent.tokenIn || !intent.tokenOut) {
        return 'N/A';
    }
    return `${intent.tokenIn} → ${intent.tokenOut}`;
}

function formatGas(value) {
    if (value === null || value === undefined) {
        return 'N/A';
    }
    if (typeof value === 'number') {
        return value.toLocaleString();
    }
    return value;
}

// 模拟交易分析
async function analyzeSimulation() {
    const rawInput = document.getElementById('simulation-url').value;
    const simUrls = rawInput
        .split(/\r?\n/)
        .map(line => line.trim())
        .filter(Boolean);

    if (simUrls.length === 0) {
        showError('请输入模拟交易URL');
        return;
    }

    try {
        if (simUrls.length === 1) {
            const simUrl = simUrls[0];
            if (!simUrl.includes('blocksec.com') || !simUrl.includes('/explorer/tx/eth/')) {
                showError('无效的BlockSec模拟URL');
                return;
            }

            showLoading();
            hideError();

            const response = await fetch('/api/analyze-simulation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ simulation_url: simUrl })
            });

            const data = await response.json();

            hideLoading();

            if (data.success) {
                simulationResultData = data;
                displaySimulationResult(data);
            } else {
                showError(data.error || '模拟分析失败');
            }
        } else {
            showLoading();
            hideError();

            const response = await fetch('/api/analyze-simulation-batch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ simulation_urls: simUrls })
            });

            const data = await response.json();

            hideLoading();

            if (data.success) {
                simulationResultData = data;
                displaySimulationBatchResult(data);
            } else {
                showError(data.error || '模拟批量分析失败');
            }
        }
    } catch (error) {
        hideLoading();
        showError('请求失败: ' + error.message);
    }
}

function displaySimulationResult(data) {
    const resultSection = document.getElementById('simulation-result');
    const statsDiv = document.getElementById('simulation-stats');
    const irDiv = document.getElementById('simulation-ir');
    const outputDiv = document.getElementById('simulation-output');

    statsDiv.innerHTML = `
        <div class="stat-card">
            <h3>${data.stats.swaps_count}</h3>
            <p>Swaps</p>
        </div>
        <div class="stat-card">
            <h3>${data.stats.transfers_count}</h3>
            <p>Transfers</p>
        </div>
        <div class="stat-card">
            <h3>${data.stats.router_count}</h3>
            <p>Router</p>
        </div>
        <div class="stat-card">
            <h3>${data.stats.direct_count}</h3>
            <p>Direct</p>
        </div>
        <div class="stat-card">
            <h3>${data.stats.virtual_count}</h3>
            <p>Virtual</p>
        </div>
        <div class="stat-card">
            <h3>${data.stats.total_gas.toLocaleString()}</h3>
            <p>Total Gas</p>
        </div>
    `;

    outputDiv.style.display = 'none';
    irDiv.textContent = data.ir_v1_json || formatJson(data.ir_v1);
    irDiv.style.display = 'block';

    resultSection.style.display = 'block';
    resultSection.scrollIntoView({ behavior: 'smooth' });
}

async function renderMermaid(containerId, mermaidText) {
    const container = document.getElementById(containerId);
    if (!container) {
        return;
    }
    if (!mermaidText) {
        container.innerHTML = '';
        container.style.display = 'none';
        return;
    }

    container.style.display = 'block';

    if (!window.mermaid) {
        container.textContent = 'Mermaid 未加载';
        return;
    }

    if (!mermaidInitialized) {
        window.mermaid.initialize({
            startOnLoad: false,
            securityLevel: 'loose'
        });
        mermaidInitialized = true;
    }

    try {
        const renderId = `mermaid-${Date.now()}`;
        const { svg } = await window.mermaid.render(renderId, mermaidText);
        container.innerHTML = svg;
        container.dataset.mermaidSvg = svg;
    } catch (error) {
        container.textContent = 'Mermaid 渲染失败: ' + error.message;
    }
}

function downloadCompareResult(side) {
    const data = side === 'A' ? compareResultA : compareResultB;
    if (!data) {
        showError(`没有可下载的结果 (${side})`);
        return;
    }
    requestDownload({
        tx_hash: data.tx_hash,
        ir_v1: data.ir_v1,
        ir_v1_json: data.ir_v1_json,
        output_type: 'ir_v1'
    });
}

function downloadMermaidSvg(svgContent) {
    const blob = new Blob([svgContent], { type: 'image/svg+xml;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `tx_dag_${new Date().getTime()}.svg`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

function getSvgDimensions(svgContent) {
    try {
        const parser = new DOMParser();
        const doc = parser.parseFromString(svgContent, 'image/svg+xml');
        const svg = doc.documentElement;
        const widthAttr = svg.getAttribute('width');
        const heightAttr = svg.getAttribute('height');
        if (widthAttr && heightAttr) {
            return {
                width: parseFloat(widthAttr),
                height: parseFloat(heightAttr),
                svg
            };
        }
        const viewBox = svg.getAttribute('viewBox');
        if (viewBox) {
            const parts = viewBox.split(/\s+/).map(Number);
            if (parts.length === 4) {
                return {
                    width: parts[2],
                    height: parts[3],
                    svg
                };
            }
        }
        return { width: 1200, height: 800, svg };
    } catch (error) {
        return { width: 1200, height: 800, svg: null };
    }
}

function downloadMermaidPng(svgContent) {
    return new Promise((resolve) => {
        const dims = getSvgDimensions(svgContent);
        let svgText = svgContent;
        if (dims.svg) {
            dims.svg.setAttribute('width', String(dims.width));
            dims.svg.setAttribute('height', String(dims.height));
            svgText = dims.svg.outerHTML;
        }
        const encoded = encodeURIComponent(svgText);
        const dataUrl = `data:image/svg+xml;charset=utf-8,${encoded}`;
        const img = new Image();
        img.onload = function() {
            const scale = window.devicePixelRatio || 1;
            const canvas = document.createElement('canvas');
            canvas.width = dims.width * scale;
            canvas.height = dims.height * scale;
            const ctx = canvas.getContext('2d');
            ctx.scale(scale, scale);
            ctx.drawImage(img, 0, 0);

            canvas.toBlob((blob) => {
                if (!blob) {
                    showError('PNG生成失败');
                    resolve(false);
                    return;
                }
                const pngUrl = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = pngUrl;
                a.download = `tx_dag_${new Date().getTime()}.png`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(pngUrl);
                document.body.removeChild(a);
                resolve(true);
            }, 'image/png');
        };
        img.onerror = function() {
            showError('PNG生成失败');
            resolve(false);
        };
        img.src = dataUrl;
    });
}

async function downloadMermaidPngFrom(containerId) {
    const container = document.getElementById(containerId);
    if (!container) {
        showError('未找到DAG容器');
        return;
    }
    const svg = container.dataset.mermaidSvg;
    if (!svg) {
        showError('没有可下载的DAG');
        return;
    }
    await downloadMermaidPng(svg);
}

function downloadMermaidSvgFrom(containerId) {
    const container = document.getElementById(containerId);
    if (!container) {
        showError('未找到DAG容器');
        return;
    }
    const svg = container.dataset.mermaidSvg;
    if (!svg) {
        showError('没有可下载的DAG');
        return;
    }
    downloadMermaidSvg(svg);
}

function openDagViewer(containerId) {
    const container = document.getElementById(containerId);
    const viewer = document.getElementById('dag-viewer');
    const viewerBody = document.getElementById('dag-viewer-body');
    if (!container || !viewer || !viewerBody) {
        return;
    }
    const svg = container.dataset.mermaidSvg;
    if (!svg) {
        showError('没有可显示的DAG');
        return;
    }
    viewerBody.innerHTML = svg;
    viewer.style.display = 'flex';
}

function closeDagViewer() {
    const viewer = document.getElementById('dag-viewer');
    const viewerBody = document.getElementById('dag-viewer-body');
    if (viewer) {
        viewer.style.display = 'none';
    }
    if (viewerBody) {
        viewerBody.innerHTML = '';
    }
}

function downloadIrJsonExample() {
    const url = '/static/examples/ir_example.json';
    const a = document.createElement('a');
    a.href = url;
    a.download = 'ir_example.json';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

function displaySimulationBatchResult(data) {
    const resultSection = document.getElementById('simulation-result');
    const statsDiv = document.getElementById('simulation-stats');
    const irDiv = document.getElementById('simulation-ir');
    const outputDiv = document.getElementById('simulation-output');

    const successCount = data.results.filter(r => r.success).length;
    const failCount = data.results.length - successCount;

    statsDiv.innerHTML = `
        <div class="stat-card">
            <h3>${data.total}</h3>
            <p>总交易数</p>
        </div>
        <div class="stat-card" style="background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);">
            <h3>${successCount}</h3>
            <p>成功</p>
        </div>
        <div class="stat-card" style="background: linear-gradient(135deg, #f56565 0%, #e53e3e 100%);">
            <h3>${failCount}</h3>
            <p>失败</p>
        </div>
    `;

    outputDiv.innerHTML = data.results.map((result, index) => {
        if (result.success) {
            return `
                <div class="batch-item success">
                    <div class="batch-item-header">
                        <h3>交易 ${index + 1}: ${result.tx_hash.substring(0, 20)}...</h3>
                        <button onclick="downloadSimulationBatchItem(${index})" class="btn btn-secondary btn-small">下载结果</button>
                    </div>
                    <div class="tx-hash">${result.tx_hash}</div>
                    <div class="tx-hash">${result.simulation_url}</div>
                    <div class="stats-grid" style="margin-top: 15px;">
                        <div class="stat-card" style="padding: 10px; font-size: 0.9em;">
                            <h3 style="font-size: 1.5em;">${result.stats.swaps_count}</h3>
                            <p>Swaps</p>
                        </div>
                        <div class="stat-card" style="padding: 10px; font-size: 0.9em;">
                            <h3 style="font-size: 1.5em;">${result.stats.transfers_count}</h3>
                            <p>Transfers</p>
                        </div>
                        <div class="stat-card" style="padding: 10px; font-size: 0.9em;">
                            <h3 style="font-size: 1.5em;">${result.stats.total_gas.toLocaleString()}</h3>
                            <p>Total Gas</p>
                        </div>
                    </div>
                    <div class="output-label">IR (V1)</div>
                    <div class="output-box" style="margin-top: 10px; max-height: 300px;">
                        ${escapeHtml(result.ir_v1_json || formatJson(result.ir_v1))}
                    </div>
                </div>
            `;
        }
        return `
            <div class="batch-item error">
                <h3>交易 ${index + 1}</h3>
                <div class="tx-hash">${result.simulation_url}</div>
                <div style="color: #c53030; margin-top: 10px;">
                    <strong>错误:</strong> ${result.error}
                </div>
            </div>
        `;
    }).join('');

    irDiv.style.display = 'none';
    outputDiv.style.display = 'grid';
    resultSection.style.display = 'block';
    resultSection.scrollIntoView({ behavior: 'smooth' });
}

// 批量分析
let selectedFile = null;

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        selectedFile = file;
        const fileInfo = document.getElementById('file-info');
        fileInfo.innerHTML = `
            <strong>已选择文件:</strong> ${file.name}<br>
            <strong>大小:</strong> ${(file.size / 1024).toFixed(2)} KB
        `;
        fileInfo.style.display = 'block';
        document.getElementById('batch-btn').disabled = false;
    }
}

async function analyzeBatch() {
    if (!selectedFile) {
        showError('请先选择CSV文件');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    showLoading();
    hideError();
    
    try {
        const response = await fetch('/api/analyze-batch', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        hideLoading();
        
        if (data.success) {
            batchResultData = data;
            displayBatchResult(data);
        } else {
            showError(data.error || '批量分析失败');
        }
    } catch (error) {
        hideLoading();
        showError('请求失败: ' + error.message);
    }
}

function displayBatchResult(data) {
    const resultSection = document.getElementById('batch-result');
    const statsDiv = document.getElementById('batch-stats');
    const outputDiv = document.getElementById('batch-output');
    
    // 显示总体统计
    const successCount = data.results.filter(r => r.success).length;
    const failCount = data.results.length - successCount;
    
    statsDiv.innerHTML = `
        <div class="stats-grid">
            <div class="stat-card">
                <h3>${data.total}</h3>
                <p>总交易数</p>
            </div>
            <div class="stat-card" style="background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);">
                <h3>${successCount}</h3>
                <p>成功</p>
            </div>
            <div class="stat-card" style="background: linear-gradient(135deg, #f56565 0%, #e53e3e 100%);">
                <h3>${failCount}</h3>
                <p>失败</p>
            </div>
        </div>
    `;
    
    // 显示每个交易的结果
    outputDiv.innerHTML = data.results.map((result, index) => {
        if (result.success) {
            return `
                <div class="batch-item success">
                    <div class="batch-item-header">
                        <h3>交易 ${index + 1}: ${result.tx_hash.substring(0, 20)}...</h3>
                        <button onclick="downloadBatchItem(${index})" class="btn btn-secondary btn-small">下载结果</button>
                    </div>
                    <div class="tx-hash">${result.tx_hash}</div>
                    <div class="stats-grid" style="margin-top: 15px;">
                        <div class="stat-card" style="padding: 10px; font-size: 0.9em;">
                            <h3 style="font-size: 1.5em;">${result.stats.swaps_count}</h3>
                            <p>Swaps</p>
                        </div>
                        <div class="stat-card" style="padding: 10px; font-size: 0.9em;">
                            <h3 style="font-size: 1.5em;">${result.stats.transfers_count}</h3>
                            <p>Transfers</p>
                        </div>
                        <div class="stat-card" style="padding: 10px; font-size: 0.9em;">
                            <h3 style="font-size: 1.5em;">${result.stats.total_gas.toLocaleString()}</h3>
                            <p>Total Gas</p>
                        </div>
                    </div>
                    <div class="output-label">IR (V1)</div>
                    <div class="output-box" style="margin-top: 10px; max-height: 300px;">
                        ${escapeHtml(result.ir_v1_json || formatJson(result.ir_v1))}
                    </div>
                </div>
            `;
        } else {
            return `
                <div class="batch-item error">
                    <h3>交易 ${index + 1}: ${result.tx_hash.substring(0, 20)}...</h3>
                    <div class="tx-hash">${result.tx_hash}</div>
                    <div style="color: #c53030; margin-top: 10px;">
                        <strong>错误:</strong> ${result.error}
                    </div>
                </div>
            `;
        }
    }).join('');
    
    resultSection.style.display = 'block';
    resultSection.scrollIntoView({ behavior: 'smooth' });
}

function downloadResult(type) {
    let data;
    
    if (type === 'single' && singleResultData) {
        data = {
            tx_hash: singleResultData.tx_hash,
            ir_v1: singleResultData.ir_v1,
            ir_v1_json: singleResultData.ir_v1_json,
            output_type: 'ir_v1'
        };
    } else if (type === 'simulation' && simulationResultData) {
        if (simulationResultData.results) {
            const allOutput = simulationResultData.results
                .filter(r => r.success)
                .map(r => r.ir_v1_json || JSON.stringify(r.ir_v1, null, 2));
            data = {
                tx_hash: 'simulation_batch',
                ir_v1_json: `[\n${allOutput.join(',\n')}\n]`,
                output_type: 'ir_v1'
            };
        } else {
            data = {
                tx_hash: simulationResultData.tx_hash,
                ir_v1: simulationResultData.ir_v1,
                ir_v1_json: simulationResultData.ir_v1_json,
                output_type: 'ir_v1'
            };
        }
    } else if (type === 'batch' && batchResultData) {
        // 批量下载所有结果
        const allOutput = batchResultData.results
            .filter(r => r.success)
            .map(r => r.ir_v1_json || JSON.stringify(r.ir_v1, null, 2));
        data = {
            tx_hash: 'batch',
            ir_v1_json: `[\n${allOutput.join(',\n')}\n]`,
            output_type: 'ir_v1'
        };
    } else {
        showError('没有可下载的结果');
        return;
    }
    
    requestDownload(data);
}

function downloadSimulationBatchItem(index) {
    if (!simulationResultData || !simulationResultData.results || !simulationResultData.results[index]) {
        showError('没有可下载的结果');
        return;
    }
    const result = simulationResultData.results[index];
    if (!result.success) {
        showError('该交易分析失败，无法下载');
        return;
    }
    requestDownload({
        tx_hash: result.tx_hash,
        ir_v1: result.ir_v1,
        ir_v1_json: result.ir_v1_json,
        output_type: 'ir_v1'
    });
}

function downloadBatchItem(index) {
    if (!batchResultData || !batchResultData.results || !batchResultData.results[index]) {
        showError('没有可下载的结果');
        return;
    }
    const result = batchResultData.results[index];
    if (!result.success) {
        showError('该交易分析失败，无法下载');
        return;
    }
    requestDownload({
        tx_hash: result.tx_hash,
        ir_v1: result.ir_v1,
        ir_v1_json: result.ir_v1_json,
        output_type: 'ir_v1'
    });
}

function requestDownload(payload) {
    fetch('/api/download-result', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
    })
    .then(response => response.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const extension = payload.output_type === 'ir_v1' ? 'json' : 'txt';
        a.download = `tx_analysis_${payload.tx_hash.substring(0, 10)}_${new Date().getTime()}.${extension}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    })
    .catch(error => {
        showError('下载失败: ' + error.message);
    });
}

function showLoading() {
    document.getElementById('loading').style.display = 'block';
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

function showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    errorDiv.scrollIntoView({ behavior: 'smooth' });
}

function hideError() {
    document.getElementById('error').style.display = 'none';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatJson(data) {
    if (!data) {
        return 'N/A';
    }
    try {
        return JSON.stringify(prioritizeTxHash(data), null, 2);
    } catch (error) {
        return 'Invalid JSON';
    }
}

function prioritizeTxHash(data) {
    if (!data) {
        return data;
    }
    if (Array.isArray(data)) {
        return data.map(item => prioritizeTxHash(item));
    }
    if (typeof data !== 'object') {
        return data;
    }
    if (!Object.prototype.hasOwnProperty.call(data, 'tx_hash')) {
        return data;
    }
    const reordered = { tx_hash: data.tx_hash };
    Object.keys(data).forEach(key => {
        if (key !== 'tx_hash') {
            reordered[key] = data[key];
        }
    });
    return reordered;
}

// 支持回车键提交
document.getElementById('tx-hash').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        analyzeSingle();
    }
});

document.getElementById('simulation-url').addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        analyzeSimulation();
    }
});

const compareUrlA = document.getElementById('compare-url-a');
const compareUrlB = document.getElementById('compare-url-b');
const compareIrA = document.getElementById('compare-ir-a-input');
const compareIrB = document.getElementById('compare-ir-b-input');
if (compareUrlA) {
    compareUrlA.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            analyzeCompare('A');
        }
    });
}
if (compareUrlB) {
    compareUrlB.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            analyzeCompare('B');
        }
    });
}
if (compareIrA) {
    compareIrA.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            analyzeCompare('A');
        }
    });
}
if (compareIrB) {
    compareIrB.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            analyzeCompare('B');
        }
    });
}

document.querySelectorAll('input[name="compare-mode-a"]').forEach((radio) => {
    radio.addEventListener('change', () => toggleCompareMode('A'));
});
document.querySelectorAll('input[name="compare-mode-b"]').forEach((radio) => {
    radio.addEventListener('change', () => toggleCompareMode('B'));
});

toggleCompareMode('A');
toggleCompareMode('B');
