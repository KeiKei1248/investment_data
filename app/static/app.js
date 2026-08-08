// 出力フィールド定義
const FIELD_DEFINITIONS = [
    { key: "date", label: "取得日時" },
    { key: "ticker", label: "銘柄コード" },
    { key: "company_name", label: "企業名" },
    { key: "price", label: "株価" },
    { key: "per", label: "PER" },
    { key: "pbr", label: "PBR" },
    { key: "dividend_yield", label: "配当利回り(%)" },
    { key: "roe", label: "ROE(%)" },
    { key: "revenue_growth", label: "売上高成長率(%)" },
    { key: "operating_margins", label: "営業利益率(%)" },
    { key: "equity_ratio", label: "自己資本比率(%)" }
];

let masterTickers = [];
let selectedTickers = new Set();
let selectedFields = new Set();
let selectedCategory = "";
let outputPath = "";
let pollingInterval = null;
let masterSyncInterval = null;

// DOM要素の取得
const tickerListContainer = document.getElementById("ticker-list");
const fieldListContainer = document.getElementById("field-list");
const searchInput = document.getElementById("search-input");
const outputPathInput = document.getElementById("output-path");
const addDateCheckbox = document.getElementById("add-date-to-filename");
const selectedCountBadge = document.getElementById("selected-count");
const btnSelectAll = document.getElementById("btn-select-all");
const btnDeselectAll = document.getElementById("btn-deselect-all");
const btnFetch = document.getElementById("btn-fetch");
const statusPanel = document.getElementById("status-panel");
const statusMessage = document.getElementById("status-message");
const statusPercent = document.getElementById("status-percent");
const statusProgressBar = document.getElementById("status-progress-bar");
const masterSyncIndicator = document.getElementById("master-sync-indicator");

// ステップ1の商品区分セレクトボックス
const selectSegment = document.getElementById("select-segment");
const btnSegmentNext = document.getElementById("btn-segment-next");

// 各種ナビゲーションボタン
const btnToStep1 = document.getElementById("btn-to-step-1");
const btnToStep2 = document.getElementById("btn-to-step-2");
const btnToStep3 = document.getElementById("btn-to-step-3");

// 起動時の初期化処理
document.addEventListener("DOMContentLoaded", async () => {
    initFieldList();
    await loadInitialData();
    setupEventListeners();
    goToStep(1); // 起動時はステップ1を表示
    
    // バックグラウンド同期ステータスの確認を開始
    checkMasterSyncStatus();
});

// 段階的ステップ制御
function goToStep(step) {
    // 全パネルを非表示にする
    document.querySelectorAll(".step-panel").forEach(p => p.classList.add("hidden"));
    
    // 指定パネルを表示
    document.getElementById(`panel-step-${step}`).classList.remove("hidden");
    
    // インジケーターを更新
    updateStepIndicators(step);
}

