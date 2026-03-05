import asyncio
import aiosmtplib
from email.mime.text import MIMEText

async def test():
    msg = MIMEText("If you see this, Gmail SMTP is working!")
    msg["Subject"] = "Task Management SMTP Test"
    msg["From"]    = "creadchristopher@gmail.com"
    msg["To"]      = "shingai.dzinotyiweyi@gmail.com"

    await aiosmtplib.send(
        msg,
        hostname="smtp.gmail.com",
        port=587,
        username="creadchristopher@gmail.com",
        password="nivtrreufpzsdfvh",   # your 16-char app password
        start_tls=True,
    )
    print("✅ Email sent successfully!")

asyncio.run(test())