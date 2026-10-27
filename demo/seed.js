/* 演示数据：号码取自各国虚构/影视专用保留号段，公司与人名均为虚构。 */

window.TG_CATEGORIES = {
  free_samples: { label: "样品费未付", short: "样品费", severity: 26, desc: "以采购为名索要免费样品、样品费未付、收到样品后不再回复" },
  no_delivery: { label: "收款未发货", short: "未发货", severity: 30, desc: "收到货款/定金后未发货、失联、拉黑" },
  unpaid_balance: { label: "尾款未付", short: "尾款", severity: 20, desc: "收货后尾款未付、拒付、以质量问题为由压款" },
  quality: { label: "质量争议", short: "质量", severity: 16, desc: "以次充好、批次不合格、货不对板" },
  fake_inquiry: { label: "无效询盘", short: "询盘", severity: 10, desc: "反复索要报价/资料/规格，无真实采购意向" },
  fake_proof: { label: "付款凭证存疑", short: "凭证", severity: 28, desc: "伪造付款水单、钓鱼链接、冒充采购方或货代" },
  other: { label: "其他争议", short: "其他", severity: 6, desc: "其他交易争议，请在经过中说明" }
};

window.TG_LEVELS = {
  high: { label: "高风险", tone: "high", desc: "多条记录或严重类型 + 近期活跃" },
  medium: { label: "中风险", tone: "medium", desc: "存在明确投诉，建议分阶段付款" },
  low: { label: "低风险", tone: "low", desc: "有零散记录，先小额试单" },
  watch: { label: "关注", tone: "watch", desc: "记录较少或较旧，仅作线索" },
  unknown: { label: "无记录", tone: "unknown", desc: "库里没有记录，不等于对方可信" }
};

