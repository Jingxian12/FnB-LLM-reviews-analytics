import streamlit as st
import pandas as pd
import plotly.express as px

# Set page configuration to wide layout
st.set_page_config(page_title="F&B Operation Dashboard", layout="wide")

# ==========================================
# 1. LOAD AND CLEAN DATA
# ==========================================
@st.cache_data # Caches data so it doesn't reload on every click
def load_data():
    # Load dataset from github
    df = pd.read_csv("datasets/final_df_llm.csv", encoding="utf-8-sig", on_bad_lines='skip')       
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Could not load CSV file. Make sure it's in datasets/final_df_llm.csv. Error: {e}")
    st.stop()

# ==========================================
# 2. SIDEBAR FILTER CONTROLS
# ==========================================
st.sidebar.header("🏪 Filter Controls")

# Brand Selection Filter
brand_list = ["All Brands"] + list(df['brand'].unique())
selected_brand = st.sidebar.selectbox("Select Brand", brand_list)

# Dynamically filter branch list based on selected brand
if selected_brand == "All Brands":
    # Show all 5 standardized cities
    city_options = list(df['city'].unique())
else:
    # Only show cities that have branches for this specific brand
    city_options = list(df[df['brand'] == selected_brand]['city'].unique())

city_list = ["All Cities"] + city_options
selected_city = st.sidebar.selectbox("Select City / Region", city_list)

# Filter by Brand
if selected_brand == "All Brands":
    filtered_df_step = df
else:
    filtered_df_step = df[df['brand'] == selected_brand]
    
# Filter by City
if selected_city == "All Cities":
    final_df = filtered_df_step
else:
    # If a specific brand AND city are chosen
    final_df = filtered_df_step[filtered_df_step['city'] == selected_city]

# ==========================================
# 3. DASHBOARD HEADER & KPI CARDS
# ==========================================
st.title("📊 F&B Customer Complaints Analytics Dashboard")
st.markdown(f"Showing data for **{selected_brand}** — *{selected_city}*")
st.write("---")

total_reviews = len(final_df)
general_complaint_count = final_df['no_specific_complaint_detected'].sum()

# Calculate percentage of complaints are general/unclassified (without giving a specific reason)
general_pct = (general_complaint_count / total_reviews * 100) if total_reviews > 0 else 0

# Calculate categorized complaints (Reviews that actually hit operational buckets)
categorized_complaint_count = total_reviews - general_complaint_count
categorized_pct = (categorized_complaint_count / total_reviews * 100) if total_reviews > 0 else 0

# 📊 Display Top KPIs (Accurate for a Negative-Only Dataset)
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Negative Reviews", f"{total_reviews:,}")
with col2:
    st.metric("Actionable Operational Complaints", f"{categorized_complaint_count:,}")
    st.caption(f"{categorized_pct:.1f}% of total reviews")
with col3:
    st.metric("Vague / General Complaints", f"{general_complaint_count:,}")
    st.caption(f"{general_pct:.1f}% of total reviews")

st.write("---")

# ==========================================
# 4. MACRO BREAKDOWN (The Percentages Chart)
# ==========================================
st.subheader("⚠️ Operational Complaint Breakdown")
st.write("Percentage of total reviews where an issue was detected (Reviews can have multiple issues).")

# List out our main classification categories
# [key : Label]
categories = {
    "food_quality": "Food Quality",
    "order_accuracy": "Order Accuracy",
    "staff_professionalism": "Staff Professionalism",
    "speed_of_service": "Speed of Service",
    "hygiene_cleanliness": "Hygiene & Cleanliness",
    "facility_equipment": "Facility & Equipment",
    "product_availability": "Product Availability"
}

# Calculate percentages for each detected column
macro_data = []
for key, label in categories.items():
    detected_col = f"{key}_detected"
    if detected_col in final_df.columns:
        total_detected = final_df[detected_col].sum()
        pct = (total_detected / total_reviews * 100) if total_reviews > 0 else 0
        macro_data.append({"Category": label, "Key": key, "Percentage Failure (%)": round(pct, 1), "Count": total_detected})

