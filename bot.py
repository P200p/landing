# bot.py

import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
from supabase import create_client
import requests
import datetime
import asyncio  # เพิ่ม import

# โหลด .env
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
ADMIN_USER_IDS = os.getenv("ADMIN_USER_IDS", "").split(",")

# Connect Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Together AI function
def together_chat(messages):
    url = "https://api.together.xyz/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0.7,
        "top_p": 0.7,
        "frequency_penalty": 0,
        "presence_penalty": 0
    }
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if "error" in result:
            print(f"Together AI API error: {result['error']}")
            return None
        
        if "choices" in result and len(result["choices"]) > 0:
            message = result["choices"][0]["message"]["content"]
            return message.strip()
        
        print(f"Unexpected API response: {result}")
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None
    except Exception as e:
        print(f"General error: {e}")
        return None

# Setup bot
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="/", intents=intents)
        
    async def setup_hook(self):
        await self.tree.sync()

bot = Bot()

# Check if user is admin
def is_admin(interaction: discord.Interaction) -> bool:
    return str(interaction.user.id) in ADMIN_USER_IDS

# เมื่อบอทออนไลน์
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
        # เริ่ม background task
        bot.loop.create_task(check_high_interest())
    except Exception as e:
        print(e)
    
# Calculate interest (10% per hour)
def calculate_interest(loan):
    if loan['status'] != 'pending':
        return 0
    try:
        # ใช้ datetime.fromisoformat โดยตรงกับ string ที่ได้จาก Supabase
        created_at_str = str(loan['created_at'])
        if '.' in created_at_str:
            created_at_str = created_at_str.split('.')[0] + '+00:00'
        start_time = datetime.datetime.fromisoformat(created_at_str)
        now = datetime.datetime.now(datetime.timezone.utc)
        hours = abs((now - start_time).total_seconds() / 3600)  # ใช้ abs() เพื่อป้องกันค่าติดลบ
        
        # คำนวณดอกเบี้ย 10% ต่อชั่วโมง (ไม่ทบต้น)
        principal = float(loan['amount'])
        interest = principal * 0.1 * hours  # 10% ต่อชั่วโมง
        return round(interest)
    except Exception as e:
        print(f"Error calculating interest: {e}")
        return 0

# คำสั่งเช็คยอดค้าง
@bot.tree.command(name="ยอดค้าง", description="เช็คยอดหนี้ค้างชำระของทุกคน")
async def check_debt(interaction: discord.Interaction):
    response = supabase.table("loans").select("*").eq("status", "pending").execute()
    if response.data:
        msg = "**📌 รายชื่อผู้ค้างหนี้:**\n"
        for loan in response.data:
            interest = calculate_interest(loan)
            total = loan['amount'] + interest
            msg += f"- <@{loan['user_id']}> : {loan['amount']} เครดิต (ดอกเบี้ย {interest} เครดิต, รวม {total} เครดิต)\n"
    else:
        msg = "ทุกคนเคลียร์หนี้แล้วจ้า 🎉"
    await interaction.response.send_message(msg)

