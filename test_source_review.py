import json

from tools.source_review_tools import source_review


sources = [
    {
        "source_index": 0,
        "title": "创作者「数位商品」怎么卖？新手完整攻略",
        "url": "https://portaly.cc/blog/digital-products-sell",
        "snippet": "整理数字商品类型、销售策略、电子书、模板、AI 提示词包等。",
        "source": "portaly.cc",
        "score": 0.8,
        "retrieved_at": "2026-06-06T00:00:00Z",
    },
    {
        "source_index": 1,
        "title": "三个月月入10万，虚拟资料暴利玩法",
        "url": "https://example-blog.com/money",
        "snippet": "保姆级教程，免费领取资料包，教你快速变现。",
        "source": "example-blog.com",
        "score": 0.7,
        "retrieved_at": "2026-06-06T00:00:00Z",
    },
    {
        "source_index": 2,
        "title": "关于即时表单问题类型和设置",
        "url": "https://ads.tiktok.com/help/article/about-instant-form-question-types-and-settings?lang=zh",
        "snippet": "介绍即时表单中的自定义问题、图片问题和跳转题。",
        "source": "ads.tiktok.com",
        "score": 0.5,
        "retrieved_at": "2026-06-06T00:00:00Z",
    },
    {
        "source_index": 3,
        "title": "如何从 0 到 1 打造爆款知识付费内容产品",
        "url": "https://www.woshipm.com/marketing/5392062.html",
        "snippet": "知识付费内容产品的核心要做好选题策划和详情营销，选题策划要把握普适度、刚需度和新颖度。",
        "source": "www.woshipm.com",
        "score": 0.9,
        "retrieved_at": "2026-06-06T00:00:00Z",
    },
    {
        "source_index": 4,
        "title": "中国在线知识付费市场研究报告",
        "url": "http://pdf.dfcfw.com/pdf/H3_AP201804081119417209_1.pdf",
        "snippet": "在线知识付费产业指代以付费购买在线知识服务为核心衍生出的上下游业态集合体。",
        "source": "pdf.dfcfw.com",
        "score": 0.7,
        "retrieved_at": "2026-06-06T00:00:00Z",
    },
    {
        "source_index": 5,
        "title": "知识付费怎么赚钱",
        "url": "https://m.polyv.net/news?p=91639",
        "snippet": "合理定价是确保收入的关键，可以采用免费试读、限时优惠、会员制等策略吸引用户。",
        "source": "m.polyv.net",
        "score": 0.6,
        "retrieved_at": "2026-06-06T00:00:00Z",
    },
]

result = source_review(
    research_goal="适合个人做电子资料商品的选题方法",
    sources=sources,
)

print(json.dumps(result, ensure_ascii=False, indent=2))
