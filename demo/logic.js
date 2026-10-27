/* 核心逻辑：号码归一、风险评分、查询聚合、WhatsApp 解析。 */
(function () {
  "use strict";

  var CATS = window.TG_CATEGORIES;

  function digitsOnly(value) {
    return String(value == null ? "" : value).replace(/\D/g, "");
  }

  function normalizePhone(raw) {
    var text = String(raw == null ? "" : raw).trim();
    if (!text) return null;
    var digits = digitsOnly(text);
    if (!digits) return null;
    if (text.indexOf("00") === 0 && digits.length > 8) digits = digits.slice(2);
    if (digits.length < 8 || digits.length > 15) return null;
    if (new Set(digits).size === 1) return null;
    if (/^(?:19|20)\d{6}$/.test(digits)) return null;
    return digits;
  }

  function phoneVariants(raw) {
    var text = String(raw == null ? "" : raw).trim();
    var digits = digitsOnly(text);
    if (!digits) return [];
    if (text.indexOf("00") === 0 && digits.length > 8) digits = digits.slice(2);
    if (text.charAt(0) === "+" || text.indexOf("00") === 0) {
      return digits.length >= 8 && digits.length <= 15 ? [digits] : [];
    }
    var out = [];
    function add(value) {
      if (value && value.length >= 8 && value.length <= 15 && out.indexOf(value) === -1) out.push(value);
    }
    add(digits);
    if (digits.length === 11 && digits.charAt(0) === "1") add("86" + digits);
    if (digits.length === 10) add("1" + digits);
    if (digits.charAt(0) === "0" && digits.length >= 10) add(digits.slice(1));
    if (digits.charAt(0) === "0" && digits.length >= 11) add("86" + digits.slice(1));
    return out;
  }

  function formatPhone(norm) {
    return norm ? "+" + norm : "—";
  }

  function maskPhone(norm) {
    if (!norm) return "—";
    if (norm.length <= 8) return "+" + norm.slice(0, 2) + "***" + norm.slice(-2);
    var country = norm.charAt(0) === "1" && norm.length === 11 ? "1" : norm.slice(0, 2);
    var rest = norm.slice(country.length);
    if (rest.length >= 7) return "+" + country + " " + rest.slice(0, 3) + "***" + rest.slice(-4);
    return "+" + norm.slice(0, 3) + "***" + norm.slice(-3);
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (char) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char];
    });
  }

  function parseDate(value) {
    if (!value) return null;
    var text = String(value).slice(0, 10);
    var parts = text.split("-");
    if (parts.length !== 3) return null;
    var date = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]), 12, 0, 0);
    return isNaN(date.getTime()) ? null : date;
  }

  function daysSince(value) {
    var date = parseDate(value);
    if (!date) return null;
    return Math.floor((Date.now() - date.getTime()) / 86400000);
  }

  function agoLabel(value) {
    var days = daysSince(value);
    if (days === null) return "未知";
    if (days <= 0) return "今天";
    if (days === 1) return "昨天";
    if (days < 30) return days + " 天前";
    if (days < 365) return Math.floor(days / 30) + " 个月前";
    return Math.floor(days / 365) + " 年前";
  }

  function assess(reports) {
    if (!reports || !reports.length) {
      return {
        score: 0,
        level: "unknown",
        label: "无记录",
        tone: "unknown",
        reasons: ["本地库中暂无该对象的举报记录"]
      };
    }
    var count = reports.length;
    var categories = new Set();
    reports.forEach(function (report) {
      (report.categories || []).forEach(function (key) {
        if (CATS[key]) categories.add(key);
      });
    });
    var severity = 6;
    categories.forEach(function (key) {
      severity = Math.max(severity, CATS[key].severity || 6);
    });

    var base = Math.min(40, 16 + 8 * count);
    var score = base + severity;

    var latest = null;
    reports.forEach(function (report) {
      var date = parseDate(report.incidentDate) || parseDate(report.createdAt);
      if (date && (!latest || date > latest)) latest = date;
    });
    var recency = 0;
    if (latest) {
      var age = Math.floor((Date.now() - latest.getTime()) / 86400000);
      if (age <= 90) recency = 12;
      else if (age <= 365) recency = 6;
    }
    score += recency;

    var hasChat = reports.some(function (report) { return !!report.chatSha; });
    if (hasChat) score += 8;

    var totalAmount = 0;
    reports.forEach(function (report) {
      var amount = Number(report.amount) || 0;
      if (amount > 0) totalAmount += amount;
    });
    if (totalAmount >= 5000) score += 8;
    else if (totalAmount >= 1000) score += 5;
    else if (totalAmount > 0) score += 2;

    var credibility = reports.reduce(function (sum, report) {
      return sum + (Number(report.credibility) || 60);
    }, 0) / count;
    score += Math.max(-3, Math.min(3, Math.round((credibility - 60) / 10)));

    if (count <= 1) {
      score = Math.min(score, hasChat && credibility >= 70 ? 55 : 39);
    }
    score = Math.max(0, Math.min(100, score));

    var level = score >= 70 ? "high" : score >= 45 ? "medium" : score >= 20 ? "low" : "watch";
    var levelInfo = window.TG_LEVELS[level];

    var reasons = [];
    if (count >= 2) reasons.push("被 " + count + " 条独立记录举报");
    else reasons.push("仅 1 条记录，尚未交叉验证");
    if (categories.size) {
      var labels = Array.from(categories)
        .sort(function (a, b) { return CATS[b].severity - CATS[a].severity; })
        .map(function (key) { return CATS[key].label; });
      reasons.push("涉及类型：" + labels.join("、"));
    }
    if (recency >= 12) reasons.push("最近 90 天内仍有新记录");
    else if (recency) reasons.push("近一年内有记录");
    if (hasChat) reasons.push("附带聊天记录佐证");
    if (totalAmount > 0) reasons.push("记录涉及金额合计约 " + totalAmount.toLocaleString("en-US") + "（未折算币种）");
    if (count >= 3 && credibility >= 70) reasons.push("多条记录的可信度较高");

    return { score: score, level: level, label: levelInfo.label, tone: levelInfo.tone, reasons: reasons };
  }

  function countValues(items, picker) {
    var map = new Map();
    items.forEach(function (item) {
      var value = picker(item);
      if (value) map.set(value, (map.get(value) || 0) + 1);
    });
    return map;
  }

  function bestValue(map) {
    var best = "";
    var bestCount = 0;
    map.forEach(function (count, value) {
      if (count > bestCount) { best = value; bestCount = count; }
    });
    return best;
  }

  function buildProfile(phone, reports, matchReason, matchKind, exact) {
    var risk = assess(reports);
    var names = countValues(reports, function (report) { return report.contactName; });
    var companies = countValues(reports, function (report) { return report.company; });
    var countries = countValues(reports, function (report) { return report.country; });
    var categoryCounts = new Map();
    reports.forEach(function (report) {
      (report.categories || []).forEach(function (key) {
        categoryCounts.set(key, (categoryCounts.get(key) || 0) + 1);
      });
    });
    var dates = reports.map(function (report) {
      return report.incidentDate || String(report.createdAt || "").slice(0, 10);
    }).filter(Boolean).sort();

    var contactName = bestValue(names);
    var company = bestValue(companies);
    var displayPhone = phone ? formatPhone(phone) : "";
    var displayName = contactName || company || (phone ? maskPhone(phone) : "未知联系人");
    var amountTotal = reports.reduce(function (sum, report) { return sum + (Number(report.amount) || 0); }, 0);
    var currencies = Array.from(new Set(reports.filter(function (report) { return Number(report.amount) > 0; })
      .map(function (report) { return report.currency || "USD"; })));

    return {
      phone: phone || "",
      displayPhone: displayPhone,
      maskedPhone: phone ? maskPhone(phone) : "",
      displayName: displayName,
      contactName: contactName,
      company: company,
      country: bestValue(countries),
      reportCount: reports.length,
      risk: risk,
      categories: Array.from(categoryCounts.entries())
        .sort(function (a, b) { return b[1] - a[1]; })
        .map(function (entry) {
          return { key: entry[0], label: CATS[entry[0]] ? CATS[entry[0]].label : entry[0], count: entry[1] };
        }),
      firstSeen: dates[0] || "",
      lastSeen: dates[dates.length - 1] || "",
      amountTotal: amountTotal,
      currencies: currencies,
      reports: reports.slice().sort(function (a, b) {
        return String(b.incidentDate || b.createdAt).localeCompare(String(a.incidentDate || a.createdAt));
      }),
      hasDemo: reports.some(function (report) { return report.source === "demo"; }),
      matchReason: matchReason || "",
      matchKind: matchKind || "text",
      exact: !!exact
    };
  }

  function searchReports(reports, query) {
    var q = String(query == null ? "" : query).trim();
    var result = { query: q, profiles: [], textReports: [], notes: [], phoneInput: null };
    if (!q) return result;

    var digits = digitsOnly(q);
    var profiles = new Map();
    var exact = new Set();

    if (digits.length >= 7 && digits.length <= 15) {
      result.phoneInput = digits;
      phoneVariants(q).forEach(function (variant) {
        reports.forEach(function (report) {
          if ((report.phones || []).indexOf(variant) !== -1) exact.add(variant);
        });
      });

      exact.forEach(function (phone) {
        var matched = reports.filter(function (report) { return (report.phones || []).indexOf(phone) !== -1; });
        if (matched.length) profiles.set(phone, buildProfile(phone, matched, "号码完全匹配", "phone_exact", true));
      });

      if (!exact.size) {
        var suffix = digits.slice(-8);
        reports.forEach(function (report) {
          (report.phones || []).forEach(function (phone) {
            if (profiles.has(phone)) return;
            if (digits.length >= 8 && phone.slice(-8) === suffix) {
              var matched = reports.filter(function (item) { return (item.phones || []).indexOf(phone) !== -1; });
              profiles.set(phone, buildProfile(phone, matched, "号码尾号匹配（可能是同一人换号）", "phone_suffix", false));
            }
          });
        });
      } else if (digits.length < 8) {
        result.notes.push("至少输入 7 位数字，才能做尾号匹配。");
      }
    } else if (digits.length > 0 && digits.length < 7) {
      result.notes.push("号码位数太少，请输入完整号码或至少 7 位数字。");
    }

    var lower = q.toLowerCase();
    var textMatched = reports.filter(function (report) {
      var haystack = ((report.company || "") + " " + (report.contactName || "") + " " + (report.narrative || "")).toLowerCase();
      return haystack.indexOf(lower) !== -1;
    });

    textMatched.forEach(function (report) {
      var phone = (report.phones || [])[0];
      if (phone && !profiles.has(phone)) {
        var matched = reports.filter(function (item) { return (item.phones || []).indexOf(phone) !== -1; });
        profiles.set(phone, buildProfile(phone, matched, "公司 / 联系人名称匹配", "text", false));
      }
      if (!phone) result.textReports.push(report);
    });

    var list = Array.from(profiles.values());
    list.sort(function (a, b) {
      if (a.exact !== b.exact) return a.exact ? -1 : 1;
      if (b.risk.score !== a.risk.score) return b.risk.score - a.risk.score;
      return String(b.lastSeen).localeCompare(String(a.lastSeen));
    });
    result.profiles = list.slice(0, 10);
    result.textReports = result.textReports.slice(0, 10);
    return result;
  }

  /* ------------------------------------------------------------ WhatsApp 解析 */

  var IOS_RE = /^\[(\d{1,4}[./-]\d{1,2}[./-]\d{1,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?)\s*([APap]\.?\s?[Mm]\.?)?\]\s*([^:\n]{1,80}?):\s?(.*)$/;
  var ANDROID_RE = /^(\d{1,4}[./-]\d{1,2}[./-]\d{1,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?)\s*([APap]\.?\s?[Mm]\.?)?\s+[-\u2013\u2014~]\s+([^:\n]{1,80}?):\s?(.*)$/;
  var SYSTEM_RE = /(end-to-end encrypted|messages to this chat and calls are now secured|changed the group|created group|joined using this group|added you|security code changed|changed their phone number|this message was deleted|已删除此消息|你加入了|加入了群组|创建了群组|更改了(群组|群聊)|安全码已更改|更改了手机号码|退出了群组|被移出|消息和通话已进行端到端加密)/i;
  var PHONE_RE = /(?<![\d])(?:\+|00)?\d(?:[\d\s().-]{6,18}\d)(?![\d])/g;
  var DATE_TEXT_RE = /^\d{1,4}[./-]\d{1,2}[./-]\d{1,4}$/;
  var MEDIA_RE = /(<Media omitted>|\b(?:image|video|audio|sticker|GIF|document|Contact card) omitted\b|\(文件已删除\)|已删除消息|媒体文件缺失)/gi;
  var URL_RE = /https?:\/\/\S+/gi;
  var EMAIL_RE = /[\w.+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)/g;
  var MONEY_RE = /(?:(?:USD|US\$|CNY|RMB|EUR|GBP|AUD|HKD|\$|¥|€|£)\s?\d[\d,]*(?:\.\d{1,2})?)|(?:\d[\d,]*(?:\.\d{1,2})?\s?(?:USD|US\$|CNY|RMB|EUR|GBP|AUD|HKD|dollars?|yuan))/gi;

  var FREE_MAIL = ["gmail.com", "googlemail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com", "aol.com", "icloud.com", "qq.com", "163.com", "126.com", "protonmail.com", "proton.me", "mail.ru", "yandex.com"];

  var SIGNALS = [
    { key: "free_sample", label: "免费样品", needles: ["免费样品", "免费拿样", "样品免费", "样品费免", "不付样品费", "白嫖", "free sample", "sample for free", "no sample fee", "free of charge"] },
    { key: "payment_proof", label: "付款 / 水单", needles: ["水单", "付款凭证", "转账截图", "汇款凭证", "银行回单", "bank slip", "swift copy", "payment proof", "payment screenshot", "western union", "usdt", "加密货币"] },
    { key: "no_delivery", label: "不发货 / 失联", needles: ["不发货", "没发货", "未发货", "失联", "拉黑", "跑路", "人间蒸发", "ghosted", "never shipped", "no delivery", "stopped replying", "blocked me"] },
    { key: "unpaid", label: "拖欠 / 不付款", needles: ["尾款", "拖欠", "不付款", "没付款", "未付款", "拒付", "unpaid", "balance due", "not paid", "refuse to pay"] },
    { key: "quality", label: "质量问题", needles: ["质量问题", "劣质", "假货", "不合格", "以次充好", "货不对板", "defective", "poor quality", "fake product", "counterfeit", "not as described"] },
    { key: "phishing", label: "链接 / 钓鱼", needles: ["钓鱼", "验证码", "verify your account", "click here", "login to confirm", "account suspended"] },
    { key: "urgency", label: "催促施压", needles: ["urgent", "asap", "今天必须", "马上", "立刻", "最后期限", "last chance"] }
  ];

  function parseTimestamp(datePart, timePart, ampm) {
    var dm = String(datePart).match(/^(\d{1,4})[./-](\d{1,2})[./-](\d{1,4})$/);
    var tm = String(timePart).match(/^(\d{1,2}):(\d{2})(?::(\d{2}))?$/);
    if (!dm || !tm) return null;
    var a = Number(dm[1]), b = Number(dm[2]), c = Number(dm[3]);
    var year, month, day;
    if (a > 31) { year = a; month = b; day = c; }
    else { day = a; month = b; year = c; if (year < 100) year += 2000; }
    var hour = Number(tm[1]), minute = Number(tm[2]), second = Number(tm[3] || 0);
    if (ampm) {
      var marker = String(ampm).toLowerCase().replace(/\./g, "").replace(/\s/g, "");
      if (marker.charAt(0) === "p" && hour < 12) hour += 12;
      if (marker.charAt(0) === "a" && hour === 12) hour = 0;
    }
    try {
      return new Date(year, month - 1, day, hour, minute, second);
    } catch (error) {
      return null;
    }
  }

  function isSystem(sender, text) {
    var name = String(sender || "").trim().toLowerCase();
    if (name === "system" || name === "系统" || name === "system message") return true;
    return !!SYSTEM_RE.test(String(text || "").slice(0, 300));
  }

  function looksLikeAmount(raw) {
    return /^\d{1,3}(?:[,\s]\d{3})+(?:\.\d{1,2})?$/.test(String(raw).trim());
  }

  function phoneConfidence(raw, digits) {
    if (/^\+/.test(raw) || /^00/.test(raw)) return "high";
    if (digits.length === 13 && digits.indexOf("86") === 0 && digits.charAt(2) === "1" && "3456789".indexOf(digits.charAt(3)) !== -1) return "high";
    if (digits.length === 11 && digits.charAt(0) === "1" && "3456789".indexOf(digits.charAt(1)) !== -1) return "high";
    if (digits.length === 10 && "23456789".indexOf(digits.charAt(0)) !== -1) return "medium";
    if (/[\s().-]/.test(raw)) return "medium";
    return "low";
  }

  function phoneCandidates(text) {
    var found = [];
    var match;
    PHONE_RE.lastIndex = 0;
    while ((match = PHONE_RE.exec(text)) !== null) {
      var raw = match[0].trim();
      if (!raw || DATE_TEXT_RE.test(raw) || looksLikeAmount(raw)) continue;
      var digits = digitsOnly(raw);
      if (digits.length < 8 || digits.length > 15) continue;
      if (new Set(digits).size === 1) continue;
      if (/^(?:19|20)\d{6}$/.test(digits)) continue;
      var prefix = /^\+/.test(raw) || /^00/.test(raw);
      var separator = /[\s().-]/.test(raw);
      if (!prefix && !separator && digits.length < 10) continue;
      var norm = normalizePhone(raw);
      if (!norm) continue;
      found.push({ raw: raw, norm: norm, confidence: phoneConfidence(raw, digits) });
    }
    return found;
  }

  function simpleHash(text) {
    var hash = 2166136261;
    for (var index = 0; index < text.length; index += 1) {
      hash ^= text.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0).toString(16);
  }

  async function sha256(text) {
    try {
      if (window.crypto && window.crypto.subtle) {
        var buffer = await window.crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
        return Array.from(new Uint8Array(buffer)).map(function (byte) {
          return byte.toString(16).padStart(2, "0");
        }).join("");
      }
    } catch (error) {
      /* file:// 或旧浏览器下回退到本地哈希 */
    }
    return "local-" + simpleHash(text);
  }

  async function parseChat(rawText, filename) {
    var warnings = [];
    var text = String(rawText == null ? "" : rawText);
    if (!text.trim()) {
      return {
        filename: filename || "粘贴内容.txt", messageCount: 0, participantCount: 0,
        senders: [], phones: [], signals: [], firstTs: null, lastTs: null,
        dateRange: "未识别", warnings: ["没有读取到聊天内容。"], mediaCount: 0,
        urlCount: 0, moneyMentions: [], companyHints: [], sha256: "", messages: []
      };
    }
    text = text.replace(/\u202f/g, " ").replace(/\u200e/g, "").replace(/\u200f/g, "").replace(/\xa0/g, " ");

    var messages = [];
    var lines = text.split(/\r?\n/);
    lines.forEach(function (line) {
      if (!line.trim()) return;
      var match = line.match(IOS_RE) || line.match(ANDROID_RE);
      if (match) {
        var timestamp = parseTimestamp(match[1], match[2], match[3]);
        var sender = String(match[4] || "").trim().replace(/^"|"$/g, "").slice(0, 80);
        messages.push({ timestamp: timestamp, sender: sender, text: match[5] || "", isSystem: isSystem(sender, match[5] || "") });
      } else if (messages.length && !messages[messages.length - 1].isSystem) {
        if (!SYSTEM_RE.test(line)) {
          messages[messages.length - 1].text += "\n" + line;
        }
      }
    });

    if (!messages.length) warnings.push("没有识别到 WhatsApp 聊天格式。请确认上传的是导出的 .txt，或直接粘贴关键对话。");

    var senders = new Map();
    var phones = new Map();
    var signalTexts = [];
    messages.forEach(function (message) {
      if (message.isSystem) return;
      senders.set(message.sender, (senders.get(message.sender) || 0) + 1);
      signalTexts.push(message.text);
      [message.sender, message.text].forEach(function (source) {
        phoneCandidates(source).forEach(function (candidate) {
          var entry = phones.get(candidate.norm) || { norm: candidate.norm, mentions: 0, sample: candidate.raw, confidence: "low" };
          entry.mentions += 1;
          var rank = { low: 0, medium: 1, high: 2 };
          if (rank[candidate.confidence] > rank[entry.confidence]) entry.confidence = candidate.confidence;
          phones.set(candidate.norm, entry);
        });
      });
    });

    var allText = signalTexts.join("\n");
    var signals = [];
    SIGNALS.forEach(function (definition) {
      var hits = 0;
      var samples = [];
      signalTexts.forEach(function (messageText) {
        var low = messageText.toLowerCase();
        var matched = definition.needles.some(function (needle) {
          return low.indexOf(needle.toLowerCase()) !== -1;
        });
        if (matched) {
          hits += 1;
          if (samples.length < 2) samples.push(messageText.replace(/\s+/g, " ").slice(0, 120));
        }
      });
      if (hits) signals.push({ key: definition.key, label: definition.label, hits: hits, samples: samples });
    });
    signals.sort(function (a, b) { return b.hits - a.hits; });

    var mediaCount = (allText.match(MEDIA_RE) || []).length;
    var urlCount = (allText.match(URL_RE) || []).length;
    var moneyMentions = [];
    var moneyMatch;
    MONEY_RE.lastIndex = 0;
    while ((moneyMatch = MONEY_RE.exec(allText)) !== null) {
      if (moneyMentions.indexOf(moneyMatch[0].trim()) === -1) moneyMentions.push(moneyMatch[0].trim());
    }

    var domains = new Map();
    var emailMatch;
    EMAIL_RE.lastIndex = 0;
    while ((emailMatch = EMAIL_RE.exec(allText)) !== null) {
      var domain = emailMatch[1].toLowerCase();
      if (FREE_MAIL.indexOf(domain) === -1) domains.set(domain, (domains.get(domain) || 0) + 1);
    }
    var companyHints = Array.from(domains.keys()).slice(0, 3).map(function (domain) {
      return domain.split(".")[0].replace(/-/g, " ").replace(/\b\w/g, function (char) { return char.toUpperCase(); });
    });

    var timestamps = messages.map(function (message) { return message.timestamp; }).filter(Boolean);
    var firstTs = timestamps.length ? new Date(Math.min.apply(null, timestamps)) : null;
    var lastTs = timestamps.length ? new Date(Math.max.apply(null, timestamps)) : null;
    var phoneList = Array.from(phones.values()).sort(function (a, b) {
      var rank = { low: 0, medium: 1, high: 2 };
      if (rank[b.confidence] !== rank[a.confidence]) return rank[b.confidence] - rank[a.confidence];
      return b.mentions - a.mentions;
    }).slice(0, 10);

    var mapping = { free_sample: "free_samples", no_delivery: "no_delivery", unpaid: "unpaid_balance", quality: "quality", payment_proof: "fake_proof", phishing: "fake_proof" };
    var primaryCategories = [];
    signals.forEach(function (signal) {
      if (mapping[signal.key] && primaryCategories.indexOf(mapping[signal.key]) === -1) primaryCategories.push(mapping[signal.key]);
    });
    if (!primaryCategories.length) primaryCategories.push("fake_inquiry");

    var evidenceHint = signals.filter(function (signal) { return signal.samples.length; }).slice(0, 3)
      .map(function (signal) { return "[" + signal.label + "] " + signal.samples[0]; }).join("\n");

    var dateRange = "未识别";
    if (firstTs && lastTs) {
      var fmt = function (date) {
        return date.getFullYear() + "-" + String(date.getMonth() + 1).padStart(2, "0") + "-" + String(date.getDate()).padStart(2, "0");
      };
      dateRange = fmt(firstTs) === fmt(lastTs) ? fmt(firstTs) : fmt(firstTs) + " → " + fmt(lastTs);
    }

    return {
      filename: filename || "粘贴内容.txt",
      messageCount: messages.filter(function (message) { return !message.isSystem; }).length,
      participantCount: senders.size,
      senders: Array.from(senders.entries()).sort(function (a, b) { return b[1] - a[1]; }).slice(0, 10),
      phones: phoneList,
      signals: signals,
      firstTs: firstTs,
      lastTs: lastTs,
      dateRange: dateRange,
      warnings: warnings,
      mediaCount: mediaCount,
      urlCount: urlCount,
      moneyMentions: moneyMentions.slice(0, 12),
      companyHints: companyHints,
      primaryCategories: primaryCategories,
      sha256: await sha256(text),
      messages: messages
    };
  }

  function evidenceHint(parsed) {
    if (!parsed) return "";
    return parsed.signals.filter(function (signal) { return signal.samples.length; }).slice(0, 3)
      .map(function (signal) { return "[" + signal.label + "] " + signal.samples[0]; }).join("\n");
  }

  window.TG = {
    digitsOnly: digitsOnly,
    normalizePhone: normalizePhone,
    phoneVariants: phoneVariants,
    formatPhone: formatPhone,
    maskPhone: maskPhone,
    escapeHtml: escapeHtml,
    assess: assess,
    buildProfile: buildProfile,
    searchReports: searchReports,
    parseChat: parseChat,
    evidenceHint: evidenceHint,
    agoLabel: agoLabel,
    parseDate: parseDate,
    daysSince: daysSince
  };
})();