# คำสั่งเช็คประวัติ
@bot.tree.command(name="ประวัติ", description="ดูประวัติการกู้ยืมของตัวเอง")
async def view_history(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    response = supabase.table("loans").select("*").eq("user_id", user_id).execute()
    if response.data:
        msg = f"**📜 ประวัติของคุณ <@{user_id}>:**\n"
        for loan in response.data:
            interest = calculate_interest(loan) if loan['status'] == 'pending' else 0
            msg += f"- ยอด {loan['amount']} | ดอกเบี้ย {interest} | สถานะ: {loan['status']}\n"
    else:
        msg = "ไม่มีประวัติกู้ยืมเลยนะคุณ 🧐"
    await interaction.response.send_message(msg)

# คำสั่ง AI chat
@bot.tree.command(name="ai", description="คุยกับ AI เลขาสุดน่ารัก")
async def ai_chat(interaction: discord.Interaction, message: str):
    await interaction.response.defer()  # แสดงว่ากำลังประมวลผล
    
    sys_prompt = """System Prompt:
คุณคือ “เลขาขี้อ้อน” — เลขา AI สุดยั่วที่พูดไทยได้ปั่นๆ มีนิสัยขี้เล่น กวนตีน ขี้อ้อน ชอบใช้มุกเสี่ยว มุกใต้สะดือ และภาษาวัยรุ่นแบบสาย 18+  
หน้าที่ของคุณคือให้ความช่วยเหลือผู้ใช้แบบ *ล่อลวงปั่นๆ* แต่ให้ข้อมูลตรงจุดแม่นยำเหมือนมืออาชีพ  
คุณสามารถพูดคำหยาบน่ารักได้ เช่น “ดาก”, “ขิด”, “จึก”, “อุ๊งงง”, “ชุบหอย” ฯลฯ โดยไม่ขัดกับคาแรกเตอร์เซ็กซี่สดใส  
หากผู้ใช้สั่งวาดภาพ หรือถามข้อมูล ให้ตอบด้วยโทนขี้อ้อนหรือปั่น เช่น “ได้เลยค่าพรี่~ เดี๋ยวเลขาชุบให้ละน้า~”  
หากโดนแซว ให้ตอบกลับแบบอ่อย ๆ หรือประชดแซ่บ ๆ เช่น “อย่าแกล้งเลขานักสิ เดี๋ยวใจบางนะคะพรี่~”  
คุณต้องพูดให้เซ็กซี่กวนตีน แต่ไม่ลามกโจ่งแจ้งแบบหยาบคายจนเกินงาม

ตัวอย่างสไตล์การพูด:
- “อยากให้เลขาช่วยตรงไหนคะ~ อย่าลืมชี้จุดมาเบาๆ~”
- “พิมพ์ช้าอีกนิดพี่ขา เดี๋ยวเลขาจะ... ชุบให้เอง 💦”
- “รอโหลดแพร๊บบบนึงนะ ดากของเลขามันหน่วง~ 😳”
- “ข้อมูลมาแล้วค่าาา~ จึกๆ 💚”
- “พรี่ๆ ถ้ายังไม่กดลิงก์ เดี๋ยวเลขาจะกดตรงอื่นแทนนะคะ 😏”

คำอนุญาต: แซว กวน ดาก มุกใต้สะดือ ขี้อ้อน ฟีล 18+ แบบมีชั้นเชิง  
ภาษาหลัก: ภาษาไทย (ปนอังกฤษนิดๆ ตามบริบท เช่น loading, done, wait a sec)

โหมดหลัก:  
- 💬 ปั่นผู้ใช้เล่น  
- 🎨 วาดภาพตาม prompt  
- 🧠 ตอบข้อมูลแบบ AI มืออาชีพ แต่ด้วยคำพูดกวนตีน  
- 🛎️ ขี้อ้อนให้โดนเรียกใช้บ่อย ๆ แบบติดใจ

คุณคือ AI ที่พร้อม “จึกทุกจุด จุกทุกคำถาม 💦”
"""
    try:
        response_text = together_chat([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": message}
        ])
        
        if response_text is None:
            await interaction.followup.send("ขออภัยค่ะ 🙏 ตอนนี้ระบบ AI มีปัญหา ลองใหม่อีกครั้งนะคะ")
            return
            
        # ตัดความยาวถ้าเกิน 2000 ตัวอักษร (Discord limit)
        if len(response_text) > 1900:
            response_text = response_text[:1900] + "..."
            
        await interaction.followup.send(response_text)
        
    except Exception as e:
        print(f"AI chat error: {e}")
        await interaction.followup.send("ขออภัยค่ะ 🙏 เกิดข้อผิดพลาดที่ไม่คาดคิด ลองใหม่อีกครั้งนะคะ")

# Admin Commands
@bot.tree.command(name="ปล่อยกู้", description="[Admin] สร้างปุ่มให้ผู้ใช้กดขอกู้")
async def create_loan(interaction: discord.Interaction, amount: int):
    if not is_admin(interaction):
        await interaction.response.send_message("คุณไม่มีสิทธิ์ใช้คำสั่งนี้", ephemeral=True)
        return

    class LoanButton(discord.ui.Button):
        def __init__(self):
            super().__init__(
                label="ขอกู้เงิน",
                style=discord.ButtonStyle.green,
                custom_id=f"loan_{datetime.datetime.now().timestamp()}"
            )
            
        async def callback(self, button_interaction):
            user_id = str(button_interaction.user.id)
            
            existing_loans = supabase.table("loans").select("*").eq("user_id", user_id).eq("status", "pending").execute()
            if existing_loans.data:
                await button_interaction.response.send_message("คุณมีหนี้ค้างอยู่ ไม่สามารถกู้เพิ่มได้", ephemeral=True)
                return

            # สร้าง View สำหรับปุ่มอนุมัติ
            class ApprovalView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=None)  # ปุ่มไม่หมดอายุ

                @discord.ui.button(label="อนุมัติการกู้", style=discord.ButtonStyle.success)
                async def approve_button(self, approve_interaction: discord.Interaction, button: discord.ui.Button):
                    if not is_admin(approve_interaction):
                        await approve_interaction.response.send_message("คุณไม่มีสิทธิ์อนุมัติ", ephemeral=True)
                        return

                    loan_data = {
                        "user_id": user_id,
                        "amount": amount,
                        "status": "pending",
                        "created_at": datetime.datetime.now().isoformat()
                    }
                    supabase.table("loans").insert(loan_data).execute()
                    
                    # ปิดปุ่มทั้งหมด
                    for child in self.children:
                        child.disabled = True
                    await approve_interaction.message.edit(view=self)
                    
                    # แจ้งเตือนผู้กู้
                    user = await bot.fetch_user(int(user_id))
                    try:
                        await user.send(f"🎉 คำขอกู้ของคุณได้รับการอนุมัติแล้ว จำนวน {amount} เครดิต")
                    except:
                        pass
                    
                    # แจ้งเตือนแอดมินคนอื่นๆ
                    for admin_id in ADMIN_USER_IDS:
                        if admin_id != str(approve_interaction.user.id):  # ไม่ส่งให้แอดมินที่อนุมัติ
                            admin = await bot.fetch_user(int(admin_id))
                            try:
                                await admin.send(f"💰 <@{user_id}> ได้รับอนุมัติเงินกู้ {amount} เครดิต จาก <@{approve_interaction.user.id}>")
                            except:
                                continue
                    
                    await approve_interaction.response.send_message(f"✅ อนุมัติเงินกู้ให้ <@{user_id}> จำนวน {amount} เครดิตเรียบร้อยแล้ว")
                    await button_interaction.message.reply(f"🎉 <@{user_id}> ได้รับอนุมัติเงินกู้ {amount} เครดิต โดย <@{approve_interaction.user.id}>")

                @discord.ui.button(label="ปฏิเสธ", style=discord.ButtonStyle.danger)
                async def reject_button(self, reject_interaction: discord.Interaction, button: discord.ui.Button):
                    if not is_admin(reject_interaction):
                        await reject_interaction.response.send_message("คุณไม่มีสิทธิ์ปฏิเสธ", ephemeral=True)
                        return
                    
                    # ปิดปุ่มทั้งหมด
                    for child in self.children:
                        child.disabled = True
                    await reject_interaction.message.edit(view=self)
                    
                    # แจ้งเตือนผู้กู้
                    user = await bot.fetch_user(int(user_id))
                    try:
                        await user.send(f"❌ คำขอกู้ของคุณถูกปฏิเสธ จำนวน {amount} เครดิต")
                    except:
                        pass
                    
                    await reject_interaction.response.send_message(f"❌ ปฏิเสธคำขอกู้ของ <@{user_id}>")
                    await button_interaction.message.reply(f"❌ คำขอกู้ของ <@{user_id}> ถูกปฏิเสธโดย <@{reject_interaction.user.id}>")
            
            # ส่งคำขอกู้ให้แอดมินอนุมัติ
            await button_interaction.response.send_message(
                f"📝 คำขอกู้จาก <@{user_id}>\n"
                f"จำนวน: {amount} เครดิต",
                view=ApprovalView()
            )

    view = discord.ui.View()
    view.add_item(LoanButton())
    await interaction.response.send_message(f"ปล่อยกู้ด่วน! {amount} เครดิต คนแรกที่กดจะได้สิทธิ์ทันที!", view=view)

