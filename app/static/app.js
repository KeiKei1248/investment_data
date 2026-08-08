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
let outputPath = "";
let pollingInterval = null;

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
const btnDownload = document.getElementById("btn-download");
const statusPanel = document.getElementById("status-panel");
const statusMessage = document.getElementById("status-message");
const statusPercent = document.getElementById("status-percent");
const statusProgressBar = document.getElementById("status-progress-bar");

// 起動時の初期化処理
document.addEventListener("DOMContentLoaded", async () => {
    initFieldList();
    await loadInitialData();
    setupEventListeners();
});

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

// データの初期読み込み
async function loadInitialData() {
    try {
        // 設定情報の取得
        const configResponse = await fetch("/api/config");
        const config = await configResponse.json();
        
        selectedTickers = new Set(config.selected_tickers || []);
        selectedFields = new Set(config.selected_fields || []);
        outputPath = config.output_path || "";
        outputPathInput.value = outputPath;
        
        if (addDateCheckbox) {
            addDateCheckbox.checked = config.add_date_to_filename || false;
        }

        // 銘柄マスターの取得
        const tickersResponse = await fetch("/api/tickers");
        masterTickers = await tickersResponse.json();

        // 描画
        renderTickerList();
        updateFieldCheckboxes();
        updateSelectedCount();
    } catch (error) {
        console.error("データの初期化に失敗しました:", error);
    }
}

// 銘柄リストの描画
function renderTickerList(filterText = "") {
    tickerListContainer.innerHTML = "";
    const filter = filterText.toLowerCase().trim();
    
    const filtered = masterTickers.filter(item => {
        return item.ticker.toLowerCase().includes(filter) || 
               item.name.toLowerCase().includes(filter);
    });

    if (filtered.length === 0) {
        tickerListContainer.innerHTML = `
            <div class="text-center py-8 text-sm text-slate-500">
                該当する銘柄が見つかりません。
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
    // リアルタイム企業検索
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

    // すべて選択ボタン
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

    // 選択クリアボタン
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

    // ダウンロードボタン
    btnDownload.addEventListener("click", () => {
        window.location.href = "/api/download";
    });
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
    btnDownload.classList.add("hidden");
    statusPanel.classList.remove("hidden");
    updateProgressUI(0, 100, "処理を開始しています...", "running");

    try {
        const response = await fetch("/api/fetch", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
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
                btnDownload.classList.remove("hidden");
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
    statusMessage.textContent = message;
    
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
