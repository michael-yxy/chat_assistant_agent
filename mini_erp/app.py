import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
plt.switch_backend('Agg')

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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory_counts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                system_stock INTEGER,
                actual_stock INTEGER,
                discrepancy INTEGER,
                count_date TEXT DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
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

def calculate_z_score(service_level):
    z_table = {
        0.80: 0.84, 0.81: 0.88, 0.82: 0.92, 0.83: 0.95, 0.84: 0.99,
        0.85: 1.04, 0.86: 1.08, 0.87: 1.13, 0.88: 1.18, 0.89: 1.23,
        0.90: 1.28, 0.91: 1.34, 0.92: 1.41, 0.93: 1.48, 0.94: 1.56,
        0.95: 1.65, 0.96: 1.75, 0.97: 1.88, 0.98: 2.05, 0.99: 2.33
    }
    if service_level in z_table:
        return z_table[service_level]
    lower = max([k for k in z_table.keys() if k <= service_level])
    upper = min([k for k in z_table.keys() if k >= service_level])
    if lower == upper:
        return z_table[lower]
    t = (service_level - lower) / (upper - lower)
    return z_table[lower] + t * (z_table[upper] - z_table[lower])

def calculate_safety_stock(avg_demand, demand_std, lead_time, lead_time_std, service_level=0.95):
    z_value = calculate_z_score(service_level)
    variance_demand = (lead_time ** 2) * (demand_std ** 2)
    variance_lead_time = (avg_demand ** 2) * (lead_time_std ** 2)
    combined_std = np.sqrt(variance_demand + variance_lead_time)
    safety_stock = z_value * combined_std
    return int(np.ceil(safety_stock))

def calculate_reorder_point(avg_demand, lead_time, safety_stock):
    return int(avg_demand * lead_time + safety_stock)

def calculate_eoq(annual_demand, ordering_cost, holding_cost_rate, unit_cost):
    holding_cost = unit_cost * holding_cost_rate
    eoq = np.sqrt((2 * annual_demand * ordering_cost) / holding_cost)
    return int(np.ceil(eoq))

