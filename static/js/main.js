let currentTab = 'single';
let singleResultData = null;
let batchResultData = null;
let simulationResultData = null;
let compareResultA = null;
let compareResultB = null;
let mermaidInitialized = false;
let singleMermaidText = null;
let isSyncingScroll = false;

function buildBlocksecTxUrl(txHash) {
    if (!txHash) {
        return '';
    }
    return `https://app.blocksec.com/explorer/tx/eth/${txHash}`;
}

function renderSourceLink(containerId, label, url) {
    const el = document.getElementById(containerId);
    if (!el) {
        return;
    }
    if (!url) {
        el.textContent = '';
        return;
    }
    const safeUrl = escapeHtml(url);
    const safeLabel = escapeHtml(label);
    el.innerHTML = `${safeLabel} <a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${safeUrl}</a>`;
}

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
    const mode = getSingleMode();
    const rawInput = getSingleInputValue(mode).trim();

    if (!rawInput) {
        showError(mode === 'ir' ? '请输入IR JSON' : '请输入交易哈希');
        return;
    }

    if (mode === 'ir') {
        let parsedObj;
        try {
            parsedObj = JSON.parse(rawInput);
        } catch (error) {
            showError('IR JSON解析失败');
            return;
        }
        const normalized = normalizeIrInput(parsedObj);
        if (!normalized) {
            showError('无法识别IR结构');
            return;
        }
        showLoading();
        hideError();
        const built = await buildCompareResultFromIr('S', normalized);
        hideLoading();
        if (!built.success) {
            showError(built.error || 'IR解析失败');
            return;
        }
        singleResultData = built;
        displaySingleResult(built);
        return;
    }

    const txHash = normalizeTxInput(rawInput);
    const parsed = parseBlocksecInput(rawInput);

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
            data.source_url = parsed.simulationUrl || buildBlocksecTxUrl(txHash);
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
            let parsedObj;
            try {
                parsedObj = JSON.parse(rawInput);
            } catch (error) {
                showCompareStatus(side, 'IR JSON解析失败', 'error');
                return;
            }
            const normalized = normalizeIrInput(parsedObj);
            if (!normalized) {
                showCompareStatus(side, '无法识别IR结构', 'error');
                return;
            }
            const irObj = normalized;
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
                data.source_url = parsed.simulationUrl;
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
            data.source_url = buildBlocksecTxUrl(parsed.txHash);
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

