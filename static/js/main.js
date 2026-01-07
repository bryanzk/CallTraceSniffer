let currentTab = 'single';
let singleResultData = null;
let batchResultData = null;
let simulationResultData = null;

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
}

// 单个交易分析
async function analyzeSingle() {
    const txHash = document.getElementById('tx-hash').value.trim();
    
    if (!txHash) {
        showError('请输入交易哈希');
        return;
    }
    
    if (!txHash.startsWith('0x') || txHash.length !== 66) {
        showError('无效的交易哈希格式（应为0x开头，66个字符）');
        return;
    }
    
    showLoading();
    hideError();
    
    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ tx_hash: txHash })
        });
        
        const data = await response.json();
        
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
    
    resultSection.style.display = 'block';
    resultSection.scrollIntoView({ behavior: 'smooth' });
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
