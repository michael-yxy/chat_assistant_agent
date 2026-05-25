import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="Mini ERP - 进销存系统", layout="wide")

class Database:
    def __init__(self, db_name='mini_erp.db'):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self._create_tables()
    
    def _create_tables(self):
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT UNIQUE NOT NULL,
                category TEXT,
                unit TEXT DEFAULT '件',
                price REAL NOT NULL,
                cost REAL NOT NULL,
                stock INTEGER DEFAULT 0,
                min_stock INTEGER DEFAULT 10,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT,
                phone TEXT,
                address TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT,
                phone TEXT,
                address TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id INTEGER,
                product_id INTEGER,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                total_amount REAL NOT NULL,
                purchase_date TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                product_id INTEGER,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                total_amount REAL NOT NULL,
                sale_date TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')
        
        self.conn.commit()
    
    def execute(self, query, params=()):
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()
        return cursor
    
    def fetch_df(self, query, params=()):
        return pd.read_sql(query, self.conn, params=params)

db = Database()

def init_sample_data():
    if db.fetch_df('SELECT COUNT(*) FROM products').iloc[0, 0] == 0:
        products = [
            ('iPhone 15 Pro', 'IP15PRO', '手机', '台', 8999, 7500, 50, 10),
            ('MacBook Pro 14', 'MBP14', '电脑', '台', 14999, 12000, 20, 5),
            ('AirPods Pro 2', 'APP2', '配件', '个', 1899, 1200, 100, 20),
            ('iPad Pro 12.9', 'IPDPRO', '平板', '台', 9299, 7800, 30, 8),
            ('Apple Watch Ultra', 'AWU', '手表', '个', 6299, 4800, 15, 5),
        ]
        for p in products:
            db.execute('INSERT INTO products (name, code, category, unit, price, cost, stock, min_stock) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', p)
        
        suppliers = [
            ('苹果中国有限公司', '张三', '13800138001', '上海市浦东新区'),
            ('深圳华强电子', '李四', '13900139002', '深圳市福田区'),
            ('广州数码城', '王五', '13600136003', '广州市天河区'),
        ]
        for s in suppliers:
            db.execute('INSERT INTO suppliers (name, contact, phone, address) VALUES (?, ?, ?, ?)', s)
        
        customers = [
            ('北京科技有限公司', '赵六', '13700137004', '北京市海淀区'),
            ('上海贸易公司', '钱七', '13500135005', '上海市静安区'),
            ('杭州电商平台', '孙八', '13400134006', '杭州市西湖区'),
        ]
        for c in customers:
            db.execute('INSERT INTO customers (name, contact, phone, address) VALUES (?, ?, ?, ?)', c)

init_sample_data()

def main():
    st.title("📦 Mini ERP - 进销存管理系统")
    
    menu = ["库存管理", "采购管理", "销售管理", "供应商管理", "客户管理", "报表分析"]
    choice = st.sidebar.selectbox("功能菜单", menu)
    
    if choice == "库存管理":
        manage_inventory()
    elif choice == "采购管理":
        manage_purchases()
    elif choice == "销售管理":
        manage_sales()
    elif choice == "供应商管理":
        manage_suppliers()
    elif choice == "客户管理":
        manage_customers()
    elif choice == "报表分析":
        show_reports()