def view_inventory():
    st.subheader("📦 库存管理")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["库存列表", "添加商品", "库存预警", "动态优化", "库存盘点"])
    
    with tab1:
        products = db.fetch_df('SELECT * FROM products ORDER BY id DESC')
        st.dataframe(products, width='stretch')
        
        if not products.empty:
            selected_ids = st.multiselect("选择要删除的商品", products['id'], format_func=lambda x: f"{products[products['id'] == x]['name'].values[0]} (ID:{x})")
            if st.button("删除选中商品"):
                if selected_ids:
                    for pid in selected_ids:
                        db.execute('DELETE FROM products WHERE id = ?', (pid,))
                    st.success(f"成功删除 {len(selected_ids)} 个商品")
                    st.rerun()
                else:
                    st.warning("请选择要删除的商品")
    
    with tab2:
        with st.form("add_product_form"):
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
            
            if st.form_submit_button("添加商品"):
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
                        st.error("❌ 商品编码已存在")
    
    with tab3:
        low_stock = db.fetch_df('SELECT * FROM products WHERE stock <= min_stock')
        if len(low_stock) > 0:
            st.warning(f"⚠️ 有 {len(low_stock)} 种商品库存不足")
            st.dataframe(low_stock, width='stretch')
        else:
            st.success("🎉 所有商品库存充足")
    
    with tab4:
        st.markdown("### 🎯 动态库存优化分析")
        st.markdown("根据需求波动和采购提前期自动计算最优库存参数")
        
        products = db.fetch_df('SELECT * FROM products')
        if products.empty:
            st.info("暂无商品数据")
        else:
            sales = db.fetch_df('SELECT product_id, SUM(quantity) as total_sold, COUNT(*) as order_count FROM sales GROUP BY product_id')
            
            col1, col2 = st.columns(2)
            with col1:
                selected_product_id = st.selectbox("选择商品", products['id'], format_func=lambda x: products[products['id'] == x]['name'].values[0], key='opt_product')
            with col2:
                service_level = st.slider("服务水平 (%)", min_value=80, max_value=99, value=95, step=1)
                service_level = service_level / 100
            
            selected_product = products[products['id'] == selected_product_id].iloc[0]
            
            product_cost = float(selected_product['cost'])
            product_min_stock = int(selected_product['min_stock'])
            product_stock = int(selected_product['stock'])
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                avg_daily_demand = st.number_input("日均需求量", min_value=1, value=10, key='opt_demand')
            with col2:
                demand_std = st.number_input("需求标准差", min_value=0.0, value=3.0, step=0.1, key='opt_demand_std')
            with col3:
                lead_time = st.number_input("采购提前期(天)", min_value=1, value=7, key='opt_lead')
            with col4:
                lead_time_std = st.number_input("提前期标准差", min_value=0.0, value=2.0, step=0.1, key='opt_lead_std')
            
            col1, col2, col3 = st.columns(3)
            with col1:
                ordering_cost = st.number_input("订货成本(元)", min_value=1, value=500, key='opt_order_cost')
            with col2:
                holding_rate = st.number_input("持有成本率", min_value=0.01, max_value=1.0, value=0.25, step=0.01, format="%.2f", key='opt_holding')
            with col3:
                annual_demand = avg_daily_demand * 365
            
            safety_stock = calculate_safety_stock(avg_daily_demand, demand_std, lead_time, lead_time_std, service_level)
            reorder_point = calculate_reorder_point(avg_daily_demand, lead_time, safety_stock)
            eoq = calculate_eoq(annual_demand, ordering_cost, holding_rate, product_cost)
            
            st.markdown("---")
            st.markdown("### � 优化计算结果")
            
            actual_daily_sales = int(sales[sales['product_id'] == selected_product_id]['total_sold'].iloc[0]) if not sales.empty and selected_product_id in sales['product_id'].values else avg_daily_demand
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("安全库存", f"{safety_stock} {selected_product['unit']}", 
                         delta=f"建议增加" if safety_stock > product_min_stock else "当前充足")
            with col2:
                st.metric("再订货点", f"{reorder_point} {selected_product['unit']}")
            with col3:
                st.metric("经济订货量(EOQ)", f"{eoq} {selected_product['unit']}")
            with col4:
                if actual_daily_sales > 0:
                    current_turnover = product_stock / actual_daily_sales
                    st.metric("库存周转天数", f"{int(current_turnover)} 天")
                else:
                    st.metric("库存周转天数", "暂无销售数据", delta="请先产生销售记录")
            
            st.markdown("---")
            st.markdown("### 💡 优化建议")
            
            current_safety_stock = product_min_stock
            if safety_stock > current_safety_stock:
                st.warning(f"⚠️ 当前安全库存({current_safety_stock})低于建议值({safety_stock})，建议调整最低库存警戒线")
            
            if product_stock < reorder_point:
                st.error(f"🚨 当前库存({product_stock})已低于再订货点({reorder_point})，建议立即采购!")
            elif product_stock > reorder_point + eoq:
                st.info(f"ℹ️ 当前库存充足，建议暂不采购，等待库存降至再订货点附近")
            else:
                st.success(f"✅ 库存状态良好，继续监控")
            
            st.markdown("---")
            st.markdown("### 📈 库存ABC分类分析")
            
            if not sales.empty:
                # 确保列名匹配，使用left_on和right_on
                merged = products.merge(sales, left_on='id', right_on='product_id', how='left').fillna(0)
                merged['turnover_value'] = merged['total_sold'] * merged['cost']
                merged = merged.sort_values('turnover_value', ascending=False)
                merged['cumulative_pct'] = merged['turnover_value'].cumsum() / merged['turnover_value'].sum() * 100
                value_column = 'turnover_value'
                value_label = '周转价值'
            else:
                merged = products.copy()
                merged['inventory_value'] = merged['stock'] * merged['cost']
                merged = merged.sort_values('inventory_value', ascending=False)
                merged['cumulative_pct'] = merged['inventory_value'].cumsum() / merged['inventory_value'].sum() * 100
                value_column = 'inventory_value'
                value_label = '库存价值'
                st.info("💡 暂无销售数据，按库存价值进行ABC分类")
            
            def classify_abc(pct):
                if pct <= 80:
                    return 'A类'
                elif pct <= 95:
                    return 'B类'
                else:
                    return 'C类'
            
            merged['分类'] = merged['cumulative_pct'].apply(classify_abc)
            display_cols = ['name', 'category', 'stock', value_column, '分类']
            st.dataframe(merged[display_cols].rename(columns={value_column: value_label}), width='stretch')
            
            col1, col2, col3 = st.columns(3)
            with col1:
                a_count = len(merged[merged['分类'] == 'A类'])
                st.metric("A类商品(高价值)", f"{a_count} 种", delta="重点管理")
            with col2:
                b_count = len(merged[merged['分类'] == 'B类'])
                st.metric("B类商品(中等)", f"{b_count} 种", delta="常规管理")
            with col3:
                c_count = len(merged[merged['分类'] == 'C类'])
                st.metric("C类商品(低价值)", f"{c_count} 种", delta="简化管理")
    
    with tab5:
        st.markdown("### 📋 库存盘点")
        
        tab_count_new, tab_count_history = st.tabs(["新增盘点", "盘点记录"])
        
        with tab_count_new:
            products = db.fetch_df('SELECT * FROM products')
            if products.empty:
                st.info("暂无商品数据")
            else:
                st.info("记录实际盘点数量，系统将自动计算差异并调整库存")
                
                selected_product_id = st.selectbox("选择盘点商品", products['id'], format_func=lambda x: products[products['id'] == x]['name'].values[0], key='count_product')
                selected_product = products[products['id'] == selected_product_id].iloc[0]
                
                system_stock = int(selected_product['stock'])
                
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"系统库存: {system_stock} {selected_product['unit']}")
                with col2:
                    actual_stock = st.number_input("实际盘点数量", min_value=0, step=1, key='count_qty')
                
                discrepancy = int(actual_stock) - system_stock
                notes = st.text_area("盘点备注", placeholder="记录盘点情况、差异原因等")
                
                if st.button("📝 确认盘点"):
                    db.execute('INSERT INTO inventory_counts (product_id, system_stock, actual_stock, discrepancy, notes) VALUES (?, ?, ?, ?, ?)',
                              (selected_product_id, selected_product['stock'], actual_stock, discrepancy, notes))
                    db.execute('UPDATE products SET stock = ? WHERE id = ?', (actual_stock, selected_product_id))
                    
                    if discrepancy == 0:
                        st.success(f"✅ 盘点完成，库存一致，无需调整")
                    elif discrepancy > 0:
                        st.success(f"✅ 盘点完成，实际库存比系统多 {discrepancy} {selected_product['unit']}，已调整")
                    else:
                        st.warning(f"⚠️ 盘点完成，实际库存比系统少 {abs(discrepancy)} {selected_product['unit']}，已调整")
        
        with tab_count_history:
            count_history = db.fetch_df('''
                SELECT ic.*, p.name as product_name, p.unit 
                FROM inventory_counts ic
                LEFT JOIN products p ON ic.product_id = p.id
                ORDER BY ic.count_date DESC
            ''')
            
            if count_history.empty:
                st.info("暂无盘点记录")
            else:
                def safe_int_convert(value):
                    if isinstance(value, bytes):
                        try:
                            return int.from_bytes(value, byteorder='big')
                        except:
                            try:
                                return int(value.decode('utf-8'))
                            except:
                                return 0
                    try:
                        return int(value)
                    except:
                        return 0
                
                count_history['discrepancy'] = count_history['discrepancy'].apply(safe_int_convert)
                st.dataframe(count_history, width='stretch')
                
                total_discrepancy = count_history['discrepancy'].sum()
                positive_count = len(count_history[count_history['discrepancy'] > 0])
                negative_count = len(count_history[count_history['discrepancy'] < 0])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("盘点批次", len(count_history))
                with col2:
                    st.metric("盘盈批次", positive_count, delta="↑ 多于系统")
                with col3:
                    st.metric("盘亏批次", negative_count, delta="↓ 少于系统")

