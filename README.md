# 🌮 TACO 壓力指數

**Treasury · Anxiety · Credit · Outflow**

四大市場壓力維度，精準定位股市抄底時機。數據每日自動更新，零 API Key。

![TACO](https://img.shields.io/badge/TACO-Stress%20Index-E8594F?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxMDAgMTAwIj48dGV4dCB5PSIuOWVtIiBmb250LXNpemU9IjkwIj7wn4yuPC90ZXh0Pjwvc3ZnPg==)

## 📊 四大指標

| 代碼 | 指標 | 數據來源 | 更新頻率 |
|:---:|:---|:---|:---:|
| **T** | 10Y-2Y 國債利差 | [Treasury.gov](https://home.treasury.gov/resource-center/data-chart-center/interest-rates) | 每日 |
| **A** | VIX 恐慌指數 | [Yahoo Finance](https://finance.yahoo.com/quote/%5EVIX/) | 每日 |
| **C** | 高收益債信用利差 | [Yahoo Finance (HYG)](https://finance.yahoo.com/quote/HYG/) | 每日 |
| **O** | 金融壓力合成指標 | VIX 期限結構 + SPY 回撤 | 每日 |

**全部使用免費公開數據，不需要任何 API Key。**

## 🚀 五分鐘部署

### Step 1：Fork 此 Repo

點右上角的 **Fork** 按鈕，複製到你的 GitHub 帳號。

### Step 2：啟用 GitHub Pages

1. 進入你 Fork 的 Repo → **Settings** → **Pages**
2. Source 選 **GitHub Actions**
3. 完成！

### Step 3：啟用 GitHub Actions

1. 進入 **Actions** 頁籤
2. 如果看到 "Workflows aren't being run on this forked repository"，點 **I understand my workflows, go ahead and enable them**
3. 點左側 **🌮 Update TACO Data** → **Run workflow** → **Run workflow**

第一次手動觸發後，之後會自動在每天以下時間更新：
- 🌅 **UTC 00:30**（台灣 08:30）— 亞洲開盤前
- 🌙 **UTC 14:30**（台灣 22:30）— 美股收盤後

### Step 4：訪問你的儀表板

```
https://你的用戶名.github.io/taco-stress-index/
```

## 🌮 壓力等級

| TACO 分數 | 等級 | 訊號 | 建議 |
|:---:|:---|:---|:---|
| 85-100 | 🌮🌮🌮 爆辣模式 | 歷史級壓力 | 分批大膽建倉 |
| 70-84 | 🌮🌮 重辣模式 | 壓力明顯 | 積極佈局 |
| 50-69 | 🌮 微辣模式 | 壓力浮現 | 觀察等待 |
| 30-49 | 😐 原味模式 | 中性 | 準備資金 |
| 0-29 | 🧊 冰鎮模式 | 市場過熱 | 注意風險 |

## 🔧 本地開發

```bash
# 手動抓取數據
python fetch_data.py

# 本地預覽（任選一種）
python -m http.server 8000
# 或
npx serve .
```

然後打開 `http://localhost:8000`。

## 📁 檔案結構

```
taco-stress-index/
├── index.html                          # 儀表板前端
├── data.json                           # 自動更新的數據（由 GitHub Actions 產生）
├── fetch_data.py                       # 數據抓取腳本（零 API Key）
├── .github/workflows/update-data.yml   # 自動排程
└── README.md
```

## ⚠️ 免責聲明

此為教育用途的量化框架，**不構成投資建議**。TACO 壓力指數是根據歷史數據模式設計的觀察工具，不保證未來表現。實際投資決策請結合個人風險承受度，並諮詢專業顧問。

## 📜 授權

MIT License — 自由使用、修改、分享。
