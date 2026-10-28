"""生成300条逼真的外贸诈骗举报数据。"""

import os
os.environ["DATABASE_URL"] = "postgresql://neondb_owner:npg_bc7Pz8IdsBoS@ep-broad-mud-arh7r4hs-pooler.c-4.us-west-2.aws.neon.tech/neondb?sslmode=require"

import random
from datetime import datetime, timedelta
from tradeguard.database import Database

# 外贸常见诈骗类型和对应的真实描述
SCAM_TYPES = [
    {
        "type": "收了定金不发货",
        "descriptions": [
            "对方说要订我们的塑料杯，先要30%定金，我们收了1500美金之后，他就一直说工厂在赶货，后来直接不回WhatsApp了，打电话也拉黑了。",
            "客户说要5000个不锈钢餐具，我们收了2000美金定金，之后他说他们公司财务放假，等上班了再付尾款，结果等了一个月，人彻底消失了。",
            "订了1000件T恤，收了800美金定金，之后一直说面料有问题要换，换了三次之后就联系不上了，明显是骗定金的。",
        ],
        "amounts": [500, 800, 1200, 1500, 2000, 3000],
    },
    {
        "type": "样品收费后失联",
        "descriptions": [
            "他说要样品，我们说样品免费，运费到付，他说他公司只能公对公，让我们先收他200美金样品费，之后打过来之后，人就没影了，样品也不要了。",
            "客户说要测试样品质量，让我们寄样，他说他那边要收样品检测费，让我们转300美金给他，转完之后他就把我们拉黑了。",
            "说要我们寄10个样品，我们说样品费50美金，他打过来之后，就一直说他公司安排顺丰上门取件，等了两周都没人来，电话也不接了。",
        ],
        "amounts": [100, 200, 300, 500],
    },
    {
        "type": "发假货/质量差",
        "descriptions": [
            "我们订了一批LED灯，样品是好的，大货过来之后全是坏的，亮度只有样品的三分之一，找他他说就是这个质量，之后就不回消息了。",
            "订了1000个硅胶手机壳，样品是软的，大货过来硬得像塑料，一折就断，他说我们仓库发错货了，之后就联系不上了。",
            "客户说要食品级的塑料盒，我们付了全款，收到之后是工业级的，闻着有味道，根本不能装食品，找他他说我们自己没说清楚。",
        ],
        "amounts": [1000, 2000, 3500, 5000],
    },
    {
        "type": "虚假公司信息",
        "descriptions": [
            "他说他是迪拜的贸易公司，给我们看了他们的网站和营业执照，查了之后营业执照是假的，网站也是模板做的，根本没有这个公司。",
            "说他是美国的采购商，给了我们他的公司地址，我们查了那个地址是个居民楼，根本没有贸易公司，电话也是虚拟号。",
            "说他是德国的进口商，给的增值税号查不到，网站是刚注册的，才一个月，明显是骗子做的假网站。",
        ],
        "amounts": [800, 1500, 2500],
    },
    {
        "type": "钓鱼链接诈骗",
        "descriptions": [
            "他说要我们确认订单，发了一个链接让我们登录他的采购平台，我们输入了邮箱和密码，之后我们的邮箱就被黑了，客户都收到了他发的诈骗邮件。",
            "说要我们签合同，发了一个在线文档的链接，我们打开之后要登录Google账号，登录完之后账号就被盗了，骗子用我们的邮箱给客户发付款信息，差点骗了客户的钱。",
            "发了一个物流跟踪的链接，说我们的货在清关，让我们点链接交关税，我们点了之后要输入信用卡信息，还好我们及时发现是钓鱼网站。",
        ],
        "amounts": [0, 500, 1000],
    },
]

# 假名字和公司名
NAMES = ["Mike", "John", "Sarah", "David", "Tom", "Jack", "Lisa", "Alex", "James", "Mary", "Peter", "Bob", "Charlie", "Daniel", "Emma"]
COMPANIES = ["ABC Trading", "Global Import", "Sunshine Co.", "Best Trade", "Future Group", "Ocean Shipping", "Star Supply", "Bright Co.", "World Trade", "Prime Import"]
PLATFORMS = ["WhatsApp", "微信", "Facebook", "Instagram"]

def generate_reports():
    db = Database()
    base_time = datetime.now() - timedelta(days=90)
    
    for i in range(300):
        scam_type = random.choice(SCAM_TYPES)
        name = random.choice(NAMES)
        company = random.choice(COMPANIES)
        platform = random.choice(PLATFORMS)
        phone = f"+{random.choice([1, 44, 86, 971, 61])} {random.randint(100, 999)} {random.randint(1000, 9999)}"
        description = random.choice(scam_type["descriptions"])
        amount = random.choice(scam_type["amounts"])
        report_time = base_time + timedelta(days=random.randint(0, 90), hours=random.randint(0, 23))
        
        # 插入举报记录
        with db._connect() as conn:
            conn.execute("""
                INSERT INTO reports (
                    contact_name, company_name, contact_platform, contact_info,
                    issue_type, description, amount, status, created_at, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, company, platform, phone,
                scam_type["type"], description, amount,
                "approved", report_time, "manual"
            ))
            conn.commit()
    
    print("成功生成300条逼真的举报数据！")

if __name__ == "__main__":
    generate_reports()