def view_purchases():
    st.subheader("�� 采购管理")
    
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
        
        with st.form("add_purchase_form"):
            supplier_id = st.selectbox("选择供应商", suppliers['id'], format_func=lambda x: suppliers[suppliers['id'] == x]['name'].values[0])
            product_id = st.selectbox("选择商品", products['id'], format_func=lambda x: products[products['id'] == x]['name'].values[0])
            
            selected_product = products[products['id'] == product_id].iloc[0]
            
            col1, col2 = st.columns(2)
            with col1:
                quantity = st.number_input("采购数量", min_value=1, step=1, value=1)
            with col2:
                unit_price = st.number_input("单价", min_value=0.01, step=0.01, value=selected_product['cost'], format="%.2f")
            
            total_amount = quantity * unit_price
            st.metric("采购总额", f"¥{total_amount:,.2f}")
            
            if st.form_submit_button("确认采购"):
                db.execute('INSERT INTO purchases (supplier_id, product_id, quantity, unit_price, total_amount) VALUES (?, ?, ?, ?, ?)',
                          (supplier_id, product_id, quantity, unit_price, total_amount))
                db.execute('UPDATE products SET stock = stock + ? WHERE id = ?', (quantity, product_id))
                st.success(f"✅ 采购成功! 已入库 {quantity} {selected_product['unit']}")

