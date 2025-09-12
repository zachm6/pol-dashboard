# Public URL: https://pol-dashboard.streamlit.app/
import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
import datetime

st.set_page_config(
    page_title="Progressive Overload Dashboard",
    page_icon=":bar_chart:",
    layout='wide'
)

st.title("Progressive Overload Dashboard")

@st.cache_data
def load_data(path:str):
    data = pd.read_csv(path)
    # light cleaning
    # rename columns: replace space with underscore
    data.columns = data.columns.str.replace(" ", "_")

    # replace Date column with Month, Day, and Year
    data['Date'] = pd.to_datetime(data['Date'])

    # drop columns
    data = data[[
        'Date',
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

# Dataset
if uploaded_file is None:
    st.info(" This is a sample dataset. Use Configuration to upload a unique CSV file. If you are uploading a unique CSV file, ensure the columns are named accordingly: Date, Exercise Name, Weight, Reps", icon=':material/info:')
    df = load_data('data/strong_2.csv')
else:
    df =load_data(uploaded_file)

# Filters
with st.sidebar:
    twentyOneDaysAgo = datetime.date.today() - datetime.timedelta(days=21)
    dateStart_str = st.date_input(label="Starting Date", value=twentyOneDaysAgo).strftime("%Y-%m-%d")
    dateEnd_str = st.date_input("Ending Date").strftime("%Y-%m-%d")

    # compute counts of rows per exercise in the date range
    exercise_counts = duckdb.sql(
        f"""
        SELECT
            Exercise_Name, 
            COUNT(*) AS Count
        FROM 
            df
        WHERE 
            Date Between DATE '{dateStart_str}' AND '{dateEnd_str}'
        GROUP BY
            Exercise_Name
        ORDER BY 
            Exercise_Name
        """
    ).fetchdf()

    if exercise_counts.empty:
        st.warning("No exercises found in this date range.")
        st.stop()

    # build label => value mapping
    options = {
        f"({row.Count}) {row.Exercise_Name}": row.Exercise_Name
        for row in exercise_counts.itertuples(index=False)
    }

    # selectbox with labels including counts
    selected_label = st.selectbox("Select an Exercise", options=list(options.keys()))
    exercise = options[selected_label]

# Visualizations
df_filtered = duckdb.sql(
f"""
    SELECT
        *
    FROM 
        df
    WHERE 
        Date BETWEEN DATE '{dateStart_str}' AND DATE '{dateEnd_str}'
        AND EXERCISE_NAME = '{exercise}'
"""
).fetchdf()

# ------ KPIs ------
maxWeightdf = duckdb.sql(
    """
    SELECT
        WEIGHT,
        REPS,
        Date
    FROM 
        df_filtered
    ORDER BY 
        WEIGHT DESC
    LIMIT 1;
    """
).fetchdf()

if maxWeightdf.empty:
    st.warning('No data available for this exercise and date range.')

else:
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
            Date,
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
                Date,
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
            Date,
            Exercise_Name,
            SUM(Reps) as Total_Reps
        FROM
            df_filtered
        GROUP BY
            Date, Exercise_Name
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

#TODO 
# Simplify filtering: add another selectbox, ex: body part & Category, so that when you select an exercise there are less choices
# create a table and then use inner join to enhance original dataset