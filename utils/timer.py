# utils/timer.py
import threading
import time
import platform

def _beep():
    # cross-platform simple beep
    try:
        if platform.system() == "Windows":
            import winsound
            winsound.Beep(1000, 300)
        else:
            # macOS / Linux: try printf bell
            print("\a", end="", flush=True)
    except Exception:
        pass

def start_timer(seconds, label=None, on_finish=None):
    """
    非阻塞計時器，seconds 為秒數。
    on_finish: function to call when timer ends，傳入 (label, seconds)
    """
    def worker():
        end = time.time() + seconds
        while True:
            rem = int(end - time.time())
            if rem <= 0:
                break
            # 每分鐘或每10秒可顯示一次 (視需要調整)
            if rem % 60 == 0 or rem <= 10:
                print(f"[timer] {label or 'timer'} — 剩餘 {rem} 秒")
            time.sleep(1)
        _beep()
        print(f"[timer] {label or 'timer'} — 時間到！({seconds} 秒)")
        if on_finish:
            try:
                on_finish(label, seconds)
            except Exception as e:
                print("[timer] on_finish callback error:", e)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t