def manage_inventory():
    st.subheader("📦 库存管理")
    
    tab1, tab2, tab3, tab4 = st.tabs(["库存列表", "添加/编辑商品", "库存预警", "商品分类"])
    
    with tab1:
        products = db.fetch_df('SELECT * FROM products ORDER BY id DESC')
        
        if not products.empty:
            st.dataframe(products, width='stretch')
            
            st.subheader("批量操作")
            selected_ids = st.multiselect(
                "选择要删除的商品",
                products['id'],
                format_func=lambda x: f"{products[products['id'] == x]['name'].values[0]} (ID:{x})"
            )
            
            if st.button("删除选中商品"):
                if selected_ids:
                    for product_id in selected_ids:
                        db.execute('DELETE FROM products WHERE id = ?', (product_id,))
                    st.success(f"成功删除 {len(selected_ids)} 个商品")
                else:
                    st.warning("请选择要删除的商品")
            
            st.subheader("单个商品操作")
            selected_id = st.selectbox(
                "选择商品查看详情", 
                products['id'], 
                format_func=lambda x: products[products['id'] == x]['name'].values[0],
                index=None,
                placeholder="请选择商品..."
            )
            
            if selected_id:
                product = products[products['id'] == selected_id].iloc[0]
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("当前库存", f"{product['stock']} {product['unit']}")
                with col2:
                    st.metric("售价", f"¥{product['price']:,.2f}")
                with col3:
                    st.metric("成本", f"¥{product['cost']:,.2f}")
                
                if st.button(f"删除商品: {product['name']}", key=f"delete_{selected_id}"):
                    db.execute('DELETE FROM products WHERE id = ?', (selected_id,))
                    st.success(f"商品 {product['name']} 已删除")
                    st.experimental_rerun()
        else:
            st.info("暂无商品数据，请先添加商品")
    
    with tab2:
        st.subheader("添加新商品")
        with st.form("add_product"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("商品名称", placeholder="如：笔记本电脑")
                code = st.text_input("商品编码", placeholder="如：NB001")
                category = st.text_input("商品分类", placeholder="如：电子产品")
                unit = st.text_input("单位", "件")
            with col2:
                price = st.number_input("售价", min_value=0.01, step=0.01, format="%.2f")
                cost = st.number_input("成本价", min_value=0.01, step=0.01, format="%.2f")
                stock = st.number_input("初始库存", min_value=0, step=1)
                min_stock = st.number_input("最低库存", min_value=0, step=1, value=10)
            
            submitted = st.form_submit_button("添加商品")
            if submitted:
                if not name:
                    st.error("请输入商品名称")
                elif not code:
                    st.error("请输入商品编码")
                elif price <= 0:
                    st.error("售价必须大于0")
                elif cost <= 0:
                    st.error("成本价必须大于0")
                else:
                    try:
                        db.execute('INSERT INTO products (name, code, category, unit, price, cost, stock, min_stock) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                                  (name, code, category, unit, price, cost, stock, min_stock))
                        st.success(f"✅ 商品 '{name}' 添加成功!")
                    except sqlite3.IntegrityError:
                        st.error("❌ 商品编码已存在，请使用其他编码")
    
    with tab3:
        low_stock = db.fetch_df('SELECT * FROM products WHERE stock <= min_stock')
        if len(low_stock) > 0:
            st.warning(f"⚠️ 有 {len(low_stock)} 种商品库存不足")
            st.dataframe(low_stock, width='stretch')
        else:
            st.success("🎉 所有商品库存充足")
    
    with tab4:
        categories = db.fetch_df('SELECT category, COUNT(*) as count, SUM(stock) as total_stock FROM products GROUP BY category')
        st.dataframe(categories, width='stretch')
        
        if not categories.empty:
            st.subheader("分类库存占比")
            fig, ax = plt.subplots()
            ax.pie(categories['total_stock'], labels=categories['category'], autopct='%1.1f%%')
            st.pyplot(fig)

def manage_suppliers():
    st.subheader("🏭 供应商管理")
    
    tab1, tab2 = st.tabs(["供应商列表", "添加供应商"])
    
    with tab1:
        suppliers = db.fetch_df('SELECT * FROM suppliers ORDER BY id DESC')
        st.dataframe(suppliers, width='stretch')
        
        if not suppliers.empty:
            selected_ids = st.multiselect(
                "选择要删除的供应商",
                suppliers['id'],
                format_func=lambda x: f"{suppliers[suppliers['id'] == x]['name'].values[0]} (ID:{x})"
            )
            
            if st.button("删除选中供应商"):
                if selected_ids:
                    for supplier_id in selected_ids:
                        db.execute('DELETE FROM suppliers WHERE id = ?', (supplier_id,))
                    st.success(f"成功删除 {len(selected_ids)} 个供应商")
                else:
                    st.warning("请选择要删除的供应商")
    
    with tab2:
        with st.form("add_supplier"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("供应商名称")
                contact = st.text_input("联系人")
            with col2:
                phone = st.text_input("联系电话")
                address = st.text_input("地址")
            
            if st.form_submit_button("添加供应商"):
                if name:
                    db.execute('INSERT INTO suppliers (name, contact, phone, address) VALUES (?, ?, ?, ?)',
                              (name, contact, phone, address))
                    st.success(f"供应商 '{name}' 添加成功!")
                else:
                    st.error("请输入供应商名称")

def manage_customers():
    st.subheader("👥 客户管理")
    
    tab1, tab2 = st.tabs(["客户列表", "添加客户"])
    
    with tab1:
        customers = db.fetch_df('SELECT * FROM customers ORDER BY id DESC')
        st.dataframe(customers, width='stretch')
        
        if not customers.empty:
            selected_ids = st.multiselect(
                "选择要删除的客户",
                customers['id'],
                format_func=lambda x: f"{customers[customers['id'] == x]['name'].values[0]} (ID:{x})"
            )
            
            if st.button("删除选中客户"):
                if selected_ids:
                    for customer_id in selected_ids:
                        db.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
                    st.success(f"成功删除 {len(selected_ids)} 个客户")
                else:
                    st.warning("请选择要删除的客户")
    
    with tab2:
        with st.form("add_customer"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("客户名称")
                contact = st.text_input("联系人")
            with col2:
                phone = st.text_input("联系电话")
                address = st.text_input("地址")
            
            if st.form_submit_button("添加客户"):
                if name:
                    db.execute('INSERT INTO customers (name, contact, phone, address) VALUES (?, ?, ?, ?)',
                              (name, contact, phone, address))
                    st.success(f"客户 '{name}' 添加成功!")
                else:
                    st.error("请输入客户名称")

def manage_purchases():
    st.subheader("📥 采购管理")
    
    tab1, tab2 = st.tabs(["采购记录", "新增采购"])
    
    with tab1:
        purchases = db.fetch_df('''
            SELECT p.*, s.name as supplier_name, pr.name as product_name, pr.unit 
            FROM purchases p
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            LEFT JOIN products pr ON p.product_id = pr.id
            ORDER BY p.purchase_date DESC
        ''')
        st.dataframe(purchases, width='stretch')
    
    with tab2:
        suppliers = db.fetch_df('SELECT * FROM suppliers')
        products = db.fetch_df('SELECT * FROM products')
        
        if suppliers.empty:
            st.error("请先添加供应商")
            return
        
        if products.empty:
            st.error("请先添加商品")
            return
        
        with st.form("add_purchase"):
            supplier_id = st.selectbox("选择供应商", suppliers['id'], format_func=lambda x: suppliers[suppliers['id'] == x]['name'].values[0])
            product_id = st.selectbox("选择商品", products['id'], format_func=lambda x: products[products['id'] == x]['name'].values[0])
            quantity = st.number_input("采购数量", min_value=1, step=1)
            
            product = products[products['id'] == product_id].iloc[0]
            unit_price = st.number_input("单价", min_value=0.01, step=0.01, value=product['cost'], format="%.2f")
            total_amount = quantity * unit_price
            st.metric("采购总额", f"¥{total_amount:,.2f}")
            
            if st.form_submit_button("确认采购"):
                db.execute('INSERT INTO purchases (supplier_id, product_id, quantity, unit_price, total_amount) VALUES (?, ?, ?, ?, ?)',
                          (supplier_id, product_id, quantity, unit_price, total_amount))
                db.execute('UPDATE products SET stock = stock + ? WHERE id = ?', (quantity, product_id))
                st.success(f"✅ 采购成功! 已入库 {quantity} {product['unit']}")

def manage_sales():
    st.subheader("📤 销售管理")
    
    tab1, tab2 = st.tabs(["销售记录", "新增销售"])
    
    with tab1:
        sales = db.fetch_df('''
            SELECT s.*, c.name as customer_name, pr.name as product_name, pr.unit 
            FROM sales s
            LEFT JOIN customers c ON s.customer_id = c.id
            LEFT JOIN products pr ON s.product_id = pr.id
            ORDER BY s.sale_date DESC
        ''')
        st.dataframe(sales, width='stretch')
    
    with tab2:
        customers = db.fetch_df('SELECT * FROM customers')
        products = db.fetch_df('SELECT * FROM products')
        
        if customers.empty:
            st.error("请先添加客户")
            return
        
        if products.empty:
            st.error("请先添加商品")
            return
        
        with st.form("add_sale"):
            customer_id = st.selectbox("选择客户", customers['id'], format_func=lambda x: customers[customers['id'] == x]['name'].values[0])
            product_id = st.selectbox("选择商品", products['id'], format_func=lambda x: products[products['id'] == x]['name'].values[0])
            
            selected_product = products[products['id'] == product_id].iloc[0]
            quantity_input = st.number_input("销售数量", min_value=1, max_value=int(selected_product['stock']), step=1, value=1)
            
            unit_price_input = st.number_input("单价", min_value=0.01, step=0.01, value=selected_product['price'], format="%.2f")
            total_amount = quantity_input * unit_price_input
            st.metric("销售总额", f"¥{total_amount:,.2f}")
            
            submitted = st.form_submit_button("确认销售")
            
        if submitted:
            current_product = db.fetch_df('SELECT * FROM products WHERE id = ?', (product_id,)).iloc[0]
            if quantity_input > current_product['stock']:
                st.error("❌ 库存不足!")
            else:
                db.execute('INSERT INTO sales (customer_id, product_id, quantity, unit_price, total_amount) VALUES (?, ?, ?, ?, ?)',
                          (customer_id, product_id, quantity_input, unit_price_input, total_amount))
                db.execute('UPDATE products SET stock = stock - ? WHERE id = ?', (quantity_input, product_id))
                st.success(f"✅ 销售成功! 已出库 {quantity_input} {current_product['unit']}")

def show_reports():
    st.subheader("📊 报表分析")
    
    tab1, tab2, tab3, tab4 = st.tabs(["库存统计", "销售报表", "采购报表", "利润分析"])
    
    with tab1:
        inventory = db.fetch_df('SELECT * FROM products')
        total_stock = inventory['stock'].sum()
        total_value = (inventory['stock'] * inventory['cost']).sum()
        total_sales_value = (inventory['stock'] * inventory['price']).sum()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("商品种类", len(inventory))
        with col2:
            st.metric("总库存数量", total_stock)
        with col3:
            st.metric("库存成本总值", f"¥{total_value:,.2f}")
        
        if not inventory.empty:
            st.subheader("库存价值分布")
            inventory['value'] = inventory['stock'] * inventory['cost']
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.bar(inventory['name'], inventory['value'])
            plt.xticks(rotation=45)
            st.pyplot(fig)
    
    with tab2:
        sales = db.fetch_df('SELECT * FROM sales')
        total_sales = sales['total_amount'].sum()
        total_qty = sales['quantity'].sum()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("销售订单数", len(sales))
        with col2:
            st.metric("销售总额", f"¥{total_sales:,.2f}")
        
        if not sales.empty:
            st.subheader("每日销售额趋势")
            sales['sale_date'] = pd.to_datetime(sales['sale_date'])
            daily_sales = sales.groupby(sales['sale_date'].dt.date)['total_amount'].sum()
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(daily_sales.index, daily_sales.values)
            plt.xticks(rotation=45)
            st.pyplot(fig)
    
    with tab3:
        purchases = db.fetch_df('SELECT * FROM purchases')
        total_purchases = purchases['total_amount'].sum()
        total_qty = purchases['quantity'].sum()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("采购订单数", len(purchases))
        with col2:
            st.metric("采购总额", f"¥{total_purchases:,.2f}")
    
    with tab4:
        sales = db.fetch_df('SELECT * FROM sales')
        purchases = db.fetch_df('SELECT * FROM purchases')
        
        total_sales = sales['total_amount'].sum()
        total_purchases = purchases['total_amount'].sum()
        
        products = db.fetch_df('SELECT * FROM products')
        current_inventory_cost = (products['stock'] * products['cost']).sum()
        
        gross_profit = total_sales - total_purchases
        profit_margin = (gross_profit / total_sales * 100) if total_sales > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("销售总额", f"¥{total_sales:,.2f}")
        with col2:
            st.metric("采购总额", f"¥{total_purchases:,.2f}")
        with col3:
            st.metric("毛利润", f"¥{gross_profit:,.2f}")
        with col4:
            st.metric("毛利率", f"{profit_margin:.2f}%")

import matplotlib.pyplot as plt
plt.switch_backend('Agg')

if __name__ == '__main__':
    main()