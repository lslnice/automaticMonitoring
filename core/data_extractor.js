/**
 * ctbwp.com 数据提取 — 简单粗暴版
 * 不依赖特定表格结构，直接扫描所有 <tr>，
 * 找到包含马号模式 (X-Y) 且含 "吃" 的行即为已证实交易
 */
(() => {
    "use strict";

    const t = (el) => el ? el.innerText.trim() : "";

    // ========== 提取已证实交易的马号 ==========
    function extractTrades() {
        const trades = [];
        const seen = new Set();

        const allRows = document.querySelectorAll("tr");
        for (const row of allRows) {
            const cells = row.querySelectorAll("td");
            if (cells.length < 3) continue;

            const texts = Array.from(cells).map(c => t(c));

            let combo = "";
            let hasEat = false;
            let race = "";

            for (let i = 0; i < texts.length; i++) {
                // 马号格式: 纯数字-纯数字, 如 "1-2", "12-5"
                if (/^\d+-\d+$/.test(texts[i])) {
                    combo = texts[i];
                }
                // 也匹配带括号的: "(1-3)"
                const m = texts[i].match(/^\(?(\d+-\d+)\)?$/);
                if (m) {
                    combo = m[1];
                }
                // "吃" 状态
                if (texts[i] === "吃") {
                    hasEat = true;
                }
                // 场次号 (第一个纯数字短文本)
                if (!race && /^\d{1,2}$/.test(texts[i])) {
                    race = texts[i];
                }
            }

            if (combo && hasEat && !seen.has(combo)) {
                seen.add(combo);
                trades.push({
                    horse_combo: combo,
                    race: race,
                    cells: texts
                });
            }
        }

        return trades;
    }

    // ========== Header 提取 ==========
    function extractHeader() {
        const header = {
            account_name: "",
            credit_balance: "",
            race_location: "",
            race_number: ""
        };

        try {
            const bodyText = document.body ? document.body.innerText : "";

            // 账户名 + 信用余额: "bb6633  信用余额 HK$975,285.42"
            const accMatch = bodyText.match(/([a-zA-Z]\w{3,10})\s+信用余额\s*(HK\$[\d,]+\.?\d*)/);
            if (accMatch) {
                header.account_name = accMatch[1];
                header.credit_balance = accMatch[2];
            }

            // 赛事场次: "场 2" 或 "Race 2"
            const raceMatch = bodyText.match(/场\s*(\d+)/);
            if (raceMatch) header.race_number = raceMatch[1];

            // 赛事地点
            const locCandidates = ["纽卡斯尔", "提阿洛亚", "沙田", "跑马地", "快活谷",
                "伊普威治", "启莫", "多宝", "达尔文", "Newcastle", "Te Aroha"];
            for (const loc of locCandidates) {
                if (bodyText.includes(loc)) {
                    header.race_location = loc;
                    break;
                }
            }
        } catch (e) {
            // ignore
        }

        return header;
    }

    return {
        header: extractHeader(),
        trades: extractTrades(),
        timestamp: Date.now() / 1000
    };
})();