def view_sales():
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
        
        customer_id = st.selectbox("选择客户", customers['id'], format_func=lambda x: customers[customers['id'] == x]['name'].values[0], key='sale_customer')
        product_id = st.selectbox("选择商品", products['id'], format_func=lambda x: products[products['id'] == x]['name'].values[0], key='sale_product')
        
        selected_product = products[products['id'] == product_id].iloc[0]
        max_qty = int(selected_product['stock'])
        product_price = float(selected_product['price'])
        
        if max_qty <= 0:
            st.error(f"❌ 该商品库存不足! 当前库存: {max_qty} {selected_product['unit']}")
            st.info("请先采购该商品后再进行销售")
            return
        
        if 'last_sale_product' not in st.session_state or st.session_state['last_sale_product'] != product_id:
            st.session_state['sale_quantity'] = 1
            st.session_state['sale_price'] = product_price
            st.session_state['last_sale_product'] = product_id
        
        col1, col2 = st.columns(2)
        with col1:
            quantity = st.number_input("销售数量", min_value=1, max_value=max_qty, step=1, value=st.session_state['sale_quantity'], key='sale_qty_input')
        with col2:
            unit_price = st.number_input("单价", min_value=0.01, step=0.01, value=st.session_state['sale_price'], format="%.2f", key='sale_price_input')
        
        st.session_state['sale_quantity'] = quantity
        st.session_state['sale_price'] = unit_price
        
        total_amount = quantity * unit_price
        st.metric("销售总额", f"¥{total_amount:,.2f}")
        st.info(f"当前库存: {selected_product['stock']} {selected_product['unit']}")
        
        if st.button("确认销售"):
            current_product = db.fetch_df('SELECT * FROM products WHERE id = ?', (product_id,)).iloc[0]
            if quantity > current_product['stock']:
                st.error(f"❌ 库存不足! 当前库存: {current_product['stock']} {current_product['unit']}")
            else:
                db.execute('INSERT INTO sales (customer_id, product_id, quantity, unit_price, total_amount) VALUES (?, ?, ?, ?, ?)',
                          (customer_id, product_id, quantity, unit_price, total_amount))
                db.execute('UPDATE products SET stock = stock - ? WHERE id = ?', (quantity, product_id))
                st.success(f"✅ 销售成功! 已出库 {quantity} {current_product['unit']}")
                st.session_state['sale_quantity'] = 1
                st.session_state['sale_price'] = selected_product['price']

