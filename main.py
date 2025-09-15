import os
import json
from datetime import datetime, timezone
from utils import logger
from utils.timer import start_timer
from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd
import pytz

# ----------------------
# 初始化 OpenAI
# ----------------------
load_dotenv()
client = None
if os.getenv("OPENAI_API_KEY"):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ----------------------
# 初始化資料庫
# ----------------------
def init_db():
    logger.init_db()

# ----------------------
# Timer callback
# ----------------------
def on_timer_finish(label, seconds):
    print(f"[callback] 計時器 '{label}' 結束 ({seconds}s)")
    # 回報計時器完成，並提供下一步建議
    print("接下來的步驟：請繼續監控病人的反應，準備給藥。")

# ----------------------
# 顯示紀錄轉為 XML
# ----------------------
def logs_to_xml():
    rows = logger.list_logs(1000)
    xml = "<logs>\n"
    for r in rows:
        xml += f'  <event id="{r[0]}" timestamp="{r[3]}">\n'
        xml += f'    <name>{r[1]}</name>\n'
        xml += f'    <note>{r[2]}</note>\n'
        xml += f'    <extra>{r[4]}</extra>\n'
        xml += "  </event>\n"
    xml += "</logs>"
    return xml

# ----------------------
# OpenAI 解析輸入
# ----------------------
def parse_openai_input(text, previous_events):
    if not client:
        return {"action": "reply", "message": "OpenAI 尚未設定"}
    
    # 定義系統提示，強調要根據急救紀錄來給建議
    system_prompt = (
        "你是一個 ACLS（急救心臟生命支持）助手，專注於協助使用者進行急救。\n"
        "你的任務包括：\n"
        "1. 判斷使用者輸入是否需要紀錄事件或給藥，並生成事件名稱、完整說明、藥物名稱、劑量、途徑、EKG等資訊。\n"
        "2. 判斷是否需要設定計時器，並提供建議。\n"
        "3. 僅提供急救建議，勿提供非急救醫療建議。\n"
        "4. 所有回覆請簡明、精準、禮貌，使用中文。\n"
        "5. 如果需要你紀錄事件，請自動根據ACLS紀錄完整，例如:epi 1mg ivp請記錄成Epinephrine 1mg IV-push\n"
        '{"action":"log_event","event":"電擊","note":"VF 心律，已執行電擊","extra":{"ekg":"VF","energy":"200J"}} 或 '
        '{"action":"start_timer","seconds":180,"label":"下一次給藥"} 或 {"action":"reply","message":"請先確定患者氣道"}'
        "\n\n"
        "如果使用者輸入了「病人OHCA」這樣的訊息，請紀錄病人發生OHCA的時間，並回覆指引："
        "紀錄事件：OHCA，開始急救。\n"
        "請提示開始心肺復甦（CPR），並準備使用除顫器（AED）。\n"
        "如果病人已經進行了電擊，請提示繼續下一步急救措施。\n"
        "\n\n"
        "這是過去的急救事件，請參考它來建議下一步：\n"
        f"過去的急救事件：{previous_events}\n"
        "現在請基於病人的狀況和過去的急救步驟，提供下一步的建議。"
    )



    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[ 
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.5
        )
        choice = resp.choices[0]
        content = getattr(choice.message, "content", "")
        try:
            data = json.loads(content)
        except:
            data = {"action": "reply", "message": content}
        return data
    except Exception as e:
        return {"action": "reply", "message": f"OpenAI解析錯誤: {e}"}
# ----------------------
# 事件紀錄處理
# ----------------------
def handle_action(data, previous_events):
    action = data.get("action")

    if action == "log_event":
        event = data.get("event", "事件")
        note = data.get("note", "")
        extra = data.get("extra")
        tz = pytz.timezone("Asia/Taipei")  # 設定台灣時區
        ts = datetime.now(tz).strftime("%Y/%m/%d %H:%M")  # 格式化時間，使用台灣時間
        logger.log_event(event, note=note, ts=ts, extra=extra)
        previous_events.append(f"{ts} {event} - {note}")  # 將事件和時間加到歷史紀錄

        print(f"已紀錄事件：{ts} {event}，並提供後續建議。")
        
        # 根據歷史紀錄獲得下一步建議
        next_step = parse_openai_input("下一步我該做什麼", previous_events)
        if next_step.get("action") == "reply":
            print(f"建議步驟：{next_step.get('message')}")
        else:
            print("無法提供建議，請手動處理。")

    elif action == "start_timer":
        sec = data.get("seconds", 60)
        label = data.get("label", "計時器")
        start_timer(sec, label=label, on_finish=on_timer_finish)
        print(f"已開始計時器: {sec}秒 ({label})")

    elif action == "reply":
        print(data.get("message", ""))

    else:
        print("無法解析動作，請重新描述。")


# ----------------------
# 主程式迴圈
# ----------------------
def main_loop():
    logger.init_db()
    logger.clear_logs()
    print("ACLS Assistant CLI\n輸入 'help' 查看可用指令。")

    previous_events = []  # 用來存儲歷史事件

    while True:
        try:
            text = input("> ").strip()
            if not text:
                continue
            if text.lower() in ("exit", "quit", "q"):
                print("bye")
                break
            if text in ("help", "h", "?"):
                print("可用指令:\n  show logs | 顯示記錄\n  export logs | 匯出紀錄\n  exit")
                continue

            # 解析輸入並處理
            data = parse_openai_input(text, previous_events)
            handle_action(data, previous_events)

            # 顯示紀錄指令
            if text.startswith("show logs") or text.startswith("顯示記錄"):
                print(logs_to_xml())
            if text.startswith("export logs") or text.startswith("匯出紀錄"):
                filename = f"ACLS_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                rows = logger.list_logs(1000)
                df = pd.DataFrame(rows, columns=["ID", "Event", "Note", "Timestamp", "Extra"])
                df.to_excel(filename, index=False)
                print(f"已匯出紀錄到 {filename}")

        except KeyboardInterrupt:
            print("\nKeyboardInterrupt, bye")
            break

if __name__ == "__main__":
    main_loop()