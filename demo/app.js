/* 界面与交互。数据保存在浏览器 localStorage，零依赖。 */
(function () {
  "use strict";

  var TG = window.TG;
  var CATS = window.TG_CATEGORIES;
  var LEVELS = window.TG_LEVELS;
  var STORE_KEY = "tradeguard.reports.v1";

  var state = {
    view: "check",
    reports: [],
    query: "",
    parsed: null,
    paste: "",
    reportPrefill: "",
    privacy: true,
    filters: { keyword: "", category: "", level: "" },
    libraryProfiles: []
  };

  var VIEWS = { check: viewCheck, report: viewReport, library: viewLibrary, dashboard: viewDashboard, settings: viewSettings };

  /* ------------------------------------------------------------ 存储 */

  function loadReports() {
    try {
      var raw = localStorage.getItem(STORE_KEY);
      if (!raw) return null;
      var data = JSON.parse(raw);
      if (data && Array.isArray(data.reports)) return data.reports;
      if (Array.isArray(data)) return data;
    } catch (error) {
      return null;
    }
    return null;
  }

  function persist() {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify({ version: 1, seeded: true, reports: state.reports }));
    } catch (error) {
      toast("浏览器存储不可用，本次记录可能无法保存");
    }
  }

  function nextId() {
    var max = 0;
    state.reports.forEach(function (report) {
      var id = Number(report.id) || 0;
      if (id > max) max = id;
    });
    return max + 1;
  }

  /* ------------------------------------------------------------ 工具 */

  function esc(value) { return TG.escapeHtml(value); }
  function pad(value) { return String(value).padStart(2, "0"); }

  function todayValue() {
    var date = new Date();
    return date.getFullYear() + "-" + pad(date.getMonth() + 1) + "-" + pad(date.getDate());
  }

  function dateValue(date) {
    return date.getFullYear() + "-" + pad(date.getMonth() + 1) + "-" + pad(date.getDate());
  }

  function uniquePhones() {
    var set = new Set();
    state.reports.forEach(function (report) {
      (report.phones || []).forEach(function (phone) { set.add(phone); });
    });
    return set.size;
  }

  function allProfiles() {
    var groups = new Map();
    state.reports.forEach(function (report) {
      var phone = (report.phones || [])[0] || "";
      var key = phone || "__" + report.id;
      if (!groups.has(key)) groups.set(key, { phone: phone, reports: [] });
      groups.get(key).reports.push(report);
    });
    return Array.from(groups.values()).map(function (group) {
      return TG.buildProfile(group.phone, group.reports, "", "text", true);
    });
  }

  function riskBadge(risk) {
    if (risk.tone === "unknown") return '<span class="risk unknown">暂无记录</span>';
    return '<span class="risk ' + risk.tone + '">' + esc(risk.label) + " · " + risk.score + "</span>";
  }

  function categoryPills(categories) {
    if (!categories || !categories.length) return "";
    return categories.map(function (item) {
      return '<span class="pill">' + esc(item.label) + " <b>×" + item.count + "</b></span>";
    }).join("");
  }

  function reportItem(report) {
    var amount = Number(report.amount) > 0
      ? " · " + esc(report.currency || "USD") + " " + Number(report.amount).toLocaleString("en-US") : "";
    var labels = (report.categories || []).map(function (key) {
      return esc(CATS[key] ? CATS[key].label : key);
    }).join(" · ");
    var evidence = report.evidence ? '<div class="quote">' + esc(report.evidence) + "</div>" : "";
    var chat = report.chatSha
      ? '<div class="chat-meta">📎 聊天记录已核验指纹 <span class="mono">' + esc(String(report.chatSha).slice(0, 12)) + "…</span> · " + esc(report.chatMessageCount || "—") + " 条消息</div>"
      : "";
    var source = report.source === "demo" ? "演示" : report.source === "chat_import" ? "聊天导入" : report.source === "csv_import" ? "批量导入" : "手动上报";
    return '<div class="report-item">'
      + '<div class="report-meta"><span>' + esc(report.incidentDate || String(report.createdAt || "").slice(0, 10)) + " · " + labels + amount + "</span>"
      + "<span>" + source + " · 可信度 " + esc(report.credibility || 60) + "</span></div>"
      + '<div class="report-text">' + esc(report.narrative) + "</div>"
      + evidence + chat + "</div>";
  }

  function profileCard(profile, showFullPhone) {
    var phone = showFullPhone ? profile.displayPhone : profile.maskedPhone;
    var phoneHtml = phone ? '<div class="phone">' + esc(phone) + "</div>" : "";
    var meta = [profile.company, profile.country].filter(Boolean).join(" · ") || "未填写公司 / 国家";
    var match = profile.matchReason ? '<div class="match">' + esc(profile.matchReason) + "</div>" : "";
    var demo = profile.hasDemo ? '<span class="tag">演示数据</span>' : "";
    var reasons = (profile.risk.reasons || []).slice(0, 4).map(esc).join(" · ");
    var reports = profile.reports.map(reportItem).join("");
    return '<div class="card">'
      + '<div class="row-between"><div>'
      + '<div class="name">' + esc(profile.displayName) + demo + "</div>"
      + '<div class="sub">' + esc(meta) + "</div>" + phoneHtml + match
      + "</div><div class=\"right\">" + riskBadge(profile.risk)
      + '<div class="sub" style="margin-top:6px">' + profile.reportCount + " 条记录 · 最近 " + TG.agoLabel(profile.lastSeen) + "</div>"
      + "</div></div>"
      + '<div class="pills">' + categoryPills(profile.categories) + "</div>"
      + '<div class="reasons"><span>评分依据</span> · ' + esc(reasons) + "</div>"
      + "<details><summary>查看 " + profile.reports.length + " 条举报记录与证据</summary>" + reports + "</details>"
      + "</div>";
  }

  function hero(kicker, title, subtitle, tag, compact) {
    return '<section class="hero' + (compact ? " compact" : "") + '">'
      + '<div class="kicker">' + esc(kicker) + "</div>"
      + "<h1>" + esc(title) + "</h1>"
      + "<p>" + esc(subtitle) + "</p>"
      + (tag ? '<div class="hero-tag">' + esc(tag) + "</div>" : "")
      + "</section>";
  }

  function sectionTitle(text) { return '<div class="section-title">' + esc(text) + "</div>"; }

  function emptyState(icon, title, lines) {
    return '<div class="empty"><div class="icon">' + icon + "</div><h3>" + esc(title) + "</h3>"
      + lines.map(function (line) { return "<p>" + esc(line) + "</p>"; }).join("") + "</div>";
  }

  function toast(message) {
    var element = document.getElementById("toast");
    if (!element) return;
    element.textContent = message;
    element.classList.add("show");
    window.clearTimeout(toast._timer);
    toast._timer = window.setTimeout(function () { element.classList.remove("show"); }, 2600);
  }

  /* ------------------------------------------------------------ 查询页 */

  function viewCheck() {
    var html = hero(
      "TRADEGUARD · 交易前先查一查",
      "这个名字，靠谱吗？",
      "输入 WhatsApp 号码、公司名或联系人，查一查本机情报库里的历史举报。数据只存在你的电脑上，查询本身不会通知对方。",
      "已收录 " + state.reports.length + " 条举报 · 覆盖 " + uniquePhones() + " 个号码"
    );
    html += '<form id="search-form" class="search-form">'
      + '<input id="search-input" autocomplete="off" placeholder="例如：+1 555 010 4477、NovaPeak Supplements、Mike R." value="' + esc(state.query) + '">'
      + '<button class="btn primary" type="submit">立即查询</button></form>';
    html += '<div class="examples"><span>试试：</span>'
      + '<button type="button" class="chip-btn" data-example="+1 555 010 4477">+1 555 010 4477</button>'
      + '<button type="button" class="chip-btn" data-example="NovaPeak Supplements">NovaPeak Supplements</button>'
      + '<button type="button" class="chip-btn" data-example="+44 7700 900123">+44 7700 900123</button>'
      + "</div>";
    html += state.query ? searchResultHtml(state.query) : introHtml();
    return html;
  }

  function introHtml() {
    var cards = [
      ["🔎", "先查再谈", "谈样品、谈价格之前，先用号码和公司名查一遍。30 秒，可能省下几周的样品和时间。"],
      ["⚖️", "风险提示 ≠ 判决", "单条举报最高只到中风险。请结合多条记录、证据、时间和自己的判断，不要只凭一个分数拉黑客户。"],
      ["🕳️", "无记录 ≠ 可信", "骗子会换号、换公司名。没有记录只说明没人报过，验厂、担保、分阶段付款仍然是底线。"]
    ];
    return sectionTitle("查询之前，先记住三条")
      + '<div class="metrics" style="grid-template-columns:repeat(3,1fr)">'
      + cards.map(function (card) {
        return '<div class="card" style="margin:0"><div style="font-size:1.5rem">' + card[0] + "</div>"
          + '<div class="name" style="margin-top:6px">' + esc(card[1]) + "</div>"
          + '<div class="sub" style="margin-top:6px;line-height:1.8">' + esc(card[2]) + "</div></div>";
      }).join("")
      + "</div>"
      + sectionTitle("这个库怎么来的")
      + '<div class="notice">每一条记录都来自真实受骗者的主动上报，包含号码、问题类型、经过和聊天证据摘要。系统会聚合同一个号码的多条记录，给出<strong>可解释</strong>的风险分，而不是一个黑箱结论。当前版本把数据保存在这台电脑的浏览器里，你可以在「设置与合规」里备份、导出或清空。</div>';
  }

  function searchResultHtml(query) {
    var result = TG.searchReports(state.reports, query);
    if (!result.profiles.length && !result.textReports.length) return noResultHtml(query, result);

    var exact = result.profiles.filter(function (profile) { return profile.matchKind === "phone_exact"; });
    var suffix = result.profiles.filter(function (profile) { return profile.matchKind === "phone_suffix"; });
    var byName = result.profiles.filter(function (profile) { return profile.matchKind === "text"; });
    var html = sectionTitle("查询结果") + '<div class="name" style="margin-bottom:12px">' + esc(query) + "</div>";

    if (exact.length) {
      html += '<div class="notice warn">⚠️ 本地库中找到了 <strong>' + exact.length + "</strong> 个号码记录。以下风险分来自历史举报聚合，不是法律结论；请看完证据再决定。</div>";
      html += exact.map(function (profile) { return profileCard(profile, true); }).join("");
    }
    if (suffix.length) {
      html += '<div class="notice warn">没有完全一致的号码，但以下号码与查询号码<strong>尾号相同</strong>，可能是同一人换号，请人工核对。</div>';
      html += suffix.map(function (profile) { return profileCard(profile, false); }).join("");
    }
    if (byName.length) {
      html += '<div class="notice warn">号码没有命中，但<strong>公司 / 联系人名称</strong>命中了以下记录。请结合公司地址、域名、联系人核实是否为同一主体。</div>';
      html += byName.map(function (profile) { return profileCard(profile, false); }).join("");
    }
    if (result.textReports.length) {
      html += sectionTitle("相关记录");
      html += result.textReports.map(reportItem).join("");
    }
    if (result.notes.length) {
      html += '<p class="sub">' + result.notes.map(esc).join("　") + "</p>";
    }
    html += '<p class="sub" style="margin-top:16px">风险分仅用于提示交易风险，不构成对任何个人或公司的法律认定。</p>';
    return html + interpretationHtml();
  }

  function noResultHtml(query, result) {
    var html = emptyState("🕳️", "本地库暂无「" + query + "」的记录", [
      "没有记录，不代表对方可信。骗子经常换号、换公司名、换接头人。",
      "建议先视频验厂/验货、核实公司注册信息，再走可追溯的付款方式。",
      "如果你和这个人打过交道并踩了坑，花 2 分钟上报，下一个人就能查到。"
    ]);
    var phone = result.phoneInput || "";
    html += '<div class="actions">'
      + '<button type="button" class="btn primary" data-action="prefill-report" data-query="' + esc(phone) + '">我遇到过这个人，去上报</button>'
      + '<button type="button" class="btn" data-action="clear-query">换个号码再查</button>'
      + "</div>";
    return html + interpretationHtml();
  }

  function interpretationHtml() {
    return '<details><summary>风险分是怎么算的？</summary>'
      + '<div class="sub" style="line-height:1.9;margin-top:8px">'
      + "<strong>加分项</strong>：被举报次数、问题类型严重度、最近 90 天是否活跃、是否附带聊天记录、涉及金额、举报可信度。<br><br>"
      + "<strong>保守设计</strong>：单条未经交叉验证的举报，有聊天记录且可信度 ≥70 时最高 55 分（中风险）；仅文字描述最高 39 分（低风险）。多条记录 + 严重类型 + 近期活跃，才可能进入高风险。<br><br>"
      + "这是一个<strong>风险提示工具</strong>，不是征信报告，也不是法院判决。</div></details>";
  }

  /* ------------------------------------------------------------ 上报页 */

  function viewReport() {
    var html = hero(
      "REPORT · 上传被骗经历",
      "把一次受骗，变成所有人的防线",
      "上传 WhatsApp 导出的聊天记录，系统自动提取对方号码、时间线和风险信号；补充经过后入库。只保存必要证据，不保存完整聊天原文。",
      "",
      true
    );
    html += '<div class="card">' + sectionTitle("1 · 上传或粘贴聊天记录")
      + '<div class="sub" style="margin-bottom:10px">WhatsApp：打开聊天 → 更多 → 导出聊天 → 不含媒体，得到 .txt 文件。文件只在浏览器本地解析。</div>'
      + '<div class="upload-box"><input type="file" id="chat-file" accept=".txt,.log">'
      + '<div class="sub" style="margin:8px 0">或者直接把关键聊天内容粘贴到这里（支持 Android / iOS 导出格式）：</div>'
      + '<textarea id="chat-paste" rows="5" placeholder="[2026/10/01, 10:23:45] Mike: Sample is for testing, you pay shipping first...">' + esc(state.paste) + "</textarea>"
      + '<div class="actions"><button type="button" class="btn primary" id="parse-chat">解析聊天记录</button>'
      + '<button type="button" class="btn" id="clear-parse">清空解析结果</button></div></div></div>';
    if (state.parsed) html += parsedHtml(state.parsed);
    html += reportFormHtml();
    return html;
  }

  function parsedHtml(parsed) {
    var html = '<div class="card">' + sectionTitle("解析结果")
      + '<div class="metrics" style="grid-template-columns:repeat(4,1fr)">'
      + '<div class="metric"><span>消息数</span><b>' + parsed.messageCount + "</b></div>"
      + '<div class="metric"><span>参与者</span><b>' + parsed.participantCount + "</b></div>"
      + '<div class="metric"><span>识别号码</span><b>' + parsed.phones.length + "</b></div>"
      + '<div class="metric"><span>风险信号</span><b>' + parsed.signals.length + "</b></div></div>"
      + '<div class="sub">文件：' + esc(parsed.filename) + " · 时间范围：" + esc(parsed.dateRange) + "</div>";
    parsed.warnings.forEach(function (warning) { html += '<div class="notice warn" style="margin-top:10px">' + esc(warning) + "</div>"; });

    if (parsed.phones.length) {
      html += '<div style="margin-top:12px"><strong>识别到的号码</strong><div class="pills" style="margin-top:8px">'
        + parsed.phones.map(function (phone) {
          var confidence = phone.confidence === "high" ? "高" : phone.confidence === "medium" ? "中" : "低";
          return '<span class="pill">' + esc(phone.display || TG.formatPhone(phone.norm)) + " · " + phone.mentions + " 次 · " + confidence + "</span>";
        }).join("") + "</div></div>";
    }
    if (parsed.signals.length) {
      html += '<div style="margin-top:12px"><strong>聊天里的风险信号（只作提示）</strong><div class="pills" style="margin-top:8px">'
        + parsed.signals.map(function (signal) {
          return '<span class="pill">' + esc(signal.label) + " <b>×" + signal.hits + "</b></span>";
        }).join("") + "</div></div>";
    }
    var details = [];
    if (parsed.senders.length) details.push("发送者：" + parsed.senders.map(function (entry) { return entry[0] + "（" + entry[1] + " 条）"; }).join("、"));
    if (parsed.moneyMentions.length) details.push("金额提及：" + parsed.moneyMentions.slice(0, 6).join("、"));
    if (parsed.companyHints.length) details.push("邮箱域名线索：" + parsed.companyHints.join("、"));
    if (parsed.mediaCount) details.push("媒体占位符：" + parsed.mediaCount + " 处");
    if (parsed.urlCount) details.push("链接：" + parsed.urlCount + " 个");
    details.forEach(function (detail) { html += '<div class="sub" style="margin-top:6px">' + esc(detail) + "</div>"; });
    var evidence = TG.evidenceHint(parsed);
    if (evidence) html += '<div class="quote" style="margin-top:12px">' + esc(evidence) + "</div>";
    return html + "</div>";
  }

  function reportFormHtml() {
    var parsed = state.parsed;
    var phoneOptions = "";
    if (parsed && parsed.phones.length) {
      phoneOptions = parsed.phones.map(function (phone, index) {
        return '<option value="' + esc(phone.norm) + '"' + (index === 0 ? " selected" : "") + ">"
          + esc(phone.display || TG.formatPhone(phone.norm)) + "（出现 " + phone.mentions + " 次）</option>";
      }).join("");
    }
    var defaultName = parsed && parsed.senders.length ? parsed.senders[0][0] : "";
    var defaultCompany = parsed && parsed.companyHints.length ? parsed.companyHints[0] : "";
    var defaultDate = parsed && parsed.lastTs ? dateValue(parsed.lastTs) : todayValue();
    var defaultEvidence = parsed ? TG.evidenceHint(parsed) : "";
    var selectedCats = parsed ? parsed.primaryCategories : ["fake_inquiry"];

    var html = '<form id="report-form" class="card">' + sectionTitle("2 · 确认真实信息")
      + '<div class="grid">'
      + '<div class="field"><label>对方主要号码</label>'
      + (phoneOptions
        ? '<select id="report-phone">' + phoneOptions + "</select>"
        : '<div class="sub" style="padding:10px 0">没有识别到号码，请在右侧手动填写。</div>')
      + '<input type="text" id="report-manual" value="' + esc(state.reportPrefill) + '" placeholder="手动输入 / 修正号码，例如 +86 138 0013 8000">'
      + '<div class="hint">手动输入会优先于上面的选择；支持 +、00、空格、括号。</div></div>'
      + '<div class="field"><label>对方称呼 / 昵称</label>'
      + '<input type="text" id="report-name" value="' + esc(defaultName) + '" placeholder="例如：Mike R.">'
      + '<label>公司名（如知道）</label><input type="text" id="report-company" value="' + esc(defaultCompany) + '" placeholder="例如：NovaPeak Supplements LLC">'
      + "</div>"
      + '<div class="field"><label>国家 / 地区</label><input type="text" id="report-country" placeholder="例如：美国、United Kingdom"></div>'
      + '<div class="field"><label>其他号码（可选，逗号分隔）</label><input type="text" id="report-extra" placeholder="同一人的其他 WhatsApp 号"></div>'
      + '<div class="field full"><label>问题类型（可多选）</label><div class="cat-grid">'
      + Object.keys(CATS).map(function (key) {
        return '<label class="cat-check"><input type="checkbox" name="cat" value="' + key + '"'
          + (selectedCats.indexOf(key) !== -1 ? " checked" : "") + "> " + esc(CATS[key].label) + "</label>";
      }).join("")
      + "</div></div>"
      + '<div class="field"><label>涉及金额（可选）</label><input type="number" id="report-amount" min="0" step="100" value="0"></div>'
      + '<div class="field"><label>币种</label><select id="report-currency">'
      + ["USD", "CNY", "EUR", "GBP", "AUD", "HKD", "JPY", "其他"].map(function (currency) {
        return '<option value="' + currency + '">' + currency + "</option>";
      }).join("") + "</select></div>"
      + '<div class="field"><label>发生时间</label><input type="date" id="report-date" value="' + esc(defaultDate) + '" max="' + todayValue() + '"></div>'
      + '<div class="field full"><label>事情经过（必填，至少 10 个字）</label>'
      + '<textarea id="report-narrative" rows="5" placeholder="什么时候、怎么认识的、对方承诺了什么、你损失了什么、对方后来怎么处理……"></textarea></div>'
      + '<div class="field full"><label>证据摘要（可选）</label>'
      + '<textarea id="report-evidence" rows="3" placeholder="粘贴 1–3 句最关键的聊天原话；不要粘贴完整聊天记录。">' + esc(defaultEvidence) + "</textarea></div>"
      + '<div class="field full"><label class="checkline"><input type="checkbox" id="report-consent"> 我确认以上信息基于真实经历，并愿意在必要时提供聊天记录原件。我理解恶意举报可能承担法律责任。</label></div>'
      + "</div>"
      + '<div id="form-error" class="notice danger" style="display:none;margin-top:14px"></div>'
      + '<div class="actions"><button class="btn primary" type="submit">提交并入库</button>'
      + '<span class="sub" style="align-self:center">只保存号码、类型、经过与证据摘要，不保存完整聊天。</span></div>'
      + "</form>";
    return html;
  }

  /* ------------------------------------------------------------ 情报库 */

  function viewLibrary() {
    var html = hero(
      "INTEL · 本地情报库",
      "所有被上报过的号码，都在这里",
      "按号码聚合记录，展示风险分、涉及类型和最近活跃时间。列表默认脱敏，可在左侧关闭「隐藏完整号码」。",
      "",
      true
    );
    var filter = state.filters;
    html += '<form id="library-form" class="card"><div class="grid" style="grid-template-columns:1.6fr 1fr .9fr auto">'
      + '<div class="field"><label>搜索</label><input type="text" id="library-keyword" value="' + esc(filter.keyword) + '" placeholder="号码 / 公司 / 联系人 / 国家"></div>'
      + '<div class="field"><label>问题类型</label><select id="library-category"><option value="">全部类型</option>'
      + Object.keys(CATS).map(function (key) {
        return '<option value="' + key + '"' + (filter.category === key ? " selected" : "") + ">" + esc(CATS[key].label) + "</option>";
      }).join("") + "</select></div>"
      + '<div class="field"><label>风险</label><select id="library-level"><option value="">全部风险</option>'
      + ["high", "medium", "low", "watch"].map(function (level) {
        return '<option value="' + level + '"' + (filter.level === level ? " selected" : "") + ">" + LEVELS[level].label + "</option>";
      }).join("") + "</select></div>"
      + '<div class="field"><label>&nbsp;</label><button class="btn primary" type="submit">筛选</button></div>'
      + "</div></form>";

    var profiles = allProfiles();
    var keyword = filter.keyword.trim().toLowerCase();
    if (filter.keyword && TG.digitsOnly(filter.keyword).length >= 7) keyword = TG.digitsOnly(filter.keyword);
    var filtered = profiles.filter(function (profile) {
      if (keyword) {
        var haystack = [profile.phone, profile.contactName, profile.company, profile.country]
          .join(" ").toLowerCase();
        if (haystack.indexOf(keyword) === -1) return false;
      }
      if (filter.category && !profile.categories.some(function (item) { return item.key === filter.category; })) return false;
      if (filter.level && profile.risk.level !== filter.level) return false;
      return true;
    });
    filtered.sort(function (a, b) {
      if (b.risk.score !== a.risk.score) return b.risk.score - a.risk.score;
      return String(b.lastSeen).localeCompare(String(a.lastSeen));
    });
    state.libraryProfiles = filtered;

    html += '<div class="row-between" style="margin:6px 0 10px"><span class="sub">共 ' + filtered.length + " 个号码 / 主体</span>"
      + '<button type="button" class="btn" data-action="export-contacts">导出筛选结果 CSV</button></div>';

    if (!filtered.length) {
      html += emptyState("🗂️", "没有符合条件的记录", ["试试清空搜索词或把风险等级切回「全部风险」。", "库是空的？先去「上报记录」提交第一条。"]);
    } else {
      html += filtered.map(function (profile) { return profileCard(profile, !state.privacy); }).join("");
    }
    html += '<p class="sub" style="margin-top:16px">隐私提示：这里是你本机的私人情报库。对外转发或公开这些记录前，请先核实事实，并注意《个人信息保护法》《民法典》名誉权等法律边界。</p>';
    return html;
  }

  /* ------------------------------------------------------------ 看板 */

  function viewDashboard() {
    var profiles = allProfiles();
    var high = profiles.filter(function (profile) { return profile.risk.level === "high"; }).length;
    var monthPrefix = todayValue().slice(0, 7);
    var thisMonth = state.reports.filter(function (report) {
      return String(report.createdAt || "").slice(0, 7) === monthPrefix;
    }).length;
    var demoCount = state.reports.filter(function (report) { return report.source === "demo"; }).length;

    var html = hero("DASHBOARD · 数据看板", "骗术在往哪里走？", "基于本地库的聚合视图：新增趋势、问题类型、国家分布和高风险号码。", "", true);
    html += '<div class="metrics">'
      + metric("举报记录", state.reports.length)
      + metric("涉及号码", uniquePhones())
      + metric("高风险号码", high)
      + metric("本月新增", thisMonth)
      + "</div>";
    if (demoCount) html += '<div class="notice warn">当前包含 ' + demoCount + " 条演示数据（虚构号码），用于展示界面；可在「设置与合规」一键清除。</div>";

    if (!state.reports.length) {
      return html + emptyState("📊", "还没有数据", ["先到「上报记录」提交第一条举报，或到设置中载入演示数据。"]);
    }

    var categoryCounts = new Map();
    state.reports.forEach(function (report) {
      (report.categories || []).forEach(function (key) {
        categoryCounts.set(key, (categoryCounts.get(key) || 0) + 1);
      });
    });
    var categoryRows = Array.from(categoryCounts.entries()).sort(function (a, b) { return b[1] - a[1]; });
    var maxCategory = Math.max.apply(null, categoryRows.map(function (row) { return row[1]; }).concat([1]));

    var months = [];
    for (var offset = 5; offset >= 0; offset -= 1) {
      var date = new Date();
      date.setDate(1);
      date.setMonth(date.getMonth() - offset);
      var label = date.getFullYear() + "-" + pad(date.getMonth() + 1);
      months.push({
        label: label,
        count: state.reports.filter(function (report) {
          return String(report.incidentDate || report.createdAt || "").slice(0, 7) === label;
        }).length
      });
    }
    var maxMonth = Math.max.apply(null, months.map(function (month) { return month.count; }).concat([1]));

    html += '<div class="two-col"><div class="card">' + sectionTitle("问题类型分布")
      + '<div class="bars">' + categoryRows.map(function (row) {
        return '<div class="bar-row"><label>' + esc(CATS[row[0]] ? CATS[row[0]].label : row[0]) + "</label>"
          + '<div class="bar-track"><div class="bar-fill" style="width:' + Math.round(row[1] / maxCategory * 100) + '%"></div></div>'
          + "<b>" + row[1] + "</b></div>";
      }).join("") + "</div></div>"
      + '<div class="card">' + sectionTitle("近 6 个月新增")
      + '<div class="monthly">' + months.map(function (month) {
        return '<div class="month"><b>' + month.count + '</b><div class="col" style="height:' + Math.max(4, Math.round(month.count / maxMonth * 110)) + 'px"></div><span>' + month.label.slice(2) + "</span></div>";
      }).join("") + "</div></div></div>";

    var countries = new Map();
    state.reports.forEach(function (report) {
      if (report.country) countries.set(report.country, (countries.get(report.country) || 0) + 1);
    });
    var countryRows = Array.from(countries.entries()).sort(function (a, b) { return b[1] - a[1]; }).slice(0, 6);
    html += '<div class="two-col" style="margin-top:18px"><div class="card">' + sectionTitle("国家 / 地区")
      + (countryRows.length
        ? '<div class="bars">' + countryRows.map(function (row) {
          return '<div class="bar-row"><label>' + esc(row[0]) + '</label><div class="bar-track"><div class="bar-fill" style="width:'
            + Math.round(row[1] / countryRows[0][1] * 100) + '%"></div></div><b>' + row[1] + "</b></div>";
        }).join("") + "</div>"
        : '<div class="sub">暂无国家数据</div>')
      + "</div><div class=\"card\">" + sectionTitle("最近入库")
      + state.reports.slice().sort(function (a, b) {
        return String(b.createdAt || "").localeCompare(String(a.createdAt || ""));
      }).slice(0, 3).map(reportItem).join("")
      + "</div></div>";

    html += '<p class="sub" style="margin-top:14px">统计口径：同一号码的多条举报合并为号码档案；看板包含演示数据。</p>';
    return html;
  }

  function metric(label, value) {
    return '<div class="metric"><span>' + esc(label) + "</span><b>" + esc(value) + "</b></div>";
  }

  /* ------------------------------------------------------------ 设置 */

  function viewSettings() {
    var high = allProfiles().filter(function (profile) { return profile.risk.level === "high"; }).length;
    var html = hero("SETTINGS · 设置与合规", "你的数据，只属于你", "备份、导入导出、演示数据，以及这个产品必须守住的边界。", "", true);
    html += '<div class="two-col"><div>'
      + '<div class="card">' + sectionTitle("数据与备份")
      + '<div class="sub">当前：<strong>' + state.reports.length + "</strong> 条举报 · <strong>" + uniquePhones() + "</strong> 个号码 · <strong>" + high + "</strong> 个高风险 · 存储在本浏览器 localStorage。</div>"
      + '<div class="actions"><button type="button" class="btn primary" data-action="export-backup">下载 JSON 备份</button>'
      + '<button type="button" class="btn" data-action="export-all-csv">导出全部 CSV</button></div></div>'
      + '<div class="card">' + sectionTitle("批量导入备份")
      + '<div class="sub" style="margin-bottom:10px">导入会覆盖当前数据，请先下载备份。支持本页导出的 JSON。</div>'
      + '<input type="file" id="import-backup" accept=".json,application/json"></div>'
      + "</div><div>"
      + '<div class="card">' + sectionTitle("演示数据")
      + '<div class="sub" style="margin-bottom:10px">首次打开会写入 9 条虚构演示记录（各国保留的影视号码），方便体验。真实使用前建议清除。</div>'
      + '<div class="actions"><button type="button" class="btn" data-action="clear-demo">删除全部演示数据</button>'
      + '<button type="button" class="btn" data-action="reset-demo">重新载入演示数据</button></div></div>'
      + '<div class="card">' + sectionTitle("危险操作")
      + '<div class="sub" style="margin-bottom:10px">清空前建议先下载备份。此操作不可撤销。</div>'
      + '<button type="button" class="btn danger" data-action="clear-all">清空所有记录</button></div>'
      + "</div></div>";

    html += '<div class="card" style="margin-top:18px">' + sectionTitle("合规边界")
      + '<div class="sub" style="line-height:1.9">'
      + "<strong>产品原则</strong><br>"
      + "· 结果只是风险提示，不是事实认定、征信报告或法律判决；<br>"
      + "· 单条未经交叉验证的举报最高只到中风险；<br>"
      + "· 每条记录都应提供申诉入口（完整版本已内置）；<br>"
      + "· 数据最小化：只存号码、类型、经过、金额与证据摘要，不保存完整聊天；<br>"
      + "· 数据默认只在本机，不上传云端。<br><br>"
      + "<strong>使用边界（重要）</strong><br>"
      + "· 不要把这个库里的内容公开发布、群发或做成「骗子名单」网站，除非已完成核实并咨询律师；<br>"
      + "· 中国场景注意《个人信息保护法》的最小必要、告知同意、删除权，以及《民法典》名誉权 / 商誉；<br>"
      + "· 海外场景注意 GDPR、当地诽谤法与数据跨境规则；<br>"
      + "· 本工具不构成法律意见。"
      + "</div></div>";
    html += '<p class="sub">TradeGuard 本地演示版 · 数据仅保存在当前浏览器 · 换浏览器 / 清缓存会丢失，请定期导出备份。</p>';
    return html;
  }

  /* ------------------------------------------------------------ 事件 */

  function bindView() {
    if (state.view === "check") bindCheck();
    else if (state.view === "report") bindReport();
    else if (state.view === "library") bindLibrary();
    else if (state.view === "settings") bindSettings();
  }

  function bindCheck() {
    var form = document.getElementById("search-form");
    if (form) {
      form.addEventListener("submit", function (event) {
        event.preventDefault();
        state.query = document.getElementById("search-input").value.trim();
        render();
      });
    }
    document.querySelectorAll("[data-example]").forEach(function (button) {
      button.addEventListener("click", function () {
        state.query = button.getAttribute("data-example");
        render();
      });
    });
    document.querySelectorAll('[data-action="clear-query"]').forEach(function (button) {
      button.addEventListener("click", function () {
        state.query = "";
        render();
      });
    });
    document.querySelectorAll('[data-action="prefill-report"]').forEach(function (button) {
      button.addEventListener("click", function () {
        state.reportPrefill = button.getAttribute("data-query") || "";
        navigate("report");
      });
    });
  }

  function bindReport() {
    var parseButton = document.getElementById("parse-chat");
    if (parseButton) parseButton.addEventListener("click", handleParse);
    var clearButton = document.getElementById("clear-parse");
    if (clearButton) clearButton.addEventListener("click", function () {
      state.parsed = null;
      state.paste = "";
      render();
    });
    var form = document.getElementById("report-form");
    if (form) form.addEventListener("submit", handleReportSubmit);
  }

  async function handleParse() {
    var fileInput = document.getElementById("chat-file");
    var pasteInput = document.getElementById("chat-paste");
    var text = pasteInput ? pasteInput.value : "";
    var filename = "粘贴内容.txt";
    if (fileInput && fileInput.files && fileInput.files[0]) {
      var file = fileInput.files[0];
      if (file.size > 8 * 1024 * 1024) {
        toast("文件超过 8 MB，请截取关键部分后再上传");
        return;
      }
      text = await file.text();
      filename = file.name;
    }
    state.paste = text;
    if (!text.trim()) {
      toast("请先上传 .txt 文件，或粘贴一段聊天内容");
      return;
    }
    var parsed = await TG.parseChat(text, filename);
    state.parsed = parsed;
    render();
  }

  function showFormError(message) {
    var box = document.getElementById("form-error");
    if (!box) { toast(message); return; }
    box.textContent = message;
    box.style.display = "block";
    box.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function handleReportSubmit(event) {
    event.preventDefault();
    var errorBox = document.getElementById("form-error");
    if (errorBox) { errorBox.style.display = "none"; errorBox.textContent = ""; }

    var manualRaw = (document.getElementById("report-manual").value || "").trim();
    var manual = manualRaw ? TG.normalizePhone(manualRaw) : null;
    if (manualRaw && !manual) return showFormError("手动输入的号码不合法，请输入 8–15 位有效号码。");

    var select = document.getElementById("report-phone");
    var phones = [];
    if (manual) phones.push(manual);
    else if (select && select.value) phones.push(select.value);
    var extraRaw = (document.getElementById("report-extra").value || "").trim();
    if (extraRaw) {
      extraRaw.split(/[;；,，|]/).forEach(function (part) {
        var normalized = TG.normalizePhone(part.trim());
        if (normalized) phones.push(normalized);
      });
    }
    phones = Array.from(new Set(phones));

    var name = (document.getElementById("report-name").value || "").trim();
    var company = (document.getElementById("report-company").value || "").trim();
    var country = (document.getElementById("report-country").value || "").trim();
    var categories = Array.from(document.querySelectorAll('input[name="cat"]:checked')).map(function (input) { return input.value; });
    var amount = Number(document.getElementById("report-amount").value) || 0;
    var currency = document.getElementById("report-currency").value;
    var incidentDate = document.getElementById("report-date").value || todayValue();
    var narrative = (document.getElementById("report-narrative").value || "").trim();
    var evidence = (document.getElementById("report-evidence").value || "").trim();
    var consent = document.getElementById("report-consent").checked;

    if (!phones.length && !name && !company) return showFormError("至少填写一个号码、公司名或联系人，否则这条记录无法被查到。");
    if (!categories.length) return showFormError("请至少选择一种问题类型。");
    if (narrative.length < 10) return showFormError("事情经过太短，请至少写 10 个字。");
    if (!consent) return showFormError("请勾选真实性确认后再提交。");

    var parsed = state.parsed;
    var report = {
      id: nextId(),
      createdAt: new Date().toISOString(),
      incidentDate: incidentDate,
      contactName: name,
      company: company,
      country: country,
      phones: phones,
      categories: categories,
      amount: amount > 0 ? amount : 0,
      currency: currency,
      narrative: narrative,
      evidence: evidence,
      source: parsed ? "chat_import" : "manual",
      chatFilename: parsed ? parsed.filename : "",
      chatSha: parsed ? parsed.sha256 : "",
      chatMessageCount: parsed ? parsed.messageCount : 0,
      credibility: parsed ? 70 : 55,
      status: "approved"
    };
    state.reports.unshift(report);
    persist();

    var query = phones.length ? TG.formatPhone(phones[0]) : (company || name);
    state.query = query;
    state.parsed = null;
    state.paste = "";
    state.reportPrefill = "";
    navigate("check");
    toast("已收录，风险档案已更新");
  }

  function bindLibrary() {
    var form = document.getElementById("library-form");
    if (form) {
      form.addEventListener("submit", function (event) {
        event.preventDefault();
        state.filters.keyword = document.getElementById("library-keyword").value.trim();
        state.filters.category = document.getElementById("library-category").value;
        state.filters.level = document.getElementById("library-level").value;
        render();
      });
    }
    var exportButton = document.querySelector('[data-action="export-contacts"]');
    if (exportButton) exportButton.addEventListener("click", exportContacts);
  }

  function bindSettings() {
    document.querySelectorAll('[data-action="export-backup"]').forEach(function (button) {
      button.addEventListener("click", exportBackup);
    });
    document.querySelectorAll('[data-action="export-all-csv"]').forEach(function (button) {
      button.addEventListener("click", exportAllCsv);
    });
    document.querySelectorAll('[data-action="clear-demo"]').forEach(function (button) {
      button.addEventListener("click", function () {
        if (!confirm("删除全部演示数据？真实上报的记录会保留。")) return;
        state.reports = state.reports.filter(function (report) { return report.source !== "demo"; });
        persist();
        render();
        toast("演示数据已删除");
      });
    });
    document.querySelectorAll('[data-action="reset-demo"]').forEach(function (button) {
      button.addEventListener("click", function () {
        if (!confirm("重新载入 9 条演示数据？不会删除你已有的真实记录。")) return;
        var existing = new Set(state.reports.map(function (report) { return report.id; }));
        window.TG_DEMO.forEach(function (demo) {
          if (!existing.has(demo.id)) state.reports.push(JSON.parse(JSON.stringify(demo)));
        });
        persist();
        render();
        toast("演示数据已载入");
      });
    });
    document.querySelectorAll('[data-action="clear-all"]').forEach(function (button) {
      button.addEventListener("click", function () {
        if (!confirm("清空所有记录？此操作不可撤销，建议先下载备份。")) return;
        state.reports = [];
        state.query = "";
        persist();
        render();
        toast("所有记录已清空");
      });
    });
    var importInput = document.getElementById("import-backup");
    if (importInput) importInput.addEventListener("change", async function () {
      var file = importInput.files && importInput.files[0];
      if (!file) return;
      try {
        var text = await file.text();
        var data = JSON.parse(text);
        var reports = Array.isArray(data) ? data : data.reports;
        if (!Array.isArray(reports)) throw new Error("bad format");
        if (!confirm("导入 " + reports.length + " 条记录？这会覆盖当前数据。")) return;
        state.reports = reports.map(sanitizeReport);
        persist();
        render();
        toast("已导入 " + state.reports.length + " 条记录");
      } catch (error) {
        alert("导入失败：文件不是合法的 TradeGuard JSON 备份。");
      }
    });
  }

  function sanitizeReport(raw) {
    var report = raw || {};
    var phones = Array.isArray(report.phones) ? report.phones.map(TG.normalizePhone).filter(Boolean) : [];
    var categories = Array.isArray(report.categories) ? report.categories.filter(function (key) { return !!CATS[key]; }) : [];
    return {
      id: Number(report.id) || nextId(),
      createdAt: report.createdAt || new Date().toISOString(),
      incidentDate: report.incidentDate || todayValue(),
      contactName: String(report.contactName || "").slice(0, 120),
      company: String(report.company || "").slice(0, 160),
      country: String(report.country || "").slice(0, 60),
      phones: phones,
      categories: categories.length ? categories : ["other"],
      amount: Number(report.amount) || 0,
      currency: String(report.currency || "USD").slice(0, 10),
      narrative: String(report.narrative || "").slice(0, 5000),
      evidence: String(report.evidence || "").slice(0, 5000),
      source: report.source === "demo" ? "demo" : report.source === "chat_import" ? "chat_import" : report.source === "csv_import" ? "csv_import" : "manual",
      chatFilename: report.chatFilename || "",
      chatSha: report.chatSha || "",
      chatMessageCount: Number(report.chatMessageCount) || 0,
      credibility: Math.max(0, Math.min(100, Number(report.credibility) || 60)),
      status: "approved"
    };
  }

  function exportBackup() {
    var payload = { version: 1, exportedAt: new Date().toISOString(), reports: state.reports };
    download("tradeguard-backup-" + todayValue() + ".json", JSON.stringify(payload, null, 2), "application/json");
    toast("备份已下载");
  }

  function exportAllCsv() {
    var rows = [["记录ID", "号码", "联系人", "公司", "国家", "类型", "金额", "币种", "发生日期", "经过", "证据", "来源", "可信度", "录入时间"]];
    state.reports.forEach(function (report) {
      rows.push([
        report.id,
        (report.phones || []).map(TG.formatPhone).join("；"),
        report.contactName,
        report.company,
        report.country,
        (report.categories || []).map(function (key) { return CATS[key] ? CATS[key].label : key; }).join("；"),
        report.amount || "",
        report.currency,
        report.incidentDate || "",
        report.narrative,
        report.evidence,
        report.source,
        report.credibility,
        report.createdAt
      ]);
    });
    download("tradeguard-reports-" + todayValue() + ".csv", "\ufeff" + toCsv(rows), "text/csv;charset=utf-8");
    toast("CSV 已下载");
  }

  function exportContacts() {
    var rows = [["号码", "联系人", "公司", "国家", "风险等级", "风险分", "举报数", "最近记录", "类型"]];
    var profiles = state.libraryProfiles || allProfiles();
    profiles.forEach(function (profile) {
      rows.push([
        profile.phone ? TG.formatPhone(profile.phone) : "",
        profile.contactName,
        profile.company,
        profile.country,
        profile.risk.label,
        profile.risk.score,
        profile.reportCount,
        profile.lastSeen,
        profile.categories.map(function (item) { return item.label; }).join("；")
      ]);
    });
    download("tradeguard-contacts-" + todayValue() + ".csv", "\ufeff" + toCsv(rows), "text/csv;charset=utf-8");
    toast("筛选结果已导出");
  }

  function toCsv(rows) {
    return rows.map(function (row) {
      return row.map(function (cell) {
        var text = String(cell == null ? "" : cell);
        if (/[",\n\r]/.test(text)) return '"' + text.replace(/"/g, '""') + '"';
        return text;
      }).join(",");
    }).join("\r\n");
  }

  function download(filename, content, mime) {
    var blob = new Blob([content], { type: mime });
    var url = URL.createObjectURL(blob);
    var link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  /* ------------------------------------------------------------ 渲染 */

  function renderSidebar() {
    var profiles = allProfiles();
    var high = profiles.filter(function (profile) { return profile.risk.level === "high"; }).length;
    document.getElementById("side-stats").innerHTML = '<div class="side-stat"><b>' + state.reports.length + "</b><span>条举报</span></div>"
      + '<div class="side-stat"><b>' + uniquePhones() + "</b><span>个号码</span></div>"
      + '<div class="side-stat"><b>' + high + "</b><span>高风险</span></div>";
    document.querySelectorAll("#nav button").forEach(function (button) {
      button.classList.toggle("active", button.getAttribute("data-view") === state.view);
    });
  }

  function render() {
    document.getElementById("view").innerHTML = (VIEWS[state.view] || viewCheck)();
    renderSidebar();
    bindView();
    window.scrollTo({ top: 0, behavior: "auto" });
  }

  function navigate(view) {
    if (!VIEWS[view]) return;
    state.view = view;
    try {
      if (location.hash !== "#" + view) history.replaceState(null, "", "#" + view);
    } catch (error) {
      /* file:// 下某些浏览器可能限制 history，忽略即可 */
    }
    render();
  }

  function init() {
    var saved = loadReports();
    if (saved === null) {
      state.reports = JSON.parse(JSON.stringify(window.TG_DEMO));
      persist();
    } else {
      state.reports = saved.map(sanitizeReport);
    }

    var hash = location.hash.replace("#", "");
    if (VIEWS[hash]) state.view = hash;

    var privacy = document.getElementById("privacy-toggle");
    privacy.checked = state.privacy;
    privacy.addEventListener("change", function () {
      state.privacy = privacy.checked;
      if (state.view === "library") render();
    });

    document.querySelectorAll("#nav button").forEach(function (button) {
      button.addEventListener("click", function () { navigate(button.getAttribute("data-view")); });
    });

    window.addEventListener("hashchange", function () {
      var target = location.hash.replace("#", "");
      if (VIEWS[target] && target !== state.view) {
        state.view = target;
        render();
      }
    });

    render();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