function tgDaysAgo(n) {
  var d = new Date();
  d.setHours(12, 0, 0, 0);
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

function tgCreatedAgo(n) {
  var d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString();
}

window.TG_DEMO = [
  {
    id: 1,
    createdAt: tgCreatedAgo(45),
    incidentDate: tgDaysAgo(46),
    contactName: "Mike R.",
    company: "NovaPeak Supplements LLC",
    country: "美国",
    phones: ["15550104477"],
    categories: ["free_samples", "fake_inquiry"],
    amount: 0,
    currency: "USD",
    narrative: "【演示数据】谈了 3 周，说先寄 2 公斤样品给美国客户测试。样品费和运费都不付，承诺下单后一起结算。样品签收后不再回复，换号继续加人。",
    evidence: "“Sample is for testing, you pay shipping first, we order 2 containers later.”（演示）",
    source: "demo",
    chatFilename: "demo-novapeak-1.txt",
    chatSha: "demo-hash-novapeak-1",
    chatMessageCount: 128,
    credibility: 72,
    status: "approved"
  },
  {
    id: 2,
    createdAt: tgCreatedAgo(19),
    incidentDate: tgDaysAgo(20),
    contactName: "Mike R.",
    company: "NovaPeak Supplements LLC",
    country: "美国",
    phones: ["15550104477"],
    categories: ["free_samples"],
    amount: 0,
    currency: "USD",
    narrative: "【演示数据】收到第一批免费样品后说“质量不达标”，要求再免费寄一批，仍然拒绝支付样品费，也不肯下正式订单。",
    evidence: "“Quality not good, send another batch free, then we decide.”（演示）",
    source: "demo",
    chatFilename: "demo-novapeak-2.txt",
    chatSha: "demo-hash-novapeak-2",
    chatMessageCount: 64,
    credibility: 68,
    status: "approved"
  },
  {
    id: 3,
    createdAt: tgCreatedAgo(3),
    incidentDate: tgDaysAgo(4),
    contactName: "Mike R.",
    company: "NovaPeak Supplements LLC",
    country: "美国",
    phones: ["15550104477"],
    categories: ["free_samples", "fake_inquiry"],
    amount: 0,
    currency: "USD",
    narrative: "【演示数据】同一个 Mike 用另一个号来加，话术和第一次一模一样：先免费寄样、再谈大货。同行提醒后才发现是同一伙人。",
    evidence: "“We are a big distributor, need free samples for our 20 clinics.”（演示）",
    source: "demo",
    chatFilename: "demo-novapeak-3.txt",
    chatSha: "demo-hash-novapeak-3",
    chatMessageCount: 43,
    credibility: 74,
    status: "approved"
  },
  {
    id: 4,
    createdAt: tgCreatedAgo(11),
    incidentDate: tgDaysAgo(12),
    contactName: "Daniel K.",
    company: "Summit Bio Labs Inc",
    country: "美国",
    phones: ["15550109922"],
    categories: ["no_delivery"],
    amount: 2800,
    currency: "USD",
    narrative: "【演示数据】支付 30% 定金 2,800 美元后，对方以“原料涨价”为由要求补款，补款后不发货，WhatsApp 拉黑，网站也打不开。",
    evidence: "“Our bank flagged the payment, please pay the balance first.”（演示）",
    source: "demo",
    chatFilename: "demo-summit.txt",
    chatSha: "demo-hash-summit",
    chatMessageCount: 96,
    credibility: 80,
    status: "approved"
  },
  {
    id: 5,
    createdAt: tgCreatedAgo(82),
    incidentDate: tgDaysAgo(83),
    contactName: "Sarah W.",
    company: "BrightLife Wholesale Ltd",
    country: "英国",
    phones: ["447700900123"],
    categories: ["quality"],
    amount: 1200,
    currency: "GBP",
    narrative: "【演示数据】500 支货，收到后近一半包装破损、批次不对，客户拒收。对方只愿意补 10%，拒绝退款，也不提供质检报告。",
    evidence: "“We can only offer 10% credit, no refund.”（演示）",
    source: "demo",
    chatFilename: "",
    chatSha: "",
    chatMessageCount: 0,
    credibility: 62,
    status: "approved"
  },
  {
    id: 6,
    createdAt: tgCreatedAgo(149),
    incidentDate: tgDaysAgo(150),
    contactName: "Liam T.",
    company: "AussieFit Distribution Pty Ltd",
    country: "澳大利亚",
    phones: ["61491570006"],
    categories: ["unpaid_balance"],
    amount: 3400,
    currency: "AUD",
    narrative: "【演示数据】首批货已签收，尾款 3,400 澳元拖了 60 多天。每次都说“下周付”，后来只读不回。",
    evidence: "“Next week for sure, our accountant is away.”（演示）",
    source: "demo",
    chatFilename: "",
    chatSha: "",
    chatMessageCount: 0,
    credibility: 66,
    status: "approved"
  },
  {
    id: 7,
    createdAt: tgCreatedAgo(30),
    incidentDate: tgDaysAgo(31),
    contactName: "James P.",
    company: "PureForm Trading Co",
    country: "英国",
    phones: ["447700900456"],
    categories: ["fake_proof"],
    amount: 4600,
    currency: "GBP",
    narrative: "【演示数据】发来一张银行水单截图要求先放货，核对后发现付款人、金额、SWIFT 号都对不上，是 P 的图。被追问后立刻删消息。",
    evidence: "“Payment done, see attached slip, release goods today.”（演示）",
    source: "demo",
    chatFilename: "demo-pureform.txt",
    chatSha: "demo-hash-pureform",
    chatMessageCount: 37,
    credibility: 78,
    status: "approved"
  },
  {
    id: 8,
    createdAt: tgCreatedAgo(204),
    incidentDate: tgDaysAgo(205),
    contactName: "Chris M.",
    company: "OceanBridge Sourcing",
    country: "美国",
    phones: ["15550101188"],
    categories: ["fake_inquiry"],
    amount: 0,
    currency: "USD",
    narrative: "【演示数据】连续三周索要完整报价表、COA、MSDS 和包装设计稿，说要给连锁客户提案。资料给完后消失，换号再来问同样的问题。",
    evidence: "“Send full spec and price list first, we will confirm this week.”（演示）",
    source: "demo",
    chatFilename: "",
    chatSha: "",
    chatMessageCount: 0,
    credibility: 58,
    status: "approved"
  },
  {
    id: 9,
    createdAt: tgCreatedAgo(5),
    incidentDate: tgDaysAgo(6),
    contactName: "Alex D.",
    company: "GreenLeaf Nutra",
    country: "美国",
    phones: ["15550106655"],
    categories: ["no_delivery", "fake_proof"],
    amount: 5000,
    currency: "USD",
    narrative: "【演示数据】付了 5,000 美元货款，对方先发假水单拖延，随后以“海关扣货”为由要求再付清关费。拒绝后彻底失联。",
    evidence: "“Customs need extra 1,200 USD, pay now or goods returned.”（演示）",
    source: "demo",
    chatFilename: "demo-greenleaf.txt",
    chatSha: "demo-hash-greenleaf",
    chatMessageCount: 152,
    credibility: 82,
    status: "approved"
  }
];
