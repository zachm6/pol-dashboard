import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
import numpy as np

st.set_page_config(
    page_title="Progressive Overload Dashboard",
    page_icon=":bar_chart:",
    layout='wide'
)

st.title("Progressive Overload Dashboard")

bodyPartDict = {

}

@st.cache_data
def load_data(path:str):
    data = pd.read_csv(path)
    # light cleaning
    # rename columns: replace space with underscore
    data.columns = data.columns.str.replace(" ", "_")

    # replace Date column with Month, Day, and Year
    data['Date'] = pd.to_datetime(data['Date'])
    data['Month'] = data['Date'].dt.month
    data['Day'] = data['Date'].dt.day
    data['Year'] = data['Date'].dt.year

    # drop columns
    data = data[[
        'Month',
        'Day',
        'Year',
        'Workout_Name',
        'Exercise_Name',
        'Weight',
        'Reps'
        ]]

    # add body part column
    # if-conditions

    return data

# File uploader
with st.sidebar:
    st.header("Configuration")
    uploaded_file = st.file_uploader("Choose a file")

if uploaded_file is None:
    st.info(" Upload a file through config", icon=':material/info:')
    st.stop()

df = load_data(uploaded_file)

# Filters
with st.sidebar: 
    exercise = st.selectbox(label="Select an Exercise", options=np.sort(df['Exercise_Name'].unique()))
    dateStart = st.date_input("Starting Date")
    dateEnd = st.date_input("Ending Date")

# Visualizations
df_filtered = duckdb.sql(
f"""
    SELECT
        *
    FROM 
        df
    WHERE 
        MONTH BETWEEN {dateStart.month} AND {dateEnd.month}
    AND DAY BETWEEN {dateStart.day} AND {dateEnd.day}
    AND YEAR BETWEEN {dateStart.year} AND {dateStart.year}
    AND EXERCISE_NAME = '{exercise}'
"""
)

# debugging
# st.dataframe(df_filtered)

# ------ KPIs ------
maxWeightdf = duckdb.sql(
    """
    SELECT
        WEIGHT,
        REPS,
        MAKE_DATE(Year, Month, Day) as Date
    FROM 
        df_filtered
    ORDER BY 
        WEIGHT DESC
    LIMIT 1;
    """
).fetchdf()

maxWeight = maxWeightdf.iloc[0][0]
maxWeightReps = maxWeightdf.iloc[0][1]
maxWeightDate = maxWeightdf.iloc[0][2]

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Max Weight (lbs)", value=maxWeight)

with col2:
    st.metric(f"Max Reps @ {maxWeight} lbs", value=maxWeightReps)

with col3:
    st.metric("Max Weight Date",value=f"{maxWeightDate.month}/{maxWeightDate.day}/{maxWeightDate.year}")

# ------ Max Weight Over Time ------
df_max_weight = duckdb.sql(
    """
    SELECT 
        MAKE_DATE(Year, Month, Day) as Date,
        Exercise_Name,
        MAX(Weight) as Max_Weight
    FROM
        df_filtered
    GROUP BY
        Date, Exercise_Name
    ORDER BY
        Date;
    """
).fetchdf()

fig_weight = px.line(
    df_max_weight,
    x="Date",
    y="Max_Weight",
    markers=True,
    title= f"Weight Over Time"
)
fig_weight.update_yaxes(rangemode="tozero")
st.plotly_chart(fig_weight)

# ------ Volume Over Time ------
df_volume = duckdb.sql(
    """
    SELECT
        Date,
        Exercise_Name,
        SUM(Volume) as Volume
    FROM (
        SELECT 
            MAKE_DATE(Year, Month, Day) as Date,
            Exercise_Name,
            SUM(Reps) * CASE WHEN Weight = 0 THEN 1 ELSE Weight END AS Volume
        FROM
            df_filtered
        GROUP BY
            Date, Exercise_Name, Weight
        ORDER BY
            Date
    ) 
    GROUP By 
        Date, Exercise_Name
    ORDER BY
        DATE;
    """
).fetchdf()

# debugging
# st.dataframe(df_volume)

fig_volume = px.line(
    df_volume,
    x="Date",
    y="Volume",
    markers=True,
    title= f"Volume Over Time"
)
fig_volume.update_yaxes(rangemode="tozero")
st.plotly_chart(fig_volume)

# ------ Reps Over Time ------
df_sum_reps = duckdb.sql(
    """
    SELECT 
        MAKE_DATE(Year, Month, Day) as Date,
        Exercise_Name,
        SUM(Reps) as Total_Reps
    FROM
        df_filtered
    GROUP BY
        Month, Day, Year, Exercise_Name
    ORDER BY
        Date;
    """
).fetchdf()

fig_reps = px.line(
    df_sum_reps,
    x="Date",
    y="Total_Reps",
    markers=True,
    title= f"Reps Over Time"
)
fig_reps.update_yaxes(rangemode="tozero")
st.plotly_chart(fig_reps)

# st.dataframe(df_filtered)
# st.dataframe(df_sum_reps)

#TODO 
# Simplify filtering: add another selectbox, ex: body part & Category, so that when you select an exercise there are less choices
# create a table and then use inner join to enhance original dataset