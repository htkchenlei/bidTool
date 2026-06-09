"""
区域查询 — 按地区查询招标信息
提供省份/城市筛选、关键词搜索、招标详情查看
"""
import json
import os
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify

region_bp = Blueprint("region", __name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
BIDDING_FILE = os.path.join(DATA_DIR, "bidding.json")

# ── 中国省份城市数据（简化版）────────────────────────────────
CHINA_REGIONS = {
    "北京市": ["东城区", "西城区", "朝阳区", "海淀区", "丰台区", "石景山区", "通州区", "大兴区", "顺义区", "昌平区"],
    "上海市": ["黄浦区", "徐汇区", "长宁区", "静安区", "普陀区", "虹口区", "杨浦区", "浦东新区", "闵行区", "宝山区"],
    "广东省": ["广州市", "深圳市", "珠海市", "东莞市", "佛山市", "中山市", "惠州市", "汕头市", "江门市", "湛江市"],
    "浙江省": ["杭州市", "宁波市", "温州市", "嘉兴市", "湖州市", "绍兴市", "金华市", "衢州市", "舟山市", "台州市"],
    "江苏省": ["南京市", "无锡市", "徐州市", "常州市", "苏州市", "南通市", "连云港市", "淮安市", "盐城市", "扬州市"],
    "四川省": ["成都市", "绵阳市", "德阳市", "宜宾市", "南充市", "泸州市", "达州市", "乐山市", "凉山州", "眉山市"],
    "湖北省": ["武汉市", "黄石市", "十堰市", "宜昌市", "襄阳市", "鄂州市", "荆门市", "孝感市", "荆州市", "黄冈市"],
    "山东省": ["济南市", "青岛市", "淄博市", "枣庄市", "东营市", "烟台市", "潍坊市", "济宁市", "泰安市", "威海市"],
    "河南省": ["郑州市", "开封市", "洛阳市", "平顶山市", "安阳市", "鹤壁市", "新乡市", "焦作市", "濮阳市", "许昌市"],
    "福建省": ["福州市", "厦门市", "莆田市", "三明市", "泉州市", "漳州市", "南平市", "龙岩市", "宁德市"],
    "湖南省": ["长沙市", "株洲市", "湘潭市", "衡阳市", "邵阳市", "岳阳市", "常德市", "张家界市", "益阳市", "郴州市"],
    "安徽省": ["合肥市", "芜湖市", "蚌埠市", "淮南市", "马鞍山市", "淮北市", "铜陵市", "安庆市", "黄山市", "滁州市"],
    "河北省": ["石家庄市", "唐山市", "秦皇岛市", "邯郸市", "邢台市", "保定市", "张家口市", "承德市", "沧州市", "廊坊市"],
    "辽宁省": ["沈阳市", "大连市", "鞍山市", "抚顺市", "本溪市", "丹东市", "锦州市", "营口市", "阜新市", "辽阳市"],
    "陕西省": ["西安市", "铜川市", "宝鸡市", "咸阳市", "渭南市", "延安市", "汉中市", "榆林市", "安康市", "商洛市"],
    "重庆市": ["渝中区", "江北区", "南岸区", "沙坪坝区", "九龙坡区", "大渡口区", "北碚区", "渝北区", "巴南区", "涪陵区"],
}

# ── 招标项目分类 ──────────────────────────────────────────
BID_CATEGORIES = ["工程建设", "IT 服务", "咨询服务", "物资采购", "设备采购", "物业服务", "设计服务", "监理服务"]

# ── 生成模拟招标数据 ─────────────────────────────────────
def generate_mock_bidding():
    """首次运行或数据为空时生成模拟招标数据"""
    now = datetime.now()
    data = []
    idx = 1

    templates = [
        {
            "title_tpl": "{city}市{dept}{project_type}项目",
            "agency_tpl": "{city}市公共资源交易中心",
            "category": "工程建设",
            "budget_range": (100, 5000),
        },
        {
            "title_tpl": "{dept}{year}年度{project_type}采购",
            "agency_tpl": "{province}省政府采购中心",
            "category": "物资采购",
            "budget_range": (20, 800),
        },
        {
            "title_tpl": "{dept}信息化{project_type}项目招标",
            "agency_tpl": "{city}招标代理有限公司",
            "category": "IT 服务",
            "budget_range": (50, 2000),
        },
        {
            "title_tpl": "{dept}{project_type}咨询服务",
            "agency_tpl": "{city}市公共资源交易中心",
            "category": "咨询服务",
            "budget_range": (10, 300),
        },
        {
            "title_tpl": "{city}{dept}{project_type}设备采购及安装",
            "agency_tpl": "{city}市公共资源交易中心",
            "category": "设备采购",
            "budget_range": (30, 1500),
        },
        {
            "title_tpl": "{dept}{project_type}项目",
            "agency_tpl": "{city}工程咨询有限公司",
            "category": "工程建设",
            "budget_range": (200, 8000),
        },
    ]

    depts = ["市政", "交通", "教育", "医疗", "水利", "环保", "公安", "消防", "园林", "体育"]
    project_types = ["建设", "改造", "升级", "扩建", "维修", "翻新"]

    import random

    for province, cities in CHINA_REGIONS.items():
        for city in cities[:4]:  # 每个省份只取前4个城市
            for _ in range(2):  # 每个城市生成2条
                tpl = random.choice(templates)
                dept = random.choice(depts)
                ptype = random.choice(project_types)
                year = now.year

                title = tpl["title_tpl"].format(
                    city=city, province=province,
                    dept=dept, project_type=ptype, year=year
                )
                budget_min, budget_max = tpl["budget_range"]
                budget_low = random.randint(budget_min, budget_max // 2)
                budget_high = random.randint(budget_low + 10, budget_max)

                publish_days = random.randint(1, 60)
                deadline_days = random.randint(7, 60)
                publish_date = now - timedelta(days=publish_days)
                deadline = now + timedelta(days=deadline_days)

                # 随机状态
                if deadline_days < 0:
                    status = "已截止"
                elif random.random() < 0.15:
                    status = "已中标"
                else:
                    status = "招标中"

                data.append({
                    "id": f"bid_{idx:04d}",
                    "title": title,
                    "region_province": province,
                    "region_city": city,
                    "agency": tpl["agency_tpl"].format(city=city, province=province),
                    "category": tpl["category"],
                    "publish_date": publish_date.strftime("%Y-%m-%d"),
                    "deadline": deadline.strftime("%Y-%m-%d"),
                    "budget_min": budget_low,
                    "budget_max": budget_high,
                    "budget_unit": "万元",
                    "status": status,
                    "contact": f"{dept}局招标办",
                    "phone": f"010-{random.randint(10000000, 99999999)}",
                })
                idx += 1

    return data


def load_bidding():
    """加载招标数据，不存在则生成模拟数据"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(BIDDING_FILE):
        data = generate_mock_bidding()
        with open(BIDDING_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data
    with open(BIDDING_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ── API 端点 ──────────────────────────────────────────────

@region_bp.route("/api/regions", methods=["GET"])
def get_regions():
    """获取省份-城市树形结构"""
    result = []
    for province, cities in CHINA_REGIONS.items():
        result.append({
            "province": province,
            "cities": cities,
        })
    return jsonify({"regions": result})


@region_bp.route("/api/bidding", methods=["GET"])
def list_bidding():
    """查询招标信息，支持区域、类别、状态、关键词筛选"""
    data = load_bidding()

    province = request.args.get("province", "").strip()
    city = request.args.get("city", "").strip()
    category = request.args.get("category", "").strip()
    keyword = request.args.get("keyword", "").strip()
    status = request.args.get("status", "").strip()

    if province:
        data = [d for d in data if d["region_province"] == province]
    if city:
        data = [d for d in data if d["region_city"] == city]
    if category:
        data = [d for d in data if d["category"] == category]
    if status:
        data = [d for d in data if d["status"] == status]
    if keyword:
        kw = keyword.lower()
        data = [d for d in data if kw in d["title"].lower() or kw in d["agency"].lower() or kw in d["region_city"].lower()]

    # 按发布日期倒序
    data.sort(key=lambda x: x["publish_date"], reverse=True)

    total = len(data)
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    start = (page - 1) * per_page
    end = start + per_page

    return jsonify({
        "items": data[start:end],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total > 0 else 1,
    })


@region_bp.route("/api/bidding/<bid_id>", methods=["GET"])
def get_bidding_detail(bid_id):
    """获取单条招标详情"""
    data = load_bidding()
    for item in data:
        if item["id"] == bid_id:
            return jsonify({"success": True, "data": item})
    return jsonify({"success": False, "message": "未找到该招标信息"}), 404


@region_bp.route("/api/bidding/stats", methods=["GET"])
def get_bidding_stats():
    """获取招标数据统计概览"""
    data = load_bidding()
    now = datetime.now()

    total = len(data)
    by_status = {}
    by_category = {}
    by_province = {}
    expiring_soon = 0

    for item in data:
        # 按状态统计
        s = item["status"]
        by_status[s] = by_status.get(s, 0) + 1

        # 按类别统计
        c = item["category"]
        by_category[c] = by_category.get(c, 0) + 1

        # 按省份统计
        p = item["region_province"]
        by_province[p] = by_province.get(p, 0) + 1

        # 即将截止（7 天内）
        try:
            deadline = datetime.strptime(item["deadline"], "%Y-%m-%d")
            if 0 <= (deadline - now).days <= 7 and item["status"] == "招标中":
                expiring_soon += 1
        except:
            pass

    return jsonify({
        "total": total,
        "by_status": by_status,
        "by_category": by_category,
        "by_province": dict(sorted(by_province.items(), key=lambda x: x[1], reverse=True)[:10]),
        "expiring_soon": expiring_soon,
    })


@region_bp.route("/api/bidding/refresh", methods=["POST"])
def refresh_bidding():
    """重新生成模拟招标数据"""
    data = generate_mock_bidding()
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(BIDDING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return jsonify({"success": True, "message": f"已重新生成 {len(data)} 条招标数据", "total": len(data)})
