# -*- coding: utf-8 -*-
"""
多角色版 DeepSeek API 调用工具 - 优化修复版（界面调整）
界面布局修改：
1. 将token统计、角色管理放在第一行末尾
2. 将"多角色协同"、"新建角色"、"关闭当前"、"搜索标签页"放在第二行
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import requests
import json
import threading
import os
import time
from datetime import datetime
import queue


class DeepSeekAPIMultiTabTool:
    """多标签页DeepSeek API工具主类"""

    def __init__(self, root):
        self.root = root
        self.root.title("DeepSeek API 调用工具 - 多角色协同版 v0.5.012109")
        self.root.geometry("1400x950")

        # 设置窗口图标和主题
        try:
            self.root.iconbitmap(default=None)
        except:
            pass

        # 设置样式
        self.setup_styles()

        # 全局API配置（在所有标签页间共享）
        self.api_key = tk.StringVar()
        self.base_url = tk.StringVar(value="https://api.deepseek.com/v1/chat/completions")
        self.timeout = tk.IntVar(value=60)
        self.stream_response = tk.BooleanVar(value=True)

        # 标签页管理
        self.tabs = {}  # tab_id: SessionTab or MultiRoleTab
        self.current_tab_id = None
        self.next_tab_id = 1  # 下一个标签页ID

        # 全局角色配置管理
        self.global_roles = {}  # 全局角色配置池
        self.role_file = "global_roles.json"

        # 状态变量
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

        # API日志文件
        self.api_log_dir = "api_logs"
        if not os.path.exists(self.api_log_dir):
            os.makedirs(self.api_log_dir)

        # 创建界面
        self.create_widgets()
        self.load_global_roles()

        # 添加一个默认角色到全局角色池
        self.add_default_roles()

    def setup_styles(self):
        """设置样式"""
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except:
            pass

        # 主标题样式
        style.configure("Title.TLabel", font=("微软雅黑", 12, "bold"), foreground="#2c3e50")

        # 分组框样式
        style.configure("Section.TLabelframe", font=("微软雅黑", 10, "bold"), foreground="#2c3e50")
        style.configure("Section.TLabelframe.Label", font=("微软雅黑", 10, "bold"))

        # 多角色分组框样式
        style.configure("MultiRole.TLabelframe", font=("微软雅黑", 10, "bold"), foreground="#2c3e50")
        style.configure("MultiRole.TLabelframe.Label", font=("微软雅黑", 10, "bold"))

        # 状态标签样式
        style.configure("Status.TLabel", font=("微软雅黑", 9), foreground="#3498db")

        # Token统计样式
        style.configure("Token.TLabel", font=("Consolas", 10, "bold"), foreground="#2c3e50")

        # 流式输出样式
        style.configure("Streaming.TLabel", font=("微软雅黑", 9), foreground="#27ae60")

        # 按钮样式
        style.configure("Primary.TButton", font=("微软雅黑", 9, "bold"))
        style.map("Primary.TButton",
                  foreground=[('active', '#ffffff'), ('!active', '#2c3e50')],
                  background=[('active', '#3498db'), ('!active', '#ecf0f1')])

        # 输入框样式
        style.configure("TEntry", font=("微软雅黑", 10))
        style.configure("TCombobox", font=("微软雅黑", 10))

        # 标签页样式
        style.configure("TNotebook", background="#ecf0f1")
        style.configure("TNotebook.Tab", font=("微软雅黑", 10), background="#bdc3c7", foreground="#2c3e50")
        style.map("TNotebook.Tab",
                  background=[('selected', '#ffffff'), ('!selected', '#bdc3c7')],
                  foreground=[('selected', '#2c3e50'), ('!selected', '#7f8c8d')])

        # 滚动条样式
        style.configure("TScrollbar", background="#bdc3c7")
        style.map("TScrollbar",
                  background=[('active', '#3498db'), ('!active', '#bdc3c7')],
                  troughcolor=[('active', '#ecf0f1'), ('!active', '#ecf0f1')])

    def add_default_roles(self):
        """添加默认角色到全局角色池"""
        if not self.global_roles:
            default_roles = {
                "编程助手": {
                    "name": "编程助手",
                    "system_prompt": "你是一个专业的编程助手，精通多种编程语言和开发框架。请帮助用户解决编程问题，提供代码示例和最佳实践建议。",
                    "temperature": 0.7,
                    "max_tokens": 4000,
                    "deep_thought": False
                },
                "创意写作": {
                    "name": "创意写作",
                    "system_prompt": "你是一个富有创意的写作助手，擅长各种文学体裁和创意表达。请帮助用户进行创意写作，提供灵感和改进建议。",
                    "temperature": 0.9,
                    "max_tokens": 4000,
                    "deep_thought": False
                },
                "学术研究": {
                    "name": "学术研究",
                    "system_prompt": "你是一个专业的学术研究助手，熟悉各学科的研究方法和学术规范。请帮助用户进行学术研究，提供文献分析和研究方法建议。",
                    "temperature": 0.6,
                    "max_tokens": 4000,
                    "deep_thought": True
                },
                "翻译助手": {
                    "name": "翻译助手",
                    "system_prompt": "你是一个专业的翻译助手，精通多国语言和翻译技巧。请帮助用户进行准确、流畅的翻译工作。",
                    "temperature": 0.5,
                    "max_tokens": 2000,
                    "deep_thought": False
                }
            }
            self.global_roles.update(default_roles)
            self.save_all_roles()

    def create_widgets(self):
        """创建主界面组件"""
        # 创建主容器
        main_container = ttk.Frame(self.root, padding="10")
        main_container.pack(fill=tk.BOTH, expand=True)

        # 创建顶部工具栏（分为两行）
        self.create_multi_line_toolbar(main_container)

        # 标签页区域
        tab_frame = self.create_tab_region(main_container)
        tab_frame.pack(fill=tk.BOTH, expand=True)

    def create_multi_line_toolbar(self, parent):
        """创建多行工具栏（调整布局）"""
        # 第一行：API配置、Token统计和角色管理
        toolbar_row1 = ttk.Frame(parent)
        toolbar_row1.pack(fill=tk.X, pady=(0, 5))

        # API配置区域（左侧）
        api_frame = ttk.LabelFrame(toolbar_row1, text="🔑 API配置", padding="5")
        api_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        # API Key
        ttk.Label(api_frame, text="API Key:").pack(side=tk.LEFT)
        self.api_entry = ttk.Entry(api_frame, textvariable=self.api_key, width=35, show="*")
        self.api_entry.pack(side=tk.LEFT, padx=(5, 5))

        # 显示/隐藏API Key按钮
        def toggle_api_visibility():
            if self.api_entry.cget('show') == '*':
                self.api_entry.config(show='')
                toggle_btn.config(text='隐藏')
            else:
                self.api_entry.config(show='*')
                toggle_btn.config(text='显示')

        toggle_btn = ttk.Button(api_frame, text="显示", command=toggle_api_visibility, width=6)
        toggle_btn.pack(side=tk.LEFT)

        # Base URL
        ttk.Label(api_frame, text="  Base URL:").pack(side=tk.LEFT)
        ttk.Entry(api_frame, textvariable=self.base_url, width=30).pack(side=tk.LEFT, padx=(5, 5))

        # Timeout
        ttk.Label(api_frame, text="Timeout:").pack(side=tk.LEFT)
        ttk.Spinbox(api_frame, from_=10, to=300, textvariable=self.timeout, width=8).pack(side=tk.LEFT, padx=(5, 0))

        # 流式响应开关
        ttk.Checkbutton(api_frame, text="流式响应", variable=self.stream_response).pack(side=tk.LEFT, padx=(10, 0))

        # Token统计（第一行中间）
        token_frame = ttk.LabelFrame(toolbar_row1, text="📊 Token统计", padding="5")
        token_frame.pack(side=tk.LEFT, fill=tk.X, padx=(0, 10))

        # Token统计内容
        token_content = ttk.Frame(token_frame)
        token_content.pack()

        self.total_prompt_label = ttk.Label(token_content, text="0", font=("Consolas", 10, "bold"))
        self.total_prompt_label.pack(side=tk.LEFT)
        ttk.Label(token_content, text=" / ").pack(side=tk.LEFT)
        self.total_completion_label = ttk.Label(token_content, text="0", font=("Consolas", 10, "bold"))
        self.total_completion_label.pack(side=tk.LEFT)
        ttk.Label(token_content, text=" (输入/输出)").pack(side=tk.LEFT)

        # 刷新按钮
        ttk.Button(token_content, text="刷新", command=self.update_global_token_display,
                   width=6).pack(side=tk.LEFT, padx=(10, 0))

        # 角色管理按钮（第一行右侧）
        role_btn_frame = ttk.LabelFrame(toolbar_row1, text="👤 角色管理", padding="5")
        role_btn_frame.pack(side=tk.RIGHT)

        role_buttons = ttk.Frame(role_btn_frame)
        role_buttons.pack()

        ttk.Button(role_buttons, text="导入角色", command=self.import_global_roles,
                   width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(role_buttons, text="导出角色", command=self.export_global_roles,
                   width=10).pack(side=tk.LEFT, padx=2)

        # 第二行：标签页控制按钮
        toolbar_row2 = ttk.Frame(parent)
        toolbar_row2.pack(fill=tk.X, pady=(0, 10))

        # 标签页控制按钮区域
        tab_control_frame = ttk.LabelFrame(toolbar_row2, text="📑 标签页管理", padding="5")
        tab_control_frame.pack(fill=tk.X)

        # 按钮框架
        button_frame = ttk.Frame(tab_control_frame)
        button_frame.pack(fill=tk.X)

        # 新建角色按钮
        ttk.Button(button_frame, text="👤 新建角色",
                   command=self.create_new_role_tab, width=12, style="Primary.TButton").pack(side=tk.LEFT, padx=(0, 10))

        # 多角色协同按钮
        ttk.Button(button_frame, text="🤝 多角色协同",
                   command=self.add_optimized_multi_role_tab, width=15, style="Primary.TButton").pack(side=tk.LEFT,
                                                                                                      padx=(0, 10))

        # 关闭当前标签页按钮
        ttk.Button(button_frame, text="🗑️ 关闭当前",
                   command=self.close_current_tab, width=12).pack(side=tk.LEFT, padx=(0, 10))

        # 搜索标签页按钮
        ttk.Button(button_frame, text="🔍 搜索标签页",
                   command=self.search_tabs, width=12).pack(side=tk.LEFT, padx=(0, 10))

        # 标签页状态
        self.tab_status_label = ttk.Label(button_frame, text="共 0 个标签页")
        self.tab_status_label.pack(side=tk.LEFT, padx=(20, 0))

    def create_tab_region(self, parent):
        """创建标签页区域"""
        tab_frame = ttk.Frame(parent)

        # 标签页控件
        self.notebook = ttk.Notebook(tab_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 绑定标签页切换事件
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # 添加提示标签（当没有标签页时显示）
        self.empty_tab_label = ttk.Label(tab_frame, text="点击'新建角色'或'多角色协同'开始",
                                         font=("微软雅黑", 12), foreground="gray")
        self.empty_tab_label.pack(fill=tk.BOTH, expand=True)

        return tab_frame

    def update_tab_title(self, tab_id, role_name):
        """更新标签页标题"""
        if tab_id in self.tabs:
            tab = self.tabs[tab_id]
            # 更新标签页名称
            new_title = f"标签页 {tab_id}: {role_name}"
            self.notebook.tab(tab.parent, text=new_title)

    def create_new_role_tab(self):
        """创建新的角色标签页（修复版）"""
        # 检查是否有全局角色
        if not self.global_roles:
            self.add_default_roles()

        # 显示角色选择对话框
        role_names = list(self.global_roles.keys())

        if not role_names:
            messagebox.showerror("错误", "没有可用的角色")
            return

        # 创建选择对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("选择角色")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()

        # 角色列表
        listbox_frame = ttk.Frame(dialog, padding="10")
        listbox_frame.pack(fill=tk.BOTH, expand=True)

        listbox = tk.Listbox(listbox_frame, font=("微软雅黑", 11))
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.config(yscrollcommand=scrollbar.set)

        # 填充角色列表
        for role_name in role_names:
            listbox.insert(tk.END, role_name)

        # 按钮区域
        button_frame = ttk.Frame(dialog, padding="10")
        button_frame.pack(fill=tk.X)

        def on_select():
            selection = listbox.curselection()
            if selection:
                role_name = listbox.get(selection[0])
                role_config = self.global_roles.get(role_name)
                if role_config:
                    self.create_new_tab(role_name, role_config)
                    dialog.destroy()
            else:
                messagebox.showwarning("警告", "请选择一个角色")

        def on_cancel():
            dialog.destroy()

        ttk.Button(button_frame, text="选择", command=on_select, width=10).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="取消", command=on_cancel, width=10).pack(side=tk.LEFT)

    def create_new_tab(self, role_name="新助手", role_config=None):
        """创建新的会话标签页"""
        tab_id = self.next_tab_id
        self.next_tab_id += 1

        tab_frame = ttk.Frame(self.notebook)

        # 创建会话标签页
        session_tab = SessionTab(
            parent=tab_frame,
            tab_id=tab_id,
            global_api_key=self.api_key,
            global_base_url=self.base_url,
            global_timeout=self.timeout,
            global_stream_response=self.stream_response,
            global_roles=self.global_roles,
            on_token_update=self.on_tab_token_update,
            on_save_role=self.save_role_to_global,
            on_load_role=self.load_role_from_global,
            on_update_tab_title=lambda rn: self.update_tab_title(tab_id, rn),
            log_dir=self.api_log_dir
        )

        # 设置初始角色
        if role_config:
            session_tab.set_role_config(role_config)
        else:
            # 如果没有指定角色配置，使用第一个全局角色
            if self.global_roles:
                first_role_name = list(self.global_roles.keys())[0]
                role_config = self.global_roles[first_role_name]
                session_tab.set_role_config(role_config)

        session_tab.pack(fill=tk.BOTH, expand=True)

        # 添加到标签页
        tab_name = f"标签页 {tab_id}: {role_name}"
        self.notebook.add(tab_frame, text=tab_name)
        self.tabs[tab_id] = session_tab

        # 隐藏空标签页提示
        if self.empty_tab_label.winfo_ismapped():
            self.empty_tab_label.pack_forget()

        # 切换到新标签页
        self.notebook.select(tab_frame)
        self.current_tab_id = tab_id

        # 更新状态
        self.update_tab_status()

    def add_optimized_multi_role_tab(self):
        """添加优化版多角色协同标签页"""
        # 检查是否有足够的角色
        if len(self.global_roles) < 2:
            messagebox.showwarning("警告", "需要至少2个角色才能创建多角色协同")
            return

        tab_id = self.next_tab_id
        self.next_tab_id += 1

        tab_frame = ttk.Frame(self.notebook)

        # 创建优化版多角色协同标签页
        optimized_multi_role_tab = OptimizedMultiRoleTab(
            parent=tab_frame,
            tab_id=tab_id,
            global_api_key=self.api_key,
            global_base_url=self.base_url,
            global_timeout=self.timeout,
            global_stream_response=self.stream_response,
            global_roles=self.global_roles,
            on_token_update=self.on_tab_token_update,
            on_save_role=self.save_role_to_global,
            on_load_role=self.load_role_from_global,
            on_update_tab_title=lambda rn: self.update_tab_title(tab_id, rn),
            log_dir=self.api_log_dir
        )

        optimized_multi_role_tab.pack(fill=tk.BOTH, expand=True)

        # 添加到标签页
        tab_name = f"多角色协同(优化) {tab_id}"
        self.notebook.add(tab_frame, text=tab_name)
        self.tabs[tab_id] = optimized_multi_role_tab

        # 隐藏空标签页提示
        if self.empty_tab_label.winfo_ismapped():
            self.empty_tab_label.pack_forget()

        # 切换到新标签页
        self.notebook.select(tab_frame)
        self.current_tab_id = tab_id

        # 更新状态
        self.update_tab_status()

    def close_current_tab(self):
        """关闭当前标签页"""
        if len(self.tabs) == 0:
            return

        if len(self.tabs) == 1:
            messagebox.showwarning("警告", "至少需要保留一个标签页")
            return

        current_tab = self.notebook.select()
        if not current_tab:
            return

        tab_frame = self.notebook.nametowidget(current_tab)

        # 查找对应的tab_id
        for tab_id, session_tab in self.tabs.items():
            if session_tab.parent == tab_frame:
                # 移除标签页
                self.notebook.forget(current_tab)
                del self.tabs[tab_id]

                # 保存角色配置（如果需要）
                try:
                    if hasattr(session_tab, 'get_role_config'):
                        role_config = session_tab.get_role_config()
                        role_name = role_config.get("name", f"标签页_{tab_id}")
                        if messagebox.askyesno("保存角色", f"是否保存角色配置 '{role_name}' 到全局配置？"):
                            self.save_role_to_global(role_name, role_config)
                except:
                    pass

                break

        # 更新状态
        self.update_tab_status()

        # 如果没有标签页了，显示提示
        if len(self.tabs) == 0 and not self.empty_tab_label.winfo_ismapped():
            self.empty_tab_label.pack(fill=tk.BOTH, expand=True)

    def on_tab_changed(self, event):
        """标签页切换事件处理"""
        current_tab = self.notebook.select()
        if not current_tab:
            return

        tab_frame = self.notebook.nametowidget(current_tab)

        # 查找对应的tab_id
        for tab_id, session_tab in self.tabs.items():
            if session_tab.parent == tab_frame:
                self.current_tab_id = tab_id
                # 更新全局Token显示
                self.update_global_token_display()
                break

    def on_tab_token_update(self, prompt_tokens, completion_tokens):
        """标签页Token更新回调"""
        # 累加全局Token
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.update_global_token_display()

    def update_global_token_display(self):
        """更新全局Token显示"""
        # 重新计算所有标签页的Token总和
        total_prompt = 0
        total_completion = 0

        for tab in self.tabs.values():
            if hasattr(tab, 'get_token_counts'):
                prompt, completion = tab.get_token_counts()
                total_prompt += prompt
                total_completion += completion

        self.total_prompt_tokens = total_prompt
        self.total_completion_tokens = total_completion

        self.total_prompt_label.config(text=str(total_prompt))
        self.total_completion_label.config(text=str(total_completion))

    def update_tab_status(self):
        """更新标签页状态"""
        tab_count = len(self.tabs)
        self.tab_status_label.config(text=f"共 {tab_count} 个标签页")

    def search_tabs(self):
        """搜索标签页"""
        if len(self.tabs) == 0:
            messagebox.showinfo("提示", "当前没有标签页")
            return

        search_dialog = tk.Toplevel(self.root)
        search_dialog.title("搜索标签页")
        search_dialog.geometry("500x400")
        search_dialog.transient(self.root)
        search_dialog.grab_set()

        # 搜索框
        search_frame = ttk.Frame(search_dialog, padding="10")
        search_frame.pack(fill=tk.X)

        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(5, 5))

        # 搜索结果列表
        results_frame = ttk.Frame(search_dialog)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        tree = ttk.Treeview(results_frame, columns=("标签页", "角色", "消息数", "最后时间"), show="headings")
        tree.heading("标签页", text="标签页")
        tree.heading("角色", text="角色名称")
        tree.heading("消息数", text="消息数量")
        tree.heading("最后时间", text="最后活动")

        # 设置列宽
        tree.column("标签页", width=80)
        tree.column("角色", width=120)
        tree.column("消息数", width=80)
        tree.column("最后时间", width=120)

        vsb = ttk.Scrollbar(results_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        def update_results():
            """更新搜索结果"""
            search_text = search_var.get().lower()
            tree.delete(*tree.get_children())

            for tab_id, tab in self.tabs.items():
                role_name = ""
                history = []
                last_time = "无记录"

                if hasattr(tab, 'role_name'):
                    role_name = tab.role_name.get()
                    if hasattr(tab, 'get_conversation_history'):
                        history = tab.get_conversation_history()
                elif hasattr(tab, 'tab_type'):
                    if hasattr(tab, 'get_dialog_history'):
                        history = tab.get_dialog_history()
                        if tab.tab_type == "optimized_multi_role":
                            role_name = "多角色协同(优化)"

                if history:
                    last_time = history[-1].get("timestamp", "无记录") if history else "无记录"

                if not search_text or search_text in role_name.lower():
                    tree.insert("", "end", values=(f"标签页 {tab_id}", role_name, len(history), last_time),
                                iid=str(tab_id))

        def on_search_change(*args):
            """搜索文本变化事件"""
            update_results()

        def on_item_double_click(event):
            """双击项目切换到对应标签页"""
            selection = tree.selection()
            if selection:
                tab_id = int(selection[0])
                if tab_id in self.tabs:
                    # 切换到对应标签页
                    tab = self.tabs[tab_id]
                    self.notebook.select(tab.parent)
                    search_dialog.destroy()

        search_var.trace("w", on_search_change)
        tree.bind("<Double-1>", on_item_double_click)

        # 初始加载
        update_results()

        # 按钮
        button_frame = ttk.Frame(search_dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Button(button_frame, text="切换到选中",
                   command=lambda: on_item_double_click(None)).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="关闭",
                   command=search_dialog.destroy).pack(side=tk.RIGHT)

    def load_global_roles(self):
        """从文件加载全局角色配置"""
        if os.path.exists(self.role_file):
            try:
                with open(self.role_file, 'r', encoding='utf-8') as f:
                    self.global_roles = json.load(f)
            except Exception as e:
                messagebox.showerror("错误", f"加载角色配置失败: {str(e)}")
                self.global_roles = {}

    def save_all_roles(self):
        """保存所有角色配置到文件"""
        try:
            # 收集所有标签页的角色配置
            for tab_id, tab in self.tabs.items():
                if hasattr(tab, 'get_role_config'):
                    role_config = tab.get_role_config()
                    role_name = role_config.get("name", f"标签页_{tab_id}")
                    self.global_roles[role_name] = role_config

            # 保存到文件
            with open(self.role_file, 'w', encoding='utf-8') as f:
                json.dump(self.global_roles, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存角色配置失败: {e}")

    def save_role_to_global(self, role_name, role_config):
        """保存角色到全局配置"""
        self.global_roles[role_name] = role_config
        try:
            with open(self.role_file, 'w', encoding='utf-8') as f:
                json.dump(self.global_roles, f, ensure_ascii=False, indent=2)
        except:
            pass

    def load_role_from_global(self, role_name):
        """从全局配置加载角色"""
        return self.global_roles.get(role_name, None)

    def import_global_roles(self):
        """从文件导入全局角色配置"""
        file_path = filedialog.askopenfilename(
            title="选择角色配置文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    imported_roles = json.load(f)

                # 合并角色配置
                self.global_roles.update(imported_roles)

                # 更新所有标签页的角色列表
                for tab in self.tabs.values():
                    if hasattr(tab, 'update_role_combobox'):
                        tab.update_role_combobox()

                messagebox.showinfo("成功", f"已从 {file_path} 导入 {len(imported_roles)} 个角色配置")
            except Exception as e:
                messagebox.showerror("错误", f"导入配置文件失败: {str(e)}")

    def export_global_roles(self):
        """导出全局角色配置到文件"""
        file_path = filedialog.asksaveasfilename(
            title="保存角色配置文件",
            filetypes=[("JSON文件", "*.json")],
            defaultextension=".json"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.global_roles, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("成功", f"角色配置已保存到 {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存配置文件失败: {str(e)}")


class OptimizedMultiRoleTab(ttk.Frame):
    """优化版多角色循环对话标签页类（支持流式输出）"""

    def __init__(self, parent, tab_id, global_api_key, global_base_url,
                 global_timeout, global_stream_response, global_roles,
                 on_token_update=None, on_save_role=None, on_load_role=None,
                 on_update_tab_title=None, log_dir="api_logs"):
        super().__init__(parent)

        self.tab_id = tab_id
        self.parent = parent
        self.on_update_tab_title = on_update_tab_title
        self.log_dir = log_dir
        self.tab_type = "optimized_multi_role"

        # 全局配置引用
        self.global_api_key = global_api_key
        self.global_base_url = global_base_url
        self.global_timeout = global_timeout
        self.global_stream_response = global_stream_response

        # 回调函数
        self.on_token_update = on_token_update
        self.on_save_role = on_save_role
        self.on_load_role = on_load_role

        # 全局角色引用
        self.global_roles = global_roles

        # 优化版多角色协同配置
        self.ordered_roles = []  # 有序角色列表，格式：[{"role": role_config, "id": id}]
        self.connections = []  # 连接词列表，格式：[{"from": role_id1, "to": role_id2, "connector": "连接词"}]
        self.connect_end_to_start = tk.BooleanVar(value=False)  # 是否首尾相连
        self.keep_mind = tk.BooleanVar(value=False)  # 是否保持初衷
        self.iteration_count = tk.IntVar(value=3)  # 循环次数
        self.initial_prompt = tk.StringVar(value="请开始你们的对话")  # 初始提示

        # 对话状态
        self.current_role_index = 0  # 当前角色索引
        self.current_iteration = 0  # 当前循环次数
        self.dialog_history = []  # 对话历史记录
        self.is_running = False  # 是否正在运行
        self.stop_requested = False  # 是否请求停止
        self.response_queue = queue.Queue()  # 用于流式输出的队列

        # Token统计
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

        # 角色ID计数器
        self.role_id_counter = 0

        # 保存/加载配置
        self.config_file = f"multi_role_config_{tab_id}.json"

        # 创建界面
        self.create_widgets()

        # 加载配置（如果有）
        self.load_config()

        # 开始队列处理
        self.process_response_queue()

    def create_widgets(self):
        """创建优化版多角色协同界面"""
        # 左侧配置区域
        left_frame = ttk.Frame(self)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))

        # 右侧区域
        right_frame = ttk.Frame(self)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 角色管理部分
        self.create_role_management_section(left_frame)

        # 连接词配置部分
        self.create_connection_section(left_frame)

        # 右侧上半部分：对话区域
        self.create_dialog_section(right_frame)

        # 右侧下半部分：初始提示和控制区域
        bottom_frame = ttk.Frame(right_frame)
        bottom_frame.pack(fill=tk.BOTH, pady=(10, 0))

        # 初始提示部分
        self.create_initial_prompt_section(bottom_frame)

        # 控制部分
        self.create_control_section(bottom_frame)

        # 配置权重
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left_frame.columnconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)

    def create_role_management_section(self, parent):
        """创建角色管理区域"""
        role_frame = ttk.LabelFrame(parent, text="👥 角色顺序管理", padding="10", style="MultiRole.TLabelframe")
        role_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # 角色选择和管理区域
        management_frame = ttk.Frame(role_frame)
        management_frame.pack(fill=tk.BOTH, expand=True)

        # 左侧：可用角色
        available_frame = ttk.LabelFrame(management_frame, text="可用角色", padding="5")
        available_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # 可用角色列表
        self.available_listbox = tk.Listbox(available_frame, selectmode=tk.SINGLE, height=8)
        self.available_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar1 = ttk.Scrollbar(available_frame, orient=tk.VERTICAL, command=self.available_listbox.yview)
        scrollbar1.pack(side=tk.RIGHT, fill=tk.Y)
        self.available_listbox.config(yscrollcommand=scrollbar1.set)

        # 填充可用角色
        self.update_available_roles()

        # 中间：控制按钮
        button_frame = ttk.Frame(management_frame)
        button_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))

        ttk.Button(button_frame, text="▶ 添加", command=self.add_selected_role,
                   width=8).pack(pady=2)
        ttk.Button(button_frame, text="◀ 移除", command=self.remove_selected_role,
                   width=8).pack(pady=2)
        ttk.Button(button_frame, text="↑ 上移", command=self.move_role_up,
                   width=8).pack(pady=2)
        ttk.Button(button_frame, text="↓ 下移", command=self.move_role_down,
                   width=8).pack(pady=2)
        ttk.Button(button_frame, text="刷新", command=self.refresh_role_lists,
                   width=8).pack(pady=2)

        # 右侧：已排序角色
        ordered_frame = ttk.LabelFrame(management_frame, text="角色顺序", padding="5")
        ordered_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 已排序角色列表
        self.ordered_listbox = tk.Listbox(ordered_frame, selectmode=tk.SINGLE, height=8)
        self.ordered_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar2 = ttk.Scrollbar(ordered_frame, orient=tk.VERTICAL, command=self.ordered_listbox.yview)
        scrollbar2.pack(side=tk.RIGHT, fill=tk.Y)
        self.ordered_listbox.config(yscrollcommand=scrollbar2.set)

        # 底部：保存/加载配置
        config_frame = ttk.Frame(role_frame)
        config_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(config_frame, text="保存配置", command=self.save_config,
                   width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(config_frame, text="加载配置", command=self.load_config_dialog,
                   width=10).pack(side=tk.LEFT)

    def create_connection_section(self, parent):
        """创建连接词配置区域"""
        conn_frame = ttk.LabelFrame(parent, text="⚙️ 连接词配置", padding="10", style="MultiRole.TLabelframe")
        conn_frame.pack(fill=tk.X, pady=(0, 15))

        # 连接词配置区域
        self.connector_frame = ttk.Frame(conn_frame)
        self.connector_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 更新连接词显示
        self.update_connector_display()

        # 首尾相连选项
        ttk.Checkbutton(conn_frame, text="首尾相连（形成完整循环）",
                        variable=self.connect_end_to_start,
                        command=self.update_connector_display).pack(anchor=tk.W, pady=(5, 0))
        # 保持初衷选项
        ttk.Checkbutton(conn_frame, text="保持初衷（每轮开始会加入初始提示）",
                        variable=self.keep_mind,
                        command=self.update_connector_display).pack(anchor=tk.W, pady=(5, 0))

        # 循环次数
        count_frame = ttk.Frame(conn_frame)
        count_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(count_frame, text="循环次数:").pack(side=tk.LEFT)
        iteration_spinbox = ttk.Spinbox(count_frame, from_=1, to=50,
                                        textvariable=self.iteration_count, width=10)
        iteration_spinbox.pack(side=tk.LEFT, padx=(5, 0))

    def create_initial_prompt_section(self, parent):
        """创建初始提示区域（带滚动条）"""
        prompt_frame = ttk.LabelFrame(parent, text="初始提示", padding="5")
        prompt_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 创建滚动条
        scrollbar = ttk.Scrollbar(prompt_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.initial_prompt_text = tk.Text(prompt_frame, height=4, wrap=tk.WORD,
                                           font=("微软雅黑", 10), yscrollcommand=scrollbar.set)
        self.initial_prompt_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.initial_prompt_text.yview)

        self.initial_prompt_text.insert("1.0", self.initial_prompt.get())
        self.initial_prompt_text.bind("<KeyRelease>",
                                      lambda e: self.initial_prompt.set(
                                          self.initial_prompt_text.get("1.0", tk.END).strip()))

    def create_control_section(self, parent):
        """创建控制区域"""
        control_frame = ttk.LabelFrame(parent, text="🎮 控制", padding="10", style="MultiRole.TLabelframe")
        control_frame.pack(fill=tk.X, pady=(0, 15))

        # 按钮框架
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X)

        self.start_button = ttk.Button(button_frame, text="▶️ 开始对话",
                                       command=self.start_dialog, width=12, style="Primary.TButton")
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_button = ttk.Button(button_frame, text="⏹️ 停止对话",
                                      command=self.stop_dialog, width=12, state='disabled', style="Primary.TButton")
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(button_frame, text="🧹 清空历史",
                   command=self.clear_dialog_history, width=12).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(button_frame, text="📋 复制配置",
                   command=self.copy_config, width=12).pack(side=tk.LEFT)

        # 状态显示
        self.status_var = tk.StringVar(value="准备就绪")
        self.status_label = ttk.Label(control_frame, textvariable=self.status_var,
                                      font=("微软雅黑", 9), foreground="blue")
        self.status_label.pack(fill=tk.X, pady=(10, 0))

        # 进度显示
        self.progress_var = tk.StringVar(value="进度: 0/0")
        self.progress_label = ttk.Label(control_frame, textvariable=self.progress_var,
                                        font=("微软雅黑", 9))
        self.progress_label.pack(fill=tk.X, pady=(5, 0))

    def create_dialog_section(self, parent):
        """创建对话显示区域"""
        dialog_frame = ttk.LabelFrame(parent, text="💬 多角色协同", padding="10")
        dialog_frame.pack(fill=tk.BOTH, expand=True)

        # 对话显示
        self.dialog_text = scrolledtext.ScrolledText(dialog_frame, height=20,
                                                     font=("微软雅黑", 10), wrap=tk.WORD,
                                                     state='disabled')
        self.dialog_text.pack(fill=tk.BOTH, expand=True)

    def update_available_roles(self):
        """更新可用角色列表"""
        self.available_listbox.delete(0, tk.END)
        role_names = list(self.global_roles.keys())

        # 始终显示所有可用角色，允许重复添加
        for role_name in role_names:
            self.available_listbox.insert(tk.END, role_name)

    def update_ordered_roles_display(self):
        """更新已排序角色显示，为重复角色添加编号"""
        self.ordered_listbox.delete(0, tk.END)

        # 统计每个角色出现的次数
        role_counts = {}

        for role_info in self.ordered_roles:
            role_name = role_info["role"]["name"]

            # 增加计数
            if role_name in role_counts:
                role_counts[role_name] += 1
            else:
                role_counts[role_name] = 1

        # 为每个角色分配显示名称，带编号
        display_names = {}
        for role_info in self.ordered_roles:
            role_name = role_info["role"]["name"]

            if role_counts[role_name] > 1:
                # 如果重复，为每个实例分配编号
                if role_name not in display_names:
                    display_names[role_name] = 1
                else:
                    display_names[role_name] += 1

                # 显示名称格式：角色名 (序号)
                display_name = f"{role_name} ({display_names[role_name]})"
            else:
                # 不重复的角色，直接显示原名
                display_name = role_name

            self.ordered_listbox.insert(tk.END, display_name)

    def refresh_role_lists(self):
        """刷新角色列表"""
        self.update_available_roles()
        self.update_ordered_roles_display()
        self.update_connector_display()

    def add_selected_role(self):
        """添加选中的角色到顺序列表"""
        selected = self.available_listbox.curselection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个角色")
            return

        role_name = self.available_listbox.get(selected[0])
        role_config = self.global_roles.get(role_name)

        if role_config:
            # 为角色分配唯一ID
            role_id = self.role_id_counter
            self.role_id_counter += 1

            # 添加到有序角色列表
            self.ordered_roles.append({
                "id": role_id,
                "role": role_config
            })

            # 更新显示
            self.update_available_roles()
            self.update_ordered_roles_display()
            self.update_connector_display()

    def remove_selected_role(self):
        """从顺序列表中移除选中的角色"""
        selected = self.ordered_listbox.curselection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个角色")
            return

        # 获取要移除的角色ID
        index = selected[0]
        role_info = self.ordered_roles[index]
        role_id = role_info["id"]

        # 从有序角色列表中移除
        del self.ordered_roles[index]

        # 从连接词列表中移除相关的连接
        self.connections = [conn for conn in self.connections
                            if conn["from"] != role_id and conn["to"] != role_id]

        # 更新显示
        self.update_available_roles()
        self.update_ordered_roles_display()
        self.update_connector_display()

    def move_role_up(self):
        """将选中的角色上移"""
        selected = self.ordered_listbox.curselection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个角色")
            return

        index = selected[0]
        if index > 0:
            # 交换位置
            self.ordered_roles[index], self.ordered_roles[index - 1] = \
                self.ordered_roles[index - 1], self.ordered_roles[index]

            # 更新显示
            self.update_ordered_roles_display()
            self.ordered_listbox.select_set(index - 1)
            self.update_connector_display()

    def move_role_down(self):
        """将选中的角色下移"""
        selected = self.ordered_listbox.curselection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个角色")
            return

        index = selected[0]
        if index < len(self.ordered_roles) - 1:
            # 交换位置
            self.ordered_roles[index], self.ordered_roles[index + 1] = \
                self.ordered_roles[index + 1], self.ordered_roles[index]

            # 更新显示
            self.update_ordered_roles_display()
            self.ordered_listbox.select_set(index + 1)
            self.update_connector_display()

    def update_connector_display(self):
        """更新连接词显示，优化布局"""
        # 清除旧的连接词显示
        for widget in self.connector_frame.winfo_children():
            widget.destroy()

        if len(self.ordered_roles) < 2:
            ttk.Label(self.connector_frame, text="至少需要2个角色才能配置连接词",
                      foreground="gray").pack()
            return

        # 创建滚动条
        scrollbar = ttk.Scrollbar(self.connector_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 创建画布来容纳连接词配置
        canvas = tk.Canvas(self.connector_frame, yscrollcommand=scrollbar.set, bg="white")
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=canvas.yview)

        # 创建内部框架来放置连接词配置
        inner_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner_frame, anchor=tk.NW)

        # 响应内部框架大小变化
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        inner_frame.bind("<Configure>", on_frame_configure)

        # 创建连接词输入框
        for i in range(len(self.ordered_roles)):
            next_i = (i + 1) % len(self.ordered_roles)

            # 如果不是首尾相连且是最后一个连接，跳过
            if not self.connect_end_to_start.get() and i == len(self.ordered_roles) - 1:
                break

            role1 = self.ordered_roles[i]
            role2 = self.ordered_roles[next_i]

            # 查找是否已有连接词
            connector_value = ""
            for conn in self.connections:
                if conn["from"] == role1["id"] and conn["to"] == role2["id"]:
                    connector_value = conn["connector"]
                    break

            # 创建输入框
            conn_frame = ttk.Frame(inner_frame)
            conn_frame.pack(fill=tk.X, pady=(5, 5), padx=5)

            # 角色关系标签
            role_label = ttk.Label(conn_frame, text=f"{role1['role']['name']} → {role2['role']['name']}:")
            role_label.pack(side=tk.LEFT, anchor=tk.CENTER)

            # 创建StringVar来跟踪连接词
            connector_var = tk.StringVar(value=connector_value)

            # 输入框，增大宽度
            entry = ttk.Entry(conn_frame, textvariable=connector_var, width=30)
            entry.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)

            # 绑定事件来保存连接词
            def save_connector(from_id=role1["id"], to_id=role2["id"], var=connector_var):
                self.save_connection(from_id, to_id, var.get())

            connector_var.trace("w",
                                lambda *args, f=role1["id"], t=role2["id"], v=connector_var: self.save_connection(f, t,
                                                                                                                  v.get()))

    def save_connection(self, from_id, to_id, connector):
        """保存连接词"""
        # 移除旧的连接
        self.connections = [conn for conn in self.connections
                            if not (conn["from"] == from_id and conn["to"] == to_id)]

        # 添加新的连接（如果有连接词）
        if connector.strip():
            self.connections.append({
                "from": from_id,
                "to": to_id,
                "connector": connector.strip()
            })

    def get_connector(self, from_id, to_id):
        """获取两个角色之间的连接词"""
        for conn in self.connections:
            if conn["from"] == from_id and conn["to"] == to_id:
                return conn["connector"]
        return "，"  # 默认连接词

    def save_config(self):
        """保存配置到文件"""
        try:
            config = {
                "ordered_roles": self.ordered_roles,
                "connections": self.connections,
                "connect_end_to_start": self.connect_end_to_start.get(),
                "iteration_count": self.iteration_count.get(),
                "initial_prompt": self.initial_prompt.get()
            }

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            messagebox.showinfo("成功", "配置已保存")
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {str(e)}")

    def load_config(self):
        """从文件加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                # 加载配置
                self.ordered_roles = config.get("ordered_roles", [])
                self.connections = config.get("connections", [])
                self.connect_end_to_start.set(config.get("connect_end_to_start", False))
                self.iteration_count.set(config.get("iteration_count", 3))
                self.initial_prompt.set(config.get("initial_prompt", "请开始你们的对话"))

                # 更新显示
                self.update_available_roles()
                self.update_ordered_roles_display()
                self.update_connector_display()

                # 更新初始提示文本框
                self.initial_prompt_text.delete("1.0", tk.END)
                self.initial_prompt_text.insert("1.0", self.initial_prompt.get())

            except Exception as e:
                print(f"加载配置失败: {e}")

    def load_config_dialog(self):
        """加载配置对话框"""
        file_path = filedialog.askopenfilename(
            title="选择多角色配置",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                # 加载配置
                self.ordered_roles = config.get("ordered_roles", [])
                self.connections = config.get("connections", [])
                self.connect_end_to_start.set(config.get("connect_end_to_start", False))
                self.iteration_count.set(config.get("iteration_count", 3))
                self.initial_prompt.set(config.get("initial_prompt", "请开始你们的对话"))

                # 更新显示
                self.update_available_roles()
                self.update_ordered_roles_display()
                self.update_connector_display()

                # 更新初始提示文本框
                self.initial_prompt_text.delete("1.0", tk.END)
                self.initial_prompt_text.insert("1.0", self.initial_prompt.get())

                messagebox.showinfo("成功", "配置已加载")
            except Exception as e:
                messagebox.showerror("错误", f"加载配置失败: {str(e)}")

    def copy_config(self):
        """复制配置到剪贴板"""
        try:
            config = {
                "ordered_roles": self.ordered_roles,
                "connections": self.connections,
                "connect_end_to_start": self.connect_end_to_start.get(),
                "iteration_count": self.iteration_count.get(),
                "initial_prompt": self.initial_prompt.get()
            }

            config_json = json.dumps(config, ensure_ascii=False, indent=2)
            self.clipboard_clear()
            self.clipboard_append(config_json)
            messagebox.showinfo("成功", "配置已复制到剪贴板")
        except Exception as e:
            messagebox.showerror("错误", f"复制配置失败: {str(e)}")

    def process_response_queue(self):
        """处理响应队列，实现流式输出"""
        try:
            while True:
                try:
                    text = self.response_queue.get_nowait()
                    if text is None:
                        break
                    self.append_to_dialog(text)
                except queue.Empty:
                    break
        except:
            pass
        finally:
            # 继续调度
            if self.is_running:
                self.after(100, self.process_response_queue)

    def start_dialog(self):
        """开始多角色协同"""
        # 检查API Key
        api_key = self.global_api_key.get().strip()
        if not api_key:
            messagebox.showerror("错误", "请输入API Key")
            return

        # 检查角色数量
        if len(self.ordered_roles) < 2:
            messagebox.showwarning("警告", "请至少选择2个角色")
            return

        # 重置状态
        self.current_role_index = 0
        self.current_iteration = 0
        self.is_running = True
        self.stop_requested = False

        # 清空对话历史
        self.dialog_text.config(state='normal')
        self.dialog_text.delete("1.0", tk.END)
        self.dialog_text.config(state='disabled')

        # 清空响应队列
        while not self.response_queue.empty():
            try:
                self.response_queue.get_nowait()
            except:
                pass

        # 禁用开始按钮，启用停止按钮
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')

        # 清空历史记录
        self.dialog_history = []

        # 更新状态
        self.status_var.set("对话开始...")
        self.update_progress_display()

        # 启动队列处理器
        self.process_response_queue()

        # 在新线程中开始对话
        thread = threading.Thread(target=self.run_dialog_cycle)
        thread.daemon = True
        thread.start()

    def stop_dialog(self):
        """停止多角色协同"""
        if self.is_running:
            self.stop_requested = True
            self.status_var.set("正在停止...")

    def run_dialog_cycle(self):
        """运行对话循环（支持流式输出）"""
        try:
            # 获取初始提示
            initial_prompt = self.initial_prompt.get().strip() or "请开始你们的对话"

            # 记录初始信息
            self.response_queue.put("=" * 60 + "\n")
            self.response_queue.put(f"多角色协同开始（优化版）\n")

            # 显示角色顺序
            role_names = [role_info["role"]["name"] for role_info in self.ordered_roles]
            self.response_queue.put(f"角色顺序: {' → '.join(role_names)}\n")

            self.response_queue.put(f"首尾相连: {'是' if self.connect_end_to_start.get() else '否'}\n")

            self.response_queue.put(f"循环次数: {self.iteration_count.get()}\n")
            self.response_queue.put(f"初始提示: {initial_prompt}\n")
            self.response_queue.put("=" * 60 + "\n\n")

            # 开始对话循环
            last_response = initial_prompt
            total_iterations = self.iteration_count.get()

            for iteration in range(total_iterations):
                if self.stop_requested:
                    break

                self.current_iteration = iteration + 1
                self.update_progress_display()

                # 记录迭代开始
                self.response_queue.put(f"\n{'=' * 40}\n")
                self.response_queue.put(f"第 {self.current_iteration} 轮对话\n")
                self.response_queue.put(f"{'=' * 40}\n\n")

                # 每个角色依次发言
                for role_index, role_info in enumerate(self.ordered_roles):
                    if self.stop_requested:
                        break

                    self.current_role_index = role_index
                    self.update_progress_display()

                    role_config = role_info["role"]
                    role_id = role_info["id"]

                    next_index = (role_index + 1) % len(self.ordered_roles)
                    next_role_id = self.ordered_roles[next_index]["id"]

                    # 显示当前角色
                    self.response_queue.put(f"【{role_config['name']}】\n")

                    # 构建消息（将上一个角色的回复+连接词作为提问）
                    messages = self.build_messages_for_role(role_config, role_id, next_role_id,
                                                            last_response, iteration, role_index)

                    # 调用API（流式输出）
                    response = self.call_api_for_role(role_config, messages)

                    if response:
                        # 更新最后响应
                        last_response = response

                        # 记录对话
                        dialog_entry = {
                            "iteration": self.current_iteration,
                            "role_index": role_index,
                            "role_name": role_config["name"],
                            "message": messages[-1]["content"] if messages else "",
                            "response": response,
                            "timestamp": datetime.now().strftime("%H:%M:%S")
                        }
                        self.dialog_history.append(dialog_entry)

                        # 添加换行
                        self.response_queue.put("\n\n")

                        # 短暂暂停，让对话更自然
                        if not self.stop_requested:
                            time.sleep(1)
                    else:
                        # API调用失败
                        self.response_queue.put("API调用失败\n\n")
                        break

                # 检查是否应该停止
                if self.stop_requested:
                    break

            # 对话结束
            self.response_queue.put("\n" + "=" * 60 + "\n")
            self.response_queue.put(f"对话{'已停止' if self.stop_requested else '完成'}\n")
            self.response_queue.put("=" * 60 + "\n")

        except Exception as e:
            self.response_queue.put(f"\n发生错误: {str(e)}\n")
        finally:
            self.response_queue.put(None)  # 发送结束信号
            self.finish_dialog()

    def build_messages_for_role(self, role_config, role_id, next_role_id, last_response, iteration, role_index):
        """为角色构建消息列表（将上一个角色的回复+连接词作为提问）"""
        messages = []

        # 添加系统提示
        messages.append({"role": "system", "content": role_config["system_prompt"]})

        # 如果是第一轮第一个角色，使用初始提示
        if iteration == 0 and role_index == 0:
            messages.append({"role": "user", "content": self.initial_prompt.get().strip()})
        else:
            # 获取连接词
            connector = self.get_connector(role_id, next_role_id)
            # 构建提问：连接词 + 上一个角色的回复
            prompt = f"{last_response}{connector}"
            if self.keep_mind.get() and role_index == 0:
                # 保持初衷，加入初始提示
                prompt += f"\n别忘记我们的初衷是\n{self.initial_prompt.get().strip()}"
            messages.append({"role": "user", "content": prompt})

        return messages

    def call_api_for_role(self, role_config, messages):
        """为角色调用API（支持流式输出）"""
        try:
            api_key = self.global_api_key.get().strip()
            if not api_key:
                return None

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": role_config.get("temperature", 0.7),
                "max_tokens": role_config.get("max_tokens", 2000),
                "stream": True  # 启用流式输出
            }

            # 添加深度思考参数
            if role_config.get("deep_thought", False):
                data["deep_thought"] = True
                data["model"] = "deepseek-reasoner"
                del data["max_tokens"]

            # 获取配置
            base_url = self.global_base_url.get().strip()
            timeout = self.global_timeout.get()

            # 记录API请求
            log_entry = {
                "timestamp": datetime.now().strftime("%Y-%m-d %H:%M:%S"),
                "role_name": role_config["name"],
                "iteration": self.current_iteration,
                "role_index": self.current_role_index,
                "request": {
                    "url": base_url,
                    "headers": {"Authorization": "Bearer ***" + api_key[-4:] if api_key else ""},
                    "data": data
                }
            }

            # 发送流式请求
            response = requests.post(base_url, headers=headers, json=data, timeout=timeout, stream=True)

            if response.status_code == 200:
                collected_chunks = []
                collected_content = ""

                # 处理流式响应
                for line in response.iter_lines():
                    if self.stop_requested:
                        break

                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data_str = line[6:]

                            if data_str == '[DONE]':
                                break

                            try:
                                data_json = json.loads(data_str)
                                if 'choices' in data_json and data_json['choices']:
                                    choice = data_json['choices'][0]
                                    if 'delta' in choice and 'content' in choice['delta']:
                                        content = choice['delta']['content']
                                        if content:
                                            collected_content += content
                                            # 将内容放入队列
                                            self.response_queue.put(content)

                                    # 检查是否有token使用信息
                                    if 'usage' in data_json:
                                        usage = data_json.get('usage', {})
                                        prompt_tokens = usage.get('prompt_tokens', 0)
                                        completion_tokens = usage.get('completion_tokens', 0)

                                        # 更新token统计
                                        self.total_prompt_tokens += prompt_tokens
                                        self.total_completion_tokens += completion_tokens

                                        # 回调通知全局token更新
                                        if self.on_token_update:
                                            self.on_token_update(prompt_tokens, completion_tokens)
                            except json.JSONDecodeError as e:
                                print(f"JSON解析错误: {e}")
                                continue

                # 记录API响应
                log_entry["response"] = {
                    "status_code": response.status_code,
                    "content": collected_content
                }
                self.save_api_log(log_entry)

                return collected_content
            else:
                error_msg = f"API错误: {response.status_code}\n{response.text}"
                log_entry["response"] = {
                    "status_code": response.status_code,
                    "error": response.text
                }
                self.save_api_log(log_entry)
                self.response_queue.put(f"API错误: {response.status_code}\n")
                return None

        except Exception as e:
            print(f"API调用失败: {e}")
            self.response_queue.put(f"API调用失败: {str(e)}\n")
            return None

    def save_api_log(self, log_entry):
        """保存API调用日志到文件，按日期目录+JSON格式"""
        try:
            # 获取当前日期，用于创建子目录
            current_date = datetime.now().strftime("%Y-%m-%d")

            # 创建日期子目录
            date_log_dir = os.path.join(self.log_dir, current_date)
            if not os.path.exists(date_log_dir):
                os.makedirs(date_log_dir)

            # 构建文件名：{角色名}{编号}_iter{循环次数}.json
            role_name = log_entry['role_name']
            role_index = log_entry.get('role_index', 0)
            iteration = log_entry.get('iteration', 0)

            # 生成文件名
            log_filename = f"{role_name}{role_index + 1}_iter{iteration}.json"
            log_path = os.path.join(date_log_dir, log_filename)

            # 准备JSON格式的日志数据
            json_log = {
                "timestamp": log_entry['timestamp'],
                "role_name": log_entry['role_name'],
                "role_index": log_entry.get('role_index', 0),
                "iteration": log_entry.get('iteration', 0),
                "request": log_entry['request'],
                "response": log_entry.get('response', {})
            }

            # 写入JSON文件
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(json_log, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存API日志失败: {e}")

    def append_to_dialog(self, text):
        """追加文本到对话显示"""
        self.dialog_text.config(state='normal')
        self.dialog_text.insert(tk.END, text)
        self.dialog_text.see(tk.END)
        self.dialog_text.config(state='disabled')

    def update_progress_display(self):
        """更新进度显示"""
        total_roles = len(self.ordered_roles)
        total_iterations = self.iteration_count.get()

        if self.is_running:
            current_step = (self.current_iteration - 1) * total_roles + self.current_role_index + 1
            total_steps = total_iterations * total_roles
            self.progress_var.set(
                f"进度: {current_step}/{total_steps} (第{self.current_iteration}轮, 角色{self.current_role_index + 1}/{total_roles})")
        else:
            self.progress_var.set(f"进度: 0/{total_iterations * total_roles}")

    def finish_dialog(self):
        """完成对话"""
        self.is_running = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')

        if self.stop_requested:
            self.status_var.set("对话已停止")
        else:
            self.status_var.set("对话完成")

    def clear_dialog_history(self):
        """清空对话历史"""
        if self.is_running:
            messagebox.showwarning("警告", "请先停止对话")
            return

        if messagebox.askyesno("确认清空", "确定要清空对话历史吗？"):
            self.dialog_text.config(state='normal')
            self.dialog_text.delete("1.0", tk.END)
            self.dialog_text.config(state='disabled')

            self.dialog_history = []
            self.total_prompt_tokens = 0
            self.total_completion_tokens = 0

            self.status_var.set("准备就绪")
            self.progress_var.set("进度: 0/0")

    def get_dialog_history(self):
        """获取对话历史"""
        return self.dialog_history

    def get_token_counts(self):
        """获取Token计数"""
        return self.total_prompt_tokens, self.total_completion_tokens


class SessionTab(ttk.Frame):
    """单个会话标签页类"""

    def __init__(self, parent, tab_id, global_api_key, global_base_url,
                 global_timeout, global_stream_response, global_roles,
                 on_token_update=None, on_save_role=None, on_load_role=None,
                 on_update_tab_title=None, log_dir="api_logs"):
        super().__init__(parent)

        self.tab_id = tab_id
        self.parent = parent
        self.on_update_tab_title = on_update_tab_title
        self.log_dir = log_dir

        # 全局配置引用
        self.global_api_key = global_api_key
        self.global_base_url = global_base_url
        self.global_timeout = global_timeout
        self.global_stream_response = global_stream_response

        # 回调函数
        self.on_token_update = on_token_update
        self.on_save_role = on_save_role
        self.on_load_role = on_load_role

        # 本地角色配置
        self.local_roles = {}  # 本地角色缓存
        self.global_roles = global_roles  # 全局角色引用
        self.current_role = tk.StringVar()
        self.role_name = tk.StringVar(value=f"助手 {tab_id}")
        self.system_prompt = tk.StringVar(value="你是一个有用的AI助手。")
        self.temperature = tk.DoubleVar(value=0.7)
        self.max_tokens = tk.IntVar(value=2000)
        self.deep_thought = tk.BooleanVar(value=False)

        # 对话历史
        self.conversation_history = []

        # Token统计
        self.prompt_tokens = 0
        self.completion_tokens = 0

        # 流式请求控制
        self.is_streaming = False
        self.stop_streaming = False
        self.response_queue = queue.Queue()

        # 创建界面
        self.create_widgets()

        # 初始化角色配置
        self.initialize_roles()

        # 启动队列处理器
        self.process_response_queue()

    def create_widgets(self):
        """创建界面组件"""
        # 创建左右分栏
        left_frame = ttk.Frame(self)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))

        right_frame = ttk.Frame(self)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 左侧：角色配置区域
        self.create_role_config_section(left_frame)

        # 右侧：对话区域
        self.create_conversation_section(right_frame)

        # 配置权重
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

    def create_role_config_section(self, parent):
        """创建角色配置区域"""
        # 角色管理框架
        role_frame = ttk.LabelFrame(parent, text="角色配置", padding="10")
        role_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 角色选择
        role_select_frame = ttk.Frame(role_frame)
        role_select_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(role_select_frame, text="选择角色:").pack(side=tk.LEFT)
        self.role_combo = ttk.Combobox(role_select_frame, textvariable=self.current_role,
                                       state="readonly", width=20)
        self.role_combo.pack(side=tk.LEFT, padx=(5, 10))

        # 加载按钮
        ttk.Button(role_select_frame, text="加载",
                   command=self.load_selected_role, width=8).pack(side=tk.LEFT)

        # 保存按钮
        ttk.Button(role_select_frame, text="保存",
                   command=self.save_current_role, width=8).pack(side=tk.LEFT, padx=(5, 0))

        # 角色名称
        name_frame = ttk.Frame(role_frame)
        name_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(name_frame, text="角色名称:").pack(side=tk.LEFT)
        ttk.Entry(name_frame, textvariable=self.role_name, width=30).pack(side=tk.LEFT, padx=(5, 0))

        # 系统提示
        prompt_frame = ttk.LabelFrame(role_frame, text="系统提示", padding="5")
        prompt_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.prompt_text = tk.Text(prompt_frame, height=6, wrap=tk.WORD, font=("微软雅黑", 10))
        self.prompt_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.prompt_text.insert("1.0", self.system_prompt.get())
        self.prompt_text.bind("<KeyRelease>",
                              lambda e: self.system_prompt.set(self.prompt_text.get("1.0", tk.END).strip()))

        # 参数配置
        param_frame = ttk.Frame(role_frame)
        param_frame.pack(fill=tk.X, pady=(0, 10))

        # 温度
        ttk.Label(param_frame, text="温度:").pack(side=tk.LEFT)
        ttk.Spinbox(param_frame, from_=0.1, to=2.0, increment=0.1,
                    textvariable=self.temperature, width=8).pack(side=tk.LEFT, padx=(5, 10))

        # 最大tokens
        ttk.Label(param_frame, text="最大tokens:").pack(side=tk.LEFT)
        ttk.Spinbox(param_frame, from_=100, to=8000, increment=100,
                    textvariable=self.max_tokens, width=8).pack(side=tk.LEFT, padx=(5, 10))

        # 深度思考
        ttk.Checkbutton(param_frame, text="深度思考",
                        variable=self.deep_thought).pack(side=tk.LEFT)

        # 状态显示
        self.status_var = tk.StringVar(value="准备就绪")
        ttk.Label(role_frame, textvariable=self.status_var,
                  font=("微软雅黑", 9), foreground="blue").pack(fill=tk.X, pady=(10, 0))

    def create_conversation_section(self, parent):
        """创建对话区域"""
        # 历史对话
        history_frame = ttk.LabelFrame(parent, text="对话历史", padding="10")
        history_frame.pack(fill=tk.BOTH, expand=True)

        self.history_text = scrolledtext.ScrolledText(history_frame, height=25,
                                                      font=("微软雅黑", 10), wrap=tk.WORD,
                                                      state='disabled')
        self.history_text.pack(fill=tk.BOTH, expand=True)

        # 输入区域
        input_frame = ttk.LabelFrame(parent, text="输入消息", padding="10")
        input_frame.pack(fill=tk.X, pady=(10, 0))

        # 为输入框添加滚动条
        scrollbar = ttk.Scrollbar(input_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.input_text = tk.Text(input_frame, height=4, wrap=tk.WORD, font=("微软雅黑", 10),
                                  yscrollcommand=scrollbar.set)
        self.input_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.input_text.yview)

        # 绑定回车键发送
        self.input_text.bind("<Control-Return>", lambda e: self.send_message())

        # 控制按钮区域
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, pady=(10, 0))

        self.send_button = ttk.Button(control_frame, text="发送",
                                      command=self.send_message, width=12, style="Primary.TButton")
        self.send_button.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_button = ttk.Button(control_frame, text="停止",
                                      command=self.stop_stream, width=12, state='disabled', style="Primary.TButton")
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(control_frame, text="清空历史",
                   command=self.clear_history, width=12).pack(side=tk.LEFT)

        # Token统计
        token_frame = ttk.Frame(parent)
        token_frame.pack(fill=tk.X, pady=(10, 0))

        self.token_label = ttk.Label(token_frame, text="Tokens: 0/0 (输入/输出)")
        self.token_label.pack(side=tk.LEFT)

    def initialize_roles(self):
        """初始化角色列表"""
        self.update_role_combobox()
        if self.global_roles:
            first_role = list(self.global_roles.keys())[0]
            self.current_role.set(first_role)
            self.load_selected_role()

    def update_role_combobox(self):
        """更新角色下拉框"""
        role_names = list(self.global_roles.keys())
        self.role_combo['values'] = role_names
        if role_names and not self.current_role.get():
            self.current_role.set(role_names[0])

    def load_selected_role(self):
        """加载选中的角色"""
        role_name = self.current_role.get()
        if not role_name:
            return

        role_config = self.global_roles.get(role_name)
        if role_config:
            self.set_role_config(role_config)
            if self.on_update_tab_title:
                self.on_update_tab_title(role_name)

    def set_role_config(self, role_config):
        """设置角色配置"""
        self.role_name.set(role_config.get("name", ""))
        self.system_prompt.set(role_config.get("system_prompt", ""))
        self.temperature.set(role_config.get("temperature", 0.7))
        self.max_tokens.set(role_config.get("max_tokens", 2000))
        self.deep_thought.set(role_config.get("deep_thought", False))

        # 更新文本框
        self.prompt_text.delete("1.0", tk.END)
        self.prompt_text.insert("1.0", self.system_prompt.get())

    def get_role_config(self):
        """获取当前角色配置"""
        return {
            "name": self.role_name.get(),
            "system_prompt": self.system_prompt.get(),
            "temperature": self.temperature.get(),
            "max_tokens": self.max_tokens.get(),
            "deep_thought": self.deep_thought.get()
        }

    def save_current_role(self):
        """保存当前角色"""
        role_name = self.role_name.get()
        if not role_name:
            messagebox.showerror("错误", "请输入角色名称")
            return

        role_config = self.get_role_config()

        if self.on_save_role:
            self.on_save_role(role_name, role_config)

        # 更新角色下拉框
        self.update_role_combobox()

        messagebox.showinfo("成功", f"角色 '{role_name}' 已保存")

    def send_message(self):
        """发送消息"""
        # 检查API Key
        api_key = self.global_api_key.get().strip()
        if not api_key:
            messagebox.showerror("错误", "请输入API Key")
            return

        # 获取用户输入
        user_input = self.input_text.get("1.0", tk.END).strip()
        if not user_input:
            return

        # 清空输入框
        self.input_text.delete("1.0", tk.END)

        # 显示用户消息
        self.append_to_history(f"用户: {user_input}\n\n")

        # 更新状态
        self.status_var.set("正在思考...")
        self.send_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.is_streaming = True
        self.stop_streaming = False

        # 在新线程中发送请求
        thread = threading.Thread(target=self.send_api_request, args=(user_input,))
        thread.daemon = True
        thread.start()

    def stop_stream(self):
        """停止流式响应"""
        if self.is_streaming:
            self.stop_streaming = True
            self.status_var.set("正在停止...")

    def send_api_request(self, user_input):
        """发送API请求"""
        try:
            # 构建消息历史
            messages = self.build_messages(user_input)

            # 调用API
            if self.global_stream_response.get():
                # 流式响应
                self.call_api_stream(messages, user_input)
            else:
                # 非流式响应
                self.call_api_normal(messages, user_input)

        except Exception as e:
            self.after(0, self.append_to_history, f"发生错误: {str(e)}\n\n")
        finally:
            self.after(0, self.finish_request)

    def build_messages(self, user_input):
        """构建消息列表"""
        messages = []

        # 添加系统提示
        system_prompt = self.system_prompt.get()
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # 添加上下文历史（最近10条）
        for entry in self.conversation_history[-10:]:
            if entry["role"] == "user":
                messages.append({"role": "user", "content": entry["content"]})
            else:
                messages.append({"role": "assistant", "content": entry["content"]})

        # 添加当前用户输入
        messages.append({"role": "user", "content": user_input})

        return messages

    def call_api_stream(self, messages, user_input):
        """流式调用API"""
        try:
            api_key = self.global_api_key.get().strip()
            base_url = self.global_base_url.get().strip()
            timeout = self.global_timeout.get()

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": self.temperature.get(),
                "max_tokens": self.max_tokens.get(),
                "stream": True
            }

            if self.deep_thought.get():
                data["deep_thought"] = True
                data["model"] = "deepseek-reasoner"
                del data["max_tokens"]

            # 记录请求
            log_entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "role_name": self.role_name.get(),
                "request": {
                    "url": base_url,
                    "headers": {"Authorization": "Bearer ***" + api_key[-4:]},
                    "data": data
                }
            }

            # 显示AI标签
            self.response_queue.put("AI: ")

            # 发送请求
            response = requests.post(base_url, headers=headers, json=data, timeout=timeout, stream=True)

            if response.status_code == 200:
                collected_content = ""
                usage_data = {}

                # 处理流式响应
                for line in response.iter_lines():
                    if self.stop_streaming:
                        break

                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data_str = line[6:]

                            if data_str == '[DONE]':
                                break

                            try:
                                data_json = json.loads(data_str)
                                if 'choices' in data_json and data_json['choices']:
                                    choice = data_json['choices'][0]
                                    if 'delta' in choice and 'content' in choice['delta']:
                                        content = choice['delta']['content']
                                        if content:
                                            collected_content += content
                                            self.response_queue.put(content)

                                    # 检查是否有token使用信息
                                    if 'usage' in data_json:
                                        usage_data = data_json.get('usage', {})
                            except json.JSONDecodeError:
                                continue

                # 添加换行
                self.response_queue.put("\n\n")

                # 记录对话历史
                self.conversation_history.append({
                    "role": "user",
                    "content": user_input,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                self.conversation_history.append({
                    "role": "assistant",
                    "content": collected_content,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                # 记录API日志
                log_entry["response"] = {
                    "status_code": response.status_code,
                    "content": collected_content,
                    "usage": usage_data
                }
                self.save_api_log(log_entry)

                # 更新token统计
                prompt_tokens = usage_data.get('prompt_tokens', 0)
                completion_tokens = usage_data.get('completion_tokens', 0)

                self.prompt_tokens += prompt_tokens
                self.completion_tokens += completion_tokens

                if self.on_token_update:
                    self.on_token_update(prompt_tokens, completion_tokens)

                self.after(0, self.update_token_display)

            else:
                error_msg = f"API错误: {response.status_code}\n{response.text}"
                self.response_queue.put(f"API错误: {response.status_code}\n\n")

                log_entry["response"] = {
                    "status_code": response.status_code,
                    "error": response.text
                }
                self.save_api_log(log_entry)

        except Exception as e:
            self.response_queue.put(f"API调用失败: {str(e)}\n\n")

    def call_api_normal(self, messages, user_input):
        """非流式调用API"""
        try:
            api_key = self.global_api_key.get().strip()
            base_url = self.global_base_url.get().strip()
            timeout = self.global_timeout.get()

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": self.temperature.get(),
                "max_tokens": self.max_tokens.get(),
                "stream": False
            }

            if self.deep_thought.get():
                data["deep_thought"] = True
                data["model"] = "deepseek-reasoner"
                del data["max_tokens"]

            # 记录请求
            log_entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "role_name": self.role_name.get(),
                "request": {
                    "url": base_url,
                    "headers": {"Authorization": "Bearer ***" + api_key[-4:]},
                    "data": data
                }
            }

            # 发送请求
            response = requests.post(base_url, headers=headers, json=data, timeout=timeout)

            if response.status_code == 200:
                result = response.json()
                ai_response = result["choices"][0]["message"]["content"]
                usage = result.get("usage", {})

                # 显示AI响应
                self.response_queue.put(f"AI: {ai_response}\n\n")

                # 记录对话历史
                self.conversation_history.append({
                    "role": "user",
                    "content": user_input,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                self.conversation_history.append({
                    "role": "assistant",
                    "content": ai_response,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                # 记录API日志
                log_entry["response"] = {
                    "status_code": response.status_code,
                    "content": ai_response,
                    "usage": usage
                }
                self.save_api_log(log_entry)

                # 更新token统计
                prompt_tokens = usage.get('prompt_tokens', 0)
                completion_tokens = usage.get('completion_tokens', 0)

                self.prompt_tokens += prompt_tokens
                self.completion_tokens += completion_tokens

                if self.on_token_update:
                    self.on_token_update(prompt_tokens, completion_tokens)

                self.after(0, self.update_token_display)

            else:
                error_msg = f"API错误: {response.status_code}\n{response.text}"
                self.response_queue.put(f"API错误: {response.status_code}\n\n")

                log_entry["response"] = {
                    "status_code": response.status_code,
                    "error": response.text
                }
                self.save_api_log(log_entry)

        except Exception as e:
            self.response_queue.put(f"API调用失败: {str(e)}\n\n")

    def process_response_queue(self):
        """处理响应队列"""
        try:
            while True:
                try:
                    text = self.response_queue.get_nowait()
                    self.append_to_history(text)
                except queue.Empty:
                    break
        except:
            pass
        finally:
            self.after(100, self.process_response_queue)

    def append_to_history(self, text):
        """追加文本到历史记录"""
        self.history_text.config(state='normal')
        self.history_text.insert(tk.END, text)
        self.history_text.see(tk.END)
        self.history_text.config(state='disabled')

    def update_token_display(self):
        """更新Token显示"""
        self.token_label.config(text=f"Tokens: {self.prompt_tokens}/{self.completion_tokens} (输入/输出)")

    def finish_request(self):
        """完成请求"""
        self.is_streaming = False
        self.send_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.status_var.set("准备就绪")

    def clear_history(self):
        """清空对话历史"""
        if self.is_streaming:
            messagebox.showwarning("警告", "请先停止当前请求")
            return

        if messagebox.askyesno("确认清空", "确定要清空对话历史吗？"):
            self.history_text.config(state='normal')
            self.history_text.delete("1.0", tk.END)
            self.history_text.config(state='disabled')

            self.conversation_history = []
            self.prompt_tokens = 0
            self.completion_tokens = 0
            self.update_token_display()

    def get_conversation_history(self):
        """获取对话历史"""
        return self.conversation_history

    def get_token_counts(self):
        """获取Token计数"""
        return self.prompt_tokens, self.completion_tokens

    def save_api_log(self, log_entry):
        """保存API调用日志到文件，按日期目录+JSON格式"""
        try:
            # 获取当前日期时间，用于创建子目录，保存每一次协同对话内容
            current_date, time_tag = datetime.now().strftime("%Y-%m-%d %H-%M-%S").split(" ")

            # 创建日期子目录
            date_log_dir = os.path.join(self.log_dir, current_date)
            if not os.path.exists(date_log_dir):
                os.makedirs(date_log_dir)

            # 构建文件名：{角色名}{编号}_iter{循环次数}.json
            # 会话模式下，循环次数固定为0
            role_name = log_entry['role_name']
            tab_id = self.tab_id
            iteration = 0  # 会话模式下没有迭代次数

            # 生成文件名
            log_filename = f"{time_tag}_{role_name}{tab_id}_iter{iteration}.json"
            log_path = os.path.join(date_log_dir, log_filename)

            # 准备JSON格式的日志数据
            json_log = {
                "timestamp": log_entry['timestamp'],
                "role_name": log_entry['role_name'],
                "tab_id": self.tab_id,
                "iteration": iteration,
                "request": log_entry['request'],
                "response": log_entry.get('response', {})
            }

            # 写入JSON文件
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(json_log, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存API日志失败: {e}")


def main():
    """主程序入口"""
    root = tk.Tk()
    app = DeepSeekAPIMultiTabTool(root)

    # 设置窗口最小大小
    root.minsize(1400, 800)

    # 使窗口可调整大小
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    # 在关闭窗口时保存角色配置
    def on_closing():
        try:
            app.save_all_roles()
        except Exception as e:
            print(f"保存配置时出错: {e}")
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