function updateStepIndicators(activeStep) {
    for (let i = 1; i <= 3; i++) {
        const ind = document.getElementById(`step-indicator-${i}`);
        const span = ind.querySelector("span");
        if (i === activeStep) {
            ind.className = "flex items-center gap-2 text-indigo-400 font-bold transition-all";
            span.className = "w-7 h-7 rounded-full bg-indigo-600/20 border border-indigo-500 flex items-center justify-center text-xs";
        } else if (i < activeStep) {
            ind.className = "flex items-center gap-2 text-emerald-400 font-medium transition-all";
            span.className = "w-7 h-7 rounded-full bg-emerald-600/10 border border-emerald-500/30 flex items-center justify-center text-xs";
            span.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4.5 w-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
            `;
        } else {
            ind.className = "flex items-center gap-2 text-slate-500 transition-all font-medium";
            span.className = "w-7 h-7 rounded-full bg-slate-950 border border-slate-850 flex items-center justify-center text-xs";
            span.innerHTML = `${i}`;
        }
    }
}

// 出力項目リストの初期描画
function initFieldList() {
    fieldListContainer.innerHTML = "";
    FIELD_DEFINITIONS.forEach(field => {
        const wrapper = document.createElement("label");
        wrapper.className = "flex items-center gap-3 p-3 bg-slate-950/40 hover:bg-slate-950/80 border border-slate-800 rounded-xl cursor-pointer transition-all select-none hover:border-indigo-500/30";
        
        wrapper.innerHTML = `
            <input type="checkbox" value="${field.key}" class="field-checkbox h-4.5 w-4.5 rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-indigo-500 focus:ring-offset-slate-900 focus:ring-2">
            <span class="text-sm font-medium text-slate-300">${field.label}</span>
        `;
        fieldListContainer.appendChild(wrapper);
    });
}

// データの初期読み込み (起動時)
async function loadInitialData() {
    try {
        const configResponse = await fetch("/api/config");
        const config = await configResponse.json();
        
        selectedCategory = config.selected_category || "プライム（内国株式）";
        selectedTickers = new Set(config.selected_tickers || []);
        selectedFields = new Set(config.selected_fields || []);
        outputPath = config.output_path || "";
        outputPathInput.value = outputPath;
        
        if (addDateCheckbox) {
            addDateCheckbox.checked = config.add_date_to_filename || false;
        }

        updateFieldCheckboxes();
        updateSelectedCount();

        // 銘柄マスターのロード (即座にキャッシュが返る)
        await loadTickersMasterOnly();
    } catch (error) {
        console.error("設定データの初期化に失敗しました:", error);
    }
}

// 銘柄マスターのみをロード
async function loadTickersMasterOnly() {
    try {
        const response = await fetch("/api/tickers");
        const data = await response.json();
        masterTickers = data.japan || [];
        
        // 商品区分のドロップダウンを生成
        renderSegmentDropdown();
    } catch (e) {
        console.error("銘柄マスターのロードに失敗しました:", e);
    }
}

// 商品区分のドロップダウンを構築
function renderSegmentDropdown() {
    // ユニークな商品区分を抽出
    const categories = Array.from(new Set(masterTickers.map(item => item.category))).filter(Boolean);
    
    selectSegment.innerHTML = "";
    if (categories.length === 0) {
        selectSegment.innerHTML = `<option value="">商品区分がありません</option>`;
        return;
    }
    
    categories.forEach(cat => {
        const option = document.createElement("option");
        option.value = cat;
        option.textContent = cat;
        if (cat === selectedCategory) {
            option.selected = true;
        }
        selectSegment.appendChild(option);
    });
}

// バックグラウンド同期ステータスの確認・ポーリング
function checkMasterSyncStatus() {
    if (masterSyncInterval) clearInterval(masterSyncInterval);
    
    fetchSyncStatus();
    
    masterSyncInterval = setInterval(() => {
        fetchSyncStatus();
    }, 2000);
}

async function fetchSyncStatus() {
    try {
        const resp = await fetch("/api/tickers/status");
        const data = await resp.json();
        
        if (data.status === "updating") {
            masterSyncIndicator.classList.remove("hidden");
        } else {
            clearInterval(masterSyncInterval);
            masterSyncIndicator.classList.add("hidden");
            
            if (data.status === "completed") {
                // 最新データを再ロードして反映
                const response = await fetch("/api/tickers");
                const updatedData = await response.json();
                const updatedTickers = updatedData.japan || [];
                
                if (updatedTickers.length !== masterTickers.length) {
                    masterTickers = updatedTickers;
                    renderSegmentDropdown(); // ドロップダウン再構築
                    if (document.getElementById("panel-step-3").classList.contains("hidden") === false) {
                        renderTickerList(searchInput.value);
                    }
                    console.log("Master tickers dynamic refresh complete");
                }
            }
        }
    } catch (e) {
        console.error("同期ステータスチェックエラー:", e);
        clearInterval(masterSyncInterval);
        masterSyncIndicator.classList.add("hidden");
    }
}

// 表記揺れ（ひらがな・カタカナ、全角・半角英数字、大文字・小文字）を統一する正規化関数
function normalizeString(str) {
    if (!str) return "";
    
    let normalized = str.replace(/[！-～]/g, function(s) {
        return String.fromCharCode(s.charCodeAt(0) - 0xfee0);
    });
    
    normalized = normalized.replace(/[\u3041-\u3096]/g, function(s) {
        return String.fromCharCode(s.charCodeAt(0) + 0x60);
    });
    
    return normalized.toLowerCase().trim();
}

// 銘柄リストの描画（選択された商品区分のみ、かつインクリメンタル検索適用）
function renderTickerList(filterText = "") {
    tickerListContainer.innerHTML = "";
    
    const filterNorm = normalizeString(filterText);
    
    // 現在選択されている商品区分 (category) で一次フィルタ
    const filteredByCategory = masterTickers.filter(item => item.category === selectedCategory);
    
    // さらに検索語でフィルタ
    const filtered = filteredByCategory.filter(item => {
        const tickerNorm = normalizeString(item.ticker);
        const nameNorm = normalizeString(item.name);
        return tickerNorm.includes(filterNorm) || nameNorm.includes(filterNorm);
    });

    if (filtered.length === 0) {
        tickerListContainer.innerHTML = `
            <div class="text-center py-8 text-sm text-slate-500">
                選択された区分「${selectedCategory}」には銘柄が見つかりません。
            </div>
        `;
        return;
    }

    filtered.forEach(item => {
        const isChecked = selectedTickers.has(item.ticker);
        const itemWrapper = document.createElement("label");
        itemWrapper.className = `flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all select-none border border-slate-800/40 hover:border-indigo-500/30 ${isChecked ? 'bg-indigo-600/5 border-indigo-500/20' : 'bg-slate-950/20 hover:bg-slate-950/50'}`;
        
        itemWrapper.innerHTML = `
            <div class="flex items-center gap-3">
                <input type="checkbox" value="${item.ticker}" ${isChecked ? 'checked' : ''} class="ticker-checkbox h-4.5 w-4.5 rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-indigo-500 focus:ring-offset-slate-900 focus:ring-2">
                <div>
                    <span class="text-xs font-semibold px-2 py-0.5 bg-slate-800 text-slate-300 rounded font-outfit">${item.ticker}</span>
                    <span class="text-sm font-medium text-slate-200 ml-2">${item.name}</span>
                </div>
            </div>
        `;
        
        tickerListContainer.appendChild(itemWrapper);
    });
}

// 設定変更時の自動保存処理
async function saveConfig() {
    const data = {
        selected_category: selectedCategory,
        selected_tickers: Array.from(selectedTickers),
        selected_fields: Array.from(selectedFields),
        output_path: outputPathInput.value.trim(),
        add_date_to_filename: addDateCheckbox ? addDateCheckbox.checked : false
    };
    try {
        await fetch("/api/config/save", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data)
        });
    } catch (e) {
        console.error("設定の保存に失敗しました:", e);
    }
}

// 選択項目チェックボックスのチェック状態更新
function updateFieldCheckboxes() {
    document.querySelectorAll(".field-checkbox").forEach(cb => {
        cb.checked = selectedFields.has(cb.value);
    });
}

// 選択済み件数バッジの更新
function updateSelectedCount() {
    selectedCountBadge.textContent = `選択中: ${selectedTickers.size} 件`;
}

// イベントリスナーのセットアップ
function setupEventListeners() {
    // ステップ1: 商品区分ドロップダウン
    selectSegment.addEventListener("change", (e) => {
        selectedCategory = e.target.value;
        saveConfig();
    });

    btnSegmentNext.addEventListener("click", () => {
        if (!selectedCategory) {
            alert("商品区分を選択してください。");
            return;
        }
        goToStep(2);
    });
    
    // マスタ手動更新ボタン
    const btnSyncMaster = document.getElementById("btn-sync-master");
    if (btnSyncMaster) {
        btnSyncMaster.addEventListener("click", async () => {
            btnSyncMaster.disabled = true;
            try {
                const resp = await fetch("/api/tickers/update", { method: "POST" });
                if (resp.ok) {
                    checkMasterSyncStatus();
                } else {
                    alert("銘柄マスターの更新要求に失敗しました。");
                }
            } catch (e) {
                console.error("手動更新エラー:", e);
                alert("エラーが発生しました。");
            } finally {
                btnSyncMaster.disabled = false;
            }
        });
    }

    // ステップ ナビゲーション
    btnToStep1.addEventListener("click", () => goToStep(1));
    btnToStep2.addEventListener("click", () => goToStep(2));
    
    btnToStep3.addEventListener("click", () => {
        if (selectedFields.size === 0) {
            alert("出力項目を最低1つ以上選択してください。");
            return;
        }
        // 選択された商品区分に該当する銘柄リストを描画
        renderTickerList();
        goToStep(3);
    });

    // リアルタイム企業検索（インクリメンタル検索）
    searchInput.addEventListener("input", (e) => {
        renderTickerList(e.target.value);
    });

    // 銘柄リスト内チェックボックスの変更
    tickerListContainer.addEventListener("change", (e) => {
        if (e.target.classList.contains("ticker-checkbox")) {
            const ticker = e.target.value;
            const itemRow = e.target.closest("label");
            if (e.target.checked) {
                selectedTickers.add(ticker);
                if (itemRow) {
                    itemRow.classList.add("bg-indigo-600/5", "border-indigo-500/20");
                    itemRow.classList.remove("bg-slate-950/20");
                }
            } else {
                selectedTickers.delete(ticker);
                if (itemRow) {
                    itemRow.classList.remove("bg-indigo-600/5", "border-indigo-500/20");
                    itemRow.classList.add("bg-slate-950/20");
                }
            }
            updateSelectedCount();
            saveConfig();
        }
    });

    // 出力項目チェックボックスの変更
    fieldListContainer.addEventListener("change", (e) => {
        if (e.target.classList.contains("field-checkbox")) {
            const key = e.target.value;
            if (e.target.checked) {
                selectedFields.add(key);
            } else {
                selectedFields.delete(key);
            }
            saveConfig();
        }
    });

    // 出力パス変更時
    outputPathInput.addEventListener("change", () => {
        saveConfig();
    });
    
    // 日付付与チェックボックス変更時
    if (addDateCheckbox) {
        addDateCheckbox.addEventListener("change", () => {
            saveConfig();
        });
    }

    // すべて選択ボタン (現在表示されているフィルタ対象に適用)
    btnSelectAll.addEventListener("click", () => {
        const checkboxes = tickerListContainer.querySelectorAll(".ticker-checkbox");
        checkboxes.forEach(cb => {
            cb.checked = true;
            selectedTickers.add(cb.value);
            const itemRow = cb.closest("label");
            if (itemRow) {
                itemRow.classList.add("bg-indigo-600/5", "border-indigo-500/20");
                itemRow.classList.remove("bg-slate-950/20");
            }
        });
        updateSelectedCount();
        saveConfig();
    });

    // 選択クリアボタン (現在表示されているフィルタ対象に適用)
    btnDeselectAll.addEventListener("click", () => {
        const checkboxes = tickerListContainer.querySelectorAll(".ticker-checkbox");
        checkboxes.forEach(cb => {
            cb.checked = false;
            selectedTickers.delete(cb.value);
            const itemRow = cb.closest("label");
            if (itemRow) {
                itemRow.classList.remove("bg-indigo-600/5", "border-indigo-500/20");
                itemRow.classList.add("bg-slate-950/20");
            }
        });
        updateSelectedCount();
        saveConfig();
    });

    // 実行ボタン
    btnFetch.addEventListener("click", startDataFetch);

}

// データの取得処理開始
async function startDataFetch() {
    if (selectedTickers.size === 0) {
        alert("銘柄が選択されていません。最低1つ以上の銘柄を選択してください。");
        return;
    }
    if (selectedFields.size === 0) {
        alert("出力項目が選択されていません。最低1つ以上の項目を選択してください。");
        return;
    }
    const path = outputPathInput.value.trim();
    if (!path) {
        alert("CSV保存先パスを入力してください。");
        return;
    }

    // UIを処理中状態に変更
    setControlsEnabled(false);
    statusPanel.classList.remove("hidden");
    updateProgressUI(0, 100, "処理を開始しています...", "running");

    try {
        const response = await fetch("/api/fetch", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                selected_category: selectedCategory,
                selected_tickers: Array.from(selectedTickers),
                selected_fields: Array.from(selectedFields),
                output_path: path,
                add_date_to_filename: addDateCheckbox ? addDateCheckbox.checked : false
            })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "取得開始時にエラーが発生しました。");
        }

        // ポーリング開始
        startProgressPolling();

    } catch (err) {
        console.error(err);
        updateProgressUI(0, 100, `エラーが発生しました: ${err.message}`, "error");
        setControlsEnabled(true);
    }
}

// UI要素の有効化・無効化
function setControlsEnabled(enabled) {
    btnFetch.disabled = !enabled;
    btnSelectAll.disabled = !enabled;
    btnDeselectAll.disabled = !enabled;
    searchInput.disabled = !enabled;
    outputPathInput.disabled = !enabled;
    btnToStep2.disabled = !enabled;
    if (addDateCheckbox) addDateCheckbox.disabled = !enabled;
    
    document.querySelectorAll(".ticker-checkbox").forEach(cb => cb.disabled = !enabled);
    document.querySelectorAll(".field-checkbox").forEach(cb => cb.disabled = !enabled);
}

// 進捗状態のポーリング
function startProgressPolling() {
    if (pollingInterval) clearInterval(pollingInterval);
    
    pollingInterval = setInterval(async () => {
        try {
            const resp = await fetch("/api/progress");
            const data = await resp.json();
            
            updateProgressUI(data.current, data.total, data.message, data.status);
            
            if (data.status === "completed") {
                clearInterval(pollingInterval);
                setControlsEnabled(true);
            } else if (data.status === "error") {
                clearInterval(pollingInterval);
                setControlsEnabled(true);
            }
        } catch (e) {
            console.error("進捗の取得に失敗しました:", e);
        }
    }, 500);
}

// 進捗UIの更新
function updateProgressUI(current, total, message, status) {
    if (status === "completed") {
        statusMessage.textContent = "指定されたパスへ保存が完了しました。";
    } else {
        statusMessage.textContent = message;
    }
    
    let percent = 0;
    if (total > 0) {
        percent = Math.round((current / total) * 100);
    }
    
    statusPercent.textContent = `${percent}%`;
    statusProgressBar.style.width = `${percent}%`;

    // ステータスに応じた色やデザインの調整
    if (status === "completed") {
        statusPercent.className = "text-emerald-400 font-bold font-outfit";
        statusProgressBar.className = "w-full h-full bg-gradient-to-r from-emerald-400 to-teal-500 rounded-full transition-all duration-300";
    } else if (status === "error") {
        statusPercent.className = "text-rose-500 font-bold font-outfit";
        statusProgressBar.className = "w-full h-full bg-rose-600 rounded-full transition-all duration-300";
    } else {
        statusPercent.className = "text-indigo-400 font-bold font-outfit";
        statusProgressBar.className = "w-full h-full bg-gradient-to-r from-indigo-500 to-violet-600 rounded-full transition-all duration-300";
    }
}

