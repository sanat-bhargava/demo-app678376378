import streamlit as st
import pandas as pd
import pymysql
import plotly.express as px
import time
from plotly.subplots import make_subplots
import plotly.graph_objects as go

DB_HOST = "tellmoredb.cd24ogmcy170.us-east-1.rds.amazonaws.com"
DB_USER = "admin"
DB_PASS = "2yYKKH8lUzaBvc92JUxW"
DB_PORT = "3306"
DB_NAME = "retail_panopticon"
CONVO_DB_NAME = "store_questions"

if 'history' not in st.session_state:
    st.session_state['history'] = []

if 'display_df_and_nlr' not in st.session_state:
    st.session_state['display_df_and_nlr'] = False

if 'user_input' not in st.session_state:
    st.session_state['user_input'] = ""

personas = [
    "Select a Persona",
    "INVENTORY OPS",
    "LOSS PREVENTION OPS",
    "MARKETING OPS",
    "STORE OPS",
    "MERCHANDISING OPS",
    "WAREHOUSE OPS"
]


def connect_to_db(db_name):
    return pymysql.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        user=DB_USER,
        password=DB_PASS,
        db=db_name
    )


def execute_query(query, connection):
    # try:
    with connection.cursor() as cursor:
        cursor.execute(query)
        getResult = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
    return pd.DataFrame(getResult, columns=columns)
    # finally:
    #     connection.close()


def store_question_in_db(question, sql_query):
    connection = connect_to_db(CONVO_DB_NAME)
    query = "INSERT INTO store_questions (question, sql_query) VALUES (%s, %s)"
    try:
        with connection.cursor() as cursor:
            # cursor.execute(query, (question, sql_query, response)) # issue no. 1
            cursor.execute(query, (question, sql_query))
        connection.commit()
    finally:
        connection.close()


def get_queries_from_db(persona):
    connection = connect_to_db(CONVO_DB_NAME)
    query = f"SELECT DISTINCT question, sql_query FROM {persona}_questions;"
    df = execute_query(query, connection)
    questions = {"Select a query": None}
    questions.update(dict(zip(df['question'], df['sql_query'])))
    return questions

# Utility functions for st.form

def submitted():
    st.session_state.submitted = True
def reset():
    st.session_state.submitted = False

def set_custom_css():
    custom_css = """
    <style>
        .st-emotion-cache-9aoz2h.e1vs0wn30 {
            display: flex;
            justify-content: center; /* Center-align the DataFrame */
        }
        .st-emotion-cache-9aoz2h.e1vs0wn30 table {
            margin: 0 auto; /* Center-align the table itself */
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


def create_figures(data, query):
    con = connect_to_db("retail_panopticon")
    if query == "For this store, which products are running low on inventory and have a per unit value greater than 50?":
        fig_bar = px.bar(data,
                         x='Description',
                         y='Stock_Availability',
                         title='Stock Availability by Product',
                         labels={'Stock_Availability': 'Units in Stock', 'Description': 'Product Description'})
        fig_bubble = px.scatter(data,
                                      x='Unit_Price',
                                      y='Stock_Availability',
                                      size='Stock_Availability',
                                      color='Description',
                                      title='Bubble Chart: Unit Price vs. Stock Availability',
                                      labels={'Unit_Price': 'Unit Price', 'Stock_Availability': 'Units in Stock'})

        figures = [fig_bar, fig_bubble]
        return figures

    if query == "Give a daily breakdown UPT for all product categories for each store during May":
        pie_fig = px.pie(
            data,
            values='UPT',
            names='Product_Category',
            title='Sum of UPT by Product Category'
        )

        bar_fig = px.bar(
            data,
            x='UPT',
            y='Store_ID',
            orientation='h', 
            title='Sum of UPT by Store_ID'
        )
        bar_fig.update_layout(yaxis={'categoryorder': 'total ascending'})  

        filtered_data = data[data['Product_Category'].isin(['Clothing', 'Toys'])]
        line_fig = px.line(
            filtered_data,
            x='Sale_Date',
            y='UPT',
            color='Product_Category',
            title='Product Category Sales report'
        )
        line_fig.update_layout(
            xaxis_title='Sale_Date',
            yaxis_title='Sum of UPT',
            legend_title='Product Category'
        )

        figures = [pie_fig, bar_fig, line_fig]
        return figures

    if query == "How do we optimize inventory levels and replenishment for high-stockout products to match sales and reduce stockouts?":
        bar_fig_sales = px.bar(
            data,
            x='Total_Sales',
            y='Description',
            title='Sum of Total Sales by Description',
            orientation='h'
        )
        bar_fig_sales.update_layout(
            xaxis_title='Total_Sales',
            yaxis_title='Description',
            yaxis={'categoryorder': 'total ascending'}
        )

        fig_inventory_sales = px.bar(
            data,
            x='Description',
            y='Average_Monthly_Inventory_Level',
            title='Sum of Average Monthly Inventory Level by Description',
            barmode='stack',
            color_discrete_sequence=['#FFFF00']
        )
        fig_inventory_sales.update_layout(
            xaxis_title='Description',
            xaxis={'categoryorder': 'total ascending'},
            yaxis_title='Average Monthly Inventory Level'
        )

        figures = [bar_fig_sales, fig_inventory_sales]
        return figures

    if query == "What was the impact of the promotional discounts offered in May on the weekend vs. weekday sales for all product categories?":
        total_sales_per_category = data.groupby('Category')['total_sales'].sum().reset_index()
        df = data.merge(total_sales_per_category, on='Category', suffixes=('', '_total'))
        fig2 = px.bar(
            df,
            y='Category',
            x='total_sales',
            color='day_type',
            title='Total Sales for Each Product Category',
            labels={'total_sales': 'Total Sales', 'Category': 'Product Category'},
            barmode='group',
            orientation='h',
            color_discrete_map={'Weekday': 'goldenrod', 'Weekend': 'dodgerblue'}
        )

        fig3 = px.bar(
            df,
            x='Category',
            y='avg_transaction_value',
            color='day_type',
            title='Average Transaction Value for Each Product Category',
            labels={'avg_transaction_value': 'Average Transaction Value', 'Category': 'Product Category'},
            barmode='stack',
            text_auto=True,
            color_discrete_map={'Weekday': 'orange', 'Weekend': 'purple'}
        )

        total_sales_per_category = data.groupby('Category')['total_sales'].sum().reset_index()
        df = data.merge(total_sales_per_category, on='Category', suffixes=('', '_total'))
        df['sales_percentage'] = df['total_sales'] / df['total_sales_total'] * 100
        fig = px.bar(
            df,
            x='Category',
            y='sales_percentage',
            color='day_type',
            title='Total Sales Percentage for Each Product Category',
            labels={'sales_percentage': 'Percentage of Total Sales', 'Category': 'Product Category'},
            text_auto=True,
            barmode='stack'
        )

        fig1 = px.bar(
            df,
            y='Category',
            x='total_transactions',
            color='day_type',
            title='Total Transactions for Each Product Category',
            labels={'total_transactions': 'Total Transactions', 'Category': 'Product Category'},
            barmode='group',
            orientation='h',
            color_discrete_map={'Weekday': 'mediumseagreen', 'Weekend': 'tomato'}
        )

        figures = [fig2, fig3, fig, fig1]
        return figures
    
    if query == "Give the total shipments delivered late and the reason for the delay for each product category":
        fig_pie = px.sunburst(
                    data,
                    path=['Category', 'Reason_Late_Shipment'],
                    values='Total_Late_Shipments',
                    title='Reasons for Late Shipments by Product Category',
                    color='Reason_Late_Shipment',
                    color_discrete_sequence=px.colors.qualitative.Set3  
                )
        
        total_shipments_by_category = data.groupby('Category')['Total_Late_Shipments'].sum().reset_index()
        fig_bar = px.bar(
                    total_shipments_by_category,
                    y='Category',
                    x='Total_Late_Shipments',
                    title='Total Late Shipments by Product Category',
                    labels={'Total_Late_Shipments': 'Total Late Shipments'},
                    color='Category',
                    color_discrete_sequence=px.colors.qualitative.Pastel  
                )
                
        figures = [fig_pie, fig_bar]
        return figures

    # Merchandizing Agentic App
    if query == "What are the top 3 most common reasons for delays in order fulfillment and which product categories are most severely affected by delays?":
        df = pd.read_sql_query("""SELECT p.Category, o.Delay_Reason, COUNT(o.Transaction_ID) AS Delay_Count
            FROM retail_panopticon.orderFulfillment o
            JOIN retail_panopticon.transactions t ON o.Transaction_ID = t.Transaction_ID
            JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID
            WHERE o.`On-Time_Fulfillment_Rate` < 100 AND o.Delay_Reason IS NOT NULL
               AND o.Delay_Reason != ''
            GROUP BY p.Category, o.Delay_Reason
            ORDER BY Delay_Count DESC;""",con)

        top_3_reasons = df.groupby('Delay_Reason')['Delay_Count'].sum().nlargest(3).reset_index()

        # Plotting
        fig_bar_delay = px.bar(top_3_reasons, x='Delay_Reason', y='Delay_Count',
                     title='Top 3 Most Common Reasons for Delays in Order Fulfillment',
                     labels={'Delay_Reason': 'Delay Reason', 'Delay_Count': 'Number of Delays'})

        filtered_df = df[df['Delay_Reason'].isin(top_3_reasons['Delay_Reason'])]
        # Plotting
        fig_bar_delay_category = px.bar(filtered_df, x='Category', y='Delay_Count', color='Delay_Reason',
                     title='Top 3 Delay Reasons by Product Category',
                     labels={'Category': 'Product Category', 'Delay_Count': 'Number of Delays',
                             'Delay_Reason': 'Delay Reason'},
                     barmode='stack')

        # Pivoting the dataframe for heatmap
        heatmap_df = df.pivot(index='Category', columns='Delay_Reason', values='Delay_Count').fillna(0)
        # Plotting
        fig_heatmap = px.imshow(heatmap_df,
                        title='Heatmap of Delay Reasons Across Product Categories',
                        labels={'x': 'Delay Reason', 'y': 'Product Category', 'color': 'Number of Delays'},
                        aspect='auto')

        figures = [fig_bar_delay, fig_bar_delay_category,fig_heatmap]
        return figures

    if query == "Which products in this category have the highest rates of replacement requests?":
        df = pd.read_sql_query("""SELECT p.Product_ID,p.Product_Description,p.Category, ROUND(AVG(r.Replacement_Order_Frequency), 2) AS Avg_Replacement_Frequency
             FROM retail_panopticon.replacementsAndDefects r 
            JOIN retail_panopticon.transactions t ON r.Transaction_ID = t.Transaction_ID 
            JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID 
            GROUP BY p.Product_ID,p.Product_Description,p.Category 
            ORDER BY Avg_Replacement_Frequency DESC LIMIT 10;""", con)

        fig_bar = px.bar(df, x='Product_Description', y='Avg_Replacement_Frequency',
                     title='Top 10 Products by Average Replacement Frequency',
                     labels={'Product_Description': 'Product',
                             'Avg_Replacement_Frequency': 'Avg Replacement Frequency'},
                     text='Avg_Replacement_Frequency')

        fig_bar.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        fig_bar.update_layout(xaxis_tickangle=-45)

        pie_df = df.groupby('Category')['Avg_Replacement_Frequency'].sum().reset_index()

        # Plotting
        fig_pie = px.pie(pie_df, values='Avg_Replacement_Frequency', names='Category',
                     title='Distribution of Replacement Requests by Product Category',
                     labels={'Category': 'Product Category',
                             'Avg_Replacement_Frequency': 'Total Replacement Frequency'})

        category_df = df.groupby('Category')['Avg_Replacement_Frequency'].mean().reset_index().sort_values(
            by='Avg_Replacement_Frequency', ascending=False)

        # Plotting
        fig_bar2 = px.bar(category_df, x='Avg_Replacement_Frequency', y='Category',
                     title='Top Categories by Average Replacement Frequency',
                     labels={'Category': 'Product Category',
                             'Avg_Replacement_Frequency': 'Avg Replacement Frequency'},
                     orientation='h',
                     text='Avg_Replacement_Frequency')

        fig_bar2.update_traces(texttemplate='%{text:.2f}', textposition='outside')

        figures = [fig_bar, fig_pie, fig_bar2]
        return figures

    if query == "How does the order fulfillment rate differ across various product categories?":
        df = pd.read_sql_query("""SELECT Product_Category,
            ROUND(AVG(p.Fulfillment_Rate_Category), 2) AS Avg_Fulfillment_Rate
            FROM retail_panopticon.productAndRegionPerformance p
            GROUP BY Product_Category
            ORDER BY Avg_Fulfillment_Rate DESC;""", con)

        fig_bar = px.bar(df,
                     x='Avg_Fulfillment_Rate',
                     y='Product_Category',
                     title="Average Fulfillment Rate by Product Category",
                     labels={'Product_Category': 'Product Category',
                             'Avg_Fulfillment_Rate': 'Average Fulfillment Rate'},
                     color='Avg_Fulfillment_Rate',
                     orientation='h',
                     height=600)

        fig = go.Figure(data=go.Heatmap(
            z=df['Avg_Fulfillment_Rate'],
            x=df['Product_Category'],
            y=['Fulfillment Rate'],
            colorscale='Viridis'))

        fig.update_layout(
            title="Heatmap of Fulfillment Rate by Product Category",
            xaxis_title="Product Category",
            yaxis_title="",
            height=400
        )
        figures = [fig_bar, fig]
        return figures

        # Warehouse Agentic App
    if query == "How efficient are our warehouse operations in terms of throughput and processing time for inbound and outbound shipments for products which have a low stock availability (<10)?":
        df = pd.read_sql_query("""SELECT
           p.Product_ID,
           p.Product_Description,
           w.Supplier_ID,
           w.Warehouse_Throughput,
           w.Inbound_Processing_Time,
           w.Outbound_Processing_Time,
           w.Warehouse_Operations_Efficiency_Metric
        FROM retail_panopticon.productInformation p
        JOIN retail_panopticon.warehouseThroughput w ON p.Supplier_ID = w.Supplier_ID
        WHERE p.Stock_Availability < 10
        GROUP BY p.Product_Description, w.Supplier_ID,w.Warehouse_Throughput,w.Inbound_Processing_Time,
         w.Outbound_Processing_Time,w.Warehouse_Operations_Efficiency_Metric
        ORDER BY w.Warehouse_Operations_Efficiency_Metric DESC;
        ;""", con)

        # Assuming 'df' is your dataframe with relevant columns
        fig = px.bar(df,
                     x='Product_ID',
                     y='Warehouse_Throughput',
                     title="Warehouse Throughput by Product",
                     labels={'Product_ID': 'Product', 'Warehouse_Throughput': 'Throughput'},
                     color='Warehouse_Throughput',
                     hover_data=['Product_Description'])

        fig.update_layout(xaxis_tickangle=-45, height=600)

        fig1 = go.Figure()

        fig1.add_trace(go.Scatter(x=df['Product_Description'],
                                  y=df['Warehouse_Throughput'],
                                  mode='lines+markers',
                                  name='Warehouse Throughput',
                                  line=dict(dash='solid', color='blue')))  # Blue color for Warehouse Throughput

        fig1.update_layout(
            title="Warehouse Throughput by Product",
            xaxis_title="Product",
            yaxis_title="Warehouse Throughput",
            height=600
        )

        fig1.update_xaxes(tickangle=-45)

        # Figure 2: Efficiency Metric with a specific color (e.g., green)
        fig2 = go.Figure()

        fig2.add_trace(go.Scatter(x=df['Product_Description'],
                                  y=df['Warehouse_Operations_Efficiency_Metric'],
                                  mode='lines+markers',
                                  name='Efficiency Metric',
                                  line=dict(dash='solid', color='green')))  # Green color for Efficiency Metric

        fig2.update_layout(
            title="Efficiency Metric by Product",
            xaxis_title="Product",
            yaxis_title="Efficiency Metric",
            height=600
        )

        fig2.update_xaxes(tickangle=-45)
        figures = [fig,fig1,fig2]

    if query == "How effectively are we managing our warehouse space to maximize storage capacity and minimize handling costs?":
        df = pd.read_sql_query("""SELECT 
            w.Supplier_ID,
            w.Warehouse_Space_Utilization,
            w.Storage_Capacity_Metric,
            w.Handling_Costs,
            w.Space_Optimization_Strategies,
            ROUND(
                CASE
                    WHEN w.Storage_Capacity_Metric > 0 THEN
                        (w.Warehouse_Space_Utilization / w.Storage_Capacity_Metric) * 100
                    ELSE
                        0
                END, 2) AS Utilization_Percentage,
            ROUND(
                CASE
                    WHEN w.Warehouse_Space_Utilization > 0 THEN
                        w.Handling_Costs / w.Warehouse_Space_Utilization
                    ELSE
                        0
                END, 2) AS Cost_Per_Unit_Space
        FROM retail_panopticon.warehouseUtilization w
        WHERE w.Supplier_ID IN ('SUPP078', 'SUPP083', 'SUPP066', 'SUPP073')
        ORDER BY Utilization_Percentage DESC, Cost_Per_Unit_Space ASC;""", con)

        fig_bar1 = px.bar(df,
                     x='Supplier_ID',
                     y='Utilization_Percentage',
                     title="Warehouse Space Utilization(%) by Supplier",
                     labels={'Supplier_ID': 'Supplier', 'Utilization_Percentage': 'Utilization Percentage (%)'},
                     color='Utilization_Percentage')

        fig_bar1.update_layout(xaxis_tickangle=-45, height=600)
        fig_bar1.show()

        fig_bar2 = px.bar(df,
                     x='Supplier_ID',
                     y='Storage_Capacity_Metric_Supplier',
                     title="Warehouse Space Utilization by Supplier",
                     labels={'Supplier_ID': 'Supplier', 'Utilization_Percentage': 'Utilization Percentage (%)'},
                     color='Utilization_Percentage')

        fig_bar2.update_layout(xaxis_tickangle=-45, height=600)
        fig_bar2.show()

        fig_pie = px.pie(df,
                     names='Supplier_ID',
                     values='Warehouse_Space_Utilization',
                     title="Warehouse Space Utilization by Supplier")

        fig_pie.update_layout(height=600)
        figures = [fig_bar1, fig_bar2, fig_pie]
        return figures

    if query == "Which product categories are the most likely to suffer from shipping delays and what are the primary causes of these delays?":
        df = pd.read_sql_query("""SELECT p.Category, s.Reason_Late_Shipment,
        COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments
        FROM retail_panopticon.transactions t
        JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID
        JOIN retail_panopticon.shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID
        GROUP BY p.Category, s.Reason_Late_Shipment
        HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0
        ORDER BY Total_Late_Shipments DESC;""", con)

        fig_bar = px.bar(df,
                     x='Category',
                     y='Total_Late_Shipments',
                     color='Category',
                     title='Total Late Shipments by Product Category',
                     labels={'Category': 'Product Category', 'Total_Late_Shipments': 'Total Late Shipments'},
                     color_continuous_scale='Blues')

        fig_bar.update_layout(xaxis_tickangle=-45, height=600)

        reason_totals = df.groupby('Reason_Late_Shipment').sum().reset_index()

        fig_pie = px.pie(reason_totals,
                     names='Reason_Late_Shipment',
                     values='Total_Late_Shipments',
                     title='Distribution of Late Shipments by Cause',
                     labels={'Reason_Late_Shipment': 'Reason for Late Shipment',
                             'Total_Late_Shipments': 'Total Late Shipments'})

        fig_pie.update_layout(height=600)

        figures = [fig_bar, fig_pie]
        return figures


def create_figures_marketing(data, query):
    if query == "How effective are different marketing strategies across product categories in terms of sales volume, inventory management, and the occurrence of stockouts during promotional campaigns?":
        bar_fig = px.bar(
            data,
            x='Total_Sales_During_Campaigns',
            y='Store_ID',
            color='Marketing_Strategy',
            orientation='h',
            title='Total Sales by Store ID with Marketing Strategy'
        )
        bar_fig.update_layout(yaxis={'categoryorder': 'total ascending'})

        sunburst_fig = px.sunburst(
            data,
            path=['Category', 'Marketing_Strategy'],
            values='Total_Sales_During_Campaigns',
            title='Sales Split by Category and Marketing Strategy'
        )

        box_fig = px.box(
            data,
            y='Total_Sales_During_Campaigns',
            x='Category',
            color='Category',
            title='Sales Variability by Product Category'
        )

        figures = [bar_fig, sunburst_fig, box_fig]
        return figures

    if query == "How effective are different types of promotional activities at various urban store locations in terms of sales uplift, customer engagement, and inventory turnover?":
        bar_fig = px.bar(
            data,
            x='Store_ID',
            y='Avg_Inventory_Turnover',
            color='Promotional_Activity_Type',
            title='Average Inventory Turnover by Store'
        )

        hist_fig = px.histogram(
            data,
            x='Total_Sales',
            color='Promotional_Activity_Type',
            barmode='group',
            title='Distribution of Total Sales by Promotional Activity Type'
        )

        area_fig = px.area(
            data,
            x='Promotional_Activity_Type',
            y='Total_Sales',
            color='Store_ID',
            line_group='Store_ID',
            title='Total Sales by Promotional Activity Type Across Stores'
        )

        pie_fig = px.pie(
            data,
            values='Total_Sales',
            names='Promotional_Activity_Type',
            title='Proportion of Total Sales by Promotional Activity Type'
        )

        figures = [bar_fig, hist_fig, area_fig, pie_fig]
        return figures

def create_figuresIM(data, query):
    if query == "How do we optimize inventory levels and replenishment for high-stockout products to match sales and reduce stockouts?":
        bar_fig_sales = px.bar(
            data,
            x='Total_Sales',
            y='Description',
            title='Sum of Total Sales by Description',
            orientation='h'
        )
        bar_fig_sales.update_layout(
            xaxis_title='Total_Sales',
            yaxis_title='Description',
            yaxis={'categoryorder': 'total ascending'}
        )

        fig_inventory_sales = px.bar(
            data,
            x='Description',
            y='Average_Monthly_Inventory_Level',
            title='Sum of Average Monthly Inventory Level by Description',
            barmode='stack',
            color_discrete_sequence=['#FFFF00']
        )
        fig_inventory_sales.update_layout(
            xaxis_title='Description',
            xaxis={'categoryorder': 'total ascending'},
            yaxis_title='Average Monthly Inventory Level'
        )

        figures = [bar_fig_sales, fig_inventory_sales]
        return figures

    if query == "Which high-sales products have low turnover rates, and what are the lead times and safety stock levels for these products?":
        bar_fig = px.bar(
            data,
            x='Total_Sales',
            y='Description',
            orientation='h',
            title='Sum of Total_Sales by Description'
        )
        bar_fig.update_layout(
            xaxis_title='Total Sales',
            yaxis_title='Product Description',
            yaxis={'categoryorder': 'total ascending'}
        )

        pie_fig = px.pie(
            data,
            values='Safety_Stock_Levels',
            names='Description',
            title='Sum of Safety_Stock_Levels by Description'
        )

        scatter_fig = px.scatter(
            data,
            x='Description',
            y='Replenishment_Lead_Time',
            title='Sum of Replenishment Lead Time by Description',
            color='Description',
            hover_name='Description',
            size='Replenishment_Lead_Time',
            labels={
                'Replenishment_Lead_Time': 'Replenishment Lead Time',
                'Description': 'Product Description'
            }
        )
        scatter_fig.update_layout(
            xaxis_title='Product Description',
            yaxis_title='Replenishment Lead Time',
            xaxis={'categoryorder': 'total ascending'},
            plot_bgcolor='black',
            xaxis_tickangle=-45
        )

        figures = [bar_fig, pie_fig, scatter_fig]
        return figures

    if query == "For products with frequent stockouts, what are their replenishment accuracy rates, and how do these relate to their sales volumes?":
        bar_fig2 = px.bar(
            data,
            x='Description',
            y='Replenishment_Accuracy',
            title='Sum of Replenishment Accuracy by Description',
            labels={'Replenishment_Accuracy': 'Sum of Replenishment Accuracy'}
        )

        treemap_fig = px.treemap(
            data,
            path=['Description'],
            values='StockOut_Incidents',
            title='Sum of StockOut Incidents by Description',
            color='StockOut_Incidents',
            color_continuous_scale='Viridis'
        )

        heatmap_fig = px.density_heatmap(
            data,
            x='Description',
            y='Fill_Rate',
            marginal_x='rug',
            marginal_y='histogram',
            title='Density of Fill Rate by Description'
        )

        figures = [bar_fig2, treemap_fig, heatmap_fig]
        return figures

def create_figures_loss_prevention(data, query):
    if query == "What are the detailed loss prevention measures for products in departments with a shrinkage rate higher than a specific threshold?":
        # df = pd.read_sql_query("""SELECT
        #     slp.Product_ID,
        #     p.Description,
        #     slp.Department,
        #     slp.Shrinkage_Rate,
        #     slp.Shrinkage_Value,
        #     slp.Loss_Prevention_Measures
        # FROM shrinkageAndLossPrevention AS slp
        # JOIN products AS p ON slp.Product_ID = p.Product_ID
        # WHERE slp.Shrinkage_Rate > 4
        # ORDER BY slp.Shrinkage_Rate DESC;""", conn)

        fig_tree = px.treemap(data,
                         path=['Department', 'Description'],
                         values='Shrinkage_Value',
                         color='Shrinkage_Rate',
                         hover_data=['Loss_Prevention_Measures'],
                         title='Shrinkage Rate by Department',
                         color_continuous_scale='Viridis')

        fig_tree.update_layout(height=600)

        fig_sun = px.sunburst(data,
                          path=['Department', 'Description'],
                          values='Shrinkage_Value',
                          color='Shrinkage_Rate',
                          hover_data=['Loss_Prevention_Measures'],
                          title='Shrinkage Rate by Department',
                          color_continuous_scale='Reds')

        fig_sun.update_layout(height=600)

        figures = [fig_tree, fig_sun]
        return figures

    if query == "How do high shrinkage rates and inventory management practices affect sales volumes for products in rural store locations?":
        fig_bar1 = px.bar(data,
                     x='Product_ID',
                     y='Total_Sales',
                     color='Shrinkage_Rate',
                     hover_data=['Description', 'Loss_Prevention_Measures'],
                     title="Total Sales by Product in Rural Stores")

        fig_bar1.update_layout(xaxis_tickangle=-45)

        fig_bar2 = px.bar(data,
                     x='Product_ID',  # Categories on x-axis
                     y='Replenishment_Lead_Time',  # Values on y-axis
                     title="Replenishment Lead Time by Product",
                     labels={'Product_ID': 'Product ID', 'Replenishment_Lead_Time': 'Replenishment Lead Time (days)'},
                     color='Replenishment_Lead_Time',  # Optional: color by lead time
                     text='Replenishment_Lead_Time')  # Display values on bars

        fig_bar2.update_layout(xaxis_tickangle=-45, height=600)

        figures = [fig_bar1,fig_bar2]
        return figures

def corporate_app(persona, questions_dict):
    st.markdown("""
    <style>
    div.stButton {
        display: flex;
        justify-content: flex-end; /* Align button to the right */
        margin-top: 10px;
    }
    """, unsafe_allow_html=True)
    save_button_pressed = st.button('SAVE', key='save_button')

    if save_button_pressed:
        if st.session_state.history:
            last_chat = st.session_state.history[-1]
            store_question_in_db(last_chat['question'], last_chat['sql'])
            st.success("Last conversation stored.")
            st.session_state['user_input'] = ""
            st.session_state['display_df_and_nlr'] = False
            st.session_state['last_result'] = None
            st.session_state['last_nlr'] = None
        else:
            st.warning("No conversation to store.")

    st.session_state['user_input'] = st.text_input("Business Question: ", st.session_state['user_input'])
    col = st.columns((1, 1), gap='medium')

    with col[0]:
        for chat in st.session_state.history:
            st.write(f"**User:** {chat['question']}")
            st.write(f"**Natural Language Response:** {chat['nlr']}")

        if st.session_state['user_input'] and not save_button_pressed:
            if st.session_state['user_input'] in questions_dict.keys() and st.session_state[
                'user_input'] != "Select a query":
                conn = connect_to_db(DB_NAME)
                result = execute_query(questions_dict[st.session_state['user_input']]['sql'], conn)
                st.session_state.history.append({
                    "question": st.session_state['user_input'],
                    "nlr": questions_dict[st.session_state['user_input']]['nlr'],
                    "sql": questions_dict[st.session_state['user_input']]['sql']
                })
                st.session_state['display_df_and_nlr'] = True
                st.session_state['last_result'] = result
                st.session_state['last_nlr'] = st.session_state.history[-1]["nlr"]

                if st.session_state['display_df_and_nlr']:
                    st.dataframe(st.session_state['last_result'], height=300)
                    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                    time.sleep(1)
                    st.write(st.session_state['last_nlr'])

    with col[1]:

        if st.session_state['display_df_and_nlr'] and not st.session_state['last_result'].empty:
            if st.session_state[
                'user_input'] == "Give a daily breakdown UPT for all product categories for each store during May":
                l_figures = create_figures(st.session_state['last_result'], st.session_state['user_input'])

                dynamic_figure_populate(l_figures)

            if st.session_state['user_input'] == "For this store, which products are running low on inventory and have a per unit value greater than 50?":
                l_figures = create_figures(st.session_state['last_result'], st.session_state['user_input'])

                dynamic_figure_populate(l_figures)
            if st.session_state['user_input'] == "What was the impact of the promotional discounts offered in May on the weekend vs. weekday sales for all product categories?":
                l_figures = create_figures(st.session_state['last_result'], st.session_state['user_input'])

                dynamic_figure_populate(l_figures)

            if st.session_state['user_input'] == "Give the total shipments delivered late and the reason for the delay for each product category":
                l_figures = create_figures(st.session_state['last_result'], st.session_state['user_input'])

                dynamic_figure_populate(l_figures)

def corporate_appIM(persona, questions_dict):
    st.markdown("""
    <style>
    div.stButton {
        display: flex;
        justify-content: flex-end; /* Align button to the right */
        margin-top: 10px;
    }
    """, unsafe_allow_html=True)
    save_button_pressed = st.button('SAVE', key='save_button')

    if save_button_pressed:
        if st.session_state.history:
            last_chat = st.session_state.history[-1]
            store_question_in_db(last_chat['question'], last_chat['sql'])
            st.success("Last conversation stored.")
            st.session_state['user_input'] = ""
            st.session_state['display_df_and_nlr'] = False
            st.session_state['last_result'] = None
            st.session_state['last_nlr'] = None
        else:
            st.warning("No conversation to store.")

    st.session_state['user_input'] = st.text_input("Business Question: ", st.session_state['user_input'])
    col = st.columns((1, 1), gap='medium')

    with col[0]:
        for chat in st.session_state.history:
            st.write(f"**User:** {chat['question']}")
            st.write(f"**Natural Language Response:** {chat['nlr']}")

        if st.session_state['user_input'] and not save_button_pressed:
            if st.session_state['user_input'] in questions_dict.keys() and st.session_state[
                'user_input'] != "Select a query":
                conn = connect_to_db(DB_NAME)
                result = execute_query(questions_dict[st.session_state['user_input']]['sql'], conn)
                st.session_state.history.append({
                    "question": st.session_state['user_input'],
                    "nlr": questions_dict[st.session_state['user_input']]['nlr'],
                    "sql": questions_dict[st.session_state['user_input']]['sql']
                })
                st.session_state['display_df_and_nlr'] = True
                st.session_state['last_result'] = result
                st.session_state['last_nlr'] = st.session_state.history[-1]["nlr"]

                if st.session_state['display_df_and_nlr']:
                    st.dataframe(st.session_state['last_result'], height=300)
                    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                    time.sleep(1)
                    st.write(st.session_state['last_nlr'])

    with col[1]:

        if st.session_state['display_df_and_nlr'] and not st.session_state['last_result'].empty:
            if st.session_state['user_input'] == "How do we optimize inventory levels and replenishment for high-stockout products to match sales and reduce stockouts?":
                l_figures = create_figuresIM(st.session_state['last_result'], st.session_state['user_input'])

                dynamic_figure_populate(l_figures)

            if st.session_state['user_input'] == "Which high-sales products have low turnover rates, and what are the lead times and safety stock levels for these products?":
                l_figures = create_figuresIM(st.session_state['last_result'], st.session_state['user_input'])

                dynamic_figure_populate(l_figures)

            if st.session_state['user_input'] == "For products with frequent stockouts, what are their replenishment accuracy rates, and how do these relate to their sales volumes?":
                l_figures = create_figuresIM(st.session_state['last_result'], st.session_state['user_input'])

                dynamic_figure_populate(l_figures)
def merchandising_app(persona, questions_dict):
    print(f"Entered Merchandising App: {time.time()}")
    st.markdown("""
    <style>
    div.stButton {
        display: flex;
        justify-content: flex-end; /* Align button to the right */
        margin-top: 10px;
    }
    """, unsafe_allow_html=True)
    save_button_pressed = st.button('SAVE', key='save_button')

    if save_button_pressed:
        if st.session_state.history:
            last_chat = st.session_state.history[-1]
            store_question_in_db(last_chat['question'], last_chat['sql'])
            st.success("Last conversation stored.")
            st.session_state['user_input'] = ""
            st.session_state['display_df_and_nlr'] = False
            st.session_state['last_result'] = None
            st.session_state['last_nlr'] = None
        else:
            st.warning("No conversation to store.")

    st.session_state['user_input'] = st.text_input("Business Question: ", st.session_state['user_input'])
    col = st.columns((1, 1), gap='medium')
    print(f"Layout set: {time.time()}")
    with col[0]:
        for chat in st.session_state.history:
            st.write(f"**User:** {chat['question']}")
            st.write(f"**Natural Language Response:** {chat['nlr']}")

        if st.session_state['user_input'] and not save_button_pressed:
            if st.session_state['user_input'] in questions_dict.keys() and st.session_state[
                'user_input'] != "Select a query":
                conn = connect_to_db(DB_NAME)
                result = execute_query(questions_dict[st.session_state['user_input']]['sql'], conn)
                st.session_state.history.append({
                    "question": st.session_state['user_input'],
                    "nlr": questions_dict[st.session_state['user_input']]['nlr'],
                    "sql": questions_dict[st.session_state['user_input']]['sql']
                })
                st.session_state['display_df_and_nlr'] = True
                st.session_state['last_result'] = result
                st.session_state['last_nlr'] = st.session_state.history[-1]["nlr"]

                if st.session_state['display_df_and_nlr']:
                    st.dataframe(st.session_state['last_result'], height=300)
                    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                    time.sleep(1)
                    st.write(st.session_state['last_nlr'])
                    print(f"Left column populated: {time.time()}")

    with col[1]:

        if st.session_state['display_df_and_nlr'] and not st.session_state['last_result'].empty:
            if st.session_state['user_input'] == "What are the top 3 most common reasons for delays in order fulfillment and which product categories are most severely affected by delays?":
                l_figures = create_figures(st.session_state['last_result'], st.session_state['user_input'])
                print(f"List of figures populated: {time.time()}")

                dynamic_figure_populate(l_figures)
                print(f"figures rendered: {time.time()}")
            if st.session_state['user_input'] == "Which products in this category have the highest rates of replacement requests?":
                l_figures = create_figures(st.session_state['last_result'], st.session_state['user_input'])

                dynamic_figure_populate(l_figures)

            if st.session_state['user_input'] == "How does the order fulfillment rate differ across various product categories?":
                l_figures = create_figures(st.session_state['last_result'], st.session_state['user_input'])

                dynamic_figure_populate(l_figures)