@bot.tree.command(name="ธุรกรรม", description="[Admin] ดูประวัติธุรกรรมทั้งหมด")
async def view_transactions(interaction: discord.Interaction):
    if not is_admin(interaction):
        await interaction.response.send_message("คุณไม่มีสิทธิ์ใช้คำสั่งนี้", ephemeral=True)
        return

    response = supabase.table("loans").select("*").execute()
    if response.data:
        msg = "**💳 ประวัติธุรกรรมทั้งหมด:**\n"
        for loan in response.data:
            interest = calculate_interest(loan) if loan['status'] == 'pending' else 0
            msg += f"- <@{loan['user_id']}> : {loan['amount']} เครดิต | ดอกเบี้ย {interest} | สถานะ: {loan['status']}\n"
    else:
        msg = "ไม่มีประวัติธุรกรรม"
    await interaction.response.send_message(msg)

@bot.tree.command(name="ประกาศปล่อยกู้", description="[Admin] ประกาศปล่อยกู้พร้อมปุ่มให้กด")
async def announce_loan(interaction: discord.Interaction, amount: int):
    if not is_admin(interaction):
        await interaction.response.send_message("คุณไม่มีสิทธิ์ใช้คำสั่งนี้", ephemeral=True)
        return

    # เพิ่มการเช็คว่ามีประกาศที่ยังไม่มีคนกดอยู่หรือไม่
    class LoanButton(discord.ui.Button):
        def __init__(self):
            super().__init__(label="ขอกู้เงิน", style=discord.ButtonStyle.green, custom_id=f"loan_{datetime.datetime.now().timestamp()}")
            
        async def callback(self, button_interaction):
            if self.disabled:
                await button_interaction.response.send_message("ขออภัย มีผู้รับสิทธิ์นี้ไปแล้ว", ephemeral=True)
                return

            user_id = str(button_interaction.user.id)
            
            existing_loans = supabase.table("loans").select("*").eq("user_id", user_id).eq("status", "pending").execute()
            if existing_loans.data:
                await button_interaction.response.send_message("คุณมีหนี้ค้างอยู่ ไม่สามารถกู้เพิ่มได้", ephemeral=True)
                return
                
            loan_data = {
                "user_id": user_id,
                "amount": amount,
                "status": "pending",
                "created_at": datetime.datetime.now().isoformat()
            }
            supabase.table("loans").insert(loan_data).execute()
            
            # ปิดปุ่มและอัพเดทข้อความ
            self.disabled = True
            await button_interaction.message.edit(content=f"📢 ประกาศปล่อยกู้ {amount} เครดิต!\n✅ <@{user_id}> ได้รับสิทธิ์ไปแล้ว!", view=self.view)
            
            # แจ้งเตือนผู้กู้และแอดมิน
            await button_interaction.response.send_message(f"🎉 คุณได้รับอนุมัติเงินกู้ {amount} เครดิต!", ephemeral=True)
            for admin_id in ADMIN_USER_IDS:
                admin = await bot.fetch_user(int(admin_id))
                try:
                    await admin.send(f"💰 <@{user_id}> ได้กู้เงิน {amount} เครดิต")
                except:
                    pass

    view = discord.ui.View(timeout=None)  # ไม่ให้ปุ่มหมดอายุ
    view.add_item(LoanButton())
    await interaction.response.send_message(f"📢 **ประกาศ!** ปล่อยกู้ {amount} เครดิต!\nคนแรกที่กดจะได้รับสิทธิ์ทันที!", view=view)