def view_suppliers():
    st.subheader("🏭 供应商管理")
    
    tab1, tab2 = st.tabs(["供应商列表", "添加供应商"])
    
    with tab1:
        suppliers = db.fetch_df('SELECT * FROM suppliers ORDER BY id DESC')
        st.dataframe(suppliers, width='stretch')
        
        if not suppliers.empty:
            selected_ids = st.multiselect("选择要删除的供应商", suppliers['id'], format_func=lambda x: f"{suppliers[suppliers['id'] == x]['name'].values[0]} (ID:{x})")
            if st.button("删除选中供应商"):
                if selected_ids:
                    for sid in selected_ids:
                        db.execute('DELETE FROM suppliers WHERE id = ?', (sid,))
                    st.success(f"成功删除 {len(selected_ids)} 个供应商")
                    st.rerun()
                else:
                    st.warning("请选择要删除的供应商")
    
    with tab2:
        with st.form("add_supplier_form"):
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
                    st.success(f"✅ 供应商 '{name}' 添加成功!")
                else:
                    st.error("请输入供应商名称")

def view_customers():
    st.subheader("👥 客户管理")
    
    tab1, tab2 = st.tabs(["客户列表", "添加客户"])
    
    with tab1:
        customers = db.fetch_df('SELECT * FROM customers ORDER BY id DESC')
        st.dataframe(customers, width='stretch')
        
        if not customers.empty:
            selected_ids = st.multiselect("选择要删除的客户", customers['id'], format_func=lambda x: f"{customers[customers['id'] == x]['name'].values[0]} (ID:{x})")
            if st.button("删除选中客户"):
                if selected_ids:
                    for cid in selected_ids:
                        db.execute('DELETE FROM customers WHERE id = ?', (cid,))
                    st.success(f"成功删除 {len(selected_ids)} 个客户")
                    st.rerun()
                else:
                    st.warning("请选择要删除的客户")
    
    with tab2:
        with st.form("add_customer_form"):
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
                    st.success(f"✅ 客户 '{name}' 添加成功!")
                else:
                    st.error("请输入客户名称")

def view_reports():
    st.subheader("📊 报表分析")
    
    tab1, tab2, tab3, tab4 = st.tabs(["库存统计", "销售报表", "采购报表", "利润分析"])
    
    with tab1:
        inventory = db.fetch_df('SELECT * FROM products')
        total_stock = inventory['stock'].sum()
        total_value = (inventory['stock'] * inventory['cost']).sum()
        
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
        sales_data = db.fetch_df('SELECT * FROM sales')
        purchases_data = db.fetch_df('SELECT * FROM purchases')
        products_data = db.fetch_df('SELECT * FROM products')
        
        total_sales = sales_data['total_amount'].sum()
        total_purchases = purchases_data['total_amount'].sum()
        current_inventory_cost = (products_data['stock'] * products_data['cost']).sum()
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

def main():
    st.title("📦 Mini ERP - 进销存管理系统")
    
    tabs = st.tabs(["库存管理", "采购管理", "销售管理", "供应商管理", "客户管理", "报表分析"])
    
    with tabs[0]:
        view_inventory()
    with tabs[1]:
        view_purchases()
    with tabs[2]:
        view_sales()
    with tabs[3]:
        view_suppliers()
    with tabs[4]:
        view_customers()
    with tabs[5]:
        view_reports()

if __name__ == '__main__':
    main()