def warehouse_app(persona, questions_dict):
    print(f"Entered Warehouse App: {time.time()}")
    st.markdown("""
    <style>
    div.stButton {
        display: flex;
        justify-content: flex-end; /* Align button to the right */
        margin-top: 10px;
    }
    """, unsafe_allow_html=True)
    save_button_pressed = st.button('SAVE', key='save_button')

    if save_button_pressed:
        if st.session_state.history:
            last_chat = st.session_state.history[-1]
            store_question_in_db(last_chat['question'], last_chat['sql'])
            st.success("Last conversation stored.")
            st.session_state['user_input'] = ""
            st.session_state['display_df_and_nlr'] = False
            st.session_state['last_result'] = None
            st.session_state['last_nlr'] = None
        else:
            st.warning("No conversation to store.")

    st.session_state['user_input'] = st.text_input("Business Question: ", st.session_state['user_input'])
    col = st.columns((1, 1), gap='medium')
    print(f"Layout set: {time.time()}")
    with col[0]:
        for chat in st.session_state.history:
            st.write(f"**User:** {chat['question']}")
            st.write(f"**Natural Language Response:** {chat['nlr']}")

        if st.session_state['user_input'] and not save_button_pressed:
            if st.session_state['user_input'] in questions_dict.keys() and st.session_state[
                'user_input'] != "Select a query":
                conn = connect_to_db(DB_NAME)
                result = execute_query(questions_dict[st.session_state['user_input']]['sql'], conn)
                st.session_state.history.append({
                    "question": st.session_state['user_input'],
                    "nlr": questions_dict[st.session_state['user_input']]['nlr'],
                    "sql": questions_dict[st.session_state['user_input']]['sql']
                })
                st.session_state['display_df_and_nlr'] = True
                st.session_state['last_result'] = result
                st.session_state['last_nlr'] = st.session_state.history[-1]["nlr"]

                if st.session_state['display_df_and_nlr']:
                    st.dataframe(st.session_state['last_result'], height=300)
                    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                    time.sleep(1)
                    st.write(st.session_state['last_nlr'])
                    print(f"Left column populated: {time.time()}")

    with col[1]:

        if st.session_state['display_df_and_nlr'] and not st.session_state['last_result'].empty:
            if st.session_state['user_input'] == "How efficient are our warehouse operations in terms of throughput and processing time for inbound and outbound shipments for products in this category which have a low stock availability (<10)?":
                l_figures = create_figures(st.session_state['last_result'], st.session_state['user_input'])
                print(f"List of figures populated: {time.time()}")

                dynamic_figure_populate(l_figures)
                print(f"figures rendered: {time.time()}")
            if st.session_state['user_input'] == "How effectively are we managing our warehouse space to maximize storage capacity and minimize handling costs?":
                l_figures = create_figures(st.session_state['last_result'], st.session_state['user_input'])

                dynamic_figure_populate(l_figures)

            if st.session_state['user_input'] == "Which product categories are the most likely to suffer from shipping delays and what are the primary causes of these delays?":
                l_figures = create_figures(st.session_state['last_result'], st.session_state['user_input'])

                dynamic_figure_populate(l_figures)

def marketing_app(persona, questions_dict):
    reset()
    st.markdown("""
    <style>
    div.stButton {
        display: flex;
        justify-content: flex-end; /* Align button to the right */
        margin-top: 10px;
    }
    """, unsafe_allow_html=True)
    save_button_pressed = st.button('SAVE', key='save_button')

    if save_button_pressed:
        if st.session_state.history:
            last_chat = st.session_state.history[-1]
            store_question_in_db(last_chat['question'], last_chat['sql'])
            st.success("Last conversation stored.")
            st.session_state['user_input'] = ""
            st.session_state['display_df_and_nlr'] = False
            st.session_state['last_result'] = None
            st.session_state['last_nlr'] = None
        else:
            st.warning("No conversation to store.")

    st.session_state['user_input'] = st.text_input("Business Question: ", st.session_state['user_input'])
    col = st.columns((1, 1), gap='medium')

    with col[0]:
        for chat in st.session_state.history:
            st.write(f"*User:* {chat['question']}")
            st.write(f"*Natural Language Response:* {chat['nlr']}")

        if st.session_state['user_input'] and not save_button_pressed:
            if st.session_state['user_input'] in questions_dict.keys() and st.session_state[
                'user_input'] != "Select a query":
                conn = connect_to_db(DB_NAME)
                result = execute_query(questions_dict[st.session_state['user_input']]['sql'], conn)
                st.session_state.history.append({
                    "question": st.session_state['user_input'],
                    "nlr": questions_dict[st.session_state['user_input']]['nlr'],
                    "sql": questions_dict[st.session_state['user_input']]['sql']
                })
                st.session_state['display_df_and_nlr'] = True
                st.session_state['last_result'] = result
                st.session_state['last_nlr'] = st.session_state.history[-1]["nlr"]

                if st.session_state['display_df_and_nlr']:
                    st.dataframe(st.session_state['last_result'], height=300)
                    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                    time.sleep(1)
                    st.write(st.session_state['last_nlr'])

    with col[1]:

        if st.session_state['display_df_and_nlr'] and not st.session_state['last_result'].empty:
            if st.session_state['user_input'] == "How effective are different marketing strategies across product categories in terms of sales volume, inventory management, and the occurrence of stockouts during promotional campaigns?":
                l_figures = create_figures_marketing(st.session_state['last_result'], st.session_state['user_input'])

                dynamic_figure_populate(l_figures)

            if st.session_state['user_input'] == "How effective are different types of promotional activities at various urban store locations in terms of sales uplift, customer engagement, and inventory turnover?":
                l_figures = create_figures_marketing(st.session_state['last_result'], st.session_state['user_input'])

                dynamic_figure_populate(l_figures)

def loss_prevention_app(persona, questions_dict):
    st.markdown("""
    <style>
    div.stButton {
        display: flex;
        justify-content: flex-end; /* Align button to the right */
        margin-top: 10px;
    }
    """, unsafe_allow_html=True)
    save_button_pressed = st.button('SAVE', key='save_button')

    if save_button_pressed:
        if st.session_state.history:
            last_chat = st.session_state.history[-1]
            store_question_in_db(last_chat['question'], last_chat['sql'])
            st.success("Last conversation stored.")
            st.session_state['user_input'] = ""
            st.session_state['display_df_and_nlr'] = False
            st.session_state['last_result'] = None
            st.session_state['last_nlr'] = None
        else:
            st.warning("No conversation to store.")

    st.session_state['user_input'] = st.text_input("Business Question: ", st.session_state['user_input'])
    col = st.columns((1, 1), gap='medium')

    with col[0]:
        for chat in st.session_state.history:
            st.write(f"*User:* {chat['question']}")
            st.write(f"*Natural Language Response:* {chat['nlr']}")

        if st.session_state['user_input'] and not save_button_pressed:
            if st.session_state['user_input'] in questions_dict.keys() and st.session_state[
                'user_input'] != "Select a query":
                conn = connect_to_db(DB_NAME)
                result = execute_query(questions_dict[st.session_state['user_input']]['sql'], conn)
                st.session_state.history.append({
                    "question": st.session_state['user_input'],
                    "nlr": questions_dict[st.session_state['user_input']]['nlr'],
                    "sql": questions_dict[st.session_state['user_input']]['sql']
                })
                st.session_state['display_df_and_nlr'] = True
                st.session_state['last_result'] = result
                st.session_state['last_nlr'] = st.session_state.history[-1]["nlr"]

                if st.session_state['display_df_and_nlr']:
                    st.dataframe(st.session_state['last_result'], height=300)
                    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                    time.sleep(1)
                    st.write(st.session_state['last_nlr'])

    with col[1]:

        if st.session_state['display_df_and_nlr'] and not st.session_state['last_result'].empty:
            if st.session_state['user_input'] == "What are the detailed loss prevention measures for products in departments with a shrinkage rate higher than a specific threshold?":
                l_figures = create_figures_loss_prevention(st.session_state['last_result'], st.session_state['user_input'])

                dynamic_figure_populate(l_figures)

            if st.session_state['user_input'] == "How do high shrinkage rates and inventory management practices affect sales volumes for products in rural store locations?":
                l_figures = create_figures_loss_prevention(st.session_state['last_result'], st.session_state['user_input'])

                dynamic_figure_populate(l_figures)