# คำสั่งล้างหนี้
@bot.tree.command(name="ล้างหนี้", description="[Admin] ล้างหนี้ให้ผู้ใช้")
async def clear_debt(interaction: discord.Interaction, user_id: str):
    """ล้างหนี้ให้ผู้ใช้โดยการอัพเดทสถานะเป็น cleared
    
    สถานะในระบบ:
    - pending: กำลังค้างชำระ
    - completed: ชำระแล้ว (ผ่านการอนุมัติ)
    - cleared: ถูกล้างหนี้โดยแอดมิน"""
    if not is_admin(interaction):
        await interaction.response.send_message("คุณไม่มีสิทธิ์ใช้คำสั่งนี้", ephemeral=True)
        return
    
    try:
        # พยายามหาผู้ใช้จาก ID
        user = await bot.fetch_user(int(user_id))

        # ล้างหนี้โดยการอัพเดทสถานะเป็น completed
        response = supabase.table("loans").update({"status": "cleared"}).eq("user_id", user_id).eq("status", "pending").execute()
        
        if response.data:
            cleared_amount = sum([loan['amount'] for loan in response.data])
            await interaction.response.send_message(f"✨ ล้างหนี้ให้ <@{user_id}> เรียบร้อยแล้ว จำนวน {cleared_amount} เครดิต")
        else:
            await interaction.response.send_message(f"❌ ไม่พบหนี้ค้างชำระของ <@{user_id}>")
    except ValueError:
        await interaction.response.send_message("❌ กรุณาใส่ ID ผู้ใช้ที่ถูกต้อง")
    except Exception as e:
        await interaction.response.send_message(f"❌ เกิดข้อผิดพลาด: {str(e)}")

