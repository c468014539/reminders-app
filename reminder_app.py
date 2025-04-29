
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2 import id_token
from google.auth.transport import requests as grequests


import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox, Toplevel
import tkinter as tk
import requests
import threading
from datetime import datetime, timedelta
import calendar
from PIL import Image, ImageDraw
import pystray

# API_URL = "https://reminder-api-o3ba.onrender.com/reminders"
API_URL = "http://127.0.0.1:8000/reminders"

class ReminderApp:
    def __init__(self, root):
        self.auth_headers = self.login_google()
        self.root = root
        self.root.title("提醒事项")
        self.reminders = []

        self.load_reminders()
        self.create_widgets()
        self.check_today_reminders()
        self.show_all()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.create_tray_icon()


    def load_reminders(self):
        print("开始执行 load_reminders")
        try:
            resp = requests.get(API_URL, headers=self.auth_headers)
            print("请求地址：", API_URL)
            print("请求头：", self.auth_headers)
            print("响应状态码：", resp.status_code)
            print("响应内容：", resp.text)
            if resp.status_code == 200:
                self.reminders = resp.json()
            else:
                messagebox.showerror("错误", f"加载提醒失败：{resp.status_code}\n{resp.text}")
                self.reminders = []
        except Exception as e:
            import traceback
            print("异常堆栈：", traceback.format_exc())
            messagebox.showerror("异常", f"无法连接服务器：{e}")
            self.reminders = []
            
    def save_reminder(self):
        d, t = self.date_var.get(), self.time_entry.get() or "00:00"
        title = self.title_entry.get()
        content = self.content_entry.get('1.0', 'end').strip()
        if not (d and title):
            messagebox.showwarning("提示", "日期和标题不能为空")
            return
        data = {
            "date": d,
            "time": t,
            "title": title,
            "description": content
        }
        try:
            resp = requests.post(API_URL, json=data, headers=self.auth_headers)
            if resp.status_code == 200:
                messagebox.showinfo("成功", "已保存")
                self.load_reminders()
                self.show_all()
                self.clear_entries()
            else:
                messagebox.showerror("错误", f"保存失败：{resp.status_code}")
        except Exception as e:
            messagebox.showerror("异常", f"网络错误：{e}")

    def update_reminder(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请选择一项")
            return
        rem_id = int(sel[0])
        reminder = next((r for r in self.reminders if r['id'] == rem_id), None)
        if not reminder:
            messagebox.showwarning("提示", "找不到对应提醒")
            return
        d, t = self.date_var.get(), self.time_entry.get() or "00:00"
        title = self.title_entry.get()
        content = self.content_entry.get('1.0', 'end').strip()
        data = {
            "date": d,
            "time": t,
            "title": title,
            "description": content
        }
        try:
            resp = requests.put(f"{API_URL}/{rem_id}", json=data)
            if resp.status_code == 200:
                messagebox.showinfo("成功", "已更新")
                self.load_reminders()
                self.show_all()
                self.clear_entries()
            else:
                messagebox.showerror("错误", f"更新失败：{resp.status_code}")
        except Exception as e:
            messagebox.showerror("异常", f"网络错误：{e}")

    def delete_reminder(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请选择一项")
            return
        rem_id = int(sel[0])
        reminder = next((r for r in self.reminders if r['id'] == rem_id), None)
        if not reminder:
            messagebox.showwarning("提示", "找不到对应提醒")
            return
        try:
            resp = requests.delete(f"{API_URL}/{rem_id}")
            if resp.status_code == 200:
                messagebox.showinfo("成功", "已删除")
                self.load_reminders()
                self.show_all()
                self.clear_entries()
            else:
                messagebox.showerror("错误", f"删除失败：{resp.status_code}")
        except Exception as e:
            messagebox.showerror("异常", f"网络错误：{e}")

    def create_widgets(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="both", expand=True)

        search_frame = ttk.Frame(frame)
        search_frame.pack(pady=5)
        ttk.Label(search_frame, text="搜索:").pack(side="left")
        self.search_var = ttk.StringVar()
        self.search_var.trace_add("write", self.filter_items)
        ttk.Entry(search_frame, textvariable=self.search_var, width=30).pack(side="left", padx=5)

        input_frame = ttk.Labelframe(frame, text="新增 / 编辑提醒", padding=10)
        input_frame.pack(fill="x", pady=10)

        self.date_var = ttk.StringVar(value=datetime.today().strftime('%Y-%m-%d'))
        ttk.Label(input_frame, text="日期:").grid(row=0, column=0, sticky="e")
        self.date_entry = ttk.Entry(input_frame, textvariable=self.date_var, width=12)
        self.date_entry.grid(row=0, column=1, padx=5)
        ttk.Button(input_frame, text="📅", command=self.show_calendar_popup).grid(row=0, column=2)

        ttk.Label(input_frame, text="时间:").grid(row=0, column=3, sticky="e")
        self.time_entry = ttk.Entry(input_frame, width=10)
        self.time_entry.grid(row=0, column=4, padx=5)

        ttk.Label(input_frame, text="标题:").grid(row=1, column=0, sticky="e")
        self.title_entry = ttk.Entry(input_frame)
        self.title_entry.grid(row=1, column=1, columnspan=4, sticky="ew", padx=5, pady=5)

        ttk.Label(input_frame, text="内容:").grid(row=2, column=0, sticky="ne")
        self.content_entry = tk.Text(input_frame, height=4, width=50, wrap="word")
        self.content_entry.grid(row=2, column=1, columnspan=4, sticky="ew", padx=5)

        input_frame.columnconfigure(1, weight=1)
        input_frame.columnconfigure(4, weight=1)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="💾 保存", command=self.save_reminder, bootstyle="success").pack(side='left', padx=5)
        ttk.Button(btn_frame, text="✏️ 更新", command=self.update_reminder, bootstyle="info").pack(side='left', padx=5)
        ttk.Button(btn_frame, text="🗑️ 删除", command=self.delete_reminder, bootstyle="danger").pack(side='left', padx=5)

        filter_frame = ttk.Frame(frame)
        filter_frame.pack(pady=5)
        ttk.Button(filter_frame, text="全部", command=self.show_all).pack(side='left', padx=2)
        ttk.Button(filter_frame, text="今天", command=self.show_today).pack(side='left', padx=2)
        ttk.Button(filter_frame, text="本周", command=self.show_week).pack(side='left', padx=2)
        ttk.Button(filter_frame, text="本月", command=self.show_month).pack(side='left', padx=2)

        self.tree = ttk.Treeview(frame, columns=("date", "time", "title", "description"), show="headings")
        for col in ("date", "time", "title", "description"):
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor='center')
        self.tree.pack(fill="both", expand=True, pady=10)
        self.tree.bind("<Double-1>", self.load_selected_reminder)

    def filter_items(self, *args):
        query = self.search_var.get().lower()
        if not query:
            self.display_items(self.reminders)
            return
        filtered = [r for r in self.reminders if query in r['date'].lower() or query in r['time'].lower() or query in r['title'].lower() or query in r['description'].lower()]
        self.display_items(filtered)

    def show_all(self):
        self.display_items(self.reminders)

    def show_today(self):
        today = datetime.today().strftime('%Y-%m-%d')
        filtered = [r for r in self.reminders if r['date'] == today]
        self.display_items(filtered)

    def show_week(self):
        today = datetime.today().date()
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        filtered = [r for r in self.reminders if start <= datetime.strptime(r['date'], "%Y-%m-%d").date() <= end]
        self.display_items(filtered)

    def show_month(self):
        today = datetime.today().date()
        start = today.replace(day=1)
        end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        filtered = [r for r in self.reminders if start <= datetime.strptime(r['date'], "%Y-%m-%d").date() <= end]
        self.display_items(filtered)

    def display_items(self, items):
        for item in self.tree.get_children():
            self.tree.delete(item)
        sorted_items = sorted(items, key=lambda r: (r['date'], r['time']))
        for r in sorted_items:
            self.tree.insert('', 'end', iid=str(r['id']), values=(r['date'], r['time'], r['title'], r['description']))

    def load_selected_reminder(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        rem_id = int(sel[0])
        reminder = next((r for r in self.reminders if r['id'] == rem_id), None)
        if not reminder:
            return
        self.date_var.set(reminder['date'])
        self.time_entry.delete(0, 'end'); self.time_entry.insert(0, reminder['time'])
        self.title_entry.delete(0, 'end'); self.title_entry.insert(0, reminder['title'])
        self.content_entry.delete('1.0', 'end'); self.content_entry.insert('1.0', reminder['description'])

    def clear_entries(self):
        self.date_var.set(datetime.today().strftime('%Y-%m-%d'))
        self.time_entry.delete(0, 'end')
        self.title_entry.delete(0, 'end')
        self.content_entry.delete('1.0', 'end')

    def show_calendar_popup(self):
        def select_day(day):
            self.date_var.set(f"{cur_year.get()}-{cur_month.get():02d}-{day:02d}")
            top.destroy()
        def prev_month():
            m, y = cur_month.get()-1, cur_year.get()
            if m < 1: m, y = 12, y-1
            cur_month.set(m); cur_year.set(y); update_calendar()
        def next_month():
            m, y = cur_month.get()+1, cur_year.get()
            if m > 12: m, y = 1, y+1
            cur_month.set(m); cur_year.set(y); update_calendar()
        def update_calendar():
            for w in cal_frame.winfo_children(): w.destroy()
            y, m = cur_year.get(), cur_month.get()
            ttk.Button(cal_frame, text="<", command=prev_month).grid(row=0,column=0)
            ttk.Label(cal_frame, text=f"{y}年 {m}月", font=("Arial",12,"bold")).grid(row=0,column=1,columnspan=5)
            ttk.Button(cal_frame, text=">", command=next_month).grid(row=0,column=6)
            for i,d in enumerate(['日','一','二','三','四','五','六']): ttk.Label(cal_frame, text=d).grid(row=1,column=i)
            for wk,week in enumerate(calendar.monthcalendar(y,m)):
                for idx,day in enumerate(week):
                    if day:
                        ttk.Button(cal_frame,text=str(day),width=3,
                                   command=lambda d=day: select_day(d)).grid(row=wk+2,column=idx)
        today = datetime.today()
        cur_year = tk.IntVar(value=today.year)
        cur_month = tk.IntVar(value=today.month)
        top = Toplevel(self.root); top.title("选择日期"); top.resizable(False,False)
        cal_frame = ttk.Frame(top,padding=10); cal_frame.pack(); update_calendar()
        ttk.Button(top, text="关闭", command=top.destroy).pack(pady=5)

    def check_today_reminders(self):
        today = datetime.today().strftime("%Y-%m-%d")
        for r in self.reminders:
            if r['date'] == today:
                messagebox.showinfo("今日提醒", r['title'])

    def on_close(self):
        result = messagebox.askyesno("最小化到托盘", "是否最小化而不是退出？")
        if result:
            self.root.withdraw()
        else:
            self.icon.stop()
            self.root.destroy()

    def show_window(self):
        self.root.deiconify()

    def create_tray_icon(self):
        img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((16, 16, 48, 48), fill=(0, 102, 204))
        draw.line((32, 32, 32, 20), fill="white", width=2)
        draw.line((32, 32, 44, 32), fill="white", width=2)
        self.icon = pystray.Icon('rem', img, '提醒事项',
            menu=pystray.Menu(
                pystray.MenuItem('打开', lambda: self.show_window()),
                pystray.MenuItem('退出', lambda: self.root.quit())
            ))
        threading.Thread(target=self.icon.run, daemon=True).start()

    def login_google(self):
        import os, json
        token_path = 'id_token.json'
        if os.path.exists(token_path):
            with open(token_path, 'r', encoding='utf-8') as f:
                token = json.load(f).get('id_token')
                try:
                    idinfo = id_token.verify_oauth2_token(token, grequests.Request())
                    raise ValueError("Token 缓存格式不完整，重新获取")
                except Exception:
                    pass  # token 失效则重新登录

        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json',
            scopes=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/drive"]
        )
        creds = flow.run_local_server(port=0)
        with open(token_path, 'w', encoding='utf-8') as f:
            json.dump({'id_token': creds.id_token, 'access_token': creds.token}, f, ensure_ascii=False, indent=2)

        self.access_token = creds.token
        self.id_token = creds.id_token
        self.auth_headers = {
            "Authorization": f"Bearer {self.id_token}",
            "X-Access-Token": self.access_token
        }
        return self.auth_headers

def main():
    root = ttk.Window(themename="minty")
    root.geometry("900x620")
    ReminderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()