def dynamic_figure_populate(list_of_figs):
    # Num plots:5
    # remaining_cols = [2,2,1]

    num_plots = len(list_of_figs)
    num_containers = num_plots // 2 + num_plots % 2
    print(f"Number of plots:{num_containers}")
    print(f"Number of containers:{num_containers}")
    remaining_cols = [2] * (num_plots // 2)
    if num_plots % 2 == 1:
        remaining_cols.append(num_plots % 2)
    print(f"column split:{remaining_cols}")
    # with streamlit_column:
    current_idx = 0
    for i in range(1, num_containers + 1):
        print(f"i: {i}")

        globals()[f'container_{i}'] = st.container()
        container = globals()[f'container_{i}']
        with container:
            cols = st.columns(remaining_cols[i - 1])
            for col_idx in range(len(cols)):
                print(f"current container column index: {col_idx}")
                with cols[col_idx]:
                    print(f"current_idx: {current_idx}")
                    if current_idx == num_plots:
                        break
                    st.plotly_chart(list_of_figs[current_idx])
                    current_idx += 1
    return


def management_app(persona, options):
    queries = get_queries_from_db(persona)

    st.markdown("""
            <style>
            div.stButton {
                display: flex;
                justify-content: flex-end; /* Align button to the right */
                margin-top: 10px;
            }

            /* Custom CSS for the dropdowns to align right and be smaller */
            div.streamlit-expander {
                width: 100%; /* Make sure it fills the container */
            }

            div.streamlit-expander > div {
                width: 30%; /* Set the width of the selectbox */
                margin-left: auto; /* Push it to the right */
            }

            /* Smaller font size for selectbox options */
            .stSelectbox div {
                font-size: 12px; /* Smaller font size */
            }

            </style>
            """, unsafe_allow_html=True)
    col1, col2 = st.columns([4, 1])
    unpin_button_pressed = st.button("DELETE", key='unpin_button')
    selected_query = st.selectbox("Select a query", queries if queries else ["Select a query"])

    with (col2):
        drop_down = st.selectbox("", options)
        if selected_query == "For this store, which products are running low on inventory and have a per unit value greater than 50?" and drop_down != "SELECT STORE":
            replenish_inventory_button = st.button("REPLENISH INVENTORY", key="replenish_button")
            if replenish_inventory_button:
                # store_names = ["SELECT STORE", "WATER TOWER PLACE", "RIVERFRONT PLAZA", "WESTFIELD WHEATON"]
                with st.form("replenish_form"):
                    # store_name = st.selectbox("Store Name", store_names, key="store_name")
                    product_id = st.text_input("Product ID", key="product_id")
                    units = st.number_input("Number of Units to Replenish", min_value=1, step=1, key="units")
                    st.form_submit_button(label="Submit", on_click=submitted)
            if 'submitted' in st.session_state:
                if st.session_state.submitted == True:
                    st.success(
                        f"{st.session_state.units} units added to inventory for Product {st.session_state.product_id} at {drop_down}")
                    reset()  # Prevents rerunning form on next page load

    # unpin_button_pressed = st.button("DELETE", key='unpin_button')
    # selected_query = st.selectbox("Select a query", queries if queries else ["Select a query"])

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    col = st.columns((1, 1), gap='medium')
    conn = connect_to_db(DB_NAME)

    with col[0]:
        if unpin_button_pressed:
            if selected_query != "Select a query":
                queries.pop(selected_query, None)
                st.success(f"Query '{selected_query}' has been removed.")
            else:
                st.warning("Select a query to unpin.")

        if drop_down and selected_query and selected_query != "Select a query" and not unpin_button_pressed and drop_down != "SELECT STORE":
            # result = execute_query(queries[selected_query], conn)

            if selected_query == "For this store, which products are running low on inventory and have a per unit value greater than 50?":
                if drop_down == "WATER TOWER PLACE":
                    time.sleep(1)
                    st.markdown("""
                    The SQL query returned a data table that includes the Product ID, Description, Unit Price, and Stock Availability of certain products. The products listed in the table have a Stock Availability of less than 10, a Unit Price greater than 50, and are associated with the Store ID 'WATER TOWER PLACE'. The table is sorted in ascending order based on the Stock Availability. \n\nIn the table, the following products are listed:\n1. Product ID: PROD0725, Description: Shirt (Clothing), Unit Price: 68.36, Stock Availability: 3\n2. Product ID: PROD0215, Description: Headphones (Electronics), Unit Price: 649.96, Stock Availability: 3\n3. Product ID: PROD0403, Description: Dress (Clothing), Unit Price: 77.27, Stock Availability: 4\n4. Product ID: PROD0753, Description: Action Figure (Toys), Unit Price: 83.93, Stock Availability: 7\n5. Product ID: PROD0157, Description: Jacket (Clothing), Unit Price: 76.89, Stock Availability: 8\n\nThese products meet the criteria specified in the business question and can be considered as low inventory items with a higher unit price.
                    """)

                elif drop_down == "RIVERFRONT PLAZA":
                    time.sleep(1)
                    st.markdown("""
                    The data table returned shows the products that meet the criteria specified in the business question. These products have a low stock availability (less than 10), a unit price higher than $50, and are associated with transactions from the store with the ID \'RIVERFRONT PLAZA\'. \n\nThe table includes the following columns: \n- Product_ID: The unique identifier for each product. The product IDs for the returned products are PROD0725, PROD0215, PROD0490, PROD0403, PROD0753, and PROD0157.\n- Description: The description or name of each product. The descriptions for the returned products are "Shirt (Clothing)", "Headphones (Electronics)", "Board Game (Toys)", "Dress (Clothing)", "Action Figure (Toys)", and "Jacket (Clothing)".\n- Unit_Price: The price of each product per unit. The unit prices for the returned products range from $67.15 to $649.96.\n- Stock_Availability: The current availability of each product in terms of stock quantity. The stock availability for the returned products ranges from 3 to 8 units.\n\nOverall, the table provides a list of products that are low in stock, have a higher price, and have been associated with transactions from the store \'RIVERFRONT PLAZA\'.
                    """)

                elif drop_down == "WESTFIELD WHEATON":
                    time.sleep(1)
                    st.markdown("""The data table returned includes information about products that meet the criteria specified in the business question. The table includes the following columns: Product_ID, Description, Unit_Price, and Stock_Availability. \n\nThe Product_IDs of the products in the table are PROD0215, PROD0490, PROD0403, PROD0753, and PROD0157. \n\nFor each product, the table provides the Description, which describes the type of product. The Unit_Price column displays the price of each product. The Stock_Availability column indicates the current availability of each product in terms of the quantity in stock.\n\nBased on the query, the table only includes products that have a Stock_Availability of less than 10, a Unit_Price greater than 50, and are associated with the Store_ID 'WESTFIELD WHEATON'. The products are sorted in ascending order based on their Stock_Availability. \n\nIn summary, the table shows the specific products that meet the criteria of low stock availability, a unit price higher than 50, and are associated with the specified store.""")

            if selected_query == "Give a daily breakdown UPT for all product categories for each store during May":
                if drop_down == "WATER TOWER PLACE":
                    time.sleep(1)
                    st.markdown("""
                    Clothing:\tWATER TOWER PLACE has a UPT of 5.38 as compared to the average of 5.48\n
                    Electronics:\tWATER TOWER PLACE does not sell Electronics items\n
                    Food:\t\tWATER TOWER PLACE has a UPT of 5.64 as compared to the average of 5.51\n
                    Furniture:\tWATER TOWER PLACE has a UPT of 5.55 as compared to the average of 5.5\n
                    Toys:\t\tWATER TOWER PLACE does not sell Toys items\n
                    """)

                elif drop_down == "RIVERFRONT PLAZA":
                    time.sleep(1)
                    st.markdown("""
                    Clothing:\tRIVERFRONT PLAZA does not sell Clothing items\n
                    Electronics:\tRIVERFRONT PLAZA does not sell Electronics items\n
                    Food:\t\tRIVERFRONT PLAZA does not sell Food items\n
                    Furniture:\tRIVERFRONT PLAZA has a UPT of 5.46 as compared to the average of 5.5\n
                    Toys:\t\tRIVERFRONT PLAZA has a UPT of 5.58 as compared to the average of 5.48\n
                    """)

                elif drop_down == "WESTFIELD WHEATON":
                    time.sleep(1)
                    st.markdown("""
                    Clothing:\tWESTFIELD WHEATON has a UPT of 5.5 as compared to the average of 5.49\n
                    Electronics:\tWESTFIELD WHEATON does not sell Electronics items\n
                    Food:\t\tWESTFIELD WHEATON has a UPT of 5.55 as compared to the average of 5.51\n
                    Furniture:\tWESTFIELD WHEATON has a UPT of 5.47 as compared to the average of 5.5\n
                    Toys:\t\tWESTFIELD WHEATON has a UPT of 5.45 as compared to the average of 5.48\n
                    """)

            elif selected_query == "What was the impact of the promotional discounts offered in May on the weekend vs. weekday sales for all product categories?":
                if drop_down == "WATER TOWER PLACE":
                    time.sleep(1)
                    st.markdown("""
                    Clothing:\tWATER TOWER PLACE saw a 288% increase in sales during the weekdays following the weekends the promotions were launched\n
                    Electronics:\tWATER TOWER PLACE saw a 235% increase in sales during the weekdays following the weekends the promotions were launched\n
                    Food:\t\tWATER TOWER PLACE saw a 236% increase in sales during the weekdays following the weekends the promotions were launched\n
                    Furniture:\tWATER TOWER PLACE saw a 287% increase in sales during the weekdays following the weekends the promotions were launched\n
                    Toys:\t\tWATER TOWER PLACE saw a 272% increase in sales during the weekdays following the weekends the promotions were launched\n
                    """)

                elif drop_down == "RIVERFRONT PLAZA":
                    time.sleep(1)
                    st.markdown("""
                    Clothing:\tRIVERFRONT PLAZA saw a 230% increase in sales during the weekdays following the weekends the promotions were launched\n
                    Electronics:\tRIVERFRONT PLAZA saw a 300% increase in sales during the weekdays following the weekends the promotions were launched\n
                    Food:\t\tRIVERFRONT PLAZA saw a 256% increase in sales during the weekdays following the weekends the promotions were launched\n
                    Furniture:\tRIVERFRONT PLAZA saw a 255% increase in sales during the weekdays following the weekends the promotions were launched\n
                    Toys:\t\tRIVERFRONT PLAZA saw a 255% increase in sales during the weekdays following the weekends the promotions were launched\n
                    """)

                elif drop_down == "WESTFIELD WHEATON":
                    time.sleep(1)
                    st.markdown("""
                    Clothing:\tWESTFIELD WHEATON saw a 242% increase in sales during the weekdays following the weekends the promotions were launched\n
                    Electronics:\tWESTFIELD WHEATON saw a 332% increase in sales during the weekdays following the weekends the promotions were launched\n
                    Food:\t\tWESTFIELD WHEATON saw a 275% increase in sales during the weekdays following the weekends the promotions were launched\n
                    Furniture:\tWESTFIELD WHEATON saw a 231% increase in sales during the weekdays following the weekends the promotions were launched\n
                    Toys:\t\tWESTFIELD WHEATON saw a 298% increase in sales during the weekdays following the weekends the promotions were launched\n
                    """)

            elif selected_query == "Give the total shipments delivered late and the reason for the delay for each product category":
                if drop_down == "WATER TOWER PLACE":
                    time.sleep(1)
                    st.markdown("""
                    Clothing:\tWATER TOWER PLACE has no Delayed Shipments\n
                    Electronics:\tWATER TOWER PLACE has no Delayed Shipments\n
                    Food:\t\tWATER TOWER PLACE has no Delayed Shipments\n
                    Furniture:\tWATER TOWER PLACE has no Delayed Shipments\n
                    Toys:\t\tWATER TOWER PLACE has no Delayed Shipments\n
                    """)

                elif drop_down == "RIVERFRONT PLAZA":
                    time.sleep(1)
                    st.markdown("""
                    Clothing:\tRIVERFRONT PLAZA has no Delayed Shipments\n
                    Electronics:\tRIVERFRONT PLAZA has no Delayed Shipments\n
                    Food:\t\tRIVERFRONT PLAZA has no Delayed Shipments\n
                    Furniture:\tRIVERFRONT PLAZA has no Delayed Shipments\n
                    Toys:\t\tRIVERFRONT PLAZA has no Delayed Shipments\n
                    """)

                elif drop_down == "WESTFIELD WHEATON":
                    time.sleep(1)
                    st.markdown("""
                    Clothing:\tWESTFIELD WHEATON has no Delayed Shipments\n
                    Electronics:\tWESTFIELD WHEATON has no Delayed Shipments\n
                    Food:\t\tWESTFIELD WHEATON has no Delayed Shipments\n
                    Furniture:\tWESTFIELD WHEATON had 7055 delayed shipments, mostly due to Weather Conditions. On average, there were 7472 shipments delayed due to Weather Conditions in the same time frame.\n
                    Toys:\t\tWESTFIELD WHEATON has no Delayed Shipments\n
                    """)

    with col[1]:
        if selected_query and drop_down:
            if selected_query == "Give a daily breakdown UPT for all product categories for each store during May":
                if drop_down == "WATER TOWER PLACE":
                    result = execute_query(
                        "SELECT DATE(t.Date) AS Sale_Date, p.Category AS Product_Category, t.Store_ID, ROUND(SUM(t.Quantity) / COUNT(t.Transaction_ID), 2) AS UPT\nFROM retail_panopticon.transactions t\nJOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID\nWHERE t.Store_ID = 'STORE01' AND  t.Date BETWEEN '2024-05-01' AND '2024-05-31'\nGROUP BY DATE(t.Date), p.Category\nORDER BY DATE(t.Date), p.Category;",
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "RIVERFRONT PLAZA":
                    result = execute_query(
                        "SELECT DATE(t.Date) AS Sale_Date, p.Category AS Product_Category, t.Store_ID, ROUND(SUM(t.Quantity) / COUNT(t.Transaction_ID), 2) AS UPT\nFROM retail_panopticon.transactions t\nJOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID\nWHERE t.Store_ID = 'STORE28' AND  t.Date BETWEEN '2024-05-01' AND '2024-05-31'\nGROUP BY DATE(t.Date), p.Category\nORDER BY DATE(t.Date), p.Category;",
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "WESTFIELD WHEATON":
                    result = execute_query(
                        "SELECT DATE(t.Date) AS Sale_Date, p.Category AS Product_Category, t.Store_ID, ROUND(SUM(t.Quantity) / COUNT(t.Transaction_ID), 2) AS UPT\nFROM retail_panopticon.transactions t\nJOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID\nWHERE t.Store_ID = 'STORE49' AND  t.Date BETWEEN '2024-05-01' AND '2024-05-31'\nGROUP BY DATE(t.Date), p.Category\nORDER BY DATE(t.Date), p.Category;",
                        conn)

                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

            elif selected_query == "What was the impact of the promotional discounts offered in May on the weekend vs. weekday sales for all product categories?":
                if drop_down == "WATER TOWER PLACE":
                    result = execute_query(
                        "SELECT CASE WHEN DAYOFWEEK(S.date) IN (1, 7) THEN 'Weekend' ELSE 'Weekday' END AS day_type, P.Category,SUM(S.Total_Amount) AS total_sales, COUNT(DISTINCT S.Transaction_ID) AS total_transactions, AVG(S.Total_Amount) AS avg_transaction_value FROM transactions S JOIN productInformation P ON S.Product_ID = P.Product_ID WHERE S.Store_ID = 'STORE01' AND DATE_FORMAT(S.date, '%Y-%m') = '2024-05' GROUP BY day_type, P.Category ORDER BY day_type DESC, total_sales DESC;",
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "RIVERFRONT PLAZA":
                    result = execute_query(
                        "SELECT CASE WHEN DAYOFWEEK(S.date) IN (1, 7) THEN 'Weekend' ELSE 'Weekday' END AS day_type, P.Category,SUM(S.Total_Amount) AS total_sales, COUNT(DISTINCT S.Transaction_ID) AS total_transactions, AVG(S.Total_Amount) AS avg_transaction_value FROM transactions S JOIN productInformation P ON S.Product_ID = P.Product_ID WHERE S.Store_ID = 'STORE28' AND DATE_FORMAT(S.date, '%Y-%m') = '2024-05' GROUP BY day_type, P.Category ORDER BY day_type DESC, total_sales DESC;",
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "WESTFIELD WHEATON":
                    result = execute_query(
                        "SELECT CASE WHEN DAYOFWEEK(S.date) IN (1, 7) THEN 'Weekend' ELSE 'Weekday' END AS day_type, P.Category,SUM(S.Total_Amount) AS total_sales, COUNT(DISTINCT S.Transaction_ID) AS total_transactions, AVG(S.Total_Amount) AS avg_transaction_value FROM transactions S JOIN productInformation P ON S.Product_ID = P.Product_ID WHERE S.Store_ID = 'STORE49' AND DATE_FORMAT(S.date, '%Y-%m') = '2024-05' GROUP BY day_type, P.Category ORDER BY day_type DESC, total_sales DESC;",
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

            elif selected_query == "Give the total shipments delivered late and the reason for the delay for each product category":
                if drop_down == "WATER TOWER PLACE":
                    result = execute_query(
                        "SELECT t.Store_ID, p.Category,s.Reason_Late_Shipment, COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments FROM transactions t JOIN productInformation p ON t.Product_ID = p.Product_ID JOIN shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID WHERE t.Store_ID = 'STORE01' GROUP BY p.Category, s.Reason_Late_Shipment HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0 ORDER BY Total_Late_Shipments DESC;",
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "RIVERFRONT PLAZA":
                    result = execute_query(
                        "SELECT t.Store_ID, p.Category,s.Reason_Late_Shipment, COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments FROM transactions t JOIN productInformation p ON t.Product_ID = p.Product_ID JOIN shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID WHERE t.Store_ID = 'STORE28' GROUP BY p.Category, s.Reason_Late_Shipment HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0 ORDER BY Total_Late_Shipments DESC;",
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "WESTFIELD WHEATON":
                    result = execute_query(
                        "SELECT t.Store_ID, p.Category,s.Reason_Late_Shipment, COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments FROM transactions t JOIN productInformation p ON t.Product_ID = p.Product_ID JOIN shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID WHERE t.Store_ID = 'STORE49' GROUP BY p.Category, s.Reason_Late_Shipment HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0 ORDER BY Total_Late_Shipments DESC;",
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

            elif selected_query == "For this store, which products are running low on inventory and have a per unit value greater than 50?":
                if drop_down == "WATER TOWER PLACE":
                    result = execute_query(
                        """
                        SELECT p.Product_ID, p.Description,p.Unit_Price, p.Stock_Availability
                        FROM products p
                        JOIN transactions t ON p.Product_ID = t.Product_ID
                        WHERE t.Store_ID = 'STORE01'
                        AND p.Stock_Availability < 10  -- Adjust the threshold for low inventory as needed
                        AND p.Unit_Price > 50
                        GROUP BY p.Product_ID, p.Description, p.Unit_Price, p.Stock_Availability
                        ORDER BY p.Stock_Availability ASC;
                        """, conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "RIVERFRONT PLAZA":
                    result = execute_query(
                        """
                        SELECT p.Product_ID, p.Description,p.Unit_Price, p.Stock_Availability
                        FROM products p
                        JOIN transactions t ON p.Product_ID = t.Product_ID
                        WHERE t.Store_ID = 'STORE28'
                        AND p.Stock_Availability < 10  -- Adjust the threshold for low inventory as needed
                        AND p.Unit_Price > 50
                        GROUP BY p.Product_ID, p.Description, p.Unit_Price, p.Stock_Availability
                        ORDER BY p.Stock_Availability ASC;
                        """, conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "WESTFIELD WHEATON":
                    result = execute_query(
                        """
                        SELECT p.Product_ID, p.Description,p.Unit_Price, p.Stock_Availability
                        FROM products p
                        JOIN transactions t ON p.Product_ID = t.Product_ID
                        WHERE t.Store_ID = 'STORE49'
                        AND p.Stock_Availability < 10  -- Adjust the threshold for low inventory as needed
                        AND p.Unit_Price > 50
                        GROUP BY p.Product_ID, p.Description, p.Unit_Price, p.Stock_Availability
                        ORDER BY p.Stock_Availability ASC;
                        """, conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)



def merchandising_management_app(persona, options):
    queries = get_queries_from_db(persona)

    st.markdown("""
            <style>
            div.stButton {
                display: flex;
                justify-content: flex-end; /* Align button to the right */
                margin-top: 10px;
            }

            /* Custom CSS for the dropdowns to align right and be smaller */
            div.streamlit-expander {
                width: 100%; /* Make sure it fills the container */
            }

            div.streamlit-expander > div {
                width: 30%; /* Set the width of the selectbox */
                margin-left: auto; /* Push it to the right */
            }

            /* Smaller font size for selectbox options */
            .stSelectbox div {
                font-size: 12px; /* Smaller font size */
            }

            </style>
            """, unsafe_allow_html=True)
    col1, col2 = st.columns([4, 1])
    with col2:
        drop_down = st.selectbox("", options)
    unpin_button_pressed = st.button("DELETE", key='unpin_button')
    selected_query = st.selectbox("Select a query", queries if queries else ["Select a query"])

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    col = st.columns((1, 1), gap='medium')
    conn = connect_to_db(DB_NAME)

    with col[0]:
        if unpin_button_pressed:
            if selected_query != "Select a query":
                queries.pop(selected_query, None)
                st.success(f"Query '{selected_query}' has been removed.")
            else:
                st.warning("Select a query to unpin.")

        if drop_down and selected_query and selected_query != "Select a query" and not unpin_button_pressed and drop_down != "SELECT STORE":
            # result = execute_query(queries[selected_query], conn)
            if selected_query == "What are the top 3 most common reasons for delays in order fulfillment and which product categories are most severely affected by delays?":
                if drop_down == "FOOD":
                    time.sleep(1)
                    st.markdown("""
                    \tFor products belonging to the "FOOD" category, the top 3 reasons for delays are: Shipping Delays, Supplier Delays, and operational delays with 1944, 1911, and 1882 delays respectively.\n
                    """)

                elif drop_down == "CLOTHING":
                    time.sleep(1)
                    st.markdown("""
                    \tFor products belonging to the "CLOTHING" category, the top 3 reasons for delays are: Supplier Delays, Shipping Problems and Inventory Issues with 2076, 2035, and 2002 delays respectively.\n
                    """)

                elif drop_down == "TOYS":
                    time.sleep(1)
                    st.markdown("""
                    \tFor products belonging to the "TOYS" category, the top 3 reasons for delays are: Shipping Problems, Operational Delays and Inventory Issues with 2061, 1985, and 1942 delays respectively.\n
                    """)
                elif drop_down == "ELECTRONICS":
                    time.sleep(1)
                    st.markdown("""
                    \tFor products belonging to the "ELECTRONICS" category, the top 3 reasons for delays are: Operational Delays, Inventory Issues and Shipping Problems with 1742, 1712, and 1677 delays respectively.\n
                    """)
                elif drop_down == "FURNITURE":
                    time.sleep(1)
                    st.markdown("""
                    \tFor products belonging to the "FURNITURE" category, the top 3 reasons for delays are: Supplier Delays, Operational Delays and Inventory Issues with 1819, 1813, and 1753 delays respectively.\n
                    """)



            elif selected_query == "Which products or categories have the highest average replacement frequency?":
                if drop_down == "FOOD":
                    time.sleep(1)
                    st.markdown("""
                    \tFor the category "FOOD", the product IDs correspondiong to products that have the highest average replacement frequency are as follows:
                    \t\t1. PROD0307: The average replacement frequency is 3.09.
                    \t\t2. PROD0085: The average replacement frequency is 3.
                    \t\t3. PROD0395: The average replacement frequency is 2.94.
                    \t\t4. PROD0545: The average replacement frequency is 2.91.
                    \t\t5. PROD0506: The average replacement frequency is 2.87.
                    \t\t6. PROD0705: The average replacement frequency is 2.87.
                    \t\t7. PROD0049: The average replacement frequency is 2.86.
                    \t\t8. PROD0004: The average replacement frequency is 2.85.
                    \t\t9. PROD0629: The average replacement frequency is 2.85.
                    \t\t10. PROD0202: The average replacement frequency is 2.83.
                    """)

                elif drop_down == "CLOTHING":
                    time.sleep(1)
                    st.markdown("""
                    \tFor the category "CLOTHING", the product IDs correspondiong to products that have the highest average replacement frequency are as follows:
                    \t\t1. PROD0910: The average replacement frequency is 3.07.
                    \t\t2. PROD0754: The average replacement frequency is 3.06.
                    \t\t3. PROD0157: The average replacement frequency is 3.05.
                    \t\t4. PROD0879: The average replacement frequency is 2.98.
                    \t\t5. PROD0027: The average replacement frequency is 2.95.
                    \t\t6. PROD0569: The average replacement frequency is 2.91.
                    \t\t7. PROD0727: The average replacement frequency is 2.91.
                    \t\t8. PROD0894: The average replacement frequency is 2.9.
                    \t\t9. PROD0989: The average replacement frequency is 2.89.
                    \t\t10. PROD0332: The average replacement frequency is 2.89.
                    """)

                elif drop_down == "TOYS":
                    time.sleep(1)
                    st.markdown("""
                    \tFor the category "TOYS", the product IDs correspondiong to products that have the highest average replacement frequency are as follows:
                    \t\t1. PROD0144: The average replacement frequency is 3.07.
                    \t\t2. PROD0327: The average replacement frequency is 3.06.
                    \t\t3. PROD0919: The average replacement frequency is 3.05.
                    \t\t4. PROD0516: The average replacement frequency is 3.02.
                    \t\t5. PROD0995: The average replacement frequency is 2.98.
                    \t\t6. PROD0527: The average replacement frequency is 2.97.
                    \t\t7. PROD0272: The average replacement frequency is 2.97.
                    \t\t8. PROD0565: The average replacement frequency is 2.93.
                    \t\t9. PROD0950: The average replacement frequency is 2.92.
                    \t\t10. PROD0971: The average replacement frequency is 2.87.
                    """)
                elif drop_down == "ELECTRONICS":
                    time.sleep(1)
                    st.markdown("""
                    \tFor the category "ELECTRONICS", the product IDs correspondiong to products that have the highest average replacement frequency are as follows:
                    \t1. PROD0651: The average replacement frequency is 3.06.
                    \t2. PROD0135: The average replacement frequency is 3.03.
                    \t3. PROD0895: The average replacement frequency is 3.02.
                    \t4. PROD0117: The average replacement frequency is 2.92.
                    \t5. PROD0177: The average replacement frequency is 2.91.
                    \t6. PROD0151: The average replacement frequency is 2.87.
                    \t7. PROD0362: The average replacement frequency is 2.86.
                    \t8. PROD0534: The average replacement frequency is 2.86.
                    \t9. PROD0320: The average replacement frequency is 2.85.
                    \t10. PROD0082: The average replacement frequency is 2.84.
                    """)

                elif drop_down == "FURNITURE":
                    time.sleep(1)
                    st.markdown("""
                    \tFor the category "FURNITURE", the product IDs correspondiong to products that have the highest average replacement frequency are as follows:
                    \t1. PROD0120: The average replacement frequency is 2.96.
                    \t2. PROD0663: The average replacement frequency is 2.95.
                    \t3. PROD0067: The average replacement frequency is 2.95.
                    \t4. PROD0376: The average replacement frequency is 2.94.
                    \t5. PROD0270: The average replacement frequency is 2.93.
                    \t6. PROD0889: The average replacement frequency is 2.88.
                    \t7. PROD0001: The average replacement frequency is 2.86.
                    \t8. PROD0185: The average replacement frequency is 2.84.
                    \t9. PROD0429: The average replacement frequency is 2.83.
                    \t10. PROD0916: The average replacement frequency is 2.8.
                    """)


            elif selected_query == "How does the order fulfillment rate differ across various product categories?":
                if drop_down == "FOOD":
                    time.sleep(1)
                    st.markdown("""
                    \tFor the category "FOOD", the average order fulfillment rate is 89.95%.
                    """)

                elif drop_down == "CLOTHING":
                    time.sleep(1)
                    st.markdown("""
                    \tFor the category "CLOTHING", the average order fulfillment rate is 89.94%.
                    """)

                elif drop_down == "TOYS":
                    time.sleep(1)
                    st.markdown("""
                    \tFor the category "TOYS", the average order fulfillment rate is 89.96%.
                    """)
                elif drop_down == "ELECTRONICS":
                    time.sleep(1)
                    st.markdown("""
                    \tFor the category "ELECTRONICS", the average order fulfillment rate is 89.93%.
                    """)
                elif drop_down == "FURNITURE":
                    time.sleep(1)
                    st.markdown("""
                    \tFor the category "FURNITURE", the average order fulfillment rate is 90.01%.
                    """)

    with col[1]:
        if selected_query and drop_down:
            if selected_query == "What are the top 3 most common reasons for delays in order fulfillment and which product categories are most severely affected by delays?":
                if drop_down == "FOOD":
                    result = execute_query(
                        "SELECT p.Category, o.Delay_Reason, COUNT(o.Transaction_ID) AS Delay_Count FROM retail_panopticon.orderFulfillment o JOIN retail_panopticon.transactions t ON o.Transaction_ID = t.Transaction_ID JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID WHERE o.`On-Time_Fulfillment_Rate` < 100 AND o.Delay_Reason IS NOT NULL AND p.Category='Food' AND o.Delay_Reason != '' GROUP BY p.Category, o.Delay_Reason ORDER BY Delay_Count DESC LIMIT 3;",
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "CLOTHING":
                    result = execute_query(
                        "SELECT p.Category, o.Delay_Reason, COUNT(o.Transaction_ID) AS Delay_Count FROM retail_panopticon.orderFulfillment o JOIN retail_panopticon.transactions t ON o.Transaction_ID = t.Transaction_ID JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID WHERE o.`On-Time_Fulfillment_Rate` < 100 AND o.Delay_Reason IS NOT NULL AND p.Category='Clothing' AND o.Delay_Reason != '' GROUP BY p.Category, o.Delay_Reason ORDER BY Delay_Count DESC LIMIT 3;",
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "TOYS":
                    result = execute_query(
                        "SELECT p.Category, o.Delay_Reason, COUNT(o.Transaction_ID) AS Delay_Count FROM retail_panopticon.orderFulfillment o JOIN retail_panopticon.transactions t ON o.Transaction_ID = t.Transaction_ID JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID WHERE o.`On-Time_Fulfillment_Rate` < 100 AND o.Delay_Reason IS NOT NULL AND p.Category='Toys' AND o.Delay_Reason != '' GROUP BY p.Category, o.Delay_Reason ORDER BY Delay_Count DESC LIMIT 3;",
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "ELECTRONICS":
                    result = execute_query(
                        "SELECT p.Category, o.Delay_Reason, COUNT(o.Transaction_ID) AS Delay_Count FROM retail_panopticon.orderFulfillment o JOIN retail_panopticon.transactions t ON o.Transaction_ID = t.Transaction_ID JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID WHERE o.`On-Time_Fulfillment_Rate` < 100 AND o.Delay_Reason IS NOT NULL AND p.Category='Electronics' AND o.Delay_Reason != '' GROUP BY p.Category, o.Delay_Reason ORDER BY Delay_Count DESC LIMIT 3;",
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "FURNITURE":
                    result = execute_query(
                        "SELECT p.Category, o.Delay_Reason, COUNT(o.Transaction_ID) AS Delay_Count FROM retail_panopticon.orderFulfillment o JOIN retail_panopticon.transactions t ON o.Transaction_ID = t.Transaction_ID JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID WHERE o.`On-Time_Fulfillment_Rate` < 100 AND o.Delay_Reason IS NOT NULL AND p.Category='Furniture' AND o.Delay_Reason != '' GROUP BY p.Category, o.Delay_Reason ORDER BY Delay_Count DESC LIMIT 3;",
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)


            elif selected_query == "Which products or categories have the highest average replacement frequency?":
                if drop_down == "FOOD":
                    result = execute_query(
                        "SELECT p.Product_ID,p.Product_Description,p.Category, ROUND(AVG(r.Replacement_Order_Frequency), 2) AS Avg_Replacement_Frequency FROM retail_panopticon.replacementsAndDefects r JOIN retail_panopticon.transactions t ON r.Transaction_ID = t.Transaction_ID JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID WHERE p.Category='Food' GROUP BY p.Product_ID,p.Product_Description,p.Category ORDER BY Avg_Replacement_Frequency DESC LIMIT 10;",
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "CLOTHING":
                    result = execute_query(
                        "SELECT p.Product_ID,p.Product_Description,p.Category, ROUND(AVG(r.Replacement_Order_Frequency), 2) AS Avg_Replacement_Frequency FROM retail_panopticon.replacementsAndDefects r JOIN retail_panopticon.transactions t ON r.Transaction_ID = t.Transaction_ID JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID WHERE p.Category='Clothing' GROUP BY p.Product_ID,p.Product_Description,p.Category ORDER BY Avg_Replacement_Frequency DESC LIMIT 10;",
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "TOYS":
                    result = execute_query(
                        "SELECT p.Product_ID,p.Product_Description,p.Category, ROUND(AVG(r.Replacement_Order_Frequency), 2) AS Avg_Replacement_Frequency FROM retail_panopticon.replacementsAndDefects r JOIN retail_panopticon.transactions t ON r.Transaction_ID = t.Transaction_ID JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID WHERE p.Category='Toys' GROUP BY p.Product_ID,p.Product_Description,p.Category ORDER BY Avg_Replacement_Frequency DESC LIMIT 10;",
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "ELECTRONICS":
                    result = execute_query(
                        "SELECT p.Product_ID,p.Product_Description,p.Category, ROUND(AVG(r.Replacement_Order_Frequency), 2) AS Avg_Replacement_Frequency FROM retail_panopticon.replacementsAndDefects r JOIN retail_panopticon.transactions t ON r.Transaction_ID = t.Transaction_ID JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID WHERE p.Category='Electronics' GROUP BY p.Product_ID,p.Product_Description,p.Category ORDER BY Avg_Replacement_Frequency DESC LIMIT 10;",
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "FURNITURE":
                    result = execute_query(
                        "SELECT p.Product_ID,p.Product_Description,p.Category, ROUND(AVG(r.Replacement_Order_Frequency), 2) AS Avg_Replacement_Frequency FROM retail_panopticon.replacementsAndDefects r JOIN retail_panopticon.transactions t ON r.Transaction_ID = t.Transaction_ID JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID WHERE p.Category='Furniture' GROUP BY p.Product_ID,p.Product_Description,p.Category ORDER BY Avg_Replacement_Frequency DESC LIMIT 10;",
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

            elif selected_query == "How does the order fulfillment rate differ across various product categories?":
                if drop_down == "FOOD":
                    result = execute_query(
                        "SELECT Product_Category, ROUND(AVG(p.Fulfillment_Rate_Category), 2) AS Avg_Fulfillment_Rate FROM retail_panopticon.productAndRegionPerformance p WHERE Product_Category ='Food' GROUP BY Product_Category",
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "CLOTHING":
                    result = execute_query(
                        "SELECT Product_Category, ROUND(AVG(p.Fulfillment_Rate_Category), 2) AS Avg_Fulfillment_Rate FROM retail_panopticon.productAndRegionPerformance p WHERE Product_Category ='Clothing' GROUP BY Product_Category",
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "TOYS":
                    result = execute_query(
                        "SELECT Product_Category, ROUND(AVG(p.Fulfillment_Rate_Category), 2) AS Avg_Fulfillment_Rate FROM retail_panopticon.productAndRegionPerformance p WHERE Product_Category ='Toys' GROUP BY Product_Category",
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "ELECTRONICS":
                    result = execute_query(
                        "SELECT Product_Category, ROUND(AVG(p.Fulfillment_Rate_Category), 2) AS Avg_Fulfillment_Rate FROM retail_panopticon.productAndRegionPerformance p WHERE Product_Category ='Electronics' GROUP BY Product_Category",
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "FURNITURE":
                    result = execute_query(
                        "SELECT Product_Category, ROUND(AVG(p.Fulfillment_Rate_Category), 2) AS Avg_Fulfillment_Rate FROM retail_panopticon.productAndRegionPerformance p WHERE Product_Category ='Furniture' GROUP BY Product_Category",
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

def warehouse_management_app(persona, options):
    queries = get_queries_from_db(persona)

    st.markdown("""
            <style>
            div.stButton {
                display: flex;
                justify-content: flex-end; /* Align button to the right */
                margin-top: 10px;
            }

            /* Custom CSS for the dropdowns to align right and be smaller */
            div.streamlit-expander {
                width: 100%; /* Make sure it fills the container */
            }

            div.streamlit-expander > div {
                width: 30%; /* Set the width of the selectbox */
                margin-left: auto; /* Push it to the right */
            }

            /* Smaller font size for selectbox options */
            .stSelectbox div {
                font-size: 12px; /* Smaller font size */
            }

            </style>
            """, unsafe_allow_html=True)
    col1, col2 = st.columns([4, 1])
    with col2:
        drop_down = st.selectbox("", options)
    unpin_button_pressed = st.button("DELETE", key='unpin_button')
    selected_query = st.selectbox("Select a query", queries if queries else ["Select a query"])

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    col = st.columns((1, 1), gap='medium')
    conn = connect_to_db(DB_NAME)

    with col[0]:
        if unpin_button_pressed:
            if selected_query != "Select a query":
                queries.pop(selected_query, None)
                st.success(f"Query '{selected_query}' has been removed.")
            else:
                st.warning("Select a query to unpin.")

        if drop_down and selected_query and selected_query != "Select a query" and not unpin_button_pressed and drop_down != "SELECT STORE":
            # result = execute_query(queries[selected_query], conn)
            if selected_query == "How efficient are our warehouse operations in terms of throughput and processing time for inbound and outbound shipments for products which have a low stock availability (<10)?":
                if drop_down == "SUPP078":
                    time.sleep(1)
                    st.markdown("""
                    \tFor this supplier, the product with ID PROD0674, i.e., Butter (Food) has low stock availability. The performance of the supplier for this product in terms of warehouse efficiency is as follows:
                    \t\t 1. Warehouse Throughput: 99,508.4
                    \t\t 2. Inbound Processing Time: 3.65
                    \t\t 3. Outbound Processing Time: 4.05
                    \t\t 4. Warehouse Efficiency: 85.55
                    """)

                elif drop_down == "SUPP083":
                    time.sleep(1)
                    st.markdown("""
                    \tFor this supplier, the product with ID PROD0725, i.e., Shirt (Clothing) has low stock availability. The performance of the supplier for this product in terms of warehouse efficiency is as follows:
                    \t\t 1. Warehouse Throughput: 97,408.6
                    \t\t 2. Inbound Processing Time: 3.73
                    \t\t 3. Outbound Processing Time: 4.13
                    \t\t 4. Warehouse Efficiency: 83.74
                    """)

                elif drop_down == "SUPP066":
                    time.sleep(1)
                    st.markdown("""
                    \tFor this supplier, the product with ID PROD0215, i.e., Headphones (Electronics) has low stock availability. The performance of the supplier for this product in terms of warehouse efficiency is as follows:
                    \t\t 1. Warehouse Throughput: 91,906.8
                    \t\t 2. Inbound Processing Time: 3.95
                    \t\t 3. Outbound Processing Time: 4.38
                    \t\t 4. Warehouse Efficiency: 79.01
                    """)
                elif drop_down == "SUPP073":
                    time.sleep(1)
                    st.markdown("""
                    \tFor this supplier, the product with ID PROD0490, i.e., Board Games (Toys) has low stock availability. The performance of the supplier for this product in terms of warehouse efficiency is as follows:
                    \t\t 1. Warehouse Throughput: 89,571.8
                    \t\t 2. Inbound Processing Time: 4.05
                    \t\t 3. Outbound Processing Time: 4.5
                    \t\t 4. Warehouse Efficiency: 77
                    """)

            elif selected_query == "How effectively are we managing our warehouse space to maximize storage capacity and minimize handling costs?":
                if drop_down == "SUPP078":
                    time.sleep(1)
                    st.markdown("""
                    \tFor this supplier, the warehouse utilization costs are as follows:
                    \t\t 1. Warehouse Space Utilization: 7.88
                    \t\t 2. Storage Capacity Metric: 13,667.2
                    \t\t 3. Handling Costs: 2,738.78
                    \t\t 4. Utilization Percentage: 0.06
                    \t\t 5. Cost Per Unit Space: 347.56
                    To improve their space optimization strategy, this supplier must improve inventory tracking. 
                    """)

                elif drop_down == "SUPP083":
                    time.sleep(1)
                    st.markdown("""
                    \tFor this supplier, the warehouse utilization costs are as follows:
                    \t\t 1. Warehouse Space Utilization: 11.05
                    \t\t 2. Storage Capacity Metric: 12,832.9
                    \t\t 3. Handling Costs: 1,764.76
                    \t\t 4. Utilization Percentage: 0.09
                    \t\t 5. Cost Per Unit Space: 159.71
                    To improve their space optimization strategy, this supplier must adopt just-in-time inventory. 
                    """)

                elif drop_down == "SUPP066":
                    time.sleep(1)
                    st.markdown("""
                    \tFor this supplier, the warehouse utilization costs are as follows:
                    \t\t 1. Warehouse Space Utilization: 6.56
                    \t\t 2. Storage Capacity Metric: 8519.71
                    \t\t 3. Handling Costs: 1630.82
                    \t\t 4. Utilization Percentage: 0.08
                    \t\t 5. Cost Per Unit Space: 248.6
                    To improve their space optimization strategy, this supplier must reorganize storage layout. 
                    """)
                elif drop_down == "SUPP073":
                    time.sleep(1)
                    st.markdown("""
                    \tFor this supplier, the warehouse utilization costs are as follows:
                    \t\t 1. Warehouse Space Utilization: 5.79
                    \t\t 2. Storage Capacity Metric: 10506.1
                    \t\t 3. Handling Costs: 2815.34
                    \t\t 4. Utilization Percentage: 0.06
                    \t\t 5. Cost Per Unit Space: 486.24
                    To improve their space optimization strategy, this supplier must improve inventory tracking. 
                    """)


            elif selected_query == "Which product categories are the most likely to suffer from shipping delays and what are the primary causes of these delays?":
                if drop_down == "SUPP078":
                    time.sleep(1)
                    st.markdown("""
                    \tFor this supplier, the department wise breakdown of shipping delays is as follows:
                    \t\t 1. Food: The most common reasons for shipping delays are: Custom Delays, Logistical issues, High demand and weather conditions with 246, 214, 213, and 208 delays respectively.
                    \t\t 2. Electronics: The most common reasons for shipping delays are: Weather conditions, Logistical issues, High demand and Custom Delays with 150, 147, 139, and 139 delays respectively.
                    \t\t 3. Furniture: The most common reasons for shipping delays are: Weather conditions, Logistical issues, Custom Delays and High demand with 124, 115, 110, and 105 delays respectively.
                    \t\t 4. Clothing: The most common reasons for shipping delays are: Custom Delays, Logistical issues, High demand and Weather conditions with 94, 87, 80, and 78 delays respectively.
                    \t\t 5. Toys: The most common reasons for shipping delays are: Weather conditions, High demand, Logistical issues, and Custom delays with 45, 40, 36, and 33 delays respectively. 
                    """)

                elif drop_down == "SUPP083":
                    time.sleep(1)
                    st.markdown("""
                    \tFor this supplier, the department wise breakdown of shipping delays is as follows:
                    \t\t 1. Furniture: The most common reasons for shipping delays are: Custom delays, Weather conditions, Logistical issues and High demand with 209, 203, 195, and 192 delays respectively.
                    \t\t 2. Food: The most common reasons for shipping delays are: Weather conditions, Custom delays, High demand and Logistical issues with 193, 189, 180, and 163 delays respectively.
                    \t\t 3. Clothing: The most common reasons for shipping delays are: Logistical issues, Weather conditions, High demand and Custom Delays with 163, 160, 151, and 127 delays respectively.
                    \t\t 4. Toys: The most common reasons for shipping delays are: Logistical issues, Custom Delays, Weather conditions and High demand with 79, 74, 64, and 61 delays respectively.
                    \t\t 5. Electronics: The most common reasons for shipping delays are: High demand, Weather conditions, Logistical issues, and Custom delays with 44, 39, 33, and 25 delays respectively. 
                    """)

                elif drop_down == "SUPP066":
                    time.sleep(1)
                    st.markdown("""
                    \tFor this supplier, the department wise breakdown of shipping delays is as follows:
                    \t\t 1. Toys: The most common reasons for shipping delays are: High demand, Custom delays, Weather conditions and Logistical issues with 166, 152, 134, and 128 delays respectively.
                    \t\t 2. Clothing: The most common reasons for shipping delays are: Logistical issues, Weather conditions, Custom delays and High demand with 164, 153, 152, and 143 delays respectively.
                    \t\t 3. Furniture: The most common reasons for shipping delays are: Weather conditions, High demand, Custom Delays and Logistical issues with 51, 43, 35, and 35 delays respectively.
                    \t\t 4. Food: The most common reasons for shipping delays are: High demand, Logistical issues, Custom delays and Weather conditions with 47, 39, 38, and 34 delays respectively.
                    \t\t 5. Electronics: The most common reasons for shipping delays are: Weather conditions, High demand, Logistical issues, and Custom delays with 40, 31, 27, and 21 delays respectively. 
                    """)

                elif drop_down == "SUPP073":
                    time.sleep(1)
                    st.markdown("""
                    \tFor this supplier, the department wise breakdown of shipping delays is as follows:
                    \t\t 1. Toys: The most common reasons for shipping delays are: Custom delays, High demand, Weather conditions and Logistical issues with 126, 123, 117, and 114 delays respectively.
                    \t\t 2. Clothing: The most common reasons for shipping delays are: Custom delays, Weather conditions, High demand and Logistical issues with 122, 111, 107, and 103 delays respectively.
                    \t\t 3. Electronics: The most common reasons for shipping delays are: Weather conditions, Custom delays, Logistical issues and High demand with 119, 115, 109, and 101 delays respectively.
                    \t\t 4. Food: The most common reasons for shipping delays are: Weather conditions, High demand, Custom delays, and Logistical issues with 90, 84, 78, and 67 delays respectively.
                    \t\t 5. Furniture: The most common reasons for shipping delays are: Weather conditions, High demand, Logistical issues, and Custom delays with 48, 40, 37, and 34 delays respectively. 
                    """)

    with col[1]:
        if selected_query and drop_down:
            if selected_query == "How efficient are our warehouse operations in terms of throughput and processing time for inbound and outbound shipments for products which have a low stock availability (<10)?":
                if drop_down == "SUPP078":
                    result = execute_query(
                        """SELECT p.product_ID,p.Product_Description, w.Supplier_ID,
                               w.Warehouse_Throughput,
                               w.Inbound_Processing_Time,
                               w.Outbound_Processing_Time,
                               w.Warehouse_Operations_Efficiency_Metric
                            FROM retail_panopticon.productInformation p
                            JOIN retail_panopticon.warehouseThroughput w ON p.Supplier_ID = w.Supplier_ID
                            WHERE p.Stock_Availability < 10 and w.Supplier_ID='SUPP078'
                            GROUP BY p.Product_Description, w.Supplier_ID,w.Warehouse_Throughput,w.Inbound_Processing_Time,
                             w.Outbound_Processing_Time,w.Warehouse_Operations_Efficiency_Metric
                            ORDER BY w.Warehouse_Operations_Efficiency_Metric DESC;
                            """,conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "SUPP083":
                    result = execute_query(
                        """SELECT p.product_ID,p.Product_Description, w.Supplier_ID,
                               w.Warehouse_Throughput,
                               w.Inbound_Processing_Time,
                               w.Outbound_Processing_Time,
                               w.Warehouse_Operations_Efficiency_Metric
                            FROM retail_panopticon.productInformation p
                            JOIN retail_panopticon.warehouseThroughput w ON p.Supplier_ID = w.Supplier_ID
                            WHERE p.Stock_Availability < 10 and w.Supplier_ID='SUPP083'
                            GROUP BY p.Product_Description, w.Supplier_ID,w.Warehouse_Throughput,w.Inbound_Processing_Time,
                             w.Outbound_Processing_Time,w.Warehouse_Operations_Efficiency_Metric
                            ORDER BY w.Warehouse_Operations_Efficiency_Metric DESC;
                            """,
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "SUPP066":
                    result = execute_query(
                        """SELECT p.product_ID,p.Product_Description, w.Supplier_ID,
                               w.Warehouse_Throughput,
                               w.Inbound_Processing_Time,
                               w.Outbound_Processing_Time,
                               w.Warehouse_Operations_Efficiency_Metric
                            FROM retail_panopticon.productInformation p
                            JOIN retail_panopticon.warehouseThroughput w ON p.Supplier_ID = w.Supplier_ID
                            WHERE p.Stock_Availability < 10 and w.Supplier_ID='SUPP066'
                            GROUP BY p.Product_Description, w.Supplier_ID,w.Warehouse_Throughput,w.Inbound_Processing_Time,
                             w.Outbound_Processing_Time,w.Warehouse_Operations_Efficiency_Metric
                            ORDER BY w.Warehouse_Operations_Efficiency_Metric DESC;
                            """,
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "SUPP073":
                    result = execute_query(
                        """SELECT p.product_ID,p.Product_Description, w.Supplier_ID,
                               w.Warehouse_Throughput,
                               w.Inbound_Processing_Time,
                               w.Outbound_Processing_Time,
                               w.Warehouse_Operations_Efficiency_Metric
                            FROM retail_panopticon.productInformation p
                            JOIN retail_panopticon.warehouseThroughput w ON p.Supplier_ID = w.Supplier_ID
                            WHERE p.Stock_Availability < 10 and w.Supplier_ID='SUPP073'
                            GROUP BY p.Product_Description, w.Supplier_ID,w.Warehouse_Throughput,w.Inbound_Processing_Time,
                             w.Outbound_Processing_Time,w.Warehouse_Operations_Efficiency_Metric
                            ORDER BY w.Warehouse_Operations_Efficiency_Metric DESC;
                            """,
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)


            elif selected_query == "Which products or categories have the highest average replacement frequency?":
                if drop_down == "SUPP078":
                    result = execute_query(
                        """SELECT w.Supplier_ID,w.Warehouse_Space_Utilization,w.Storage_Capacity_Metric,
                            w.Handling_Costs,w.Space_Optimization_Strategies,
                            ROUND(
                                CASE
                                    WHEN w.Storage_Capacity_Metric > 0 THEN
                                        (w.Warehouse_Space_Utilization / w.Storage_Capacity_Metric) * 100
                                    ELSE
                                        0
                                END,2) AS Utilization_Percentage,
                            ROUND(
                                CASE
                                    WHEN w.Warehouse_Space_Utilization > 0 THEN
                                        w.Handling_Costs / w.Warehouse_Space_Utilization
                                    ELSE
                                        0
                                END,2 ) AS Cost_Per_Unit_Space
                        FROM retail_panopticon.warehouseUtilization w
                        WHERE w.Supplier_ID='SUPP078'
                        ORDER BY  Utilization_Percentage DESC, Cost_Per_Unit_Space ASC;""",conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "SUPP083":
                    result = execute_query(
                        """SELECT w.Supplier_ID,w.Warehouse_Space_Utilization,w.Storage_Capacity_Metric,
                            w.Handling_Costs,w.Space_Optimization_Strategies,
                            ROUND(
                                CASE
                                    WHEN w.Storage_Capacity_Metric > 0 THEN
                                        (w.Warehouse_Space_Utilization / w.Storage_Capacity_Metric) * 100
                                    ELSE
                                        0
                                END,2) AS Utilization_Percentage,
                            ROUND(
                                CASE
                                    WHEN w.Warehouse_Space_Utilization > 0 THEN
                                        w.Handling_Costs / w.Warehouse_Space_Utilization
                                    ELSE
                                        0
                                END,2 ) AS Cost_Per_Unit_Space
                        FROM retail_panopticon.warehouseUtilization w
                        WHERE w.Supplier_ID='SUPP083'
                        ORDER BY  Utilization_Percentage DESC, Cost_Per_Unit_Space ASC;""",conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "SUPP066":
                    result = execute_query(
                        """SELECT w.Supplier_ID,w.Warehouse_Space_Utilization,w.Storage_Capacity_Metric,
                            w.Handling_Costs,w.Space_Optimization_Strategies,
                            ROUND(
                                CASE
                                    WHEN w.Storage_Capacity_Metric > 0 THEN
                                        (w.Warehouse_Space_Utilization / w.Storage_Capacity_Metric) * 100
                                    ELSE
                                        0
                                END,2) AS Utilization_Percentage,
                            ROUND(
                                CASE
                                    WHEN w.Warehouse_Space_Utilization > 0 THEN
                                        w.Handling_Costs / w.Warehouse_Space_Utilization
                                    ELSE
                                        0
                                END,2 ) AS Cost_Per_Unit_Space
                        FROM retail_panopticon.warehouseUtilization w
                        WHERE w.Supplier_ID='SUPP083'
                        ORDER BY  Utilization_Percentage DESC, Cost_Per_Unit_Space ASC;""",conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "SUPP073":
                    result = execute_query(
                        """SELECT w.Supplier_ID,w.Warehouse_Space_Utilization,w.Storage_Capacity_Metric,
                            w.Handling_Costs,w.Space_Optimization_Strategies,
                            ROUND(
                                CASE
                                    WHEN w.Storage_Capacity_Metric > 0 THEN
                                        (w.Warehouse_Space_Utilization / w.Storage_Capacity_Metric) * 100
                                    ELSE
                                        0
                                END,2) AS Utilization_Percentage,
                            ROUND(
                                CASE
                                    WHEN w.Warehouse_Space_Utilization > 0 THEN
                                        w.Handling_Costs / w.Warehouse_Space_Utilization
                                    ELSE
                                        0
                                END,2 ) AS Cost_Per_Unit_Space
                        FROM retail_panopticon.warehouseUtilization w
                        WHERE w.Supplier_ID='SUPP073'
                        ORDER BY  Utilization_Percentage DESC, Cost_Per_Unit_Space ASC;""",
                        conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

            elif selected_query == "How does the order fulfillment rate differ across various product categories?":
                if drop_down == "SUPP078":
                    result = execute_query(
                """SELECT p.Category, s.Reason_Late_Shipment,
                COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments
                FROM retail_panopticon.transactions t
                JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID
                JOIN retail_panopticon.shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID
                WHERE p.Supplier_ID='SUPP078'
                GROUP BY p.Category, s.Reason_Late_Shipment
                HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0
                ORDER BY Total_Late_Shipments DESC;""",conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "SUPP083":
                    result = execute_query(
            """SELECT p.Category, s.Reason_Late_Shipment,
                COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments
                FROM retail_panopticon.transactions t
                JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID
                JOIN retail_panopticon.shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID
                WHERE p.Supplier_ID='SUPP083'
                GROUP BY p.Category, s.Reason_Late_Shipment
                HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0
                ORDER BY Total_Late_Shipments DESC;""",conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "SUPP066":
                    result = execute_query(
                        """SELECT p.Category, s.Reason_Late_Shipment,
                COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments
                FROM retail_panopticon.transactions t
                JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID
                JOIN retail_panopticon.shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID
                WHERE p.Supplier_ID='SUPP066'
                GROUP BY p.Category, s.Reason_Late_Shipment
                HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0
                ORDER BY Total_Late_Shipments DESC;""",conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "SUPP073":
                    result = execute_query(
                        """SELECT p.Category, s.Reason_Late_Shipment,
                COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments
                FROM retail_panopticon.transactions t
                JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID
                JOIN retail_panopticon.shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID
                WHERE p.Supplier_ID='SUPP073'
                GROUP BY p.Category, s.Reason_Late_Shipment
                HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0
                ORDER BY Total_Late_Shipments DESC;""", conn)
                    l_figures = create_figures2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)


def management_appIM(persona, options):
    queries = get_queries_from_db(persona)

    st.markdown("""
            <style>
            div.stButton {
                display: flex;
                justify-content: flex-end; /* Align button to the right */
                margin-top: 10px;
            }

            /* Custom CSS for the dropdowns to align right and be smaller */
            div.streamlit-expander {
                width: 100%; /* Make sure it fills the container */
            }

            div.streamlit-expander > div {
                width: 30%; /* Set the width of the selectbox */
                margin-left: auto; /* Push it to the right */
            }

            /* Smaller font size for selectbox options */
            .stSelectbox div {
                font-size: 12px; /* Smaller font size */
            }

            </style>
            """, unsafe_allow_html=True)
    col1, col2 = st.columns([4, 1])
    with col2:
        drop_down = st.selectbox("", options)

    unpin_button_pressed = st.button("DELETE", key='unpin_button')
    selected_query = st.selectbox("Select a query", queries if queries else ["Select a query"])

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    col = st.columns((1, 1), gap='medium')
    conn = connect_to_db(DB_NAME)

    with col[0]:
        if unpin_button_pressed:
            if selected_query != "Select a query":
                queries.pop(selected_query, None)
                st.success(f"Query '{selected_query}' has been removed.")
            else:
                st.warning("Select a query to unpin.")

        if drop_down and selected_query and selected_query != "Select a query" and not unpin_button_pressed and drop_down != "SELECT STORE":
            # result = execute_query(queries[selected_query], conn)
            if selected_query == "How do we optimize inventory levels and replenishment for high-stockout products to match sales and reduce stockouts?":
                if drop_down == "INVENTORY FOR TOYS":
                    time.sleep(1)
                    st.markdown("""
                            Inventory Adjustments:\tConsidering 'PROD0011' and 'PROD0933' with sales over 800 units but low inventory levels relative to sales, it's advisable to adjust their inventory thresholds.\n
                            Lead Time Reduction:\tWork on reducing lead times, especially for products like 'PROD0507' and 'PROD0706', which have lead times exceeding 16 days, to enhance responsiveness and reduce the risk of stockouts.\n
                            Replenishment Strategy:\tImplement more dynamic replenishment strategies responsive to changes in demand, notably for toys like action figures and board games with rapid turnover rates.\n
                            Backorder Management:\tRefine the backorder management processes for products like 'PROD0277' and 'PROD0950' to mitigate the impact on customer satisfaction and sales.\n
                            Analytical Review:\tContinuously monitor and analyze sales data, inventory levels, and replenishment metrics to align the stocking strategy with market demands and logistical capabilities, effectively preventing both overstock and understock scenarios.\n
                            """)

                elif drop_down == "INVENTORY FOR CLOTHING":
                    time.sleep(1)
                    st.markdown("""
                            Inventory Adjustments:\tSignificant sales items like 'PROD0519' (T-Shirt) and 'PROD0554' (Shirt) have high sales but lower than expected inventory levels, suggesting a need to increase their inventory to better match sales performance and minimize stockouts.\n
                            Lead Time Reduction:\tFocus on products like 'PROD0176' (Jacket) and 'PROD0785' (T-Shirt) with the highest lead times over 24 days, suggesting a strategic need to negotiate faster supplier responses or find alternative suppliers to shorten the replenishment cycle.\n
                            Replenishment Strategy:\tAdopt a flexible replenishment strategy especially for fast-moving items like 'PROD0547' (T-Shirt) and 'PROD0910' (T-Shirt), ensuring replenishment frequency aligns with their sales velocity to avoid potential stockouts.\n
                            Backorder Management:\tEnhance backorder management for 'PROD0165' (Jeans) and 'PROD0261' (T-Shirt) that show higher stockout incidents alongside significant lead times, to better manage customer expectations and improve satisfaction.\n
                            Analytical Review:\tRigorously review and adjust inventory parameters regularly, using advanced analytics to predict and respond to market demands more effectively, particularly for high-turnover categories like T-Shirts and Jeans to optimize both stock levels and sales outcomes.\n
                            """)

                elif drop_down == "INVENTORY FOR FURNITURE":
                    time.sleep(1)
                    st.markdown("""
                            Sales Volume and Inventory Levels:\tHigh sales products like sofas and wardrobes should maintain higher inventory levels to meet demand without frequent stockouts.\n
                            Replenishment Lead Times:\tProducts with high lead times like PROD0801 (Sofa) with 29.13 days indicate a need to enhance supply chain efficiency or find alternate suppliers to reduce these times.\n
                            Backorder and Stockout Management:\tFor items with higher stockout incidents and backorders, such as several sofas and chairs noted with up to 9 incidents, it's crucial to adjust safety stock levels and reorder points accordingly.\n
                            Continuous Monitoring:\tRegularly review sales data and inventory metrics to adjust stock levels dynamically, preventing overstock and understock situations.\n
                            Strategic Supplier Relationships:\tEngage with suppliers to ensure they can meet rapid replenishment needs, especially for high-turnover items, to minimize lead times and respond quickly to market demand changes.\n
                            """)

            elif selected_query == "Which high-sales products have low turnover rates, and what are the lead times and safety stock levels for these products?":
                if drop_down == "INVENTORY FOR TOYS":
                    time.sleep(1)
                    st.markdown("""
                            Inventory Adjustments:\tAdjust inventory levels for high-sales items such as 'PROD0107' and 'PROD0608', which are significant contributors to sales but may have inadequate inventory levels to sustain market demand consistently.\n
                            Lead Time Reduction:\tParticularly for products like 'PROD0217' and 'PROD0608' with exceptionally long lead times (over 26 days), efforts should be made to negotiate better terms with suppliers or find alternative supply sources to accelerate replenishment cycles.\n
                            Replenishment Strategy:\tEmploy more dynamic replenishment strategies tailored to demand volatility, especially for high-turnover toys such as action figures ('PROD0608') and board games ('PROD0523'), ensuring replenishment rates are attuned to actual sales performance.\n
                            Backorder Management:\tOptimize backorder processes for items like 'PROD0924' and 'PROD0608', which have high safety stock levels yet face significant replenishment lead times, to mitigate negative customer impacts.\n
                            Analytical Review:\tMaintain rigorous monitoring of sales patterns, stock levels, and replenishment data. This continuous analytical approach will help fine-tune inventory strategies for toys, ensuring a balanced approach between preventing overstocks and minimizing stockouts.\n

                    """)

                elif drop_down == "INVENTORY FOR CLOTHING":
                    time.sleep(1)
                    st.markdown("""
                                Inventory Adjustments:\tGiven the sales figures for products like 'PROD0446' (857 units) and 'PROD0570' (999 units), coupled with relatively low safety stock levels, it’s prudent to revise their inventory thresholds upwards to ensure consistent availability.\n
                                Lead Time Reduction:\tFocus on reducing lead times, especially for products like 'PROD0112' and 'PROD0302', which exhibit extended lead times of over 23 days, to increase supply chain responsiveness and minimize sales disruptions.\n
                                Replenishment Strategy:\tAdopt flexible replenishment strategies that are quick to respond to market changes. This is crucial for items such as 'PROD0652', ensuring that inventory levels are kept optimal relative to sales trends.\n
                                Backorder Management:\tEnhance the management of backorders for products with significant lead times like 'PROD0112' and 'PROD0302' to improve customer satisfaction and maintain competitive advantage.\n
                                Analytical Review:\tRegularly evaluate sales trends, inventory statuses, and replenishment rates for these clothing items. This ongoing review will help align inventory strategies with actual market conditions, thus avoiding overstocks and reducing stockouts effectively.\n
                    """)

                elif drop_down == "INVENTORY FOR FURNITURE":
                    time.sleep(1)
                    st.markdown("""
                            Inventory Adjustments:\tFor high-turnover products like 'PROD00916' with 802 sales and 'PROD0210' with 925 sales, it's crucial to adjust inventory levels upward to prevent stockouts and maintain service levels, considering their inventory turnover rates exceed 100.\n
                            Lead Time Reduction:\tPrioritize reducing lead times for items like 'PROD0210' and 'PROD0343' which have lead times of over 26 days, to better match supply with demand and improve customer satisfaction.\n
                            Replenishment Strategy:\tImplement agile replenishment strategies for all listed products, particularly those with high turnover rates to ensure inventory levels are responsive to sales patterns and customer demand.\n
                            Backorder Management:\tEnhance backorder management for items such as 'PROD0210' and 'PROD0180', ensuring that customers are kept informed and alternatives are offered to mitigate any negative impacts from stockouts.\n
                            Analytical Review:\tRegularly assess performance data such as sales, stock levels, and replenishment lead times for these furniture items to adapt stocking strategies dynamically and efficiently meet market needs.\n
                    """)

            elif selected_query == "For products with frequent stockouts, what are their replenishment accuracy rates, and how do these relate to their sales volumes?":
                if drop_down == "INVENTORY FOR TOYS":
                    time.sleep(1)
                    st.markdown("""
                                Inventory Adjustments:\tFor toys like 'PROD0646' and 'PROD0905' with sales nearing 900 units, it is crucial to adjust their inventory thresholds higher to cope with demand and minimize stockouts, especially given their high sales figures.\n
                                Lead Time Reduction:\tFocus on reducing lead times, particularly for action figures and dolls with replenishment lead times over 20 days, like 'PROD0501' and 'PROD0419', to enhance market responsiveness and customer satisfaction.\n
                                Replenishment Strategy:\tImplement dynamic replenishment strategies that can adapt to changes in demand patterns, particularly for frequently sold items like puzzles and board games that exhibit rapid sales cycles.\n
                                Backorder Management:\tImprove backorder management for high-demand products like 'PROD0933' and 'PROD0475' to better manage customer expectations and maintain service levels during stockouts.\n
                                Analytical Review:\tRegularly monitor and analyze key metrics such as sales data, inventory levels, and replenishment rates to ensure the inventory management strategy remains aligned with current market demands and operational capabilities, thus preventing both overstock and understock situations.\n

                    """)

                elif drop_down == "INVENTORY FOR CLOTHING":
                    time.sleep(1)
                    st.markdown("""
                                Inventory Adjustments:\tFor high-sales items like 'PROD0961' (Jeans) and 'PROD0570' (Shirt), which have sales nearing or exceeding 950 units, it is crucial to adjust their inventory thresholds higher to cope with demand and minimize stockouts.\n
                                Lead Time Reduction:\tFocus on reducing lead times, particularly for items with longer replenishment cycles such as 'PROD0988' (Shirt) and 'PROD0879' (Jeans), which have longer lead times that may impact delivery and restocking efficiency.\n
                                Replenishment Strategy:\tImplement dynamic replenishment strategies that can adapt to changes in demand patterns, especially for frequently sold items like shirts and jeans that exhibit rapid sales cycles.\n
                                Backorder Management:\tImprove backorder management for high-demand products like 'PROD0967' (Shirt) and 'PROD0929' (Jacket) to better manage customer expectations and maintain service levels during stockouts.\n
                                Analytical Review:\tRegularly monitor and analyze key metrics such as sales data, inventory levels, and replenishment rates to ensure the inventory management strategy remains aligned with current market demands and operational capabilities, thus preventing both overstock and understock situations.\n

                    """)

                elif drop_down == "INVENTORY FOR FURNITURE":
                    time.sleep(1)
                    st.markdown("""
                                Inventory Adjustments:\tWith high-sales items like 'PROD0801' (Sofa) achieving over 1000 units, it's advisable to raise their inventory thresholds to meet the demand and reduce potential stockouts, ensuring adequate stock levels are maintained.\n
                                Lead Time Reduction:\tFocus on reducing lead times, particularly for products with longer replenishment cycles such as 'PROD0120' (Bed) and 'PROD0208' (Bed), to improve responsiveness and stock availability.\n
                                Replenishment Strategy:\tImplement dynamic replenishment strategies that are responsive to changes in demand patterns, especially for frequently sold items like sofas and tables that exhibit rapid turnover rates.\n
                                Backorder Management:\tEnhance backorder management processes for high-demand items like 'PROD0084' (Chair) and 'PROD0581' (Chair) to manage customer expectations and maintain satisfaction levels during stockouts.\n
                                Analytical Review:\tRoutinely monitor and analyze sales data, inventory levels, and replenishment rates to ensure the inventory management strategy is aligned with current market demands and operational capabilities, effectively managing both overstock and understock situations.\n

                    """)

    with col[1]:
        if selected_query and drop_down:
            if selected_query == "How do we optimize inventory levels and replenishment for high-stockout products to match sales and reduce stockouts?":
                if drop_down == "INVENTORY FOR TOYS":
                    result = execute_query(
                        "SELECT DATE(t.Date) AS Sale_Date, p.Category AS Product_Category, ROUND(SUM(t.Quantity) / COUNT(t.Transaction_ID), 2) AS UPT\nFROM retail_panopticon.transactions t\nJOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID\nWHERE t.Store_ID = 'STORE01' AND  t.Date BETWEEN '2024-05-01' AND '2024-05-31'\nGROUP BY DATE(t.Date), p.Category\nORDER BY DATE(t.Date), p.Category;",
                        conn)
                    l_figures = create_figuresIM2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "INVENTORY FOR CLOTHING":
                    result = execute_query(
                        "SELECT DATE(t.Date) AS Sale_Date, p.Category AS Product_Category, t.Store_ID, ROUND(SUM(t.Quantity) / COUNT(t.Transaction_ID), 2) AS UPT\nFROM retail_panopticon.transactions t\nJOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID\nWHERE t.Store_ID = 'STORE28' AND  t.Date BETWEEN '2024-05-01' AND '2024-05-31'\nGROUP BY DATE(t.Date), p.Category\nORDER BY DATE(t.Date), p.Category;",
                        conn)
                    l_figures = create_figuresIM2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "INVENTORY FOR FURNITURE":
                    result = execute_query(
                        "SELECT DATE(t.Date) AS Sale_Date, p.Category AS Product_Category, t.Store_ID, ROUND(SUM(t.Quantity) / COUNT(t.Transaction_ID), 2) AS UPT\nFROM retail_panopticon.transactions t\nJOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID\nWHERE t.Store_ID = 'STORE49' AND  t.Date BETWEEN '2024-05-01' AND '2024-05-31'\nGROUP BY DATE(t.Date), p.Category\nORDER BY DATE(t.Date), p.Category;",
                        conn)
                    l_figures = create_figuresIM2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

            elif selected_query == "Which high-sales products have low turnover rates, and what are the lead times and safety stock levels for these products?":
                if drop_down == "INVENTORY FOR TOYS":
                    result = execute_query(
                        "SELECT CASE WHEN DAYOFWEEK(S.date) IN (1, 7) THEN 'Weekend' ELSE 'Weekday' END AS day_type, P.Category,SUM(S.Total_Amount) AS total_sales, COUNT(DISTINCT S.Transaction_ID) AS total_transactions, AVG(S.Total_Amount) AS avg_transaction_value FROM transactions S JOIN productInformation P ON S.Product_ID = P.Product_ID WHERE S.Store_ID = 'STORE01' AND DATE_FORMAT(S.date, '%Y-%m') = '2024-05' GROUP BY day_type, P.Category ORDER BY day_type DESC, total_sales DESC;",
                        conn)
                    l_figures = create_figuresIM2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "INVENTORY FOR CLOTHING":
                    result = execute_query(
                        "SELECT CASE WHEN DAYOFWEEK(S.date) IN (1, 7) THEN 'Weekend' ELSE 'Weekday' END AS day_type, P.Category,SUM(S.Total_Amount) AS total_sales, COUNT(DISTINCT S.Transaction_ID) AS total_transactions, AVG(S.Total_Amount) AS avg_transaction_value FROM transactions S JOIN productInformation P ON S.Product_ID = P.Product_ID WHERE S.Store_ID = 'STORE28' AND DATE_FORMAT(S.date, '%Y-%m') = '2024-05' GROUP BY day_type, P.Category ORDER BY day_type DESC, total_sales DESC;",
                        conn)
                    l_figures = create_figuresIM2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "INVENTORY FOR FURNITURE":
                    result = execute_query(
                        "SELECT CASE WHEN DAYOFWEEK(S.date) IN (1, 7) THEN 'Weekend' ELSE 'Weekday' END AS day_type, P.Category,SUM(S.Total_Amount) AS total_sales, COUNT(DISTINCT S.Transaction_ID) AS total_transactions, AVG(S.Total_Amount) AS avg_transaction_value FROM transactions S JOIN productInformation P ON S.Product_ID = P.Product_ID WHERE S.Store_ID = 'STORE49' AND DATE_FORMAT(S.date, '%Y-%m') = '2024-05' GROUP BY day_type, P.Category ORDER BY day_type DESC, total_sales DESC;",
                        conn)
                    l_figures = create_figuresIM2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

            elif selected_query == "For products with frequent stockouts, what are their replenishment accuracy rates, and how do these relate to their sales volumes?":
                if drop_down == "INVENTORY FOR TOYS":
                    result = execute_query(
                        "SELECT t.Store_ID, p.Category,s.Reason_Late_Shipment, COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments FROM transactions t JOIN productInformation p ON t.Product_ID = p.Product_ID JOIN shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID WHERE t.Store_ID = 'STORE01' GROUP BY p.Category, s.Reason_Late_Shipment HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0 ORDER BY Total_Late_Shipments DESC;",
                        conn)
                    l_figures = create_figuresIM2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "INVENTORY FOR CLOTHING":
                    result = execute_query(
                        "SELECT t.Store_ID, p.Category,s.Reason_Late_Shipment, COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments FROM transactions t JOIN productInformation p ON t.Product_ID = p.Product_ID JOIN shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID WHERE t.Store_ID = 'STORE28' GROUP BY p.Category, s.Reason_Late_Shipment HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0 ORDER BY Total_Late_Shipments DESC;",
                        conn)
                    l_figures = create_figuresIM2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "INVENTORY FOR FURNITURE":
                    result = execute_query(
                        "SELECT t.Store_ID, p.Category,s.Reason_Late_Shipment, COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments FROM transactions t JOIN productInformation p ON t.Product_ID = p.Product_ID JOIN shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID WHERE t.Store_ID = 'STORE49' GROUP BY p.Category, s.Reason_Late_Shipment HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0 ORDER BY Total_Late_Shipments DESC;",
                        conn)
                    l_figures = create_figuresIM2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)


def loss_prevention_app_management_app(persona, options):
    queries = get_queries_from_db(persona)

    st.markdown("""
            <style>
            div.stButton {
                display: flex;
                justify-content: flex-end; /* Align button to the right */
                margin-top: 10px;
            }

            /* Custom CSS for the dropdowns to align right and be smaller */
            div.streamlit-expander {
                width: 100%; /* Make sure it fills the container */
            }

            div.streamlit-expander > div {
                width: 30%; /* Set the width of the selectbox */
                margin-left: auto; /* Push it to the right */
            }

            /* Smaller font size for selectbox options */
            .stSelectbox div {
                font-size: 12px; /* Smaller font size */
            }

            </style>
            """, unsafe_allow_html=True)
    col1, col2 = st.columns([4, 1])
    with col2:
        drop_down = st.selectbox("", options)
    unpin_button_pressed = st.button("DELETE", key='unpin_button')
    selected_query = st.selectbox("Select a query", queries if queries else ["Select a query"])

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    col = st.columns((1, 1), gap='medium')
    conn = connect_to_db(DB_NAME)

    with col[0]:
        if unpin_button_pressed:
            if selected_query != "Select a query":
                queries.pop(selected_query, None)
                st.success(f"Query '{selected_query}' has been removed.")
            else:
                st.warning("Select a query to unpin.")

        if drop_down and selected_query and selected_query != "Select a query" and not unpin_button_pressed and drop_down != "SELECT DEPARTMENT":
            # result = execute_query(queries[selected_query], conn)
            if selected_query == "What are the detailed loss prevention measures for products in departments with a shrinkage rate higher than a specific threshold?":
                if drop_down == "FOOD":
                    time.sleep(1)
                    st.markdown("""
                                Vendor Audits:\tProducts like 'PROD0453' (Eggs) and 'PROD0906' (Eggs) with high shrinkage rates leverage Vendor Audits to ensure supplier compliance and product quality, mitigating potential losses.\n
                                Enhanced Security:\tItems such as 'PROD0744' (Eggs) and 'PROD0449' (Eggs) implement Enhanced Security measures including surveillance systems and theft-prevention protocols to safeguard inventory.\n
                                Inventory Management Systems:\tFor products like 'PROD0591' (Bread) and 'PROD0689' (Butter), utilizing Inventory Management Systems helps track and manage stock levels precisely, reducing discrepancies and preventing loss.\n
                                Customer Awareness Programs:\tEngage customers with awareness programs for products like 'PROD0367' (Milk) and 'PROD0918' (Bread) to educate them about the impacts of shrinkage and promote responsible purchasing.\n
                                Employee Training:\tProducts experiencing higher shrinkage rates, such as 'PROD0838' (Eggs) and 'PROD0359' (Cheese), benefit from Employee Training to enhance staff vigilance and capability in identifying and addressing potential shrinkage sources.\n
                                """)

                elif drop_down == "FURNITURE":
                    time.sleep(1)
                    st.markdown("""
                                Vendor Audits:\tFor furniture products such as 'PROD0934' (Chair) and 'PROD0923' (Wardrobe), Vendor Audits are crucial to ensure compliance with quality and supply chain standards, helping to mitigate shrinkage.\n
                                Enhanced Security:\tProducts like 'PROD0613' (Table) and 'PROD0208' (Bed) utilize Enhanced Security measures, including surveillance and physical security systems, to protect against theft and damage.\n
                                Inventory Management Systems:\tItems such as 'PROD0710' (Bed) and 'PROD0986' (Chair) benefit from Inventory Management Systems that accurately track stock levels and movements to minimize losses due to mismanagement.\n
                                Customer Awareness Programs:\tProducts like 'PROD0928' (Wardrobe) and 'PROD0392' (Table) engage in Customer Awareness Programs to educate customers about the impacts of shrinkage and the value of product care.\n
                                Employee Training:\tItems such as 'PROD0378' (Table) and 'PROD0801' (Sofa) rely on Employee Training to equip staff with the skills necessary to detect and prevent potential losses, enhancing overall security and product handling.\n
                                """)

                elif drop_down == "CLOTHING":
                    time.sleep(1)
                    st.markdown("""
                            Inventory Management Systems:\tFor clothing items like 'PROD0964' (Jacket) and 'PROD0403' (Dress), Inventory Management Systems are crucial for maintaining accurate stock levels and reducing losses due to mismanagement or theft.\n
                            Enhanced Security:\tProducts such as 'PROD0684' (Jeans) and 'PROD0094' (Jacket) implement Enhanced Security measures, including surveillance cameras and security tags, to deter theft and ensure product safety.\n
                            Customer Awareness Programs:\tItems like 'PROD0875' (Jacket) and 'PROD0398' (Dress) utilize Customer Awareness Programs to educate customers on the impacts of shrinkage and promote ethical shopping behaviors.\n
                            Vendor Audits:\tClothing products such as 'PROD0584' (Jeans) and 'PROD0166' (Jacket) benefit from Vendor Audits to ensure supplier compliance and product quality, reducing the risk of receiving counterfeit or substandard goods.\n
                            Employee Training:\tFor products like 'PROD0904' (Jeans) and 'PROD0713' (T-Shirt), Employee Training is essential to equip staff with the skills to identify and handle potential shrinkage effectively, from spotting shoplifting to managing inventory.\n
                            """)

                elif drop_down == "TOYS":
                    time.sleep(1)
                    st.markdown("""
                            Vendor Audits:\tFor toys like 'PROD0056' (Action Figure) and 'PROD0184' (Toy Car), Vendor Audits are essential to ensure compliance with manufacturing and quality standards, helping to prevent losses from defective or counterfeit items.\n
                            Enhanced Security:\tProducts such as 'PROD0486' (Board Game) and 'PROD0057' (Action Figure) implement Enhanced Security measures, including RFID tagging and surveillance systems, to protect against theft and damage in stores.\n
                            Customer Awareness Programs:\tItems like 'PROD0824' (Action Figure) and 'PROD0550' (Doll) utilize Customer Awareness Programs to engage customers in understanding the value of products and reducing mishandling or theft.\n
                            Inventory Management Systems:\tFor toys such as 'PROD0671' (Toy Car) and 'PROD0679' (Board Game), Inventory Management Systems are crucial for tracking stock accurately and managing restocks effectively to minimize losses.\n
                            Employee Training:\tProducts like 'PROD0808' (Toy Car) and 'PROD0512' (Doll) benefit from Employee Training to equip staff with the skills to detect and handle potential losses, improving overall security and customer service.\n
                            """)

                elif drop_down == "ELECTRONICS":
                    time.sleep(1)
                    st.markdown("""
                            Vendor Audits:\tFor electronics like 'PROD0413' (Smartphone) and 'PROD0008' (Laptop), Vendor Audits are critical to ensure quality control and supply chain integrity, helping to prevent losses from counterfeit or defective products.\n
                            Enhanced Security:\tProducts such as 'PROD0585' (Smartphone) and 'PROD0400' (Laptop) implement Enhanced Security measures, including advanced surveillance systems and access controls, to protect high-value electronics.\n
                            Customer Awareness Programs:\tItems like 'PROD0715' (Tablet) and 'PROD0149' (Headphones) utilize Customer Awareness Programs to educate consumers on the importance of handling products carefully to reduce accidental damage and theft.\n
                            Inventory Management Systems:\tFor electronics such as 'PROD0874' (Smartphone) and 'PROD0782' (Laptop), Inventory Management Systems are crucial for tracking stock levels and movements accurately to prevent losses.\n
                            Employee Training:\tProducts like 'PROD0330' (Laptop) and 'PROD0856' (Smartwatch) benefit from Employee Training to equip staff with the skills to detect and prevent potential shrinkage effectively, ensuring products are handled and secured properly.\n
                            """)

            elif selected_query == "How do high shrinkage rates and inventory management practices affect sales volumes for products in rural store locations?":
                if drop_down == "FOOD":
                    time.sleep(1)
                    st.markdown("""
                            Inventory Adjustments:\tHigh shrinkage rates for products like 'PROD0024' (Butter) and 'PROD0687' (Eggs) indicate potential inventory accuracy issues or theft, which suggests the need for tighter inventory control measures to ensure product availability and maintain sales volumes.\n
                            Lead Time Reduction:\tExtended lead times for 'PROD0323' (Milk) and 'PROD0836' (Milk) could be impacting their sales, suggesting that reducing lead time could help in maintaining stock levels more effectively and responding quicker to consumer demand in rural areas.\n
                            Replenishment Strategy:\tImplementing more dynamic replenishment strategies for items such as 'PROD0269' (Bread) and 'PROD0300' (Eggs) could help manage their inventory better to avoid overstocking while ensuring that popular items are always available, thereby maximizing sales.\n
                            Backorder Management:\tEffective backorder management for high-shrinkage items like 'PROD0567' (Butter) could minimize the sales impact of out-of-stock situations by ensuring timely replenishment, thus maintaining customer trust and loyalty.\n
                            Analytical Review:\tContinuous analysis of sales data and inventory levels for 'PROD0453' (Eggs) and 'PROD0596' (Butter) is critical. Adjusting procurement and sales strategies based on these insights can help optimize stock levels and reduce shrinkage-related losses, enhancing overall sales performance in rural locations.\n
                            """)

                elif drop_down == "FURNITURE":
                    time.sleep(1)
                    st.markdown("""
                                Inventory Adjustments:\tFor high shrinkage items like 'PROD0168' (Wardrobe) with an inventory level of 948.31, there appears to be a need to realign inventory to actual sales demand to prevent overstocking and associated losses.\n
                                Lead Time Reduction:\tProducts such as 'PROD0429' (Bed) and 'PROD0378' (Table) show a lead time of over 17 days, indicating potential delays in restocking. Reducing these lead times could enhance sales by ensuring popular items are readily available to meet consumer demand.\n
                                Replenishment Strategy:\tItems like 'PROD0741' (Chair) and 'PROD0986' (Chair) could benefit from a more dynamic replenishment strategy, particularly due to their high shrinkage rates and the need to balance inventory levels closely with sales rates to avoid excess or shortages.\n
                                Backorder Management:\tEfficient management of backorders, especially for items such as 'PROD0153' (Chair) and 'PROD0343' (Table) with significant lead times, is crucial to maintain customer satisfaction and support consistent sales figures in rural locations.\n
                                Analytical Review:\tContinuous review and analysis of sales data and inventory metrics for 'PROD0801' (Sofa) and 'PROD0881' (Bed), which exhibit moderate shrinkage but high sales, can help optimize inventory levels and reduce the impact of shrinkage on profitability.\n
                            """)

                elif drop_down == "CLOTHING":
                    time.sleep(1)
                    st.markdown("""
                                Inventory Adjustments:\tHigh shrinkage rates in products like 'PROD0188' (Jacket) and 'PROD0072' (Jeans), which also have high sales, suggest a need for accurate inventory adjustments to mitigate losses and ensure that demand is met without overstocking.\n
                                Lead Time Reduction:\tExtended replenishment lead times for items such as 'PROD0412' (T-Shirt) and 'PROD0302' (Dress) can delay restocking and impact sales. Reducing these times could enhance availability and responsiveness, directly influencing sales positively.\n
                                Replenishment Strategy:\tAdopting a dynamic replenishment strategy for fast-moving items like 'PROD0369' (Shirt) and 'PROD0879' (Jeans) with relatively low inventory levels can prevent stockouts during peak demand periods, ensuring continuous sales flow.\n
                                Backorder Management:\tEfficient backorder management for items with high sales and high shrinkage rates, such as 'PROD0095' (T-Shirt) and 'PROD0086' (Jacket), is essential to maintain customer satisfaction and avoid lost sales opportunities due to unavailable stock.\n
                                Analytical Review:\tContinuous monitoring and analysis of sales and inventory data for 'PROD0811' (Dress) and 'PROD0742' (Jeans) are crucial. Insights derived from this data can help in adjusting purchasing plans and marketing strategies to optimize stock levels and reduce shrinkage.\n
                            """)

                elif drop_down == "TOYS":
                    time.sleep(1)
                    st.markdown("""
                                Inventory Adjustments:\tHigh shrinkage rates in products like 'PROD0288' (Board Game) and 'PROD0244' (Puzzle) highlight the need for precise inventory adjustments to manage stock levels more efficiently and minimize losses due to shrinkage.\n
                                Lead Time Reduction:\tExtended replenishment lead times for items such as 'PROD0824' (Action Figure) and 'PROD0731' (Board Game) can impact their availability and sales. Reducing these lead times could help in maintaining adequate stock levels to meet consumer demand.\n
                                Replenishment Strategy:\tAdopting a dynamic replenishment strategy for fast-moving items like 'PROD0056' (Action Figure) and 'PROD0913' (Board Game) with high shrinkage rates can help balance inventory levels closely with sales rates, avoiding overstocking or stockouts.\n
                                Backorder Management:\tEfficient management of backorders for high-demand toys such as 'PROD0942' (Puzzle) and 'PROD0808' (Toy Car) is essential to maintain customer satisfaction and avoid lost sales opportunities due to unavailable stock.\n
                                Analytical Review:\tContinuous monitoring and analysis of sales and inventory data for 'PROD0057' (Action Figure) and 'PROD0069' (Puzzle) are crucial. Adjusting purchasing plans and marketing strategies based on these insights can help optimize stock levels and reduce shrinkage.\n
                                """)

                elif drop_down == "ELECTRONICS":
                    time.sleep(1)
                    st.markdown("""
                            Inventory Adjustments:\tHigh shrinkage rates in products like 'PROD0331' (Tablet) and 'PROD0149' (Headphones) with substantial inventory levels suggest a need for accurate inventory adjustments to prevent overstocking and reduce losses from shrinkage.\n
                            Lead Time Reduction:\tExtended replenishment lead times for items such as 'PROD0146' (Headphones) and 'PROD0782' (Laptop) can impact their availability and sales negatively. Reducing these lead times could enhance availability and responsiveness, positively influencing sales.\n
                            Replenishment Strategy:\tAdopting a dynamic replenishment strategy for high-turnover items like 'PROD0837' (Smartphone) and 'PROD0895' (Tablet) with high shrinkage rates can help balance inventory levels closely with sales rates, avoiding overstocking or stockouts.\n
                            Backorder Management:\tEfficient management of backorders for high-demand electronics such as 'PROD0624' (Smartphone) and 'PROD0845' (Smartwatch) is crucial to maintain customer satisfaction and avoid lost sales opportunities due to unavailable stock.\n
                            Analytical Review:\tContinuous monitoring and analysis of sales and inventory data for 'PROD0457' (Headphones) and 'PROD0366' (Smartphone) are essential. Adjusting purchasing plans and marketing strategies based on these insights can help optimize stock levels and reduce shrinkage.\n
                            """)

    with col[1]:
        if selected_query and drop_down:
            if selected_query == "What are the detailed loss prevention measures for products in departments with a shrinkage rate higher than a specific threshold?":
                if drop_down == "FOOD":
                    l_figures = create_figures_loss_prevention2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "FURNITURE":
                    l_figures = create_figures_loss_prevention2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "CLOTHING":
                    l_figures = create_figures_loss_prevention2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "TOYS":
                    l_figures = create_figures_loss_prevention2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "ELECTRONICS":
                    l_figures = create_figures_loss_prevention2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

            elif selected_query == "How do high shrinkage rates and inventory management practices affect sales volumes for products in rural store locations?":
                if drop_down == "FOOD":
                    l_figures = create_figures_loss_prevention2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "FURNITURE":
                    l_figures = create_figures_loss_prevention2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "CLOTHING":
                    l_figures = create_figures_loss_prevention2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "TOYS":
                    l_figures = create_figures_loss_prevention2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "ELECTRONICS":
                    l_figures = create_figures_loss_prevention2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

def marketing_management_app(persona, options):
    queries = get_queries_from_db(persona)

    st.markdown("""
            <style>
            div.stButton {
                display: flex;
                justify-content: flex-end; /* Align button to the right */
                margin-top: 10px;
            }

            /* Custom CSS for the dropdowns to align right and be smaller */
            div.streamlit-expander {
                width: 100%; /* Make sure it fills the container */
            }

            div.streamlit-expander > div {
                width: 30%; /* Set the width of the selectbox */
                margin-left: auto; /* Push it to the right */
            }

            /* Smaller font size for selectbox options */
            .stSelectbox div {
                font-size: 12px; /* Smaller font size */
            }

            </style>
            """, unsafe_allow_html=True)
    col1, col2 = st.columns([4, 1])
    with col2:
        drop_down = st.selectbox("", options)
    unpin_button_pressed = st.button("DELETE", key='unpin_button')
    selected_query = st.selectbox("Select a query", queries if queries else ["Select a query"])

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    col = st.columns((1, 1), gap='medium')
    conn = connect_to_db(DB_NAME)

    with col[0]:
        if unpin_button_pressed:
            if selected_query != "Select a query":
                queries.pop(selected_query, None)
                st.success(f"Query '{selected_query}' has been removed.")
            else:
                st.warning("Select a query to unpin.")

        if drop_down and selected_query and selected_query != "Select a query" and not unpin_button_pressed and drop_down != "SELECT DEPARTMENT":
            # result = execute_query(queries[selected_query], conn)
            if selected_query == "How effective are different marketing strategies across product categories in terms of sales volume, inventory management, and the occurrence of stockouts during promotional campaigns?":
                if drop_down == "WATER TOWER PLACE":
                    time.sleep(1)
                    st.markdown('The data table returned provides information on the marketing campaigns and sales performance for different product categories in WATER TOWER PLACE. It includes the store ID, category, marketing strategy, number of marketing campaigns, total sales during the campaigns, average inventory level during the campaigns, minimum replenishment lead time, and maximum stockouts. The table is sorted based on the total sales during the campaigns and the average inventory level during the campaigns in descending order.')

                elif drop_down == "RIVERFRONT PLAZA":
                    time.sleep(1)
                    st.markdown('The data table returned provides information on the marketing campaigns and sales performance for different categories of products in RIVERFRONT PLAZA. The table includes the Store ID, category of the product, marketing strategy used, the number of marketing campaigns conducted, total sales during the campaigns, average inventory level during the campaigns, minimum replenishment lead time, and maximum stockouts.\n\nFor RIVERFRONT PLAZA, the table shows that the most successful marketing strategy in terms of total sales during campaigns is the "Social Media Campaign" for the "Toys" category, with 772 units sold. The marketing strategy with the highest average inventory level during campaigns is "Email Marketing" for the "Clothing" category, with an average inventory level of 592.1 units. The minimum replenishment lead time across all categories and marketing strategies is 1.23 days, and the maximum number of stockouts is 9 incidents.\n\nOverall, the table provides insights into the performance of different marketing strategies and their impact on sales and inventory levels for different product categories in RIVERFRONT PLAZA.')

                elif drop_down == "WESTFIELD WHEATON":
                    time.sleep(1)
                    st.markdown("The data table shows the results of a query that was performed to answer a business question. The query involved joining multiple tables from an enterprise database schema. The table includes information about the store ID, category of products, marketing strategy, number of marketing campaigns, total sales during the campaigns, average inventory level during the campaigns, minimum replenishment lead time, and maximum stockouts. The data in the table is specific to Store ID 'WESTFIELD WHEATON'. The rows in the table are sorted based on the total sales during the campaigns in descending order, followed by the average inventory level during the campaigns.")

            elif selected_query == "How effective are different types of promotional activities at various urban store locations in terms of sales uplift, customer engagement, and inventory turnover?":
                if drop_down == "WATER TOWER PLACE":
                    time.sleep(1)
                    st.markdown('The data table returned provides information about Store ID, Store Location Type, Promotional Activity Type, Number of Promotions, Average Sales Uplift, Total Sales, Average Inventory Turnover, and Average Customer Engagement for a specific store (WATER TOWER PLACE) in an urban location. The table is sorted by the Average Sales Uplift and Average Inventory Turnover in descending order. It shows that for each promotional activity type (Discount, Clearance Sale, Buy One Get One Free, Flash Sale, and Seasonal Sale), there was one promotion conducted. The Average Sales Uplift for all the promotions is 6298.19, indicating the average increase in sales due to the promotional activities. The Total Sales for each promotion type varies, with the highest being 3745. The Average Inventory Turnover is also provided, indicating the rate at which inventory is sold and replenished. The Average Customer Engagement metric measures the average dwell time and interactions of customers in the store.')

                elif drop_down == "RIVERFRONT PLAZA":
                    time.sleep(1)
                    st.markdown('The data table returned provides information about the promotional activities, sales, inventory turnover, and customer engagement metrics for a specific store (RIVERFRONT PLAZA) located in an urban area. The table includes the Store ID, Store Location Type, Promotional Activity Type, Number of Promotions, Average Sales Uplift, Total Sales, Average Inventory Turnover, and Average Customer Engagement metrics. Each row represents a different promotional activity type, such as Discount, Buy One Get One Free, Flash Sale, Clearance Sale, and Seasonal Sale. The table shows that for each promotional activity, there was only one promotion conducted. The Average Sales Uplift represents the average increase in sales due to visual merchandising efforts. The Total Sales column shows the total quantity of products sold. The Average Inventory Turnover indicates the rate at which inventory is sold and replenished. Lastly, the Average Customer Engagement metric represents the average time customers spent in the store and the number of interactions they had. The table is sorted based on the highest Average Sales Uplift and Average Inventory Turnover.')

                elif drop_down == "WESTFIELD WHEATON":
                    time.sleep(1)
                    st.markdown('The data table that was returned provides information about the promotional activities and sales performance of a specific urban store (Store ID: WESTFIELD WHEATON). The table includes the following columns:\n\n1. Store_ID: The unique identifier of the store (WESTFIELD WHEATON).\n2. Store_Location_Type: Indicates that the store is located in an urban area.\n3. Promotional_Activity_Type: Specifies the type of promotional activity conducted in the store, such as discounts, clearance sales, seasonal sales, buy one get one free offers, and flash sales.\n4. Number_of_Promotions: Represents the count of distinct promotional activity dates for each promotional activity type.\n5. Avg_Sales_Uplift: Indicates the average increase in sales achieved through visual merchandising techniques.\n6. Total_Sales: Represents the total quantity of products sold in the store.\n7. Avg_Inventory_Turnover: Represents the average rate at which inventory is sold and replenished in the store.\n8. Avg_Customer_Engagement: Indicates the average level of customer engagement, measured by metrics such as dwell time and interactions.\n\nThe table is sorted in descending order based on the average sales uplift and average inventory turnover. This information can help analyze the effectiveness of different promotional activities in driving sales and engaging customers in the urban store.')



    with col[1]:
        if selected_query and drop_down:
            if selected_query == "How effective are different marketing strategies across product categories in terms of sales volume, inventory management, and the occurrence of stockouts during promotional campaigns?":
                if drop_down == "WATER TOWER PLACE":
                    l_figures = create_figures_marketing2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "RIVERFRONT PLAZA":
                    l_figures = create_figures_marketing2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "WESTFIELD WHEATON":
                    l_figures = create_figures_marketing2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)


            elif selected_query == "How effective are different types of promotional activities at various urban store locations in terms of sales uplift, customer engagement, and inventory turnover?":
                if drop_down == "WATER TOWER PLACE":
                    l_figures = create_figures_marketing2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "RIVERFRONT PLAZA":
                    l_figures = create_figures_marketing2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)

                elif drop_down == "WESTFIELD WHEATON":
                    l_figures = create_figures_marketing2(selected_query, drop_down)
                    dynamic_figure_populate(l_figures)


def create_figures_loss_prevention2(query, drop):
    conn = connect_to_db(DB_NAME)
    if query and drop:
        if query == "How do high shrinkage rates and inventory management practices affect sales volumes for products in rural store locations?":
            if drop == "FOOD":
                data = pd.read_sql(
                    """
                    SELECT p.Product_ID, p.Description, ss.Store_Location_Type, SUM(t.Quantity) AS Total_Sales, slp.Shrinkage_Rate, slp.Loss_Prevention_Measures, iv.Average_Monthly_Inventory_Level, iv.Replenishment_Lead_Time FROM products AS p JOIN transactions AS t ON p.Product_ID = t.Product_ID JOIN shrinkageAndLossPrevention AS slp ON p.Product_ID = slp.Product_ID JOIN inventoryMetrics AS iv ON p.Product_ID = iv.Product_ID JOIN shrinkageStores AS ss ON t.Store_ID = ss.Store_ID WHERE slp.Shrinkage_Rate > 4 AND slp.Department ='Food' AND ss.Store_Location_Type IN ('rural') GROUP BY p.Product_ID, ss.Store_Location_Type ORDER BY slp.Shrinkage_Rate DESC, iv.Replenishment_Lead_Time;
                    """, conn
                )
                fig_bar1 = px.bar(data,
                                  x='Product_ID',
                                  y='Total_Sales',
                                  color='Shrinkage_Rate',
                                  hover_data=['Description', 'Loss_Prevention_Measures'],
                                  title="Total Sales by Product by Shrinkage Rate")

                fig_bar1.update_layout(xaxis_tickangle=-45)

                fig_bar2 = px.bar(data,
                                  x='Product_ID',  # Categories on x-axis
                                  y='Replenishment_Lead_Time',  # Values on y-axis
                                  title="Replenishment Lead Time by Product",
                                  labels={'Product_ID': 'Product ID',
                                          'Replenishment_Lead_Time': 'Replenishment Lead Time (days)'},
                                  color='Replenishment_Lead_Time',  # Optional: color by lead time
                                  text='Replenishment_Lead_Time')  # Display values on bars

                fig_bar2.update_layout(xaxis_tickangle=-45, height=600)

                figures = [fig_bar1, fig_bar2]
                return figures

            elif drop == "CLOTHING":
                data = pd.read_sql(
                    """
                    SELECT p.Product_ID, p.Description, ss.Store_Location_Type, SUM(t.Quantity) AS Total_Sales, slp.Shrinkage_Rate, slp.Loss_Prevention_Measures, iv.Average_Monthly_Inventory_Level, iv.Replenishment_Lead_Time FROM products AS p JOIN transactions AS t ON p.Product_ID = t.Product_ID JOIN shrinkageAndLossPrevention AS slp ON p.Product_ID = slp.Product_ID JOIN inventoryMetrics AS iv ON p.Product_ID = iv.Product_ID JOIN shrinkageStores AS ss ON t.Store_ID = ss.Store_ID WHERE slp.Shrinkage_Rate > 4 AND slp.Department ='Clothing' AND ss.Store_Location_Type IN ('rural') GROUP BY p.Product_ID, ss.Store_Location_Type ORDER BY slp.Shrinkage_Rate DESC, iv.Replenishment_Lead_Time;
                    """, conn
                )
                fig_bar1 = px.bar(data,
                                  x='Product_ID',
                                  y='Total_Sales',
                                  color='Shrinkage_Rate',
                                  hover_data=['Description', 'Loss_Prevention_Measures'],
                                  title="Total Sales by Product by Shrinkage Rate")

                fig_bar1.update_layout(xaxis_tickangle=-45)

                fig_bar2 = px.bar(data,
                                  x='Product_ID',  # Categories on x-axis
                                  y='Replenishment_Lead_Time',  # Values on y-axis
                                  title="Replenishment Lead Time by Product",
                                  labels={'Product_ID': 'Product ID',
                                          'Replenishment_Lead_Time': 'Replenishment Lead Time (days)'},
                                  color='Replenishment_Lead_Time',  # Optional: color by lead time
                                  text='Replenishment_Lead_Time')  # Display values on bars

                fig_bar2.update_layout(xaxis_tickangle=-45, height=600)

                figures = [fig_bar1, fig_bar2]
                return figures

            if drop == "TOYS":
                data = pd.read_sql(
                    """
                    SELECT p.Product_ID, p.Description, ss.Store_Location_Type, SUM(t.Quantity) AS Total_Sales, slp.Shrinkage_Rate, slp.Loss_Prevention_Measures, iv.Average_Monthly_Inventory_Level, iv.Replenishment_Lead_Time FROM products AS p JOIN transactions AS t ON p.Product_ID = t.Product_ID JOIN shrinkageAndLossPrevention AS slp ON p.Product_ID = slp.Product_ID JOIN inventoryMetrics AS iv ON p.Product_ID = iv.Product_ID JOIN shrinkageStores AS ss ON t.Store_ID = ss.Store_ID WHERE slp.Shrinkage_Rate > 4 AND slp.Department ='Toys' AND ss.Store_Location_Type IN ('rural') GROUP BY p.Product_ID, ss.Store_Location_Type ORDER BY slp.Shrinkage_Rate DESC, iv.Replenishment_Lead_Time;
                    """, conn
                )
                fig_bar1 = px.bar(data,
                                  x='Product_ID',
                                  y='Total_Sales',
                                  color='Shrinkage_Rate',
                                  hover_data=['Description', 'Loss_Prevention_Measures'],
                                  title="Total Sales by Product in top 10 Rural Stores (by Shrinkage Rate)")

                fig_bar1.update_layout(xaxis_tickangle=-45)

                fig_bar2 = px.bar(data,
                                  x='Product_ID',  # Categories on x-axis
                                  y='Replenishment_Lead_Time',  # Values on y-axis
                                  title="Replenishment Lead Time by Product",
                                  labels={'Product_ID': 'Product ID',
                                          'Replenishment_Lead_Time': 'Replenishment Lead Time (days)'},
                                  color='Replenishment_Lead_Time',  # Optional: color by lead time
                                  text='Replenishment_Lead_Time')  # Display values on bars

                fig_bar2.update_layout(xaxis_tickangle=-45, height=600)

                figures = [fig_bar1, fig_bar2]
                return figures

            elif drop == "FURNITURE":
                data = pd.read_sql(
                    """
                    SELECT p.Product_ID, p.Description, ss.Store_Location_Type, SUM(t.Quantity) AS Total_Sales, slp.Shrinkage_Rate, slp.Loss_Prevention_Measures, iv.Average_Monthly_Inventory_Level, iv.Replenishment_Lead_Time FROM products AS p JOIN transactions AS t ON p.Product_ID = t.Product_ID JOIN shrinkageAndLossPrevention AS slp ON p.Product_ID = slp.Product_ID JOIN inventoryMetrics AS iv ON p.Product_ID = iv.Product_ID JOIN shrinkageStores AS ss ON t.Store_ID = ss.Store_ID WHERE slp.Shrinkage_Rate > 4 AND slp.Department ='Furniture' AND ss.Store_Location_Type IN ('rural') GROUP BY p.Product_ID, ss.Store_Location_Type ORDER BY slp.Shrinkage_Rate DESC, iv.Replenishment_Lead_Time;
                    """, conn
                )
                fig_bar1 = px.bar(data,
                                  x='Product_ID',
                                  y='Total_Sales',
                                  color='Shrinkage_Rate',
                                  hover_data=['Description', 'Loss_Prevention_Measures'],
                                  title="Total Sales by Product in top 10 Rural Stores (by Shrinkage Rate)")

                fig_bar1.update_layout(xaxis_tickangle=-45)

                fig_bar2 = px.bar(data,
                                  x='Product_ID',  # Categories on x-axis
                                  y='Replenishment_Lead_Time',  # Values on y-axis
                                  title="Replenishment Lead Time by Product",
                                  labels={'Product_ID': 'Product ID',
                                          'Replenishment_Lead_Time': 'Replenishment Lead Time (days)'},
                                  color='Replenishment_Lead_Time',  # Optional: color by lead time
                                  text='Replenishment_Lead_Time')  # Display values on bars

                fig_bar2.update_layout(xaxis_tickangle=-45, height=600)

                figures = [fig_bar1, fig_bar2]
                return figures

            if drop == "ELECTRONICS":
                data = pd.read_sql(
                    """
                    SELECT p.Product_ID, p.Description, ss.Store_Location_Type, SUM(t.Quantity) AS Total_Sales, slp.Shrinkage_Rate, slp.Loss_Prevention_Measures, iv.Average_Monthly_Inventory_Level, iv.Replenishment_Lead_Time FROM products AS p JOIN transactions AS t ON p.Product_ID = t.Product_ID JOIN shrinkageAndLossPrevention AS slp ON p.Product_ID = slp.Product_ID JOIN inventoryMetrics AS iv ON p.Product_ID = iv.Product_ID JOIN shrinkageStores AS ss ON t.Store_ID = ss.Store_ID WHERE slp.Shrinkage_Rate > 4 AND slp.Department ='Electronics' AND ss.Store_Location_Type IN ('rural') GROUP BY p.Product_ID, ss.Store_Location_Type ORDER BY slp.Shrinkage_Rate DESC, iv.Replenishment_Lead_Time;
                    """, conn
                )
                fig_bar1 = px.bar(data,
                                  x='Product_ID',
                                  y='Total_Sales',
                                  color='Shrinkage_Rate',
                                  hover_data=['Description', 'Loss_Prevention_Measures'],
                                  title="Total Sales by Product in top 10 Rural Stores (by Shrinkage Rate)")

                fig_bar1.update_layout(xaxis_tickangle=-45)

                fig_bar2 = px.bar(data,
                                  x='Product_ID',  # Categories on x-axis
                                  y='Replenishment_Lead_Time',  # Values on y-axis
                                  title="Replenishment Lead Time by Product",
                                  labels={'Product_ID': 'Product ID',
                                          'Replenishment_Lead_Time': 'Replenishment Lead Time (days)'},
                                  color='Replenishment_Lead_Time',  # Optional: color by lead time
                                  text='Replenishment_Lead_Time')  # Display values on bars

                fig_bar2.update_layout(xaxis_tickangle=-45, height=600)

                figures = [fig_bar1, fig_bar2]
                return figures

        if query == "What are the detailed loss prevention measures for products in departments with a shrinkage rate higher than a specific threshold?":
            if drop == "FOOD":
                df = pd.read_sql_query("""SELECT slp.Product_ID,
                    p.Description,
                    slp.Department,
                    slp.Shrinkage_Rate,
                    slp.Shrinkage_Value,
                    slp.Loss_Prevention_Measures
                FROM shrinkageAndLossPrevention AS slp
                JOIN products AS p ON slp.Product_ID = p.Product_ID
                WHERE slp.Shrinkage_Rate > 4 and slp.Department='Food'
                ORDER BY slp.Shrinkage_Rate DESC;""", conn)

                fig_tree = px.treemap(df,
                                 path=['Department', 'Description'],
                                 values='Shrinkage_Value',
                                 color='Shrinkage_Rate',
                                 hover_data=['Loss_Prevention_Measures'],
                                 title='Shrinkage Rate by Department',
                                 color_continuous_scale='Viridis')

                fig_tree.update_layout(height=600)

                fig_sun = px.sunburst(df,
                                  path=['Department', 'Description'],
                                  values='Shrinkage_Value',
                                  color='Shrinkage_Rate',
                                  hover_data=['Loss_Prevention_Measures'],
                                  title='Shrinkage Rate by Department',
                                  color_continuous_scale='Reds')

                fig_sun.update_layout(height=600)
                figures = [fig_tree, fig_sun]
                return figures

            elif drop == "CLOTHING":
                df = pd.read_sql_query("""SELECT slp.Product_ID,
                    p.Description,
                    slp.Department,
                    slp.Shrinkage_Rate,
                    slp.Shrinkage_Value,
                    slp.Loss_Prevention_Measures
                FROM shrinkageAndLossPrevention AS slp
                JOIN products AS p ON slp.Product_ID = p.Product_ID
                WHERE slp.Shrinkage_Rate > 4 and slp.Department='Clothing'
                ORDER BY slp.Shrinkage_Rate DESC;""", conn)

                fig_tree = px.treemap(df,
                                 path=['Department', 'Description'],
                                 values='Shrinkage_Value',
                                 color='Shrinkage_Rate',
                                 hover_data=['Loss_Prevention_Measures'],
                                 title='Shrinkage Rate by Department',
                                 color_continuous_scale='Viridis')

                fig_tree.update_layout(height=600)

                fig_sun = px.sunburst(df,
                                  path=['Department', 'Description'],
                                  values='Shrinkage_Value',
                                  color='Shrinkage_Rate',
                                  hover_data=['Loss_Prevention_Measures'],
                                  title='Shrinkage Rate by Department',
                                  color_continuous_scale='Reds')

                fig_sun.update_layout(height=600)
                figures = [fig_tree, fig_sun]
                return figures

            elif drop == "TOYS":
                df = pd.read_sql_query("""SELECT slp.Product_ID,
                    p.Description,
                    slp.Department,
                    slp.Shrinkage_Rate,
                    slp.Shrinkage_Value,
                    slp.Loss_Prevention_Measures
                FROM shrinkageAndLossPrevention AS slp
                JOIN products AS p ON slp.Product_ID = p.Product_ID
                WHERE slp.Shrinkage_Rate > 4 and slp.Department='Toys'
                ORDER BY slp.Shrinkage_Rate DESC;""", conn)

                fig_tree = px.treemap(df,
                                 path=['Department', 'Description'],
                                 values='Shrinkage_Value',
                                 color='Shrinkage_Rate',
                                 hover_data=['Loss_Prevention_Measures'],
                                 title='Shrinkage Rate by Department',
                                 color_continuous_scale='Viridis')

                fig_tree.update_layout(height=600)

                fig_sun = px.sunburst(df,
                                  path=['Department', 'Description'],
                                  values='Shrinkage_Value',
                                  color='Shrinkage_Rate',
                                  hover_data=['Loss_Prevention_Measures'],
                                  title='Shrinkage Rate by Department',
                                  color_continuous_scale='Reds')

                fig_sun.update_layout(height=600)
                figures = [fig_tree, fig_sun]
                return figures

            elif drop == "FURNITURE":
                df = pd.read_sql_query("""SELECT slp.Product_ID,
                    p.Description,
                    slp.Department,
                    slp.Shrinkage_Rate,
                    slp.Shrinkage_Value,
                    slp.Loss_Prevention_Measures
                FROM shrinkageAndLossPrevention AS slp
                JOIN products AS p ON slp.Product_ID = p.Product_ID
                WHERE slp.Shrinkage_Rate > 4 and slp.Department='Furniture'
                ORDER BY slp.Shrinkage_Rate DESC;""", conn)

                fig_tree = px.treemap(df,
                                 path=['Department', 'Description'],
                                 values='Shrinkage_Value',
                                 color='Shrinkage_Rate',
                                 hover_data=['Loss_Prevention_Measures'],
                                 title='Shrinkage Rate by Department',
                                 color_continuous_scale='Viridis')

                fig_tree.update_layout(height=600)

                fig_sun = px.sunburst(df,
                                  path=['Department', 'Description'],
                                  values='Shrinkage_Value',
                                  color='Shrinkage_Rate',
                                  hover_data=['Loss_Prevention_Measures'],
                                  title='Shrinkage Rate by Department',
                                  color_continuous_scale='Reds')

                fig_sun.update_layout(height=600)
                figures = [fig_tree, fig_sun]
                return figures

            elif drop == "ELECTRONICS":
                df = pd.read_sql_query("""SELECT slp.Product_ID,
                    p.Description,
                    slp.Department,
                    slp.Shrinkage_Rate,
                    slp.Shrinkage_Value,
                    slp.Loss_Prevention_Measures
                FROM shrinkageAndLossPrevention AS slp
                JOIN products AS p ON slp.Product_ID = p.Product_ID
                WHERE slp.Shrinkage_Rate > 4 and slp.Department='Electronics'
                ORDER BY slp.Shrinkage_Rate DESC;""", conn)

                fig_tree = px.treemap(df,
                                 path=['Department', 'Description'],
                                 values='Shrinkage_Value',
                                 color='Shrinkage_Rate',
                                 hover_data=['Loss_Prevention_Measures'],
                                 title='Shrinkage Rate by Department',
                                 color_continuous_scale='Viridis')

                fig_tree.update_layout(height=600)

                fig_sun = px.sunburst(df,
                                  path=['Department', 'Description'],
                                  values='Shrinkage_Value',
                                  color='Shrinkage_Rate',
                                  hover_data=['Loss_Prevention_Measures'],
                                  title='Shrinkage Rate by Department',
                                  color_continuous_scale='Reds')

                fig_sun.update_layout(height=600)
                figures = [fig_tree, fig_sun]
                return figures

def create_figuresIM2(query, drop):
    conn = connect_to_db(DB_NAME)
    if query and drop:
        if query == "How do we optimize inventory levels and replenishment for high-stockout products to match sales and reduce stockouts?":
            if drop == "INVENTORY FOR TOYS":
                result = execute_query(
                    "SELECT p.Product_ID, p.Description, SUM(t.Quantity) AS Total_Sales, iv.Average_Monthly_Inventory_Level, iv.Replenishment_Lead_Time, iv.Backorder_Rate, iv.StockOut_Incidents FROM products AS p JOIN transactions AS t ON p.Product_ID = t.Product_ID JOIN inventoryMetrics AS iv ON p.Product_ID = iv.Product_ID  WHERE iv.StockOut_Incidents > 7 AND p.Category = 'Toys' GROUP BY p.Product_ID ORDER BY iv.Replenishment_Lead_Time, iv.StockOut_Incidents;",
                    conn)

                bar_fig_sales = px.bar(
                    result,
                    x='Total_Sales',
                    y='Description',
                    title='Sum of Total Sales by Description',
                    orientation='h'
                )
                bar_fig_sales.update_layout(
                    xaxis_title='Total_Sales',
                    yaxis_title='Description',
                    yaxis={'categoryorder': 'total ascending'}
                )

                fig_inventory_sales = px.bar(
                    result,
                    x='Description',
                    y='Average_Monthly_Inventory_Level',
                    title='Sum of Average Monthly Inventory Level by Description',
                    barmode='stack',
                    color_discrete_sequence=['#FFFF00']
                )
                fig_inventory_sales.update_layout(
                    xaxis_title='Description',
                    xaxis={'categoryorder': 'total ascending'},
                    yaxis_title='Average Monthly Inventory Level'
                )

                figures = [bar_fig_sales, fig_inventory_sales]
                return figures



            elif drop == "INVENTORY FOR CLOTHING":
                result = execute_query(
                    "SELECT p.Product_ID, p.Description, SUM(t.Quantity) AS Total_Sales, iv.Average_Monthly_Inventory_Level, iv.Replenishment_Lead_Time, iv.Backorder_Rate, iv.StockOut_Incidents FROM products AS p JOIN transactions AS t ON p.Product_ID = t.Product_ID JOIN inventoryMetrics AS iv ON p.Product_ID = iv.Product_ID WHERE iv.StockOut_Incidents > 7 AND p.Category = 'Clothing' GROUP BY p.Product_ID ORDER BY iv.Replenishment_Lead_Time, iv.StockOut_Incidents;",
                    conn)

                bar_fig_sales = px.bar(
                    result,
                    x='Total_Sales',
                    y='Description',
                    title='Sum of Total Sales by Description',
                    orientation='h'
                )
                bar_fig_sales.update_layout(
                    xaxis_title='Total_Sales',
                    yaxis_title='Description',
                    yaxis={'categoryorder': 'total ascending'}
                )

                fig_inventory_sales = px.bar(
                    result,
                    x='Description',
                    y='Average_Monthly_Inventory_Level',
                    title='Sum of Average Monthly Inventory Level by Description',
                    barmode='stack',
                    color_discrete_sequence=['#FFFF00']
                )
                fig_inventory_sales.update_layout(
                    xaxis_title='Description',
                    xaxis={'categoryorder': 'total ascending'},
                    yaxis_title='Average Monthly Inventory Level'
                )

                figures = [bar_fig_sales, fig_inventory_sales]
                return figures

            elif drop == "INVENTORY FOR FURNITURE":
                result = execute_query(
                    "SELECT p.Product_ID, p.Description, SUM(t.Quantity) AS Total_Sales, iv.Average_Monthly_Inventory_Level, iv.Replenishment_Lead_Time, iv.Backorder_Rate, iv.StockOut_Incidents FROM products AS p JOIN transactions AS t ON p.Product_ID = t.Product_ID JOIN inventoryMetrics AS iv ON p.Product_ID = iv.Product_ID WHERE iv.StockOut_Incidents > 7 AND p.Category = 'Furniture' GROUP BY p.Product_ID ORDER BY iv.Replenishment_Lead_Time, iv.StockOut_Incidents;",
                    conn)

                bar_fig_sales = px.bar(
                    result,
                    x='Total_Sales',
                    y='Description',
                    title='Sum of Total Sales by Description',
                    orientation='h'
                )
                bar_fig_sales.update_layout(
                    xaxis_title='Total_Sales',
                    yaxis_title='Description',
                    yaxis={'categoryorder': 'total ascending'}
                )

                fig_inventory_sales = px.bar(
                    result,
                    x='Description',
                    y='Average_Monthly_Inventory_Level',
                    title='Sum of Average Monthly Inventory Level by Description',
                    barmode='stack',
                    color_discrete_sequence=['#FFFF00']
                )
                fig_inventory_sales.update_layout(
                    xaxis_title='Description',
                    xaxis={'categoryorder': 'total ascending'},
                    yaxis_title='Average Monthly Inventory Level'
                )

                figures = [bar_fig_sales, fig_inventory_sales]
                return figures

        elif query == "Which high-sales products have low turnover rates, and what are the lead times and safety stock levels for these products?":
            if drop == "INVENTORY FOR TOYS":
                result = execute_query(
                    "SELECT p.Product_ID, p.Description, COUNT(t.Transaction_ID) AS Number_of_Transactions, SUM(t.Quantity) AS Total_Sales, iv.Inventory_Monthly_Turnover_Rate, iv.Safety_Stock_Levels, iv.Lead_Time, iv.Replenishment_Lead_Time FROM products AS p JOIN transactions AS t ON p.Product_ID = t.Product_ID JOIN inventoryMetrics AS iv ON p.Product_ID = iv.Product_ID WHERE iv.Inventory_Monthly_Turnover_Rate < 15 AND p.Category = 'Toys' GROUP BY p.Product_ID HAVING SUM(t.Quantity) > 750 ORDER BY iv.Inventory_Monthly_Turnover_Rate DESC, iv.Lead_Time;",
                    conn)

                bar_fig = px.bar(
                    result,
                    x='Total_Sales',
                    y='Description',
                    orientation='h',
                    title='Sum of Total_Sales by Description'
                )
                bar_fig.update_layout(
                    xaxis_title='Total Sales',
                    yaxis_title='Product Description',
                    yaxis={'categoryorder': 'total ascending'}
                )

                pie_fig = px.pie(
                    result,
                    values='Safety_Stock_Levels',
                    names='Description',
                    title='Sum of Safety_Stock_Levels by Description'
                )

                scatter_fig = px.scatter(
                    result,
                    x='Description',
                    y='Replenishment_Lead_Time',
                    title='Sum of Replenishment Lead Time by Description',
                    color='Description',
                    hover_name='Description',
                    size='Replenishment_Lead_Time',
                    labels={
                        'Replenishment_Lead_Time': 'Replenishment Lead Time',
                        'Description': 'Product Description'
                    }
                )
                scatter_fig.update_layout(
                    xaxis_title='Product Description',
                    yaxis_title='Replenishment Lead Time',
                    xaxis={'categoryorder': 'total ascending'},
                    plot_bgcolor='black',
                    xaxis_tickangle=-45
                )

                figures = [bar_fig, pie_fig, scatter_fig]
                return figures

            elif drop == "INVENTORY FOR CLOTHING":
                result = execute_query(
                    "SELECT p.Product_ID, p.Description, COUNT(t.Transaction_ID) AS Number_of_Transactions, SUM(t.Quantity) AS Total_Sales, iv.Inventory_Monthly_Turnover_Rate, iv.Safety_Stock_Levels, iv.Lead_Time, iv.Replenishment_Lead_Time FROM products AS p JOIN transactions AS t ON p.Product_ID = t.Product_ID JOIN inventoryMetrics AS iv ON p.Product_ID = iv.Product_ID WHERE iv.Inventory_Monthly_Turnover_Rate < 15 AND p.Category = 'Clothing' GROUP BY p.Product_ID HAVING SUM(t.Quantity) > 750 ORDER BY iv.Inventory_Monthly_Turnover_Rate DESC, iv.Lead_Time;",
                    conn)

                bar_fig = px.bar(
                    result,
                    x='Total_Sales',
                    y='Description',
                    orientation='h',
                    title='Sum of Total_Sales by Description'
                )
                bar_fig.update_layout(
                    xaxis_title='Total Sales',
                    yaxis_title='Product Description',
                    yaxis={'categoryorder': 'total ascending'}
                )

                pie_fig = px.pie(
                    result,
                    values='Safety_Stock_Levels',
                    names='Description',
                    title='Sum of Safety_Stock_Levels by Description'
                )

                scatter_fig = px.scatter(
                    result,
                    x='Description',
                    y='Replenishment_Lead_Time',
                    title='Sum of Replenishment Lead Time by Description',
                    color='Description',
                    hover_name='Description',
                    size='Replenishment_Lead_Time',
                    labels={
                        'Replenishment_Lead_Time': 'Replenishment Lead Time',
                        'Description': 'Product Description'
                    }
                )
                scatter_fig.update_layout(
                    xaxis_title='Product Description',
                    yaxis_title='Replenishment Lead Time',
                    xaxis={'categoryorder': 'total ascending'},
                    plot_bgcolor='black',
                    xaxis_tickangle=-45
                )

                figures = [bar_fig, pie_fig, scatter_fig]
                return figures

            elif drop == "INVENTORY FOR FURNITURE":
                result = execute_query(
                    "SELECT p.Product_ID, p.Description, COUNT(t.Transaction_ID) AS Number_of_Transactions, SUM(t.Quantity) AS Total_Sales, iv.Inventory_Monthly_Turnover_Rate, iv.Safety_Stock_Levels, iv.Lead_Time, iv.Replenishment_Lead_Time FROM products AS p JOIN transactions AS t ON p.Product_ID = t.Product_ID JOIN inventoryMetrics AS iv ON p.Product_ID = iv.Product_ID WHERE iv.Inventory_Monthly_Turnover_Rate < 150 AND p.Category = 'Furniture' GROUP BY p.Product_ID HAVING SUM(t.Quantity) > 750 ORDER BY iv.Inventory_Monthly_Turnover_Rate DESC, iv.Lead_Time;",
                    conn)

                bar_fig = px.bar(
                    result,
                    x='Total_Sales',
                    y='Description',
                    orientation='h',
                    title='Sum of Total_Sales by Description'
                )
                bar_fig.update_layout(
                    xaxis_title='Total Sales',
                    yaxis_title='Product Description',
                    yaxis={'categoryorder': 'total ascending'}
                )

                pie_fig = px.pie(
                    result,
                    values='Safety_Stock_Levels',
                    names='Description',
                    title='Sum of Safety_Stock_Levels by Description'
                )

                scatter_fig = px.scatter(
                    result,
                    x='Description',
                    y='Replenishment_Lead_Time',
                    title='Sum of Replenishment Lead Time by Description',
                    color='Description',
                    hover_name='Description',
                    size='Replenishment_Lead_Time',
                    labels={
                        'Replenishment_Lead_Time': 'Replenishment Lead Time',
                        'Description': 'Product Description'
                    }
                )
                scatter_fig.update_layout(
                    xaxis_title='Product Description',
                    yaxis_title='Replenishment Lead Time',
                    xaxis={'categoryorder': 'total ascending'},
                    plot_bgcolor='black',
                    xaxis_tickangle=-45
                )

                figures = [bar_fig, pie_fig, scatter_fig]
                return figures

        elif query == "For products with frequent stockouts, what are their replenishment accuracy rates, and how do these relate to their sales volumes?":
            if drop == "INVENTORY FOR TOYS":
                result = execute_query(
                    "SELECT  p.Product_ID, p.Description, SUM(t.Quantity) AS Total_Sales, iv.Replenishment_Accuracy, iv.Backorder_Rate, iv.StockOut_Incidents, iv.Fill_Rate FROM products AS p JOIN transactions AS t ON p.Product_ID = t.Product_ID JOIN inventoryMetrics AS iv ON p.Product_ID = iv.Product_ID WHERE iv.StockOut_Incidents > 4 AND p.Category = 'Toys' GROUP BY p.Product_ID ORDER BY iv.Replenishment_Accuracy DESC, Total_Sales DESC;",
                    conn)
                bar_fig2 = px.bar(
                    result,
                    x='Description',
                    y='Replenishment_Accuracy',
                    title='Sum of Replenishment Accuracy by Description',
                    labels={'Replenishment_Accuracy': 'Sum of Replenishment Accuracy'}
                )

                treemap_fig = px.treemap(
                    result,
                    path=['Description'],
                    values='StockOut_Incidents',
                    title='Sum of StockOut Incidents by Description',
                    color='StockOut_Incidents',
                    color_continuous_scale='Viridis'
                )

                heatmap_fig = px.density_heatmap(
                    result,
                    x='Description',
                    y='Fill_Rate',
                    marginal_x='rug',
                    marginal_y='histogram',
                    title='Density of Fill Rate by Description'
                )

                figures = [bar_fig2, treemap_fig, heatmap_fig]
                return figures

            elif drop == "INVENTORY FOR CLOTHING":
                result = execute_query(
                    "SELECT  p.Product_ID, p.Description, SUM(t.Quantity) AS Total_Sales, iv.Replenishment_Accuracy, iv.Backorder_Rate, iv.StockOut_Incidents, iv.Fill_Rate FROM products AS p JOIN transactions AS t ON p.Product_ID = t.Product_ID JOIN inventoryMetrics AS iv ON p.Product_ID = iv.Product_ID WHERE iv.StockOut_Incidents > 4 AND p.Category = 'Clothing' GROUP BY p.Product_ID ORDER BY iv.Replenishment_Accuracy DESC, Total_Sales DESC;",
                    conn)
                bar_fig2 = px.bar(
                    result,
                    x='Description',
                    y='Replenishment_Accuracy',
                    title='Sum of Replenishment Accuracy by Description',
                    labels={'Replenishment_Accuracy': 'Sum of Replenishment Accuracy'}
                )

                treemap_fig = px.treemap(
                    result,
                    path=['Description'],
                    values='StockOut_Incidents',
                    title='Sum of StockOut Incidents by Description',
                    color='StockOut_Incidents',
                    color_continuous_scale='Viridis'
                )

                heatmap_fig = px.density_heatmap(
                    result,
                    x='Description',
                    y='Fill_Rate',
                    marginal_x='rug',
                    marginal_y='histogram',
                    title='Density of Fill Rate by Description'
                )

                figures = [bar_fig2, treemap_fig, heatmap_fig]
                return figures

            elif drop == "INVENTORY FOR FURNITURE":
                result = execute_query(
                    "SELECT  p.Product_ID, p.Description, SUM(t.Quantity) AS Total_Sales, iv.Replenishment_Accuracy, iv.Backorder_Rate, iv.StockOut_Incidents, iv.Fill_Rate FROM products AS p JOIN transactions AS t ON p.Product_ID = t.Product_ID JOIN inventoryMetrics AS iv ON p.Product_ID = iv.Product_ID WHERE iv.StockOut_Incidents > 4 AND p.Category = 'Furniture' GROUP BY p.Product_ID ORDER BY iv.Replenishment_Accuracy DESC, Total_Sales DESC;",
                    conn)
                bar_fig2 = px.bar(
                    result,
                    x='Description',
                    y='Replenishment_Accuracy',
                    title='Sum of Replenishment Accuracy by Description',
                    labels={'Replenishment_Accuracy': 'Sum of Replenishment Accuracy'}
                )

                treemap_fig = px.treemap(
                    result,
                    path=['Description'],
                    values='StockOut_Incidents',
                    title='Sum of StockOut Incidents by Description',
                    color='StockOut_Incidents',
                    color_continuous_scale='Viridis'
                )

                heatmap_fig = px.density_heatmap(
                    result,
                    x='Description',
                    y='Fill_Rate',
                    marginal_x='rug',
                    marginal_y='histogram',
                    title='Density of Fill Rate by Description'
                )

                figures = [bar_fig2, treemap_fig, heatmap_fig]
                return figures


def create_figures_marketing2(query, drop):
    conn = connect_to_db(DB_NAME)
    if query and drop:
        if query == "How effective are different marketing strategies across product categories in terms of sales volume, inventory management, and the occurrence of stockouts during promotional campaigns?":
            if drop == "WATER TOWER PLACE":
                result = execute_query(
                    "SELECT s.Store_ID, p.Category, pd.Marketing_Strategy, COUNT(pd.Promotional_Activity_Date) AS Number_of_Marketing_Campaigns, SUM(t.Quantity) AS Total_Sales_During_Campaigns, AVG(iv.Average_Monthly_Inventory_Level) AS Avg_Inventory_Level_During_Campaign, MIN(iv.Replenishment_Lead_Time) AS Min_Replenishment_Lead_Time, MAX(iv.StockOut_Incidents) AS Max_StockOuts FROM products AS p JOIN transactions AS t ON p.Product_ID = t.Product_ID JOIN shrinkageStores AS s ON t.Store_ID = s.Store_ID JOIN promotionalAndMarketData AS pd ON p.Product_ID = pd.Product_ID JOIN inventoryMetrics AS iv ON p.Product_ID = iv.Product_ID WHERE t.Date >= pd.Promotional_Activity_Date AND t.Store_ID = 'STORE01' GROUP BY p.Category, pd.Marketing_Strategy ORDER BY Total_Sales_During_Campaigns DESC, Avg_Inventory_Level_During_Campaign;",
                    conn)

                bar_fig = px.bar(
                    result,
                    x='Total_Sales_During_Campaigns',
                    y='Store_ID',
                    color='Marketing_Strategy',
                    orientation='h',
                    title='Total Sales by Store ID with Marketing Strategy Highlight'
                )
                bar_fig.update_layout(yaxis={'categoryorder': 'total ascending'})

                sunburst_fig = px.sunburst(
                    result,
                    path=['Category', 'Marketing_Strategy'],
                    values='Total_Sales_During_Campaigns',
                    title='Sales Breakdown by Category and Marketing Strategy'
                )

                box_fig = px.box(
                    result,
                    y='Total_Sales_During_Campaigns',
                    x='Category',
                    color='Category',
                    title='Sales Variability by Product Category'
                )

                figures = [bar_fig, sunburst_fig, box_fig]
                return figures



            elif drop == "RIVERFRONT PLAZA":
                result = execute_query(
                    "SELECT s.Store_ID, p.Category, pd.Marketing_Strategy, COUNT(pd.Promotional_Activity_Date) AS Number_of_Marketing_Campaigns, SUM(t.Quantity) AS Total_Sales_During_Campaigns, AVG(iv.Average_Monthly_Inventory_Level) AS Avg_Inventory_Level_During_Campaign, MIN(iv.Replenishment_Lead_Time) AS Min_Replenishment_Lead_Time, MAX(iv.StockOut_Incidents) AS Max_StockOuts FROM products AS p JOIN transactions AS t ON p.Product_ID = t.Product_ID JOIN shrinkageStores AS s ON t.Store_ID = s.Store_ID JOIN promotionalAndMarketData AS pd ON p.Product_ID = pd.Product_ID JOIN inventoryMetrics AS iv ON p.Product_ID = iv.Product_ID WHERE t.Date >= pd.Promotional_Activity_Date AND t.Store_ID = 'STORE28' GROUP BY p.Category, pd.Marketing_Strategy ORDER BY Total_Sales_During_Campaigns DESC, Avg_Inventory_Level_During_Campaign;",
                    conn)
                bar_fig = px.bar(
                    result,
                    x='Total_Sales_During_Campaigns',
                    y='Store_ID',
                    color='Marketing_Strategy',
                    orientation='h',
                    title='Total Sales by Store ID with Marketing Strategy Highlight'
                )
                bar_fig.update_layout(yaxis={'categoryorder': 'total ascending'})

                sunburst_fig = px.sunburst(
                    result,
                    path=['Category', 'Marketing_Strategy'],
                    values='Total_Sales_During_Campaigns',
                    title='Sales Breakdown by Category and Marketing Strategy'
                )

                box_fig = px.box(
                    result,
                    y='Total_Sales_During_Campaigns',
                    x='Category',
                    color='Category',
                    title='Sales Variability by Product Category'
                )

                figures = [bar_fig, sunburst_fig, box_fig]
                return figures


            elif drop == "WESTFIELD WHEATON":
                result = execute_query(
                    "SELECT s.Store_ID, p.Category, pd.Marketing_Strategy, COUNT(pd.Promotional_Activity_Date) AS Number_of_Marketing_Campaigns, SUM(t.Quantity) AS Total_Sales_During_Campaigns, AVG(iv.Average_Monthly_Inventory_Level) AS Avg_Inventory_Level_During_Campaign, MIN(iv.Replenishment_Lead_Time) AS Min_Replenishment_Lead_Time, MAX(iv.StockOut_Incidents) AS Max_StockOuts FROM products AS p JOIN transactions AS t ON p.Product_ID = t.Product_ID JOIN shrinkageStores AS s ON t.Store_ID = s.Store_ID JOIN promotionalAndMarketData AS pd ON p.Product_ID = pd.Product_ID JOIN inventoryMetrics AS iv ON p.Product_ID = iv.Product_ID WHERE t.Date >= pd.Promotional_Activity_Date AND t.Store_ID = 'STORE49' GROUP BY p.Category, pd.Marketing_Strategy ORDER BY Total_Sales_During_Campaigns DESC, Avg_Inventory_Level_During_Campaign;",
                    conn)
                bar_fig = px.bar(
                    result,
                    x='Total_Sales_During_Campaigns',
                    y='Store_ID',
                    color='Marketing_Strategy',
                    orientation='h',
                    title='Total Sales by Store ID with Marketing Strategy Highlight'
                )
                bar_fig.update_layout(yaxis={'categoryorder': 'total ascending'})

                sunburst_fig = px.sunburst(
                    result,
                    path=['Category', 'Marketing_Strategy'],
                    values='Total_Sales_During_Campaigns',
                    title='Sales Breakdown by Category and Marketing Strategy'
                )

                box_fig = px.box(
                    result,
                    y='Total_Sales_During_Campaigns',
                    x='Category',
                    color='Category',
                    title='Sales Variability by Product Category'
                )

                figures = [bar_fig, sunburst_fig, box_fig]
                return figures

        elif query == "How effective are different types of promotional activities at various urban store locations in terms of sales uplift, customer engagement, and inventory turnover?":
            if drop == "WATER TOWER PLACE":
                result = execute_query(
                    "SELECT s.Store_ID, s.Store_Location_Type, pd.Promotional_Activity_Type, COUNT(DISTINCT pd.Promotional_Activity_Date) AS Number_of_Promotions, AVG(vm.Sales_Uplift_by_Visual_Merchandising) AS Avg_Sales_Uplift, SUM(t.Quantity) AS Total_Sales, AVG(iv.Inventory_Monthly_Turnover_Rate) AS Avg_Inventory_Turnover, AVG(vm.Customer_Engagement_Metrics_Dwell_Time_Interactions) AS Avg_Customer_Engagement FROM shrinkageStores AS s JOIN transactions AS t ON s.Store_ID = t.Store_ID JOIN promotionalAndMarketData AS pd ON t.Product_ID = pd.Product_ID JOIN visualMerchandising AS vm ON s.Store_ID = vm.Store_ID JOIN inventoryMetrics AS iv ON t.Product_ID = iv.Product_ID WHERE t.Date >= pd.Promotional_Activity_Date AND s.Store_Location_Type = 'urban' AND t.Store_ID = 'STORE01' GROUP BY s.Store_ID, pd.Promotional_Activity_Type ORDER BY Avg_Sales_Uplift DESC, Avg_Inventory_Turnover DESC;",
                    conn)

                bar_fig = px.bar(
                    result,
                    x='Store_ID',
                    y='Avg_Inventory_Turnover',
                    color='Promotional_Activity_Type',
                    title='Average Inventory Turnover by Store'
                )

                hist_fig = px.histogram(
                    result,
                    x='Total_Sales',
                    color='Promotional_Activity_Type',
                    barmode='group',
                    title='Distribution of Total Sales by Promotional Activity Type'
                )

                area_fig = px.area(
                    result,
                    x='Promotional_Activity_Type',
                    y='Total_Sales',
                    color='Store_ID',
                    line_group='Store_ID',
                    title='Total Sales by Promotional Activity Type Across Stores'
                )

                pie_fig = px.pie(
                    result,
                    values='Total_Sales',
                    names='Promotional_Activity_Type',
                    title='Proportion of Total Sales by Promotional Activity Type'
                )

                figures = [bar_fig, hist_fig, area_fig, pie_fig]
                return figures

            elif drop == "RIVERFRONT PLAZA":
                result = execute_query(
                    "SELECT s.Store_ID, s.Store_Location_Type, pd.Promotional_Activity_Type, COUNT(DISTINCT pd.Promotional_Activity_Date) AS Number_of_Promotions, AVG(vm.Sales_Uplift_by_Visual_Merchandising) AS Avg_Sales_Uplift, SUM(t.Quantity) AS Total_Sales, AVG(iv.Inventory_Monthly_Turnover_Rate) AS Avg_Inventory_Turnover, AVG(vm.Customer_Engagement_Metrics_Dwell_Time_Interactions) AS Avg_Customer_Engagement FROM shrinkageStores AS s JOIN transactions AS t ON s.Store_ID = t.Store_ID JOIN promotionalAndMarketData AS pd ON t.Product_ID = pd.Product_ID JOIN visualMerchandising AS vm ON s.Store_ID = vm.Store_ID JOIN inventoryMetrics AS iv ON t.Product_ID = iv.Product_ID WHERE t.Date >= pd.Promotional_Activity_Date AND s.Store_Location_Type = 'urban' AND t.Store_ID = 'STORE28' GROUP BY s.Store_ID, pd.Promotional_Activity_Type ORDER BY Avg_Sales_Uplift DESC, Avg_Inventory_Turnover DESC;",
                    conn)
                bar_fig = px.bar(
                    result,
                    x='Store_ID',
                    y='Avg_Inventory_Turnover',
                    color='Promotional_Activity_Type',
                    title='Average Inventory Turnover by Store'
                )

                hist_fig = px.histogram(
                    result,
                    x='Total_Sales',
                    color='Promotional_Activity_Type',
                    barmode='group',
                    title='Distribution of Total Sales by Promotional Activity Type'
                )

                area_fig = px.area(
                    result,
                    x='Promotional_Activity_Type',
                    y='Total_Sales',
                    color='Store_ID',
                    line_group='Store_ID',
                    title='Total Sales by Promotional Activity Type Across Stores'
                )

                pie_fig = px.pie(
                    result,
                    values='Total_Sales',
                    names='Promotional_Activity_Type',
                    title='Proportion of Total Sales by Promotional Activity Type'
                )

                figures = [bar_fig, hist_fig, area_fig, pie_fig]
                return figures

            elif drop == "WESTFIELD WHEATON":
                result = execute_query(
                    "SELECT s.Store_ID, s.Store_Location_Type, pd.Promotional_Activity_Type, COUNT(DISTINCT pd.Promotional_Activity_Date) AS Number_of_Promotions, AVG(vm.Sales_Uplift_by_Visual_Merchandising) AS Avg_Sales_Uplift, SUM(t.Quantity) AS Total_Sales, AVG(iv.Inventory_Monthly_Turnover_Rate) AS Avg_Inventory_Turnover, AVG(vm.Customer_Engagement_Metrics_Dwell_Time_Interactions) AS Avg_Customer_Engagement FROM shrinkageStores AS s JOIN transactions AS t ON s.Store_ID = t.Store_ID JOIN promotionalAndMarketData AS pd ON t.Product_ID = pd.Product_ID JOIN visualMerchandising AS vm ON s.Store_ID = vm.Store_ID JOIN inventoryMetrics AS iv ON t.Product_ID = iv.Product_ID WHERE t.Date >= pd.Promotional_Activity_Date AND s.Store_Location_Type = 'urban' AND t.Store_ID = 'STORE49' GROUP BY s.Store_ID, pd.Promotional_Activity_Type ORDER BY Avg_Sales_Uplift DESC, Avg_Inventory_Turnover DESC;",
                    conn)
                bar_fig = px.bar(
                    result,
                    x='Store_ID',
                    y='Avg_Inventory_Turnover',
                    color='Promotional_Activity_Type',
                    title='Average Inventory Turnover by Store'
                )

                hist_fig = px.histogram(
                    result,
                    x='Total_Sales',
                    color='Promotional_Activity_Type',
                    barmode='group',
                    title='Distribution of Total Sales by Promotional Activity Type'
                )

                area_fig = px.area(
                    result,
                    x='Promotional_Activity_Type',
                    y='Total_Sales',
                    color='Store_ID',
                    line_group='Store_ID',
                    title='Total Sales by Promotional Activity Type Across Stores'
                )

                pie_fig = px.pie(
                    result,
                    values='Total_Sales',
                    names='Promotional_Activity_Type',
                    title='Proportion of Total Sales by Promotional Activity Type'
                )

                figures = [bar_fig, hist_fig, area_fig, pie_fig]
                return figures
def create_figures2(query, drop):
    conn = connect_to_db(DB_NAME)
    if query and drop:
        if query == "For this store, which products are running low on inventory and have a per unit value greater than 50?":
            if drop == "WATER TOWER PLACE":
                result = execute_query(
                        """
                        SELECT p.Product_ID, p.Description,p.Unit_Price, p.Stock_Availability
                        FROM products p
                        JOIN transactions t ON p.Product_ID = t.Product_ID
                        WHERE t.Store_ID = 'STORE01'
                        AND p.Stock_Availability < 10  -- Adjust the threshold for low inventory as needed
                        AND p.Unit_Price > 50
                        GROUP BY p.Product_ID, p.Description, p.Unit_Price, p.Stock_Availability
                        ORDER BY p.Stock_Availability ASC;
                        """,conn)

                fig_bar = px.bar(result,
                         x='Description',
                         y='Stock_Availability',
                         title='Stock Availability by Product',
                         labels={'Stock_Availability': 'Units in Stock', 'Description': 'Product Description'})
                fig_bubble = fig = px.scatter(result,
                 x='Unit_Price',
                 y='Stock_Availability',
                 size='Stock_Availability',
                 color='Description',
                 title='Bubble Chart: Unit Price vs. Stock Availability',
                 labels={'Unit_Price': 'Unit Price', 'Stock_Availability': 'Units in Stock'})

                figures = [fig_bar, fig_bubble]
                return figures

            if drop == "RIVERFRONT PLAZA":
                result = execute_query(
                        """
                        SELECT p.Product_ID, p.Description,p.Unit_Price, p.Stock_Availability
                        FROM products p
                        JOIN transactions t ON p.Product_ID = t.Product_ID
                        WHERE t.Store_ID = 'STORE28'
                        AND p.Stock_Availability < 10  -- Adjust the threshold for low inventory as needed
                        AND p.Unit_Price > 50
                        GROUP BY p.Product_ID, p.Description, p.Unit_Price, p.Stock_Availability
                        ORDER BY p.Stock_Availability ASC;
                        """,conn)

                fig_bar = px.bar(result,
                         x='Description',
                         y='Stock_Availability',
                         title='Stock Availability by Product',
                         labels={'Stock_Availability': 'Units in Stock', 'Description': 'Product Description'})
                fig_bubble = fig = px.scatter(result,
                 x='Unit_Price',
                 y='Stock_Availability',
                 size='Stock_Availability',
                 color='Description',
                 title='Bubble Chart: Unit Price vs. Stock Availability',
                 labels={'Unit_Price': 'Unit Price', 'Stock_Availability': 'Units in Stock'})

                figures = [fig_bar, fig_bubble]
                return figures

            if drop == "WESTFIELD WHEATON":
                result = execute_query(
                        """
                        SELECT p.Product_ID, p.Description,p.Unit_Price, p.Stock_Availability
                        FROM products p
                        JOIN transactions t ON p.Product_ID = t.Product_ID
                        WHERE t.Store_ID = 'STORE49'
                        AND p.Stock_Availability < 10  -- Adjust the threshold for low inventory as needed
                        AND p.Unit_Price > 50
                        GROUP BY p.Product_ID, p.Description, p.Unit_Price, p.Stock_Availability
                        ORDER BY p.Stock_Availability ASC;
                        """,conn)

                fig_bar = px.bar(result,
                         x='Description',
                         y='Stock_Availability',
                         title='Stock Availability by Product',
                         labels={'Stock_Availability': 'Units in Stock', 'Description': 'Product Description'})
                fig_bubble = fig = px.scatter(result,
                 x='Unit_Price',
                 y='Stock_Availability',
                 size='Stock_Availability',
                 color='Description',
                 title='Bubble Chart: Unit Price vs. Stock Availability',
                 labels={'Unit_Price': 'Unit Price', 'Stock_Availability': 'Units in Stock'})

                figures = [fig_bar, fig_bubble]
                return figures

            if query == "Give a daily breakdown UPT for all product categories for each store during May":
                if drop == "WATER TOWER PLACE":
                    result = execute_query(
                        "SELECT DATE(t.Date) AS Sale_Date, p.Category AS Product_Category, t.Store_ID, ROUND(SUM(t.Quantity) / COUNT(t.Transaction_ID), 2) AS UPT\nFROM retail_panopticon.transactions t\nJOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID\nWHERE t.Store_ID = 'STORE01' AND  t.Date BETWEEN '2024-05-01' AND '2024-05-31'\nGROUP BY DATE(t.Date), p.Category\nORDER BY DATE(t.Date), p.Category;",
                        conn)

                    pie_fig = px.pie(
                        result,
                        values='UPT',
                        names='Product_Category',
                        title='Sum of UPT by Product Category'
                    )

                    filtered_data = result[result['Product_Category'].isin(['Clothing', 'Toys'])]
                    line_fig = px.line(
                        filtered_data,
                        x='Sale_Date',
                        y='UPT',
                        color='Product_Category',
                        title='Product Category Sales report'
                    )
                    line_fig.update_layout(
                        xaxis_title='Sale_Date',
                        yaxis_title='Sum of UPT',
                        legend_title='Product Category'
                    )

                    bar_fig = px.bar(
                        result,
                        x='UPT',
                        y='Store_ID',
                        orientation='h',
                        title='Sum of UPT by Store_ID'
                    )
                    bar_fig.update_layout(yaxis={'categoryorder': 'total ascending'})

                    figures = [pie_fig, bar_fig, line_fig]
                    return figures



                elif drop == "RIVERFRONT PLAZA":
                    result = execute_query(
                        "SELECT DATE(t.Date) AS Sale_Date, p.Category AS Product_Category, t.Store_ID, ROUND(SUM(t.Quantity) / COUNT(t.Transaction_ID), 2) AS UPT\nFROM retail_panopticon.transactions t\nJOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID\nWHERE t.Store_ID = 'STORE28' AND  t.Date BETWEEN '2024-05-01' AND '2024-05-31'\nGROUP BY DATE(t.Date), p.Category\nORDER BY DATE(t.Date), p.Category;",
                        conn)
                    pie_fig = px.pie(
                        result,
                        values='UPT',
                        names='Product_Category',
                        title='Sum of UPT by Product Category'
                    )

                    filtered_data = result[result['Product_Category'].isin(['Clothing', 'Toys'])]
                    line_fig = px.line(
                        filtered_data,
                        x='Sale_Date',
                        y='UPT',
                        color='Product_Category',
                        title='Product Category Sales report'
                    )
                    line_fig.update_layout(
                        xaxis_title='Sale_Date',
                        yaxis_title='Sum of UPT',
                        legend_title='Product Category'
                    )

                    bar_fig = px.bar(
                        result,
                        x='UPT',
                        y='Store_ID',
                        orientation='h',
                        title='Sum of UPT by Store_ID'
                    )
                    bar_fig.update_layout(yaxis={'categoryorder': 'total ascending'})

                    figures = [pie_fig, bar_fig, line_fig]
                    return figures

                elif drop == "WESTFIELD WHEATON":
                    result = execute_query(
                        "SELECT DATE(t.Date) AS Sale_Date, p.Category AS Product_Category, t.Store_ID, ROUND(SUM(t.Quantity) / COUNT(t.Transaction_ID), 2) AS UPT\nFROM retail_panopticon.transactions t\nJOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID\nWHERE t.Store_ID = 'STORE49' AND  t.Date BETWEEN '2024-05-01' AND '2024-05-31'\nGROUP BY DATE(t.Date), p.Category\nORDER BY DATE(t.Date), p.Category;",
                        conn)
                    pie_fig = px.pie(
                        result,
                        values='UPT',
                        names='Product_Category',
                        title='Sum of UPT by Product Category'
                    )

                    filtered_data = result[result['Product_Category'].isin(['Clothing', 'Toys'])]
                    line_fig = px.line(
                        filtered_data,
                        x='Sale_Date',
                        y='UPT',
                        color='Product_Category',
                        title='Product Category Sales report'
                    )
                    line_fig.update_layout(
                        xaxis_title='Sale_Date',
                        yaxis_title='Sum of UPT',
                        legend_title='Product Category'
                    )

                    bar_fig = px.bar(
                        result,
                        x='UPT',
                        y='Store_ID',
                        orientation='h',
                        title='Sum of UPT by Store_ID'
                    )
                    bar_fig.update_layout(yaxis={'categoryorder': 'total ascending'})

                    figures = [pie_fig, bar_fig, line_fig]
                    return figures

            elif query == "What was the impact of the promotional discounts offered in May on the weekend vs. weekday sales for all product categories?":
                if drop == "WATER TOWER PLACE":
                    result = execute_query(
                        "SELECT CASE WHEN DAYOFWEEK(S.date) IN (1, 7) THEN 'Weekend' ELSE 'Weekday' END AS day_type, P.Category,SUM(S.Total_Amount) AS total_sales, COUNT(DISTINCT S.Transaction_ID) AS total_transactions, AVG(S.Total_Amount) AS avg_transaction_value FROM transactions S JOIN productInformation P ON S.Product_ID = P.Product_ID WHERE S.Store_ID = 'STORE01' AND DATE_FORMAT(S.date, '%Y-%m') = '2024-05' GROUP BY day_type, P.Category ORDER BY day_type DESC, total_sales DESC;",
                        conn)

                    total_sales_per_category = result.groupby('Category')['total_sales'].sum().reset_index()
                    df = result.merge(total_sales_per_category, on='Category', suffixes=('', '_total'))
                    fig2 = px.bar(
                        df,
                        y='Category',
                        x='total_sales',
                        color='day_type',
                        title='Total Sales for Each Product Category',
                        labels={'total_sales': 'Total Sales', 'Category': 'Product Category'},
                        barmode='group',
                        orientation='h',
                        color_discrete_map={'Weekday': 'goldenrod', 'Weekend': 'dodgerblue'}
                    )

                    fig3 = px.bar(
                        df,
                        x='Category',
                        y='avg_transaction_value',
                        color='day_type',
                        title='Average Transaction Value for Each Category',
                        labels={'avg_transaction_value': 'Average Transaction Value', 'Category': 'Product Category'},
                        barmode='stack',
                        text_auto=True,
                        color_discrete_map={'Weekday': 'orange', 'Weekend': 'purple'}
                    )

                    total_sales_per_category = result.groupby('Category')['total_sales'].sum().reset_index()
                    df = result.merge(total_sales_per_category, on='Category', suffixes=('', '_total'))
                    df['sales_percentage'] = df['total_sales'] / df['total_sales_total'] * 100
                    fig = px.bar(
                        df,
                        x='Category',
                        y='sales_percentage',
                        color='day_type',
                        title='Total Sales Percentage for Each Product Category',
                        labels={'sales_percentage': 'Percentage of Total Sales', 'Category': 'Product Category'},
                        text_auto=True,
                        barmode='stack'
                    )

                    fig1 = px.bar(
                        df,
                        y='Category',
                        x='total_transactions',
                        color='day_type',
                        title='Total Transactions for Each Product Category',
                        labels={'total_transactions': 'Total Transactions', 'Category': 'Product Category'},
                        barmode='group',
                        orientation='h',
                        color_discrete_map={'Weekday': 'mediumseagreen', 'Weekend': 'tomato'}
                    )
                    figures = [fig2, fig3, fig, fig1]
                    return figures

                elif drop == "RIVERFRONT PLAZA":
                    result = execute_query(
                        "SELECT CASE WHEN DAYOFWEEK(S.date) IN (1, 7) THEN 'Weekend' ELSE 'Weekday' END AS day_type, P.Category,SUM(S.Total_Amount) AS total_sales, COUNT(DISTINCT S.Transaction_ID) AS total_transactions, AVG(S.Total_Amount) AS avg_transaction_value FROM transactions S JOIN productInformation P ON S.Product_ID = P.Product_ID WHERE S.Store_ID = 'STORE28' AND DATE_FORMAT(S.date, '%Y-%m') = '2024-05' GROUP BY day_type, P.Category ORDER BY day_type DESC, total_sales DESC;",
                        conn)
                    total_sales_per_category = result.groupby('Category')['total_sales'].sum().reset_index()
                    df = result.merge(total_sales_per_category, on='Category', suffixes=('', '_total'))
                    fig2 = px.bar(
                        df,
                        y='Category',
                        x='total_sales',
                        color='day_type',
                        title='Total Sales for Each Product Category',
                        labels={'total_sales': 'Total Sales', 'Category': 'Product Category'},
                        barmode='group',
                        orientation='h',
                        color_discrete_map={'Weekday': 'goldenrod', 'Weekend': 'dodgerblue'}
                    )

                    fig3 = px.bar(
                        df,
                        x='Category',
                        y='avg_transaction_value',
                        color='day_type',
                        title='Average Transaction Value for Each Category',
                        labels={'avg_transaction_value': 'Average Transaction Value', 'Category': 'Product Category'},
                        barmode='stack',
                        text_auto=True,
                        color_discrete_map={'Weekday': 'orange', 'Weekend': 'purple'}
                    )

                    total_sales_per_category = result.groupby('Category')['total_sales'].sum().reset_index()
                    df = result.merge(total_sales_per_category, on='Category', suffixes=('', '_total'))
                    df['sales_percentage'] = df['total_sales'] / df['total_sales_total'] * 100
                    fig = px.bar(
                        df,
                        x='Category',
                        y='sales_percentage',
                        color='day_type',
                        title='Total Sales Percentage for Each Product Category',
                        labels={'sales_percentage': 'Percentage of Total Sales', 'Category': 'Product Category'},
                        text_auto=True,
                        barmode='stack'
                    )

                    fig1 = px.bar(
                        df,
                        y='Category',
                        x='total_transactions',
                        color='day_type',
                        title='Total Transactions for Each Product Category',
                        labels={'total_transactions': 'Total Transactions', 'Category': 'Product Category'},
                        barmode='group',
                        orientation='h',
                        color_discrete_map={'Weekday': 'mediumseagreen', 'Weekend': 'tomato'}
                    )
                    figures = [fig2, fig3, fig, fig1]
                    return figures

                elif drop == "WESTFIELD WHEATON":
                    result = execute_query(
                        "SELECT CASE WHEN DAYOFWEEK(S.date) IN (1, 7) THEN 'Weekend' ELSE 'Weekday' END AS day_type, P.Category,SUM(S.Total_Amount) AS total_sales, COUNT(DISTINCT S.Transaction_ID) AS total_transactions, AVG(S.Total_Amount) AS avg_transaction_value FROM transactions S JOIN productInformation P ON S.Product_ID = P.Product_ID WHERE S.Store_ID = 'STORE49' AND DATE_FORMAT(S.date, '%Y-%m') = '2024-05' GROUP BY day_type, P.Category ORDER BY day_type DESC, total_sales DESC;",
                        conn)
                    total_sales_per_category = result.groupby('Category')['total_sales'].sum().reset_index()
                    df = result.merge(total_sales_per_category, on='Category', suffixes=('', '_total'))
                    fig2 = px.bar(
                        df,
                        y='Category',
                        x='total_sales',
                        color='day_type',
                        title='Total Sales for Each Product Category',
                        labels={'total_sales': 'Total Sales', 'Category': 'Product Category'},
                        barmode='group',
                        orientation='h',
                        color_discrete_map={'Weekday': 'goldenrod', 'Weekend': 'dodgerblue'}
                    )

                    fig3 = px.bar(
                        df,
                        x='Category',
                        y='avg_transaction_value',
                        color='day_type',
                        title='Average Transaction Value for Each Category',
                        labels={'avg_transaction_value': 'Average Transaction Value', 'Category': 'Product Category'},
                        barmode='stack',
                        text_auto=True,
                        color_discrete_map={'Weekday': 'orange', 'Weekend': 'purple'}
                    )

                    total_sales_per_category = result.groupby('Category')['total_sales'].sum().reset_index()
                    df = result.merge(total_sales_per_category, on='Category', suffixes=('', '_total'))
                    df['sales_percentage'] = df['total_sales'] / df['total_sales_total'] * 100
                    fig = px.bar(
                        df,
                        x='Category',
                        y='sales_percentage',
                        color='day_type',
                        title='Total Sales Percentage for Each Product Category',
                        labels={'sales_percentage': 'Percentage of Total Sales', 'Category': 'Product Category'},
                        text_auto=True,
                        barmode='stack'
                    )

                    fig1 = px.bar(
                        df,
                        y='Category',
                        x='total_transactions',
                        color='day_type',
                        title='Total Transactions for Each Product Category',
                        labels={'total_transactions': 'Total Transactions', 'Category': 'Product Category'},
                        barmode='group',
                        orientation='h',
                        color_discrete_map={'Weekday': 'mediumseagreen', 'Weekend': 'tomato'}
                    )
                    figures = [fig2, fig3, fig, fig1]
                    return figures

            elif query == "Give the total shipments delivered late and the reason for the delay for each product category":
                if drop == "WATER TOWER PLACE":
                    result = execute_query(
                        "SELECT t.Store_ID, p.Category,s.Reason_Late_Shipment, COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments FROM transactions t JOIN productInformation p ON t.Product_ID = p.Product_ID JOIN shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID WHERE t.Store_ID = 'STORE01' GROUP BY p.Category, s.Reason_Late_Shipment HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0 ORDER BY Total_Late_Shipments DESC;",
                        conn)
                    fig_pie = px.sunburst(
                        result,
                        path=['Category', 'Reason_Late_Shipment'],
                        values='Total_Late_Shipments',
                        title='Reasons for Late Shipments by Product Category',
                        color='Reason_Late_Shipment',
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )

                    total_shipments_by_category = result.groupby('Category')['Total_Late_Shipments'].sum().reset_index()
                    fig_bar = px.bar(
                        total_shipments_by_category,
                        y='Category',
                        x='Total_Late_Shipments',
                        title='Total Late Shipments by Product Category',
                        labels={'Total_Late_Shipments': 'Total Late Shipments'},
                        color='Category',
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    figures = [fig_pie, fig_bar]
                    return figures

                elif drop == "RIVERFRONT PLAZA":
                    result = execute_query(
                        "SELECT t.Store_ID, p.Category,s.Reason_Late_Shipment, COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments FROM transactions t JOIN productInformation p ON t.Product_ID = p.Product_ID JOIN shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID WHERE t.Store_ID = 'STORE28' GROUP BY p.Category, s.Reason_Late_Shipment HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0 ORDER BY Total_Late_Shipments DESC;",
                        conn)
                    fig_pie = px.sunburst(
                        result,
                        path=['Category', 'Reason_Late_Shipment'],
                        values='Total_Late_Shipments',
                        title='Reasons for Late Shipments by Product Category',
                        color='Reason_Late_Shipment',
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )

                    total_shipments_by_category = result.groupby('Category')['Total_Late_Shipments'].sum().reset_index()
                    fig_bar = px.bar(
                        total_shipments_by_category,
                        y='Category',
                        x='Total_Late_Shipments',
                        title='Total Late Shipments by Product Category',
                        labels={'Total_Late_Shipments': 'Total Late Shipments'},
                        color='Category',
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    figures = [fig_pie, fig_bar]
                    return figures

                elif drop == "WESTFIELD WHEATON":
                    result = execute_query(
                        "SELECT t.Store_ID, p.Category,s.Reason_Late_Shipment, COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments FROM transactions t JOIN productInformation p ON t.Product_ID = p.Product_ID JOIN shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID WHERE t.Store_ID = 'STORE49' GROUP BY p.Category, s.Reason_Late_Shipment HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0 ORDER BY Total_Late_Shipments DESC;",
                        conn)
                    fig_pie = px.sunburst(
                        result,
                        path=['Category', 'Reason_Late_Shipment'],
                        values='Total_Late_Shipments',
                        title='Reasons for Late Shipments by Product Category',
                        color='Reason_Late_Shipment',
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )

                    total_shipments_by_category = result.groupby('Category')['Total_Late_Shipments'].sum().reset_index()
                    fig_bar = px.bar(
                        total_shipments_by_category,
                        y='Category',
                        x='Total_Late_Shipments',
                        title='Total Late Shipments by Product Category',
                        labels={'Total_Late_Shipments': 'Total Late Shipments'},
                        color='Category',
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    figures = [fig_pie, fig_bar]
                    return figures
            # Merchandizing Agentic App
            # Question 1
            elif query == "What are the top 3 most common reasons for delays in order fulfillment and which product categories are most severely affected by delays?":
                if drop == "FOOD":
                    df = pd.read_sql_query("""SELECT p.Category, o.Delay_Reason, COUNT(o.Transaction_ID) AS Delay_Count
                        FROM retail_panopticon.orderFulfillment o
                        JOIN retail_panopticon.transactions t ON o.Transaction_ID = t.Transaction_ID
                        JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID
                        WHERE o.`On-Time_Fulfillment_Rate` < 100  AND p.Category='Food' AND o.Delay_Reason IS NOT NULL
                           AND o.Delay_Reason != ''
                        GROUP BY p.Category, o.Delay_Reason
                        ORDER BY Delay_Count DESC;""", conn)

                    top_3_reasons = df.groupby('Delay_Reason')['Delay_Count'].sum().nlargest(3).reset_index()

                    # Plotting
                    fig_bar_delay = px.bar(top_3_reasons, x='Delay_Reason', y='Delay_Count',
                                           title='Top 3 Most Common Reasons for Delays in Order Fulfillment',
                                           labels={'Delay_Reason': 'Delay Reason',
                                                   'Delay_Count': 'Number of Delays'})

                    filtered_df = df[df['Delay_Reason'].isin(top_3_reasons['Delay_Reason'])]
                    # Plotting
                    fig_bar_delay_category = px.bar(filtered_df, x='Category', y='Delay_Count',
                                                    color='Delay_Reason',
                                                    title='Top 3 Delay Reasons by Product Category',
                                                    labels={'Category': 'Product Category',
                                                            'Delay_Count': 'Number of Delays',
                                                            'Delay_Reason': 'Delay Reason'},
                                                    barmode='stack')

                    # Pivoting the dataframe for heatmap
                    heatmap_df = df.pivot(index='Category', columns='Delay_Reason', values='Delay_Count').fillna(0)
                    # Plotting
                    fig_heatmap = px.imshow(heatmap_df,
                                            title='Heatmap of Delay Reasons Across Product Categories',
                                            labels={'x': 'Delay Reason', 'y': 'Product Category',
                                                    'color': 'Number of Delays'},
                                            aspect='auto')

                    figures = [fig_bar_delay, fig_bar_delay_category, fig_heatmap]
                    return figures

                if drop == "CLOTHING":
                    df = pd.read_sql_query("""SELECT p.Category, o.Delay_Reason, COUNT(o.Transaction_ID) AS Delay_Count
                        FROM retail_panopticon.orderFulfillment o
                        JOIN retail_panopticon.transactions t ON o.Transaction_ID = t.Transaction_ID
                        JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID
                        WHERE o.`On-Time_Fulfillment_Rate` < 100  AND p.Category='Clothing' AND o.Delay_Reason IS NOT NULL
                           AND o.Delay_Reason != ''
                        GROUP BY p.Category, o.Delay_Reason
                        ORDER BY Delay_Count DESC;""", conn)

                    top_3_reasons = df.groupby('Delay_Reason')['Delay_Count'].sum().nlargest(3).reset_index()

                    # Plotting
                    fig_bar_delay = px.bar(top_3_reasons, x='Delay_Reason', y='Delay_Count',
                                           title='Top 3 Most Common Reasons for Delays in Order Fulfillment',
                                           labels={'Delay_Reason': 'Delay Reason',
                                                   'Delay_Count': 'Number of Delays'})

                    filtered_df = df[df['Delay_Reason'].isin(top_3_reasons['Delay_Reason'])]
                    # Plotting
                    fig_bar_delay_category = px.bar(filtered_df, x='Category', y='Delay_Count',
                                                    color='Delay_Reason',
                                                    title='Top 3 Delay Reasons by Product Category',
                                                    labels={'Category': 'Product Category',
                                                            'Delay_Count': 'Number of Delays',
                                                            'Delay_Reason': 'Delay Reason'},
                                                    barmode='stack')

                    # Pivoting the dataframe for heatmap
                    heatmap_df = df.pivot(index='Category', columns='Delay_Reason', values='Delay_Count').fillna(0)
                    # Plotting
                    fig_heatmap = px.imshow(heatmap_df,
                                            title='Heatmap of Delay Reasons Across Product Categories',
                                            labels={'x': 'Delay Reason', 'y': 'Product Category',
                                                    'color': 'Number of Delays'},
                                            aspect='auto')

                    figures = [fig_bar_delay, fig_bar_delay_category, fig_heatmap]
                    return figures

                if drop == "TOYS":
                    df = pd.read_sql_query("""SELECT p.Category, o.Delay_Reason, COUNT(o.Transaction_ID) AS Delay_Count
                        FROM retail_panopticon.orderFulfillment o
                        JOIN retail_panopticon.transactions t ON o.Transaction_ID = t.Transaction_ID
                        JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID
                        WHERE o.`On-Time_Fulfillment_Rate` < 100 AND p.Category='Toys' AND o.Delay_Reason IS NOT NULL
                           AND o.Delay_Reason != ''
                        GROUP BY p.Category, o.Delay_Reason
                        ORDER BY Delay_Count DESC;""", conn)

                    top_3_reasons = df.groupby('Delay_Reason')['Delay_Count'].sum().nlargest(3).reset_index()

                    # Plotting
                    fig_bar_delay = px.bar(top_3_reasons, x='Delay_Reason', y='Delay_Count',
                                           title='Top 3 Most Common Reasons for Delays in Order Fulfillment',
                                           labels={'Delay_Reason': 'Delay Reason',
                                                   'Delay_Count': 'Number of Delays'})

                    filtered_df = df[df['Delay_Reason'].isin(top_3_reasons['Delay_Reason'])]
                    # Plotting
                    fig_bar_delay_category = px.bar(filtered_df, x='Category', y='Delay_Count',
                                                    color='Delay_Reason',
                                                    title='Top 3 Delay Reasons by Product Category',
                                                    labels={'Category': 'Product Category',
                                                            'Delay_Count': 'Number of Delays',
                                                            'Delay_Reason': 'Delay Reason'},
                                                    barmode='stack')

                    # Pivoting the dataframe for heatmap
                    heatmap_df = df.pivot(index='Category', columns='Delay_Reason', values='Delay_Count').fillna(0)
                    # Plotting
                    fig_heatmap = px.imshow(heatmap_df,
                                            title='Heatmap of Delay Reasons Across Product Categories',
                                            labels={'x': 'Delay Reason', 'y': 'Product Category',
                                                    'color': 'Number of Delays'},
                                            aspect='auto')

                    figures = [fig_bar_delay, fig_bar_delay_category, fig_heatmap]
                    return figures

                if drop == "ELECTRONICS":
                    df = pd.read_sql_query("""SELECT p.Category, o.Delay_Reason, COUNT(o.Transaction_ID) AS Delay_Count
                        FROM retail_panopticon.orderFulfillment o
                        JOIN retail_panopticon.transactions t ON o.Transaction_ID = t.Transaction_ID
                        JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID
                        WHERE o.`On-Time_Fulfillment_Rate` < 100 AND p.Category='Electronics' AND o.Delay_Reason IS NOT NULL
                           AND o.Delay_Reason != ''
                        GROUP BY p.Category, o.Delay_Reason
                        ORDER BY Delay_Count DESC;""", conn)

                    top_3_reasons = df.groupby('Delay_Reason')['Delay_Count'].sum().nlargest(3).reset_index()

                    # Plotting
                    fig_bar_delay = px.bar(top_3_reasons, x='Delay_Reason', y='Delay_Count',
                                           title='Top 3 Most Common Reasons for Delays in Order Fulfillment',
                                           labels={'Delay_Reason': 'Delay Reason',
                                                   'Delay_Count': 'Number of Delays'})

                    filtered_df = df[df['Delay_Reason'].isin(top_3_reasons['Delay_Reason'])]
                    # Plotting
                    fig_bar_delay_category = px.bar(filtered_df, x='Category', y='Delay_Count',
                                                    color='Delay_Reason',
                                                    title='Top 3 Delay Reasons by Product Category',
                                                    labels={'Category': 'Product Category',
                                                            'Delay_Count': 'Number of Delays',
                                                            'Delay_Reason': 'Delay Reason'},
                                                    barmode='stack')

                    # Pivoting the dataframe for heatmap
                    heatmap_df = df.pivot(index='Category', columns='Delay_Reason', values='Delay_Count').fillna(0)
                    # Plotting
                    fig_heatmap = px.imshow(heatmap_df,
                                            title='Heatmap of Delay Reasons Across Product Categories',
                                            labels={'x': 'Delay Reason', 'y': 'Product Category',
                                                    'color': 'Number of Delays'},
                                            aspect='auto')

                    figures = [fig_bar_delay, fig_bar_delay_category, fig_heatmap]
                    return figures

            # Question 2
            elif query == "Which products in this category have the highest rates of replacement requests?":
                if drop=="FOOD":
                    df = pd.read_sql_query("""SELECT p.Product_ID,p.Product_Description,p.Category, ROUND(AVG(r.Replacement_Order_Frequency), 2) AS Avg_Replacement_Frequency
                         FROM retail_panopticon.replacementsAndDefects r
                        JOIN retail_panopticon.transactions t ON r.Transaction_ID = t.Transaction_ID
                        JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID
                        WHERE p.Category='Food'
                        GROUP BY p.Product_ID,p.Product_Description,p.Category
                        ORDER BY Avg_Replacement_Frequency DESC LIMIT 10;""", conn)

                    fig_bar = px.bar(df, x='Product_Description', y='Avg_Replacement_Frequency',
                                     title='Top 10 Products by Average Replacement Frequency',
                                     labels={'Product_Description': 'Product',
                                             'Avg_Replacement_Frequency': 'Avg Replacement Frequency'},
                                     text='Avg_Replacement_Frequency')

                    fig_bar.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                    fig_bar.update_layout(xaxis_tickangle=-45)

                    pie_df = df.groupby('Category')['Avg_Replacement_Frequency'].sum().reset_index()

                    # Plotting
                    fig_pie = px.pie(pie_df, values='Avg_Replacement_Frequency', names='Category',
                                     title='Distribution of Replacement Requests by Product Category',
                                     labels={'Category': 'Product Category',
                                             'Avg_Replacement_Frequency': 'Total Replacement Frequency'})

                    category_df = df.groupby('Category')[
                        'Avg_Replacement_Frequency'].mean().reset_index().sort_values(
                        by='Avg_Replacement_Frequency', ascending=False)

                    # Plotting
                    fig_bar2 = px.bar(category_df, x='Avg_Replacement_Frequency', y='Category',
                                      title='Top Categories by Average Replacement Frequency',
                                      labels={'Category': 'Product Category',
                                              'Avg_Replacement_Frequency': 'Avg Replacement Frequency'},
                                      orientation='h',
                                      text='Avg_Replacement_Frequency')

                    fig_bar2.update_traces(texttemplate='%{text:.2f}', textposition='outside')

                    figures = [fig_bar, fig_pie, fig_bar2]
                    return figures

                elif drop == "CLOTHING":
                    df = pd.read_sql_query("""SELECT p.Product_ID,p.Product_Description,p.Category, ROUND(AVG(r.Replacement_Order_Frequency), 2) AS Avg_Replacement_Frequency
                         FROM retail_panopticon.replacementsAndDefects r
                        JOIN retail_panopticon.transactions t ON r.Transaction_ID = t.Transaction_ID
                        JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID
                        WHERE p.Category='Clothing'
                        GROUP BY p.Product_ID,p.Product_Description,p.Category
                        ORDER BY Avg_Replacement_Frequency DESC LIMIT 10;""", conn)

                    fig_bar = px.bar(df, x='Product_Description', y='Avg_Replacement_Frequency',
                                     title='Top 10 Products by Average Replacement Frequency',
                                     labels={'Product_Description': 'Product',
                                             'Avg_Replacement_Frequency': 'Avg Replacement Frequency'},
                                     text='Avg_Replacement_Frequency')

                    fig_bar.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                    fig_bar.update_layout(xaxis_tickangle=-45)

                    pie_df = df.groupby('Category')['Avg_Replacement_Frequency'].sum().reset_index()

                    # Plotting
                    fig_pie = px.pie(pie_df, values='Avg_Replacement_Frequency', names='Category',
                                     title='Distribution of Replacement Requests by Product Category',
                                     labels={'Category': 'Product Category',
                                             'Avg_Replacement_Frequency': 'Total Replacement Frequency'})

                    category_df = df.groupby('Category')[
                        'Avg_Replacement_Frequency'].mean().reset_index().sort_values(
                        by='Avg_Replacement_Frequency', ascending=False)

                    # Plotting
                    fig_bar2 = px.bar(category_df, x='Avg_Replacement_Frequency', y='Category',
                                      title='Top Categories by Average Replacement Frequency',
                                      labels={'Category': 'Product Category',
                                              'Avg_Replacement_Frequency': 'Avg Replacement Frequency'},
                                      orientation='h',
                                      text='Avg_Replacement_Frequency')

                    fig_bar2.update_traces(texttemplate='%{text:.2f}', textposition='outside')

                    figures = [fig_bar, fig_pie, fig_bar2]
                    return figures

                elif drop == "TOYS":
                    df = pd.read_sql_query("""SELECT p.Product_ID,p.Product_Description,p.Category, ROUND(AVG(r.Replacement_Order_Frequency), 2) AS Avg_Replacement_Frequency
                     FROM retail_panopticon.replacementsAndDefects r
                    JOIN retail_panopticon.transactions t ON r.Transaction_ID = t.Transaction_ID
                    JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID
                    WHERE p.Category='Toys'
                    GROUP BY p.Product_ID,p.Product_Description,p.Category
                    ORDER BY Avg_Replacement_Frequency DESC LIMIT 10;""", conn)

                    fig_bar = px.bar(df, x='Product_Description', y='Avg_Replacement_Frequency',
                                 title='Top 10 Products by Average Replacement Frequency',
                                 labels={'Product_Description': 'Product',
                                         'Avg_Replacement_Frequency': 'Avg Replacement Frequency'},
                                 text='Avg_Replacement_Frequency')

                    fig_bar.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                    fig_bar.update_layout(xaxis_tickangle=-45)

                    pie_df = df.groupby('Category')['Avg_Replacement_Frequency'].sum().reset_index()

                    # Plotting
                    fig_pie = px.pie(pie_df, values='Avg_Replacement_Frequency', names='Category',
                                     title='Distribution of Replacement Requests by Product Category',
                                     labels={'Category': 'Product Category',
                                             'Avg_Replacement_Frequency': 'Total Replacement Frequency'})

                    category_df = df.groupby('Category')[
                        'Avg_Replacement_Frequency'].mean().reset_index().sort_values(
                        by='Avg_Replacement_Frequency', ascending=False)

                    # Plotting
                    fig_bar2 = px.bar(category_df, x='Avg_Replacement_Frequency', y='Category',
                                      title='Top Categories by Average Replacement Frequency',
                                      labels={'Category': 'Product Category',
                                              'Avg_Replacement_Frequency': 'Avg Replacement Frequency'},
                                      orientation='h',
                                      text='Avg_Replacement_Frequency')

                    fig_bar2.update_traces(texttemplate='%{text:.2f}', textposition='outside')

                    figures = [fig_bar, fig_pie, fig_bar2]
                    return figures
                elif drop == "ELECTRONICS":
                    df = pd.read_sql_query("""SELECT p.Product_ID,p.Product_Description,p.Category, ROUND(AVG(r.Replacement_Order_Frequency), 2) AS Avg_Replacement_Frequency
                     FROM retail_panopticon.replacementsAndDefects r
                    JOIN retail_panopticon.transactions t ON r.Transaction_ID = t.Transaction_ID
                    JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID
                    WHERE p.Category='Electronics'
                    GROUP BY p.Product_ID,p.Product_Description,p.Category
                    ORDER BY Avg_Replacement_Frequency DESC LIMIT 10;""", conn)

                    fig_bar = px.bar(df, x='Product_Description', y='Avg_Replacement_Frequency',
                                     title='Top 10 Products by Average Replacement Frequency',
                                     labels={'Product_Description': 'Product',
                                             'Avg_Replacement_Frequency': 'Avg Replacement Frequency'},
                                     text='Avg_Replacement_Frequency')

                    fig_bar.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                    fig_bar.update_layout(xaxis_tickangle=-45)

                    pie_df = df.groupby('Category')['Avg_Replacement_Frequency'].sum().reset_index()

                    # Plotting
                    fig_pie = px.pie(pie_df, values='Avg_Replacement_Frequency', names='Category',
                                     title='Distribution of Replacement Requests by Product Category',
                                     labels={'Category': 'Product Category',
                                             'Avg_Replacement_Frequency': 'Total Replacement Frequency'})

                    category_df = df.groupby('Category')[
                        'Avg_Replacement_Frequency'].mean().reset_index().sort_values(
                        by='Avg_Replacement_Frequency', ascending=False)

                    # Plotting
                    fig_bar2 = px.bar(category_df, x='Avg_Replacement_Frequency', y='Category',
                                      title='Top Categories by Average Replacement Frequency',
                                      labels={'Category': 'Product Category',
                                              'Avg_Replacement_Frequency': 'Avg Replacement Frequency'},
                                      orientation='h',
                                      text='Avg_Replacement_Frequency')

                    fig_bar2.update_traces(texttemplate='%{text:.2f}', textposition='outside')

                    figures = [fig_bar, fig_pie, fig_bar2]
                    return figures
            # Question 3
            elif query == "How does the order fulfillment rate differ across various product categories?":
                df = pd.read_sql_query("""SELECT Product_Category,
                    ROUND(AVG(p.Fulfillment_Rate_Category), 2) AS Avg_Fulfillment_Rate
                    FROM retail_panopticon.productAndRegionPerformance p
                    GROUP BY Product_Category
                    ORDER BY Avg_Fulfillment_Rate DESC;""", conn)

                fig_bar = px.bar(df,
                                 x='Avg_Fulfillment_Rate',
                                 y='Product_Category',
                                 title="Average Fulfillment Rate by Product Category",
                                 labels={'Product_Category': 'Product Category',
                                         'Avg_Fulfillment_Rate': 'Average Fulfillment Rate'},
                                 color='Avg_Fulfillment_Rate',
                                 orientation='h',
                                 height=600)

                fig = go.Figure(data=go.Heatmap(
                    z=df['Avg_Fulfillment_Rate'],
                    x=df['Product_Category'],
                    y=['Fulfillment Rate'],
                    colorscale='Viridis'))

                fig.update_layout(
                    title="Heatmap of Fulfillment Rate by Product Category",
                    xaxis_title="Product Category",
                    yaxis_title="",
                    height=400
                )
                figures = [fig_bar, fig]
                return figures

            # Warehouse App
            elif query == "How efficient are our warehouse operations in terms of throughput and processing time for inbound and outbound shipments for products which have a low stock availability (<10)?":
                if drop=="SUPP078":
                    df = pd.read_sql_query("""SELECT
                       p.Product_ID,
                       p.Product_Description,
                       w.Supplier_ID,
                       w.Warehouse_Throughput,
                       w.Inbound_Processing_Time,
                       w.Outbound_Processing_Time,
                       w.Warehouse_Operations_Efficiency_Metric
                    FROM retail_panopticon.productInformation p
                    JOIN retail_panopticon.warehouseThroughput w ON p.Supplier_ID = w.Supplier_ID
                    WHERE p.Stock_Availability < 10 AND w.Supplier_ID='SUPP078'
                    GROUP BY p.Product_Description, w.Supplier_ID,w.Warehouse_Throughput,w.Inbound_Processing_Time,
                     w.Outbound_Processing_Time,w.Warehouse_Operations_Efficiency_Metric
                    ORDER BY w.Warehouse_Operations_Efficiency_Metric DESC;""", conn)

                    # Assuming 'df' is your dataframe with relevant columns
                    fig = px.bar(df,
                                 x='Product_ID',
                                 y='Warehouse_Throughput',
                                 title="Warehouse Throughput by Product",
                                 labels={'Product_ID': 'Product', 'Warehouse_Throughput': 'Throughput'},
                                 color='Warehouse_Throughput',
                                 hover_data=['Product_Description'])

                    fig.update_layout(xaxis_tickangle=-45, height=600)
                    fig1 = go.Figure()

                    fig1.add_trace(go.Scatter(x=df['Product_Description'],
                                              y=df['Warehouse_Throughput'],
                                              mode='lines+markers',
                                              name='Warehouse Throughput',
                                              line=dict(dash='solid',
                                                        color='blue')))  # Blue color for Warehouse Throughput

                    fig1.update_layout(
                        title="Warehouse Throughput by Product",
                        xaxis_title="Product",
                        yaxis_title="Warehouse Throughput",
                        height=600
                    )

                    fig1.update_xaxes(tickangle=-45)

                    # Figure 2: Efficiency Metric with a specific color (e.g., green)
                    fig2 = go.Figure()

                    fig2.add_trace(go.Scatter(x=df['Product_Description'],
                                              y=df['Warehouse_Operations_Efficiency_Metric'],
                                              mode='lines+markers',
                                              name='Efficiency Metric',
                                              line=dict(dash='solid',
                                                        color='green')))  # Green color for Efficiency Metric

                    fig2.update_layout(
                        title="Efficiency Metric by Product",
                        xaxis_title="Product",
                        yaxis_title="Efficiency Metric",
                        height=600
                    )

                    fig2.update_xaxes(tickangle=-45)
                    figures = [fig, fig1, fig2]
                    return figures

                if drop == "SUPP083":
                    df = pd.read_sql_query("""SELECT
                       p.Product_ID,
                       p.Product_Description,
                       w.Supplier_ID,
                       w.Warehouse_Throughput,
                       w.Inbound_Processing_Time,
                       w.Outbound_Processing_Time,
                       w.Warehouse_Operations_Efficiency_Metric
                    FROM retail_panopticon.productInformation p
                    JOIN retail_panopticon.warehouseThroughput w ON p.Supplier_ID = w.Supplier_ID
                    WHERE p.Stock_Availability < 10 AND w.Supplier_ID='SUPP083'
                    GROUP BY p.Product_Description, w.Supplier_ID,w.Warehouse_Throughput,w.Inbound_Processing_Time,
                     w.Outbound_Processing_Time,w.Warehouse_Operations_Efficiency_Metric
                    ORDER BY w.Warehouse_Operations_Efficiency_Metric DESC;""", conn)

                    # Assuming 'df' is your dataframe with relevant columns
                    fig = px.bar(df,
                                 x='Product_ID',
                                 y='Warehouse_Throughput',
                                 title="Warehouse Throughput by Product",
                                 labels={'Product_ID': 'Product', 'Warehouse_Throughput': 'Throughput'},
                                 color='Warehouse_Throughput',
                                 hover_data=['Product_Description'])
                    fig.update_layout(xaxis_tickangle=-45, height=600)
                    fig1 = go.Figure()
                    fig1.add_trace(go.Scatter(x=df['Product_Description'],
                                              y=df['Warehouse_Throughput'],
                                              mode='lines+markers',
                                              name='Warehouse Throughput',
                                              line=dict(dash='solid',color='blue')))  # Blue color for Warehouse Throughput

                    fig1.update_layout(title="Warehouse Throughput by Product",xaxis_title="Product",
                        yaxis_title="Warehouse Throughput",
                        height=600)
                    fig1.update_xaxes(tickangle=-45)

                    # Figure 2: Efficiency Metric with a specific color (e.g., green)
                    fig2 = go.Figure()
                    fig2.add_trace(go.Scatter(x=df['Product_Description'],
                                              y=df['Warehouse_Operations_Efficiency_Metric'],
                                              mode='lines+markers',
                                              name='Efficiency Metric',
                                              line=dict(dash='solid',
                                              color='green')))  # Green color for Efficiency Metric
                    fig2.update_layout(title="Efficiency Metric by Product",
                        xaxis_title="Product",
                        yaxis_title="Efficiency Metric",
                        height=600)
                    fig2.update_xaxes(tickangle=-45)

                    figures = [fig, fig1, fig2]
                    return figures

                if drop == "SUPP066":
                    df = pd.read_sql_query("""SELECT
                       p.Product_ID,
                       p.Product_Description,
                       w.Supplier_ID,
                       w.Warehouse_Throughput,
                       w.Inbound_Processing_Time,
                       w.Outbound_Processing_Time,
                       w.Warehouse_Operations_Efficiency_Metric
                    FROM retail_panopticon.productInformation p
                    JOIN retail_panopticon.warehouseThroughput w ON p.Supplier_ID = w.Supplier_ID
                    WHERE p.Stock_Availability < 10 AND w.Supplier_ID='SUPP066'
                    GROUP BY p.Product_Description, w.Supplier_ID,w.Warehouse_Throughput,w.Inbound_Processing_Time,
                     w.Outbound_Processing_Time,w.Warehouse_Operations_Efficiency_Metric
                    ORDER BY w.Warehouse_Operations_Efficiency_Metric DESC;""", conn)

                    # Assuming 'df' is your dataframe with relevant columns
                    fig = px.bar(df,
                                 x='Product_ID',
                                 y='Warehouse_Throughput',
                                 title="Warehouse Throughput by Product",
                                 labels={'Product_ID': 'Product', 'Warehouse_Throughput': 'Throughput'},
                                 color='Warehouse_Throughput',
                                 hover_data=['Product_Description'])

                    fig.update_layout(xaxis_tickangle=-45, height=600)
                    fig1 = go.Figure()

                    fig1.add_trace(go.Scatter(x=df['Product_Description'],
                                              y=df['Warehouse_Throughput'],
                                              mode='lines+markers',
                                              name='Warehouse Throughput',
                                              line=dict(dash='solid',
                                                        color='blue')))  # Blue color for Warehouse Throughput

                    fig1.update_layout(
                        title="Warehouse Throughput by Product",
                        xaxis_title="Product",
                        yaxis_title="Warehouse Throughput",
                        height=600
                    )

                    fig1.update_xaxes(tickangle=-45)

                    # Figure 2: Efficiency Metric with a specific color (e.g., green)
                    fig2 = go.Figure()

                    fig2.add_trace(go.Scatter(x=df['Product_Description'],
                                              y=df['Warehouse_Operations_Efficiency_Metric'],
                                              mode='lines+markers',
                                              name='Efficiency Metric',
                                              line=dict(dash='solid',
                                                        color='green')))  # Green color for Efficiency Metric

                    fig2.update_layout(
                        title="Efficiency Metric by Product",
                        xaxis_title="Product",
                        yaxis_title="Efficiency Metric",
                        height=600
                    )

                    fig2.update_xaxes(tickangle=-45)
                    figures = [fig, fig1, fig2]
                    return figures

                if drop == "SUPP073":
                    df = pd.read_sql_query("""SELECT
                       p.Product_ID,
                       p.Product_Description,
                       w.Supplier_ID,
                       w.Warehouse_Throughput,
                       w.Inbound_Processing_Time,
                       w.Outbound_Processing_Time,
                       w.Warehouse_Operations_Efficiency_Metric
                    FROM retail_panopticon.productInformation p
                    JOIN retail_panopticon.warehouseThroughput w ON p.Supplier_ID = w.Supplier_ID
                    WHERE p.Stock_Availability < 10 AND w.Supplier_ID='SUPP073'
                    GROUP BY p.Product_Description, w.Supplier_ID,w.Warehouse_Throughput,w.Inbound_Processing_Time,
                     w.Outbound_Processing_Time,w.Warehouse_Operations_Efficiency_Metric
                    ORDER BY w.Warehouse_Operations_Efficiency_Metric DESC;""", conn)

                    # Assuming 'df' is your dataframe with relevant columns
                    fig = px.bar(df,
                                 x='Product_ID',
                                 y='Warehouse_Throughput',
                                 title="Warehouse Throughput by Product",
                                 labels={'Product_ID': 'Product', 'Warehouse_Throughput': 'Throughput'},
                                 color='Warehouse_Throughput',
                                 hover_data=['Product_Description'])

                    fig.update_layout(xaxis_tickangle=-45, height=600)
                    fig1 = go.Figure()

                    fig1.add_trace(go.Scatter(x=df['Product_Description'],
                                              y=df['Warehouse_Throughput'],
                                              mode='lines+markers',
                                              name='Warehouse Throughput',
                                              line=dict(dash='solid',
                                                        color='blue')))  # Blue color for Warehouse Throughput

                    fig1.update_layout(
                        title="Warehouse Throughput by Product",
                        xaxis_title="Product",
                        yaxis_title="Warehouse Throughput",
                        height=600
                    )

                    fig1.update_xaxes(tickangle=-45)

                    # Figure 2: Efficiency Metric with a specific color (e.g., green)
                    fig2 = go.Figure()

                    fig2.add_trace(go.Scatter(x=df['Product_Description'],
                                              y=df['Warehouse_Operations_Efficiency_Metric'],
                                              mode='lines+markers',
                                              name='Efficiency Metric',
                                              line=dict(dash='solid',
                                                        color='green')))  # Green color for Efficiency Metric

                    fig2.update_layout(
                        title="Efficiency Metric by Product",
                        xaxis_title="Product",
                        yaxis_title="Efficiency Metric",
                        height=600
                    )

                    fig2.update_xaxes(tickangle=-45)
                    figures = [fig, fig1, fig2]
                    return figures

            elif query == "Which product categories are the most likely to suffer from shipping delays and what are the primary causes of these delays?":
                if drop == "SUPP078":
                    df = pd.read_sql_query("""SELECT p.Category, s.Reason_Late_Shipment,
                    COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments
                    FROM retail_panopticon.transactions t
                    JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID
                    JOIN retail_panopticon.shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID
                    WHERE p.Supplier_ID='SUPP078'
                    GROUP BY p.Category, s.Reason_Late_Shipment
                    HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0
                    ORDER BY Total_Late_Shipments DESC;""", conn)

                    fig_bar1 = px.bar(df,
                                 x='Category',
                                 y='Total_Late_Shipments',
                                 color='Category',
                                 title='Total Late Shipments by Product Category',
                                 labels={'Category': 'Product Category',
                                         'Total_Late_Shipments': 'Total Late Shipments'},
                                 color_continuous_scale='Blues')

                    fig_bar1.update_layout(xaxis_tickangle=-45, height=600)

                    reason_totals = df.groupby('Reason_Late_Shipment').sum().reset_index()
                    fig_pie = px.pie(reason_totals,
                                 names='Reason_Late_Shipment',
                                 values='Total_Late_Shipments',
                                 title='Distribution of Late Shipments by Cause',
                                 labels={'Reason_Late_Shipment': 'Reason for Late Shipment',
                                         'Total_Late_Shipments': 'Total Late Shipments'})

                    fig_pie.update_layout(height=600)
                    figures = [fig_bar1, fig_pie]
                    return figures

                if drop == "SUPP083":
                    df = pd.read_sql_query("""SELECT p.Category, s.Reason_Late_Shipment,
                                        COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments
                                        FROM retail_panopticon.transactions t
                                        JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID
                                        JOIN retail_panopticon.shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID
                                        WHERE p.Supplier_ID='SUPP083'
                                        GROUP BY p.Category, s.Reason_Late_Shipment
                                        HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0
                                        ORDER BY Total_Late_Shipments DESC;""", conn)

                    fig_bar1 = px.bar(df,
                                      x='Category',
                                      y='Total_Late_Shipments',
                                      color='Category',
                                      title='Total Late Shipments by Product Category',
                                      labels={'Category': 'Product Category',
                                              'Total_Late_Shipments': 'Total Late Shipments'},
                                      color_continuous_scale='Blues')

                    fig_bar1.update_layout(xaxis_tickangle=-45, height=600)

                    reason_totals = df.groupby('Reason_Late_Shipment').sum().reset_index()
                    fig_pie = px.pie(reason_totals,
                                     names='Reason_Late_Shipment',
                                     values='Total_Late_Shipments',
                                     title='Distribution of Late Shipments by Cause',
                                     labels={'Reason_Late_Shipment': 'Reason for Late Shipment',
                                             'Total_Late_Shipments': 'Total Late Shipments'})

                    fig_pie.update_layout(height=600)
                    figures = [fig_bar1, fig_pie]
                    return figures

                if drop == "SUPP066":
                    df = pd.read_sql_query("""SELECT p.Category, s.Reason_Late_Shipment,
                                        COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments
                                        FROM retail_panopticon.transactions t
                                        JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID
                                        JOIN retail_panopticon.shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID
                                        WHERE p.Supplier_ID='SUPP066'
                                        GROUP BY p.Category, s.Reason_Late_Shipment
                                        HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0
                                        ORDER BY Total_Late_Shipments DESC;""", conn)

                    fig_bar1 = px.bar(df,
                                      x='Category',
                                      y='Total_Late_Shipments',
                                      color='Category',
                                      title='Total Late Shipments by Product Category',
                                      labels={'Category': 'Product Category',
                                              'Total_Late_Shipments': 'Total Late Shipments'},
                                      color_continuous_scale='Blues')

                    fig_bar1.update_layout(xaxis_tickangle=-45, height=600)

                    reason_totals = df.groupby('Reason_Late_Shipment').sum().reset_index()
                    fig_pie = px.pie(reason_totals,
                                     names='Reason_Late_Shipment',
                                     values='Total_Late_Shipments',
                                     title='Distribution of Late Shipments by Cause',
                                     labels={'Reason_Late_Shipment': 'Reason for Late Shipment',
                                             'Total_Late_Shipments': 'Total Late Shipments'})

                    fig_pie.update_layout(height=600)
                    figures = [fig_bar1, fig_pie]
                    return figures

                if drop == "SUPP073":
                    df = pd.read_sql_query("""SELECT p.Category, s.Reason_Late_Shipment,
                                        COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments
                                        FROM retail_panopticon.transactions t
                                        JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID
                                        JOIN retail_panopticon.shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID
                                        WHERE p.Supplier_ID='SUPP073'
                                        GROUP BY p.Category, s.Reason_Late_Shipment
                                        HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0
                                        ORDER BY Total_Late_Shipments DESC;""", conn)

                    fig_bar1 = px.bar(df,
                                      x='Category',
                                      y='Total_Late_Shipments',
                                      color='Category',
                                      title='Total Late Shipments by Product Category',
                                      labels={'Category': 'Product Category',
                                              'Total_Late_Shipments': 'Total Late Shipments'},
                                      color_continuous_scale='Blues')

                    fig_bar1.update_layout(xaxis_tickangle=-45, height=600)

                    reason_totals = df.groupby('Reason_Late_Shipment').sum().reset_index()
                    fig_pie = px.pie(reason_totals,
                                     names='Reason_Late_Shipment',
                                     values='Total_Late_Shipments',
                                     title='Distribution of Late Shipments by Cause',
                                     labels={'Reason_Late_Shipment': 'Reason for Late Shipment',
                                             'Total_Late_Shipments': 'Total Late Shipments'})

                    fig_pie.update_layout(height=600)
                    figures = [fig_bar1, fig_pie]
                    return figures

st.set_page_config(layout='wide', initial_sidebar_state='collapsed')

set_custom_css()

# with open(r'tellmore_logo.svg', 'r') as image:
#     image_data = image.read()
# st.logo(image=image_data)

col1, col2 = st.columns([4, 1])

with col2:
    selected_option = st.selectbox("", personas, key='super_admin_selectbox')

if selected_option == "Select a Persona":
    st.title("SUPER ADMIN")
else:
    if selected_option == "INVENTORY OPS":
        selected_persona = "store"
        ops_selection = st.sidebar.radio("Toggle View", ["INVENTORY OPS", "SIMULATE INVENTORY MANAGER"])
        if ops_selection == "INVENTORY OPS":
            store_questions = {
                "How do we optimize inventory levels and replenishment for high-stockout products to match sales and reduce stockouts?":
                    {
                        "sql": "SELECT p.Product_ID, p.Description, SUM(t.Quantity) AS Total_Sales, iv.Average_Monthly_Inventory_Level, iv.Replenishment_Lead_Time, iv.Backorder_Rate, iv.StockOut_Incidents FROM products AS p JOIN transactions AS t ON p.Product_ID = t.Product_ID JOIN inventoryMetrics AS iv ON p.Product_ID = iv.Product_ID WHERE iv.StockOut_Incidents > 7 GROUP BY p.Product_ID ORDER BY iv.Replenishment_Lead_Time, iv.StockOut_Incidents;",
                        "nlr": "To manage inventory levels and replenishment times for products with frequent stockouts, we need to consider the following factors:\n1. **Total Sales**: We should analyze the total sales of each product to understand the demand and popularity. This will help us determine the appropriate inventory levels and replenishment quantities.\n2. **Average Monthly Inventory Level**: By calculating the average monthly inventory level, we can identify the average stock available for each product. This will help us determine if the current inventory levels are sufficient to meet demand or if adjustments need to be made.\n3. **Replenishment Lead Time**: The replenishment lead time refers to the time it takes to restock inventory once an order is placed. By analyzing the lead time, we can ensure that new stock arrives in a timely manner to minimize stockouts and backorders.\n4. **Backorder Rate**: The backorder rate indicates the percentage of orders that cannot be fulfilled immediately due to stockouts. By monitoring the backorder rate, we can identify products that frequently experience stockouts and take appropriate actions to minimize them.\n5. **Stockout Incidents**: The number of stockout incidents provides insight into the frequency of stockouts for each product. By analyzing this data, we can identify products that require better inventory management to minimize stockouts and backorders.\nBased on the data provided, we can analyze the inventory levels, replenishment lead times, backorder rates, and stockout incidents for each product. This analysis will help us identify products that require adjustments in inventory management strategies to align with sales volumes and minimize stockouts and backorders."
                    },
                "Which high-sales products have low turnover rates, and what are the lead times and safety stock levels for these products?":
                    {
                        "sql": "SELECT p.Product_ID, p.Description, COUNT(t.Transaction_ID) AS Number_of_Transactions, SUM(t.Quantity) AS Total_Sales, iv.Inventory_Monthly_Turnover_Rate, iv.Safety_Stock_Levels, iv.Lead_Time, iv.Replenishment_Lead_Time FROM products AS p JOIN transactions AS t ON p.Product_ID = t.Product_ID JOIN inventoryMetrics AS iv ON p.Product_ID = iv.Product_ID WHERE iv.Inventory_Monthly_Turnover_Rate < 15 GROUP BY p.Product_ID HAVING SUM(t.Quantity) > 750 ORDER BY iv.Inventory_Monthly_Turnover_Rate DESC, iv.Lead_Time;",
                        "nlr": "To identify products with high sales but low turnover rates, we analyze their transaction counts and total sales. Here are some examples:\n\n1. Eggs (Food) - High sales across multiple IDs with varying lead times and safety stock levels suggesting different replenishment strategies.\n2. Butter (Food) - Consistent sales performance with moderate safety stock, reflecting efficient inventory management.\n3. Milk (Food) - Strong sales performance, accompanied by significant inventory management that ensures availability despite high demand.\n\nThese products exhibit varied lead times and safety stock levels, which are crucial for maintaining supply chain efficiency. For instance, lead times range from 1.13 to 29.97 days, and safety stock levels from 25.91 to 141.45 units, indicating tailored inventory strategies to mitigate stockouts and ensure steady supply."
                    },
                "For products with frequent stockouts, what are their replenishment accuracy rates, and how do these relate to their sales volumes?":
                    {
                        "sql": "SELECT  p.Product_ID, p.Description, SUM(t.Quantity) AS Total_Sales, iv.Replenishment_Accuracy, iv.Backorder_Rate, iv.StockOut_Incidents, iv.Fill_Rate FROM products AS p JOIN transactions AS t ON p.Product_ID = t.Product_ID JOIN inventoryMetrics AS iv ON p.Product_ID = iv.Product_ID WHERE iv.StockOut_Incidents > 4 GROUP BY p.Product_ID ORDER BY iv.Replenishment_Accuracy DESC, Total_Sales DESC;",
                        "nlr": "To determine the correlation between replenishment accuracy and sales volumes for products with frequent stockouts, we examine their sales performance and inventory metrics. The following products have shown significant stockout incidents, influencing their inventory strategies:\n\n1. Milk (Food) - High replenishment accuracy with frequent stockouts, indicating a dynamic response to fluctuating demand.\n2. Board Game (Toys), Laptop (Electronics), Dress (Clothing), and Sofa (Furniture) - These products also exhibit high replenishment accuracies but have faced several stockout incidents, suggesting a need for better demand forecasting or faster supply chain reactions.\n\nFurther analysis of these products shows varied replenishment accuracy rates closely tied to their sales figures, highlighting the importance of precise inventory management in maintaining sales momentum and customer satisfaction in the face of supply challenges."
                    },
            }
            st.title("INVENTORY OPS")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            corporate_appIM(selected_persona, store_questions)
        elif ops_selection == "SIMULATE INVENTORY MANAGER":
            stores = [
                "SELECT INVENTORY",
                "INVENTORY FOR TOYS",
                "INVENTORY FOR CLOTHING",
                "INVENTORY FOR FURNITURE"
            ]
            st.title("SIMULATE INVENTORY MANAGER")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            management_appIM(selected_persona, stores)

    elif selected_option == "STORE OPS":

        selected_persona = "store"
        ops_selection = st.sidebar.radio("Toggle View", ["STORE OPS", "SIMULATE STORE MANAGER"])
        if ops_selection == "STORE OPS":
            store_questions = {
                "Give a daily breakdown UPT for all product categories for each store during May":
                    {
                        "sql": "SELECT DATE(t.Date) AS Sale_Date, p.Category AS Product_Category, t.Store_ID, ROUND(SUM(t.Quantity) / COUNT(t.Transaction_ID), 2) AS UPT\nFROM retail_panopticon.transactions t\nJOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID\nWHERE t.Date BETWEEN '2024-05-01' AND '2024-05-31'\nGROUP BY DATE(t.Date), p.Category\nORDER BY DATE(t.Date), p.Category;",
                        "nlr": "To provide a daily breakdown of Units Per Transaction (UPT) for all product categories for the month of May, we can group the data by the Sale_Date and calculate the average UPT for each day.\n\nHere is the daily breakdown of UPT for all product categories for the month of May:\n\nMay 1st: 5.83\nMay 2nd: 5.53\nMay 3rd: 5.69\nMay 4th: 5.60\nMay 5th: 5.64\nMay 6th: 4.94\nMay 7th: 5.15\nMay 8th: 5.64\nMay 9th: 5.08\nMay 10th: 5.51\nMay 11th: 5.58\nMay 12th: 5.47\nMay 13th: 5.07\nMay 14th: 5.21\nMay 15th: 5.48\nMay 16th: 5.24\nMay 17th: 5.50\nMay 18th: 5.39\nMay 19th: 5.33\nMay 20th: 5.29\n\nPlease note that the values provided are rounded to two decimal places.",
                    },
                "What was the impact of the promotional discounts offered in May on the weekend vs. weekday sales for all product categories?":
                    {
                        "sql": "SELECT CASE WHEN DAYOFWEEK(S.date) IN (1, 7) THEN 'Weekend' ELSE 'Weekday' END AS day_type, P.Category,SUM(S.Total_Amount) AS total_sales, COUNT(DISTINCT S.Transaction_ID) AS total_transactions, AVG(S.Total_Amount) AS avg_transaction_value FROM transactions S JOIN productInformation P ON S.Product_ID = P.Product_ID WHERE DATE_FORMAT(S.date, '%Y-%m') = '2024-05' GROUP BY day_type, P.Category ORDER BY day_type DESC, total_sales DESC;",
                        "nlr": "Weekdays saw higher total sales and transaction volumes across all product categories, indicating that promotional discounts drove more frequent and larger purchases during the week.\n\nHowever, weekends had a slightly higher average transaction value in categories like Furniture and Electronics, suggesting that while fewer purchases were made, they tended to be more significant.\n\nOverall, the promotions were more effective on weekdays, but the higher weekend transaction values hint at opportunities to target high-value weekend shoppers more effectively.",
                    },
                "Give the total shipments delivered late and the reason for the delay for each product category":
                    {
                        "sql": "SELECT t.Store_ID, p.Category,s.Reason_Late_Shipment, COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments FROM transactions t JOIN productInformation p ON t.Product_ID = p.Product_ID JOIN shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID GROUP BY p.Category, s.Reason_Late_Shipment HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0 ORDER BY Total_Late_Shipments DESC;",
                        "nlr": "The data table provides a detailed breakdown of the total late shipments and reasons for delays across different product categories. For each category, multiple reasons contribute to late deliveries, such as high demand, logistical issues, and customs delays.\n\nThe pie chart visualizes the distribution of reasons for late shipments within each product category. This chart highlights the proportion of each delay reason, providing insight into the most common causes for each category.\n\nThe horizontal bar chart shows the total number of late shipments per product category. This chart helps in understanding which categories experienced the highest volume of late deliveries, guiding efforts to address specific issues and improve shipping efficiency.",
                    },
                "For this store, which products are running low on inventory and have a per unit value greater than 50?":
                    {
                        "sql": """SELECT p.Product_ID, p.Description, p.Unit_Price, p.Stock_Availability
                                  FROM products p
                                  JOIN transactions t ON p.Product_ID = t.Product_ID
                                  WHERE p.Stock_Availability < 10 
                                  AND p.Unit_Price > 50
                                  GROUP BY p.Product_ID, p.Description, p.Unit_Price, p.Stock_Availability
                                  ORDER BY p.Stock_Availability ASC;""",
                        "nlr": "The data table returned shows the products that have low stock availability and a unit price higher than $50. The table includes the product ID, description, unit price, and stock availability for each product. The products listed in the table are headphones, a shirt, a board game, a dress, an action figure, and a jacket. These products have stock availability ranging from 3 to 8, with the lowest stock availability being 3."
                    }
            }
            st.title("STORE OPS")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            corporate_app(selected_persona, store_questions)
        elif ops_selection == "SIMULATE STORE MANAGER":
            stores = [
                "SELECT STORE",
                "WATER TOWER PLACE",
                "RIVERFRONT PLAZA",
                "WESTFIELD WHEATON"
            ]
            st.title("SIMULATE STORE MANAGER")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            management_app(selected_persona, stores)

    elif selected_option == "LOSS PREVENTION OPS":

        selected_persona = "store"

        ops_selection = st.sidebar.radio("Toggle View", ["LOSS PREVENTION OPS", "SIMULATE LOSS PREVENTION MANAGER"])

        if ops_selection == "LOSS PREVENTION OPS":

            store_questions = {

                "What are the detailed loss prevention measures for products in departments with a shrinkage rate higher than a specific threshold?":

                    {

                        "sql": "SELECT slp.Product_ID, p.Description, slp.Department, slp.Shrinkage_Rate, slp.Shrinkage_Value, slp.Loss_Prevention_Measures FROM shrinkageAndLossPrevention AS slp JOIN products AS p ON slp.Product_ID = p.Product_ID WHERE slp.Shrinkage_Rate > 4 ORDER BY slp.Shrinkage_Rate DESC;",

                        "nlr": "The detailed loss prevention measures for products in departments with a shrinkage rate higher than a specific threshold are as follows:\n\n1. Toys Department:\n - Vendor Audits: Conduct regular audits of toy vendors to ensure compliance with security measures and identify any potential areas of shrinkage.\n\n2. Electronics Department:\n - Enhanced Security: Implement additional security measures such as surveillance cameras, electronic article surveillance (EAS) systems, and access control systems to prevent theft and reduce shrinkage.\n - Inventory Management Systems: Implement advanced inventory management systems to track and monitor electronic products, ensuring accurate stock levels and reducing the risk of loss.\n\n3. Clothing Department:\n - Enhanced Security: Implement additional security measures such as surveillance cameras, electronic article surveillance (EAS) systems, and access control systems to prevent theft and reduce shrinkage.\n - Inventory Management Systems: Implement advanced inventory management systems to track and monitor clothing products, ensuring accurate stock levels and reducing the risk of loss.\n - Customer Awareness Programs: Educate customers about the importance of preventing theft and encourage them to report any suspicious activities.\n\n4. Food Department:\n - Customer Awareness Programs: Educate customers about the importance of preventing theft and encourage them to report any suspicious activities.\n - Vendor Audits: Conduct regular audits of food vendors to ensure compliance with security measures and identify any potential areas of shrinkage.\n - Inventory Management Systems: Implement advanced inventory management systems to track and monitor food products, ensuring accurate stock levels and reducing the risk of loss.\n\n5. Furniture Department:\n - Employee Training: Provide comprehensive training to employees on loss prevention strategies, including identifying and reporting suspicious activities.\n - Vendor Audits: Conduct regular audits of furniture vendors to ensure compliance with security measures and identify any potential areas of shrinkage.\n - Inventory Management Systems: Implement advanced inventory management systems to track and monitor furniture products, ensuring accurate stock levels and reducing the risk of loss.\n\nNote: The specific loss prevention measures may vary depending on the company's policies and industry standards."

                    },

                "How do high shrinkage rates and inventory management practices affect sales volumes for products in rural store locations?":

                    {

                        "sql": "SELECT p.Product_ID, p.Description, ss.Store_Location_Type, SUM(t.Quantity) AS Total_Sales, slp.Shrinkage_Rate, slp.Loss_Prevention_Measures, iv.Average_Monthly_Inventory_Level, iv.Replenishment_Lead_Time FROM products AS p JOIN transactions AS t ON p.Product_ID = t.Product_ID JOIN shrinkageAndLossPrevention AS slp ON p.Product_ID = slp.Product_ID JOIN inventoryMetrics AS iv ON p.Product_ID = iv.Product_ID JOIN shrinkageStores AS ss ON t.Store_ID = ss.Store_ID WHERE slp.Shrinkage_Rate > 4 AND ss.Store_Location_Type IN ('rural') GROUP BY p.Product_ID, ss.Store_Location_Type ORDER BY slp.Shrinkage_Rate DESC, iv.Replenishment_Lead_Time;",

                        "nlr": "Based on the given data, high shrinkage rates and inventory management practices can have the following effects on sales volumes for products in rural store locations:\n\n1. Shrinkage Rate: The higher the shrinkage rate, the more products are lost or stolen. This can lead to a decrease in sales volumes as there may be fewer products available for customers to purchase.\n\n2. Loss Prevention Measures: The effectiveness of loss prevention measures, such as enhanced security, vendor audits, and customer awareness programs, can impact sales volumes. If these measures are successful in reducing shrinkage, it can result in higher sales volumes as more products are available for customers.\n\n3. Average Monthly Inventory Level: The average monthly inventory level can affect sales volumes. If the inventory level is low due to high shrinkage rates or poor inventory management practices, it can lead to lower sales volumes as there may be limited product availability.\n\n4. Replenishment Lead Time: The time it takes to replenish inventory can also impact sales volumes. If the lead time is long, it can result in stockouts and lower sales volumes. On the other hand, if the lead time is short, it can ensure a consistent supply of products and potentially increase sales volumes.\n\nIn summary, high shrinkage rates and poor inventory management practices can negatively affect sales volumes for products in rural store locations by reducing product availability and potentially leading to stockouts. Implementing effective loss prevention measures and improving inventory management practices can help mitigate these negative effects and potentially increase sales volumes."

                    }

            }

            st.title("LOSS PREVENTION OPS")

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

            loss_prevention_app(selected_persona, store_questions)

        elif ops_selection == "SIMULATE LOSS PREVENTION MANAGER":

            categories = [

                "SELECT DEPARTMENT",

                "FOOD",

                "FURNITURE",

                "CLOTHING",

                "TOYS",

                "ELECTRONICS"

            ]

            st.title("SIMULATE LOSS PREVENTION MANAGER")

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

            loss_prevention_app_management_app(selected_persona, categories)

    elif selected_option == "MARKETING OPS":
        selected_persona = "store"
        ops_selection = st.sidebar.radio("Toggle View", ["MARKETING OPS", "SIMULATE MARKETING MANAGER"])
        if ops_selection == "MARKETING OPS":
            store_questions = {
                "How effective are different marketing strategies across product categories in terms of sales volume, inventory management, and the occurrence of stockouts during promotional campaigns?":
                    {
                        "sql": "SELECT s.Store_ID, p.Category, pd.Marketing_Strategy, COUNT(pd.Promotional_Activity_Date) AS Number_of_Marketing_Campaigns, SUM(t.Quantity) AS Total_Sales_During_Campaigns, AVG(iv.Average_Monthly_Inventory_Level) AS Avg_Inventory_Level_During_Campaign, MIN(iv.Replenishment_Lead_Time) AS Min_Replenishment_Lead_Time, MAX(iv.StockOut_Incidents) AS Max_StockOuts FROM products AS p JOIN transactions AS t ON p.Product_ID = t.Product_ID JOIN shrinkageStores AS s ON t.Store_ID = s.Store_ID JOIN promotionalAndMarketData AS pd ON p.Product_ID = pd.Product_ID JOIN inventoryMetrics AS iv ON p.Product_ID = iv.Product_ID WHERE t.Date >= pd.Promotional_Activity_Date GROUP BY p.Category, pd.Marketing_Strategy ORDER BY Total_Sales_During_Campaigns DESC, Avg_Inventory_Level_During_Campaign;",
                        "nlr": "To evaluate the effectiveness of different marketing strategies across product categories, we can analyze the provided data. Here are the findings:\n\n1. Sales Volume:\n - Loyalty Programs: Highest sales volume in the Toys category (7586) and Furniture category (4630).\n - Email Marketing: Highest sales volume in the Toys category (7176) and Clothing category (6707).\n - In-Store Promotions: Highest sales volume in the Clothing category (6814) and Furniture category (4546).\n - Social Media Campaign: Highest sales volume in the Food category (6750) and Toys category (6568).\n - Aggressive Advertising: Highest sales volume in the Electronics category (6497) and Clothing category (6510).\n\n2. Inventory Management:\n - Avg Inventory Level During Campaign: The highest average inventory level during campaigns is observed in the Email Marketing strategy for the Toys category (596.445730).\n - Min Replenishment Lead Time: The shortest replenishment lead time is observed in the Email Marketing strategy for the Clothing category (1.23).\n - Max Stockouts: The maximum occurrence of stockouts during campaigns is 9 for all marketing strategies across product categories.\n\nBased on the provided data, we can conclude that the effectiveness of marketing strategies varies across product categories in terms of sales volume and inventory management. However, the occurrence of stockouts during promotional campaigns is consistent across all marketing strategies."
                    },
                "How effective are different types of promotional activities at various urban store locations in terms of sales uplift, customer engagement, and inventory turnover?":
                    {
                        "sql": "SELECT s.Store_ID, s.Store_Location_Type, pd.Promotional_Activity_Type, COUNT(DISTINCT pd.Promotional_Activity_Date) AS Number_of_Promotions, AVG(vm.Sales_Uplift_by_Visual_Merchandising) AS Avg_Sales_Uplift, SUM(t.Quantity) AS Total_Sales, AVG(iv.Inventory_Monthly_Turnover_Rate) AS Avg_Inventory_Turnover, AVG(vm.Customer_Engagement_Metrics_Dwell_Time_Interactions) AS Avg_Customer_Engagement FROM shrinkageStores AS s JOIN transactions AS t ON s.Store_ID = t.Store_ID JOIN promotionalAndMarketData AS pd ON t.Product_ID = pd.Product_ID JOIN visualMerchandising AS vm ON s.Store_ID = vm.Store_ID JOIN inventoryMetrics AS iv ON t.Product_ID = iv.Product_ID WHERE t.Date >= pd.Promotional_Activity_Date AND s.Store_Location_Type IN ('urban') GROUP BY s.Store_ID, pd.Promotional_Activity_Type ORDER BY Avg_Sales_Uplift DESC, Avg_Inventory_Turnover DESC;",
                        "nlr": "To analyze the effectiveness of different types of promotional activities at various urban store locations, we can look at the average sales uplift, average inventory turnover, and average customer engagement for each promotional activity type.\n\nHere are the findings based on the given data:\n\nDiscount:\n- Average sales uplift: 28,670.15\n- Average inventory turnover: 531.12\n- Average customer engagement: 187.92\n\nClearance Sale:\n- Average sales uplift: 28,670.15\n- Average inventory turnover: 425.26\n- Average customer engagement: 187.92\n\nBuy One Get One Free:\n- Average sales uplift: 28,670.15\n- Average inventory turnover: 412.72\n- Average customer engagement: 187.92\n\nSeasonal Sale:\n- Average sales uplift: 28,670.15\n- Average inventory turnover: 381.44\n- Average customer engagement: 187.92\n\nFlash Sale:\n- Average sales uplift: 28,670.15\n- Average inventory turnover: 362.21\n- Average customer engagement: 187.92\n\nBased on this data, it appears that all types of promotional activities have the same average sales uplift, average inventory turnover, and average customer engagement. However, it's important to note that this analysis is based on a small sample size and may not be representative of all urban store locations. Further analysis with a larger dataset is recommended to draw more accurate conclusions."
                    }

            }
            st.title("MARKETING OPS")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            marketing_app(selected_persona, store_questions)
        elif ops_selection == "SIMULATE MARKETING MANAGER":
            stores = [
                "SELECT STORE",
                "WATER TOWER PLACE",
                "RIVERFRONT PLAZA",
                "WESTFIELD WHEATON"
            ]
            st.title("SIMULATE MARKETING MANAGER")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            marketing_management_app(selected_persona, stores)

    elif selected_option == "MERCHANDISING OPS":
        selected_persona = "store"
        ops_selection = st.sidebar.radio("Toggle View", ["MERCHANDISING OPS", "MERCHANDISING MANAGEMENT"])
        if ops_selection == "MERCHANDISING OPS":
            store_questions = {
                "What are the top 3 most common reasons for delays in order fulfillment and which product categories are most severely affected by delays?":
                    {
                        "sql": "SELECT p.Category, o.Delay_Reason, COUNT(o.Transaction_ID) AS Delay_Count FROM retail_panopticon.orderFulfillment o JOIN retail_panopticon.transactions t ON o.Transaction_ID = t.Transaction_ID JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID WHERE o.`On-Time_Fulfillment_Rate` < 100 AND o.Delay_Reason IS NOT NULL AND o.Delay_Reason != '' GROUP BY p.Category, o.Delay_Reason ORDER BY Delay_Count DESC;",
                        "nlr": "The top 3 most common reasons for delays in order fulfillment are:\n\n1. Supplier Delay - 2076 delays\n2. Shipping Problems - 2061 delays\n3. Inventory Issues - 2002 delays\n\nThe product categories most severely affected by delays are:\n\n1. Clothing - 2076 delays\n2. Toys - 2061 delays\n3. Food - 1944 delays",
                    },
                "Which products in this category have the highest rates of replacement requests?":
                    {
                        "sql": "SELECT p.Product_ID,p.Product_Description,p.Category, ROUND(AVG(r.Replacement_Order_Frequency), 2) AS Avg_Replacement_Frequency FROM retail_panopticon.replacementsAndDefects r JOIN retail_panopticon.transactions t ON r.Transaction_ID = t.Transaction_ID JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID GROUP BY p.Product_ID,p.Product_Description,p.Category ORDER BY Avg_Replacement_Frequency DESC LIMIT 10;",
                        "nlr": "The products or categories with the highest rates of replacement requests are:\n\n1. T-Shirt (Clothing) - 3.07\n2. Toy Car (Toys) - 3.07\n3. Board Game (Toys) - 3.06\n4. Headphones (Electronics) - 3.06\n5. Jacket (Clothing) - 3.05\n6. Puzzle (Toys) - 3.05\n7. Tablet (Electronics) - 3.03\n8. Tablet (Electronics) - 3.02",
                    },
                "How does the order fulfillment rate differ across various product categories?":
                    {
                        "sql": "SELECT Product_Category,ROUND(AVG(p.Fulfillment_Rate_Category), 2) AS Avg_Fulfillment_Rate FROM retail_panopticon.productAndRegionPerformance p GROUP BY Product_Category ORDER BY Avg_Fulfillment_Rate DESC;",
                        "nlr": "Based on the given data, the order fulfillment rate differs slightly across various product categories. The furniture category has the highest average fulfillment rate of 90.01%, followed by toys at 89.96%, food at 89.95%, clothing at 89.94%, and electronics at 89.93%.",
                    },
            }
            st.title("MERCHANDISING OPS")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            merchandising_app(selected_persona, store_questions)
        elif ops_selection == "MERCHANDISING MANAGEMENT":
            categories = [
                "SELECT DEPARTMENT",
                "FOOD",
                "FURNITURE",
                "CLOTHING",
                "TOYS",
                "ELECTRONICS"
            ]
            st.title("MERCHANDISING MANAGEMENT")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            merchandising_management_app(selected_persona, categories)

    elif selected_option == "WAREHOUSE OPS":
        selected_persona = "store"
        ops_selection = st.sidebar.radio("Toggle View", ["WAREHOUSE OPS", "WAREHOUSE MANAGEMENT"])
        if ops_selection == "WAREHOUSE OPS":
            store_questions = {
                "How efficient are our warehouse operations in terms of throughput and processing time for inbound and outbound shipments for products which have a low stock availability (<10)?":
                    {
                        "sql": "SELECT p.Product_Description, w.Supplier_ID, w.Warehouse_Throughput, w.Inbound_Processing_Time, w.Outbound_Processing_Time, w.Warehouse_Operations_Efficiency_Metric FROM retail_panopticon.productInformation p JOIN retail_panopticon.warehouseThroughput w ON p.Supplier_ID = w.Supplier_ID WHERE p.Stock_Availability < 10 GROUP BY p.Product_Description, w.Supplier_ID,w.Warehouse_Throughput,w.Inbound_Processing_Time, w.Outbound_Processing_Time,w.Warehouse_Operations_Efficiency_Metric ORDER BY w.Warehouse_Operations_Efficiency_Metric DESC;",
                        "nlr": """To determine the efficiency of warehouse operations for products with low stock availability (<10), we can analyze the data provided.

                The Warehouse_Throughput column represents the number of units processed by the warehouse in a given time period. The higher the value, the more efficient the warehouse is in terms of throughput.
                
                The Inbound_Processing_Time column represents the average time taken to process inbound shipments for a product. The lower the value, the more efficient the warehouse is in terms of processing time for inbound shipments.
                
                The Outbound_Processing_Time column represents the average time taken to process outbound shipments for a product. The lower the value, the more efficient the warehouse is in terms of processing time for outbound shipments.
                
                The Warehouse_Operations_Efficiency_Metric column represents an overall efficiency metric for warehouse operations. The higher the value, the more efficient the warehouse is considered.
                
                Based on the data provided, we can analyze the efficiency of warehouse operations for products with low stock availability (<10):
                
                1. Butter (Food):
                   - Warehouse Throughput: 99508.4
                   - Inbound Processing Time: 3.65
                   - Outbound Processing Time: 4.05
                   - Warehouse Operations Efficiency Metric: 85.55
                
                2. Shirt (Clothing):
                   - Warehouse Throughput: 97408.6
                   - Inbound Processing Time: 3.73
                   - Outbound Processing Time: 4.13
                   - Warehouse Operations Efficiency Metric: 83.74
                
                3. Headphones (Electronics):
                   - Warehouse Throughput: 91906.8
                   - Inbound Processing Time: 3.95
                   - Outbound Processing Time: 4.38
                   - Warehouse Operations Efficiency Metric: 79.01
                
                4. Board Game (Toys):
                   - Warehouse Throughput: 89571.8
                   - Inbound Processing Time: 4.05
                   - Outbound Processing Time: 4.50
                   - Warehouse Operations Efficiency Metric: 77.00
                
                5. T-Shirt (Clothing):
                   - Warehouse Throughput: 82739.2
                   - Inbound Processing Time: 4.39
                   - Outbound Processing Time: 4.87
                   - Warehouse Operations Efficiency Metric: 71.13
                
                6. Jacket (Clothing):
                   - Warehouse Throughput: 74394.6
                   - Inbound Processing Time: 4.88
                   - Outbound Processing Time: 5.41
                   - Warehouse Operations Efficiency Metric: 63.96
                
                7. Eggs (Food):
                   - Warehouse Throughput: 68363.3
                   - Inbound Processing Time: 5.31
                   - Outbound Processing Time: 5.89
                   - Warehouse Operations Efficiency Metric: 58.77
                
                8. Dress (Clothing):
                   - Warehouse Throughput: 58379.3
                   - Inbound Processing Time: 6.22
                   - Outbound Processing Time: 6.90
                   - Warehouse Operations Efficiency Metric: 50.19
                
                9. Action Figure (Toys):
                   - Warehouse Throughput: 57777.7
                   - Inbound Processing Time: 6.28
                   - Outbound Processing Time: 6.97
                   - Warehouse Operations Efficiency Metric: 49.67
                
                10. Action Figure (Toys):
                    - Warehouse Throughput: 34719.7
                    - Inbound Processing Time: 10.45
                    - Outbound Processing Time: 11.60
                    - Warehouse Operations Efficiency Metric: 29.85
                
                11. Bread (Food):
                    - Warehouse Throughput: 22199.5
                    - Inbound Processing Time: 16.35
                    - Outbound Processing Time: 18.14
                    - Warehouse Operations Efficiency Metric: 19.08
                Based on the provided data, the warehouse operations are more efficient in terms of throughput and processing time for products with low stock availability (<10) that have higher values in the Warehouse_Throughput column, lower values in the Inbound_Processing_Time and Outbound_Processing_Time columns, and higher values in the Warehouse_Operations_Efficiency_Metric column.""",
                    },
                "How effectively are we managing our warehouse space to maximize storage capacity and minimize handling costs?":
                    {
                        "sql": "SELECT w.Supplier_ID,w.Warehouse_Space_Utilization,w.Storage_Capacity_Metric,w.Handling_Costs,w.Space_Optimization_Strategies, ROUND(CASE WHEN w.Storage_Capacity_Metric > 0 THEN(w.Warehouse_Space_Utilization / w.Storage_Capacity_Metric) * 100 ELSE 0 END,2) AS Utilization_Percentage, ROUND(CASE WHEN w.Warehouse_Space_Utilization > 0 THEN w.Handling_Costs / w.Warehouse_Space_Utilization ELSE 0 END,2 ) AS Cost_Per_Unit_Space FROM retail_panopticon.warehouseUtilization w ORDER BY  Utilization_Percentage DESC, Cost_Per_Unit_Space ASC;",
                        "nlr": "To determine how effectively we are managing our warehouse space to maximize storage capacity and minimize handling costs, we can analyze the data provided.\n\n1. Warehouse Space Utilization: The average warehouse space utilization is 6.10%, indicating that we are not effectively utilizing the available space.\n\n2. Storage Capacity Metric: The average storage capacity metric is 9,972.07, which suggests that we have sufficient storage capacity.\n\n3. Handling Costs: The average handling costs are $2,256.20, indicating that we have relatively high handling costs.\n\n4. Space Optimization Strategies: The most common space optimization strategies implemented are adopting just-in-time inventory, implementing vertical storage, and reorganizing storage layout.\n\n5. Utilization Percentage: The average utilization percentage is 0.08, which is relatively low.\n\n6. Cost Per Unit Space: The average cost per unit space is $419.62, indicating that we have high costs associated with each unit of space.\n\nBased on this analysis, it appears that we are not effectively managing our warehouse space to maximize storage capacity and minimize handling costs. We have low warehouse space utilization, high handling costs, and relatively high cost per unit space. Implementing more effective space optimization strategies and improving warehouse space utilization can help maximize storage capacity and reduce handling costs.",
                    },
                "Which product categories are the most likely to suffer from shipping delays and what are the primary causes of these delays?":
                    {
                        "sql": "SELECT p.Category, s.Reason_Late_Shipment,COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) AS Total_Late_Shipments FROM retail_panopticon.transactions t JOIN retail_panopticon.productInformation p ON t.Product_ID = p.Product_ID JOIN retail_panopticon.shipmentPerformance s ON t.Transaction_ID = s.Transaction_ID GROUP BY p.Category, s.Reason_Late_Shipment HAVING COUNT(CASE WHEN s.Late_Shipment_Rate > 0 THEN t.Transaction_ID END) > 0 ORDER BY Total_Late_Shipments DESC;",
                        "nlr": "Based on the data provided, the product categories most likely to suffer from shipping delays are:\n\n1. Clothing: This category has the highest total number of late shipments, with reasons including high demand, logistical issues, customs delays, and weather conditions.\n\n2. Toys: This category also experiences a significant number of late shipments, primarily due to high demand, customs delays, weather conditions, and logistical issues.\n\n3. Food: Although food has a slightly lower total number of late shipments compared to clothing and toys, it still faces delays. The primary causes of these delays include weather conditions, logistical issues, high demand, and customs delays.\n\n4. Furniture: This category experiences delays, with reasons including high demand, customs delays, weather conditions, and logistical issues.\n\n5. Electronics: While electronics have a relatively lower total number of late shipments compared to the other categories, they still face delays. The primary causes of these delays include high demand, customs delays, weather conditions, and logistical issues.",
                    },
            }
            st.title("WAREHOUSE OPS")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            warehouse_app(selected_persona, store_questions)
        elif ops_selection == "WAREHOUSE MANAGEMENT":
            categories = [
                "SELECT SUPPLIER",
                "SUPP078",
                "SUPP083",
                "SUPP066",
                "SUPP073"
            ]
            st.title("WAREHOUSE MANAGEMENT")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            warehouse_management_app(selected_persona, categories)