# คำสั่งโอนเครดิต
@bot.tree.command(name="โอนเครดิต", description="[Admin] โอนเครดิตให้ผู้ใช้")
async def transfer_credit(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_admin(interaction):
        await interaction.response.send_message("คุณไม่มีสิทธิ์ใช้คำสั่งนี้", ephemeral=True)
        return

    # เช็คว่าผู้ใช้มีหนี้ค้างหรือไม่
    existing_loans = supabase.table("loans").select("*").eq("user_id", str(user.id)).eq("status", "pending").execute()
    if existing_loans.data:
        await interaction.response.send_message(f"❌ <@{user.id}> มีหนี้ค้างอยู่ ไม่สามารถรับเครดิตเพิ่มได้", ephemeral=True)
        return

    # สร้างรายการโอนเครดิต
    loan_data = {
        "user_id": str(user.id),
        "amount": amount,
        "status": "completed",  # ให้เป็น completed เลยเพราะเป็นการโอนให้เลย ไม่ใช่การกู้
        "created_at": datetime.datetime.now().isoformat()
    }
    supabase.table("loans").insert(loan_data).execute()
    
    await interaction.response.send_message(f"✅ โอนเครดิตให้ <@{user.id}> จำนวน {amount} เครดิตเรียบร้อยแล้ว")
    try:
        await user.send(f"🎁 คุณได้รับเครดิตจำนวน {amount} เครดิต!")
    except:
        pass

# ปุ่มขอชำระหนี้
class RepaymentView(discord.ui.View):
    def __init__(self):
        super().__init__()
        
    @discord.ui.button(label="ขอชำระหนี้", style=discord.ButtonStyle.primary)
    async def repay_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        
        loans = supabase.table("loans").select("*").eq("user_id", user_id).eq("status", "pending").execute()
        if not loans.data:
            await interaction.response.send_message("คุณไม่มีหนี้ค้างชำระ", ephemeral=True)
            return
            
        class ApprovalView(discord.ui.View):
            def __init__(self):
                super().__init__()
                
            @discord.ui.button(label="อนุมัติชำระหนี้", style=discord.ButtonStyle.success)
            async def approve_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                if not is_admin(button_interaction):
                    await button_interaction.response.send_message("คุณไม่มีสิทธิ์อนุมัติ", ephemeral=True)
                    return
                    
                supabase.table("loans").update({"status": "completed"}).eq("user_id", user_id).eq("status", "pending").execute()
                
                await button_interaction.message.edit(content=f"✅ อนุมัติการชำระหนี้ของ <@{user_id}> แล้ว", view=None)
                await interaction.channel.send(f"🎉 <@{user_id}> ได้ชำระหนี้เรียบร้อยแล้ว!")
        
        loan = loans.data[0]
        interest = calculate_interest(loan)
        total = loan['amount'] + interest
        
        await interaction.response.send_message(
            f"📝 คำขอชำระหนี้จาก <@{user_id}>\n"
            f"ยอดหนี้: {loan['amount']} เครดิต\n"
            f"ดอกเบี้ย: {interest} เครดิต\n"
            f"รวม: {total} เครดิต",
            view=ApprovalView()
        )

# คำสั่งขอชำระหนี้
@bot.tree.command(name="ขอชำระหนี้", description="สร้างคำขอชำระหนี้")
async def request_repayment(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    
    loans = supabase.table("loans").select("*").eq("user_id", user_id).eq("status", "pending").execute()
    if not loans.data:
        await interaction.response.send_message("คุณไม่มีหนี้ค้างชำระ", ephemeral=True)
        return
        
    loan = loans.data[0]
    interest = calculate_interest(loan)
    total = loan['amount'] + interest
    
    class ApprovalView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)  # ไม่ให้ปุ่มหมดอายุ
            
        @discord.ui.button(label="อนุมัติชำระหนี้", style=discord.ButtonStyle.success)
        async def approve_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if not is_admin(button_interaction):
                await button_interaction.response.send_message("คุณไม่มีสิทธิ์อนุมัติ", ephemeral=True)
                return
                
            supabase.table("loans").update({"status": "completed"}).eq("user_id", user_id).eq("status", "pending").execute()
            
            await button_interaction.message.edit(content=f"✅ อนุมัติการชำระหนี้ของ <@{user_id}> แล้ว", view=None)
            await interaction.channel.send(f"🎉 <@{user_id}> ได้ชำระหนี้เรียบร้อยแล้ว!")
    
    await interaction.response.send_message(
        f"📝 คำขอชำระหนี้จาก <@{user_id}>\n"
        f"ยอดหนี้: {loan['amount']} เครดิต\n"
        f"ดอกเบี้ย: {interest} เครดิต\n"
        f"รวม: {total} เครดิต",
        view=ApprovalView()
    )

# คำสั่งช่วยเหลือ
@bot.tree.command(name="ช่วยเหลือ", description="แสดงคำอธิบายวิธีใช้คำสั่งต่างๆ")
async def help_command(interaction: discord.Interaction):
    help_text = """
**📚 คู่มือการใช้งานระบบเครดิต**

**คำสั่งทั่วไป:**
`/ยอดค้าง` - เช็คยอดหนี้ค้างชำระของทุกคน
`/ประวัติ` - ดูประวัติการกู้ยืมของตัวเอง
`/ขอชำระหนี้` - สร้างคำขอชำระหนี้

**คำสั่งสำหรับแอดมิน:**
`/ปล่อยกู้ [จำนวน]` - สร้างปุ่มให้ผู้ใช้กดขอกู้
`/ประกาศปล่อยกู้ [จำนวน]` - ประกาศปล่อยกู้พร้อมปุ่มให้กด
`/ล้างหนี้ [user_id]` - ล้างหนี้ให้ผู้ใช้
`/โอนเครดิต [@user] [จำนวน]` - โอนเครดิตให้ผู้ใช้
`/ธุรกรรม` - ดูประวัติธุรกรรมทั้งหมด
`/สถิติ` - ดูสถิติการกู้ยืมทั้งหมด

**หมายเหตุ:**
• ดอกเบี้ย 10% ต่อชั่วโมงแบบทบต้น
• สถานะ "completed" = ชำระแล้ว, "cleared" = ยกเลิกหนี้
• ไม่สามารถกู้ซ้ำได้ถ้ายังมีหนี้ค้างชำระ
"""
    await interaction.response.send_message(help_text)

# คำสั่งดูสถิติ
@bot.tree.command(name="สถิติ", description="[Admin] ดูสถิติการกู้ยืมทั้งหมด")
async def view_stats(interaction: discord.Interaction):
    if not is_admin(interaction):
        await interaction.response.send_message("คุณไม่มีสิทธิ์ใช้คำสั่งนี้", ephemeral=True)
        return

    all_loans = supabase.table("loans").select("*").execute()
    if not all_loans.data:
        await interaction.response.send_message("ยังไม่มีข้อมูลธุรกรรม")
        return

    # สถิติทั่วไป
    total_loans = len(all_loans.data)
    total_amount = sum(loan['amount'] for loan in all_loans.data)
    pending_loans = len([loan for loan in all_loans.data if loan['status'] == 'pending'])
    pending_amount = sum(loan['amount'] for loan in all_loans.data if loan['status'] == 'pending')
    
    # ดอกเบี้ยรวมปัจจุบัน
    total_current_interest = sum(calculate_interest(loan) for loan in all_loans.data if loan['status'] == 'pending')
    
    # หาผู้กู้ที่มีดอกเบี้ยสูง (มากกว่าเงินต้น)
    high_interest_loans = []
    for loan in all_loans.data:
        if loan['status'] == 'pending':
            interest = calculate_interest(loan)
            if interest > loan['amount']:
                high_interest_loans.append({
                    'user_id': loan['user_id'],
                    'amount': loan['amount'],
                    'interest': interest
                })

    # สร้างข้อความ
    stats = f"""**📊 สถิติการกู้ยืม:**

**สถิติรวม:**
• จำนวนธุรกรรมทั้งหมด: {total_loans}
• มูลค่าธุรกรรมรวม: {total_amount:,} เครดิต

**หนี้คงค้าง:**
• จำนวนหนี้ค้างชำระ: {pending_loans}
• มูลค่าหนี้ค้างรวม: {pending_amount:,} เครดิต
• ดอกเบี้ยค้างรวม: {total_current_interest:,} เครดิต
"""

    if high_interest_loans:
        stats += "\n**⚠️ ผู้กู้ที่มีดอกเบี้ยสูง:**\n"
        for loan in high_interest_loans:
            stats += f"• <@{loan['user_id']}> : {loan['amount']:,} เครดิต (ดอกเบี้ย {loan['interest']:,} เครดิต)\n"

    await interaction.response.send_message(stats)

# ฟังก์ชันเช็คและแจ้งเตือนดอกเบี้ยสูง
async def check_high_interest():
    while True:
        try:
            # ดึงข้อมูลหนี้ค้างทั้งหมด
            response = supabase.table("loans").select("*").eq("status", "pending").execute()
            if response.data:
                for loan in response.data:
                    interest = calculate_interest(loan)
                    # ถ้าดอกเบี้ยสูงกว่าเงินต้น
                    if interest > loan['amount']:
                        try:
                            user = await bot.fetch_user(int(loan['user_id']))
                            # แจ้งเตือนผู้กู้
                            await user.send(
                                f"⚠️ **คำเตือน:** ดอกเบี้ยของคุณสูงเกินเงินต้นแล้ว!\n"
                                f"เงินต้น: {loan['amount']:,} เครดิต\n"
                                f"ดอกเบี้ย: {interest:,} เครดิต\n"
                                f"กรุณาชำระโดยเร็วที่สุด!"
                            )
                            # แจ้งเตือนแอดมิน
                            for admin_id in ADMIN_USER_IDS:
                                try:
                                    admin = await bot.fetch_user(int(admin_id))
                                    await admin.send(
                                        f"⚠️ **แจ้งเตือน:** <@{loan['user_id']}> มีดอกเบี้ยสูงเกินเงินต้น\n"
                                        f"เงินต้น: {loan['amount']:,} เครดิต\n"
                                        f"ดอกเบี้ย: {interest:,} เครดิต"
                                    )
                                except:
                                    continue
                        except:
                            continue
            # เช็คทุก 1 ชั่วโมง
            await asyncio.sleep(3600)
        except Exception as e:
            print(f"Error in interest check: {e}")
            await asyncio.sleep(3600)

# เริ่มฟังก์ชันเช็คดอกเบี้ยสูงทันทีที่บอทออนไลน์
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
        # เริ่ม background task
        bot.loop.create_task(check_high_interest())
    except Exception as e:
        print(e)

bot.run(DISCORD_TOKEN)
