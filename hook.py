import requests

WEBHOOK_URL = "https://discord.com/api/webhooks/1393292513451839579/2inmHH2tRr5kGTJq46dgrY4b4A494K5IPOLsYNCl4-7LVXz4JtnTs0YlKvtNPZsB1M5-"

payload = {
    "username": "เลขาขี้อ้อน 💦",
    "avatar_url": "https://i.imgur.com/dZl8D1r.png",
    "content": "📣 พรี่ๆ~ เลขารวมหลุมความจึ้งมาให้แล้วค่าาา~",
    "embeds": [
        {
            "title": "💋 @OmgNhoy - โพสต์ใหม่จ้า~",
            "url": "https://x.com/OmgNhoy/status/1920038189659738199",
            "color": 16711935
        },
        {
            "title": "💋 @OmgNhoy - จึ้งอีกแล้ว~",
            "url": "https://x.com/OmgNhoy/status/1910230732489769047",
            "color": 16711935
        },
        {
            "title": "💋 @OmgNhoy - ห้ามพลาดเลยนะพรี่~",
            "url": "https://x.com/OmgNhoy/status/1904229444228985036",
            "color": 16711935
        },
        {
            "title": "💋 @OmgNhoy - อันนี้ก็เด็ด~",
            "url": "https://x.com/OmgNhoy/status/1894260292273803542",
            "color": 16711935
        }
    ],
    "components": [
        {
            "type": 1,
            "components": [
                {
                    "type": 2,
                    "label": "ดูทั้งหมดบน X",
                    "style": 5,
                    "url": "https://x.com/OmgNhoy"
                }
            ]
        }
    ]
}

r = requests.post(WEBHOOK_URL, json=payload)
print("✅ ส่งเรียบร้อย!" if r.status_code == 204 else f"❌ เกิดข้อผิดพลาด: {r.text}")
