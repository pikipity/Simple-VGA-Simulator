import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re
import os

class PinPlanner:
    def __init__(self, root):
        self.root = root
        self.root.title("Pin Planner")
        self.root.geometry("800x600")
        
        # Predefined testbench signals
        self.tb_signals = [
            'clk', 'reset', 'B2', 'B3', 'B4', 'B5', 'h_sync', 'v_sync', 'rgb',
            'led1', 'led2', 'led3', 'led4', 'led5'
        ]
        
        # Module signals (will be populated from file)
        self.module_signals = ['']

        self.combobox_list = []
        
        # Mapping dictionary
        self.mapping = {}
        
        self.setup_gui()
    
    def setup_gui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # File selection section
        file_frame = ttk.LabelFrame(main_frame, text="1. Select Verilog Module File", padding="10")
        file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Button(file_frame, text="Browse Verilog File", 
                  command=self.browse_verilog_file).grid(row=0, column=0, padx=(0, 10))
        
        self.file_path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path_var, state='readonly').grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Mapping section with scrollbar
        mapping_frame_main = ttk.LabelFrame(main_frame, text="2. Map Signals", padding="10")
        mapping_frame_main.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        mapping_frame_main.columnconfigure(0, weight=1)
        mapping_frame_main.rowconfigure(0, weight=1)
        
        # Create canvas and scrollbar for scrollable area
        canvas = tk.Canvas(mapping_frame_main, highlightthickness=0)
        scrollbar = ttk.Scrollbar(mapping_frame_main, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Mapping frame content
        ttk.Label(scrollable_frame, text="Development Board Pins", font=('Arial', 10, 'bold')).grid(row=0, column=0, pady=(0, 5), padx=10)
        ttk.Label(scrollable_frame, text="=>", font=('Arial', 10, 'bold')).grid(row=0, column=1, pady=(0, 5), padx=10)
        ttk.Label(scrollable_frame, text="Module Interface", font=('Arial', 10, 'bold')).grid(row=0, column=2, pady=(0, 5), padx=10)
        
        for row_i in range(len(self.tb_signals)):
            ttk.Label(scrollable_frame, text=self.tb_signals[row_i], font=('Arial', 10)).grid(row=1 + row_i, column=0, pady=(0, 5), sticky=tk.E)
            ttk.Label(scrollable_frame, text="=>", font=('Arial', 10)).grid(row=1 + row_i, column=1, pady=(0, 5))
            combobox = ttk.Combobox(scrollable_frame, state="readonly", width=20)
            combobox.grid(row=1 + row_i, column=2, sticky=(tk.W, tk.E), pady=(0, 5))
            self.combobox_list.append(combobox)

        # Generate button
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, pady=10)
        
        ttk.Button(button_frame, text="Save Pins", 
                  command=self.generate_testbench).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Reset", 
                  command=self.reset).pack(side=tk.LEFT, padx=5)
    
    def browse_verilog_file(self):
        """Browse for Verilog file and parse it"""
        filename = filedialog.askopenfilename(
            title="Select Verilog Module File",
            filetypes=[("Verilog files", "*.v"), ("All files", "*.*")],
            initialdir=os.getcwd()
        )
        
        if filename:
            self.file_path_var.set(filename)
            self.parse_verilog_file(filename)
    
    def _extract_signal_name(self, decl):
        """
        从单个信号声明中提取信号名
        处理格式: [direction] [wire/reg] [bitwidth] signal_name
        例: "input wire [7:0] data" -> "data"
        """
        decl = decl.strip()
        if not decl:
            return None
        
        # 移除方向关键字 (input/output/inout)
        decl = re.sub(r'^(input|output|inout)\s*', '', decl, flags=re.IGNORECASE)
        
        # 移除类型关键字 (wire/reg)
        decl = re.sub(r'^(wire|reg)\s*', '', decl, flags=re.IGNORECASE)
        
        # 移除位宽声明 [x:y] 或多维 [x:y][a:b]
        decl = re.sub(r'(\[[^\]]+\])+', '', decl)
        
        # 剩余部分应该是信号名
        decl = decl.strip().rstrip(',').strip()
        
        # 验证信号名是合法的Verilog标识符
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', decl):
            return decl
        return None
    
    def parse_verilog_file(self, filename):
        """Parse Verilog file to extract inputs and outputs"""
        try:
            with open(filename, 'r') as file:
                content = file.read()
            
            # Remove comments
            content = re.sub(r'//.*', '', content)
            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
            
            # Find module declaration
            module_match = re.search(r'module\s+(\w+)\s*\(([^)]*)\)', content, re.DOTALL)
            if not module_match:
                messagebox.showerror("Error", "Could not find module declaration")
                return
            
            # print(module_match.group)
            module_name = module_match.group(1)
            self.module_name = module_name
            
            # Reset module signals
            self.module_signals = ['']
            
            # Parse port declarations
            # 获取模块端口声明部分
            port_declaration = module_match.group(2)
            
            # 新的解析策略：处理Verilog的换行不敏感特性
            # 1. 将声明按逗号分割成独立的信号声明
            # 2. 对每个声明提取方向和信号名
            all_signals = []
            
            # 按逗号分割，但保留逗号在结果中用于处理
            raw_items = re.split(r'(,)', port_declaration)
            
            # 合并被逗号分割的项，处理每个信号声明
            current_decl = ""
            for item in raw_items:
                item = item.strip()
                if not item:
                    continue
                
                if item == ',':
                    # 遇到逗号，处理当前累积的声明
                    if current_decl:
                        signal = self._extract_signal_name(current_decl)
                        if signal:
                            all_signals.append(signal)
                        current_decl = ""
                else:
                    # 累积声明内容
                    if current_decl:
                        current_decl += " " + item
                    else:
                        current_decl = item
            
            # 处理最后一个声明（没有尾随逗号）
            if current_decl:
                signal = self._extract_signal_name(current_decl)
                if signal:
                    all_signals.append(signal)
            
            # 去重并保持原始顺序
            seen = set()
            unique_signals = []
            for s in all_signals:
                if s not in seen and s not in ['input', 'output', 'inout', 'wire', 'reg']:
                    seen.add(s)
                    unique_signals.append(s)
            
            self.module_signals.extend(unique_signals)
            
            # Update comboboxes
            for combobox_i in range(len(self.combobox_list)):
                self.combobox_list[combobox_i]['values'] = self.module_signals
                if self.combobox_list[combobox_i]['values']:
                    self.combobox_list[combobox_i].current(0)
            
            messagebox.showinfo("Success", f"Successfully parsed module '{module_name}'\n"
                                            f"Found {len(self.module_signals)-1} inputs and outputs")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to parse Verilog file: {str(e)}")
    
    def has_duplicates(self, lst):
        non_zero_list = [x for x in lst if x != 0]
        return len(non_zero_list) != len(set(non_zero_list))
    
    def is_mapping_empty(self, lst):
        """检查是否至少有一个有效的映射"""
        non_zero_list = [x for x in lst if x != 0]
        return len(non_zero_list) == 0
    
    def update_mapping(self):
        # 首先清空旧的映射，确保每次都是从零开始构建
        self.mapping = {}
        
        # Get selections
        select_item = []
        for combobox_i in range(len(self.combobox_list)):
            select_item.append(self.combobox_list[combobox_i].current())
        
        # Check repeat
        if self.has_duplicates(select_item):
            messagebox.showwarning("Warning", "Duplicate signal mapping detected. Please ensure each module signal is mapped to only one board pin.")
            self.mapping = {}
            return
        
        # Check if at least one signal is mapped (allow partial mapping)
        if self.is_mapping_empty(select_item):
            return

        # 构建新的映射
        for select_i in range(len(select_item)):
            if select_item[select_i] != 0:
                self.mapping[self.module_signals[select_item[select_i]]] = self.tb_signals[select_i]
    
    def generate_testbench(self):
        """Generate the Verilog testbench file"""
        if not hasattr(self, 'module_name'):
            messagebox.showerror("Error", "Please select and parse a Verilog module file first")
            return
        
        self.update_mapping()
        
        if not self.mapping:
            messagebox.showwarning("Warning", "No mappings defined")
            return
        
        # Ask for save location
        # filename = filedialog.asksaveasfilename(
        #     title="Save Testbench As",
        #     defaultextension=".v",
        #     filetypes=[("Verilog files", "*.v"), ("All files", "*.*")]
        # )
        filename = filedialog.askdirectory(
            title="Select simulation folder",
            initialdir=os.getcwd(),
        )
        
        if not filename:
            return
        else:
            filename = os.path.join(filename, f'DevelopmentBoard.v')
        
        try:
            with open(filename, 'w') as file:
                file.write(self.generate_testbench_code())
            
            messagebox.showinfo("Success", f"Pin Plan successfully!!\nRemember insert timescale to all your own modules!!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate testbench: {str(e)}")
    
    def generate_testbench_code(self):
        """Generate the actual Verilog testbench code"""

        code = f"""`timescale 1ns / 1ns

module DevelopmentBoard(
    input wire clk,  // 50MHz
    input wire reset, B2, B3, B4, B5,
    // reset is "a"
    // B2 is "s"
    // B3 is "d"
    // B4 is "f"
    // B5 is "g"
    output wire h_sync, v_sync,
    output wire [15:0] rgb,
    output wire led1,
    output wire led2,
    output wire led3,
    output wire led4,
    output wire led5
);

{self.module_name} {self.module_name}_inst(
"""

        connections = []
        for module_signal, tb_signal in self.mapping.items():
            connections.append(f"    .{module_signal}({tb_signal})")
        code += ',\n'.join(connections)
        code += "\n);\n\n"

        code += "endmodule\n"

        return code
    
    def reset(self):
        """Reset the application"""
        self.file_path_var.set("")
        self.module_signals = ['']
        self.mapping = {}
        for combobox_i in range(len(self.combobox_list)):
            self.combobox_list[combobox_i].set('')
        if hasattr(self, 'module_name'):
            del self.module_name

def main():
    root = tk.Tk()
    app = PinPlanner(root)
    root.mainloop()

if __name__ == "__main__":
    main()