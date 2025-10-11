import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import sqlite3
import os
import hashlib
from openpyxl import Workbook
from datetime import datetime

# Set appearance mode and color theme
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


class PasswordDialog(ctk.CTkToplevel):
    """A dialog for password entry."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Enter Password")
        self.transient(parent)
        self.grab_set()

        self.password_ok = False

        self.label = ctk.CTkLabel(self, text="Please enter your password to proceed:")
        self.label.pack(padx=20, pady=(20, 10))

        self.password_entry = ctk.CTkEntry(self, show="*")
        self.password_entry.pack(padx=20, pady=10, fill="x")
        self.password_entry.focus()

        self.ok_button = ctk.CTkButton(self, text="OK", command=self.on_ok)
        self.ok_button.pack(side="left", padx=(20, 10), pady=20, expand=True)

        self.cancel_button = ctk.CTkButton(self, text="Cancel", command=self.on_cancel)
        self.cancel_button.pack(side="right", padx=(10, 20), pady=20, expand=True)

        self.password_entry.bind("<Return>", self.on_ok)

    def on_ok(self, event=None):
        entered_password = self.password_entry.get()
        if self.master.verify_password(entered_password):
            self.password_ok = True
            self.destroy()
        else:
            messagebox.showerror("Error", "Incorrect password.", parent=self)

    def on_cancel(self):
        self.password_ok = False
        self.destroy()

    def show(self):
        self.wait_window()
        return self.password_ok


class RetailApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Retail POS & Inventory")
        self.geometry("1200x700")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        app_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        os.makedirs(app_data_path, exist_ok=True)
        self.db_path = os.path.join(app_data_path, "retail.db")

        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.create_tables()

        self.navigation_frame = ctk.CTkFrame(self, corner_radius=0)
        self.navigation_frame.grid(row=0, column=0, sticky="nsew")
        self.navigation_frame.grid_rowconfigure(6, weight=1)

        self.navigation_frame_label = ctk.CTkLabel(self.navigation_frame, text="SAMARA trade center",
                                                   font=ctk.CTkFont(size=20, weight="bold"))
        self.navigation_frame_label.grid(row=0, column=0, padx=20, pady=20)

        # Navigation Buttons
        self.inventory_button = self.create_nav_button("Inventory", self.inventory_button_event, 1)
        self.pos_button = self.create_nav_button("POS", self.pos_button_event, 2)
        self.sales_button = self.create_nav_button("Sales", self.sales_button_event, 3)
        self.export_button = self.create_nav_button("Export to Excel", self.export_to_excel_secure, 4)
        self.settings_button = self.create_nav_button("Settings", self.settings_button_event, 5)

        self.inventory_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.pos_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.sales_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.settings_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")

        self.create_inventory_ui()
        self.create_pos_ui()
        self.create_sales_ui()
        self.create_settings_ui()

        self.select_frame_by_name("inventory")

    def create_nav_button(self, text, command, row):
        button = ctk.CTkButton(self.navigation_frame, corner_radius=0, height=40, text=text, font=ctk.CTkFont(size=14),
                               fg_color="transparent", text_color=("gray10", "gray90"),
                               hover_color=("gray70", "gray30"),
                               command=command)
        button.grid(row=row, column=0, sticky="ew")
        return button

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, entered_password):
        self.cursor.execute("SELECT password FROM settings WHERE id = 1")
        stored_hash = self.cursor.fetchone()
        if stored_hash:
            return stored_hash[0] == self.hash_password(entered_password)
        return False

    def ask_password(self):
        dialog = PasswordDialog(self)
        return dialog.show()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
                price REAL NOT NULL, quantity INTEGER NOT NULL)''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT, total_price REAL NOT NULL,
                sale_date TIMESTAMP DEFAULT (datetime('now', 'localtime')))''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sale_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT, sale_id INTEGER, product_id INTEGER,
                product_name TEXT, quantity INTEGER, price REAL,
                FOREIGN KEY (sale_id) REFERENCES sales (id),
                FOREIGN KEY (product_id) REFERENCES products (id))''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY CHECK (id = 1), password TEXT NOT NULL)''')

        # Set default password if not set
        self.cursor.execute("SELECT * FROM settings WHERE id = 1")
        if not self.cursor.fetchone():
            default_password_hash = self.hash_password("admin")
            self.cursor.execute("INSERT INTO settings (id, password) VALUES (1, ?)", (default_password_hash,))

        self.conn.commit()

    # --- Inventory Section ---
    def create_inventory_ui(self):
        form_frame = ctk.CTkFrame(self.inventory_frame)
        form_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkLabel(form_frame, text="Add/Update Product", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0,
                                                                                                           column=0,
                                                                                                           columnspan=2,
                                                                                                           padx=10,
                                                                                                           pady=10,
                                                                                                           sticky="w")

        self.product_id_entry = ctk.CTkEntry(form_frame, placeholder_text="Product ID (for updating)")
        self.product_id_entry.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.product_name_entry = ctk.CTkEntry(form_frame, placeholder_text="Name")
        self.product_name_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self.product_price_entry = ctk.CTkEntry(form_frame, placeholder_text="Price")
        self.product_price_entry.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self.product_qty_entry = ctk.CTkEntry(form_frame, placeholder_text="Quantity")
        self.product_qty_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkButton(form_frame, text="Add Product", command=self.add_product_secure).grid(row=3, column=0, padx=10,
                                                                                            pady=10, sticky="ew")
        ctk.CTkButton(form_frame, text="Update Product", command=self.update_product_secure).grid(row=3, column=1,
                                                                                                  padx=10, pady=10,
                                                                                                  sticky="ew")
        ctk.CTkButton(form_frame, text="Clear All Stock", command=self.clear_stock_secure, fg_color="red",
                      hover_color="darkred").grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        inventory_list_frame = ctk.CTkFrame(self.inventory_frame)
        inventory_list_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.inventory_tree = ttk.Treeview(inventory_list_frame, columns=("ID", "Name", "Price", "Quantity"),
                                           show='headings')
        self.inventory_tree.heading("ID", text="ID")
        self.inventory_tree.heading("Name", text="Name")
        self.inventory_tree.heading("Price", text="Price (Rs.)")
        self.inventory_tree.heading("Quantity", text="Quantity")
        self.inventory_tree.pack(fill="both", expand=True)
        self.inventory_tree.bind("<<TreeviewSelect>>", self.on_product_select)

        self.refresh_inventory_list()

    def refresh_inventory_list(self):
        for i in self.inventory_tree.get_children():
            self.inventory_tree.delete(i)
        self.cursor.execute("SELECT * FROM products")
        for row in self.cursor.fetchall():
            self.inventory_tree.insert("", "end", values=row)

    def add_product_secure(self):
        if self.ask_password():
            self.add_product()

    def add_product(self):
        name = self.product_name_entry.get()
        price_str = self.product_price_entry.get()
        qty_str = self.product_qty_entry.get()

        if not all([name, price_str, qty_str]):
            messagebox.showerror("Error", "Please fill out all fields.")
            return

        try:
            price = float(price_str)
            qty = int(qty_str)
            self.cursor.execute("INSERT INTO products (name, price, quantity) VALUES (?, ?, ?)", (name, price, qty))
            self.conn.commit()
            messagebox.showinfo("Success", f"Product '{name}' added.")
            self.clear_inventory_form()
            self.refresh_inventory_list()
        except ValueError:
            messagebox.showerror("Error", "Price must be a number and Quantity a whole number.")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"An error occurred: {e}")

    def update_product_secure(self):
        if self.ask_password():
            self.update_product()

    def update_product(self):
        product_id = self.product_id_entry.get()
        name = self.product_name_entry.get()
        price_str = self.product_price_entry.get()
        qty_str = self.product_qty_entry.get()

        if not product_id:
            messagebox.showerror("Error", "Please select a product to update or enter a product ID.")
            return

        if not all([name, price_str, qty_str]):
            messagebox.showerror("Error", "Please fill out all fields for updating.")
            return

        try:
            price = float(price_str)
            qty = int(qty_str)
            self.cursor.execute("UPDATE products SET name=?, price=?, quantity=? WHERE id=?",
                                (name, price, qty, product_id))
            self.conn.commit()
            messagebox.showinfo("Success", f"Product ID '{product_id}' updated.")
            self.clear_inventory_form()
            self.refresh_inventory_list()
        except ValueError:
            messagebox.showerror("Error", "Price must be a number and Quantity a whole number.")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"An error occurred: {e}")

    def clear_stock_secure(self):
        if self.ask_password():
            self.clear_stock()

    def clear_stock(self):
        if messagebox.askyesno("Confirm Clear Stock",
                               "Are you sure you want to delete ALL products? This action cannot be undone."):
            try:
                self.cursor.execute("DELETE FROM products")
                self.cursor.execute("DELETE FROM sqlite_sequence WHERE name='products'")
                self.conn.commit()
                messagebox.showinfo("Success", "All products have been cleared from the inventory.")
                self.refresh_inventory_list()
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"An error occurred: {e}")

    def on_product_select(self, event):
        selected_item = self.inventory_tree.focus()
        if not selected_item:
            return
        item = self.inventory_tree.item(selected_item)
        values = item['values']
        self.product_id_entry.delete(0, tk.END)
        self.product_id_entry.insert(0, values[0])
        self.product_name_entry.delete(0, tk.END)
        self.product_name_entry.insert(0, values[1])
        self.product_price_entry.delete(0, tk.END)
        self.product_price_entry.insert(0, values[2])
        self.product_qty_entry.delete(0, tk.END)
        self.product_qty_entry.insert(0, values[3])

    def clear_inventory_form(self):
        self.product_id_entry.delete(0, tk.END)
        self.product_name_entry.delete(0, tk.END)
        self.product_price_entry.delete(0, tk.END)
        self.product_qty_entry.delete(0, tk.END)

    # --- POS Section ---
    def create_pos_ui(self):
        pos_left_frame = ctk.CTkFrame(self.pos_frame)
        pos_left_frame.pack(side="left", fill="both", expand=True, padx=20, pady=20)

        # Search Area
        ctk.CTkLabel(pos_left_frame, text="Search Products", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)
        self.search_entry = ctk.CTkEntry(pos_left_frame, placeholder_text="Search by name...")
        self.search_entry.pack(fill="x", padx=10, pady=5)
        self.search_entry.bind("<KeyRelease>", self.search_product)

        self.product_listbox = tk.Listbox(pos_left_frame, font=("Arial", 12))
        self.product_listbox.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        self.populate_product_listbox()
        self.product_listbox.bind("<<ListboxSelect>>", self.on_pos_product_select)

        # Add to Cart Area
        add_frame = ctk.CTkFrame(pos_left_frame)
        add_frame.pack(fill="x", padx=10, pady=10)

        self.pos_product_label = ctk.CTkLabel(add_frame, text="Select a product", font=ctk.CTkFont(size=14))
        self.pos_product_label.pack(pady=5)

        self.pos_qty_entry = ctk.CTkEntry(add_frame, placeholder_text="Quantity")
        self.pos_qty_entry.pack(fill="x", pady=5)
        self.pos_qty_entry.insert(0, "1")

        ctk.CTkButton(add_frame, text="Add to Cart", command=self.add_to_cart_secure).pack(fill="x", pady=10)

        # Cart (Right Side)
        pos_right_frame = ctk.CTkFrame(self.pos_frame)
        pos_right_frame.pack(side="right", fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(pos_right_frame, text="Cart", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)

        self.cart_tree = ttk.Treeview(pos_right_frame, columns=("ID", "Name", "Price", "Quantity"), show='headings')
        self.cart_tree.heading("ID", text="ID")
        self.cart_tree.heading("Name", text="Name")
        self.cart_tree.heading("Price", text="Price (Rs.)")
        self.cart_tree.heading("Quantity", text="Quantity")
        self.cart_tree.pack(fill="both", expand=True, padx=10, pady=10)

        self.total_label = ctk.CTkLabel(pos_right_frame, text="Total: Rs.0.00",
                                        font=ctk.CTkFont(size=18, weight="bold"))
        self.total_label.pack(pady=10)

        ctk.CTkButton(pos_right_frame, text="Checkout", command=self.checkout_secure).pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(pos_right_frame, text="Clear Cart", command=self.clear_cart).pack(fill="x", padx=10, pady=5)

        self.cart = {}
        self.selected_pos_product_id = None

    def populate_product_listbox(self):
        self.product_listbox.delete(0, tk.END)
        self.cursor.execute("SELECT id, name, price, quantity FROM products WHERE quantity > 0")
        for row in self.cursor.fetchall():
            self.product_listbox.insert(tk.END, f"{row[0]} - {row[1]} (Rs.{row[2]}) - Stock: {row[3]}")

    def search_product(self, event):
        search_term = self.search_entry.get()
        self.product_listbox.delete(0, tk.END)
        self.cursor.execute("SELECT id, name, price, quantity FROM products WHERE name LIKE ? AND quantity > 0",
                            (f"%{search_term}%",))
        for row in self.cursor.fetchall():
            self.product_listbox.insert(tk.END, f"{row[0]} - {row[1]} (Rs.{row[2]}) - Stock: {row[3]}")

    def on_pos_product_select(self, event):
        if not self.product_listbox.curselection():
            return
        selected_product_str = self.product_listbox.get(self.product_listbox.curselection())
        self.selected_pos_product_id = int(selected_product_str.split(" - ")[0])
        product_name = selected_product_str.split(" - ")[1].split(" (Rs.")[0]
        self.pos_product_label.configure(text=f"Selected: {product_name}")
        self.pos_qty_entry.delete(0, tk.END)
        self.pos_qty_entry.insert(0, "1")

    def add_to_cart_secure(self):
        if self.selected_pos_product_id is None:
            messagebox.showerror("Error", "Please select a product first.")
            return

        try:
            quantity = int(self.pos_qty_entry.get())
            if quantity <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid quantity.")
            return

        self.add_to_cart(self.selected_pos_product_id, quantity)

    def add_to_cart(self, product_id, quantity):
        self.cursor.execute("SELECT name, price, quantity FROM products WHERE id=?", (product_id,))
        product = self.cursor.fetchone()
        if not product:
            return

        stock = product[2]

        current_cart_qty = self.cart.get(product_id, {}).get('quantity', 0)

        if (quantity + current_cart_qty) > stock:
            messagebox.showwarning("Out of Stock",
                                   f"Cannot add {quantity}. Only {stock - current_cart_qty} more available.")
            return

        if product_id in self.cart:
            self.cart[product_id]['quantity'] += quantity
        else:
            self.cart[product_id] = {'name': product[0], 'price': product[1], 'quantity': quantity}

        self.refresh_cart_tree()

    def refresh_cart_tree(self):
        for i in self.cart_tree.get_children():
            self.cart_tree.delete(i)
        total = sum(item['price'] * item['quantity'] for item in self.cart.values())
        self.total_label.configure(text=f"Total: Rs.{total:.2f}")
        for pid, item in self.cart.items():
            self.cart_tree.insert("", "end", values=(pid, item['name'], item['price'], item['quantity']))

    def clear_cart(self):
        self.cart = {}
        self.refresh_cart_tree()
        self.pos_product_label.configure(text="Select a product")
        self.selected_pos_product_id = None

    def checkout_secure(self):
        if self.ask_password():
            self.checkout()

    def checkout(self):
        if not self.cart:
            messagebox.showerror("Error", "Cart is empty.")
            return

        total_price = sum(item['price'] * item['quantity'] for item in self.cart.values())

        try:
            self.cursor.execute("INSERT INTO sales (total_price) VALUES (?)", (total_price,))
            sale_id = self.cursor.lastrowid

            for product_id, item in self.cart.items():
                self.cursor.execute(
                    "INSERT INTO sale_items (sale_id, product_id, product_name, quantity, price) VALUES (?, ?, ?, ?, ?)",
                    (sale_id, product_id, item['name'], item['quantity'], item['price']))
                self.cursor.execute("UPDATE products SET quantity = quantity - ? WHERE id = ?",
                                    (item['quantity'], product_id))

            self.conn.commit()
            messagebox.showinfo("Success", "Checkout complete.")
            self.clear_cart()
            self.populate_product_listbox()
            self.refresh_sales_list()

        except sqlite3.Error as e:
            self.conn.rollback()
            messagebox.showerror("Database Error", f"An error occurred during checkout: {e}")

    # --- Sales Section ---
    def create_sales_ui(self):
        sales_main_frame = ctk.CTkFrame(self.sales_frame)
        sales_main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        sales_main_frame.grid_columnconfigure(1, weight=1)
        sales_main_frame.grid_rowconfigure(0, weight=1)

        sales_list_frame = ctk.CTkFrame(sales_main_frame)
        sales_list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        sales_list_frame.grid_rowconfigure(1, weight=1)

        controls_frame = ctk.CTkFrame(sales_list_frame)
        controls_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(controls_frame, text="Sales History", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left",
                                                                                                          padx=10)
        ctk.CTkButton(controls_frame, text="Clear All Sales", command=self.clear_sales_secure, fg_color="red",
                      hover_color="darkred").pack(side="right", padx=10)

        self.sales_tree = ttk.Treeview(sales_list_frame, columns=("ID", "Total", "Date"), show='headings')
        self.sales_tree.heading("ID", text="Sale ID")
        self.sales_tree.heading("Total", text="Total (Rs.)")
        self.sales_tree.heading("Date", text="Date")
        self.sales_tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.sales_tree.bind("<<TreeviewSelect>>", self.on_sale_select)

        sale_details_frame = ctk.CTkFrame(sales_main_frame)
        sale_details_frame.grid(row=0, column=1, sticky="nsew")
        sale_details_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(sale_details_frame, text="Sale Details", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        self.sale_items_tree = ttk.Treeview(sale_details_frame, columns=("Product", "Qty", "Price"), show='headings')
        self.sale_items_tree.heading("Product", text="Product")
        self.sale_items_tree.heading("Qty", text="Quantity")
        self.sale_items_tree.heading("Price", text="Price (Rs.)")
        self.sale_items_tree.pack(fill="both", expand=True, padx=10, pady=10)

        self.refresh_sales_list()

    def refresh_sales_list(self):
        for i in self.sales_tree.get_children():
            self.sales_tree.delete(i)
        self.cursor.execute("SELECT id, total_price, sale_date FROM sales ORDER BY sale_date DESC")
        for row in self.cursor.fetchall():
            self.sales_tree.insert("", "end", values=row)

    def on_sale_select(self, event):
        selected_item = self.sales_tree.focus()
        if not selected_item:
            return

        sale_id = self.sales_tree.item(selected_item)['values'][0]

        for i in self.sale_items_tree.get_children():
            self.sale_items_tree.delete(i)
        self.cursor.execute("SELECT product_name, quantity, price FROM sale_items WHERE sale_id=?", (sale_id,))
        for row in self.cursor.fetchall():
            self.sale_items_tree.insert("", "end", values=row)

    def clear_sales_secure(self):
        if self.ask_password():
            self.clear_sales()

    def clear_sales(self):
        if messagebox.askyesno("Confirm Clear Sales",
                               "Are you sure you want to delete ALL sales history? This action cannot be undone."):
            try:
                self.cursor.execute("DELETE FROM sales")
                self.cursor.execute("DELETE FROM sale_items")
                self.cursor.execute("DELETE FROM sqlite_sequence WHERE name='sales'")
                self.cursor.execute("DELETE FROM sqlite_sequence WHERE name='sale_items'")
                self.conn.commit()
                messagebox.showinfo("Success", "All sales history has been cleared.")
                self.refresh_sales_list()
                for i in self.sale_items_tree.get_children():
                    self.sale_items_tree.delete(i)
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"An error occurred: {e}")

    # --- Export Section ---
    def export_to_excel_secure(self):
        if self.ask_password():
            self.export_to_excel()

    def export_to_excel(self):
        filename = filedialog.asksaveasfilename(
            initialfile=f"retail_export_{datetime.now().strftime('%Y%m%d')}.xlsx",
            defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")])
        if not filename:
            return

        try:
            wb = Workbook()
            ws_products = wb.active
            ws_products.title = "Products"
            ws_products.append(["ID", "Name", "Price (Rs.)", "Quantity"])
            for row in self.cursor.execute("SELECT * FROM products"):
                ws_products.append(row)

            ws_sales = wb.create_sheet(title="Recent Sales")
            ws_sales.append(["Sale ID", "Total Price (Rs.)", "Date"])
            today_sales = self.cursor.execute(
                "SELECT id, total_price, sale_date FROM sales WHERE date(sale_date) = date('now')").fetchall()
            sale_ids = [row[0] for row in today_sales]
            for row in today_sales:
                ws_sales.append(row)

            ws_sale_items = wb.create_sheet(title="Recent Sale Items")
            ws_sale_items.append(["Sale Item ID", "Sale ID", "Product ID", "Product Name", "Quantity", "Price (Rs.)"])
            if sale_ids:
                placeholders = ','.join('?' for _ in sale_ids)
                query = f"SELECT id, sale_id, product_id, product_name, quantity, price FROM sale_items WHERE sale_id IN ({placeholders})"
                for row in self.cursor.execute(query, sale_ids):
                    ws_sale_items.append(row)

            wb.save(filename)
            messagebox.showinfo("Success", f"Data exported to {filename}")

        except Exception as e:
            messagebox.showerror("Export Error", f"An error occurred during export: {e}")

    # --- Settings Section ---
    def create_settings_ui(self):
        settings_main_frame = ctk.CTkFrame(self.settings_frame)
        settings_main_frame.pack(padx=20, pady=20, fill="x")

        ctk.CTkLabel(settings_main_frame, text="Change Password", font=ctk.CTkFont(size=18, weight="bold")).pack(
            pady=(0, 10))

        self.old_password_entry = ctk.CTkEntry(settings_main_frame, placeholder_text="Old Password", show="*")
        self.old_password_entry.pack(fill="x", padx=20, pady=5)

        self.new_password_entry = ctk.CTkEntry(settings_main_frame, placeholder_text="New Password", show="*")
        self.new_password_entry.pack(fill="x", padx=20, pady=5)

        self.confirm_password_entry = ctk.CTkEntry(settings_main_frame, placeholder_text="Confirm New Password",
                                                   show="*")
        self.confirm_password_entry.pack(fill="x", padx=20, pady=5)

        ctk.CTkButton(settings_main_frame, text="Save New Password", command=self.change_password).pack(padx=20,
                                                                                                        pady=20)

    def change_password(self):
        old_password = self.old_password_entry.get()
        new_password = self.new_password_entry.get()
        confirm_password = self.confirm_password_entry.get()

        if not self.verify_password(old_password):
            messagebox.showerror("Error", "Old password is not correct.")
            return

        if not new_password:
            messagebox.showerror("Error", "New password cannot be empty.")
            return

        if new_password != confirm_password:
            messagebox.showerror("Error", "New passwords do not match.")
            return

        try:
            new_password_hash = self.hash_password(new_password)
            self.cursor.execute("UPDATE settings SET password = ? WHERE id = 1", (new_password_hash,))
            self.conn.commit()
            messagebox.showinfo("Success", "Password changed successfully.")
            self.old_password_entry.delete(0, tk.END)
            self.new_password_entry.delete(0, tk.END)
            self.confirm_password_entry.delete(0, tk.END)
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"An error occurred: {e}")

    # --- Frame Navigation ---
    def select_frame_by_name(self, name):
        buttons = {"inventory": self.inventory_button, "pos": self.pos_button, "sales": self.sales_button,
                   "settings": self.settings_button}
        frames = {"inventory": self.inventory_frame, "pos": self.pos_frame, "sales": self.sales_frame,
                  "settings": self.settings_frame}

        for frame_name, button in buttons.items():
            button.configure(fg_color=("gray75", "gray25") if name == frame_name else "transparent")

        for frame in frames.values():
            frame.grid_forget()

        frames[name].grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        if name == "inventory":
            self.refresh_inventory_list()
        elif name == "pos":
            self.populate_product_listbox()
        elif name == "sales":
            self.refresh_sales_list()

    def inventory_button_event(self):
        self.select_frame_by_name("inventory")

    def pos_button_event(self):
        self.select_frame_by_name("pos")

    def sales_button_event(self):
        self.select_frame_by_name("sales")

    def settings_button_event(self):
        self.select_frame_by_name("settings")


if __name__ == "__main__":
    app = RetailApp()
    app.mainloop()
    app.conn.close()