function normalizeIrInput(input) {
    if (!input || typeof input !== 'object') {
        return null;
    }
    if (input.raw_ir && typeof input.raw_ir === 'object') {
        const raw = input.raw_ir;
        if (input.tx_hash && !raw.tx_hash) {
            raw.tx_hash = input.tx_hash;
        }
        return raw;
    }
    if (input.ir_v1 && typeof input.ir_v1 === 'object') {
        return input.ir_v1;
    }
    if (input.rootTrace) {
        return input;
    }
    const keys = Object.keys(input);
    if (keys.length === 1) {
        const key = keys[0];
        if (key.startsWith('0x') && key.length === 66 && typeof input[key] === 'object') {
            const wrapped = input[key];
            if (!wrapped.tx_hash) {
                wrapped.tx_hash = key;
            }
            return wrapped;
        }
    }
    return null;
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

function getSingleMode() {
    const selected = document.querySelector('input[name="single-mode"]:checked');
    return selected ? selected.value : 'url';
}

function getSingleInputValue(mode) {
    if (mode === 'ir') {
        const el = document.getElementById('single-ir-input');
        return el ? el.value : '';
    }
    const el = document.getElementById('tx-hash');
    return el ? el.value : '';
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
        ir_v1_json: formatIrPayload(irObj),
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
    
    const displayIr = stripTxHash(data.ir_v1);
    irDiv.textContent = formatIrPayload(data.ir_v1_json || displayIr, { stripTxHash: true });
    singleMermaidText = data.mermaid_dag || null;
    renderMermaid('single-mermaid', data.mermaid_dag);
    renderSourceLink('single-source-url', 'BlockSec URL:', data.source_url);

    resultSection.style.display = 'block';
    resultSection.scrollIntoView({ behavior: 'smooth' });
}

function displayCompareResult() {
    const resultSection = document.getElementById('compare-result');
    if (!resultSection) {
        return;
    }
    const hasA = !!compareResultA;
    const hasB = !!compareResultB;
    if (!hasA && !hasB) {
        return;
    }

    const summary = document.getElementById('compare-summary');
    if (hasA && hasB) {
        summary.innerHTML = buildCompareSummary(compareResultA, compareResultB);
    } else {
        const done = hasA ? 'A' : 'B';
        const pending = hasA ? 'B' : 'A';
        summary.innerHTML = `
            <div class="compare-card">
                <h4>对比准备</h4>
                <div class="compare-values">已完成 ${done}，请继续分析 ${pending} 以生成差异对比。</div>
            </div>
        `;
    }

    const irA = document.getElementById('compare-ir-a');
    const irB = document.getElementById('compare-ir-b');
    if (hasA && hasB) {
        const irTextA = formatIrPayload(compareResultA.ir_v1_json || compareResultA.ir_v1, { stripTxHash: true });
        const irTextB = formatIrPayload(compareResultB.ir_v1_json || compareResultB.ir_v1, { stripTxHash: true });
        const diffHtml = buildDiffHtml(irTextA, irTextB);
        irA.innerHTML = diffHtml.left;
        irB.innerHTML = diffHtml.right;
        renderMermaid('compare-mermaid-a', compareResultA.mermaid_dag);
        renderMermaid('compare-mermaid-b', compareResultB.mermaid_dag);
        renderSourceLink('compare-source-a', 'BlockSec URL:', compareResultA.source_url);
        renderSourceLink('compare-source-b', 'BlockSec URL:', compareResultB.source_url);
    } else {
        if (hasA) {
            irA.textContent = formatIrPayload(compareResultA.ir_v1_json || compareResultA.ir_v1, { stripTxHash: true });
            setComparePlaceholder('compare-mermaid-a', compareResultA.mermaid_dag, '等待 DAG A');
            renderSourceLink('compare-source-a', 'BlockSec URL:', compareResultA.source_url);
        } else {
            irA.textContent = '等待 Tx A';
            setComparePlaceholder('compare-mermaid-a', null, '等待 Tx A');
            renderSourceLink('compare-source-a', '', '');
        }
        if (hasB) {
            irB.textContent = formatIrPayload(compareResultB.ir_v1_json || compareResultB.ir_v1, { stripTxHash: true });
            setComparePlaceholder('compare-mermaid-b', compareResultB.mermaid_dag, '等待 DAG B');
            renderSourceLink('compare-source-b', 'BlockSec URL:', compareResultB.source_url);
        } else {
            irB.textContent = '等待 Tx B';
            setComparePlaceholder('compare-mermaid-b', null, '等待 Tx B');
            renderSourceLink('compare-source-b', '', '');
        }
    }

    resultSection.style.display = 'block';
    resultSection.scrollIntoView({ behavior: 'smooth' });

    setupCompareSync();
}

function setComparePlaceholder(containerId, mermaidText, message) {
    const container = document.getElementById(containerId);
    if (!container) {
        return;
    }
    if (!mermaidText) {
        container.textContent = message;
        container.style.display = 'block';
        container.dataset.mermaidSvg = '';
        return;
    }
    renderMermaid(containerId, mermaidText);
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
    const parsedA = parseJsonMaybe(textA);
    const parsedB = parseJsonMaybe(textB);
    if (!parsedA || !parsedB) {
        return buildLineDiffHtml(textA, textB);
    }

    const orderedA = orderIrForOutput(parsedA);
    const orderedB = orderIrForOutput(parsedB);
    const diffMap = buildPathDiffMap(orderedA, orderedB);
    const left = renderJsonLines(orderedA, diffMap, 'left');
    const right = renderJsonLines(orderedB, diffMap, 'right');

    return {
        left: `<div class="compare-diff">${left.join('')}</div>`,
        right: `<div class="compare-diff">${right.join('')}</div>`
    };
}

function buildLineDiffHtml(textA, textB) {
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

function parseJsonMaybe(input) {
    if (!input) {
        return null;
    }
    if (typeof input === 'object') {
        return input;
    }
    if (typeof input !== 'string') {
        return null;
    }
    try {
        return JSON.parse(input);
    } catch (error) {
        return null;
    }
}

function buildPathDiffMap(leftObj, rightObj) {
    const leftNodes = {};
    const rightNodes = {};
    const leftValues = {};
    const rightValues = {};
    collectPathInfo(leftObj, '', leftNodes, leftValues);
    collectPathInfo(rightObj, '', rightNodes, rightValues);

    const diffMap = {};
    const allPaths = new Set([...Object.keys(leftNodes), ...Object.keys(rightNodes)]);
    allPaths.forEach((path) => {
        if (!path) {
            return;
        }
        if (!leftNodes[path]) {
            diffMap[path] = 'added';
            return;
        }
        if (!rightNodes[path]) {
            diffMap[path] = 'removed';
            return;
        }
        if (leftNodes[path] !== rightNodes[path]) {
            diffMap[path] = 'changed';
            return;
        }
        if (leftNodes[path] === 'primitive' && leftValues[path] !== rightValues[path]) {
            diffMap[path] = 'changed';
        }
    });
    return diffMap;
}

function collectPathInfo(value, path, nodeMap, valueMap) {
    const type = detectNodeType(value);
    nodeMap[path] = type;
    if (type === 'primitive') {
        valueMap[path] = JSON.stringify(value);
        return;
    }
    if (type === 'array') {
        value.forEach((item, index) => {
            collectPathInfo(item, `${path}[${index}]`, nodeMap, valueMap);
        });
        return;
    }
    if (type === 'object') {
        Object.keys(value).forEach((key) => {
            const nextPath = path ? `${path}.${key}` : key;
            collectPathInfo(value[key], nextPath, nodeMap, valueMap);
        });
    }
}

function detectNodeType(value) {
    if (value === null || value === undefined) {
        return 'primitive';
    }
    if (Array.isArray(value)) {
        return 'array';
    }
    if (typeof value === 'object') {
        return 'object';
    }
    return 'primitive';
}

function renderJsonLines(value, diffMap, side) {
    const lines = [];
    renderJsonValue(value, null, '', true, diffMap, side, lines);
    return lines;
}

function renderJsonValue(value, keyLabel, indent, isLast, diffMap, side, lines, path = '') {
    const type = detectNodeType(value);
    const prefix = keyLabel !== null ? `${indent}"${keyLabel}": ` : indent;
    if (type === 'object') {
        lines.push(buildDiffLine(`${prefix}{`, path, diffMap, side));
        const keys = Object.keys(value);
        keys.forEach((key, index) => {
            const nextPath = path ? `${path}.${key}` : key;
            renderJsonValue(
                value[key],
                key,
                indent + '  ',
                index === keys.length - 1,
                diffMap,
                side,
                lines,
                nextPath
            );
        });
        lines.push(buildDiffLine(`${indent}}${isLast ? '' : ','}`, '', diffMap, side));
        return;
    }
    if (type === 'array') {
        lines.push(buildDiffLine(`${prefix}[`, path, diffMap, side));
        value.forEach((item, index) => {
            const nextPath = `${path}[${index}]`;
            renderJsonValue(
                item,
                null,
                indent + '  ',
                index === value.length - 1,
                diffMap,
                side,
                lines,
                nextPath
            );
        });
        lines.push(buildDiffLine(`${indent}]${isLast ? '' : ','}`, '', diffMap, side));
        return;
    }
    const literal = JSON.stringify(value);
    lines.push(buildDiffLine(`${prefix}${literal}${isLast ? '' : ','}`, path, diffMap, side));
}

function buildDiffLine(text, path, diffMap, side) {
    let className = 'diff-line';
    if (path && diffMap[path]) {
        const status = diffMap[path];
        if (status === 'changed') {
            className = 'diff-line diff-changed';
        } else if (status === 'added' && side === 'right') {
            className = 'diff-line diff-added';
        } else if (status === 'removed' && side === 'left') {
            className = 'diff-line diff-removed';
        }
    }
    return `<span class="${className}">${escapeHtml(text)}</span>`;
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
                data.source_url = simUrl;
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
    const copyButton = document.getElementById('copy-simulation-ir');

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
    const displayIr = stripTxHash(data.ir_v1);
    irDiv.textContent = formatIrPayload(data.ir_v1_json || displayIr, { stripTxHash: true });
    irDiv.style.display = 'block';
    if (copyButton) {
        copyButton.style.display = 'inline-flex';
    }
    renderSourceLink('simulation-source-url', 'BlockSec URL:', data.simulation_url || data.source_url);

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
    const stripped = stripTxHash(data.ir_v1);
    requestDownload({
        tx_hash: data.tx_hash,
        ir_v1: stripped,
        ir_v1_json: formatIrPayload(data.ir_v1_json || stripped, { stripTxHash: true }),
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

function copyTextToClipboard(text, button) {
    if (!text) {
        showError('没有可复制的内容');
        return;
    }
    const flashButton = () => {
        if (!button) {
            return;
        }
        const original = button.textContent;
        button.textContent = '已复制';
        button.disabled = true;
        setTimeout(() => {
            button.textContent = original;
            button.disabled = false;
        }, 1200);
    };
    const fallbackCopy = () => {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.setAttribute('readonly', '');
        textarea.style.position = 'absolute';
        textarea.style.left = '-9999px';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        flashButton();
    };
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(flashButton).catch(fallbackCopy);
    } else {
        fallbackCopy();
    }
}

function copySingleIr(button) {
    if (!singleResultData) {
        showError('没有可复制的IR结果');
        return;
    }
    const stripped = stripTxHash(singleResultData.ir_v1);
    const text = formatIrPayload(singleResultData.ir_v1_json || stripped, { stripTxHash: true });
    copyTextToClipboard(text, button);
}

function copyCompareIr(side, button) {
    const result = side === 'A' ? compareResultA : compareResultB;
    if (!result) {
        showCompareStatus(side, '没有可复制的IR结果', 'error');
        return;
    }
    const text = formatIrPayload(result.ir_v1_json || result.ir_v1, { stripTxHash: true });
    copyTextToClipboard(text, button);
}

function copySimulationIr(button) {
    if (!simulationResultData || simulationResultData.results) {
        showError('没有可复制的IR结果');
        return;
    }
    const text = formatIrPayload(simulationResultData.ir_v1_json || simulationResultData.ir_v1, { stripTxHash: true });
    copyTextToClipboard(text, button);
}

function copySimulationBatchItemIr(index, button) {
    if (!simulationResultData || !simulationResultData.results || !simulationResultData.results[index]) {
        showError('没有可复制的IR结果');
        return;
    }
    const result = simulationResultData.results[index];
    if (!result.success) {
        showError('该交易分析失败，无法复制');
        return;
    }
    const text = formatIrPayload(result.ir_v1_json || result.ir_v1);
    copyTextToClipboard(text, button);
}

function copyBatchItemIr(index, button) {
    if (!batchResultData || !batchResultData.results || !batchResultData.results[index]) {
        showError('没有可复制的IR结果');
        return;
    }
    const result = batchResultData.results[index];
    if (!result.success) {
        showError('该交易分析失败，无法复制');
        return;
    }
    const text = formatIrPayload(result.ir_v1_json || result.ir_v1);
    copyTextToClipboard(text, button);
}

function displaySimulationBatchResult(data) {
    const resultSection = document.getElementById('simulation-result');
    const statsDiv = document.getElementById('simulation-stats');
    const irDiv = document.getElementById('simulation-ir');
    const outputDiv = document.getElementById('simulation-output');
    const copyButton = document.getElementById('copy-simulation-ir');

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
                        <div class="compare-actions">
                            <button onclick="downloadSimulationBatchItem(${index})" class="btn btn-secondary btn-small">下载结果</button>
                            <button onclick="copySimulationBatchItemIr(${index}, this)" class="btn btn-secondary btn-small">复制IR</button>
                        </div>
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
                        ${escapeHtml(formatIrPayload(result.ir_v1_json || result.ir_v1))}
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
    if (copyButton) {
        copyButton.style.display = 'none';
    }
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
                        <div class="compare-actions">
                            <button onclick="downloadBatchItem(${index})" class="btn btn-secondary btn-small">下载结果</button>
                            <button onclick="copyBatchItemIr(${index}, this)" class="btn btn-secondary btn-small">复制IR</button>
                        </div>
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
                        ${escapeHtml(formatIrPayload(result.ir_v1_json || result.ir_v1))}
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
        const stripped = stripTxHash(singleResultData.ir_v1);
        data = {
            tx_hash: singleResultData.tx_hash,
            ir_v1: stripped,
            ir_v1_json: formatIrPayload(singleResultData.ir_v1_json || stripped, { stripTxHash: true }),
            output_type: 'ir_v1'
        };
    } else if (type === 'simulation' && simulationResultData) {
        if (simulationResultData.results) {
            const allOutput = simulationResultData.results
                .filter(r => r.success)
                .map(r => formatIrPayload(r.ir_v1_json || r.ir_v1));
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
            .map(r => formatIrPayload(r.ir_v1_json || r.ir_v1));
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
        ir_v1_json: formatIrPayload(result.ir_v1_json || result.ir_v1),
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
        ir_v1_json: formatIrPayload(result.ir_v1_json || result.ir_v1),
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

const IR_TOP_LEVEL_ORDER = ["pattern", "baseTokenAmountIn", "baseTokenAmountOut", "rootTrace", "children"];
const IR_ROOT_TRACE_ORDER = ["type", "swap", "transfer", "wethWrapOrUnwarp", "callback", "encoded"];
const IR_SWAP_ORDER = ["swapIntent", "executionArgs"];
const IR_SWAP_INTENT_ORDER = [
    "poolId",
    "protocolId",
    "tokenIn",
    "tokenInDecimals",
    "tokenOut",
    "tokenOutDecimals",
    "amountIn",
    "amountInBig",
    "amountInEncoded",
    "amountOut",
    "amountOutBig",
    "amountOutEncoded"
];
const IR_EXEC_ARGS_ORDER = [
    "amount",
    "isAmountIn",
    "zeroForOne",
    "recipientIsBot",
    "recipient",
    "recipientType",
    "tokenInIsWETH",
    "tokenOutIsWETH"
];
const IR_TRANSFER_ORDER = ["tokenId", "to", "amount"];

function orderedByKeys(data, keyOrder) {
    const ordered = {};
    keyOrder.forEach(key => {
        if (Object.prototype.hasOwnProperty.call(data, key)) {
            ordered[key] = data[key];
        }
    });
    Object.keys(data).forEach(key => {
        if (!Object.prototype.hasOwnProperty.call(ordered, key)) {
            ordered[key] = data[key];
        }
    });
    return ordered;
}

function orderIrValue(value) {
    if (Array.isArray(value)) {
        return value.map(item => orderIrValue(item));
    }
    if (value && typeof value === 'object') {
        return orderIrDict(value);
    }
    return value;
}

function orderIrDict(data) {
    const processed = {};
    Object.keys(data).forEach(key => {
        processed[key] = orderIrValue(data[key]);
    });

    if (Object.prototype.hasOwnProperty.call(processed, 'rootTrace')
        && Object.prototype.hasOwnProperty.call(processed, 'children')) {
        const order = (Object.prototype.hasOwnProperty.call(processed, 'tx_hash')
            ? ['tx_hash'] : []).concat(IR_TOP_LEVEL_ORDER);
        return orderedByKeys(processed, order);
    }

    if (Object.prototype.hasOwnProperty.call(processed, 'swapIntent')
        || Object.prototype.hasOwnProperty.call(processed, 'executionArgs')) {
        const ordered = orderedByKeys(processed, IR_SWAP_ORDER);
        if (ordered.swapIntent && typeof ordered.swapIntent === 'object') {
            ordered.swapIntent = orderedByKeys(ordered.swapIntent, IR_SWAP_INTENT_ORDER);
        }
        if (ordered.executionArgs && typeof ordered.executionArgs === 'object') {
            ordered.executionArgs = orderedByKeys(ordered.executionArgs, IR_EXEC_ARGS_ORDER);
        }
        return ordered;
    }

    if (Object.prototype.hasOwnProperty.call(processed, 'poolId')
        && Object.prototype.hasOwnProperty.call(processed, 'protocolId')
        && (Object.prototype.hasOwnProperty.call(processed, 'tokenIn')
            || Object.prototype.hasOwnProperty.call(processed, 'tokenOut'))) {
        return orderedByKeys(processed, IR_SWAP_INTENT_ORDER);
    }

    if (Object.prototype.hasOwnProperty.call(processed, 'type')
        && (Object.prototype.hasOwnProperty.call(processed, 'swap')
            || Object.prototype.hasOwnProperty.call(processed, 'transfer'))) {
        return orderedByKeys(processed, IR_ROOT_TRACE_ORDER);
    }

    if (IR_TRANSFER_ORDER.every(key => Object.prototype.hasOwnProperty.call(processed, key))) {
        return orderedByKeys(processed, IR_TRANSFER_ORDER);
    }

    if (Object.prototype.hasOwnProperty.call(processed, 'tx_hash')) {
        return orderedByKeys(processed, ['tx_hash']);
    }

    return processed;
}

function orderIrForOutput(data) {
    if (!data) {
        return data;
    }
    if (Array.isArray(data)) {
        return data.map(item => orderIrForOutput(item));
    }
    if (typeof data !== 'object') {
        return data;
    }
    return orderIrDict(data);
}

function formatJson(data) {
    if (!data) {
        return 'N/A';
    }
    try {
        return JSON.stringify(orderIrForOutput(data), null, 2);
    } catch (error) {
        return 'Invalid JSON';
    }
}

function formatIrPayload(payload, options = {}) {
    if (!payload) {
        return 'N/A';
    }
    let data = payload;
    if (typeof data === 'string') {
        try {
            data = JSON.parse(data);
        } catch (error) {
            return payload;
        }
    }
    if (options.stripTxHash) {
        data = stripTxHash(data);
    }
    return formatJson(data);
}

function stripTxHash(data) {
    if (!data || typeof data !== 'object' || Array.isArray(data)) {
        return data;
    }
    if (!Object.prototype.hasOwnProperty.call(data, 'tx_hash')) {
        return data;
    }
    const { tx_hash, ...rest } = data;
    return rest;
}

function stripTxHashJson(text) {
    return formatIrPayload(text, { stripTxHash: true });
}

function prioritizeTxHash(data) {
    return orderIrForOutput(data);
}

// 支持回车键提交
const singleUrl = document.getElementById('tx-hash');
const singleIr = document.getElementById('single-ir-input');
if (singleUrl) {
    singleUrl.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            analyzeSingle();
        }
    });
}
if (singleIr) {
    singleIr.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            analyzeSingle();
        }
    });
}

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

document.querySelectorAll('input[name="single-mode"]').forEach((radio) => {
    radio.addEventListener('change', (event) => {
        const mode = event.target.value;
        const urlBlock = document.getElementById('single-input-url');
        const irBlock = document.getElementById('single-input-ir');
        if (!urlBlock || !irBlock) {
            return;
        }
        urlBlock.style.display = mode === 'url' ? 'flex' : 'none';
        irBlock.style.display = mode === 'ir' ? 'block' : 'none';
    });
});

toggleCompareMode('A');
toggleCompareMode('B');
