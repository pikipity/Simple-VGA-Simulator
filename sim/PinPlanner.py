import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re
import os

class VerilogTestbenchGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Verilog Testbench Generator")
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
        main_frame.columnconfigure(1, weight=1)
        
        # File selection section
        file_frame = ttk.LabelFrame(main_frame, text="1. Select Verilog Module File", padding="10")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Button(file_frame, text="Browse Verilog File", 
                  command=self.browse_verilog_file).grid(row=0, column=0, padx=(0, 10))
        
        self.file_path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path_var, state='readonly').grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Mapping section
        mapping_frame_main = ttk.LabelFrame(main_frame, text="2. Map Signals", padding="10")
        mapping_frame_main.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        # mapping_frame.columnconfigure(1, weight=1)
        # mapping_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        mapping_frame = ttk.Frame()
        mapping_frame.place(in_=main_frame, anchor="c", relx=.5, rely=.5)

        # Mapping frame
        # row: 0
        ttk.Label(mapping_frame, text="Development Board Pins", font=('Arial', 10, 'bold')).grid(row=0, column=0, pady=(0, 5))
        ttk.Label(mapping_frame, text="Module Interface", font=('Arial', 10, 'bold')).grid(row=0, column=2, pady=(0, 5))
        # row: 1~
        for row_i in range(len(self.tb_signals)):
            ttk.Label(mapping_frame, text=self.tb_signals[row_i], font=('Arial', 10)).grid(row=1 + row_i, column=0, pady=(0, 5))
            ttk.Label(mapping_frame, text="=>", font=('Arial', 10)).grid(row=1 + row_i, column=1, pady=(0, 5))
            self.combobox_list.append(
                ttk.Combobox(mapping_frame, state="readonly")
            )
            self.combobox_list[-1].grid(row=1 + row_i, column=2, sticky=(tk.W, tk.E), pady=(0, 5))

        # # Generate button
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Save Pins", 
                  command=self.generate_testbench).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Reset", 
                  command=self.reset).pack(side=tk.LEFT, padx=5)
        
        
        # # Testbench signals frame
        # tb_frame = ttk.Frame(mapping_frame)
        # tb_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # ttk.Label(tb_frame, text="Development Board Pins", font=('Arial', 10, 'bold')).grid(row=0, column=0, pady=(0, 5))
        
        # # Inputs
        # ttk.Label(tb_frame, text="Inputs:").grid(row=1, column=0, sticky=tk.W)
        # self.tb_inputs_listbox = tk.Listbox(tb_frame, height=8, width=25)
        # self.tb_inputs_listbox.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # # Outputs
        # ttk.Label(tb_frame, text="Outputs:").grid(row=3, column=0, sticky=tk.W)
        # self.tb_outputs_listbox = tk.Listbox(tb_frame, height=8, width=25)
        # self.tb_outputs_listbox.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # tb_frame.columnconfigure(0, weight=1)
        # tb_frame.rowconfigure(2, weight=1)
        # tb_frame.rowconfigure(4, weight=1)
        
        # # Module signals frame
        # module_frame = ttk.Frame(mapping_frame)
        # module_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ttk.Label(module_frame, text="Module Signals", font=('Arial', 10, 'bold')).grid(row=0, column=0, pady=(0, 5))
        
        # # Module inputs
        # ttk.Label(module_frame, text="Inputs:").grid(row=1, column=0, sticky=tk.W)
        # self.module_inputs_combobox = ttk.Combobox(module_frame, state="readonly")
        # self.module_inputs_combobox.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # # Module outputs
        # ttk.Label(module_frame, text="Outputs:").grid(row=3, column=0, sticky=tk.W)
        # self.module_outputs_combobox = ttk.Combobox(module_frame, state="readonly")
        # self.module_outputs_combobox.grid(row=4, column=0, sticky=(tk.W, tk.E))
        
        # # Mapping controls
        # mapping_controls = ttk.Frame(mapping_frame)
        # mapping_controls.grid(row=0, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10)
        
        # ttk.Button(mapping_controls, text="Map Selected", 
        #           command=self.map_signals).grid(row=0, column=0, pady=5)
        # ttk.Button(mapping_controls, text="Clear Mapping", 
        #           command=self.clear_mapping).grid(row=1, column=0, pady=5)
        
        # # Current mappings display
        # ttk.Label(mapping_controls, text="Current Mappings:", font=('Arial', 9, 'bold')).grid(row=2, column=0, pady=(20, 5))
        
        # self.mappings_text = tk.Text(mapping_controls, height=15, width=30)
        # self.mappings_text.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # mapping_controls.rowconfigure(3, weight=1)
        
        # # Generate button
        # button_frame = ttk.Frame(main_frame)
        # button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        # ttk.Button(button_frame, text="Generate Testbench", 
        #           command=self.generate_testbench).pack(side=tk.LEFT, padx=5)
        # ttk.Button(button_frame, text="Reset", 
        #           command=self.reset).pack(side=tk.LEFT, padx=5)
        
        # # Initialize lists
        # self.populate_tb_signals()
    
    # def populate_tb_signals(self):
    #     """Populate the testbench signals listboxes"""
    #     self.tb_inputs_listbox.delete(0, tk.END)
    #     self.tb_outputs_listbox.delete(0, tk.END)
        
    #     for signal in self.tb_signals['inputs']:
    #         self.tb_inputs_listbox.insert(tk.END, signal)
        
    #     for signal in self.tb_signals['outputs']:
    #         self.tb_outputs_listbox.insert(tk.END, signal)
    
    def browse_verilog_file(self):
        """Browse for Verilog file and parse it"""
        filename = filedialog.askopenfilename(
            title="Select Verilog Module File",
            filetypes=[("Verilog files", "*.v"), ("All files", "*.*")]
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
    
    # def map_signals(self):
    #     """Map selected testbench signal to module signal"""
    #     # Check if input or output is selected in testbench
    #     tb_input_selection = self.tb_inputs_listbox.curselection()
    #     tb_output_selection = self.tb_outputs_listbox.curselection()
        
    #     if not tb_input_selection and not tb_output_selection:
    #         messagebox.showwarning("Warning", "Please select a testbench signal")
    #         return
        
    #     if tb_input_selection:
    #         tb_signal = self.tb_inputs_listbox.get(tb_input_selection[0])
    #         module_signal = self.module_inputs_combobox.get()
    #         if not module_signal:
    #             messagebox.showwarning("Warning", "Please select a module input signal")
    #             return
    #     else:
    #         tb_signal = self.tb_outputs_listbox.get(tb_output_selection[0])
    #         module_signal = self.module_outputs_combobox.get()
    #         if not module_signal:
    #             messagebox.showwarning("Warning", "Please select a module output signal")
    #             return
        
    #     # Add to mapping
    #     self.mapping[tb_signal] = module_signal
    #     self.update_mappings_display()
    
    # def clear_mapping(self):
    #     """Clear the current mapping for selected signal"""
    #     tb_input_selection = self.tb_inputs_listbox.curselection()
    #     tb_output_selection = self.tb_outputs_listbox.curselection()
        
    #     if not tb_input_selection and not tb_output_selection:
    #         messagebox.showwarning("Warning", "Please select a testbench signal to clear")
    #         return
        
    #     if tb_input_selection:
    #         tb_signal = self.tb_inputs_listbox.get(tb_input_selection[0])
    #     else:
    #         tb_signal = self.tb_outputs_listbox.get(tb_output_selection[0])
        
    #     if tb_signal in self.mapping:
    #         del self.mapping[tb_signal]
    #         self.update_mappings_display()
    
    # def update_mappings_display(self):
    #     """Update the mappings text display"""
    #     self.mappings_text.delete(1.0, tk.END)
    #     for tb_signal, module_signal in self.mapping.items():
    #         self.mappings_text.insert(tk.END, f"{tb_signal} -> {module_signal}\n")

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

        code = f"""
`timescale 1ns / 1ns

module DevelopmentBoard(
    input wire clk, //50MHz
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

        """

        code += f"""
{self.module_name} {self.module_name}_inst(
        """

        connections = []
        for module_signal, tb_signal in self.mapping.items():
            connections.append(f"        .{module_signal}({tb_signal})")
        code += ',\n'.join(connections)
        code += "\n    );\n\n"

        code += f"""
endmodule
        """

#         # Get current mappings for inputs and outputs
#         tb_inputs = {sig: self.mapping[sig] for sig in self.tb_signals['inputs'] if sig in self.mapping}
#         tb_outputs = {sig: self.mapping[sig] for sig in self.tb_signals['outputs'] if sig in self.mapping}
        
#         code = f"""// Verilog Testbench for {self.module_name}
# // Auto-generated by Verilog Testbench Generator

# `timescale 1ns/1ps

# module tb_{self.module_name};
# """
        
#         # Declare testbench signals
#         for signal in self.tb_signals['inputs']:
#             if signal in tb_inputs:
#                 code += f"    reg {signal};\n"
        
#         for signal in self.tb_signals['outputs']:
#             if signal in tb_outputs:
#                 code += f"    wire {signal};\n"
        
#         code += f"""
#     // Instantiate the Unit Under Test (UUT)
#     {self.module_name} uut (
# """
        
#         # Create port connections
#         connections = []
#         for tb_signal, module_signal in self.mapping.items():
#             connections.append(f"        .{module_signal}({tb_signal})")
        
#         code += ',\n'.join(connections)
#         code += "\n    );\n\n"
        
#         # Add clock generation if clk is mapped
#         if 'clk' in self.mapping:
#             code += """    // Clock generation
#     always #5 clk = ~clk;

# """
        
#         # Add test stimulus
#         code += """    // Test stimulus
#     initial begin
#         // Initialize inputs
# """
        
#         for signal in self.tb_signals['inputs']:
#             if signal in tb_inputs:
#                 code += f"        {signal} = 0;\n"
        
#         code += """
#         // Wait for global reset
#         #100;
        
#         // Add test cases here
#         $display("Testbench started");
        
#         // Example test sequence
# """
        
#         if 'reset' in tb_inputs:
#             code += """        reset = 1;
#         #20;
#         reset = 0;
#         #20;
# """
        
#         if 'start' in tb_inputs:
#             code += """        start = 1;
#         #10;
#         start = 0;
# """
        
#         code += """
#         // Monitor outputs
#         $monitor("Time: %0t, data_out: %h, valid: %b", $time, data_out, valid);
        
#         // Run simulation
#         #1000;
#         $display("Testbench completed");
#         $finish;
#     end

# endmodule
# """
        
        return code
    
    def reset(self):
        """Reset the application"""
        self.file_path_var.set("")
        self.module_signals = ['']
        self.mapping = {}
        for combobox_i in range(len(self.combobox_list)):
            self.combobox_list[combobox_i].set('')
        # self.module_inputs_combobox.set('')
        # self.module_outputs_combobox.set('')
        # self.mappings_text.delete(1.0, tk.END)
        if hasattr(self, 'module_name'):
            del self.module_name

def main():
    root = tk.Tk()
    app = VerilogTestbenchGenerator(root)
    root.mainloop()

if __name__ == "__main__":
    main()