# Sorted ascending because Plotly plots from bottom to top; this pushes the largest failures to the top 
macro_df = pd.DataFrame(macro_data).sort_values(by="Percentage Failure (%)", ascending=True) 

# Plot Horizontal Chart using Plotly
fig_macro = px.bar(
    macro_df, 
    x="Percentage Failure (%)", 
    y="Category", 
    orientation='h', # horizontal
    text="Percentage Failure (%)",
    color="Percentage Failure (%)",
    color_continuous_scale="Reds"
)
fig_macro.update_layout(coloraxis_showscale=False, height=400)
# Makes the chart responsive, auto-scaling horizontally to perfectly fit any screen size.
st.plotly_chart(fig_macro, use_container_width=True)

# ==========================================
# 5. MICRO DRILL-DOWN (What's inside that X%)
# ==========================================
st.write("---")
st.subheader("🔍 Deep-Dive Root Cause Analyzer")

# Let manager choose which bar they want to explode
drill_choice_label = st.selectbox("Select a complaint category to view specific reasons:", list(categories.values()))
# Find the technical key name for the chosen category label
drill_key = [k for k, v in categories.items() if v == drill_choice_label][0]

detected_col = f"{drill_key}_detected"
issues_col = f"{drill_key}_issues"

# Filter down to rows where this problem actually exists
drill_df = final_df[final_df[detected_col] == 1]

if len(drill_df) == 0:
    st.info(f"🎉 Awesome! There are zero recorded complaints regarding **{drill_choice_label}** for this selection.")

else:
    # Explode the lists into individual item strings
    exploded_issues = drill_df.explode(issues_col)
    
    # Strip any empty spaces and drop null values if any
    exploded_issues[issues_col] = exploded_issues[issues_col].str.strip()
    issue_counts = exploded_issues[issues_col].value_counts().reset_index()
    issue_counts.columns = ['Specific Issue Extracted by LLM', 'Incident Count']
    
    # Show Sub-Breakdown Pie/Donut Chart
    col_chart, col_table = st.columns([3, 2])
    with col_chart:
        fig_micro = px.pie(
            issue_counts.head(5), # Show top 5 root causes
            values='Incident Count', 
            names='Specific Issue Extracted by LLM',
            title=f"Top Root Causes inside: {drill_choice_label}",
            hole=0.4
        )
        
        # 🛠️ THE FIX: Lock the height and force long legend texts to wrap onto new lines
        fig_micro.update_layout(
            height=400,  # Forces the chart layout size to be consistent
            legend=dict(
                itemwidth=40,  # Prevents text from pushing the chart
                font=dict(size=11)
            ),
            # Injects a CSS rule into Plotly to break long words onto a new line
            template="plotly_white"
        )
        # Wrap long text labels using a quick list comprehension for the chart display
        fig_micro.for_each_trace(lambda t: t.update(labels=[
            label if len(label) < 25 else label[:23] + "<br>" + label[23:] 
            for label in t.labels
        ]))
        
        st.plotly_chart(fig_micro, use_container_width=True)

    with col_table:
        st.write("📋 **Incident Frequencies**")
        # Added a matching height to the table container so everything looks balanced side-by-side
        st.dataframe(issue_counts, use_container_width=True, hide_index=True, height=400)
        
    # ==========================================
    # 6. EVIDENCE AUDIT FEED
    # ==========================================
    st.write("📝 **Raw Customer Evidence**")
    st.write(f"Read the raw reviews categorized under **{drill_choice_label}**:")
    
    # Display raw clean text and what the LLM extracted out of it side-by-side
    st.dataframe(
        drill_df[['clean_text', issues_col]].rename(
            columns={'clean_text': 'Raw Review text', issues_col: 'Extracted Bullet Points'}
        ),
        use_container_width=True,
        hide_index=True
    )
