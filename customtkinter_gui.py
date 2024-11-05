import customtkinter as ctk
from tkinter import filedialog, messagebox, Text, END
import configparser
import os
import webbrowser
from core.utils import logger
import threading
import asyncio
from core.utils.bot import Bot
from core.captcha import CaptchaService
from PIL import Image, ImageTk
import csv

CONFIG_FILE = "data/settings.ini"

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("dark-blue")

class BotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NodePay Bot 汉化作者雪糕战神推特用户@Hy78516012")
        self.root.geometry("900x700")
        # self.root.resizable(True, True)
        try:
            favicon = ImageTk.PhotoImage(Image.open("core/static/faviconV2.png"))
            self.root.iconphoto(True, favicon)
        except Exception as e:
            logger.error(f"无法加载图标: {e}")
        self.config = configparser.ConfigParser()
        self.load_settings()
        self.threads_entry = ctk.CTkEntry(self.root)
        self.captcha_service_var = ctk.StringVar(value="capmonster")
        self.captcha_api_entry = ctk.CTkEntry(self.root)
        self.ref_code_entry = ctk.CTkEntry(self.root)
        self.delay_min_entry = ctk.CTkEntry(self.root)
        self.delay_max_entry = ctk.CTkEntry(self.root)
        self.create_widgets()
        self.bot = None
        self.bot_thread = None
        self.running = False

    def create_widgets(self):
        self.root.configure(bg="#F1F3FF")
        self.main_frame = ctk.CTkFrame(self.root, fg_color="#F1F3FF")
        self.main_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # 头部框架
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="#F1F3FF")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        self.header_frame.columnconfigure(0, weight=1)
        self.header_frame.columnconfigure(1, weight=0)
        self.header_frame.columnconfigure(2, weight=0)
        self.header_frame.columnconfigure(3, weight=0)  # 为新列添加此行

        # Logo 和标题
        self.logo_frame = ctk.CTkFrame(self.header_frame, fg_color="#F1F3FF")
        self.logo_frame.grid(row=0, column=0, sticky="w")

        try:
            self.logo_image = ctk.CTkImage(light_image=Image.open("core/static/logo.png"), size=(60, 60))
            self.logo_label = ctk.CTkLabel(self.logo_frame, image=self.logo_image, text="")
            self.logo_label.pack(side="left", padx=(0, 10))
        except Exception as e:
            logger.error(f"无法加载 logo: {e}")

        self.nodepay_label = ctk.CTkLabel(
            self.logo_frame,
            text="NodePay+",
            font=("Helvetica", 24, "bold"),
            fg_color="#F1F3FF"
        )
        self.nodepay_label.pack(side="left")

        # 水印按钮
        button_style = {
            "fg_color": "#593FDE",
            "hover_color": "#452CC6",
            "corner_radius": 20,
            "border_width": 2,
            "border_color": "#FFFFFF",
            "text_color": "white",
            "font": ("Helvetica", 12)
        }

        self.instructions_button = ctk.CTkButton(
            self.header_frame,
            text="我的推特主页",
            command=lambda: self.open_link("https://x.com/Hy78516012"),
            **button_style
        )
        self.instructions_button.grid(row=0, column=1, padx=(0, 10), sticky="e")

        self.web3_products_button = ctk.CTkButton(
            self.header_frame,
            text="原作者Github",
            command=lambda: self.open_link("https://github.com/MsLolita/Nodepay_plus"),
            **button_style
        )
        self.web3_products_button.grid(row=0, column=2, padx=(0, 10), sticky="e")

        self.enjoyer_button = ctk.CTkButton(
            self.header_frame,
            text="汉化作者Github",
            command=lambda: self.open_link("https://github.com/GzGod/"),
            **button_style
        )
        self.enjoyer_button.grid(row=0, column=3, padx=(0, 10), sticky="e")

        # 主内容框架
        self.content_frame = ctk.CTkFrame(self.main_frame, fg_color="#FFFFFF", corner_radius=20)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        self.main_frame.rowconfigure(1, weight=1)
        self.main_frame.columnconfigure(0, weight=1)

        # 文件选择框架
        self.file_frame = ctk.CTkFrame(self.content_frame, fg_color="#FFFFFF")
        self.file_frame.pack(fill="x", padx=20, pady=(20, 10))

        self.accounts_label, self.accounts_button = self.create_file_selection("账户文件:", self.load_accounts_file)
        self.proxies_label, self.proxies_button = self.create_file_selection("代理文件:", self.load_proxies_file)

        # 输入框架
        self.input_frame = ctk.CTkFrame(self.content_frame, fg_color="#FFFFFF")
        self.input_frame.pack(fill="x", padx=20, pady=10)

        # 创建输入字段的网格布局
        self.input_frame.columnconfigure(1, weight=1)
        self.input_frame.columnconfigure(3, weight=1)

        # 验证码和 API Key 在同一行
        self.captcha_label, self.captcha_menu = self.create_input_field("验证码:", ctk.CTkOptionMenu(
            self.input_frame,
            variable=self.captcha_service_var,
            values=["capmonster"],  # "2captcha", "anticaptcha", "capsolver",
            width=120,
            text_color="#000",
        ))
        self.captcha_label.grid(row=0, column=0, sticky="w", pady=5, padx=(0, 5))
        self.captcha_menu.grid(row=0, column=1, sticky="w", pady=5)

        self.captcha_api_label, self.captcha_api_entry = self.create_input_field("API Key:", ctk.CTkEntry(self.input_frame, width=100))
        self.captcha_api_label.grid(row=0, column=2, sticky="w", pady=5, padx=(0, 5))
        self.captcha_api_entry.grid(row=0, column=3, sticky="ew", pady=5)

        # 线程和隐藏推荐码切换按钮在同一行
        self.threads_label, self.threads_entry = self.create_input_field("线程:", ctk.CTkEntry(self.input_frame, width=60))
        self.threads_label.grid(row=1, column=0, sticky="w", pady=5)
        self.threads_entry.grid(row=1, column=1, sticky="w", pady=5)

        self.toggle_ref_code_button = ctk.CTkButton(
            self.input_frame,
            text="⋮",  # 垂直省略号字符
            command=self.toggle_ref_code_visibility,
            width=5,
            height=5,
            corner_radius=25,
            fg_color="#FFFFFF",  # 改为非常浅的颜色
            text_color="#A0A0A0",  # 改为浅灰色
            hover_color="#E9E4FF",
            font=("Helvetica", 14, "bold")
        )
        self.toggle_ref_code_button.grid(row=1, column=1, sticky="e", pady=5, padx=(0, 5))

        self.ref_code_label, self.ref_code_entry = self.create_input_field("推荐码:", ctk.CTkEntry(self.input_frame, width=100))
        self.ref_code_label.grid(row=1, column=2, sticky="w", pady=5, padx=(0, 10))
        self.ref_code_entry.grid(row=1, column=3, sticky="ew", pady=5)

        # 初始隐藏推荐码输入
        self.ref_code_label.grid_remove()
        self.ref_code_entry.grid_remove()

        # 在线程输入后添加延迟输入
        self.delay_label = ctk.CTkLabel(
            self.input_frame,
            text="延迟（秒）:",
            font=("Helvetica", 14),
            fg_color="#FFFFFF",
            text_color="#2E3A59"
        )
        self.delay_label.grid(row=2, column=0, sticky="w", pady=5, padx=(0, 5))

        self.delay_min_entry = ctk.CTkEntry(self.input_frame, width=60)
        self.delay_min_entry.grid(row=2, column=1, sticky="w", pady=5)

        self.delay_to_label = ctk.CTkLabel(
            self.input_frame,
            text="到",
            font=("Helvetica", 14),
            fg_color="#FFFFFF",
            text_color="#2E3A59"
        )
        self.delay_to_label.grid(row=2, column=1, sticky="w", pady=5, padx=(65, 0))

        self.delay_max_entry = ctk.CTkEntry(self.input_frame, width=60)
        self.delay_max_entry.grid(row=2, column=1, sticky="w", pady=5, padx=(90, 0))

        # Buttons frame
        self.buttons_frame = ctk.CTkFrame(self.content_frame, fg_color="#FFFFFF")
        self.buttons_frame.pack(fill="x", padx=20, pady=(10, 20))

        main_button_style = {
            "fg_color": "#4A55A2",
            "hover_color": "#3D478F",
            "corner_radius": 10,
            "border_width": 0,
            "font": ("Helvetica", 14, "bold"),
            "text_color": "white"
        }

        earnings_button_style = {
            "fg_color": "#E9E4FF",  # Light purple background
            "hover_color": "#D6D6F5",  # Slightly darker on hover
            "corner_radius": 8,
            "border_width": 1,
            "border_color": "#593FDE",  # Purple border
            "font": ("Helvetica", 12),  # Smaller font
            "text_color": "#593FDE",  # Purple text
            "width": 100,  # Fixed width
            "height": 28  # Smaller height
        }

        self.register_button = ctk.CTkButton(
            self.buttons_frame,
            text="注册账户",
            command=self.register_accounts,
            **main_button_style
        )
        self.register_button.pack(side="left", padx=(0, 10), expand=True, fill="x")

        self.mining_button = ctk.CTkButton(
            self.buttons_frame,
            text="开始工作",
            command=self.start_mining,
            **main_button_style
        )
        self.mining_button.pack(side="left", padx=(0, 10), expand=True, fill="x")

        self.stop_button = ctk.CTkButton(
            self.buttons_frame,
            text="停止工作",
            command=self.stop_bot,
            **main_button_style
        )
        self.stop_button.pack(side="left", padx=(0, 10), expand=True, fill="x")

        # Add View Earnings button with different style
        self.view_earnings_button = ctk.CTkButton(
            self.buttons_frame,
            text="查看收益",
            command=self.view_earnings,
            **earnings_button_style
        )
        self.view_earnings_button.pack(side="left", expand=False)  # Changed to expand=False

        # Log frame
        self.log_frame = ctk.CTkFrame(self.content_frame, fg_color="#FFFFFF")
        self.log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.log_box = Text(
            self.log_frame,
            wrap="word",
            bg="#F8F9FA",
            fg="#2E3A59",
            font=("Consolas", 12),
            relief="flat",
            borderwidth=0,
            highlightthickness=0
        )
        self.log_box.pack(fill="both", expand=True, padx=10, pady=10)

        # Apply styles
        self.beautify_ui()

        # Load saved values
        self.load_values()

    def create_file_selection(self, label_text, command):
        frame = ctk.CTkFrame(self.file_frame, fg_color="#FFFFFF")
        frame.pack(fill="x", pady=5)

        label = ctk.CTkLabel(
            frame,
            text=label_text,
            font=("Helvetica", 14),
            fg_color="#FFFFFF"
        )
        label.pack(side="left")

        button = ctk.CTkButton(
            frame,
            text="选择文件",
            command=command,
            fg_color="#E9E4FF",
            text_color="#2E3A59",
            hover_color="#D6D6F5",
            corner_radius=10,
            width=200,
            font=("Helvetica", 14)
        )
        button.pack(side="right")

        return label, button

    def create_input_field(self, label_text, widget):
        label = ctk.CTkLabel(
            self.input_frame,
            text=label_text,
            font=("Helvetica", 14),
            fg_color="#FFFFFF",
            text_color="#2E3A59"
        )

        if isinstance(widget, ctk.CTkEntry):
            widget.configure(
                height=30,
                font=("Helvetica", 14),
                fg_color="#FFFFFF",
                border_color="#4A55A2",
                border_width=1,
                corner_radius=5
            )
        elif isinstance(widget, ctk.CTkOptionMenu):
            widget.configure(
                height=30,
                font=("Helvetica", 14),
                fg_color="#FFFFFF",
                button_color="#4A55A2",
                button_hover_color="#3D478F",
                dropdown_fg_color="#FFFFFF",
                dropdown_hover_color="#E9E4FF",
                corner_radius=5
            )

        return label, widget

    def open_link(self, url):
        webbrowser.open(url)

    def on_mousewheel(self, event):
        if os.name == 'nt':
            self.log_box.yview_scroll(int(-1*(event.delta/120)), "units")
        elif event.num == 4:
            self.log_box.yview_scroll(-1, "units")
        elif event.num == 5:
            self.log_box.yview_scroll(1, "units")

    def load_accounts_file(self):
        file_path = filedialog.askopenfilename(title="Select Accounts File")
        if file_path:
            self.accounts_path = file_path
            filename = os.path.basename(file_path)
            self.accounts_button.configure(text=filename)

    def load_proxies_file(self):
        file_path = filedialog.askopenfilename(title="Select Proxies File")
        if file_path:
            self.proxies_path = file_path
            filename = os.path.basename(file_path)
            self.proxies_button.configure(text=filename)

    def save_settings(self):
        ref_codes = [code.strip() for code in self.ref_code_entry.get().split(',') if code.strip()]
        self.config['DEFAULT'] = {
            'AccountsFile': getattr(self, 'accounts_path', ''),
            'ProxiesFile': getattr(self, 'proxies_path', ''),
            'ReferralCodes': ','.join(ref_codes),
            'Threads': self.threads_entry.get(),
            'CaptchaService': self.captcha_service_var.get(),
            'CaptchaAPIKey': self.captcha_api_entry.get(),
            'DelayMin': self.delay_min_entry.get(),
            'DelayMax': self.delay_max_entry.get()
        }
        with open(CONFIG_FILE, 'w') as configfile:
            self.config.write(configfile)

    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            self.config.read(CONFIG_FILE)
        else:
            self.config['DEFAULT'] = {
                'AccountsFile': '',
                'ProxiesFile': '',
                'ReferralCodes': '',
                'Threads': '5',
                'CaptchaService': 'capmonster',
                'CaptchaAPIKey': '',
                'DelayMin': '1',
                'DelayMax': '2'
            }

    def load_values(self):
        accounts = self.config['DEFAULT'].get('AccountsFile', '')
        proxies = self.config['DEFAULT'].get('ProxiesFile', '')
        self.accounts_path = accounts
        self.proxies_path = proxies

        ref_codes = self.config['DEFAULT'].get('ReferralCodes', '')
        self.ref_code_entry.delete(0, 'end')
        self.ref_code_entry.insert(0, ref_codes)
        threads = self.config['DEFAULT'].get('Threads', '5')
        self.threads_entry.insert(0, threads)
        self.captcha_service_var.set(self.config['DEFAULT'].get('CaptchaService', 'capmonster'))
        self.captcha_api_entry.insert(0, self.config['DEFAULT'].get('CaptchaAPIKey', ''))
        self.delay_min_entry.insert(0, self.config['DEFAULT'].get('DelayMin', '1'))
        self.delay_max_entry.insert(0, self.config['DEFAULT'].get('DelayMax', '2'))

        if self.accounts_path:
            accounts_filename = os.path.basename(self.accounts_path)
            self.accounts_button.configure(text=accounts_filename)
        if self.proxies_path:
            proxies_filename = os.path.basename(self.proxies_path)
            self.proxies_button.configure(text=proxies_filename)

    def setup_logger(self):
        logger.remove()
        
        # Configure text styles with bigger font and colors
        self.log_box.tag_configure("INFO", foreground="black", font=("Consolas", 14))
        self.log_box.tag_configure("ERROR", foreground="red", font=("Consolas", 14, "bold"))
        self.log_box.tag_configure("WARNING", foreground="orange", font=("Consolas", 14))
        self.log_box.tag_configure("DEBUG", foreground="purple", font=("Consolas", 14))
        self.log_box.tag_configure("SUCCESS", foreground="green", font=("Consolas", 14, "bold"))

        def gui_log_sink(message):
            log_text = message.strip()
            level = message.record["level"].name
            if level == "INFO":
                tag = "INFO"
            elif level == "ERROR":
                tag = "ERROR"
            elif level == "WARNING":
                tag = "WARNING"
            elif level == "DEBUG":
                tag = "DEBUG"
            elif level == "SUCCESS":
                tag = "SUCCESS"
            else:
                tag = "INFO"
            self.root.after(0, self.append_log, log_text, tag)

        logger.add(gui_log_sink, format="{time} {level} {message}", level="DEBUG")

    def append_log(self, log_text, tag):
        self.log_box.configure(state="normal")
        self.log_box.insert(END, log_text + "\n", tag)
        self.log_box.configure(state="disabled")
        self.log_box.see(END)

    def register_accounts(self):
        if not self.validate_inputs():
            return
        self.save_settings()
        if not self.running:
            ref_codes = [code.strip() for code in self.ref_code_entry.get().split(',') if code.strip()]
            delay_min = float(self.delay_min_entry.get())
            delay_max = float(self.delay_max_entry.get())
            self.bot = Bot(
                account_path=self.accounts_path,
                proxy_path=self.proxies_path,
                threads=int(self.threads_entry.get()),
                ref_codes=ref_codes,
                captcha_service=CaptchaService(api_key=self.captcha_api_entry.get()),
                delay_range=(delay_min, delay_max)
            )
            self.bot_thread = threading.Thread(target=asyncio.run, args=(self.bot.start_registration(),), daemon=True)
            self.bot_thread.start()
            self.running = True
            logger.info("Started account registration with slow start.")

    def start_mining(self):
        if not self.validate_inputs():
            return
        self.save_settings()
        if not self.running:
            ref_codes = [code.strip() for code in self.ref_code_entry.get().split(',') if code.strip()]
            delay_min = float(self.delay_min_entry.get())
            delay_max = float(self.delay_max_entry.get())
            self.bot = Bot(
                account_path=self.accounts_path,
                proxy_path=self.proxies_path,
                threads=int(self.threads_entry.get()),
                ref_codes=ref_codes,
                captcha_service=CaptchaService(api_key=self.captcha_api_entry.get()),
                delay_range=(delay_min, delay_max)
            )
            self.bot_thread = threading.Thread(target=asyncio.run, args=(self.bot.start_mining(),), daemon=True)
            self.bot_thread.start()
            self.running = True

    def stop_bot(self):
        if self.running and self.bot:
            self.bot.stop()
            self.running = False
            logger.info("Bot stopped.")
            if self.bot_thread:
                self.bot_thread.join(timeout=1)  # Wait for the thread to finish
                # if self.bot_thread.is_alive():
                #     logger.warning("Bot thread did not stop in time.")
        else:
            logger.warning("Bot is not running.")

    def validate_inputs(self):
        if not getattr(self, 'accounts_path', ''):
            logger.error("Error: 没有找到账户文件!")
            messagebox.showerror("Error", "没有找到账户文件!")
            return False
        if not getattr(self, 'proxies_path', ''):
            logger.error("Error: 没有找到代理文件!")
            messagebox.showerror("Error", "没有找到代理文件!")
            return False
        if not self.captcha_api_entry.get():
            logger.error("Error: Captcha API key 错误!")
            messagebox.showerror("Error", "Captcha API key 错误!")
            return False
        try:
            threads = int(self.threads_entry.get())
            if threads <= 0:
                raise ValueError
        except ValueError:
            logger.error("Error: 线程数必须是正整数!")
            messagebox.showerror("Error", "线程数必须是正整数!")
            return False
        try:
            delay_min = float(self.delay_min_entry.get())
            delay_max = float(self.delay_max_entry.get())
            if delay_min < 0 or delay_max < 0 or delay_min > delay_max:
                raise ValueError
        except ValueError:
            logger.error("Error: Invalid delay range!")
            messagebox.showerror("Error", "延迟范围无效！请输入有效的正数, with min <= max.")
            return False
        return True

    def beautify_ui(self):
        self.root.configure(bg="#F1F3FF")
        self.main_frame.configure(fg_color="#F1F3FF")

        # Update entry styles
        entry_style = {
            "fg_color": "#FFFFFF",
            "border_color": "#4A55A2",
            "border_width": 1,
            "corner_radius": 10
        }

        for entry in [self.threads_entry, self.captcha_api_entry, self.ref_code_entry, self.delay_min_entry, self.delay_max_entry]:
            entry.configure(**entry_style)

        # Update label styles
        label_style = {
            "font": ("Helvetica", 14),
            "text_color": "#2E3A59"
        }

        for label in [self.accounts_label, self.proxies_label, self.threads_label, self.captcha_label, self.captcha_api_label, self.ref_code_label, self.delay_label]:
            label.configure(**label_style)

        # Update log box style with bigger font
        self.log_box.configure(
            bg="#F8F9FA",
            fg="#2E3A59",
            font=("Consolas", 14),  # Increased font size
            relief="flat",
            padx=10,
            pady=10
        )

    def toggle_ref_code_visibility(self):
        if self.ref_code_label.winfo_viewable():
            self.ref_code_label.grid_remove()
            self.ref_code_entry.grid_remove()
            self.toggle_ref_code_button.configure(text="⋮")
        else:
            self.ref_code_label.grid()
            self.ref_code_entry.grid()
            self.toggle_ref_code_button.configure(text="×")

    def view_earnings(self):
        try:
            # Store earnings window as class attribute
            if hasattr(self, 'earnings_window') and self.earnings_window.winfo_exists():
                self.earnings_window.lift()  # Bring window to front if it exists
                return

            with open('data/earnings.csv', 'r', newline='') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                earnings_data = list(reader)

            # Create a new window to display earnings
            self.earnings_window = ctk.CTkToplevel()
            self.earnings_window.title("Account Earnings")
            self.earnings_window.geometry("500x300")
            self.earnings_window.configure(fg_color="#F1F3FF")
            
            # Position the window to the right of the main window
            main_x = self.root.winfo_x()
            main_y = self.root.winfo_y()
            self.earnings_window.geometry(f"+{main_x + self.root.winfo_width() + 10}+{main_y}")

            # Create a frame for the content
            content_frame = ctk.CTkFrame(self.earnings_window, fg_color="#FFFFFF", corner_radius=10)
            content_frame.pack(fill="both", expand=True, padx=10, pady=10)

            # Create a text widget to display the data
            self.earnings_text = Text(
                content_frame,
                wrap="none",
                bg="#FFFFFF",
                fg="#2E3A59",
                font=("Consolas", 12),
                relief="flat",
                padx=10,
                pady=10,
                height=15
            )
            self.earnings_text.pack(fill="both", expand=True, padx=5, pady=5)

            # Add scrollbars
            y_scrollbar = ctk.CTkScrollbar(content_frame, command=self.earnings_text.yview)
            y_scrollbar.pack(side="right", fill="y")
            x_scrollbar = ctk.CTkScrollbar(content_frame, command=self.earnings_text.xview, orientation="horizontal")
            x_scrollbar.pack(side="bottom", fill="x")
            self.earnings_text.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)

            # Configure tags for styling
            self.earnings_text.tag_configure("header", font=("Consolas", 12, "bold"), foreground="#4A55A2")
            self.earnings_text.tag_configure("separator", foreground="#4A55A2")
            self.earnings_text.tag_configure("data", font=("Consolas", 11))
            self.earnings_text.tag_configure("earnings", foreground="#593FDE", font=("Consolas", 11, "bold"))

            def update_earnings():
                if not self.earnings_window.winfo_exists():
                    return
                
                try:
                    with open('data/earnings.csv', 'r', newline='') as f:
                        reader = csv.reader(f)
                        next(reader)  # Skip header
                        current_data = list(reader)

                    self.earnings_text.configure(state="normal")
                    self.earnings_text.delete("1.0", "end")
                    
                    # Format and display the data
                    self.earnings_text.insert("1.0", f"{'Email':<35} {'Last Update':<20} {'Total Earnings':<15}\n", "header")
                    self.earnings_text.insert("2.0", "─" * 70 + "\n", "separator")
                    
                    for email, last_update, total_earning in current_data:
                        line = f"{email:<35} {last_update:<20} "
                        self.earnings_text.insert("end", line, "data")
                        self.earnings_text.insert("end", f"{total_earning:>15}\n", "earnings")

                    self.earnings_text.configure(state="disabled")
                    
                    # Schedule next update
                    self.earnings_window.after(5000, update_earnings)  # Update every 5 seconds
                except Exception as e:
                    logger.error(f"Error updating earnings: {e}")

            # Initial display
            update_earnings()

            # Make the window stay on top
            self.earnings_window.attributes('-topmost', True)
            self.earnings_window.update()

        except FileNotFoundError:
            messagebox.showinfo("No Data", "目前还没有可用的收益数据.")
        except Exception as e:
            logger.error(f"Error viewing earnings: {e}")
            messagebox.showerror("Error", f"无法加载收益数据: {e}")

if __name__ == "__main__":
    root = ctk.CTk()
    app = BotGUI(root)
    app.setup_logger()
    root.mainloop()
